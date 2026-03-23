"""Client for BTS time-series forecasting pipeline.

Supports three data sources:
  --mode real                    Generate random sensor data (default)
  --mode simulated --sim-config  Send sample IDs for ground-truth tracking
  --dataset path/to/folder       Read real sensor data from CSV files

Dataset folder format:
  dataset/
    readings_001.csv   (columns: temperature,humidity,hvac_power,lighting_power,occupancy,solar_irradiance)
    readings_002.csv
    ...
  Each CSV row is one sensor reading sent as a request.
  If a "label" column exists, it's used as ground_truth.
"""
from __future__ import annotations

import argparse
import csv
import logging
import random
import time
from pathlib import Path
from typing import Any, Iterator

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


def generate_sensor_data() -> list[float]:
    """Generate random building sensor readings."""
    return [
        round(random.gauss(22.0, 5.0), 2),
        round(random.gauss(50.0, 15.0), 2),
        round(max(0, random.gauss(15.0, 8.0)), 2),
        round(max(0, random.gauss(5.0, 3.0)), 2),
        round(max(0, random.gauss(50.0, 30.0))),
        round(max(0, random.gauss(400.0, 200.0)), 2),
    ]


def iter_dataset(dataset_dir: str) -> Iterator[tuple[list[float], str]]:
    """Iterate over CSV files in dataset directory.

    Yields (sensor_values, ground_truth_label) tuples.
    Cycles through the dataset indefinitely.
    """
    dataset_path = Path(dataset_dir)
    csv_files = sorted(dataset_path.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {dataset_dir}")

    logger.info(f"Loading dataset from {dataset_dir}: {len(csv_files)} CSV files")

    while True:
        for csv_file in csv_files:
            with open(csv_file, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    label = row.pop("label", "")
                    values = [float(v) for v in row.values()]
                    yield values, label


def run_workload(
    gateway_url: str,
    rps: float,
    duration_seconds: int,
    output_csv: str,
    mode: str = "real",
    dataset_dir: str | None = None,
    sim_config: str | None = None,
    pipeline_id: str = "bts",
) -> None:
    """Run workload against gateway and log results."""
    data_gen = None
    dataset_iter: Iterator[tuple[list[float], str]] | None = None

    if mode == "simulated":
        from simulation.simulated_data_generator import SimulatedDataGenerator
        data_gen = SimulatedDataGenerator(sim_config or "sim_config/client.yaml")
    elif dataset_dir:
        dataset_iter = iter_dataset(dataset_dir)

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

        logger.info(
            f"Starting workload: {rps} RPS for {duration_seconds}s -> {gateway_url} "
            f"(mode={mode}, dataset={'yes' if dataset_dir else 'no'})"
        )

        with httpx.Client(timeout=30.0) as client:
            while time.time() < end_time:
                start = time.perf_counter()

                sample_id = ""
                ground_truth = ""
                payload: dict[str, Any]

                if data_gen:
                    sample_id, ground_truth = data_gen.next_sample()
                    payload = {"data": sample_id}
                elif dataset_iter:
                    sensor_values, ground_truth = next(dataset_iter)
                    sample_id = f"dataset-{request_count}"
                    payload = {"data": sensor_values}
                else:
                    payload = {"data": generate_sensor_data()}

                try:
                    response = client.post(
                        f"{gateway_url}/predict",
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
    parser = argparse.ArgumentParser(description="BTS Client")
    parser.add_argument("--gateway", default="http://localhost:8000", help="Gateway URL")
    parser.add_argument("--rps", type=float, default=5.0, help="Requests per second")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--output", default="./results/client_results.csv", help="Output CSV path")
    parser.add_argument("--profile", default=None, help="Workload profile YAML path")
    parser.add_argument("--pipeline-id", default="bts", help="Pipeline ID for monitoring")
    parser.add_argument("--mode", choices=["real", "simulated"], default="real", help="Client mode")
    parser.add_argument("--sim-config", default=None, help="Simulation client config YAML path")
    parser.add_argument("--dataset", default=None, help="Path to dataset folder with CSV files")
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
        dataset_dir=args.dataset,
        sim_config=args.sim_config,
        pipeline_id=args.pipeline_id,
    )


if __name__ == "__main__":
    main()
