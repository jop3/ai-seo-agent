"""Analysis endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from src.agents.seo_analyst import SEOAnalystAgent
from src.api.dependencies import AgentContextDep, ApiKeyDep
from src.models.agents import AgentTask, TaskPriority

router = APIRouter()


class FullAnalysisRequest(BaseModel):
    """Request for full SEO analysis."""
    query_limit: int = 500
    days: int = 30
    traffic_threshold: float = 20.0


class AIOCheckRequest(BaseModel):
    """Request to check queries for AI Overviews."""
    queries: list[str]


class TrafficAnalysisRequest(BaseModel):
    """Request for traffic drop analysis."""
    threshold_percent: float = 20.0
    comparison_days: int = 7


class QueryClassificationRequest(BaseModel):
    """Request to classify queries."""
    queries: list[str]


@router.post("/full")
async def run_full_analysis(
    request: FullAnalysisRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Run a comprehensive SEO analysis.

    This will:
    1. Fetch top queries from GSC
    2. Classify queries by intent and AIO risk
    3. Check high-risk queries for AI Overviews
    4. Detect traffic changes
    5. Generate recommendations
    """
    agent = SEOAnalystAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="full_analysis",
        parameters=request.model_dump(),
        priority=TaskPriority.HIGH,
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Analysis failed"))

    return {
        "success": True,
        "data": result.data,
        "recommendations": [r.model_dump() for r in result.recommendations],
        "alerts": [a.model_dump() for a in result.alerts],
        "execution_time_ms": result.execution_time_ms,
    }


@router.post("/aio-check")
async def check_aio_status(
    request: AIOCheckRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Check specific queries for AI Overview presence.

    Returns detailed information about whether queries trigger
    AI Overviews and if you're being cited.
    """
    agent = SEOAnalystAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="detect_aio_impact",
        parameters={"queries": request.queries},
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Check failed"))

    return {
        "success": True,
        "data": result.data,
        "alerts": [a.model_dump() for a in result.alerts],
    }


@router.post("/traffic-drops")
async def analyze_traffic_drops(
    request: TrafficAnalysisRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Analyze traffic drops and correlate with AI Overviews.

    Compares recent traffic to previous period and identifies
    queries with significant drops, checking if they correlate
    with AI Overview introduction.
    """
    agent = SEOAnalystAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="traffic_drop_analysis",
        parameters=request.model_dump(),
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Analysis failed"))

    return {
        "success": True,
        "data": result.data,
    }


@router.post("/classify-queries")
async def classify_queries(
    request: QueryClassificationRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Classify queries by intent and AI Overview risk.

    Uses LLM to classify each query as:
    - Intent: informational, navigational, transactional, commercial, local
    - AIO Risk: high, medium, low
    - Optimization Priority: high, medium, low
    """
    agent = SEOAnalystAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="query_classification",
        parameters={"queries": request.queries},
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Classification failed"))

    return {
        "success": True,
        "data": result.data,
    }
