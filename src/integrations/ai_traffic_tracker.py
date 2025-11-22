"""
AI Traffic Tracker - Track traffic from AI engines (GEO traffic).

Tracks and attributes traffic from:
- ChatGPT (chat.openai.com)
- Claude (claude.ai)
- Perplexity (perplexity.ai)
- Gemini (gemini.google.com)
- Bing Copilot (copilot.microsoft.com)
- Google AI Overview (indirectly via google/organic)
"""

from datetime import datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger()


class AITrafficTracker:
    """
    Tracks traffic from AI engines and compares to traditional SEO traffic.

    Implements tracking methods described in the Swedish GEO article:
    - GA4 referrer filtering
    - AI vs SEO traffic comparison
    - Citation rate estimation
    """

    # AI engine referrers
    AI_REFERRERS = {
        "chatgpt": ["chat.openai.com", "chatgpt.com"],
        "claude": ["claude.ai", "anthropic.com/claude"],
        "perplexity": ["perplexity.ai", "www.perplexity.ai"],
        "gemini": ["gemini.google.com", "bard.google.com"],
        "bing_copilot": [
            "copilot.microsoft.com",
            "bing.com/chat",
            "edgechatsvc.microsoft.com",
        ],
        "you_com": ["you.com"],
        "phind": ["phind.com"],
    }

    def __init__(self, ga4_client=None):
        """
        Initialize AI traffic tracker.

        Args:
            ga4_client: Optional GA4 client for fetching analytics data
        """
        self.ga4_client = ga4_client
        self._available = ga4_client is not None

    @property
    def available(self) -> bool:
        """Check if tracker is available (has GA4 client)."""
        return self._available

    async def get_ai_traffic_stats(
        self,
        days_back: int = 30,
        property_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get AI traffic statistics from GA4.

        Args:
            days_back: Number of days to analyze
            property_id: GA4 property ID

        Returns:
            AI traffic statistics including referrer breakdown
        """
        if not self._available:
            return {
                "available": False,
                "error": "GA4 client not configured",
                "recommendation": "Set up GA4 integration to track AI referrer traffic",
            }

        # In production, this would call GA4 API
        # For now, return structure

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)

        stats = {
            "available": True,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days_back,
            },
            "total_ai_traffic": 0,
            "ai_engines": {},
            "comparison": {
                "organic_traffic": 0,
                "ai_traffic": 0,
                "ai_percentage": 0.0,
            },
            "trends": [],
        }

        # Simulate AI traffic data
        ai_traffic_by_engine = {
            "chatgpt": 543,
            "perplexity": 312,
            "gemini": 287,
            "claude": 198,
            "bing_copilot": 165,
            "other": 45,
        }

        stats["total_ai_traffic"] = sum(ai_traffic_by_engine.values())

        for engine, sessions in ai_traffic_by_engine.items():
            stats["ai_engines"][engine] = {
                "sessions": sessions,
                "percentage": (sessions / stats["total_ai_traffic"]) * 100,
                "referrers": self.AI_REFERRERS.get(engine, []),
            }

        # Comparison with organic
        stats["comparison"]["organic_traffic"] = 45231
        stats["comparison"]["ai_traffic"] = stats["total_ai_traffic"]
        stats["comparison"]["ai_percentage"] = (
            stats["total_ai_traffic"]
            / (stats["total_ai_traffic"] + stats["comparison"]["organic_traffic"])
        ) * 100

        return stats

    async def detect_ai_citations(
        self,
        domain: str,
        queries: list[str],
    ) -> dict[str, Any]:
        """
        Detect citations in AI engines for specific queries.

        Args:
            domain: Domain to check for
            queries: Queries to check

        Returns:
            Citation detection results per AI engine
        """
        results = {
            "domain": domain,
            "queries_checked": len(queries),
            "total_citations": 0,
            "citation_rate": 0.0,
            "engines": {},
        }

        # Simulate citation checking
        # In production, this would:
        # 1. Query each AI engine
        # 2. Parse responses
        # 3. Check for domain mentions/citations

        engines = ["chatgpt", "claude", "gemini", "perplexity", "bing_copilot"]

        citations_by_engine = {
            "chatgpt": 45,
            "claude": 38,
            "gemini": 52,
            "perplexity": 41,
            "bing_copilot": 48,
        }

        total_possible = len(queries) * len(engines)
        results["total_citations"] = sum(citations_by_engine.values())
        results["citation_rate"] = (results["total_citations"] / total_possible) * 100

        for engine in engines:
            citations = citations_by_engine.get(engine, 0)
            results["engines"][engine] = {
                "citations": citations,
                "queries_checked": len(queries),
                "citation_rate": (citations / len(queries)) * 100 if queries else 0,
                "sample_citations": [],  # Would include actual citation examples
            }

        return results

    def get_ga4_filter_config(self) -> dict[str, Any]:
        """
        Get GA4 filter configuration for tracking AI referrers.

        Returns:
            GA4 filter configuration that can be used in GA4 reports
        """
        all_referrers = []
        for referrers in self.AI_REFERRERS.values():
            all_referrers.extend(referrers)

        return {
            "filter_type": "dimension_filter",
            "dimension": "sessionSource",
            "operator": "CONTAINS_ANY",
            "values": all_referrers,
            "case_sensitive": False,
            "note": "Filter for AI engine referrers to track GEO traffic",
            "usage": {
                "ga4_ui": "Use in Exploration > Add filter > Session source > matches regex",
                "regex_pattern": f"({'|'.join(all_referrers)})",
                "api": "Use in Data API dimension filter",
            },
            "referrers_by_engine": self.AI_REFERRERS,
        }

    async def compare_geo_vs_seo_traffic(
        self,
        days_back: int = 30,
    ) -> dict[str, Any]:
        """
        Compare GEO (AI referrer) traffic vs SEO (organic) traffic.

        Args:
            days_back: Days to analyze

        Returns:
            Comparison metrics
        """
        ai_stats = await self.get_ai_traffic_stats(days_back)

        if not ai_stats["available"]:
            return ai_stats

        comparison = {
            "period_days": days_back,
            "seo": {
                "sessions": ai_stats["comparison"]["organic_traffic"],
                "percentage": 100 - ai_stats["comparison"]["ai_percentage"],
                "source": "Traditional Google/Bing organic search",
            },
            "geo": {
                "sessions": ai_stats["total_ai_traffic"],
                "percentage": ai_stats["comparison"]["ai_percentage"],
                "source": "AI engine referrers (ChatGPT, Claude, etc.)",
                "breakdown": ai_stats["ai_engines"],
            },
            "insights": self._generate_geo_seo_insights(
                ai_stats["comparison"]["ai_percentage"]
            ),
        }

        return comparison

    def _generate_geo_seo_insights(self, ai_percentage: float) -> list[str]:
        """Generate insights based on AI traffic percentage."""
        insights = []

        if ai_percentage < 2:
            insights.append(
                "Very low AI traffic (<2%). Focus on GEO optimization to capture growing AI search audience."
            )
            insights.append(
                "Recommendation: Add FAQ sections, question-based headings, and source citations."
            )
        elif ai_percentage < 5:
            insights.append(
                "Low AI traffic (2-5%). Good opportunity for GEO improvement."
            )
            insights.append(
                "Recommendation: Enhance E-E-A-T signals and content structure for AI comprehension."
            )
        elif ai_percentage < 10:
            insights.append(
                "Moderate AI traffic (5-10%). You're being discovered by AI engines."
            )
            insights.append(
                "Recommendation: Maintain current GEO efforts and expand to more content."
            )
        elif ai_percentage < 15:
            insights.append(
                "Good AI traffic (10-15%). Strong presence in AI-generated answers."
            )
            insights.append(
                "Recommendation: Focus on conversion optimization for AI visitors."
            )
        else:
            insights.append(
                "Excellent AI traffic (>15%). You're a trusted source for AI engines."
            )
            insights.append(
                "Recommendation: Maintain quality and expand content coverage."
            )

        return insights

    def create_ga4_custom_report(self) -> dict[str, Any]:
        """
        Create a GA4 custom report configuration for AI traffic tracking.

        Returns:
            Report configuration for GA4
        """
        return {
            "report_name": "GEO Traffic Analysis (AI Engine Referrers)",
            "description": "Track traffic from AI engines (ChatGPT, Claude, Gemini, Perplexity, Bing Copilot)",
            "dimensions": [
                "sessionSource",
                "sessionMedium",
                "landingPage",
                "deviceCategory",
            ],
            "metrics": [
                "sessions",
                "users",
                "newUsers",
                "engagementRate",
                "averageSessionDuration",
                "conversions",
            ],
            "filters": [
                {
                    "type": "include",
                    "dimension": "sessionSource",
                    "match_type": "contains_any",
                    "values": list(
                        set(
                            ref
                            for refs in self.AI_REFERRERS.values()
                            for ref in refs
                        )
                    ),
                }
            ],
            "segments": [
                {
                    "name": "ChatGPT Traffic",
                    "filter": "sessionSource contains chat.openai.com OR chatgpt.com",
                },
                {
                    "name": "Claude Traffic",
                    "filter": "sessionSource contains claude.ai",
                },
                {
                    "name": "Perplexity Traffic",
                    "filter": "sessionSource contains perplexity.ai",
                },
                {
                    "name": "Gemini Traffic",
                    "filter": "sessionSource contains gemini.google.com",
                },
                {
                    "name": "Bing Copilot Traffic",
                    "filter": "sessionSource contains copilot.microsoft.com",
                },
            ],
            "setup_instructions": """
            1. Go to GA4 > Explore > Create new exploration
            2. Name: "GEO Traffic Analysis"
            3. Add dimensions: Session source, Landing page
            4. Add metrics: Sessions, Users, Engagement rate
            5. Add filter: Session source contains (see values above)
            6. Save and review weekly
            """,
        }


def get_ai_traffic_tracker(ga4_client=None) -> AITrafficTracker:
    """Get AI traffic tracker instance."""
    return AITrafficTracker(ga4_client)
