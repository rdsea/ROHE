"""Client for smart building multi-modal activity recognition.

The client does NOT send data -- data is streamed continuously to DataHub
by the data-streamer service. The client sends inference requests with:
  - modalities: which sensor streams to use
  - window_length: how many recent samples to extract per modality
  - time_constraint_ms: end-to-end latency budget

The orchestrator tells the preprocessor to extract a window of data from
DataHub's stream buffer, preprocess it, and feed it to inference services.
"""
from __future__ import annotations

import argparse
import csv
import logging
import time
from pathlib import Path

import httpx
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    from rohe.monitoring.sdk import RoheMonitor
    monitor = RoheMonitor.from_env()
except Exception:
    monitor = None  # type: ignore[assignment]


def load_workload_profile(profile_path: str) -> dict:
    """Load workload profile from YAML."""
    with open(profile_path) as f:
        return yaml.safe_load(f)


def run_workload(
    control_plane_url: str,
    rps: float,
    duration_seconds: int,
    output_csv: str,
    modalities: list[str],
    window_length: int = 128,
    time_constraint_ms: float = 500.0,
    pipeline_id: str = "smart-building",
) -> None:
    """Send inference requests to the gateway.

    Each request specifies which modalities and window length.
    No data is sent -- the preprocessor extracts it from DataHub streams.
    """
    interval = 1.0 / rps if rps > 0 else 1.0
    end_time = time.time() + duration_seconds
    request_count = 0

    csv_path = Path(output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "query_id", "timestamp", "modalities", "window_length",
            "response_time_ms", "top_prediction", "confidence",
            "model_count", "status",
        ])

        logger.info(
            f"Starting workload: {rps} RPS for {duration_seconds}s "
            f"-> {control_plane_url} (modalities={modalities}, "
            f"window={window_length}, time_constraint={time_constraint_ms}ms)"
        )

        with httpx.Client(timeout=max(30.0, time_constraint_ms / 1000 * 2)) as client:
            while time.time() < end_time:
                start = time.perf_counter()

                payload = {
                    "modalities": modalities,
                    "window_length": window_length,
                    "time_constraint_ms": time_constraint_ms,
                }

                try:
                    response = client.post(
                        f"{control_plane_url}/predict",
                        json=payload,
                    )
                    elapsed_ms = (time.perf_counter() - start) * 1000

                    if response.status_code == 200:
                        data = response.json()
                        query_id = data["query_id"]
                        ensemble = data.get("ensemble_result", {})
                        top_class = next(iter(ensemble), "")
                        top_conf = ensemble.get(top_class, 0.0)
                        model_count = data.get("model_count", 0)

                        writer.writerow([
                            query_id, time.time(),
                            "+".join(modalities), window_length,
                            round(elapsed_ms, 2), top_class, round(top_conf, 4),
                            model_count, "ok",
                        ])

                        if monitor:
                            monitor.report_request(
                                query_id=query_id,
                                pipeline_id=pipeline_id,
                                response_time_ms=elapsed_ms,
                                ground_truth=None,
                                prediction=ensemble,
                            )
                    else:
                        writer.writerow([
                            "", time.time(),
                            "+".join(modalities), window_length,
                            round(elapsed_ms, 2), "", 0, 0,
                            f"error-{response.status_code}",
                        ])
                except Exception as e:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    writer.writerow([
                        "", time.time(),
                        "+".join(modalities), window_length,
                        round(elapsed_ms, 2), "", 0, 0, str(e),
                    ])

                request_count += 1
                sleep_time = interval - (time.perf_counter() - start)
                if sleep_time > 0:
                    time.sleep(sleep_time)

    if monitor:
        monitor.flush()
        monitor.close()

    logger.info(f"Workload complete: {request_count} requests sent, results in {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smart Building Client")
    parser.add_argument(
        "--control-plane", default="http://localhost:8000",
        help="Control plane (gateway) URL",
    )
    parser.add_argument("--rps", type=float, default=5.0, help="Requests per second")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument(
        "--output", default="./results/client_results.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--modalities", nargs="+",
        default=["video", "acc_phone", "acc_watch", "gyro", "orientation"],
        help="Modalities to request inference on",
    )
    parser.add_argument(
        "--window-length", type=int, default=128,
        help="Number of recent samples to extract per modality",
    )
    parser.add_argument(
        "--time-constraint", type=float, default=500.0,
        help="End-to-end time constraint in milliseconds",
    )
    parser.add_argument("--profile", default=None, help="Workload profile YAML path")
    parser.add_argument(
        "--pipeline-id", default="smart-building",
        help="Pipeline ID for monitoring",
    )
    args = parser.parse_args()

    if args.profile:
        profile = load_workload_profile(args.profile)
        args.rps = profile.get("rps", args.rps)
        args.duration = profile.get("duration_seconds", args.duration)
        args.modalities = profile.get("modalities", args.modalities)
        args.window_length = profile.get("window_length", args.window_length)
        args.time_constraint = profile.get("time_constraint_ms", args.time_constraint)

    run_workload(
        control_plane_url=args.control_plane,
        rps=args.rps,
        duration_seconds=args.duration,
        output_csv=args.output,
        modalities=args.modalities,
        window_length=args.window_length,
        time_constraint_ms=args.time_constraint,
        pipeline_id=args.pipeline_id,
    )


if __name__ == "__main__":
    main()
