"""Run latency-accuracy tradeoff experiment across ensemble sizes.

For each (app, ensemble_size, repetition) combination:
  1. PATCH the orchestrator to set ensemble_size on all modalities
  2. Run the client for the configured duration
  3. Collect the results CSV
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

import httpx
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

APP_DIR_MAP: dict[str, str] = {
    "bts": "bts",
    "cctvs": "cctvs",
    "object-classification": "object_classification",
    "smart-building": "smart_building",
}

APP_PIPELINE_MAP: dict[str, str] = {
    "bts": "bts",
    "cctvs": "cctvs",
    "object-classification": "object-classification",
    "smart-building": "smart-building",
}

REPO_ROOT = Path(__file__).resolve().parents[3]


def load_config(config_path: str) -> dict:
    """Load scenario configuration from YAML."""
    with open(config_path) as f:
        return yaml.safe_load(f)["scenario"]


def patch_ensemble_size(
    orchestrator_url: str,
    pipeline_id: str,
    ensemble_size: int,
) -> None:
    """Patch all modality ensembles to use the given ensemble size."""
    plans_url = f"{orchestrator_url}/plans/{pipeline_id}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(plans_url)
        resp.raise_for_status()
        plan = resp.json()

    modality_ensembles: dict = plan.get("modality_ensembles", {})
    if not modality_ensembles:
        raise RuntimeError(f"No modality ensembles found for pipeline '{pipeline_id}'")

    with httpx.Client(timeout=10.0) as client:
        for modality, ensemble_data in modality_ensembles.items():
            ensemble_data["ensemble_size"] = ensemble_size

            # Activate only the first N members, deactivate the rest
            members = ensemble_data.get("ensemble_members", [])
            for i, member in enumerate(members):
                member["is_active"] = i < ensemble_size

            patch_url = f"{orchestrator_url}/plans/{pipeline_id}/ensemble/{modality}"
            resp = client.patch(patch_url, json=ensemble_data)
            resp.raise_for_status()
            logger.info(
                f"Set {modality} ensemble_size={ensemble_size} for {pipeline_id} "
                f"({min(ensemble_size, len(members))}/{len(members)} members active)"
            )


def run_client(
    app_name: str,
    gateway_url: str,
    rps: float,
    duration_seconds: int,
    output_csv: str,
    pipeline_id: str,
) -> None:
    """Run an application client as a subprocess."""
    app_dir = APP_DIR_MAP[app_name]
    client_script = REPO_ROOT / "examples" / "applications" / app_dir / "client" / "client.py"
    if not client_script.is_file():
        raise FileNotFoundError(f"Client script not found: {client_script}")

    cmd = [
        sys.executable,
        str(client_script),
        "--gateway", gateway_url,
        "--rps", str(rps),
        "--duration", str(duration_seconds),
        "--output", output_csv,
        "--pipeline-id", pipeline_id,
    ]
    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        logger.error(f"Client exited with code {result.returncode}")
    else:
        logger.info(f"Client finished, results at {output_csv}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Latency-accuracy tradeoff experiment runner")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).parent / "config.yaml"),
        help="Path to scenario config.yaml",
    )
    parser.add_argument("--output-dir", default="./output", help="Directory for result CSVs")
    parser.add_argument("--gateway-url", default="http://localhost:8000", help="Gateway URL")
    parser.add_argument("--orchestrator-url", default="http://localhost:8001", help="Orchestrator URL")
    args = parser.parse_args()

    config = load_config(args.config)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    apps: list[str] = config["apps"]
    ensemble_sizes: list[int] = config["ensemble_sizes"]
    rps: float = config["rps"]
    duration: int = config["duration_seconds"]
    repetitions: int = config["repetitions"]

    total_runs = len(apps) * len(ensemble_sizes) * repetitions
    run_index = 0

    for app_name in apps:
        pipeline_id = APP_PIPELINE_MAP[app_name]
        for ensemble_size in ensemble_sizes:
            for rep in range(1, repetitions + 1):
                run_index += 1
                print(
                    f"[{run_index}/{total_runs}] "
                    f"app={app_name} ensemble_size={ensemble_size} rep={rep}"
                )

                try:
                    patch_ensemble_size(
                        args.orchestrator_url, pipeline_id, ensemble_size,
                    )
                except Exception as exc:
                    logger.error(
                        f"Failed to patch ensemble size for {app_name}/size={ensemble_size}: {exc}"
                    )
                    continue

                csv_name = f"{app_name}_size{ensemble_size}_rep{rep}.csv"
                csv_path = str(output_dir / csv_name)

                try:
                    run_client(
                        app_name=app_name,
                        gateway_url=args.gateway_url,
                        rps=rps,
                        duration_seconds=duration,
                        output_csv=csv_path,
                        pipeline_id=pipeline_id,
                    )
                except Exception as exc:
                    logger.error(f"Client run failed for {csv_name}: {exc}")

    print(f"Experiment complete. Results saved to {output_dir}")


if __name__ == "__main__":
    main()
