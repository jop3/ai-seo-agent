"""
AI Mode Tracker Agent - Track visibility in Google AI Mode and AI search platforms.

Monitors citations, brand mentions, and source attribution across:
- Google AI Mode (Sweden, Nordic markets, Europe)
- Google AI Overviews
- ChatGPT
- Perplexity
- Claude
- Gemini

Key insight from Swedish launch: Traditional KPIs (clicks, CTR) losing relevance.
New KPIs: Citations, brand mentions, expert recognition.
"""

from datetime import datetime, timedelta
from typing import Any

import structlog

from src.agents.base import BaseAgent, AgentContext
from src.models.agents import AgentTask, AgentResult, Recommendation, Alert, Priority, Severity

logger = structlog.get_logger()


class AIModeTrackerAgent(BaseAgent):
    """
    Tracks visibility in Google AI Mode and other AI search platforms.

    Google AI Mode launched in Sweden (Oct 8, 2025) and Nordic markets.
    This represents a fundamental shift: from clicks to citations.

    Traditional metrics (declining):
    - Clicks
    - CTR
    - Impressions

    New metrics (critical):
    - Citation frequency
    - Brand mention count
    - Source attribution rate
    - Expert recognition score
    - AI visibility share
    """

    # AI platforms with search/answer features
    AI_PLATFORMS = {
        "google_ai_mode": {
            "name": "Google AI Mode",
            "markets": ["se", "no", "dk", "fi", "de", "fr", "uk"],
            "launch_date": "2025-10-08",
        },
        "google_ai_overviews": {
            "name": "Google AI Overviews",
            "markets": ["us", "uk", "global"],
            "launch_date": "2024-05-14",
        },
        "chatgpt": {
            "name": "ChatGPT",
            "markets": ["global"],
            "launch_date": "2022-11-30",
        },
        "perplexity": {
            "name": "Perplexity",
            "markets": ["global"],
            "launch_date": "2022-12-07",
        },
        "claude": {
            "name": "Claude",
            "markets": ["global"],
            "launch_date": "2023-03-14",
        },
        "gemini": {
            "name": "Gemini (Bard)",
            "markets": ["global"],
            "launch_date": "2023-03-21",
        },
    }

    def __init__(self, context: AgentContext):
        super().__init__(
            agent_type="ai-mode-tracker",
            description="Tracks visibility and citations in Google AI Mode and AI search platforms",
            context=context,
        )

    async def run(self, task: AgentTask) -> AgentResult:
        """Execute AI Mode tracking task."""
        start_time = datetime.utcnow()

        try:
            if task.task_type == "track_ai_mode_citations":
                result = await self._track_ai_mode_citations(task.parameters)
            elif task.task_type == "analyze_citation_patterns":
                result = await self._analyze_citation_patterns(task.parameters)
            elif task.task_type == "compare_platforms":
                result = await self._compare_platforms(task.parameters)
            elif task.task_type == "track_competitor_citations":
                result = await self._track_competitor_citations(task.parameters)
            elif task.task_type == "full_ai_mode_audit":
                result = await self._full_ai_mode_audit(task.parameters)
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
            logger.error("AI Mode tracking failed", error=str(e))
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": str(e)},
            )

    async def _full_ai_mode_audit(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Complete AI Mode visibility audit.

        Tracks citations across all AI platforms and provides comprehensive analysis.
        """
        domain = params.get("domain", self.context.property_url)
        market = params.get("market", "se")  # Default to Swedish market

        results = {
            "analyzed_at": datetime.utcnow().isoformat(),
            "domain": domain,
            "market": market,
            "overall_ai_visibility_score": 0,
            "platforms": {},
            "citation_metrics": {},
            "competitor_comparison": {},
            "trend_analysis": {},
        }

        recommendations = []
        alerts = []

        # Track citations per platform
        platforms_data = {}
        for platform_id, platform_info in self.AI_PLATFORMS.items():
            if market in platform_info["markets"] or "global" in platform_info["markets"]:
                platform_data = await self._track_platform_citations(domain, platform_id, market)
                platforms_data[platform_id] = platform_data

        results["platforms"] = platforms_data

        # Calculate citation metrics
        citation_metrics = self._calculate_citation_metrics(platforms_data)
        results["citation_metrics"] = citation_metrics

        # Competitor comparison
        competitors = params.get("competitors", [])
        if competitors:
            comp_comparison = await self._compare_with_competitors(domain, competitors, market)
            results["competitor_comparison"] = comp_comparison

        # Calculate overall score
        overall_score = self._calculate_overall_ai_visibility(platforms_data, citation_metrics)
        results["overall_ai_visibility_score"] = overall_score

        # Generate recommendations
        if citation_metrics["citation_frequency"] < 2.0:
            recommendations.append(Recommendation(
                title="Increase AI Mode Citation Frequency",
                description=f"Current citation frequency is {citation_metrics['citation_frequency']:.1f} per 100 queries. Target: 3+ citations per 100 queries.",
                category="AI Mode - Visibility",
                priority=Priority.HIGH,
                estimated_impact="Higher visibility in Google AI Mode responses",
                implementation_effort="medium",
            ))

        if citation_metrics["source_attribution_rate"] < 15.0:
            recommendations.append(Recommendation(
                title="Improve Source Attribution Rate",
                description=f"Only {citation_metrics['source_attribution_rate']:.1f}% of AI responses cite your content. Target: 20%+.",
                category="AI Mode - Attribution",
                priority=Priority.HIGH,
                estimated_impact="More frequent citations as expert source",
                implementation_effort="medium",
            ))

        # Alerts for declining visibility
        if citation_metrics.get("citation_trend") == "declining":
            alerts.append(Alert(
                title="Declining AI Mode Citations",
                message=f"Citations in AI Mode down {citation_metrics.get('citation_change_pct', 0):.1f}% over last 30 days",
                severity=Severity.WARNING,
                source=self.agent_type,
                affected_urls=[domain],
            ))

        return {
            "data": results,
            "recommendations": recommendations,
            "alerts": alerts,
        }

    async def _track_ai_mode_citations(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Track citations in Google AI Mode specifically.

        Since Search Console doesn't show AI Mode data separately,
        we use alternative tracking methods.
        """
        domain = params.get("domain")
        market = params.get("market", "se")

        # In production, this would:
        # 1. Monitor brand mentions in AI Mode responses
        # 2. Track citation patterns
        # 3. Analyze source attribution
        # 4. Compare with competitors

        ai_mode_data = {
            "market": market,
            "citation_count_30d": 47,
            "citation_frequency": 3.2,  # per 100 queries
            "source_attribution_rate": 18.5,  # % of responses citing you
            "average_citation_position": 2.3,  # position in response (1=first)
            "citation_topics": [
                {"topic": "SEO optimization", "citations": 15},
                {"topic": "Content strategy", "citations": 12},
                {"topic": "AI search trends", "citations": 10},
                {"topic": "E-commerce SEO", "citations": 10},
            ],
            "competing_sources": [
                {"domain": "competitor1.se", "citations": 52},
                {"domain": "competitor2.se", "citations": 38},
                {"domain": "competitor3.se", "citations": 29},
            ],
        }

        recommendations = []

        # Check if launch is recent
        if market == "se":
            recommendations.append(Recommendation(
                title="Optimize for Swedish AI Mode Launch",
                description="Google AI Mode launched in Sweden on Oct 8, 2025. Early optimization gives competitive advantage.",
                category="AI Mode - Market Opportunity",
                priority=Priority.HIGH,
                estimated_impact="Early mover advantage in Swedish market",
                implementation_effort="medium",
            ))

        return {
            "data": ai_mode_data,
            "recommendations": recommendations,
        }

    async def _track_platform_citations(
        self, domain: str, platform_id: str, market: str
    ) -> dict[str, Any]:
        """Track citations for a specific AI platform."""
        # Simulated data - in production, this would use actual tracking
        platform_citations = {
            "platform": self.AI_PLATFORMS[platform_id]["name"],
            "citation_count": 0,
            "citation_frequency": 0.0,
            "attribution_rate": 0.0,
            "expert_recognition_score": 0,
        }

        # Simulate different platform performance
        if platform_id == "google_ai_mode":
            platform_citations.update({
                "citation_count": 47,
                "citation_frequency": 3.2,
                "attribution_rate": 18.5,
                "expert_recognition_score": 72,
            })
        elif platform_id == "chatgpt":
            platform_citations.update({
                "citation_count": 31,
                "citation_frequency": 2.1,
                "attribution_rate": 12.3,
                "expert_recognition_score": 68,
            })
        elif platform_id == "perplexity":
            platform_citations.update({
                "citation_count": 58,
                "citation_frequency": 4.5,
                "attribution_rate": 24.2,
                "expert_recognition_score": 81,
            })

        return platform_citations

    async def _analyze_citation_patterns(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze patterns in how and when you're cited.

        Insights:
        - Which topics you're cited for
        - Time-based patterns
        - Citation context (primary source, supporting source, etc.)
        """
        citation_patterns = {
            "top_citation_topics": [
                {"topic": "SEO best practices", "citations": 15, "trend": "up"},
                {"topic": "AI search optimization", "citations": 12, "trend": "up"},
                {"topic": "Content strategy", "citations": 10, "trend": "stable"},
                {"topic": "E-commerce SEO", "citations": 10, "trend": "up"},
            ],
            "citation_context": {
                "primary_source": 28,  # Cited as main/primary source
                "supporting_source": 19,  # Cited as additional/supporting
                "expert_quote": 12,  # Cited for expert opinion
            },
            "time_patterns": {
                "weekday_avg": 2.8,
                "weekend_avg": 1.2,
                "peak_hours": ["09:00-11:00", "14:00-16:00"],
            },
        }

        recommendations = [
            Recommendation(
                title="Expand Coverage of High-Citation Topics",
                description="You're frequently cited for SEO and AI search. Create more in-depth content on these topics.",
                category="AI Mode - Content Strategy",
                priority=Priority.MEDIUM,
                estimated_impact="Increase citation frequency by 20-30%",
                implementation_effort="high",
            ),
        ]

        return {
            "data": citation_patterns,
            "recommendations": recommendations,
        }

    async def _compare_platforms(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Compare visibility across different AI platforms.

        Identify which platforms cite you most and where to improve.
        """
        platform_comparison = {
            "platforms": {
                "perplexity": {
                    "citations": 58,
                    "frequency": 4.5,
                    "attribution_rate": 24.2,
                    "strength": "highest",
                },
                "google_ai_mode": {
                    "citations": 47,
                    "frequency": 3.2,
                    "attribution_rate": 18.5,
                    "strength": "strong",
                },
                "chatgpt": {
                    "citations": 31,
                    "frequency": 2.1,
                    "attribution_rate": 12.3,
                    "strength": "moderate",
                },
                "gemini": {
                    "citations": 22,
                    "frequency": 1.8,
                    "attribution_rate": 9.7,
                    "strength": "weak",
                },
            },
            "strongest_platform": "perplexity",
            "weakest_platform": "gemini",
            "overall_trend": "improving",
        }

        recommendations = [
            Recommendation(
                title="Optimize for ChatGPT and Gemini",
                description="These platforms cite you less frequently. Optimize content format and structure for better ChatGPT/Gemini visibility.",
                category="AI Mode - Platform Optimization",
                priority=Priority.MEDIUM,
                estimated_impact="15-20% increase in citations from these platforms",
                implementation_effort="medium",
            ),
        ]

        return {
            "data": platform_comparison,
            "recommendations": recommendations,
        }

    async def _track_competitor_citations(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Track competitor citations to understand competitive position.

        Key insight from Swedish article: You don't need to rank top 3 to be cited.
        """
        domain = params.get("domain")
        competitors = params.get("competitors", [])

        competitor_analysis = {
            "your_domain": {
                "domain": domain,
                "citations": 47,
                "citation_frequency": 3.2,
                "visibility_share": 23.1,  # % of total citations in category
            },
            "competitors": [
                {
                    "domain": "competitor1.se",
                    "citations": 52,
                    "citation_frequency": 3.5,
                    "visibility_share": 25.6,
                    "organic_ranking_avg": 2.3,  # Traditional ranking
                },
                {
                    "domain": "competitor2.se",
                    "citations": 38,
                    "citation_frequency": 2.6,
                    "visibility_share": 18.7,
                    "organic_ranking_avg": 4.1,  # Ranks lower but still cited
                },
                {
                    "domain": "competitor3.se",
                    "citations": 29,
                    "citation_frequency": 2.0,
                    "visibility_share": 14.3,
                    "organic_ranking_avg": 1.8,  # Ranks high but fewer citations
                },
            ],
            "insights": [
                "Competitor2 ranks position 4 on average but gets significant AI citations",
                "Competitor3 ranks position 2 but gets fewer citations than you",
                "AI Mode favors depth and expertise over traditional ranking",
            ],
        }

        recommendations = [
            Recommendation(
                title="Increase Visibility Share",
                description=f"Your visibility share is 23.1%. Top competitor has 25.6%. Focus on expert content to increase share.",
                category="AI Mode - Competitive",
                priority=Priority.HIGH,
                estimated_impact="Become leading cited source in category",
                implementation_effort="high",
            ),
        ]

        return {
            "data": competitor_analysis,
            "recommendations": recommendations,
        }

    async def _compare_with_competitors(
        self, domain: str, competitors: list[str], market: str
    ) -> dict[str, Any]:
        """Compare citation performance with competitors."""
        # Simulated competitor data
        return {
            "your_visibility_share": 23.1,
            "market_leader_share": 25.6,
            "gap_to_leader": -2.5,
            "total_competitors_tracked": len(competitors),
        }

    def _calculate_citation_metrics(self, platforms_data: dict[str, Any]) -> dict[str, Any]:
        """Calculate aggregate citation metrics across platforms."""
        total_citations = sum(p.get("citation_count", 0) for p in platforms_data.values())
        avg_frequency = sum(p.get("citation_frequency", 0) for p in platforms_data.values()) / len(platforms_data) if platforms_data else 0
        avg_attribution = sum(p.get("attribution_rate", 0) for p in platforms_data.values()) / len(platforms_data) if platforms_data else 0

        return {
            "total_citations_30d": total_citations,
            "citation_frequency": round(avg_frequency, 2),
            "source_attribution_rate": round(avg_attribution, 2),
            "platforms_tracked": len(platforms_data),
            "citation_trend": "improving",  # Would be calculated from historical data
            "citation_change_pct": 12.5,  # % change vs. previous period
        }

    def _calculate_overall_ai_visibility(
        self, platforms_data: dict[str, Any], citation_metrics: dict[str, Any]
    ) -> float:
        """Calculate overall AI visibility score (0-100)."""
        # Weighted scoring
        citation_freq_score = min(citation_metrics["citation_frequency"] / 5.0 * 100, 100)
        attribution_score = min(citation_metrics["source_attribution_rate"] / 30.0 * 100, 100)
        platform_coverage_score = (len(platforms_data) / len(self.AI_PLATFORMS)) * 100

        # Weighted average
        overall = (
            citation_freq_score * 0.4 +
            attribution_score * 0.4 +
            platform_coverage_score * 0.2
        )

        return round(overall, 1)
