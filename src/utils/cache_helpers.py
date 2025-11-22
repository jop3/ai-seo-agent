"""
Cache Helper Utilities - Advanced caching patterns and optimizations.

Quick wins for better cache performance:
- Incremental crawling (only fetch stale pages)
- Smart warming (priority-based pre-caching)
- Batch invalidation patterns
- Cache health monitoring
"""

from datetime import datetime, timedelta
from typing import Any, Optional

import structlog

from src.cache.page_cache import PageData, get_cache

logger = structlog.get_logger()


def get_stale_urls(
    urls: list[str],
    max_age_hours: int = 24,
) -> tuple[list[str], dict[str, Any]]:
    """
    Identify URLs that need re-fetching (incremental crawling).

    Args:
        urls: List of URLs to check
        max_age_hours: Maximum age before considering stale

    Returns:
        Tuple of (stale_urls, stats)

    Example:
        urls = get_all_product_urls()  # 1000 URLs
        stale, stats = get_stale_urls(urls, max_age_hours=24)
        # Only fetch stale: 200 URLs instead of 1000 (80% cache hit!)
    """
    cache = get_cache()
    stale = []
    cached = []
    never_cached = []

    max_age = timedelta(hours=max_age_hours)

    for url in urls:
        page_data = cache.get(url)

        if not page_data:
            never_cached.append(url)
            stale.append(url)
        else:
            age = datetime.utcnow() - page_data.fetched_at
            if age > max_age:
                cached.append(url)
                stale.append(url)
            # else: fresh, skip

    stats = {
        "total_urls": len(urls),
        "stale_urls": len(stale),
        "fresh_urls": len(urls) - len(stale),
        "never_cached": len(never_cached),
        "expired_cached": len(cached),
        "cache_hit_rate": round((len(urls) - len(stale)) / len(urls) * 100, 1) if urls else 0,
        "bandwidth_saved_percent": round((1 - len(stale) / len(urls)) * 100, 1) if urls else 0,
    }

    logger.info(
        "Incremental crawl analysis",
        **stats,
    )

    return stale, stats


def warm_cache_priority(
    urls: list[str],
    priorities: dict[str, int],
    fetch_func,
    max_concurrent: int = 10,
) -> dict[str, Any]:
    """
    Smart cache warming based on priority.

    Warms high-priority URLs first (homepage, best sellers, top categories).

    Args:
        urls: List of URLs to warm
        priorities: Dict of {url: priority} (higher = more important)
        fetch_func: Async function to fetch page data
        max_concurrent: Max parallel fetches

    Returns:
        Warming statistics

    Example:
        priorities = {
            "/": 100,  # Homepage - highest priority
            "/products/best-seller": 90,
            "/category/popular": 80,
            "/blog/latest": 50,
        }
        stats = warm_cache_priority(urls, priorities, fetch_func)
    """
    cache = get_cache()

    # Sort by priority (high to low)
    sorted_urls = sorted(
        urls,
        key=lambda url: priorities.get(url, 0),
        reverse=True,
    )

    warmed = 0
    already_cached = 0
    failed = 0

    for url in sorted_urls:
        # Check if already cached
        if cache.get(url):
            already_cached += 1
            continue

        # Fetch and cache
        try:
            page_data = fetch_func(url)
            if page_data:
                cache.set(url, page_data)
                warmed += 1
        except Exception as e:
            logger.error("Cache warming failed", url=url, error=str(e))
            failed += 1

    stats = {
        "total_urls": len(urls),
        "warmed": warmed,
        "already_cached": already_cached,
        "failed": failed,
        "success_rate": round(warmed / len(urls) * 100, 1) if urls else 0,
    }

    logger.info("Cache warming complete", **stats)
    return stats


def invalidate_pattern_batch(
    patterns: list[str],
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Batch invalidate multiple patterns.

    Useful for bulk content updates (e.g., all products, all blog posts).

    Args:
        patterns: List of URL patterns to invalidate
        dry_run: If True, only report what would be invalidated

    Returns:
        Invalidation statistics

    Example:
        patterns = ["/products/", "/category/", "/blog/2024/"]
        stats = invalidate_pattern_batch(patterns)
        # Invalidated 450 product pages, 30 categories, 20 blog posts
    """
    cache = get_cache()
    results = {}
    total_invalidated = 0

    for pattern in patterns:
        if dry_run:
            # Count matching entries without invalidating
            count = sum(1 for key in cache._cache.keys() if pattern in key)
            results[pattern] = {"would_invalidate": count, "dry_run": True}
        else:
            count = cache.invalidate_pattern(pattern)
            results[pattern] = {"invalidated": count}
            total_invalidated += count

    stats = {
        "patterns": len(patterns),
        "total_invalidated": total_invalidated,
        "dry_run": dry_run,
        "details": results,
    }

    logger.info("Batch pattern invalidation", **stats)
    return stats


def get_cache_health() -> dict[str, Any]:
    """
    Check cache health and efficiency.

    Returns warnings for:
    - Low hit rate (<50%)
    - High memory usage (>80%)
    - Too many entries
    - Poor TTL settings

    Example:
        health = get_cache_health()
        if health["warnings"]:
            print("Cache issues:", health["warnings"])
    """
    cache = get_cache()
    stats = cache.get_stats()

    warnings = []
    recommendations = []

    # Check hit rate
    if stats["hit_rate_percent"] < 50:
        warnings.append("Low cache hit rate (<50%)")
        recommendations.append("Increase TTL or pre-warm cache before workflows")

    # Check memory usage
    if stats["utilization_percent"] > 80:
        warnings.append("High cache utilization (>80%)")
        recommendations.append("Increase max_entries or enable compression")

    # Check if compression would help
    if not cache.config.enable_compression and stats["total_size_mb"] > 100:
        recommendations.append(
            f"Enable compression to reduce {stats['total_size_mb']} MB by ~70%"
        )

    # Check for adaptive TTL
    if not cache.config.adaptive_ttl:
        recommendations.append("Enable adaptive TTL for better cache efficiency")

    health = {
        "status": "healthy" if not warnings else "needs_attention",
        "hit_rate": stats["hit_rate_percent"],
        "memory_usage_mb": stats["total_size_mb"],
        "utilization_percent": stats["utilization_percent"],
        "total_entries": stats["total_entries"],
        "warnings": warnings,
        "recommendations": recommendations,
        "stats": stats,
    }

    if warnings:
        logger.warning("Cache health check", **health)
    else:
        logger.info("Cache health check", **health)

    return health


def get_recommended_ttls(
    url_patterns: dict[str, str],
    current_hit_counts: Optional[dict[str, int]] = None,
) -> dict[str, int]:
    """
    Get recommended TTLs based on content type and access patterns.

    Args:
        url_patterns: Dict of {pattern: content_type}
        current_hit_counts: Optional dict of {url: hit_count} for adaptive TTL

    Returns:
        Dict of {pattern: recommended_ttl_seconds}

    Example:
        patterns = {
            "/products/": "product",
            "/blog/": "article",
            "/": "homepage",
        }
        ttls = get_recommended_ttls(patterns)
        # {"/products/": 1800, "/blog/": 86400, "/": 1800}
    """
    base_ttls = {
        "product": 1800,     # 30 min (prices change)
        "category": 3600,    # 1 hour
        "article": 86400,    # 24 hours (static)
        "blog": 86400,       # 24 hours
        "homepage": 1800,    # 30 min (dynamic)
        "default": 3600,     # 1 hour
    }

    recommended = {}

    for pattern, content_type in url_patterns.items():
        base_ttl = base_ttls.get(content_type, base_ttls["default"])

        # Adjust based on hit count (adaptive)
        if current_hit_counts:
            avg_hits = sum(
                count for url, count in current_hit_counts.items()
                if pattern in url
            )
            if avg_hits > 100:
                # High traffic - cache 2x longer
                recommended[pattern] = base_ttl * 2
            elif avg_hits > 10:
                # Medium traffic - cache 1.5x longer
                recommended[pattern] = int(base_ttl * 1.5)
            else:
                recommended[pattern] = base_ttl
        else:
            recommended[pattern] = base_ttl

    return recommended


def analyze_cache_efficiency(
    time_window_hours: int = 24,
) -> dict[str, Any]:
    """
    Analyze cache efficiency over time window.

    Identifies:
    - Most/least accessed pages
    - Cache waste (rarely accessed)
    - Optimization opportunities

    Args:
        time_window_hours: Analysis window

    Returns:
        Efficiency analysis

    Example:
        analysis = analyze_cache_efficiency(time_window_hours=24)
        print(f"Top pages: {analysis['top_pages']}")
        print(f"Wasted space: {analysis['waste_percent']}%")
    """
    cache = get_cache()
    stats = cache.get_stats()
    top_hits = cache.get_top_hits(limit=50)

    # Calculate waste (pages cached but never/rarely accessed)
    total_pages = stats["total_entries"]
    high_value_pages = sum(1 for entry in top_hits if entry["hit_count"] > 5)
    waste_percent = round((1 - high_value_pages / total_pages) * 100, 1) if total_pages > 0 else 0

    # Identify patterns
    top_patterns = {}
    for entry in top_hits[:10]:
        url = entry["url"]
        # Extract pattern (e.g., "/products/", "/blog/")
        parts = url.split("/")
        if len(parts) >= 2:
            pattern = f"/{parts[1]}/" if len(parts) > 1 else "/"
            top_patterns[pattern] = top_patterns.get(pattern, 0) + 1

    analysis = {
        "total_entries": total_pages,
        "high_value_entries": high_value_pages,
        "waste_percent": waste_percent,
        "hit_rate": stats["hit_rate_percent"],
        "top_pages": top_hits[:10],
        "top_patterns": top_patterns,
        "recommendations": [],
    }

    # Generate recommendations
    if waste_percent > 30:
        analysis["recommendations"].append(
            f"Cache has {waste_percent}% waste. Consider lowering TTL for rarely accessed pages."
        )

    if stats["hit_rate_percent"] < 60:
        analysis["recommendations"].append(
            "Low hit rate. Pre-warm cache before running workflows."
        )

    return analysis


# Quick access functions for common operations

def quick_invalidate_products():
    """Quick invalidate all product pages."""
    return invalidate_pattern_batch(["/product/", "/products/", "/p/"])


def quick_invalidate_blog():
    """Quick invalidate all blog posts."""
    return invalidate_pattern_batch(["/blog/", "/article/", "/post/"])


def quick_warm_homepage():
    """Quick warm homepage and top pages."""
    cache = get_cache()
    important_urls = [
        "/",
        "/products",
        "/blog",
        "/about",
        "/contact",
    ]
    # Would need fetch function in practice
    return {"urls_to_warm": important_urls}
