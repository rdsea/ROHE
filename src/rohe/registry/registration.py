from __future__ import annotations

import copy
import logging
import time
import uuid
from typing import Any

from rohe.repositories.base import PipelineRepository

logger = logging.getLogger(__name__)


class ApplicationRegistrar:
    """Application registration and metadata management.

    Moved from observation/registration_manager.py to registry/ since
    registration is a Registry concern, not an Observation concern.
    Uses PipelineRepository for storage instead of direct MDBClient.
    """

    def __init__(self, repository: PipelineRepository) -> None:
        self._repo = repository

    def get_app(self, application_name: str) -> dict[str, Any] | None:
        """Get application by name."""
        return self._repo.get_application(application_name)

    def register_app(
        self,
        application_name: str,
        run_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Register a new application and return its metadata."""
        app_id = str(uuid.uuid4())
        metadata: dict[str, Any] = {
            "application_name": application_name,
            "run_id": run_id,
            "user_id": user_id,
            "app_id": app_id,
            "db": f"application_{application_name}_{app_id}",
            "timestamp": time.time(),
            "client_count": 1,
        }

        self._repo.register_application(metadata)
        logger.info(f"Registered application '{application_name}' with id '{app_id}'")
        return metadata

    def update_app(self, application_name: str, updates: dict[str, Any]) -> bool:
        """Update application metadata."""
        return self._repo.update_application(application_name, updates)

    def delete_app(
        self,
        application_name: str,
    ) -> bool:
        """Delete an application."""
        result = self._repo.delete_application(application_name)
        if result:
            logger.info(f"Deleted application '{application_name}'")
        return result

    def list_apps(self) -> list[dict[str, Any]]:
        """List all registered applications."""
        return self._repo.list_applications()

    def increment_client_count(self, application_name: str) -> dict[str, Any] | None:
        """Increment client count for an application and return updated metadata."""
        app = self.get_app(application_name)
        if app is None:
            return None

        updated = copy.deepcopy(app)
        updated["client_count"] = updated.get("client_count", 0) + 1
        updated["timestamp"] = time.time()
        self.update_app(application_name, updated)
        return updated
