"""
Performance Monitoring Dashboard - Real-time optimization metrics.

Provides comprehensive performance monitoring and visualization for all
optimization systems.
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

import structlog

from src.cache.page_cache import get_cache
from src.utils.agent_memoization import get_agent_memo_cache
from src.utils.background_refresh import get_background_refresher
from src.utils.bloom_filter import get_cache_bloom
from src.utils.connection_pool import get_connection_pool
from src.utils.request_deduplication import get_deduplicator
from src.utils.smart_retry import get_retry_policy
from src.utils.workflow_cache import get_workflow_cache

logger = structlog.get_logger()


async def get_all_optimization_stats() -> dict[str, Any]:
    """
    Get comprehensive statistics from all optimization systems.

    Returns:
        Complete statistics from all optimizations
    """
    page_cache = get_cache()
    workflow_cache = get_workflow_cache()
    agent_memo = get_agent_memo_cache()
    deduplicator = get_deduplicator()
    connection_pool = get_connection_pool()
    retry_policy = get_retry_policy()
    cache_bloom = get_cache_bloom()

    bg_refresher = get_background_refresher()

    stats = {
        "timestamp": datetime.utcnow().isoformat(),
        "page_cache": page_cache.get_stats(),
        "workflow_cache": workflow_cache.get_stats(),
        "agent_memoization": agent_memo.get_stats(),
        "request_deduplication": deduplicator.get_stats(),
        "connection_pool": await connection_pool.get_stats(),
        "smart_retry": retry_policy.get_stats(),
        "bloom_filter": cache_bloom.get_stats(),
        "background_refresh": bg_refresher.get_stats() if bg_refresher else None,
    }

    # Calculate overall metrics
    total_cache_requests = (
        stats["page_cache"]["total_hits"] + stats["page_cache"]["total_misses"]
    )

    stats["summary"] = {
        "overall_cache_hit_rate": stats["page_cache"]["hit_rate_percent"],
        "total_cache_entries": (
            stats["page_cache"]["total_entries"]
            + stats["workflow_cache"]["total_entries"]
            + stats["agent_memoization"]["total_entries"]
        ),
        "deduplication_savings": stats["request_deduplication"]["deduplication_rate_percent"],
        "retry_success_rate": stats["smart_retry"]["success_rate_percent"],
        "bloom_effectiveness": stats["bloom_filter"].get("bloom_effectiveness_percent", 0),
    }

    return stats


def format_performance_dashboard(stats: dict[str, Any]) -> str:
    """
    Format statistics as a beautiful CLI dashboard.

    Args:
        stats: Statistics from get_all_optimization_stats()

    Returns:
        Formatted dashboard string
    """
    page = stats["page_cache"]
    workflow = stats["workflow_cache"]
    agent = stats["agent_memoization"]
    dedup = stats["request_deduplication"]
    retry = stats["smart_retry"]
    bloom = stats["bloom_filter"]
    pool = stats["connection_pool"]
    summary = stats["summary"]

    # Helper for colored metrics
    def color_metric(value: float, good_threshold: float, bad_threshold: float) -> str:
        if value >= good_threshold:
            return f"🟢 {value}%"
        elif value >= bad_threshold:
            return f"🟡 {value}%"
        else:
            return f"🔴 {value}%"

    dashboard = f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    🚀 PERFORMANCE OPTIMIZATION DASHBOARD                  ║
╚═══════════════════════════════════════════════════════════════════════════╝

📊 OVERALL SUMMARY
├─ Cache Hit Rate:        {color_metric(summary["overall_cache_hit_rate"], 70, 50)}
├─ Total Cache Entries:   {summary["total_cache_entries"]:,}
├─ Deduplication Savings: {color_metric(summary["deduplication_savings"], 20, 10)}
└─ Retry Success Rate:    {color_metric(summary["retry_success_rate"], 90, 70)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 PAGE CACHE (LRU Eviction)
├─ Entries:       {page["total_entries"]:,} / {page["max_entries"]:,} ({page["utilization_percent"]}% full)
├─ Hit Rate:      {color_metric(page["hit_rate_percent"], 70, 50)}
├─ Hits/Misses:   {page["total_hits"]:,} / {page["total_misses"]:,}
├─ Size:          {page["total_size_mb"]:.1f} MB
├─ Evictions:     {page["total_evictions"]:,}
└─ Avg Entry:     {page["avg_entry_size_kb"]:.1f} KB

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️  WORKFLOW CACHE
├─ Cached Workflows: {workflow["total_entries"]:,}
├─ Hit Rate:         {color_metric(workflow["hit_rate_percent"], 80, 60)}
├─ Hits/Misses:      {workflow["hits"]:,} / {workflow["misses"]:,}
└─ Workflows Saved:  {workflow["hits"]:,}x executions avoided

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧠 AGENT MEMOIZATION
├─ Cached Results:   {agent["total_entries"]:,}
├─ Hit Rate:         {color_metric(agent["hit_rate_percent"], 70, 50)}
├─ Hits/Misses:      {agent["hits"]:,} / {agent["misses"]:,}
└─ Work Avoided:     {agent["hits"]:,}x agent executions

Breakdown by Agent:
"""

    # Add agent breakdown
    if agent.get("entries_by_agent"):
        for agent_type, count in sorted(agent["entries_by_agent"].items(), key=lambda x: x[1], reverse=True)[:5]:
            dashboard += f"  • {agent_type:.<30} {count:>4} results\n"

    dashboard += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 REQUEST DEDUPLICATION
├─ Total Requests:     {dedup["total_requests"]:,}
├─ Unique Requests:    {dedup["unique_requests"]:,}
├─ Deduplicated:       {dedup["deduplicated_requests"]:,}
├─ Dedup Rate:         {color_metric(dedup["deduplication_rate_percent"], 30, 15)}
└─ Bandwidth Saved:    ~{dedup["bandwidth_saved_percent"]}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 HTTP CONNECTION POOL
├─ Status:           {pool.get("status", "unknown")}
├─ Total Limit:      {pool.get("limit", "N/A")}
├─ Per-Host Limit:   {pool.get("limit_per_host", "N/A")}
├─ DNS Cache TTL:    {pool.get("ttl_dns_cache", "N/A")}s
├─ HTTP/2:           {"✅ Enabled" if pool.get("http2_enabled") else "❌ Disabled"}
└─ HTTP/2 Available: {"✅ Yes" if pool.get("http2_available") else "❌ No"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔄 SMART RETRY (with Jitter)
├─ Total Attempts:   {retry["total_attempts"]:,}
├─ First Try OK:     {retry["successful_first_try"]:,}
├─ Retries Needed:   {retry["retries_needed"]:,}
├─ Failures:         {retry["total_failures"]:,}
├─ Success Rate:     {color_metric(retry["success_rate_percent"], 90, 70)}
└─ Retry Rate:       {retry["retry_rate_percent"]}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 BLOOM FILTER (Cache Existence)
├─ Items Added:        {bloom["items_added"]:,} / {bloom["expected_items"]:,}
├─ Total Checks:       {bloom["total_checks"]:,}
├─ Definitely Not:     {bloom["bloom_misses"]:,}
├─ Might Exist:        {bloom["bloom_hits"]:,}
├─ False Positives:    {bloom["false_positives"]:,}
├─ Effectiveness:      {bloom.get("bloom_effectiveness_percent", 0)}% lookups saved
├─ Memory:             {bloom["memory_kb"]:.2f} KB
└─ Overloaded:         {"⚠️  Yes" if bloom.get("overloaded") else "✅ No"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

    # Background refresh (optional)
    bg_refresh = stats.get("background_refresh")
    if bg_refresh:
        status = "🟢 Running" if bg_refresh["is_running"] else "🔴 Stopped"
        dashboard += f"""
🔄 BACKGROUND CACHE REFRESH
├─ Status:           {status}
├─ Total Checks:     {bg_refresh["total_checks"]:,}
├─ Refreshes:        {bg_refresh["background_refreshes"]:,}
└─ Errors:           {bg_refresh["refresh_errors"]:,}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    dashboard += f"""
💡 RECOMMENDATIONS
"""

    # Generate recommendations
    recommendations = []

    if page["hit_rate_percent"] < 50:
        recommendations.append("⚠️  Low page cache hit rate - consider pre-warming cache")

    if page["utilization_percent"] > 80:
        recommendations.append("⚠️  Page cache nearly full - consider increasing max_entries")

    if workflow["hit_rate_percent"] < 30 and workflow["total_requests"] > 10:
        recommendations.append("⚠️  Low workflow cache hit rate - workflows not being reused")

    if dedup["deduplication_rate_percent"] < 10 and dedup["total_requests"] > 100:
        recommendations.append("💡 Low deduplication - consider running more parallel workflows")

    if not pool.get("http2_enabled") and pool.get("http2_available"):
        recommendations.append("💡 HTTP/2 available but not enabled - enable for better performance")

    if retry["retry_rate_percent"] > 20:
        recommendations.append("⚠️  High retry rate - check for upstream issues")

    if bloom.get("overloaded"):
        recommendations.append("⚠️  Bloom filter overloaded - increase expected_items")

    if not recommendations:
        recommendations.append("✅ All systems operating optimally!")

    for rec in recommendations:
        dashboard += f"  {rec}\n"

    dashboard += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Last Updated: {stats["timestamp"]}
"""

    return dashboard


async def print_performance_dashboard():
    """Print performance dashboard to console."""
    stats = await get_all_optimization_stats()
    dashboard = format_performance_dashboard(stats)
    print(dashboard)


async def watch_performance_dashboard(interval: int = 5):
    """
    Continuously watch and update performance dashboard.

    Args:
        interval: Update interval in seconds (default: 5)
    """
    import os

    while True:
        # Clear screen (works on Unix and Windows)
        os.system('cls' if os.name == 'nt' else 'clear')

        # Print dashboard
        await print_performance_dashboard()

        # Wait
        await asyncio.sleep(interval)


def get_performance_health() -> dict[str, Any]:
    """
    Get performance health assessment.

    Returns:
        Health status with warnings and recommendations
    """
    page_cache = get_cache()
    workflow_cache = get_workflow_cache()
    agent_memo = get_agent_memo_cache()
    deduplicator = get_deduplicator()
    retry_policy = get_retry_policy()

    page_stats = page_cache.get_stats()
    workflow_stats = workflow_cache.get_stats()
    agent_stats = agent_memo.get_stats()
    dedup_stats = deduplicator.get_stats()
    retry_stats = retry_policy.get_stats()

    warnings = []
    recommendations = []
    critical_issues = []

    # Check page cache
    if page_stats["hit_rate_percent"] < 30:
        critical_issues.append("Critical: Page cache hit rate <30%")
    elif page_stats["hit_rate_percent"] < 50:
        warnings.append("Low page cache hit rate (<50%)")

    if page_stats["utilization_percent"] > 90:
        critical_issues.append("Critical: Page cache >90% full")
    elif page_stats["utilization_percent"] > 80:
        warnings.append("Page cache >80% full")

    # Check workflow cache
    if workflow_stats["total_requests"] > 10 and workflow_stats["hit_rate_percent"] < 30:
        warnings.append("Low workflow cache hit rate (<30%)")

    # Check retry rate
    if retry_stats["retry_rate_percent"] > 30:
        critical_issues.append("Critical: High retry rate (>30%)")
    elif retry_stats["retry_rate_percent"] > 20:
        warnings.append("High retry rate (>20%)")

    # Determine overall status
    if critical_issues:
        status = "critical"
    elif warnings:
        status = "warning"
    else:
        status = "healthy"

    # Generate recommendations
    if page_stats["hit_rate_percent"] < 50:
        recommendations.append("Pre-warm cache with sitemap preload")
        recommendations.append("Enable background cache refresh")

    if page_stats["utilization_percent"] > 80:
        recommendations.append("Increase page cache max_entries")
        recommendations.append("Enable compression to fit more entries")

    return {
        "status": status,
        "critical_issues": critical_issues,
        "warnings": warnings,
        "recommendations": recommendations,
        "overall_hit_rate": page_stats["hit_rate_percent"],
        "cache_utilization": page_stats["utilization_percent"],
        "retry_rate": retry_stats["retry_rate_percent"],
    }


# CLI entry point
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "watch":
        # Watch mode
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        asyncio.run(watch_performance_dashboard(interval))
    else:
        # One-shot
        asyncio.run(print_performance_dashboard())
