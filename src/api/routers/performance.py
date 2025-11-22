"""
Performance Monitoring API - REST endpoints for optimization metrics.

Provides HTTP endpoints to monitor and manage performance optimizations.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.dashboard.performance import (
    get_all_optimization_stats,
    get_performance_health,
)
from src.cache.page_cache import get_cache
from src.utils.agent_memoization import get_agent_memo_cache
from src.utils.bloom_filter import get_cache_bloom
from src.utils.request_deduplication import get_deduplicator
from src.utils.smart_retry import get_retry_policy
from src.utils.workflow_cache import get_workflow_cache

router = APIRouter(prefix="/performance", tags=["performance"])


class PerformanceStats(BaseModel):
    """Performance statistics response."""

    timestamp: str
    page_cache: dict[str, Any]
    workflow_cache: dict[str, Any]
    agent_memoization: dict[str, Any]
    request_deduplication: dict[str, Any]
    connection_pool: dict[str, Any]
    smart_retry: dict[str, Any]
    bloom_filter: dict[str, Any]
    background_refresh: dict[str, Any] | None
    summary: dict[str, Any]


class HealthStatus(BaseModel):
    """Performance health status."""

    status: str
    critical_issues: list[str]
    warnings: list[str]
    recommendations: list[str]
    overall_hit_rate: float
    cache_utilization: float
    retry_rate: float


class ClearCacheRequest(BaseModel):
    """Request to clear specific caches."""

    page_cache: bool = False
    workflow_cache: bool = False
    agent_memoization: bool = False
    request_deduplication: bool = False
    bloom_filter: bool = False
    all: bool = False


@router.get("/stats", response_model=PerformanceStats)
async def get_performance_stats():
    """
    Get comprehensive performance statistics.

    Returns all optimization metrics including:
    - Page cache (LRU eviction)
    - Workflow cache
    - Agent memoization
    - Request deduplication
    - Connection pooling
    - Smart retry
    - Bloom filter
    - Background refresh

    Example:
        GET /api/performance/stats
    """
    stats = await get_all_optimization_stats()
    return stats


@router.get("/health", response_model=HealthStatus)
def get_health_status():
    """
    Get performance health status.

    Returns health assessment with warnings and recommendations.

    Example:
        GET /api/performance/health

    Response:
        {
            "status": "healthy|warning|critical",
            "critical_issues": [],
            "warnings": ["Low cache hit rate"],
            "recommendations": ["Enable compression"]
        }
    """
    health = get_performance_health()
    return health


@router.get("/page-cache/stats")
def get_page_cache_stats():
    """Get page cache statistics."""
    cache = get_cache()
    return cache.get_stats()


@router.get("/page-cache/top-hits")
def get_page_cache_top_hits(limit: int = 10):
    """
    Get most frequently accessed cached pages.

    Args:
        limit: Number of top pages to return (default: 10)

    Example:
        GET /api/performance/page-cache/top-hits?limit=20
    """
    cache = get_cache()
    return cache.get_top_hits(limit=limit)


@router.get("/workflow-cache/stats")
def get_workflow_cache_stats():
    """Get workflow cache statistics."""
    cache = get_workflow_cache()
    return cache.get_stats()


@router.get("/workflow-cache/top-hits")
def get_workflow_cache_top_hits(limit: int = 10):
    """Get most frequently cached workflows."""
    cache = get_workflow_cache()
    return cache.get_top_hits(limit=limit)


@router.get("/agent-memo/stats")
def get_agent_memo_stats():
    """Get agent memoization statistics."""
    cache = get_agent_memo_cache()
    return cache.get_stats()


@router.get("/deduplication/stats")
def get_deduplication_stats():
    """Get request deduplication statistics."""
    dedup = get_deduplicator()
    return dedup.get_stats()


@router.get("/retry/stats")
def get_retry_stats():
    """Get smart retry statistics."""
    policy = get_retry_policy()
    return policy.get_stats()


@router.get("/bloom-filter/stats")
def get_bloom_filter_stats():
    """Get Bloom filter statistics."""
    bloom = get_cache_bloom()
    return bloom.get_stats()


@router.post("/cleanup")
async def cleanup_expired_entries():
    """
    Clean up expired entries from all caches.

    Returns:
        Cleanup counts for each cache

    Example:
        POST /api/performance/cleanup

    Response:
        {
            "page_cache": 125,
            "workflow_cache": 3,
            "agent_memoization": 45
        }
    """
    from src.utils.optimizations import cleanup_all_caches

    counts = await cleanup_all_caches()
    return counts


@router.post("/clear", status_code=204)
def clear_caches(request: ClearCacheRequest):
    """
    Clear specific caches (use with caution!).

    Args:
        request: Specifies which caches to clear

    Example:
        POST /api/performance/clear
        {
            "page_cache": true,
            "workflow_cache": false,
            "all": false
        }

    Response:
        204 No Content
    """
    if request.all:
        get_cache().clear()
        get_workflow_cache().clear()
        get_agent_memo_cache().clear()
        get_deduplicator().reset_stats()
        get_cache_bloom().clear()
        return

    if request.page_cache:
        get_cache().clear()

    if request.workflow_cache:
        get_workflow_cache().clear()

    if request.agent_memoization:
        get_agent_memo_cache().clear()

    if request.request_deduplication:
        get_deduplicator().reset_stats()

    if request.bloom_filter:
        get_cache_bloom().clear()


@router.get("/summary")
async def get_performance_summary():
    """
    Get human-readable performance summary.

    Returns:
        Performance summary text

    Example:
        GET /api/performance/summary
    """
    from src.utils.optimizations import get_optimization_summary

    summary = get_optimization_summary()
    return {"summary": summary}


@router.post("/page-cache/invalidate")
def invalidate_page_cache(url: str):
    """
    Invalidate specific URL in page cache.

    Args:
        url: URL to invalidate

    Example:
        POST /api/performance/page-cache/invalidate?url=https://example.com

    Response:
        {"invalidated": true}
    """
    cache = get_cache()
    result = cache.invalidate(url)
    return {"invalidated": result}


@router.post("/page-cache/invalidate-pattern")
def invalidate_page_cache_pattern(pattern: str):
    """
    Invalidate all URLs matching pattern.

    Args:
        pattern: URL pattern to match

    Example:
        POST /api/performance/page-cache/invalidate-pattern?pattern=/products/

    Response:
        {"count": 150}
    """
    cache = get_cache()
    count = cache.invalidate_pattern(pattern)
    return {"count": count}


@router.post("/workflow-cache/invalidate")
def invalidate_workflow_cache(workflow_id: str):
    """
    Invalidate all cached results for a workflow.

    Args:
        workflow_id: Workflow ID to invalidate

    Example:
        POST /api/performance/workflow-cache/invalidate?workflow_id=technical_audit

    Response:
        {"count": 5}
    """
    cache = get_workflow_cache()
    count = cache.invalidate_workflow(workflow_id)
    return {"count": count}


@router.post("/agent-memo/invalidate-url")
def invalidate_agent_memo_url(url: str):
    """
    Invalidate all agent results for a URL.

    Args:
        url: URL to invalidate

    Example:
        POST /api/performance/agent-memo/invalidate-url?url=https://example.com

    Response:
        {"count": 8}
    """
    cache = get_agent_memo_cache()
    count = cache.invalidate_url(url)
    return {"count": count}


@router.post("/agent-memo/invalidate-agent")
def invalidate_agent_memo_agent(agent_type: str):
    """
    Invalidate all cached results for an agent type.

    Args:
        agent_type: Agent type to invalidate

    Example:
        POST /api/performance/agent-memo/invalidate-agent?agent_type=technical_seo

    Response:
        {"count": 25}
    """
    cache = get_agent_memo_cache()
    count = cache.invalidate_agent(agent_type)
    return {"count": count}
