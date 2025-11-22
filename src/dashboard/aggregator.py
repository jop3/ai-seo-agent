"""
Dashboard Data Aggregator - Combines all agent results into unified dashboard.

Provides:
- Overall SEO health score (0-100)
- Category breakdowns (Technical, Content, E-commerce, AI, etc.)
- Trend analysis over time
- Red/Green indicators
- Key stats and metrics
- Platform readiness scores
"""

from datetime import datetime, timedelta
from typing import Any
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from src.models.agents import AgentResult, Recommendation, Alert, Priority, Severity

logger = structlog.get_logger()


class HealthStatus(str, Enum):
    """Health status indicators."""
    CRITICAL = "critical"  # 0-40: Red
    WARNING = "warning"    # 41-60: Yellow
    GOOD = "good"          # 61-80: Light Green
    EXCELLENT = "excellent"  # 81-100: Dark Green


class TrendDirection(str, Enum):
    """Trend direction indicators."""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class CategoryScore(BaseModel):
    """Score for a specific category."""
    category: str
    score: float  # 0-100
    previous_score: float | None = None
    trend: TrendDirection = TrendDirection.STABLE
    status: HealthStatus
    issues_count: int = 0
    opportunities_count: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class PlatformReadiness(BaseModel):
    """Readiness score for a specific platform."""
    platform: str
    score: float  # 0-100
    status: HealthStatus
    missing_requirements: list[str] = Field(default_factory=list)
    eligible_products: int | None = None
    total_products: int | None = None


class DashboardMetrics(BaseModel):
    """Complete dashboard metrics."""

    # Overall health
    overall_score: float  # 0-100
    overall_status: HealthStatus
    overall_trend: TrendDirection = TrendDirection.STABLE

    # Category scores
    categories: dict[str, CategoryScore] = Field(default_factory=dict)

    # Platform readiness
    platforms: dict[str, PlatformReadiness] = Field(default_factory=dict)

    # Key stats
    total_issues: int = 0
    critical_issues: int = 0
    total_opportunities: int = 0
    high_priority_opportunities: int = 0

    # Traffic metrics
    traffic_stats: dict[str, Any] = Field(default_factory=dict)

    # Recent activity
    last_audit_date: datetime | None = None
    workflows_run_count: int = 0

    # Alerts
    active_alerts: list[Alert] = Field(default_factory=list)

    # Top recommendations
    top_recommendations: list[Recommendation] = Field(default_factory=list)

    # Generated at
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class DashboardAggregator:
    """
    Aggregates data from all agents and workflows into unified dashboard.

    Provides complete overview of SEO health, trends, and opportunities.
    """

    # Category definitions
    CATEGORIES = {
        "technical": {
            "name": "Technical SEO",
            "agents": ["technical_auditor", "monitoring"],
            "weight": 0.15,
        },
        "content": {
            "name": "Content Quality",
            "agents": ["content_generator", "ai_content_analyzer", "content_decay"],
            "weight": 0.15,
        },
        "ecommerce": {
            "name": "E-commerce",
            "agents": ["ecommerce_seo", "product_feed_analyzer", "visual_search", "conversational_commerce"],
            "weight": 0.20,
        },
        "ai_readiness": {
            "name": "AI Readiness (GEO)",
            "agents": ["geo_analyzer", "ai_visibility_control", "eeat_analyzer"],
            "weight": 0.20,
        },
        "local": {
            "name": "Local SEO",
            "agents": ["local_seo"],
            "weight": 0.10,
        },
        "competitive": {
            "name": "Competitive Position",
            "agents": ["competitor_monitor", "serp_features"],
            "weight": 0.10,
        },
        "authority": {
            "name": "Authority & Trust",
            "agents": ["link_analyzer", "eeat_analyzer"],
            "weight": 0.10,
        },
    }

    # Platform definitions
    PLATFORMS = {
        "google_search": "Google Search",
        "google_shopping": "Google Shopping",
        "chatgpt": "ChatGPT",
        "perplexity": "Perplexity",
        "claude": "Claude",
        "gemini": "Gemini (Bard)",
        "bing": "Bing",
    }

    def __init__(self):
        self.history_store: list[DashboardMetrics] = []

    def aggregate(
        self,
        workflow_results: list[dict[str, Any]],
        agent_results: list[AgentResult] | None = None,
    ) -> DashboardMetrics:
        """
        Aggregate all data into dashboard metrics.

        Args:
            workflow_results: List of recent workflow executions
            agent_results: Optional list of individual agent results

        Returns:
            Complete dashboard metrics
        """
        # Get previous metrics for trend comparison
        previous_metrics = self.history_store[-1] if self.history_store else None

        # Calculate category scores
        categories = self._calculate_category_scores(workflow_results, previous_metrics)

        # Calculate platform readiness
        platforms = self._calculate_platform_readiness(workflow_results)

        # Aggregate recommendations and alerts
        all_recommendations = self._aggregate_recommendations(workflow_results)
        all_alerts = self._aggregate_alerts(workflow_results)

        # Calculate overall score
        overall_score = self._calculate_overall_score(categories)
        overall_status = self._get_health_status(overall_score)
        overall_trend = self._calculate_trend(
            overall_score,
            previous_metrics.overall_score if previous_metrics else None
        )

        # Count issues and opportunities
        critical_issues = sum(1 for a in all_alerts if a.severity == Severity.CRITICAL)
        total_issues = len(all_alerts)
        high_priority_opps = sum(1 for r in all_recommendations if r.priority == Priority.HIGH)
        total_opportunities = len(all_recommendations)

        # Get traffic stats (if available)
        traffic_stats = self._extract_traffic_stats(workflow_results)

        # Build dashboard metrics
        metrics = DashboardMetrics(
            overall_score=round(overall_score, 1),
            overall_status=overall_status,
            overall_trend=overall_trend,
            categories=categories,
            platforms=platforms,
            total_issues=total_issues,
            critical_issues=critical_issues,
            total_opportunities=total_opportunities,
            high_priority_opportunities=high_priority_opps,
            traffic_stats=traffic_stats,
            last_audit_date=datetime.utcnow(),
            workflows_run_count=len(workflow_results),
            active_alerts=sorted(all_alerts, key=lambda a: a.severity.value, reverse=True)[:10],
            top_recommendations=sorted(all_recommendations, key=lambda r: r.priority.value, reverse=True)[:10],
        )

        # Store in history
        self.history_store.append(metrics)

        # Keep only last 90 days
        cutoff = datetime.utcnow() - timedelta(days=90)
        self.history_store = [
            m for m in self.history_store
            if m.generated_at >= cutoff
        ]

        return metrics

    def _calculate_category_scores(
        self,
        workflow_results: list[dict[str, Any]],
        previous_metrics: DashboardMetrics | None,
    ) -> dict[str, CategoryScore]:
        """Calculate scores for each category."""
        categories = {}

        for category_id, category_info in self.CATEGORIES.items():
            # Extract relevant agent results
            agent_scores = []
            issues_count = 0
            opportunities_count = 0

            for workflow in workflow_results:
                for step in workflow.get("step_results", []):
                    agent_type = step.get("agent_type", "")

                    if agent_type in category_info["agents"]:
                        # Extract score from result data
                        result_data = step.get("result", {}).get("data", {})

                        # Try different score field names
                        score = (
                            result_data.get("overall_score") or
                            result_data.get("health_score") or
                            result_data.get("optimization_score") or
                            result_data.get("score") or
                            70.0  # Default if no score
                        )
                        agent_scores.append(score)

                        # Count issues and opportunities
                        issues_count += len(step.get("result", {}).get("alerts", []))
                        opportunities_count += len(step.get("result", {}).get("recommendations", []))

            # Calculate average score
            avg_score = sum(agent_scores) / len(agent_scores) if agent_scores else 0.0

            # Get previous score for trend
            previous_score = None
            if previous_metrics and category_id in previous_metrics.categories:
                previous_score = previous_metrics.categories[category_id].score

            # Determine trend
            trend = self._calculate_trend(avg_score, previous_score)

            # Create category score
            categories[category_id] = CategoryScore(
                category=category_info["name"],
                score=round(avg_score, 1),
                previous_score=previous_score,
                trend=trend,
                status=self._get_health_status(avg_score),
                issues_count=issues_count,
                opportunities_count=opportunities_count,
            )

        return categories

    def _calculate_platform_readiness(
        self,
        workflow_results: list[dict[str, Any]],
    ) -> dict[str, PlatformReadiness]:
        """Calculate readiness scores for each platform."""
        platforms = {}

        # Extract platform scores from relevant agents
        for workflow in workflow_results:
            for step in workflow.get("step_results", []):
                result_data = step.get("result", {}).get("data", {})

                # Check for platform readiness data
                platform_data = (
                    result_data.get("platform_readiness") or
                    result_data.get("platform_compatibility") or
                    result_data.get("ai_platform_compatibility") or
                    {}
                )

                for platform_id, platform_info in platform_data.items():
                    if isinstance(platform_info, dict):
                        score = platform_info.get("score", 0)
                        platforms[platform_id] = PlatformReadiness(
                            platform=self.PLATFORMS.get(platform_id, platform_id.title()),
                            score=round(score, 1),
                            status=self._get_health_status(score),
                            missing_requirements=platform_info.get("missing_required", []),
                            eligible_products=platform_info.get("eligible_products"),
                            total_products=platform_info.get("total_products"),
                        )
                    elif isinstance(platform_info, (int, float)):
                        # Just a score
                        platforms[platform_id] = PlatformReadiness(
                            platform=self.PLATFORMS.get(platform_id, platform_id.title()),
                            score=round(float(platform_info), 1),
                            status=self._get_health_status(float(platform_info)),
                        )

        return platforms

    def _calculate_overall_score(self, categories: dict[str, CategoryScore]) -> float:
        """Calculate weighted overall score from category scores."""
        total_score = 0.0
        total_weight = 0.0

        for category_id, category_score in categories.items():
            if category_id in self.CATEGORIES:
                weight = self.CATEGORIES[category_id]["weight"]
                total_score += category_score.score * weight
                total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def _calculate_trend(self, current: float, previous: float | None) -> TrendDirection:
        """Calculate trend direction."""
        if previous is None:
            return TrendDirection.STABLE

        diff = current - previous

        if abs(diff) < 2:  # Within 2 points = stable
            return TrendDirection.STABLE
        elif diff > 0:
            return TrendDirection.UP
        else:
            return TrendDirection.DOWN

    def _get_health_status(self, score: float) -> HealthStatus:
        """Get health status from score."""
        if score >= 81:
            return HealthStatus.EXCELLENT
        elif score >= 61:
            return HealthStatus.GOOD
        elif score >= 41:
            return HealthStatus.WARNING
        else:
            return HealthStatus.CRITICAL

    def _aggregate_recommendations(self, workflow_results: list[dict[str, Any]]) -> list[Recommendation]:
        """Aggregate all recommendations from workflow results."""
        recommendations = []

        for workflow in workflow_results:
            for step in workflow.get("step_results", []):
                result = step.get("result", {})
                recommendations.extend(result.get("recommendations", []))

        # Deduplicate by title
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec.title not in seen:
                seen.add(rec.title)
                unique_recommendations.append(rec)

        return unique_recommendations

    def _aggregate_alerts(self, workflow_results: list[dict[str, Any]]) -> list[Alert]:
        """Aggregate all alerts from workflow results."""
        alerts = []

        for workflow in workflow_results:
            for step in workflow.get("step_results", []):
                result = step.get("result", {})
                alerts.extend(result.get("alerts", []))

        # Deduplicate by title
        seen = set()
        unique_alerts = []
        for alert in alerts:
            if alert.title not in seen:
                seen.add(alert.title)
                unique_alerts.append(alert)

        return unique_alerts

    def _extract_traffic_stats(self, workflow_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract traffic statistics from results."""
        traffic_stats = {
            "organic_traffic": None,
            "ai_traffic": None,
            "total_traffic": None,
            "traffic_trend": None,
        }

        for workflow in workflow_results:
            for step in workflow.get("step_results", []):
                result_data = step.get("result", {}).get("data", {})

                # Check for traffic data
                if "traffic_stats" in result_data:
                    traffic_stats.update(result_data["traffic_stats"])

                # Check for AI traffic
                if "ai_traffic_stats" in result_data:
                    traffic_stats["ai_traffic"] = result_data["ai_traffic_stats"]

        return traffic_stats

    def get_trend_data(self, days: int = 30) -> dict[str, Any]:
        """
        Get trend data for the last N days.

        Returns data suitable for charting.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_metrics = [
            m for m in self.history_store
            if m.generated_at >= cutoff
        ]

        if not recent_metrics:
            return {"error": "No historical data available"}

        # Build time series data
        dates = [m.generated_at.strftime("%Y-%m-%d") for m in recent_metrics]
        overall_scores = [m.overall_score for m in recent_metrics]

        # Category trends
        category_trends = {}
        for category_id in self.CATEGORIES.keys():
            category_trends[category_id] = [
                m.categories.get(category_id).score if category_id in m.categories else 0
                for m in recent_metrics
            ]

        # Platform trends
        platform_trends = {}
        for platform_id in self.PLATFORMS.keys():
            platform_trends[platform_id] = [
                m.platforms.get(platform_id).score if platform_id in m.platforms else 0
                for m in recent_metrics
            ]

        return {
            "dates": dates,
            "overall_scores": overall_scores,
            "category_trends": category_trends,
            "platform_trends": platform_trends,
            "data_points": len(recent_metrics),
        }

    def get_quick_stats(self) -> dict[str, Any]:
        """Get quick stats for dashboard summary."""
        if not self.history_store:
            return {"error": "No data available"}

        latest = self.history_store[-1]

        # Calculate improvements from last month
        one_month_ago = datetime.utcnow() - timedelta(days=30)
        month_ago_metrics = next(
            (m for m in reversed(self.history_store) if m.generated_at <= one_month_ago),
            None
        )

        score_change = None
        if month_ago_metrics:
            score_change = latest.overall_score - month_ago_metrics.overall_score

        return {
            "overall_score": latest.overall_score,
            "overall_status": latest.overall_status.value,
            "score_change_30d": round(score_change, 1) if score_change else None,
            "critical_issues": latest.critical_issues,
            "total_issues": latest.total_issues,
            "high_priority_opportunities": latest.high_priority_opportunities,
            "total_opportunities": latest.total_opportunities,
            "last_audit": latest.last_audit_date.strftime("%Y-%m-%d %H:%M") if latest.last_audit_date else None,
        }
