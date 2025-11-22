"""
Dashboard API endpoints.

Provides unified dashboard data, trends, and visualizations.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.dashboard import DashboardAggregator, DashboardMetrics

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Global dashboard aggregator (in production, use proper state management)
dashboard_aggregator = DashboardAggregator()


class DashboardResponse(BaseModel):
    """Dashboard data response."""
    success: bool = True
    data: DashboardMetrics
    message: str = "Dashboard data retrieved successfully"


class TrendDataResponse(BaseModel):
    """Trend data response for charting."""
    success: bool = True
    data: dict[str, Any]
    message: str = "Trend data retrieved successfully"


class QuickStatsResponse(BaseModel):
    """Quick stats response."""
    success: bool = True
    data: dict[str, Any]
    message: str = "Quick stats retrieved successfully"


@router.get("/", response_model=DashboardResponse)
async def get_dashboard():
    """
    Get complete dashboard metrics.

    Returns overall SEO health, category scores, platform readiness,
    issues, opportunities, and recommendations.
    """
    try:
        # In production, fetch actual workflow results from database
        # For now, return simulated dashboard
        workflow_results = _get_recent_workflow_results()

        metrics = dashboard_aggregator.aggregate(workflow_results)

        return DashboardResponse(data=metrics)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick-stats", response_model=QuickStatsResponse)
async def get_quick_stats():
    """
    Get quick dashboard statistics.

    Returns high-level metrics for dashboard summary:
    - Overall score
    - Critical issues count
    - Opportunities count
    - 30-day score change
    """
    try:
        stats = dashboard_aggregator.get_quick_stats()

        return QuickStatsResponse(data=stats)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends", response_model=TrendDataResponse)
async def get_trend_data(
    days: int = Query(30, ge=7, le=90, description="Number of days to include"),
):
    """
    Get trend data for charting.

    Returns time series data for:
    - Overall score over time
    - Category scores over time
    - Platform readiness over time

    Args:
        days: Number of days of historical data (7-90)
    """
    try:
        trend_data = dashboard_aggregator.get_trend_data(days=days)

        return TrendDataResponse(data=trend_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/category/{category_id}")
async def get_category_details(category_id: str):
    """
    Get detailed metrics for a specific category.

    Categories:
    - technical: Technical SEO
    - content: Content Quality
    - ecommerce: E-commerce
    - ai_readiness: AI Readiness (GEO)
    - local: Local SEO
    - competitive: Competitive Position
    - authority: Authority & Trust
    """
    try:
        # Get latest dashboard
        workflow_results = _get_recent_workflow_results()
        metrics = dashboard_aggregator.aggregate(workflow_results)

        if category_id not in metrics.categories:
            raise HTTPException(status_code=404, detail=f"Category '{category_id}' not found")

        category_score = metrics.categories[category_id]

        # Get category-specific recommendations
        category_recommendations = [
            rec for rec in metrics.top_recommendations
            if category_id in (rec.category or "").lower()
        ]

        return {
            "success": True,
            "data": {
                "category": category_score.dict(),
                "recommendations": [rec.dict() for rec in category_recommendations[:5]],
                "trend_direction": category_score.trend.value,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/{platform_id}")
async def get_platform_details(platform_id: str):
    """
    Get detailed metrics for a specific platform.

    Platforms:
    - google_search: Google Search
    - google_shopping: Google Shopping
    - chatgpt: ChatGPT
    - perplexity: Perplexity
    - claude: Claude
    - gemini: Gemini (Bard)
    - bing: Bing
    """
    try:
        # Get latest dashboard
        workflow_results = _get_recent_workflow_results()
        metrics = dashboard_aggregator.aggregate(workflow_results)

        if platform_id not in metrics.platforms:
            raise HTTPException(status_code=404, detail=f"Platform '{platform_id}' not found")

        platform_readiness = metrics.platforms[platform_id]

        return {
            "success": True,
            "data": {
                "platform": platform_readiness.dict(),
                "recommendations": _get_platform_recommendations(platform_id, metrics),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_active_alerts(
    severity: str | None = Query(None, description="Filter by severity: critical, error, warning, info"),
):
    """
    Get active alerts.

    Optionally filter by severity level.
    """
    try:
        workflow_results = _get_recent_workflow_results()
        metrics = dashboard_aggregator.aggregate(workflow_results)

        alerts = metrics.active_alerts

        # Filter by severity if specified
        if severity:
            alerts = [a for a in alerts if a.severity.value == severity.lower()]

        return {
            "success": True,
            "data": {
                "total": len(alerts),
                "alerts": [a.dict() for a in alerts],
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_recommendations(
    priority: str | None = Query(None, description="Filter by priority: critical, high, medium, low"),
    limit: int = Query(20, ge=1, le=100, description="Number of recommendations to return"),
):
    """
    Get optimization recommendations.

    Optionally filter by priority level.
    """
    try:
        workflow_results = _get_recent_workflow_results()
        metrics = dashboard_aggregator.aggregate(workflow_results)

        recommendations = metrics.top_recommendations

        # Filter by priority if specified
        if priority:
            recommendations = [r for r in recommendations if r.priority.value == priority.lower()]

        # Limit results
        recommendations = recommendations[:limit]

        return {
            "success": True,
            "data": {
                "total": len(recommendations),
                "recommendations": [r.dict() for r in recommendations],
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_dashboard():
    """
    Trigger dashboard data refresh.

    Recalculates all metrics from latest workflow results.
    """
    try:
        workflow_results = _get_recent_workflow_results()
        metrics = dashboard_aggregator.aggregate(workflow_results)

        return {
            "success": True,
            "data": {
                "refreshed_at": metrics.generated_at.isoformat(),
                "overall_score": metrics.overall_score,
                "overall_status": metrics.overall_status.value,
            },
            "message": "Dashboard refreshed successfully",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions

def _get_recent_workflow_results() -> list[dict[str, Any]]:
    """
    Get recent workflow results.

    In production, this would query the database for recent workflow executions.
    For now, returns simulated data.
    """
    # TODO: Replace with actual database query
    # This is a placeholder that returns simulated workflow results

    return [
        {
            "workflow_id": "full_audit",
            "executed_at": datetime.utcnow() - timedelta(hours=2),
            "step_results": [
                {
                    "agent_type": "technical_auditor",
                    "result": {
                        "data": {"overall_score": 78.5},
                        "recommendations": [],
                        "alerts": [],
                    },
                },
                {
                    "agent_type": "geo_analyzer",
                    "result": {
                        "data": {"overall_score": 65.2},
                        "recommendations": [],
                        "alerts": [],
                    },
                },
            ],
        }
    ]


def _get_platform_recommendations(platform_id: str, metrics: DashboardMetrics) -> list[dict]:
    """Get recommendations specific to a platform."""
    # Filter recommendations that mention the platform
    platform_name = dashboard_aggregator.PLATFORMS.get(platform_id, "")

    relevant_recs = [
        rec for rec in metrics.top_recommendations
        if platform_name.lower() in (rec.description or "").lower()
    ]

    return [rec.dict() for rec in relevant_recs[:5]]
