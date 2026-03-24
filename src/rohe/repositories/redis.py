from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import redis
except ImportError:
    redis = None  # type: ignore[assignment,unused-ignore]


class RedisCache:
    """Redis-based cache for hot data: node state, service profiles, CDM evaluations.

    Provides get/set with TTL and pub/sub for inter-service events.
    """

    def __init__(self, url: str = "redis://localhost:6379") -> None:
        if redis is None:
            raise ImportError("redis package is required: uv add redis")
        self._client: redis.Redis[str] = redis.from_url(url, decode_responses=True)
        self._client.ping()
        logger.info(f"Connected to Redis at {url}")

    def get(self, key: str) -> dict[str, Any] | None:
        """Get a JSON value by key."""
        raw = self._client.get(key)
        if raw is None:
            return None
        return json.loads(raw)  # type: ignore[no-any-return]

    def set(
        self, key: str, value: dict[str, Any], ttl_seconds: int | None = None
    ) -> None:
        """Set a JSON value with optional TTL."""
        serialized = json.dumps(value)
        if ttl_seconds:
            self._client.setex(key, ttl_seconds, serialized)
        else:
            self._client.set(key, serialized)

    def delete(self, key: str) -> bool:
        """Delete a key."""
        return bool(self._client.delete(key) > 0)

    def keys(self, pattern: str = "*") -> list[str]:
        """List keys matching pattern."""
        return list(self._client.keys(pattern))

    def publish(self, channel: str, message: dict[str, Any]) -> int:
        """Publish a JSON message to a pub/sub channel."""
        return int(self._client.publish(channel, json.dumps(message)))

    def subscribe(self, channel: str) -> redis.client.PubSub:
        """Subscribe to a pub/sub channel. Returns a PubSub object for iteration."""
        pubsub = self._client.pubsub()
        pubsub.subscribe(channel)
        return pubsub

    def close(self) -> None:
        """Close the Redis connection."""
        self._client.close()
