"""
Bloom Filter for Cache - Fast "definitely not in cache" checks.

A Bloom filter provides instant membership checks with minimal memory.
Perfect for large caches (10k+ entries).

Impact: Saves hash table lookups for non-existent keys.
"""

import hashlib
from typing import Optional

import structlog

logger = structlog.get_logger()


class BloomFilter:
    """
    Simple Bloom filter for cache existence checks.

    A Bloom filter is a probabilistic data structure that tells you:
    - "Definitely NOT in set" (100% accurate)
    - "Probably in set" (99.9% accurate with proper sizing)

    Usage:
        bloom = BloomFilter(expected_items=10000, false_positive_rate=0.01)

        # Add items
        bloom.add("https://example.com")

        # Check existence
        if not bloom.might_contain("https://unknown.com"):
            # Definitely not in cache, skip expensive lookup
            return None

        # Might be in cache, do actual lookup
        return cache.get("https://unknown.com")
    """

    def __init__(
        self,
        expected_items: int = 10000,
        false_positive_rate: float = 0.01,
    ):
        """
        Initialize Bloom filter.

        Args:
            expected_items: Expected number of items (default: 10,000)
            false_positive_rate: Desired false positive rate (default: 0.01 = 1%)
        """
        import math

        # Calculate optimal bit array size
        self.expected_items = expected_items
        self.false_positive_rate = false_positive_rate

        # m = -(n * ln(p)) / (ln(2)^2)
        m = -((expected_items * math.log(false_positive_rate)) / (math.log(2) ** 2))
        self.bit_array_size = int(m)

        # Calculate optimal number of hash functions
        # k = (m/n) * ln(2)
        k = (self.bit_array_size / expected_items) * math.log(2)
        self.num_hash_functions = int(k)

        # Initialize bit array
        self.bit_array = [False] * self.bit_array_size

        # Stats
        self._items_added = 0

        logger.info(
            "Bloom filter initialized",
            expected_items=expected_items,
            false_positive_rate=false_positive_rate,
            bit_array_size=self.bit_array_size,
            num_hash_functions=self.num_hash_functions,
            memory_kb=round(self.bit_array_size / 8 / 1024, 2),
        )

    def _hash(self, item: str, seed: int) -> int:
        """Generate hash for item with given seed."""
        h = hashlib.md5(f"{item}:{seed}".encode()).digest()
        return int.from_bytes(h[:4], byteorder='little') % self.bit_array_size

    def add(self, item: str) -> None:
        """
        Add item to Bloom filter.

        Args:
            item: Item to add (typically a cache key)
        """
        for i in range(self.num_hash_functions):
            index = self._hash(item, i)
            self.bit_array[index] = True

        self._items_added += 1

    def might_contain(self, item: str) -> bool:
        """
        Check if item might be in the set.

        Args:
            item: Item to check

        Returns:
            True if item MIGHT be in set (check actual cache)
            False if item is DEFINITELY NOT in set (skip cache check)
        """
        for i in range(self.num_hash_functions):
            index = self._hash(item, i)
            if not self.bit_array[index]:
                # Definitely not in set
                return False

        # Might be in set (could be false positive)
        return True

    def clear(self) -> None:
        """Clear the Bloom filter."""
        self.bit_array = [False] * self.bit_array_size
        self._items_added = 0
        logger.info("Bloom filter cleared")

    def get_stats(self) -> dict:
        """Get Bloom filter statistics."""
        import math

        # Estimate current false positive rate
        # p ≈ (1 - e^(-kn/m))^k
        if self._items_added > 0:
            exponent = -(self.num_hash_functions * self._items_added) / self.bit_array_size
            current_fp_rate = (1 - math.exp(exponent)) ** self.num_hash_functions
        else:
            current_fp_rate = 0.0

        # Calculate fill rate
        fill_count = sum(self.bit_array)
        fill_rate = fill_count / self.bit_array_size

        return {
            "expected_items": self.expected_items,
            "items_added": self._items_added,
            "bit_array_size": self.bit_array_size,
            "num_hash_functions": self.num_hash_functions,
            "memory_bytes": self.bit_array_size // 8,
            "memory_kb": round(self.bit_array_size / 8 / 1024, 2),
            "fill_rate_percent": round(fill_rate * 100, 2),
            "target_false_positive_rate": self.false_positive_rate,
            "estimated_false_positive_rate": round(current_fp_rate, 4),
            "overloaded": self._items_added > self.expected_items,
        }


class CacheBloomFilter:
    """
    Bloom filter wrapper for cache operations.

    Integrates with page cache to provide fast existence checks.

    Usage:
        cache_bloom = CacheBloomFilter()

        # Add cached items
        cache_bloom.add("https://example.com")

        # Fast existence check
        if cache_bloom.definitely_not_cached(url):
            # Skip expensive cache lookup
            return None

        # Might be cached, do actual lookup
        return cache.get(url)
    """

    def __init__(
        self,
        expected_items: int = 10000,
        false_positive_rate: float = 0.01,
    ):
        """
        Initialize cache Bloom filter.

        Args:
            expected_items: Expected cache size
            false_positive_rate: Desired false positive rate
        """
        self.bloom = BloomFilter(expected_items, false_positive_rate)
        self._hits = 0  # Bloom said "might exist"
        self._misses = 0  # Bloom said "definitely not"
        self._false_positives = 0  # Bloom said "might" but wasn't

    def add(self, cache_key: str) -> None:
        """Add cache key to Bloom filter."""
        self.bloom.add(cache_key)

    def definitely_not_cached(self, cache_key: str) -> bool:
        """
        Check if item is definitely not in cache.

        Args:
            cache_key: Cache key to check

        Returns:
            True if definitely not cached (skip cache lookup)
            False if might be cached (do cache lookup)
        """
        might_exist = self.bloom.might_contain(cache_key)

        if might_exist:
            self._hits += 1
            return False  # Might be cached, need to check
        else:
            self._misses += 1
            return True  # Definitely not cached

    def record_false_positive(self) -> None:
        """Record a false positive (Bloom said "might" but wasn't cached)."""
        self._false_positives += 1

    def clear(self) -> None:
        """Clear Bloom filter and stats."""
        self.bloom.clear()
        self._hits = 0
        self._misses = 0
        self._false_positives = 0

    def get_stats(self) -> dict:
        """Get cache Bloom filter statistics."""
        bloom_stats = self.bloom.get_stats()

        total_checks = self._hits + self._misses
        actual_fp_rate = (
            self._false_positives / self._hits if self._hits > 0 else 0
        )

        return {
            **bloom_stats,
            "total_checks": total_checks,
            "bloom_hits": self._hits,  # Said "might exist"
            "bloom_misses": self._misses,  # Said "definitely not"
            "false_positives": self._false_positives,
            "actual_false_positive_rate": round(actual_fp_rate, 4),
            "bloom_effectiveness_percent": round(
                self._misses / total_checks * 100, 1
            ) if total_checks > 0 else 0,
        }


# Global Bloom filter for cache
_global_cache_bloom: Optional[CacheBloomFilter] = None


def get_cache_bloom() -> CacheBloomFilter:
    """Get global cache Bloom filter instance."""
    global _global_cache_bloom

    if _global_cache_bloom is None:
        _global_cache_bloom = CacheBloomFilter(
            expected_items=10000,
            false_positive_rate=0.01,
        )

    return _global_cache_bloom
