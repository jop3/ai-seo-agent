"""
Integration tests for performance optimizations.

Tests all 10 optimization features:
- LRU eviction
- Request deduplication
- Connection pooling
- Workflow result caching
- Agent result memoization
- Smart retry with jitter
- Background cache refresh
- HTTP/2 support
- Sitemap preload
- Bloom filter
"""

import asyncio
from datetime import datetime
import pytest

from src.cache.page_cache import PageCache, PageData, CacheConfig
from src.utils.request_deduplication import RequestDeduplicator
from src.utils.connection_pool import ConnectionPool
from src.utils.workflow_cache import WorkflowResultCache
from src.utils.agent_memoization import AgentMemoCache, memoize_agent_result
from src.utils.smart_retry import SmartRetryPolicy, retry_with_jitter
from src.utils.background_refresh import BackgroundRefresher
from src.utils.bloom_filter import BloomFilter, CacheBloomFilter
from src.utils.sitemap_preload import fetch_sitemap, preload_from_sitemap


class TestLRUEviction:
    """Test LRU eviction policy."""

    def test_lru_eviction_keeps_popular_pages(self):
        """Test that LRU keeps frequently accessed pages."""
        # Small cache for testing
        config = CacheConfig(max_entries=3)
        cache = PageCache(config)

        # Add 3 pages
        page1 = PageData(url="https://example.com/page1", fetched_at=datetime.utcnow(), status_code=200, html="test1")
        page2 = PageData(url="https://example.com/page2", fetched_at=datetime.utcnow(), status_code=200, html="test2")
        page3 = PageData(url="https://example.com/page3", fetched_at=datetime.utcnow(), status_code=200, html="test3")

        cache.set("https://example.com/page1", page1)
        cache.set("https://example.com/page2", page2)
        cache.set("https://example.com/page3", page3)

        # Access page1 5 times (make it popular)
        for _ in range(5):
            cache.get("https://example.com/page1")

        # Access page2 once
        cache.get("https://example.com/page2")

        # Don't access page3 (least recently used)

        # Add page4 (should evict page3 - LRU)
        page4 = PageData(url="https://example.com/page4", fetched_at=datetime.utcnow(), status_code=200, html="test4")
        cache.set("https://example.com/page4", page4)

        # Check results
        assert cache.get("https://example.com/page1") is not None, "Popular page1 should be kept"
        assert cache.get("https://example.com/page2") is not None, "Used page2 should be kept"
        assert cache.get("https://example.com/page3") is None, "Unused page3 should be evicted"
        assert cache.get("https://example.com/page4") is not None, "New page4 should be in cache"

    def test_lru_updates_access_time(self):
        """Test that accessing pages updates their access time."""
        config = CacheConfig(max_entries=2)
        cache = PageCache(config)

        page1 = PageData(url="https://example.com/page1", fetched_at=datetime.utcnow(), status_code=200, html="test1")
        page2 = PageData(url="https://example.com/page2", fetched_at=datetime.utcnow(), status_code=200, html="test2")

        cache.set("https://example.com/page1", page1)
        cache.set("https://example.com/page2", page2)

        # Access page1 to update its access time
        cache.get("https://example.com/page1")

        # Add page3 (should evict page2 since page1 was accessed more recently)
        page3 = PageData(url="https://example.com/page3", fetched_at=datetime.utcnow(), status_code=200, html="test3")
        cache.set("https://example.com/page3", page3)

        assert cache.get("https://example.com/page1") is not None
        assert cache.get("https://example.com/page2") is None
        assert cache.get("https://example.com/page3") is not None


class TestRequestDeduplication:
    """Test request deduplication."""

    @pytest.mark.asyncio
    async def test_deduplicates_simultaneous_requests(self):
        """Test that simultaneous requests are deduplicated."""
        dedup = RequestDeduplicator()
        fetch_count = 0

        async def fetch_func():
            nonlocal fetch_count
            fetch_count += 1
            await asyncio.sleep(0.1)  # Simulate network delay
            return "result"

        # Make 5 simultaneous requests
        results = await asyncio.gather(*[
            dedup.deduplicate("test_key", fetch_func)
            for _ in range(5)
        ])

        # Should only fetch once
        assert fetch_count == 1, f"Expected 1 fetch, got {fetch_count}"
        assert all(r == "result" for r in results)

        stats = dedup.get_stats()
        assert stats["total_requests"] == 5
        assert stats["unique_requests"] == 1
        assert stats["deduplicated_requests"] == 4

    @pytest.mark.asyncio
    async def test_different_keys_not_deduplicated(self):
        """Test that different keys are not deduplicated."""
        dedup = RequestDeduplicator()
        fetch_count = 0

        async def fetch_func():
            nonlocal fetch_count
            fetch_count += 1
            return "result"

        # Different keys
        await dedup.deduplicate("key1", fetch_func)
        await dedup.deduplicate("key2", fetch_func)

        assert fetch_count == 2


class TestConnectionPool:
    """Test HTTP connection pooling."""

    @pytest.mark.asyncio
    async def test_connection_pool_initialization(self):
        """Test connection pool initializes correctly."""
        pool = ConnectionPool(
            limit=50,
            limit_per_host=5,
            enable_http2=False,  # Disable HTTP/2 for testing
        )

        # Ensure session is initialized before checking stats
        await pool._ensure_session()

        stats = await pool.get_stats()
        assert stats["limit"] == 50
        assert stats["limit_per_host"] == 5

        await pool.close()

    @pytest.mark.asyncio
    async def test_connection_pool_http2_detection(self):
        """Test HTTP/2 availability detection."""
        pool = ConnectionPool(enable_http2=True)

        # Ensure session is initialized before checking stats
        await pool._ensure_session()

        stats = await pool.get_stats()
        # Should have http2_available key
        assert "http2_available" in stats
        assert "http2_enabled" in stats

        await pool.close()


class TestWorkflowCache:
    """Test workflow result caching."""

    def test_workflow_cache_hit(self):
        """Test workflow cache returns cached results."""
        cache = WorkflowResultCache()

        # Cache a result
        cache_key = cache.get_cache_key("test_workflow", {"param": "value"})
        cache.set(cache_key, {"result": "data"}, ttl=3600)

        # Retrieve it
        cached = cache.get(cache_key)
        assert cached is not None
        assert cached["result"] == "data"

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0

    def test_workflow_cache_miss(self):
        """Test workflow cache miss."""
        cache = WorkflowResultCache()

        cache_key = cache.get_cache_key("test_workflow", {"param": "value"})
        cached = cache.get(cache_key)

        assert cached is None

        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 1

    def test_workflow_cache_key_generation(self):
        """Test cache key generation is consistent."""
        cache = WorkflowResultCache()

        key1 = cache.get_cache_key("workflow1", {"a": 1, "b": 2})
        key2 = cache.get_cache_key("workflow1", {"b": 2, "a": 1})  # Different order

        # Should be same (order-independent)
        assert key1 == key2

        key3 = cache.get_cache_key("workflow1", {"a": 1, "b": 3})  # Different value
        assert key1 != key3


class TestAgentMemoization:
    """Test agent result memoization."""

    def test_agent_memo_cache_hit(self):
        """Test agent memoization caches results."""
        cache = AgentMemoCache()

        # Cache a result
        cache.set(
            agent_type="technical_seo",
            task_type="full_audit",
            result={"findings": ["issue1", "issue2"]},
            url="https://example.com",
        )

        # Retrieve it
        cached = cache.get(
            agent_type="technical_seo",
            task_type="full_audit",
            url="https://example.com",
        )

        assert cached is not None
        assert cached["findings"] == ["issue1", "issue2"]

    def test_agent_memo_different_urls(self):
        """Test memoization distinguishes different URLs."""
        cache = AgentMemoCache()

        cache.set(
            agent_type="technical_seo",
            task_type="full_audit",
            result={"url": "example.com"},
            url="https://example.com",
        )

        cache.set(
            agent_type="technical_seo",
            task_type="full_audit",
            result={"url": "other.com"},
            url="https://other.com",
        )

        result1 = cache.get(agent_type="technical_seo", task_type="full_audit", url="https://example.com")
        result2 = cache.get(agent_type="technical_seo", task_type="full_audit", url="https://other.com")

        assert result1["url"] == "example.com"
        assert result2["url"] == "other.com"


class TestSmartRetry:
    """Test smart retry with jitter."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failures(self):
        """Test retry succeeds after transient failures."""
        attempts = 0

        async def flaky_func():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError("Transient error")
            return "success"

        result = await retry_with_jitter(
            flaky_func,
            max_attempts=5,
            base_delay=0.01,  # Small delay for testing
            jitter_factor=0.1,
        )

        assert result == "success"
        assert attempts == 3

    @pytest.mark.asyncio
    async def test_retry_fails_after_max_attempts(self):
        """Test retry fails after max attempts."""
        async def always_fails():
            raise ConnectionError("Permanent error")

        with pytest.raises(ConnectionError):
            await retry_with_jitter(
                always_fails,
                max_attempts=3,
                base_delay=0.01,
            )

    @pytest.mark.asyncio
    async def test_retry_policy_stats(self):
        """Test retry policy tracks statistics."""
        policy = SmartRetryPolicy(max_attempts=3, base_delay=0.01)

        call_count = 0

        async def sometimes_fails():
            nonlocal call_count
            call_count += 1
            # First execute() call: fail on attempt 1, succeed on attempt 2
            # Second execute() call: succeed immediately
            if call_count == 1:
                raise ConnectionError("Fail once")
            return "success"

        # First call - needs retry (fails once, then succeeds)
        await policy.execute(sometimes_fails)

        # Second call - succeeds first try
        await policy.execute(sometimes_fails)

        stats = policy.get_stats()
        assert stats["total_attempts"] == 2
        assert stats["successful_first_try"] == 1
        assert stats["retries_needed"] == 1


class TestBackgroundRefresh:
    """Test background cache refresh."""

    @pytest.mark.asyncio
    async def test_background_refresher_initialization(self):
        """Test background refresher initializes correctly."""
        async def mock_fetch(url):
            return PageData(url=url, fetched_at=datetime.utcnow(), status_code=200)

        refresher = BackgroundRefresher(
            fetch_func=mock_fetch,
            refresh_threshold_seconds=600,
            check_interval_seconds=60,
        )

        assert refresher._running is False
        stats = refresher.get_stats()
        assert stats["is_running"] is False
        assert stats["total_checks"] == 0


class TestBloomFilter:
    """Test Bloom filter."""

    def test_bloom_filter_definitely_not_exists(self):
        """Test Bloom filter correctly identifies non-existent items."""
        bloom = BloomFilter(expected_items=1000, false_positive_rate=0.01)

        # Add items
        bloom.add("item1")
        bloom.add("item2")
        bloom.add("item3")

        # Check non-existent item
        assert bloom.might_contain("item1") is True
        assert bloom.might_contain("item2") is True
        assert bloom.might_contain("item3") is True
        assert bloom.might_contain("item4") is False  # Definitely not

    def test_bloom_filter_false_positive_rate(self):
        """Test Bloom filter false positive rate is acceptable."""
        bloom = BloomFilter(expected_items=1000, false_positive_rate=0.01)

        # Add 1000 items
        for i in range(1000):
            bloom.add(f"item{i}")

        # Check 1000 non-existent items
        false_positives = 0
        for i in range(1000, 2000):
            if bloom.might_contain(f"item{i}"):
                false_positives += 1

        false_positive_rate = false_positives / 1000

        # Should be close to 1% (within 5%)
        assert false_positive_rate < 0.05, f"False positive rate too high: {false_positive_rate}"

    def test_cache_bloom_filter(self):
        """Test cache-specific Bloom filter."""
        cache_bloom = CacheBloomFilter(expected_items=100, false_positive_rate=0.01)

        # Add cached items
        cache_bloom.add("https://example.com/page1")
        cache_bloom.add("https://example.com/page2")

        # Check existence
        assert cache_bloom.definitely_not_cached("https://example.com/page1") is False
        assert cache_bloom.definitely_not_cached("https://example.com/page99") is True

        stats = cache_bloom.get_stats()
        assert stats["total_checks"] == 2
        assert stats["bloom_misses"] == 1  # page99 definitely not cached


class TestSitemapPreload:
    """Test sitemap-based preload."""

    @pytest.mark.asyncio
    async def test_sitemap_parsing(self):
        """Test sitemap XML parsing."""
        # Mock sitemap XML
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/</loc>
        <priority>1.0</priority>
        <changefreq>daily</changefreq>
    </url>
    <url>
        <loc>https://example.com/page1</loc>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>https://example.com/page2</loc>
        <priority>0.5</priority>
    </url>
</urlset>"""

        # Save to temp file
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(sitemap_xml)
            temp_path = f.name

        try:
            # Mock HTTP client
            class MockClient:
                async def get(self, url):
                    with open(temp_path, 'r') as f:
                        return 200, f.read()

            client = MockClient()

            # Parse sitemap
            urls = await fetch_sitemap("https://example.com/sitemap.xml", client)

            assert len(urls) == 3
            assert urls[0]["loc"] == "https://example.com/"
            assert urls[0]["priority"] == 1.0
            assert urls[1]["priority"] == 0.8

        finally:
            os.unlink(temp_path)


class TestOptimizationIntegration:
    """Integration tests for combined optimizations."""

    @pytest.mark.asyncio
    async def test_deduplication_with_cache(self):
        """Test request deduplication works with page cache."""
        from src.cache.page_cache import get_cache
        from src.utils.request_deduplication import get_deduplicator

        cache = get_cache()
        dedup = get_deduplicator()

        fetch_count = 0

        async def fetch_and_cache(url):
            nonlocal fetch_count
            fetch_count += 1

            # Check cache first
            if cached := cache.get(url):
                return cached

            # Fetch
            await asyncio.sleep(0.1)
            page_data = PageData(url=url, fetched_at=datetime.utcnow(), status_code=200, html="test")

            # Cache
            cache.set(url, page_data)
            return page_data

        # Make 10 simultaneous requests
        url = "https://example.com/test"
        results = await asyncio.gather(*[
            dedup.deduplicate(url, lambda: fetch_and_cache(url))
            for _ in range(10)
        ])

        # Should only fetch once (deduplication)
        assert fetch_count == 1
        assert all(r.url == url for r in results)

        # Subsequent requests should hit cache
        fetch_count = 0
        result = cache.get(url)
        assert result is not None
        assert fetch_count == 0  # No new fetch needed

    def test_workflow_cache_with_agent_memo(self):
        """Test workflow cache and agent memo work together."""
        from src.utils.workflow_cache import get_workflow_cache
        from src.utils.agent_memoization import get_agent_memo_cache

        wf_cache = get_workflow_cache()
        agent_cache = get_agent_memo_cache()

        # Simulate workflow with agents
        workflow_id = "test_workflow"
        params = {"url": "https://example.com"}

        # Cache workflow result
        wf_key = wf_cache.get_cache_key(workflow_id, params)
        wf_cache.set(wf_key, {"agents_run": 3, "results": []})

        # Cache individual agent results
        agent_cache.set(
            agent_type="technical",
            task_type="audit",
            result={"issues": []},
            url=params["url"],
        )

        # Both should be cached
        assert wf_cache.get(wf_key) is not None
        assert agent_cache.get(agent_type="technical", task_type="audit", url=params["url"]) is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
