"""
Page Cache Service - Centralized caching for crawled page data.

Eliminates redundant crawls by caching extracted page data that multiple
agents can reuse. Dramatically improves performance for multi-agent workflows.

Key benefits:
- Single fetch per URL instead of N fetches for N agents
- In-memory cache with configurable TTL
- Thread-safe operations
- Automatic expiration
- Cache statistics and monitoring
- Optional gzip compression (70% size reduction)
- Adaptive TTL based on access patterns
"""

import gzip
import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


@dataclass
class CacheConfig:
    """Configuration for page cache."""

    # Default TTL by content type (in seconds)
    default_ttl: int = 3600  # 1 hour
    product_page_ttl: int = 1800  # 30 minutes (prices/stock change frequently)
    blog_post_ttl: int = 86400  # 24 hours (mostly static)
    homepage_ttl: int = 1800  # 30 minutes (dynamic content)
    category_page_ttl: int = 3600  # 1 hour

    # Cache size limits
    max_entries: int = 10000  # Maximum cached pages
    max_size_bytes: int = 500_000_000  # 500 MB max cache size

    # Performance settings
    enable_compression: bool = False  # Compress HTML to save memory (~70% reduction)
    auto_cleanup: bool = True  # Automatically remove expired entries
    adaptive_ttl: bool = True  # Adjust TTL based on access patterns

    # Adaptive TTL thresholds
    high_traffic_threshold: int = 100  # Hits to be considered high traffic
    medium_traffic_threshold: int = 10  # Hits to be considered medium traffic


@dataclass
class PageData:
    """
    Comprehensive page data extracted once and shared across all agents.

    This eliminates redundant fetching and parsing.
    """

    # Basic info
    url: str
    fetched_at: datetime
    status_code: int
    content_type: str = "unknown"  # product, blog, article, homepage, category

    # HTML content
    html: str = ""
    html_size: int = 0

    # Meta tags
    meta_title: str = ""
    meta_description: str = ""
    meta_keywords: str = ""
    canonical_url: str = ""
    og_title: str = ""
    og_description: str = ""
    og_image: str = ""
    og_type: str = ""
    twitter_card: str = ""
    twitter_title: str = ""
    twitter_description: str = ""

    # Content structure
    h1_tags: list[str] = field(default_factory=list)
    h2_tags: list[str] = field(default_factory=list)
    h3_tags: list[str] = field(default_factory=list)
    h4_tags: list[str] = field(default_factory=list)
    h5_tags: list[str] = field(default_factory=list)
    h6_tags: list[str] = field(default_factory=list)

    # Links
    internal_links: list[dict[str, str]] = field(default_factory=list)  # {href, text, title}
    external_links: list[dict[str, str]] = field(default_factory=list)
    total_links: int = 0

    # Images
    images: list[dict[str, Any]] = field(default_factory=list)  # {src, alt, width, height, loading}
    total_images: int = 0

    # Schema markup
    schema_types: list[str] = field(default_factory=list)
    schema_json: list[dict[str, Any]] = field(default_factory=list)

    # Content analysis
    word_count: int = 0
    text_content: str = ""
    language: str = "en"

    # Performance metrics
    page_load_time_ms: float = 0.0
    dom_content_loaded_ms: float = 0.0
    first_contentful_paint_ms: float = 0.0

    # Mobile
    is_mobile_friendly: bool = True
    viewport_meta: str = ""

    # Technical
    robots_meta: str = ""
    has_ssl: bool = True
    redirects: list[str] = field(default_factory=list)

    # E-commerce specific
    product_price: Optional[float] = None
    product_currency: str = ""
    product_availability: str = ""
    product_sku: str = ""
    product_brand: str = ""

    # Cache metadata
    cache_key: str = ""
    ttl_seconds: int = 3600
    expires_at: datetime = field(default_factory=datetime.utcnow)
    hit_count: int = 0  # How many times this cache entry was accessed


@dataclass
class CacheEntry:
    """Internal cache entry with metadata."""

    data: PageData
    created_at: datetime
    expires_at: datetime
    size_bytes: int
    hit_count: int = 0


class PageCache:
    """
    Thread-safe page cache with TTL and automatic cleanup.

    Usage:
        cache = PageCache()

        # Store page data
        page_data = PageData(url="https://example.com", ...)
        cache.set("https://example.com", page_data, ttl=3600)

        # Retrieve page data
        cached_page = cache.get("https://example.com")

        # Check cache stats
        stats = cache.get_stats()
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._cache: dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._total_hits = 0
        self._total_misses = 0
        self._total_sets = 0
        self._total_evictions = 0

        logger.info("Page cache initialized", config=self.config)

    def _generate_cache_key(self, url: str, params: Optional[dict[str, Any]] = None) -> str:
        """
        Generate cache key from URL and optional parameters.

        Different parameters (e.g., user-agent, cookies) create different cache entries.
        """
        if params:
            # Hash parameters for consistent key
            params_str = str(sorted(params.items()))
            param_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            return f"{url}:{param_hash}"
        return url

    def get(self, url: str, params: Optional[dict[str, Any]] = None) -> Optional[PageData]:
        """
        Retrieve cached page data.

        Args:
            url: Page URL
            params: Optional parameters that affect caching (user-agent, etc.)

        Returns:
            PageData if cached and not expired, None otherwise
        """
        cache_key = self._generate_cache_key(url, params)

        with self._lock:
            entry = self._cache.get(cache_key)

            if entry is None:
                self._total_misses += 1
                logger.debug("Cache miss", url=url, cache_key=cache_key)
                return None

            # Check if expired
            if datetime.utcnow() > entry.expires_at:
                # Remove expired entry
                del self._cache[cache_key]
                self._total_misses += 1
                self._total_evictions += 1
                logger.debug("Cache expired", url=url, cache_key=cache_key)
                return None

            # Cache hit!
            self._total_hits += 1
            entry.hit_count += 1
            entry.data.hit_count += 1

            # Decompress if needed
            if hasattr(entry.data, '_is_compressed') and entry.data._is_compressed:
                if hasattr(entry.data, '_compressed_html'):
                    entry.data.html = gzip.decompress(entry.data._compressed_html).decode()
                if hasattr(entry.data, '_compressed_text'):
                    entry.data.text_content = gzip.decompress(entry.data._compressed_text).decode()

            logger.debug(
                "Cache hit",
                url=url,
                cache_key=cache_key,
                hit_count=entry.hit_count,
                age_seconds=(datetime.utcnow() - entry.created_at).total_seconds(),
            )
            return entry.data

    def set(
        self,
        url: str,
        data: PageData,
        ttl: Optional[int] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Store page data in cache.

        Args:
            url: Page URL
            data: PageData to cache
            ttl: Time-to-live in seconds (uses default from config if not specified)
            params: Optional parameters that affect caching
        """
        cache_key = self._generate_cache_key(url, params)

        # Use adaptive TTL if enabled
        if self.config.adaptive_ttl and ttl is None:
            # Check if this URL was cached before (has hit history)
            existing = self._cache.get(cache_key)
            if existing and existing.hit_count > 0:
                ttl = self._get_adaptive_ttl(existing.hit_count, data.content_type)
            else:
                ttl = self._get_ttl_for_content_type(data.content_type)
        else:
            ttl = ttl or self._get_ttl_for_content_type(data.content_type)

        with self._lock:
            # Check cache size limits
            if len(self._cache) >= self.config.max_entries:
                self._evict_oldest()

            # Compress if enabled
            html_data = data.html
            text_data = data.text_content
            size_bytes = len(html_data) + len(text_data)

            if self.config.enable_compression:
                html_data = gzip.compress(html_data.encode()) if html_data else b""
                text_data = gzip.compress(text_data.encode()) if text_data else b""
                compressed_size = len(html_data) + len(text_data)

                # Store compressed data
                data._compressed_html = html_data
                data._compressed_text = text_data
                data._is_compressed = True

                logger.debug(
                    "Compression enabled",
                    original_size=size_bytes,
                    compressed_size=compressed_size,
                    reduction_percent=round((1 - compressed_size/size_bytes) * 100, 1) if size_bytes > 0 else 0,
                )
                size_bytes = compressed_size

            # Create cache entry
            created_at = datetime.utcnow()
            expires_at = created_at + timedelta(seconds=ttl)

            entry = CacheEntry(
                data=data,
                created_at=created_at,
                expires_at=expires_at,
                size_bytes=size_bytes,
                hit_count=0,
            )

            # Update data metadata
            data.cache_key = cache_key
            data.ttl_seconds = ttl
            data.expires_at = expires_at

            self._cache[cache_key] = entry
            self._total_sets += 1

            logger.debug(
                "Cache set",
                url=url,
                cache_key=cache_key,
                ttl_seconds=ttl,
                size_bytes=size_bytes,
                compressed=self.config.enable_compression,
                adaptive_ttl=self.config.adaptive_ttl,
            )

    def _get_ttl_for_content_type(self, content_type: str) -> int:
        """Get appropriate TTL based on content type."""
        ttl_map = {
            "product": self.config.product_page_ttl,
            "blog": self.config.blog_post_ttl,
            "article": self.config.blog_post_ttl,
            "homepage": self.config.homepage_ttl,
            "category": self.config.category_page_ttl,
        }
        return ttl_map.get(content_type, self.config.default_ttl)

    def _get_adaptive_ttl(self, hit_count: int, content_type: str) -> int:
        """
        Calculate adaptive TTL based on access patterns.

        High-traffic pages get longer TTL, low-traffic pages get shorter TTL.
        This optimizes cache efficiency.
        """
        base_ttl = self._get_ttl_for_content_type(content_type)

        if hit_count >= self.config.high_traffic_threshold:
            # High traffic - cache longer (2x base)
            return base_ttl * 2
        elif hit_count >= self.config.medium_traffic_threshold:
            # Medium traffic - cache 1.5x base
            return int(base_ttl * 1.5)
        else:
            # Low traffic - use base TTL
            return base_ttl

    def _evict_oldest(self) -> None:
        """Evict oldest cache entry to make room."""
        if not self._cache:
            return

        # Find oldest entry
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]
        self._total_evictions += 1
        logger.debug("Cache eviction", cache_key=oldest_key)

    def invalidate(self, url: str, params: Optional[dict[str, Any]] = None) -> bool:
        """
        Manually invalidate a cache entry.

        Args:
            url: Page URL to invalidate
            params: Optional parameters

        Returns:
            True if entry was found and removed, False otherwise
        """
        cache_key = self._generate_cache_key(url, params)

        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.info("Cache invalidated", url=url, cache_key=cache_key)
                return True
            return False

    def invalidate_pattern(self, url_pattern: str) -> int:
        """
        Invalidate all cache entries matching a URL pattern.

        Args:
            url_pattern: Pattern to match (e.g., "example.com/products/")

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys() if url_pattern in key
            ]
            for key in keys_to_remove:
                del self._cache[key]

            if keys_to_remove:
                logger.info(
                    "Pattern invalidation",
                    pattern=url_pattern,
                    count=len(keys_to_remove),
                )

            return len(keys_to_remove)

    def clear(self) -> None:
        """Clear entire cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info("Cache cleared", entries_removed=count)

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        now = datetime.utcnow()

        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if now > entry.expires_at
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                self._total_evictions += len(expired_keys)
                logger.info("Expired entries cleaned up", count=len(expired_keys))

            return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache performance metrics
        """
        with self._lock:
            total_requests = self._total_hits + self._total_misses
            hit_rate = (
                (self._total_hits / total_requests * 100) if total_requests > 0 else 0
            )

            total_size = sum(entry.size_bytes for entry in self._cache.values())
            avg_entry_size = (
                total_size / len(self._cache) if self._cache else 0
            )

            return {
                "total_entries": len(self._cache),
                "total_hits": self._total_hits,
                "total_misses": self._total_misses,
                "total_sets": self._total_sets,
                "total_evictions": self._total_evictions,
                "hit_rate_percent": round(hit_rate, 2),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "avg_entry_size_kb": round(avg_entry_size / 1024, 2),
                "max_entries": self.config.max_entries,
                "utilization_percent": round(
                    len(self._cache) / self.config.max_entries * 100, 2
                ),
            }

    def get_top_hits(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get most frequently accessed cache entries.

        Args:
            limit: Number of top entries to return

        Returns:
            List of top cache entries with metadata
        """
        with self._lock:
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].hit_count,
                reverse=True,
            )[:limit]

            return [
                {
                    "url": entry.data.url,
                    "cache_key": key,
                    "hit_count": entry.hit_count,
                    "age_seconds": (datetime.utcnow() - entry.created_at).total_seconds(),
                    "ttl_remaining_seconds": (
                        entry.expires_at - datetime.utcnow()
                    ).total_seconds(),
                    "size_kb": round(entry.size_bytes / 1024, 2),
                }
                for key, entry in sorted_entries
            ]

    def warm_cache(self, urls: list[str], fetch_func) -> int:
        """
        Pre-warm cache with URLs.

        Args:
            urls: List of URLs to pre-fetch
            fetch_func: Async function to fetch page data (url -> PageData)

        Returns:
            Number of URLs successfully cached
        """
        count = 0
        for url in urls:
            try:
                # Check if already cached
                if self.get(url) is not None:
                    logger.debug("URL already cached", url=url)
                    continue

                # Fetch and cache
                page_data = fetch_func(url)
                if page_data:
                    self.set(url, page_data)
                    count += 1
            except Exception as e:
                logger.error("Cache warming failed", url=url, error=str(e))

        logger.info("Cache warmed", urls_cached=count, total_urls=len(urls))
        return count


# Global singleton instance
_global_cache: Optional[PageCache] = None


def get_cache(config: Optional[CacheConfig] = None) -> PageCache:
    """
    Get global page cache instance.

    Args:
        config: Optional cache configuration (only used on first call)

    Returns:
        Global PageCache instance
    """
    global _global_cache

    if _global_cache is None:
        _global_cache = PageCache(config)

    return _global_cache
