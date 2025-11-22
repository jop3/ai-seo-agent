"""
Sitemap-Based Auto-Preload - Pre-warm cache from sitemap on startup.

Automatically fetches and caches top URLs from sitemap.xml to ensure
first user requests hit warm cache.

Impact: First user requests are instant (cache already warm).
"""

import asyncio
import xml.etree.ElementTree as ET
from typing import Any, Callable, Optional
from urllib.parse import urljoin

import structlog

from src.cache.page_cache import get_cache

logger = structlog.get_logger()


async def fetch_sitemap(
    sitemap_url: str,
    http_client: Optional[Any] = None,
) -> list[dict[str, Any]]:
    """
    Fetch and parse sitemap XML.

    Args:
        sitemap_url: URL to sitemap.xml
        http_client: Optional HTTP client (must have .get(url) method)

    Returns:
        List of URL entries with metadata

    Example:
        urls = await fetch_sitemap("https://example.com/sitemap.xml")
        # Returns: [
        #     {"loc": "https://example.com/", "priority": "1.0", "changefreq": "daily"},
        #     {"loc": "https://example.com/products", "priority": "0.8"},
        #     ...
        # ]
    """
    try:
        # Fetch sitemap
        if http_client:
            status, content = await http_client.get(sitemap_url)
            if status != 200:
                logger.error(
                    "Failed to fetch sitemap",
                    url=sitemap_url,
                    status=status,
                )
                return []
        else:
            # Use httpx as fallback
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(sitemap_url)
                content = response.text

        # Parse XML
        root = ET.fromstring(content)

        # Handle namespace
        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        urls = []
        for url in root.findall(".//ns:url", namespace):
            loc = url.find("ns:loc", namespace)
            priority = url.find("ns:priority", namespace)
            changefreq = url.find("ns:changefreq", namespace)
            lastmod = url.find("ns:lastmod", namespace)

            if loc is not None and loc.text:
                entry = {"loc": loc.text}

                if priority is not None and priority.text:
                    entry["priority"] = float(priority.text)

                if changefreq is not None and changefreq.text:
                    entry["changefreq"] = changefreq.text

                if lastmod is not None and lastmod.text:
                    entry["lastmod"] = lastmod.text

                urls.append(entry)

        logger.info(
            "Sitemap parsed successfully",
            url=sitemap_url,
            total_urls=len(urls),
        )

        return urls

    except Exception as e:
        logger.error(
            "Failed to parse sitemap",
            url=sitemap_url,
            error=str(e),
        )
        return []


async def preload_from_sitemap(
    sitemap_url: str,
    fetch_func: Callable,
    max_urls: int = 100,
    priority_threshold: float = 0.5,
    concurrency: int = 10,
    http_client: Optional[Any] = None,
) -> dict[str, Any]:
    """
    Pre-warm cache from sitemap.

    Args:
        sitemap_url: URL to sitemap.xml
        fetch_func: Async function to fetch page data (url -> PageData)
        max_urls: Maximum URLs to preload (default: 100)
        priority_threshold: Only preload URLs with priority >= this (default: 0.5)
        concurrency: Max concurrent fetches (default: 10)
        http_client: Optional HTTP client

    Returns:
        Dict with preload statistics

    Example:
        stats = await preload_from_sitemap(
            sitemap_url="https://example.com/sitemap.xml",
            fetch_func=fetch_page,
            max_urls=100,
            priority_threshold=0.7
        )

        # Pre-warms cache with top 100 URLs (priority >= 0.7)
        # First user requests = instant cache hits!
    """
    logger.info(
        "Starting sitemap preload",
        sitemap_url=sitemap_url,
        max_urls=max_urls,
        priority_threshold=priority_threshold,
    )

    # Fetch sitemap
    urls = await fetch_sitemap(sitemap_url, http_client)

    if not urls:
        return {
            "success": False,
            "error": "Failed to fetch or parse sitemap",
            "preloaded": 0,
        }

    # Filter by priority
    filtered_urls = [
        url for url in urls
        if url.get("priority", 0.5) >= priority_threshold
    ]

    # Sort by priority (high to low)
    filtered_urls.sort(key=lambda x: x.get("priority", 0.5), reverse=True)

    # Limit to max_urls
    urls_to_preload = filtered_urls[:max_urls]

    logger.info(
        "Sitemap filtered",
        total_urls=len(urls),
        filtered_urls=len(filtered_urls),
        urls_to_preload=len(urls_to_preload),
    )

    # Preload URLs with concurrency control
    cache = get_cache()
    semaphore = asyncio.Semaphore(concurrency)

    async def preload_url(url_entry: dict[str, Any]) -> bool:
        url = url_entry["loc"]

        async with semaphore:
            try:
                # Check if already cached
                if cache.get(url):
                    logger.debug("URL already cached, skipping", url=url)
                    return False

                # Fetch and cache
                page_data = await fetch_func(url)
                if page_data:
                    cache.set(url, page_data)
                    logger.debug(
                        "URL preloaded",
                        url=url,
                        priority=url_entry.get("priority"),
                    )
                    return True

                return False

            except Exception as e:
                logger.error("Preload failed", url=url, error=str(e))
                return False

    # Preload all URLs in parallel
    results = await asyncio.gather(
        *[preload_url(url_entry) for url_entry in urls_to_preload],
        return_exceptions=True,
    )

    # Count successes
    preloaded = sum(1 for r in results if r is True)
    already_cached = sum(1 for r in results if r is False)
    errors = sum(1 for r in results if isinstance(r, Exception))

    stats = {
        "success": True,
        "sitemap_url": sitemap_url,
        "total_urls_in_sitemap": len(urls),
        "urls_to_preload": len(urls_to_preload),
        "preloaded": preloaded,
        "already_cached": already_cached,
        "errors": errors,
        "priority_threshold": priority_threshold,
    }

    logger.info("Sitemap preload complete", **stats)
    return stats


async def auto_preload_on_startup(
    domain: str,
    fetch_func: Callable,
    max_urls: int = 100,
    sitemap_paths: Optional[list[str]] = None,
    http_client: Optional[Any] = None,
) -> dict[str, Any]:
    """
    Automatically discover and preload from sitemaps on startup.

    Args:
        domain: Domain to preload (e.g., "https://example.com")
        fetch_func: Function to fetch page data
        max_urls: Max URLs to preload
        sitemap_paths: Optional custom sitemap paths (default: tries common paths)
        http_client: Optional HTTP client

    Returns:
        Preload statistics

    Example:
        # On app startup
        stats = await auto_preload_on_startup(
            domain="https://example.com",
            fetch_func=fetch_page,
            max_urls=100
        )

        # Automatically tries:
        # - https://example.com/sitemap.xml
        # - https://example.com/sitemap_index.xml
        # - https://example.com/sitemap1.xml
    """
    if sitemap_paths is None:
        sitemap_paths = [
            "/sitemap.xml",
            "/sitemap_index.xml",
            "/sitemap1.xml",
            "/sitemap-index.xml",
        ]

    logger.info(
        "Auto-preload on startup",
        domain=domain,
        sitemap_paths=sitemap_paths,
    )

    for path in sitemap_paths:
        sitemap_url = urljoin(domain, path)

        try:
            stats = await preload_from_sitemap(
                sitemap_url=sitemap_url,
                fetch_func=fetch_func,
                max_urls=max_urls,
                http_client=http_client,
            )

            if stats.get("success") and stats.get("preloaded", 0) > 0:
                logger.info(
                    "Auto-preload successful",
                    sitemap_url=sitemap_url,
                    preloaded=stats["preloaded"],
                )
                return stats

        except Exception as e:
            logger.debug(
                "Sitemap not found or failed",
                sitemap_url=sitemap_url,
                error=str(e),
            )
            continue

    logger.warning("No sitemaps found for auto-preload", domain=domain)
    return {
        "success": False,
        "error": "No sitemaps found",
        "preloaded": 0,
    }
