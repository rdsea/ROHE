"""Simulated client for smart building multi-modal activity recognition.

Sends multi-modal inference queries to the control plane at configurable
rates and logs results to CSV. Supports modality selection (video only,
timeseries only, or both). Reports metrics via rohe-sdk.
"""
from __future__ import annotations

import argparse
import csv
import logging
import random
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

SENSOR_DATA_LENGTH = 128


def load_workload_profile(profile_path: str) -> dict:
    """Load workload profile from YAML."""
    with open(profile_path) as f:
        return yaml.safe_load(f)


def generate_dummy_sensor_data(length: int = SENSOR_DATA_LENGTH) -> list[float]:
    """Generate simulated accelerometer/gyroscope sensor readings."""
    return [random.gauss(0.0, 1.0) for _ in range(length)]


def run_workload(
    control_plane_url: str,
    rps: float,
    duration_seconds: int,
    output_csv: str,
    modalities: list[str],
    time_constraint_ms: int = 500,
    pipeline_id: str = "smart-building",
) -> None:
    """Run workload against control plane and log results."""
    interval = 1.0 / rps if rps > 0 else 1.0
    end_time = time.time() + duration_seconds
    request_count = 0

    csv_path = Path(output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "query_id", "timestamp", "response_time_ms", "top_prediction",
            "confidence", "model_count", "modalities_used", "status",
        ])

        logger.info(
            f"Starting workload: {rps} RPS for {duration_seconds}s "
            f"-> {control_plane_url} (modalities: {modalities})"
        )

        with httpx.Client(timeout=30.0) as client:
            while time.time() < end_time:
                start = time.perf_counter()

                payload: dict = {
                    "modalities": modalities,
                    "time_constraint_ms": time_constraint_ms,
                }

                if "timeseries" in modalities:
                    payload["timeseries_data"] = generate_dummy_sensor_data()

                try:
                    response = client.post(
                        f"{control_plane_url}/infer",
                        json=payload,
                    )
                    elapsed_ms = (time.perf_counter() - start) * 1000

                    if response.status_code == 200:
                        data = response.json()
                        query_id = data["query_id"]
                        ensemble = data.get("ensemble_result", {})
                        top_class = next(iter(ensemble), "unknown")
                        top_conf = ensemble.get(top_class, 0.0)
                        model_count = len(data.get("individual_results", []))
                        used_modalities = ",".join(data.get("modalities_used", []))

                        writer.writerow([
                            query_id, time.time(), round(elapsed_ms, 2),
                            top_class, round(top_conf, 4), model_count,
                            used_modalities, "ok",
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
                            "", time.time(), round(elapsed_ms, 2),
                            "", 0, 0, "", f"error-{response.status_code}",
                        ])
                except Exception as e:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    writer.writerow([
                        "", time.time(), round(elapsed_ms, 2),
                        "", 0, 0, "", str(e),
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
    parser = argparse.ArgumentParser(description="Smart Building Simulated Client")
    parser.add_argument(
        "--control-plane", default="http://localhost:8000",
        help="Control plane URL",
    )
    parser.add_argument("--rps", type=float, default=5.0, help="Requests per second")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument(
        "--output", default="./results/client_results.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--modalities", nargs="+", default=["video", "timeseries"],
        choices=["video", "timeseries"],
        help="Modalities to include in queries",
    )
    parser.add_argument(
        "--time-constraint", type=int, default=500,
        help="Time constraint in milliseconds",
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
        args.time_constraint = profile.get("time_constraint_ms", args.time_constraint)

    run_workload(
        control_plane_url=args.control_plane,
        rps=args.rps,
        duration_seconds=args.duration,
        output_csv=args.output,
        modalities=args.modalities,
        time_constraint_ms=args.time_constraint,
        pipeline_id=args.pipeline_id,
    )


if __name__ == "__main__":
    main()
