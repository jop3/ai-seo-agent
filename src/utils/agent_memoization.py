"""
Agent Result Memoization - Cache individual agent analysis results.

Prevents duplicate agent work when same agent analyzes same URL/params multiple times.

Impact: Eliminates redundant AI analysis, saves tokens and time.

Example:
    Technical SEO agent analyzes example.com 3x → only runs once, cached 2x
"""

import hashlib
import json
from datetime import datetime, timedelta
from functools import wraps
from threading import Lock
from typing import Any, Callable, Optional

import structlog

logger = structlog.get_logger()


class AgentMemoCache:
    """
    Memoization cache for agent results.

    Caches by (agent_type, url, task_type, parameters).
    """

    def __init__(self, default_ttl: int = 3600):
        """
        Initialize agent memoization cache.

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

        logger.info("Agent memoization cache initialized", default_ttl=default_ttl)

    def _generate_key(
        self,
        agent_type: str,
        task_type: str,
        url: Optional[str] = None,
        parameters: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Generate cache key from agent execution context.

        Args:
            agent_type: Agent type (e.g., "technical_seo")
            task_type: Task type (e.g., "full_audit")
            url: Optional URL being analyzed
            parameters: Optional task parameters

        Returns:
            Cache key
        """
        # Normalize parameters
        params_str = json.dumps(
            parameters or {},
            sort_keys=True,
            default=str,
        )

        # Create key string
        key_parts = [agent_type, task_type]
        if url:
            key_parts.append(url)
        key_parts.append(params_str)

        key_str = ":".join(key_parts)

        # Hash for consistent key
        key_hash = hashlib.md5(key_str.encode()).hexdigest()

        return f"agent:{agent_type}:{task_type}:{key_hash[:16]}"

    def get(
        self,
        agent_type: str,
        task_type: str,
        url: Optional[str] = None,
        parameters: Optional[dict[str, Any]] = None,
    ) -> Optional[Any]:
        """
        Get cached agent result.

        Args:
            agent_type: Agent type
            task_type: Task type
            url: Optional URL
            parameters: Optional parameters

        Returns:
            Cached result or None if not found/expired
        """
        cache_key = self._generate_key(agent_type, task_type, url, parameters)
        self._stats["total_requests"] += 1

        with self._lock:
            entry = self._cache.get(cache_key)

            if not entry:
                self._stats["misses"] += 1
                logger.debug(
                    "Agent memo cache miss",
                    agent_type=agent_type,
                    task_type=task_type,
                    url=url,
                )
                return None

            # Check expiration
            if datetime.utcnow() > entry["expires_at"]:
                del self._cache[cache_key]
                self._stats["misses"] += 1
                logger.debug(
                    "Agent memo cache expired",
                    agent_type=agent_type,
                    task_type=task_type,
                )
                return None

            # Cache hit!
            self._stats["hits"] += 1
            entry["hit_count"] += 1
            entry["last_accessed_at"] = datetime.utcnow()

            logger.info(
                "Agent memo cache hit",
                agent_type=agent_type,
                task_type=task_type,
                url=url,
                hit_count=entry["hit_count"],
                age_seconds=(datetime.utcnow() - entry["created_at"]).total_seconds(),
                hit_rate=round(self._stats["hits"] / self._stats["total_requests"] * 100, 1),
            )

            return entry["result"]

    def set(
        self,
        agent_type: str,
        task_type: str,
        result: Any,
        url: Optional[str] = None,
        parameters: Optional[dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Cache agent result.

        Args:
            agent_type: Agent type
            task_type: Task type
            result: Agent result to cache
            url: Optional URL
            parameters: Optional parameters
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        cache_key = self._generate_key(agent_type, task_type, url, parameters)
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
                "agent_type": agent_type,
                "task_type": task_type,
                "url": url,
            }

            self._stats["sets"] += 1

            logger.debug(
                "Agent result cached",
                agent_type=agent_type,
                task_type=task_type,
                url=url,
                ttl_seconds=ttl,
            )

    def invalidate_agent(self, agent_type: str) -> int:
        """
        Invalidate all cached results for an agent type.

        Args:
            agent_type: Agent type to invalidate

        Returns:
            Number of entries invalidated
        """
        prefix = f"agent:{agent_type}:"

        with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys()
                if key.startswith(prefix)
            ]

            for key in keys_to_remove:
                del self._cache[key]

            if keys_to_remove:
                logger.info(
                    "Agent memo cache invalidated",
                    agent_type=agent_type,
                    count=len(keys_to_remove),
                )

            return len(keys_to_remove)

    def invalidate_url(self, url: str) -> int:
        """
        Invalidate all cached results for a URL.

        Args:
            url: URL to invalidate

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if entry.get("url") == url
            ]

            for key in keys_to_remove:
                del self._cache[key]

            if keys_to_remove:
                logger.info(
                    "Agent memo cache invalidated for URL",
                    url=url,
                    count=len(keys_to_remove),
                )

            return len(keys_to_remove)

    def clear(self) -> None:
        """Clear entire cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info("Agent memo cache cleared", entries_removed=count)

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
                    "Expired agent memo entries cleaned up",
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

            # Count by agent type
            by_agent = {}
            for entry in self._cache.values():
                agent_type = entry.get("agent_type", "unknown")
                by_agent[agent_type] = by_agent.get(agent_type, 0) + 1

            return {
                "total_entries": len(self._cache),
                "total_requests": total,
                "hits": hits,
                "misses": self._stats["misses"],
                "sets": self._stats["sets"],
                "hit_rate_percent": round(hits / total * 100, 1) if total > 0 else 0,
                "entries_by_agent": by_agent,
            }


# Global singleton
_global_agent_memo: Optional[AgentMemoCache] = None


def get_agent_memo_cache() -> AgentMemoCache:
    """
    Get global agent memoization cache instance.

    Returns:
        Global AgentMemoCache instance
    """
    global _global_agent_memo

    if _global_agent_memo is None:
        _global_agent_memo = AgentMemoCache(default_ttl=3600)

    return _global_agent_memo


def memoize_agent_result(ttl: int = 3600):
    """
    Decorator to automatically memoize agent results.

    Usage:
        class TechnicalSEOAgent(BaseAgent):
            @memoize_agent_result(ttl=3600)
            async def execute(self, task: AgentTask) -> AgentResult:
                # This result will be cached!
                ...

    Args:
        ttl: Time-to-live in seconds

    Returns:
        Decorated function with memoization
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, task, *args, **kwargs):
            cache = get_agent_memo_cache()

            # Try to get cached result
            cached = cache.get(
                agent_type=str(self.agent_type),
                task_type=task.task_type,
                url=task.parameters.get("url"),
                parameters=task.parameters,
            )

            if cached is not None:
                return cached

            # Not cached - execute
            result = await func(self, task, *args, **kwargs)

            # Cache result
            cache.set(
                agent_type=str(self.agent_type),
                task_type=task.task_type,
                result=result,
                url=task.parameters.get("url"),
                parameters=task.parameters,
                ttl=ttl,
            )

            return result

        return wrapper
    return decorator
