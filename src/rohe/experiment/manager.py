from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from rohe.repositories.base import ExperimentRepository

logger = logging.getLogger(__name__)


class ExperimentManager:
    """Manages experiment lifecycle: create, start, stop, query.

    All monitoring data collected during an experiment is tagged with
    the experiment_id for later filtering and export.
    """

    def __init__(self, repo: ExperimentRepository) -> None:
        self._repo = repo

    def create(
        self,
        name: str,
        algorithm: str,
        contract_id: str,
        pipeline_id: str,
        config: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a new experiment."""
        experiment_id = str(uuid.uuid4())
        experiment: dict[str, Any] = {
            "experiment_id": experiment_id,
            "name": name,
            "algorithm": algorithm,
            "contract_id": contract_id,
            "pipeline_id": pipeline_id,
            "status": "created",
            "config": config or {},
            "tags": tags or {},
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "started_at": None,
            "stopped_at": None,
        }
        self._repo.create_experiment(experiment)
        logger.info(f"Created experiment '{name}' ({experiment_id})")
        return experiment

    def start(self, experiment_id: str) -> dict[str, Any] | None:
        """Start an experiment (set status to running)."""
        experiment = self._repo.get_experiment(experiment_id)
        if experiment is None:
            return None

        if experiment["status"] == "running":
            logger.warning(f"Experiment '{experiment_id}' is already running")
            return experiment

        self._repo.update_experiment(
            experiment_id,
            {
                "status": "running",
                "started_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        )
        logger.info(f"Started experiment '{experiment['name']}' ({experiment_id})")
        return self._repo.get_experiment(experiment_id)

    def stop(self, experiment_id: str) -> dict[str, Any] | None:
        """Stop an experiment (set status to stopped)."""
        experiment = self._repo.get_experiment(experiment_id)
        if experiment is None:
            return None

        self._repo.update_experiment(
            experiment_id,
            {
                "status": "stopped",
                "stopped_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        )
        logger.info(f"Stopped experiment '{experiment['name']}' ({experiment_id})")
        return self._repo.get_experiment(experiment_id)

    def get(self, experiment_id: str) -> dict[str, Any] | None:
        """Get experiment by ID."""
        return self._repo.get_experiment(experiment_id)

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get experiment by name."""
        return self._repo.get_experiment_by_name(name)

    def list(
        self,
        status: str | None = None,
        pipeline_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List experiments with optional filters."""
        return self._repo.list_experiments(status=status, pipeline_id=pipeline_id)

    def delete(self, experiment_id: str) -> bool:
        """Delete an experiment."""
        return self._repo.delete_experiment(experiment_id)
