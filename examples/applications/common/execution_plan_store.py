"""ExecutionPlan storage backed by Redis.

Provides CRUD operations for ExecutionPlans with pub/sub notifications
for real-time propagation to multiple orchestrator replicas.
"""
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

PLAN_KEY_PREFIX = "rohe:plan:"
PLAN_UPDATES_CHANNEL = "rohe:plan:updates"


class ExecutionPlanStore:
    """Redis-backed store for ExecutionPlans.

    Keys: rohe:plan:{pipeline_id} -> JSON-serialized ExecutionPlan
    Pub/Sub: rohe:plan:updates -> {"pipeline_id": "...", "version": N}
    """

    def __init__(self, redis_url: str = "redis://localhost:6379") -> None:
        self._redis_url = redis_url
        self._client: Any = None  # RedisCache, lazy-initialized

    def _ensure_connected(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from rohe.repositories.redis import RedisCache
            self._client = RedisCache(url=self._redis_url)
            logger.info(f"ExecutionPlanStore connected to Redis at {self._redis_url}")
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}")
            self._client = None
        return self._client

    def get_plan(self, pipeline_id: str) -> dict[str, Any] | None:
        """Load an ExecutionPlan from Redis by pipeline_id."""
        client = self._ensure_connected()
        if client is None:
            return None
        return client.get(f"{PLAN_KEY_PREFIX}{pipeline_id}")

    def save_plan(self, plan_dict: dict[str, Any]) -> None:
        """Save an ExecutionPlan to Redis and publish an update notification."""
        client = self._ensure_connected()
        if client is None:
            logger.warning("Cannot save plan: Redis unavailable")
            return

        pipeline_id = plan_dict["pipeline_id"]
        version = plan_dict.get("version", 0)
        client.set(f"{PLAN_KEY_PREFIX}{pipeline_id}", plan_dict)
        client.publish(PLAN_UPDATES_CHANNEL, {
            "pipeline_id": pipeline_id,
            "version": version,
        })
        logger.info(f"Saved plan '{pipeline_id}' v{version} to Redis")

    def delete_plan(self, pipeline_id: str) -> bool:
        """Delete an ExecutionPlan from Redis."""
        client = self._ensure_connected()
        if client is None:
            return False
        return client.delete(f"{PLAN_KEY_PREFIX}{pipeline_id}")

    def list_plans(self) -> list[str]:
        """List all stored pipeline IDs."""
        client = self._ensure_connected()
        if client is None:
            return []
        keys = client.keys(f"{PLAN_KEY_PREFIX}*")
        prefix_len = len(PLAN_KEY_PREFIX)
        return [k[prefix_len:] for k in keys]

    def close(self) -> None:
        """Close the Redis connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
