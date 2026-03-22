"""Simulated client for building energy time-series forecasting pipeline.

Sends sensor data to the gateway at configurable rates and logs results to CSV.
Reports predictions via rohe-sdk for quality evaluation.
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


def load_workload_profile(profile_path: str) -> dict:
    """Load workload profile from YAML."""
    with open(profile_path) as f:
        return yaml.safe_load(f)


def generate_sensor_data() -> list[float]:
    """Generate simulated building sensor readings.

    Returns 6 float values:
    [temperature_c, humidity_pct, hvac_power_kw, lighting_power_kw,
     occupancy_count, solar_irradiance_wm2]
    """
    return [
        round(random.gauss(22.0, 5.0), 2),     # temperature_c
        round(random.gauss(50.0, 15.0), 2),     # humidity_pct
        round(max(0, random.gauss(15.0, 8.0)), 2),  # hvac_power_kw
        round(max(0, random.gauss(5.0, 3.0)), 2),   # lighting_power_kw
        round(max(0, random.gauss(50.0, 30.0))),     # occupancy_count
        round(max(0, random.gauss(400.0, 200.0)), 2),  # solar_irradiance_wm2
    ]


def run_workload(
    gateway_url: str,
    rps: float,
    duration_seconds: int,
    output_csv: str,
    pipeline_id: str = "bts",
) -> None:
    """Run workload against gateway and log results."""
    interval = 1.0 / rps if rps > 0 else 1.0
    end_time = time.time() + duration_seconds
    request_count = 0

    csv_path = Path(output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "query_id", "timestamp", "response_time_ms",
            "energy_forecast_kwh", "avg_confidence", "model_count", "status",
        ])

        logger.info(f"Starting workload: {rps} RPS for {duration_seconds}s -> {gateway_url}")

        with httpx.Client(timeout=30.0) as client:
            while time.time() < end_time:
                start = time.perf_counter()

                sensor_data = generate_sensor_data()

                try:
                    response = client.post(
                        f"{gateway_url}/forecast",
                        json={"sensor_values": sensor_data},
                    )
                    elapsed_ms = (time.perf_counter() - start) * 1000

                    if response.status_code == 200:
                        data = response.json()
                        query_id = data["query_id"]
                        ensemble = data.get("ensemble_result", {})
                        energy_forecast = ensemble.get("energy_forecast_kwh", 0.0)
                        model_count = len(data.get("individual_results", []))
                        confidences = [
                            r["confidence"] for r in data.get("individual_results", [])
                        ]
                        avg_confidence = (
                            sum(confidences) / len(confidences) if confidences else 0.0
                        )

                        writer.writerow([
                            query_id, time.time(), round(elapsed_ms, 2),
                            round(energy_forecast, 4), round(avg_confidence, 4),
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
                            "", time.time(), round(elapsed_ms, 2),
                            "", 0, 0, f"error-{response.status_code}",
                        ])
                except Exception as e:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    writer.writerow(["", time.time(), round(elapsed_ms, 2), "", 0, 0, str(e)])

                request_count += 1

                sleep_time = interval - (time.perf_counter() - start)
                if sleep_time > 0:
                    time.sleep(sleep_time)

    if monitor:
        monitor.flush()
        monitor.close()

    logger.info(f"Workload complete: {request_count} requests sent, results in {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="BTS Simulated Client")
    parser.add_argument("--gateway", default="http://localhost:8000", help="Gateway URL")
    parser.add_argument("--rps", type=float, default=5.0, help="Requests per second")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--output", default="./results/client_results.csv", help="Output CSV path")
    parser.add_argument("--profile", default=None, help="Workload profile YAML path")
    parser.add_argument("--pipeline-id", default="bts", help="Pipeline ID for monitoring")
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
        pipeline_id=args.pipeline_id,
    )


if __name__ == "__main__":
    main()
