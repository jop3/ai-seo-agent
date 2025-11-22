"""
Parallel Workflow Execution - Run multiple workflows simultaneously.

Key benefit: All workflows share the same page cache!
- Workflow 1 fetches a page → cached
- Workflow 2 needs same page → instant cache hit
- Workflow 3 needs same page → instant cache hit

Result: 3x faster than running workflows sequentially.
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

import structlog

from src.cache.page_cache import get_cache
from src.orchestrator.engine import Workflow, WorkflowResult

logger = structlog.get_logger()


async def run_workflows_parallel(
    orchestrator,
    workflows: list[Workflow],
    parameters: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Run multiple workflows in parallel with shared cache.

    All workflows share the same page cache, so pages fetched by one
    workflow are immediately available to others.

    Args:
        orchestrator: AgentOrchestrator instance
        workflows: List of Workflow objects to run
        parameters: Global parameters for all workflows

    Returns:
        Dict with results from all workflows

    Example:
        workflows = [
            technical_audit_workflow,
            content_optimization_workflow,
            ecommerce_seo_workflow,
        ]

        results = await run_workflows_parallel(
            orchestrator,
            workflows,
            parameters={"domain": "example.com"}
        )

        # All 3 workflows share cached pages!
        # If all 3 analyze same 100 pages:
        # Sequential: 300 HTTP requests
        # Parallel with cache: 100 HTTP requests (3x faster!)
    """
    start_time = datetime.utcnow()
    cache = get_cache()

    logger.info(
        "Starting parallel workflow execution",
        workflow_count=len(workflows),
    )

    # Get initial cache stats
    initial_stats = cache.get_stats()

    # Run all workflows in parallel
    tasks = [
        orchestrator.run_workflow(workflow, parameters)
        for workflow in workflows
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Get final cache stats
    final_stats = cache.get_stats()

    # Calculate cache benefit
    cache_hits_during_execution = final_stats["total_hits"] - initial_stats["total_hits"]
    cache_sets_during_execution = final_stats["total_sets"] - initial_stats["total_sets"]

    duration = (datetime.utcnow() - start_time).total_seconds()

    # Process results
    workflow_results = []
    successful = 0
    failed = 0

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            workflow_results.append({
                "workflow": workflows[i].name,
                "status": "failed",
                "error": str(result),
            })
            failed += 1
        else:
            workflow_results.append({
                "workflow": workflows[i].name,
                "status": "success",
                "result": result,
            })
            successful += 1

    # Calculate efficiency gain from shared cache
    if cache_sets_during_execution > 0:
        sharing_efficiency = round(
            cache_hits_during_execution / cache_sets_during_execution,
            2
        )
    else:
        sharing_efficiency = 0

    summary = {
        "total_workflows": len(workflows),
        "successful": successful,
        "failed": failed,
        "duration_seconds": round(duration, 2),
        "cache_stats": {
            "hits_during_execution": cache_hits_during_execution,
            "sets_during_execution": cache_sets_during_execution,
            "sharing_efficiency": sharing_efficiency,
            "hit_rate": final_stats["hit_rate_percent"],
        },
        "workflows": workflow_results,
    }

    logger.info(
        "Parallel workflow execution complete",
        **summary,
    )

    return summary


async def run_workflows_sequential_with_cache_warming(
    orchestrator,
    workflows: list[Workflow],
    parameters: Optional[dict[str, Any]] = None,
    warm_urls: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Run workflows sequentially but pre-warm cache first.

    Useful when parallel execution isn't possible but you still want
    cache benefits.

    Args:
        orchestrator: AgentOrchestrator instance
        workflows: List of Workflow objects to run sequentially
        parameters: Global parameters
        warm_urls: URLs to pre-warm in cache

    Returns:
        Dict with results from all workflows

    Example:
        warm_urls = [
            "https://example.com/",
            "https://example.com/products/best-seller",
            "https://example.com/blog/latest",
        ]

        results = await run_workflows_sequential_with_cache_warming(
            orchestrator,
            workflows,
            warm_urls=warm_urls,
        )

        # Cache pre-warmed, all workflows benefit!
    """
    from src.agents.page_analyzer import PageAnalyzerAgent
    from src.models.agents import AgentTask, AgentType

    start_time = datetime.utcnow()
    cache = get_cache()

    # Step 1: Warm cache if URLs provided
    if warm_urls:
        logger.info("Pre-warming cache", url_count=len(warm_urls))

        page_analyzer = PageAnalyzerAgent(orchestrator.context)
        warm_task = AgentTask(
            id="cache-warm",
            agent_type=AgentType.PAGE_ANALYZER,
            task_type="analyze_batch",
            parameters={
                "urls": warm_urls,
                "concurrency": 10,
            }
        )

        await page_analyzer.run(warm_task)

    # Step 2: Run workflows sequentially
    workflow_results = []

    for workflow in workflows:
        result = await orchestrator.run_workflow(workflow, parameters)
        workflow_results.append({
            "workflow": workflow.name,
            "status": "success" if result.success else "failed",
            "result": result,
        })

    duration = (datetime.utcnow() - start_time).total_seconds()
    stats = cache.get_stats()

    summary = {
        "total_workflows": len(workflows),
        "duration_seconds": round(duration, 2),
        "cache_warmed": len(warm_urls) if warm_urls else 0,
        "cache_hit_rate": stats["hit_rate_percent"],
        "workflows": workflow_results,
    }

    logger.info("Sequential workflow execution complete", **summary)
    return summary


def estimate_parallel_speedup(
    workflows: list[Workflow],
    estimated_pages_per_workflow: int = 100,
) -> dict[str, Any]:
    """
    Estimate speedup from running workflows in parallel vs sequential.

    Args:
        workflows: List of workflows to analyze
        estimated_pages_per_workflow: Avg pages each workflow analyzes

    Returns:
        Speedup estimation

    Example:
        estimate = estimate_parallel_speedup(
            [workflow1, workflow2, workflow3],
            estimated_pages_per_workflow=100
        )
        print(f"Speedup: {estimate['speedup_factor']}x faster")
    """
    num_workflows = len(workflows)

    # Sequential: each workflow fetches all pages independently
    sequential_requests = num_workflows * estimated_pages_per_workflow

    # Parallel with shared cache: each unique page fetched once
    # Assume 70% overlap across workflows (conservative)
    overlap_factor = 0.7
    unique_pages = estimated_pages_per_workflow * (1 + (num_workflows - 1) * (1 - overlap_factor))
    parallel_requests = int(unique_pages)

    speedup_factor = round(sequential_requests / parallel_requests, 2)

    estimate = {
        "num_workflows": num_workflows,
        "estimated_pages_per_workflow": estimated_pages_per_workflow,
        "sequential_requests": sequential_requests,
        "parallel_requests": parallel_requests,
        "speedup_factor": speedup_factor,
        "time_saved_percent": round((1 - 1/speedup_factor) * 100, 1),
        "recommendation": (
            f"Running {num_workflows} workflows in parallel will be "
            f"{speedup_factor}x faster ({estimate.get('time_saved_percent', 0)}% time saved) "
            f"due to shared cache."
        )
    }

    return estimate


async def run_with_progressive_caching(
    orchestrator,
    workflow: Workflow,
    url_batches: list[list[str]],
    parameters: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Run workflow on progressively larger batches with caching.

    Useful for very large sites where you want to:
    1. Test on small batch first
    2. Scale up progressively
    3. Use cached results from previous batches

    Args:
        orchestrator: AgentOrchestrator instance
        workflow: Workflow to run
        url_batches: List of URL batches (e.g., [[10 urls], [100 urls], [1000 urls]])
        parameters: Global parameters

    Returns:
        Results from all batches

    Example:
        url_batches = [
            top_10_urls,      # Test batch
            top_100_urls,     # Includes top 10 (cached!)
            all_1000_urls,    # Includes top 100 (cached!)
        ]

        results = await run_with_progressive_caching(
            orchestrator,
            workflow,
            url_batches,
        )

        # Batch 1: 10 fetches
        # Batch 2: 90 fetches (10 cached)
        # Batch 3: 900 fetches (100 cached)
        # Total: 1000 fetches vs 3x1000=3000 without caching
    """
    from src.agents.page_analyzer import PageAnalyzerAgent
    from src.models.agents import AgentTask, AgentType

    cache = get_cache()
    page_analyzer = PageAnalyzerAgent(orchestrator.context)

    batch_results = []

    for i, urls in enumerate(url_batches, 1):
        logger.info(f"Processing batch {i}/{len(url_batches)}", url_count=len(urls))

        # Pre-cache batch
        cache_task = AgentTask(
            id=f"batch-{i}-cache",
            agent_type=AgentType.PAGE_ANALYZER,
            task_type="analyze_batch",
            parameters={
                "urls": urls,
                "concurrency": 10,
            }
        )

        cache_result = await page_analyzer.run(cache_task)

        # Run workflow
        workflow_params = {**(parameters or {}), "urls": urls}
        workflow_result = await orchestrator.run_workflow(workflow, workflow_params)

        batch_results.append({
            "batch": i,
            "urls": len(urls),
            "cache_hits": cache_result.data.get("cache_hits", 0),
            "fresh_fetches": cache_result.data.get("fresh_fetches", 0),
            "workflow_result": workflow_result,
        })

    summary = {
        "total_batches": len(url_batches),
        "batches": batch_results,
        "final_cache_stats": cache.get_stats(),
    }

    return summary
