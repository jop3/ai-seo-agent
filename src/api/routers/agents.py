"""Agent execution endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from src.agents.agent_tester import AgentTesterAgent
from src.agents.monitoring import MonitoringAgent
from src.api.dependencies import AgentContextDep, ApiKeyDep
from src.models.agents import AgentTask

router = APIRouter()


class PageInterpretRequest(BaseModel):
    """Request to interpret a page as an AI agent would."""
    url: HttpUrl


class CheckoutFlowRequest(BaseModel):
    """Request to test checkout flow."""
    product_url: HttpUrl
    product_query: str = ""


class SchemaValidationRequest(BaseModel):
    """Request to validate schema markup."""
    url: HttpUrl


class BulkPageTestRequest(BaseModel):
    """Request to test multiple pages."""
    urls: list[HttpUrl]
    concurrency: int = 3


class CompetitiveTestRequest(BaseModel):
    """Request for competitive agent comparison."""
    query: str
    client_url: HttpUrl
    competitor_urls: list[HttpUrl] = []


class MonitoringCycleRequest(BaseModel):
    """Request for monitoring cycle."""
    tracked_queries: list[str] = []
    traffic_threshold: float = 25.0


@router.post("/interpret-page")
async def interpret_page(
    request: PageInterpretRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Test how an AI agent would interpret a page.

    Simulates an AI agent visiting the page and analyzing:
    - What it can understand
    - What data it can extract
    - Whether it could complete actions
    - Agent-friendliness score
    """
    agent = AgentTesterAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="interpret_page",
        parameters={"url": str(request.url)},
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Interpretation failed"))

    return {
        "success": True,
        "data": result.data,
        "recommendations": [r.model_dump() for r in result.recommendations],
    }


@router.post("/test-checkout")
async def test_checkout_flow(
    request: CheckoutFlowRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Test if an AI agent could complete a checkout flow.

    Simulates an autonomous shopping agent trying to:
    1. Find product information
    2. Locate add-to-cart button
    3. Check checkout requirements

    Does NOT actually complete purchases.
    """
    agent = AgentTesterAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="test_checkout_flow",
        parameters={
            "product_url": str(request.product_url),
            "product_query": request.product_query,
        },
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Test failed"))

    return {
        "success": True,
        "data": result.data,
        "recommendations": [r.model_dump() for r in result.recommendations],
    }


@router.post("/validate-schema")
async def validate_schema(
    request: SchemaValidationRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Validate Schema.org markup on a page.

    Checks:
    - What schema types are present
    - Required fields for each type
    - Completeness score
    - Missing recommended schemas
    """
    agent = AgentTesterAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="validate_schema",
        parameters={"url": str(request.url)},
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Validation failed"))

    return {
        "success": True,
        "data": result.data,
        "recommendations": [r.model_dump() for r in result.recommendations],
    }


@router.post("/bulk-test")
async def bulk_page_test(
    request: BulkPageTestRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Test multiple pages for agent-friendliness.

    Returns aggregate statistics and identifies pages
    that need the most attention.
    """
    agent = AgentTesterAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="bulk_page_test",
        parameters={
            "urls": [str(url) for url in request.urls],
            "concurrency": request.concurrency,
        },
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Test failed"))

    return {
        "success": True,
        "data": result.data,
    }


@router.post("/competitive-test")
async def competitive_agent_test(
    request: CompetitiveTestRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Compare how an AI agent would evaluate you vs competitors.

    Simulates: "An AI agent is asked to help with [query].
    Who would it recommend and why?"
    """
    agent = AgentTesterAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="competitive_agent_test",
        parameters={
            "query": request.query,
            "client_url": str(request.client_url),
            "competitor_urls": [str(url) for url in request.competitor_urls],
        },
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Test failed"))

    return {
        "success": True,
        "data": result.data,
    }


@router.post("/monitoring/run-cycle")
async def run_monitoring_cycle(
    request: MonitoringCycleRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Run a full monitoring cycle.

    Checks:
    1. Traffic anomalies
    2. Algorithm updates
    3. AIO status changes
    4. Sends alerts for significant findings
    """
    agent = MonitoringAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="full_monitoring_cycle",
        parameters={
            "tracked_queries": request.tracked_queries,
            "threshold_percent": request.traffic_threshold,
        },
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Monitoring failed"))

    return {
        "success": True,
        "data": result.data,
        "alerts": [a.model_dump() for a in result.alerts],
    }


@router.post("/monitoring/daily-summary")
async def send_daily_summary(
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Generate and send daily summary to Teams.
    """
    agent = MonitoringAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="daily_summary",
        parameters={},
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Summary failed"))

    return {
        "success": True,
        "data": result.data,
    }
