"""Optimization endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from src.agents.optimizer import OptimizationRecommenderAgent
from src.api.dependencies import AgentContextDep, ApiKeyDep
from src.models.agents import AgentTask

router = APIRouter()


class GenerateRecommendationsRequest(BaseModel):
    """Request to generate optimization recommendations."""
    url: HttpUrl
    page_content: str | None = None
    page_type: str = "product"
    target_queries: list[str] = []


class GenerateSchemaRequest(BaseModel):
    """Request to generate schema markup."""
    url: HttpUrl
    page_type: str
    page_data: dict[str, Any]


class GenerateFAQRequest(BaseModel):
    """Request to generate FAQ content."""
    topic: str
    url: HttpUrl | None = None
    page_content: str = ""
    target_queries: list[str] = []
    num_faqs: int = 5


class OptimizeForQueryRequest(BaseModel):
    """Request to optimize for a specific query."""
    query: str
    url: HttpUrl
    page_content: str
    aio_content: str | None = None


class BulkOptimizeRequest(BaseModel):
    """Request for bulk optimization."""
    pages: list[dict[str, Any]]  # [{url, content, queries}, ...]


@router.post("/recommendations")
async def generate_recommendations(
    request: GenerateRecommendationsRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Generate optimization recommendations for a page.

    Analyzes the page and generates actionable recommendations for:
    - Schema markup
    - Content structure
    - FAQ additions
    - Meta tags
    """
    agent = OptimizationRecommenderAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="generate_recommendations",
        parameters={
            "url": str(request.url),
            "page_content": request.page_content,
            "page_type": request.page_type,
            "target_queries": request.target_queries,
        },
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Generation failed"))

    return {
        "success": True,
        "data": result.data,
        "recommendations": [r.model_dump() for r in result.recommendations],
    }


@router.post("/generate-schema")
async def generate_schema(
    request: GenerateSchemaRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Generate Schema.org markup for a page.

    Generates optimized JSON-LD markup ready for implementation.
    """
    agent = OptimizationRecommenderAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="generate_schema",
        parameters={
            "url": str(request.url),
            "page_type": request.page_type,
            "page_data": request.page_data,
        },
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Generation failed"))

    return {
        "success": True,
        "data": result.data,
        "recommendations": [r.model_dump() for r in result.recommendations],
    }


@router.post("/generate-faq")
async def generate_faq(
    request: GenerateFAQRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Generate FAQ content and schema for a topic.

    Creates FAQs that:
    - Address target search queries
    - Are optimized for AI Overview citation
    - Include FAQPage schema markup
    """
    agent = OptimizationRecommenderAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="generate_faq",
        parameters={
            "topic": request.topic,
            "url": str(request.url) if request.url else "",
            "page_content": request.page_content,
            "target_queries": request.target_queries,
            "num_faqs": request.num_faqs,
        },
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Generation failed"))

    return {
        "success": True,
        "data": result.data,
        "recommendations": [r.model_dump() for r in result.recommendations],
    }


@router.post("/optimize-for-query")
async def optimize_for_query(
    request: OptimizeForQueryRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Generate optimizations for a specific search query.

    Analyzes how to optimize a page to be cited in AI Overviews
    for a particular query.
    """
    agent = OptimizationRecommenderAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="optimize_for_query",
        parameters={
            "query": request.query,
            "url": str(request.url),
            "page_content": request.page_content,
            "aio_content": request.aio_content,
        },
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Optimization failed"))

    return {
        "success": True,
        "data": result.data,
        "recommendations": [r.model_dump() for r in result.recommendations],
    }


@router.post("/bulk")
async def bulk_optimize(
    request: BulkOptimizeRequest,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Generate optimizations for multiple pages.

    Processes pages in batch and returns prioritized recommendations.
    """
    agent = OptimizationRecommenderAgent(context)

    task = AgentTask(
        agent_type=agent.agent_type,
        task_type="bulk_optimize",
        parameters={"pages": request.pages},
    )

    result = await agent.run(task)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.data.get("error", "Bulk optimization failed"))

    return {
        "success": True,
        "data": result.data,
        "recommendations": [r.model_dump() for r in result.recommendations],
    }
