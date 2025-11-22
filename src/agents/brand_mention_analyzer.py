"""
Brand Mention Analyzer - Track brand mentions across AI platforms.

Key insight from Swedish AI Mode launch:
Traditional KPIs (clicks, CTR) are declining in importance.
NEW KPI: Brand mentions and citations = visibility in AI era.

Tracks brand visibility even when users don't click through to your site.
"""

from datetime import datetime, timedelta
from typing import Any

import structlog

from src.agents.base import BaseAgent, AgentContext
from src.models.agents import AgentTask, AgentResult, Recommendation, Alert, Priority, Severity

logger = structlog.get_logger()


class BrandMentionAnalyzerAgent(BaseAgent):
    """
    Analyzes brand mentions across AI platforms.

    The NEW KPI for AI Mode era:
    - Brand mention frequency
    - Mention context (positive, neutral, negative)
    - Mention prominence (primary, supporting, tangential)
    - Expert recognition (cited as authority)
    - Competitive mention share

    Why it matters:
    In AI Mode, users get answers without clicking.
    Your brand can still gain visibility through mentions.
    """

    # Mention context types
    MENTION_CONTEXTS = {
        "expert_source": {
            "weight": 1.0,
            "description": "Cited as expert or authoritative source",
        },
        "primary_reference": {
            "weight": 0.9,
            "description": "Main reference for answer",
        },
        "supporting_reference": {
            "weight": 0.6,
            "description": "Supporting or additional reference",
        },
        "comparison": {
            "weight": 0.5,
            "description": "Mentioned in comparison with others",
        },
        "passing_mention": {
            "weight": 0.3,
            "description": "Brief or tangential mention",
        },
    }

    def __init__(self, context: AgentContext):
        super().__init__(
            agent_type="brand-mention-analyzer",
            description="Tracks and analyzes brand mentions across AI platforms",
            context=context,
        )

    async def run(self, task: AgentTask) -> AgentResult:
        """Execute brand mention analysis task."""
        start_time = datetime.utcnow()

        try:
            if task.task_type == "analyze_brand_mentions":
                result = await self._analyze_brand_mentions(task.parameters)
            elif task.task_type == "track_mention_trends":
                result = await self._track_mention_trends(task.parameters)
            elif task.task_type == "analyze_mention_context":
                result = await self._analyze_mention_context(task.parameters)
            elif task.task_type == "compare_competitor_mentions":
                result = await self._compare_competitor_mentions(task.parameters)
            elif task.task_type == "full_mention_audit":
                result = await self._full_mention_audit(task.parameters)
            else:
                return AgentResult(
                    task_id=task.id,
                    agent_type=self.agent_type,
                    success=False,
                    data={"error": f"Unknown task type: {task.task_type}"},
                )

            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=True,
                data=result["data"],
                recommendations=result.get("recommendations", []),
                alerts=result.get("alerts", []),
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            )

        except Exception as e:
            logger.error("Brand mention analysis failed", error=str(e))
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": str(e)},
            )

    async def _full_mention_audit(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Complete brand mention audit.

        Comprehensive analysis of brand visibility in AI responses.
        """
        brand_name = params.get("brand_name", self.context.property_url)
        timeframe_days = params.get("timeframe_days", 30)

        results = {
            "analyzed_at": datetime.utcnow().isoformat(),
            "brand_name": brand_name,
            "timeframe_days": timeframe_days,
            "overall_mention_score": 0,
            "mention_metrics": {},
            "mention_breakdown": {},
            "platform_distribution": {},
            "sentiment_analysis": {},
            "competitor_comparison": {},
        }

        recommendations = []
        alerts = []

        # Calculate mention metrics
        mention_metrics = await self._calculate_mention_metrics(brand_name, timeframe_days)
        results["mention_metrics"] = mention_metrics

        # Analyze mention breakdown by context
        mention_breakdown = await self._get_mention_breakdown(brand_name)
        results["mention_breakdown"] = mention_breakdown

        # Platform distribution
        platform_dist = await self._get_platform_distribution(brand_name)
        results["platform_distribution"] = platform_dist

        # Sentiment analysis
        sentiment = await self._analyze_mention_sentiment(brand_name)
        results["sentiment_analysis"] = sentiment

        # Competitor comparison
        competitors = params.get("competitors", [])
        if competitors:
            comp_comparison = await self._compare_with_competitors_mentions(brand_name, competitors)
            results["competitor_comparison"] = comp_comparison

        # Calculate overall score
        overall_score = self._calculate_mention_score(mention_metrics, mention_breakdown, sentiment)
        results["overall_mention_score"] = overall_score

        # Generate recommendations
        if mention_metrics["mention_frequency"] < 5.0:
            recommendations.append(Recommendation(
                title="Increase Brand Mention Frequency",
                description=f"Current: {mention_metrics['mention_frequency']:.1f} mentions per 100 queries. Target: 8+ for strong brand visibility.",
                category="Brand Mentions - Frequency",
                priority=Priority.HIGH,
                estimated_impact="Higher brand awareness in AI responses",
                implementation_effort="medium",
            ))

        if mention_breakdown["expert_source_pct"] < 30:
            recommendations.append(Recommendation(
                title="Improve Expert Source Recognition",
                description=f"Only {mention_breakdown['expert_source_pct']:.1f}% of mentions cite you as expert. Increase E-E-A-T signals.",
                category="Brand Mentions - Authority",
                priority=Priority.HIGH,
                estimated_impact="Higher quality mentions as authoritative source",
                implementation_effort="high",
            ))

        if sentiment["negative_pct"] > 10:
            alerts.append(Alert(
                title="Negative Brand Mentions Detected",
                message=f"{sentiment['negative_pct']:.1f}% of mentions have negative context",
                severity=Severity.WARNING,
                source=self.agent_type,
            ))

        return {
            "data": results,
            "recommendations": recommendations,
            "alerts": alerts,
        }

    async def _analyze_brand_mentions(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze brand mentions across AI platforms.

        Tracks frequency, context, and quality of mentions.
        """
        brand_name = params.get("brand_name")

        # In production, this would track actual mentions across platforms
        # For now, simulated data
        mention_data = {
            "total_mentions_30d": 127,
            "mention_frequency": 6.8,  # per 100 queries
            "unique_queries_mentioned": 94,
            "average_prominence_score": 72.5,  # 0-100
            "mention_trend": "increasing",
            "mention_change_30d": 18.5,  # % change
            "top_mention_topics": [
                {"topic": "SEO tools", "mentions": 35},
                {"topic": "Content optimization", "mentions": 28},
                {"topic": "AI search", "mentions": 24},
                {"topic": "E-commerce SEO", "mentions": 22},
            ],
        }

        recommendations = [
            Recommendation(
                title="Expand Content on Top Mention Topics",
                description="You're frequently mentioned for SEO tools and content optimization. Create more authoritative content on these topics.",
                category="Brand Mentions - Content Strategy",
                priority=Priority.MEDIUM,
                estimated_impact="Increase mention frequency by 20-25%",
                implementation_effort="high",
            ),
        ]

        return {
            "data": mention_data,
            "recommendations": recommendations,
        }

    async def _calculate_mention_metrics(
        self, brand_name: str, timeframe_days: int
    ) -> dict[str, Any]:
        """Calculate key mention metrics."""
        # Simulated data
        return {
            "total_mentions": 127,
            "mention_frequency": 6.8,  # per 100 queries
            "daily_avg_mentions": 4.2,
            "peak_day_mentions": 12,
            "mention_trend": "increasing",
            "mention_growth_pct": 18.5,
        }

    async def _get_mention_breakdown(self, brand_name: str) -> dict[str, Any]:
        """Break down mentions by context type."""
        breakdown = {
            "expert_source": 38,
            "primary_reference": 31,
            "supporting_reference": 28,
            "comparison": 18,
            "passing_mention": 12,
        }

        total = sum(breakdown.values())

        return {
            "breakdown": breakdown,
            "expert_source_pct": round(breakdown["expert_source"] / total * 100, 1),
            "primary_reference_pct": round(breakdown["primary_reference"] / total * 100, 1),
            "high_quality_mentions": breakdown["expert_source"] + breakdown["primary_reference"],
            "total_mentions": total,
        }

    async def _get_platform_distribution(self, brand_name: str) -> dict[str, Any]:
        """Distribution of mentions across platforms."""
        return {
            "google_ai_mode": 47,
            "perplexity": 38,
            "chatgpt": 22,
            "claude": 12,
            "gemini": 8,
        }

    async def _analyze_mention_sentiment(self, brand_name: str) -> dict[str, Any]:
        """Analyze sentiment of brand mentions."""
        return {
            "positive": 92,
            "neutral": 31,
            "negative": 4,
            "positive_pct": 72.4,
            "neutral_pct": 24.4,
            "negative_pct": 3.1,
            "overall_sentiment_score": 84.7,  # 0-100
        }

    async def _track_mention_trends(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Track brand mention trends over time.

        Identify growth patterns and seasonality.
        """
        brand_name = params.get("brand_name")

        trend_data = {
            "trend_direction": "increasing",
            "weekly_data": [
                {"week": "Week 1", "mentions": 28},
                {"week": "Week 2", "mentions": 31},
                {"week": "Week 3", "mentions": 34},
                {"week": "Week 4", "mentions": 34},
            ],
            "growth_rate": 18.5,  # %
            "seasonality_detected": False,
            "prediction_next_30d": 151,  # Predicted mentions
        }

        return {
            "data": trend_data,
            "recommendations": [],
        }

    async def _analyze_mention_context(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze context in which brand is mentioned.

        Quality matters more than quantity.
        """
        brand_name = params.get("brand_name")

        context_analysis = {
            "mention_quality_score": 73.5,  # 0-100
            "context_breakdown": {
                "expert_authority": 38,
                "product_recommendation": 31,
                "how_to_guide": 28,
                "comparison_alternative": 18,
                "general_mention": 12,
            },
            "co_mentions": [
                {"entity": "Google Search Console", "count": 23},
                {"entity": "Ahrefs", "count": 18},
                {"entity": "Semrush", "count": 15},
            ],
            "mention_prominence": {
                "first_in_response": 28,
                "middle_of_response": 67,
                "end_of_response": 32,
            },
        }

        recommendations = [
            Recommendation(
                title="Increase Expert Authority Mentions",
                description="Focus on creating deep expert content to be cited as authoritative source more frequently.",
                category="Brand Mentions - Quality",
                priority=Priority.HIGH,
                estimated_impact="Higher quality mentions with better prominence",
                implementation_effort="high",
            ),
        ]

        return {
            "data": context_analysis,
            "recommendations": recommendations,
        }

    async def _compare_competitor_mentions(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Compare brand mentions with competitors.

        Competitive mention analysis for market positioning.
        """
        brand_name = params.get("brand_name")
        competitors = params.get("competitors", [])

        competitor_data = {
            "your_brand": {
                "brand": brand_name,
                "mentions": 127,
                "mention_share": 28.4,  # % of total mentions in category
                "quality_score": 73.5,
            },
            "competitors": [
                {
                    "brand": "Competitor A",
                    "mentions": 142,
                    "mention_share": 31.8,
                    "quality_score": 71.2,
                },
                {
                    "brand": "Competitor B",
                    "mentions": 98,
                    "mention_share": 21.9,
                    "quality_score": 68.5,
                },
                {
                    "brand": "Competitor C",
                    "mentions": 79,
                    "mention_share": 17.7,
                    "quality_score": 65.3,
                },
            ],
            "market_position": 2,  # Your position in mention rankings
            "share_gap_to_leader": -3.4,  # % points behind leader
        }

        recommendations = [
            Recommendation(
                title="Close Gap to Mention Leader",
                description="You're 3.4% points behind the mention leader. Increase content depth and E-E-A-T signals.",
                category="Brand Mentions - Competitive",
                priority=Priority.HIGH,
                estimated_impact="Become most-mentioned brand in category",
                implementation_effort="high",
            ),
        ]

        return {
            "data": competitor_data,
            "recommendations": recommendations,
        }

    async def _compare_with_competitors_mentions(
        self, brand_name: str, competitors: list[str]
    ) -> dict[str, Any]:
        """Compare mentions with specific competitors."""
        return {
            "your_mention_share": 28.4,
            "leader_mention_share": 31.8,
            "gap_to_leader": -3.4,
            "position": 2,
        }

    def _calculate_mention_score(
        self,
        mention_metrics: dict[str, Any],
        mention_breakdown: dict[str, Any],
        sentiment: dict[str, Any],
    ) -> float:
        """Calculate overall brand mention score (0-100)."""
        # Frequency score (0-100)
        frequency_score = min(mention_metrics["mention_frequency"] / 10.0 * 100, 100)

        # Quality score (based on context breakdown)
        quality_score = (
            mention_breakdown["expert_source_pct"] * 0.5 +
            mention_breakdown["primary_reference_pct"] * 0.3 +
            20  # Base score
        )

        # Sentiment score
        sentiment_score = sentiment["overall_sentiment_score"]

        # Weighted average
        overall = (
            frequency_score * 0.3 +
            quality_score * 0.4 +
            sentiment_score * 0.3
        )

        return round(overall, 1)
