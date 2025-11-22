"""
Workflow Result Caching - Cache entire workflow results for instant reruns.

Perfect for dashboards that refresh hourly or repeated workflow executions.

Impact: 100x faster for repeated workflows with same parameters.
"""

import hashlib
import json
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class WorkflowResultCache:
    """
    Cache workflow results by workflow ID + parameters.

    Usage:
        cache = WorkflowResultCache()

        # First run - execute workflow
        cache_key = cache.get_cache_key(workflow_id, parameters)
        if not cache.get(cache_key):
            result = await run_workflow(...)
            cache.set(cache_key, result, ttl=3600)

        # Second run - instant from cache!
        cached = cache.get(cache_key)  # Returns immediately
    """

    def __init__(self, default_ttl: int = 3600):
        """
        Initialize workflow result cache.

        Args:
            default_ttl: Default TTL in seconds (default: 1 hour)
        """
        self.default_ttl = default_ttl
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = Lock()
        self._stats = {
            "total_requests": 0,
            "hits": 0,
            "misses": 0,
            "sets": 0,
        }

        logger.info("Workflow result cache initialized", default_ttl=default_ttl)

    def get_cache_key(
        self,
        workflow_id: str,
        parameters: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Generate cache key from workflow ID and parameters.

        Args:
            workflow_id: Workflow identifier
            parameters: Workflow parameters

        Returns:
            Cache key (hash of workflow ID + parameters)
        """
        # Normalize parameters for consistent hashing
        params_str = json.dumps(
            parameters or {},
            sort_keys=True,
            default=str,
        )

        # Create hash
        key_str = f"{workflow_id}:{params_str}"
        key_hash = hashlib.md5(key_str.encode()).hexdigest()

        return f"workflow:{workflow_id}:{key_hash[:16]}"

    def get(self, cache_key: str) -> Optional[Any]:
        """
        Get cached workflow result.

        Args:
            cache_key: Cache key from get_cache_key()

        Returns:
            Cached result or None if not found/expired
        """
        self._stats["total_requests"] += 1

        with self._lock:
            entry = self._cache.get(cache_key)

            if not entry:
                self._stats["misses"] += 1
                logger.debug("Workflow cache miss", cache_key=cache_key)
                return None

            # Check expiration
            if datetime.utcnow() > entry["expires_at"]:
                del self._cache[cache_key]
                self._stats["misses"] += 1
                logger.debug("Workflow cache expired", cache_key=cache_key)
                return None

            # Cache hit!
            self._stats["hits"] += 1
            entry["hit_count"] += 1
            entry["last_accessed_at"] = datetime.utcnow()

            age_seconds = (datetime.utcnow() - entry["created_at"]).total_seconds()

            logger.info(
                "Workflow cache hit",
                cache_key=cache_key,
                hit_count=entry["hit_count"],
                age_seconds=round(age_seconds, 1),
                hit_rate=round(self._stats["hits"] / self._stats["total_requests"] * 100, 1),
            )

            return entry["result"]

    def set(
        self,
        cache_key: str,
        result: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Cache workflow result.

        Args:
            cache_key: Cache key from get_cache_key()
            result: Workflow result to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        ttl = ttl or self.default_ttl
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(seconds=ttl)

        with self._lock:
            self._cache[cache_key] = {
                "result": result,
                "created_at": created_at,
                "expires_at": expires_at,
                "last_accessed_at": created_at,
                "hit_count": 0,
                "ttl_seconds": ttl,
            }

            self._stats["sets"] += 1

            logger.info(
                "Workflow result cached",
                cache_key=cache_key,
                ttl_seconds=ttl,
                total_cached=len(self._cache),
            )

    def invalidate(self, cache_key: str) -> bool:
        """
        Invalidate cached workflow result.

        Args:
            cache_key: Cache key to invalidate

        Returns:
            True if entry was found and removed, False otherwise
        """
        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.info("Workflow cache invalidated", cache_key=cache_key)
                return True
            return False

    def invalidate_workflow(
        self,
        workflow_id: str,
    ) -> int:
        """
        Invalidate all cached results for a workflow.

        Args:
            workflow_id: Workflow ID to invalidate

        Returns:
            Number of entries invalidated
        """
        prefix = f"workflow:{workflow_id}:"

        with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys()
                if key.startswith(prefix)
            ]

            for key in keys_to_remove:
                del self._cache[key]

            if keys_to_remove:
                logger.info(
                    "Workflow cache invalidated",
                    workflow_id=workflow_id,
                    count=len(keys_to_remove),
                )

            return len(keys_to_remove)

    def clear(self) -> None:
        """Clear entire cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info("Workflow cache cleared", entries_removed=count)

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        now = datetime.utcnow()

        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry["expires_at"]
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.info(
                    "Expired workflow cache entries cleaned up",
                    count=len(expired_keys),
                )

            return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Cache performance metrics
        """
        with self._lock:
            total = self._stats["total_requests"]
            hits = self._stats["hits"]

            return {
                "total_entries": len(self._cache),
                "total_requests": total,
                "hits": hits,
                "misses": self._stats["misses"],
                "sets": self._stats["sets"],
                "hit_rate_percent": round(hits / total * 100, 1) if total > 0 else 0,
            }

    def get_top_hits(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get most frequently cached workflows.

        Args:
            limit: Number of top entries to return

        Returns:
            List of top cached workflows
        """
        with self._lock:
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1]["hit_count"],
                reverse=True,
            )[:limit]

            return [
                {
                    "cache_key": key,
                    "hit_count": entry["hit_count"],
                    "age_seconds": (datetime.utcnow() - entry["created_at"]).total_seconds(),
                    "ttl_remaining_seconds": (
                        entry["expires_at"] - datetime.utcnow()
                    ).total_seconds(),
                }
                for key, entry in sorted_entries
            ]


# Global singleton
_global_workflow_cache: Optional[WorkflowResultCache] = None


def get_workflow_cache() -> WorkflowResultCache:
    """
    Get global workflow result cache instance.

    Returns:
        Global WorkflowResultCache instance
    """
    global _global_workflow_cache

    if _global_workflow_cache is None:
        _global_workflow_cache = WorkflowResultCache(default_ttl=3600)

    return _global_workflow_cache
