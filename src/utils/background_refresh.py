"""
Background Cache Refresh - Proactively refresh cache before expiration.

Prevents cache misses for popular pages by refreshing them in the background
before they expire.

Impact: Users never see cache misses for popular content.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

import structlog

from src.cache.page_cache import get_cache

logger = structlog.get_logger()


class BackgroundRefresher:
    """
    Background cache refresh manager.

    Monitors cache entries and refreshes popular ones before expiration.

    Usage:
        refresher = BackgroundRefresher(
            fetch_func=fetch_page,
            refresh_threshold_seconds=600  # Refresh if expires in <10 min
        )

        # Start background refresh loop
        await refresher.start()

        # Stop when done
        await refresher.stop()
    """

    def __init__(
        self,
        fetch_func: Callable,
        refresh_threshold_seconds: int = 600,
        check_interval_seconds: int = 60,
        min_hit_count: int = 3,
    ):
        """
        Initialize background refresher.

        Args:
            fetch_func: Async function to fetch page data (url -> PageData)
            refresh_threshold_seconds: Refresh if TTL < this value (default: 10 min)
            check_interval_seconds: How often to check for refresh (default: 60s)
            min_hit_count: Minimum hits to qualify for refresh (default: 3)
        """
        self.fetch_func = fetch_func
        self.refresh_threshold = timedelta(seconds=refresh_threshold_seconds)
        self.check_interval = check_interval_seconds
        self.min_hit_count = min_hit_count

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._cache = get_cache()

        self._stats = {
            "total_checks": 0,
            "background_refreshes": 0,
            "refresh_errors": 0,
        }

        logger.info(
            "Background refresher initialized",
            refresh_threshold_seconds=refresh_threshold_seconds,
            check_interval_seconds=check_interval_seconds,
            min_hit_count=min_hit_count,
        )

    async def start(self) -> None:
        """Start background refresh loop."""
        if self._running:
            logger.warning("Background refresher already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._refresh_loop())
        logger.info("Background refresher started")

    async def stop(self) -> None:
        """Stop background refresh loop."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Background refresher stopped")

    async def _refresh_loop(self) -> None:
        """Main refresh loop."""
        while self._running:
            try:
                await self._check_and_refresh()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Error in background refresh loop",
                    error=str(e),
                )
                await asyncio.sleep(self.check_interval)

    async def _check_and_refresh(self) -> None:
        """Check cache and refresh entries that need it."""
        self._stats["total_checks"] += 1

        now = datetime.utcnow()
        candidates = []

        # Find entries that need refresh
        with self._cache._lock:
            for cache_key, entry in self._cache._cache.items():
                # Check if expires soon
                time_to_expiry = entry.expires_at - now

                if time_to_expiry < self.refresh_threshold:
                    # Check if popular enough
                    if entry.hit_count >= self.min_hit_count:
                        candidates.append({
                            "url": entry.data.url,
                            "cache_key": cache_key,
                            "hit_count": entry.hit_count,
                            "expires_in_seconds": time_to_expiry.total_seconds(),
                        })

        if not candidates:
            return

        # Sort by hit count (refresh most popular first)
        candidates.sort(key=lambda x: x["hit_count"], reverse=True)

        logger.info(
            "Background refresh candidates found",
            count=len(candidates),
            top_urls=[c["url"] for c in candidates[:5]],
        )

        # Refresh in background (don't block)
        for candidate in candidates:
            asyncio.create_task(self._refresh_entry(candidate))

    async def _refresh_entry(self, candidate: dict[str, Any]) -> None:
        """Refresh a single cache entry."""
        url = candidate["url"]

        try:
            # Fetch fresh data
            page_data = await self.fetch_func(url)

            if page_data:
                # Update cache
                self._cache.set(url, page_data)
                self._stats["background_refreshes"] += 1

                logger.info(
                    "Background refresh successful",
                    url=url,
                    hit_count=candidate["hit_count"],
                    was_expiring_in_seconds=round(candidate["expires_in_seconds"], 1),
                )
        except Exception as e:
            self._stats["refresh_errors"] += 1
            logger.error(
                "Background refresh failed",
                url=url,
                error=str(e),
            )

    def get_stats(self) -> dict[str, Any]:
        """Get refresh statistics."""
        return {
            "total_checks": self._stats["total_checks"],
            "background_refreshes": self._stats["background_refreshes"],
            "refresh_errors": self._stats["refresh_errors"],
            "is_running": self._running,
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = {
            "total_checks": 0,
            "background_refreshes": 0,
            "refresh_errors": 0,
        }


# Global refresher instance
_global_refresher: Optional[BackgroundRefresher] = None


async def start_background_refresh(
    fetch_func: Callable,
    refresh_threshold_seconds: int = 600,
    check_interval_seconds: int = 60,
    min_hit_count: int = 3,
) -> BackgroundRefresher:
    """
    Start global background refresher.

    Args:
        fetch_func: Function to fetch page data
        refresh_threshold_seconds: Refresh if expires in <X seconds
        check_interval_seconds: Check interval
        min_hit_count: Minimum hits to refresh

    Returns:
        BackgroundRefresher instance
    """
    global _global_refresher

    if _global_refresher and _global_refresher._running:
        logger.warning("Background refresher already running")
        return _global_refresher

    _global_refresher = BackgroundRefresher(
        fetch_func=fetch_func,
        refresh_threshold_seconds=refresh_threshold_seconds,
        check_interval_seconds=check_interval_seconds,
        min_hit_count=min_hit_count,
    )

    await _global_refresher.start()
    return _global_refresher


async def stop_background_refresh() -> None:
    """Stop global background refresher."""
    global _global_refresher

    if _global_refresher:
        await _global_refresher.stop()


def get_background_refresher() -> Optional[BackgroundRefresher]:
    """Get global background refresher instance."""
    return _global_refresher
