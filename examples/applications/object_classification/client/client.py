"""Client for object classification pipeline.

Supports two modes:
  --mode real       Send real/dummy images (default)
  --mode simulated  Send sample IDs from sim_config for ground-truth tracking
"""
from __future__ import annotations

import argparse
import csv
import io
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


def generate_dummy_image() -> bytes:
    """Generate a small dummy image for testing."""
    from PIL import Image
    img = Image.new("RGB", (224, 224), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def run_workload(
    gateway_url: str,
    rps: float,
    duration_seconds: int,
    output_csv: str,
    mode: str = "real",
    sim_config: str | None = None,
    pipeline_id: str = "object-classification",
) -> None:
    """Run workload against gateway and log results."""
    data_gen = None
    if mode == "simulated":
        from simulation.simulated_data_generator import SimulatedDataGenerator
        data_gen = SimulatedDataGenerator(sim_config or "sim_config/client.yaml")

    interval = 1.0 / rps if rps > 0 else 1.0
    end_time = time.time() + duration_seconds
    request_count = 0

    csv_path = Path(output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "query_id", "timestamp", "sample_id", "ground_truth",
            "response_time_ms", "top_prediction", "confidence",
            "model_count", "status",
        ])

        logger.info(f"Starting workload: {rps} RPS for {duration_seconds}s -> {gateway_url} (mode={mode})")

        with httpx.Client(timeout=30.0) as client:
            while time.time() < end_time:
                start = time.perf_counter()

                sample_id = ""
                ground_truth = ""

                try:
                    if data_gen:
                        sample_id, ground_truth = data_gen.next_sample()
                        response = client.post(
                            f"{gateway_url}/predict",
                            json={"data": sample_id},
                        )
                    else:
                        image_bytes = generate_dummy_image()
                        response = client.post(
                            f"{gateway_url}/predict",
                            files={"image": ("test.jpg", image_bytes, "image/jpeg")},
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
                            query_id, time.time(), sample_id, ground_truth,
                            round(elapsed_ms, 2), top_class, round(top_conf, 4),
                            model_count, "ok",
                        ])

                        if monitor:
                            monitor.report_request(
                                query_id=query_id,
                                pipeline_id=pipeline_id,
                                response_time_ms=elapsed_ms,
                                ground_truth=ground_truth or None,
                                prediction=ensemble,
                            )
                    else:
                        writer.writerow([
                            "", time.time(), sample_id, ground_truth,
                            round(elapsed_ms, 2), "", 0, 0,
                            f"error-{response.status_code}",
                        ])
                except Exception as e:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    writer.writerow([
                        "", time.time(), sample_id, ground_truth,
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
    parser = argparse.ArgumentParser(description="Object Classification Client")
    parser.add_argument("--gateway", default="http://localhost:8000", help="Gateway URL")
    parser.add_argument("--rps", type=float, default=5.0, help="Requests per second")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--output", default="./results/client_results.csv", help="Output CSV path")
    parser.add_argument("--profile", default=None, help="Workload profile YAML path")
    parser.add_argument("--pipeline-id", default="object-classification", help="Pipeline ID for monitoring")
    parser.add_argument("--mode", choices=["real", "simulated"], default="real", help="Client mode")
    parser.add_argument("--sim-config", default=None, help="Simulation client config YAML path")
    args = parser.parse_args()

    if args.profile:
        profile = load_workload_profile(args.profile)
        args.rps = profile.get("rps", args.rps)
        args.duration = profile.get("duration_seconds", args.duration)

    run_workload(
        gateway_url=args.gateway,
        rps=args.rps,
        duration_seconds=args.duration,
        output_csv=args.output,
        mode=args.mode,
        sim_config=args.sim_config,
        pipeline_id=args.pipeline_id,
    )


if __name__ == "__main__":
    main()
