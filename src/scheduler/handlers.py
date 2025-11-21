"""
Job handlers that connect scheduled jobs to agents.

Supports both individual agent execution and orchestrated workflows.
"""

import structlog
from typing import Any

from src.agents.base import AgentContext
from src.agents.seo_analyst import SEOAnalystAgent
from src.agents.monitoring import MonitoringAgent
from src.config import get_settings
from src.integrations.azure_openai import AzureOpenAIClient
from src.integrations.google_search_console import GoogleSearchConsoleClient
from src.integrations.serp import get_serp_client
from src.integrations.teams import TeamsNotifier
from src.models.agents import AgentTask
from src.scheduler.jobs import JobType, get_scheduler
from src.orchestrator import AgentOrchestrator, get_workflow

logger = structlog.get_logger()


async def create_agent_context() -> AgentContext:
    """Create a shared agent context for job execution."""
    settings = get_settings()

    openai_client = AzureOpenAIClient(settings.azure)

    gsc_client = None
    if settings.google.gsc_property_url:
        gsc_client = GoogleSearchConsoleClient(
            credentials_path=settings.google.gsc_credentials_path,
            property_url=settings.google.gsc_property_url,
        )

    serp_client = None
    if settings.google.gsc_property_url:
        from urllib.parse import urlparse
        domain = urlparse(settings.google.gsc_property_url).netloc
        serp_client = get_serp_client(settings.serp, domain)

    teams_notifier = None
    webhook_url = settings.alerts.teams_webhook_url.get_secret_value()
    if webhook_url:
        teams_notifier = TeamsNotifier(webhook_url)

    from urllib.parse import urlparse
    return AgentContext(
        settings=settings,
        openai_client=openai_client,
        gsc_client=gsc_client,
        serp_client=serp_client,
        teams_notifier=teams_notifier,
        client_domain=urlparse(settings.google.gsc_property_url).netloc if settings.google.gsc_property_url else "",
        property_url=settings.google.gsc_property_url or "",
    )


async def handle_full_analysis(params: dict[str, Any]) -> dict[str, Any]:
    """Handle full SEO analysis job using orchestrator."""
    context = await create_agent_context()

    # Use the full audit workflow for comprehensive analysis
    workflow = get_workflow("full_audit")
    if workflow:
        orchestrator = AgentOrchestrator(context)
        result = await orchestrator.run_workflow(workflow, params)

        # Send Teams notification with workflow results
        if context.teams_notifier:
            severity = "critical" if result.steps_failed > 0 else "info"
            await context.teams_notifier.send_alert(
                title=f"{result.workflow_name} Complete",
                message=result.executive_summary[:500],
                severity=severity,
                data={
                    "steps_completed": result.steps_completed,
                    "steps_failed": result.steps_failed,
                    "alerts": len(result.all_alerts),
                    "recommendations": len(result.all_recommendations),
                    "duration_ms": result.duration_ms,
                },
            )

        return {
            "success": result.success,
            "workflow_id": result.workflow_id,
            "steps_completed": result.steps_completed,
            "alerts": len(result.all_alerts),
            "recommendations": len(result.all_recommendations),
            "priority_actions": len(result.priority_actions),
        }

    # Fallback to single agent if workflow not found
    agent = SEOAnalystAgent(context)
    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="full_analysis",
        parameters=params,
    )
    result = await agent.run(task)

    return {
        "success": result.success,
        "alerts": len(result.alerts),
        "recommendations": len(result.recommendations),
    }


async def handle_traffic_monitor(params: dict[str, Any]) -> dict[str, Any]:
    """Handle traffic monitoring job."""
    context = await create_agent_context()
    agent = MonitoringAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="check_traffic_anomalies",
        parameters=params,
    )

    result = await agent.run(task)

    # Alert on critical anomalies
    if result.alerts:
        critical = [a for a in result.alerts if a.severity.value == "critical"]
        if critical and context.teams_notifier:
            await context.teams_notifier.send_alert(
                title="Critical Traffic Anomaly Detected",
                message=critical[0].message,
                severity="critical",
                data={"total_anomalies": len(result.alerts)},
            )

    return {
        "success": result.success,
        "anomalies": len(result.alerts),
    }


async def handle_aio_check(params: dict[str, Any]) -> dict[str, Any]:
    """Handle AIO status check job."""
    context = await create_agent_context()
    agent = SEOAnalystAgent(context)

    # Get top queries first
    if context.gsc_client:
        queries = await context.gsc_client.get_top_queries(limit=params.get("query_limit", 100))
        query_strings = [q.query for q in queries[:params.get("query_limit", 100)]]
    else:
        query_strings = []

    if not query_strings:
        return {"success": True, "checked": 0, "with_aio": 0}

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="detect_aio_impact",
        parameters={"queries": query_strings},
    )

    result = await agent.run(task)

    return {
        "success": result.success,
        "checked": len(query_strings),
        "data": result.data,
    }


async def handle_competitor_check(params: dict[str, Any]) -> dict[str, Any]:
    """Handle competitor monitoring job."""
    # Import here to avoid circular imports
    from src.agents.competitor_monitor import CompetitorMonitorAgent

    context = await create_agent_context()
    agent = CompetitorMonitorAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="full_competitor_analysis",
        parameters=params,
    )

    result = await agent.run(task)

    return {
        "success": result.success,
        "data": result.data,
    }


async def handle_multi_engine_check(params: dict[str, Any]) -> dict[str, Any]:
    """Handle multi-engine presence check."""
    # Import here to avoid circular imports
    from src.agents.multi_engine_tracker import MultiEngineTrackerAgent

    context = await create_agent_context()
    agent = MultiEngineTrackerAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="check_all_engines",
        parameters=params,
    )

    result = await agent.run(task)

    return {
        "success": result.success,
        "data": result.data,
    }


async def handle_technical_audit(params: dict[str, Any]) -> dict[str, Any]:
    """Handle technical SEO audit job."""
    # Import here to avoid circular imports
    from src.agents.technical_seo import TechnicalSEOAgent

    context = await create_agent_context()
    agent = TechnicalSEOAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="full_audit",
        parameters=params,
    )

    result = await agent.run(task)

    return {
        "success": result.success,
        "issues": len(result.recommendations) if result.recommendations else 0,
    }


def register_all_handlers():
    """Register all job handlers with the scheduler."""
    scheduler = get_scheduler()

    scheduler.register_handler(JobType.FULL_ANALYSIS, handle_full_analysis)
    scheduler.register_handler(JobType.TRAFFIC_MONITOR, handle_traffic_monitor)
    scheduler.register_handler(JobType.AIO_CHECK, handle_aio_check)
    scheduler.register_handler(JobType.COMPETITOR_CHECK, handle_competitor_check)
    scheduler.register_handler(JobType.MULTI_ENGINE_CHECK, handle_multi_engine_check)
    scheduler.register_handler(JobType.TECHNICAL_AUDIT, handle_technical_audit)

    logger.info("Registered all job handlers")
