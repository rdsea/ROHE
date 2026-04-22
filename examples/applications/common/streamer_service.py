"""Reusable data streamer service factory.

Reads data from a dataset directory and continuously pushes samples
to DataHub's stream buffer at a configurable rate. Simulates real
sensor/camera data streams in a K8s deployment.

Each modality streams independently. The streamer reads files from
the dataset, parses them, and pushes one sample at a time to
DataHub's POST /stream/push endpoint.
"""
from __future__ import annotations

import asyncio
import csv
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI

logger = logging.getLogger(__name__)


def create_streamer_app() -> FastAPI:
    """Create a data streamer FastAPI application.

    The streamer starts pushing data on startup and runs continuously
    in a background task. It also exposes /health and /status endpoints.
    """
    app = FastAPI(title="Data Streamer")
    app.state.running = False
    app.state.stats: dict[str, int] = {}  # modality -> samples pushed

    @app.on_event("startup")
    async def startup() -> None:
        data_hub_url = os.environ.get("DATA_HUB_URL", "http://data-hub:8000")
        dataset_dir = os.environ.get("DATASET_DIR", "/data/dataset")
        stream_rate = float(os.environ.get("STREAM_RATE", "10"))  # samples/sec per modality
        modalities_str = os.environ.get("STREAM_MODALITIES", "")

        if not Path(dataset_dir).is_dir():
            logger.warning(f"Dataset dir {dataset_dir} not found, streamer idle")
            return

        modalities = [m.strip() for m in modalities_str.split(",") if m.strip()]
        if not modalities:
            # Auto-detect modalities from subdirectories
            modalities = [
                d.name for d in sorted(Path(dataset_dir).iterdir()) if d.is_dir()
            ]
        if not modalities:
            # Flat directory -- single modality named "default"
            modalities = ["default"]

        logger.info(
            f"Streamer starting: {len(modalities)} modalities at {stream_rate} samples/sec "
            f"from {dataset_dir} -> {data_hub_url}"
        )

        app.state.running = True
        app.state.tasks = []
        for modality in modalities:
            app.state.stats[modality] = 0
            task = asyncio.create_task(
                _stream_modality(app, data_hub_url, dataset_dir, modality, stream_rate)
            )
            app.state.tasks.append(task)

    @app.on_event("shutdown")
    async def shutdown() -> None:
        app.state.running = False
        for task in getattr(app.state, "tasks", []):
            task.cancel()

    @app.get("/status")
    async def status() -> dict[str, Any]:
        return {
            "running": app.state.running,
            "modalities": app.state.stats,
        }

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok" if app.state.running else "idle",
            "service": "data-streamer",
        }

    return app


async def _stream_modality(
    app: FastAPI,
    data_hub_url: str,
    dataset_dir: str,
    modality: str,
    rate: float,
) -> None:
    """Stream data for a single modality in a loop."""
    interval = 1.0 / rate if rate > 0 else 1.0
    dataset_path = Path(dataset_dir)

    # Determine data source for this modality
    modality_dir = dataset_path / modality
    if modality_dir.is_dir():
        data_iter = _iter_modality_data(modality_dir, modality)
    else:
        data_iter = _iter_modality_data(dataset_path, modality)

    async with httpx.AsyncClient(timeout=5.0) as client:
        while app.state.running:
            try:
                sample = next(data_iter)
                await client.post(
                    f"{data_hub_url}/stream/push",
                    json={
                        "modality": modality,
                        "data": sample,
                        "timestamp": time.time(),
                    },
                )
                app.state.stats[modality] += 1
            except StopIteration:
                break
            except (httpx.TimeoutException, httpx.ConnectError):
                logger.debug("DataHub unavailable, retrying in 1s")
                await asyncio.sleep(1.0)
                continue
            except Exception as e:
                logger.warning(f"Stream error for {modality}: {e}")

            await asyncio.sleep(interval)

    logger.info(f"Streamer for '{modality}' stopped after {app.state.stats.get(modality, 0)} samples")


def _iter_modality_data(data_dir: Path, modality: str) -> Any:
    """Iterate over data files for a modality, cycling indefinitely.

    Supports:
    - CSV files: each row is a sample (list of floats)
    - Text files with one value per line
    - Falls back to generating sequential sample IDs
    """
    csv_files = sorted(data_dir.glob("*.csv"))
    if csv_files:
        while True:
            for csv_file in csv_files:
                with open(csv_file, newline="") as f:
                    reader = csv.reader(f)
                    next(reader, None)  # skip header
                    for row in reader:
                        try:
                            yield [float(v) for v in row]
                        except ValueError:
                            yield row

    # No CSV files -- generate sequential sample IDs
    counter = 0
    while True:
        yield f"{modality}-sample-{counter:06d}"
        counter += 1
