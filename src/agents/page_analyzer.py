"""
Page Analyzer Agent - Comprehensive page data extraction and caching.

This agent crawls pages ONCE and extracts ALL data that other agents need.
Results are cached so subsequent agents can read from cache instead of
making redundant HTTP requests.

Performance impact:
- Before: 10 pages × 5 agents = 50 HTTP requests
- After:  10 pages × 1 agent = 10 HTTP requests (5x faster!)
"""

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import structlog

from src.agents.base import BaseAgent, AgentContext
from src.cache.page_cache import PageData, get_cache
from src.models.agents import AgentResult, AgentTask, Priority, Recommendation

logger = structlog.get_logger()


class PageAnalyzerAgent(BaseAgent):
    """
    Comprehensive page analyzer that extracts all data for caching.

    Extracts:
    - Meta tags (title, description, OG, Twitter)
    - Content structure (headings, text, word count)
    - Links (internal, external)
    - Images (src, alt, dimensions)
    - Schema markup
    - Performance metrics
    - Mobile-friendliness
    - E-commerce data (price, availability)

    All extracted data is cached for other agents to reuse.
    """

    def __init__(self, context: AgentContext):
        super().__init__(
            agent_type="page-analyzer",
            description="Comprehensive page data extraction and caching",
            context=context,
        )
        self.cache = get_cache()

    async def run(self, task: AgentTask) -> AgentResult:
        """Execute page analysis task."""
        start_time = datetime.utcnow()

        try:
            if task.task_type == "analyze_page":
                result = await self._analyze_page(task.parameters)
            elif task.task_type == "analyze_batch":
                result = await self._analyze_batch(task.parameters)
            elif task.task_type == "analyze_sitemap":
                result = await self._analyze_sitemap(task.parameters)
            elif task.task_type == "refresh_cache":
                result = await self._refresh_cache(task.parameters)
            else:
                return AgentResult(
                    task_id=task.id,
                    agent_type=self.agent_type,
                    success=False,
                    data={"error": f"Unknown task type: {task.task_type}"},
                )

            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=True,
                data=result["data"],
                recommendations=result.get("recommendations", []),
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            )

        except Exception as e:
            logger.error("Page analysis failed", error=str(e))
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": str(e)},
            )

    async def _analyze_page(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze single page and cache results.

        This is the core extraction function that pulls all data from a page.
        """
        url = params.get("url")
        force_refresh = params.get("force_refresh", False)

        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_data = self.cache.get(url)
            if cached_data:
                logger.info("Page data from cache", url=url, age_seconds=(
                    datetime.utcnow() - cached_data.fetched_at
                ).total_seconds())
                return {
                    "data": {
                        "url": url,
                        "source": "cache",
                        "cached_at": cached_data.fetched_at.isoformat(),
                        "cache_hit_count": cached_data.hit_count,
                        "page_data": self._serialize_page_data(cached_data),
                    },
                    "recommendations": [],
                }

        # Fetch and extract (in production, use actual HTTP client + parser)
        logger.info("Fetching page", url=url)

        # SIMULATE page fetch and extraction
        # In production, replace with:
        # - aiohttp for async HTTP requests
        # - BeautifulSoup or lxml for HTML parsing
        # - Lighthouse API for performance metrics
        page_data = await self._fetch_and_extract(url)

        # Cache the results
        ttl = self._determine_ttl(page_data)
        self.cache.set(url, page_data, ttl=ttl)

        recommendations = []

        # Generate recommendations based on findings
        if not page_data.meta_title:
            recommendations.append(Recommendation(
                title="Missing Meta Title",
                description=f"Page {url} has no meta title tag",
                category="SEO - Meta Tags",
                priority=Priority.HIGH,
                estimated_impact="Critical for SEO",
                implementation_effort="low",
            ))

        if not page_data.meta_description:
            recommendations.append(Recommendation(
                title="Missing Meta Description",
                description=f"Page {url} has no meta description",
                category="SEO - Meta Tags",
                priority=Priority.HIGH,
                estimated_impact="Important for CTR",
                implementation_effort="low",
            ))

        if page_data.word_count < 300:
            recommendations.append(Recommendation(
                title="Thin Content",
                description=f"Page has only {page_data.word_count} words (minimum 300 recommended)",
                category="Content Quality",
                priority=Priority.MEDIUM,
                estimated_impact="Low word count may hurt rankings",
                implementation_effort="medium",
            ))

        if not page_data.schema_types:
            recommendations.append(Recommendation(
                title="Missing Schema Markup",
                description="No structured data found on page",
                category="Technical SEO",
                priority=Priority.MEDIUM,
                estimated_impact="Schema helps search engines understand content",
                implementation_effort="medium",
            ))

        return {
            "data": {
                "url": url,
                "source": "fresh",
                "fetched_at": page_data.fetched_at.isoformat(),
                "cached": True,
                "ttl_seconds": ttl,
                "page_data": self._serialize_page_data(page_data),
            },
            "recommendations": recommendations,
        }

    async def _analyze_batch(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze multiple pages in batch.

        Much faster than analyzing one-by-one due to:
        - Parallel requests
        - Connection pooling
        - Batch caching
        """
        urls = params.get("urls", [])
        concurrency = params.get("concurrency", 5)  # Parallel requests
        force_refresh = params.get("force_refresh", False)

        results = []
        cache_hits = 0
        fresh_fetches = 0

        # In production: Use asyncio.gather() for parallel fetching
        for url in urls:
            # Check cache
            if not force_refresh:
                cached_data = self.cache.get(url)
                if cached_data:
                    results.append({
                        "url": url,
                        "source": "cache",
                        "status": "success",
                    })
                    cache_hits += 1
                    continue

            # Fetch fresh
            try:
                page_data = await self._fetch_and_extract(url)
                ttl = self._determine_ttl(page_data)
                self.cache.set(url, page_data, ttl=ttl)
                results.append({
                    "url": url,
                    "source": "fresh",
                    "status": "success",
                })
                fresh_fetches += 1
            except Exception as e:
                results.append({
                    "url": url,
                    "status": "failed",
                    "error": str(e),
                })
                logger.error("Batch fetch failed", url=url, error=str(e))

        performance_improvement = (
            f"{cache_hits / len(urls) * 100:.1f}% cache hit rate"
            if urls else "N/A"
        )

        return {
            "data": {
                "total_urls": len(urls),
                "cache_hits": cache_hits,
                "fresh_fetches": fresh_fetches,
                "failed": len([r for r in results if r["status"] == "failed"]),
                "performance_improvement": performance_improvement,
                "results": results,
            },
            "recommendations": [],
        }

    async def _analyze_sitemap(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze all URLs from sitemap and pre-warm cache.

        Useful for:
        - Pre-warming cache before running multiple workflows
        - Bulk content audits
        - Site-wide analysis
        """
        sitemap_url = params.get("sitemap_url")
        limit = params.get("limit", 100)  # Max URLs to process

        # In production: Fetch and parse XML sitemap
        # For now, simulate
        urls = [
            f"{self.context.property_url}/page-{i}"
            for i in range(1, min(limit + 1, 101))
        ]

        # Analyze in batch
        batch_result = await self._analyze_batch({
            "urls": urls,
            "concurrency": 10,
        })

        return {
            "data": {
                "sitemap_url": sitemap_url,
                "urls_found": len(urls),
                "urls_processed": len(urls),
                **batch_result["data"],
            },
            "recommendations": [],
        }

    async def _refresh_cache(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Refresh cache entries (force re-fetch).

        Useful after:
        - Content updates
        - Site redesigns
        - Price changes (e-commerce)
        """
        urls = params.get("urls", [])
        pattern = params.get("pattern")  # e.g., "/products/"

        if pattern:
            # Invalidate pattern and re-fetch
            invalidated = self.cache.invalidate_pattern(pattern)
            logger.info("Pattern invalidated", pattern=pattern, count=invalidated)

        if urls:
            # Force refresh specific URLs
            for url in urls:
                self.cache.invalidate(url)

            # Re-fetch
            batch_result = await self._analyze_batch({
                "urls": urls,
                "force_refresh": True,
            })
            return batch_result

        return {
            "data": {
                "invalidated": invalidated if pattern else len(urls),
                "pattern": pattern,
            },
            "recommendations": [],
        }

    async def _fetch_and_extract(self, url: str) -> PageData:
        """
        Fetch URL and extract all data.

        In production, this would:
        1. Make HTTP request with aiohttp
        2. Parse HTML with BeautifulSoup/lxml
        3. Extract all meta tags, headings, links, images
        4. Run Lighthouse for performance metrics
        5. Detect content type and extract e-commerce data

        For now, we simulate with realistic data.
        """
        # SIMULATED DATA - replace with actual fetching in production
        parsed = urlparse(url)

        page_data = PageData(
            url=url,
            fetched_at=datetime.utcnow(),
            status_code=200,
            content_type=self._detect_content_type(url),
            html=f"<html><head><title>Example Page</title></head><body>Content for {url}</body></html>",
            html_size=50000,
            meta_title=f"Example Page - {parsed.path}",
            meta_description=f"This is an example page at {url}",
            canonical_url=url,
            h1_tags=["Main Heading"],
            h2_tags=["Subheading 1", "Subheading 2"],
            h3_tags=["Detail 1", "Detail 2", "Detail 3"],
            internal_links=[
                {"href": "/page1", "text": "Page 1", "title": ""},
                {"href": "/page2", "text": "Page 2", "title": ""},
            ],
            external_links=[
                {"href": "https://example.com", "text": "External Link", "title": ""},
            ],
            total_links=3,
            images=[
                {"src": "/image1.jpg", "alt": "Image 1", "width": 800, "height": 600, "loading": "lazy"},
                {"src": "/image2.jpg", "alt": "Image 2", "width": 1200, "height": 800, "loading": "eager"},
            ],
            total_images=2,
            schema_types=["Article", "BreadcrumbList"],
            word_count=850,
            text_content=f"Sample text content for {url}" * 100,
            language="en",
            page_load_time_ms=1200,
            is_mobile_friendly=True,
            viewport_meta="width=device-width, initial-scale=1",
            robots_meta="index, follow",
            has_ssl=url.startswith("https"),
        )

        # E-commerce specific data
        if page_data.content_type == "product":
            page_data.product_price = 49.99
            page_data.product_currency = "USD"
            page_data.product_availability = "InStock"
            page_data.product_sku = "SKU-12345"
            page_data.product_brand = "Example Brand"

        return page_data

    def _detect_content_type(self, url: str) -> str:
        """Detect content type from URL patterns."""
        url_lower = url.lower()

        if "/product/" in url_lower or "/p/" in url_lower:
            return "product"
        elif "/blog/" in url_lower or "/article/" in url_lower:
            return "blog"
        elif "/category/" in url_lower or "/c/" in url_lower:
            return "category"
        elif url_lower.endswith("/") and url_lower.count("/") == 3:
            return "homepage"
        else:
            return "article"

    def _determine_ttl(self, page_data: PageData) -> int:
        """Determine appropriate TTL based on content type."""
        ttl_map = {
            "product": 1800,    # 30 min (prices change)
            "blog": 86400,      # 24 hours (static)
            "article": 86400,   # 24 hours
            "homepage": 1800,   # 30 min (dynamic)
            "category": 3600,   # 1 hour
        }
        return ttl_map.get(page_data.content_type, 3600)

    def _serialize_page_data(self, page_data: PageData) -> dict[str, Any]:
        """Convert PageData to dictionary for API responses."""
        return {
            "url": page_data.url,
            "fetched_at": page_data.fetched_at.isoformat(),
            "status_code": page_data.status_code,
            "content_type": page_data.content_type,
            "meta": {
                "title": page_data.meta_title,
                "description": page_data.meta_description,
                "canonical": page_data.canonical_url,
            },
            "headings": {
                "h1": page_data.h1_tags,
                "h2": page_data.h2_tags,
                "h3": page_data.h3_tags,
            },
            "links": {
                "internal": len(page_data.internal_links),
                "external": len(page_data.external_links),
                "total": page_data.total_links,
            },
            "images": {
                "count": page_data.total_images,
                "details": page_data.images[:5],  # First 5 only
            },
            "schema": page_data.schema_types,
            "content": {
                "word_count": page_data.word_count,
                "language": page_data.language,
            },
            "performance": {
                "page_load_ms": page_data.page_load_time_ms,
            },
            "mobile": {
                "friendly": page_data.is_mobile_friendly,
            },
            "ecommerce": {
                "price": page_data.product_price,
                "currency": page_data.product_currency,
                "availability": page_data.product_availability,
            } if page_data.product_price else None,
            "cache": {
                "hit_count": page_data.hit_count,
                "ttl_seconds": page_data.ttl_seconds,
                "expires_at": page_data.expires_at.isoformat(),
            },
        }
