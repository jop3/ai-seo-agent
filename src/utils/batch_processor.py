"""
Batch Processing Utility - Efficiently process multiple URLs in parallel.

Key optimizations:
- Parallel fetching with concurrency limits
- Automatic page caching
- Rate limiting and throttling
- Progress tracking
- Error handling and retries
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

import structlog

from src.agents.page_analyzer import PageAnalyzerAgent
from src.cache.page_cache import PageData, get_cache
from src.models.agents import AgentTask

logger = structlog.get_logger()


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    concurrency: int = 5  # Parallel requests
    rate_limit_per_second: int = 10  # Max requests per second
    retry_attempts: int = 3  # Retry failed requests
    retry_delay_seconds: float = 1.0  # Delay between retries
    timeout_seconds: float = 30.0  # Request timeout
    use_cache: bool = True  # Use page cache
    cache_ttl: Optional[int] = None  # Cache TTL override


@dataclass
class BatchResult:
    """Result from batch processing."""

    total_urls: int
    successful: int
    failed: int
    cached: int
    fresh_fetches: int
    duration_seconds: float
    errors: list[dict[str, Any]]
    results: list[dict[str, Any]]


class BatchProcessor:
    """
    Efficiently process multiple URLs with caching and parallelization.

    Example:
        processor = BatchProcessor(page_analyzer_agent)
        urls = ["https://example.com/page1", "https://example.com/page2"]
        result = await processor.process_urls(urls)
        print(f"Processed {result.successful} URLs in {result.duration_seconds}s")
        print(f"Cache hit rate: {result.cached / result.total_urls * 100:.1f}%")
    """

    def __init__(
        self,
        page_analyzer: Optional[PageAnalyzerAgent] = None,
        config: Optional[BatchConfig] = None,
    ):
        self.page_analyzer = page_analyzer
        self.config = config or BatchConfig()
        self.cache = get_cache()
        self.semaphore = asyncio.Semaphore(self.config.concurrency)
        self.rate_limiter = RateLimiter(self.config.rate_limit_per_second)

    async def process_urls(
        self,
        urls: list[str],
        processor_func: Optional[Callable] = None,
    ) -> BatchResult:
        """
        Process multiple URLs in parallel with caching.

        Args:
            urls: List of URLs to process
            processor_func: Optional custom processing function

        Returns:
            BatchResult with statistics and results
        """
        start_time = datetime.utcnow()

        logger.info("Starting batch processing", total_urls=len(urls))

        # Process URLs in parallel
        tasks = [
            self._process_single_url(url, processor_func)
            for url in urls
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        successful = 0
        failed = 0
        cached = 0
        fresh_fetches = 0
        errors = []
        processed_results = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed += 1
                errors.append({
                    "url": urls[i],
                    "error": str(result),
                })
            elif result:
                successful += 1
                if result.get("source") == "cache":
                    cached += 1
                else:
                    fresh_fetches += 1
                processed_results.append(result)

        duration = (datetime.utcnow() - start_time).total_seconds()

        batch_result = BatchResult(
            total_urls=len(urls),
            successful=successful,
            failed=failed,
            cached=cached,
            fresh_fetches=fresh_fetches,
            duration_seconds=duration,
            errors=errors,
            results=processed_results,
        )

        logger.info(
            "Batch processing complete",
            total_urls=batch_result.total_urls,
            successful=batch_result.successful,
            failed=batch_result.failed,
            cache_hit_rate=f"{cached / len(urls) * 100:.1f}%" if urls else "0%",
            duration_seconds=batch_result.duration_seconds,
            urls_per_second=len(urls) / duration if duration > 0 else 0,
        )

        return batch_result

    async def _process_single_url(
        self,
        url: str,
        processor_func: Optional[Callable] = None,
    ) -> dict[str, Any]:
        """Process single URL with rate limiting and retries."""
        async with self.semaphore:
            # Rate limiting
            await self.rate_limiter.acquire()

            # Check cache first
            if self.config.use_cache:
                cached_data = self.cache.get(url)
                if cached_data:
                    logger.debug("Cache hit", url=url)
                    return {
                        "url": url,
                        "source": "cache",
                        "page_data": cached_data,
                    }

            # Retry logic
            for attempt in range(self.config.retry_attempts):
                try:
                    # Fetch with timeout
                    page_data = await asyncio.wait_for(
                        self._fetch_url(url, processor_func),
                        timeout=self.config.timeout_seconds,
                    )

                    # Cache result
                    if self.config.use_cache and page_data:
                        self.cache.set(url, page_data, ttl=self.config.cache_ttl)

                    return {
                        "url": url,
                        "source": "fresh",
                        "page_data": page_data,
                    }

                except asyncio.TimeoutError:
                    logger.warning(
                        "URL fetch timeout",
                        url=url,
                        attempt=attempt + 1,
                    )
                    if attempt < self.config.retry_attempts - 1:
                        await asyncio.sleep(self.config.retry_delay_seconds)
                    else:
                        raise

                except Exception as e:
                    logger.error(
                        "URL fetch failed",
                        url=url,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    if attempt < self.config.retry_attempts - 1:
                        await asyncio.sleep(self.config.retry_delay_seconds)
                    else:
                        raise

    async def _fetch_url(
        self,
        url: str,
        processor_func: Optional[Callable] = None,
    ) -> PageData:
        """Fetch URL using page analyzer or custom processor."""
        if processor_func:
            return await processor_func(url)

        # Use PageAnalyzer if available
        if self.page_analyzer:
            task = AgentTask(
                id=f"batch-{url}",
                agent_type="page-analyzer",
                task_type="analyze_page",
                parameters={"url": url},
            )
            result = await self.page_analyzer.run(task)
            if result.success:
                return result.data.get("page_data")

        raise ValueError("No page analyzer or processor function provided")

    async def warm_cache(self, urls: list[str]) -> int:
        """
        Pre-warm cache with URLs.

        Useful before running workflows to ensure all data is cached.

        Args:
            urls: List of URLs to pre-fetch

        Returns:
            Number of URLs successfully cached
        """
        result = await self.process_urls(urls)
        return result.successful


class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self, rate_per_second: int):
        self.rate = rate_per_second
        self.tokens = rate_per_second
        self.last_update = datetime.utcnow()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Wait until a token is available."""
        async with self.lock:
            now = datetime.utcnow()
            elapsed = (now - self.last_update).total_seconds()

            # Refill tokens based on time elapsed
            self.tokens = min(
                self.rate,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            # Wait if no tokens available
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


async def process_urls_in_batches(
    urls: list[str],
    batch_size: int = 100,
    **kwargs,
) -> list[BatchResult]:
    """
    Process large list of URLs in smaller batches.

    Useful for very large sites (1000s of URLs) to avoid memory issues.

    Example:
        urls = get_all_product_urls()  # 5000 URLs
        results = await process_urls_in_batches(urls, batch_size=100)
        total_processed = sum(r.successful for r in results)
    """
    processor = BatchProcessor(**kwargs)
    results = []

    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        logger.info(
            "Processing batch",
            batch_num=i // batch_size + 1,
            batch_size=len(batch),
        )
        result = await processor.process_urls(batch)
        results.append(result)

    return results
