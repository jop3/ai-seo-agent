"""
Content Decay Agent - Identifies declining content that needs refresh.
"""

from datetime import datetime, timedelta
from typing import Any

import structlog

from src.agents.base import BaseAgent, AgentContext
from src.core.errors import AgentError, ErrorCode
from src.models.agents import (
    AgentTask, AgentResult, AgentType, Recommendation, Alert, Priority, Severity
)

logger = structlog.get_logger()


class ContentDecayAgent(BaseAgent):
    """
    Identifies content showing signs of decay and prioritizes refresh.

    Capabilities:
    - Detect traffic decline patterns
    - Identify ranking drops
    - Find content losing AIO citations
    - Analyze content freshness
    - Prioritize content refresh queue
    """

    agent_type = AgentType.CONTENT_DECAY

    def __init__(self, context: AgentContext):
        self.context = context
        self.logger = logger.bind(agent="content-decay")

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute content decay analysis task."""
        task_handlers = {
            "detect_decay": self._detect_decay,
            "analyze_traffic_trends": self._analyze_traffic_trends,
            "find_aio_losers": self._find_aio_losers,
            "check_content_freshness": self._check_content_freshness,
            "prioritize_refresh": self._prioritize_refresh,
        }

        handler = task_handlers.get(task.task_type)
        if not handler:
            raise AgentError(
                f"Unknown task type: {task.task_type}",
                agent_type="content-decay",
                task_type=task.task_type,
                code=ErrorCode.VALIDATION_ERROR,
            )

        result = await handler(task.parameters)

        return AgentResult(
            task_id=task.id,
            agent_type=self.agent_type,
            success=True,
            data=result["data"],
            recommendations=result.get("recommendations", []),
            alerts=result.get("alerts", []),
        )

    async def _detect_decay(self, params: dict[str, Any]) -> dict[str, Any]:
        """Detect content showing decay signals (traffic/ranking drops)."""
        days_back = params.get("days_back", 90)
        min_decline_pct = params.get("min_decline_pct", 20)

        if not self.context.gsc_client:
            return {"data": {"error": "GSC client not configured"}, "recommendations": []}

        recommendations = []
        alerts = []
        decaying_pages = []

        try:
            # Get performance data for comparison periods
            end_date = datetime.now().date()
            mid_date = end_date - timedelta(days=days_back // 2)
            start_date = end_date - timedelta(days=days_back)

            # Current period (recent half)
            current_data = await self.context.gsc_client.get_performance(
                property_url=self.context.property_url,
                start_date=mid_date.isoformat(),
                end_date=end_date.isoformat(),
                dimensions=["page"],
            )

            # Previous period (older half)
            previous_data = await self.context.gsc_client.get_performance(
                property_url=self.context.property_url,
                start_date=start_date.isoformat(),
                end_date=mid_date.isoformat(),
                dimensions=["page"],
            )

            # Build comparison
            current_by_page = {
                row.get("page", ""): {
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "position": row.get("position", 0),
                }
                for row in current_data.get("rows", [])
            }

            previous_by_page = {
                row.get("page", ""): {
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "position": row.get("position", 0),
                }
                for row in previous_data.get("rows", [])
            }

            # Find decaying pages
            for page, prev_metrics in previous_by_page.items():
                curr_metrics = current_by_page.get(page, {"clicks": 0, "impressions": 0, "position": 100})

                if prev_metrics["clicks"] > 10:  # Minimum threshold
                    click_change = (
                        (curr_metrics["clicks"] - prev_metrics["clicks"]) / prev_metrics["clicks"] * 100
                    )
                    impression_change = (
                        (curr_metrics["impressions"] - prev_metrics["impressions"]) / max(prev_metrics["impressions"], 1) * 100
                    )
                    position_change = curr_metrics["position"] - prev_metrics["position"]

                    # Detect significant decline
                    if click_change <= -min_decline_pct:
                        decay_score = self._calculate_decay_score(
                            click_change, impression_change, position_change, prev_metrics["clicks"]
                        )

                        decaying_pages.append({
                            "page": page,
                            "click_change_pct": round(click_change, 1),
                            "impression_change_pct": round(impression_change, 1),
                            "position_change": round(position_change, 1),
                            "previous_clicks": prev_metrics["clicks"],
                            "current_clicks": curr_metrics["clicks"],
                            "decay_score": decay_score,
                            "decay_type": self._classify_decay_type(click_change, impression_change, position_change),
                        })

            # Sort by decay score (worst first)
            decaying_pages.sort(key=lambda x: x["decay_score"], reverse=True)

            # Generate recommendations
            if decaying_pages:
                high_priority = [p for p in decaying_pages if p["decay_score"] >= 70]
                recommendations.append(Recommendation(
                    title=f"Found {len(decaying_pages)} pages with content decay",
                    description=f"{len(high_priority)} require urgent attention. Review and refresh these pages.",
                    priority=Priority.HIGH if high_priority else Priority.MEDIUM,
                    category="content_decay",
                    estimated_impact="high" if high_priority else "medium",
                    data={"top_decaying": [p["page"] for p in decaying_pages[:5]]},
                ))

                # Alert for severe decay
                severe_decay = [p for p in decaying_pages if p["click_change_pct"] <= -50]
                if severe_decay:
                    alerts.append(Alert(
                        title=f"{len(severe_decay)} pages lost 50%+ traffic",
                        message="Urgent content review needed for severely declining pages",
                        severity=Severity.ERROR,
                        source="content-decay",
                        data={"pages": [p["page"] for p in severe_decay[:3]]},
                    ))

        except Exception as e:
            self.logger.error("Decay detection failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}

        return {
            "data": {
                "analysis_period_days": days_back,
                "pages_analyzed": len(previous_by_page),
                "decaying_pages_found": len(decaying_pages),
                "decaying_pages": decaying_pages[:50],  # Top 50
            },
            "recommendations": recommendations,
            "alerts": alerts,
        }

    def _calculate_decay_score(
        self,
        click_change: float,
        impression_change: float,
        position_change: float,
        previous_clicks: int,
    ) -> int:
        """Calculate decay severity score (0-100)."""
        score = 0

        # Click decline weight (most important)
        if click_change <= -50:
            score += 40
        elif click_change <= -30:
            score += 30
        elif click_change <= -20:
            score += 20

        # Impression decline
        if impression_change <= -40:
            score += 20
        elif impression_change <= -20:
            score += 10

        # Position drop
        if position_change >= 10:
            score += 20
        elif position_change >= 5:
            score += 10

        # Volume bonus (higher traffic = more important)
        if previous_clicks >= 100:
            score += 20
        elif previous_clicks >= 50:
            score += 10

        return min(score, 100)

    def _classify_decay_type(
        self,
        click_change: float,
        impression_change: float,
        position_change: float,
    ) -> str:
        """Classify the type of content decay."""
        if position_change >= 5 and impression_change <= -20:
            return "ranking_drop"  # Lost rankings
        elif impression_change <= -30 and position_change < 3:
            return "visibility_loss"  # Search demand dropped or AIO impact
        elif click_change <= -30 and impression_change > -10:
            return "ctr_decline"  # Impressions stable but CTR dropped
        else:
            return "general_decline"

    async def _analyze_traffic_trends(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze traffic trends to identify patterns."""
        pages = params.get("pages", [])
        days_back = params.get("days_back", 180)

        if not self.context.gsc_client:
            return {"data": {"error": "GSC client not configured"}, "recommendations": []}

        trends = []

        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)

            for page in pages[:20]:  # Limit to 20 pages
                page_data = await self.context.gsc_client.get_performance(
                    property_url=self.context.property_url,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    dimensions=["date"],
                    dimension_filter={"dimension": "page", "expression": page},
                )

                if page_data.get("rows"):
                    daily_data = sorted(page_data["rows"], key=lambda x: x.get("date", ""))

                    # Calculate trend
                    trend = self._calculate_trend(daily_data)
                    trends.append({
                        "page": page,
                        "trend_direction": trend["direction"],
                        "trend_strength": trend["strength"],
                        "peak_date": trend.get("peak_date"),
                        "decline_start": trend.get("decline_start"),
                    })

        except Exception as e:
            self.logger.error("Traffic trend analysis failed", error=str(e))

        return {
            "data": {
                "pages_analyzed": len(trends),
                "trends": trends,
            },
            "recommendations": [],
        }

    def _calculate_trend(self, daily_data: list[dict]) -> dict[str, Any]:
        """Calculate trend from daily data."""
        if len(daily_data) < 14:
            return {"direction": "insufficient_data", "strength": 0}

        # Split into first and last quarter
        quarter = len(daily_data) // 4
        first_quarter_clicks = sum(d.get("clicks", 0) for d in daily_data[:quarter])
        last_quarter_clicks = sum(d.get("clicks", 0) for d in daily_data[-quarter:])

        if first_quarter_clicks == 0:
            return {"direction": "new_content", "strength": 0}

        change_pct = (last_quarter_clicks - first_quarter_clicks) / first_quarter_clicks * 100

        if change_pct >= 20:
            direction = "growing"
        elif change_pct <= -20:
            direction = "declining"
        else:
            direction = "stable"

        # Find peak
        max_clicks = max(d.get("clicks", 0) for d in daily_data)
        peak_date = next(
            (d.get("date") for d in daily_data if d.get("clicks", 0) == max_clicks),
            None
        )

        return {
            "direction": direction,
            "strength": abs(change_pct),
            "peak_date": peak_date,
        }

    async def _find_aio_losers(self, params: dict[str, Any]) -> dict[str, Any]:
        """Find content that has lost AI Overview citations."""
        queries = params.get("queries", [])

        # This would compare current AIO citations with historical data
        # For now, check current status and flag queries without citations

        if not self.context.serp_client:
            return {"data": {"error": "SERP client not configured"}, "recommendations": []}

        results = []
        recommendations = []

        for query in queries:
            try:
                serp = await self.context.serp_client.get_serp(query)

                if serp and serp.ai_overview:
                    citations = serp.ai_overview.get("citations", [])
                    client_cited = any(
                        self.context.client_domain in c
                        for c in citations
                    ) if self.context.client_domain else False

                    results.append({
                        "query": query,
                        "has_aio": True,
                        "client_cited": client_cited,
                        "total_citations": len(citations),
                    })

            except Exception as e:
                self.logger.warning("AIO check failed", query=query, error=str(e))

        uncited = [r for r in results if r["has_aio"] and not r["client_cited"]]
        if uncited:
            recommendations.append(Recommendation(
                title=f"{len(uncited)} queries without your AIO citation",
                description="Review and update content for these queries to regain/gain AIO visibility",
                priority=Priority.HIGH,
                category="aio_optimization",
            ))

        return {
            "data": {
                "queries_checked": len(results),
                "queries_with_aio": sum(1 for r in results if r["has_aio"]),
                "queries_cited": sum(1 for r in results if r.get("client_cited")),
                "results": results,
            },
            "recommendations": recommendations,
        }

    async def _check_content_freshness(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check content freshness based on last modified dates."""
        urls = params.get("urls", [])
        max_age_days = params.get("max_age_days", 365)

        import httpx

        stale_content = []
        fresh_content = []

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for url in urls[:50]:
                try:
                    response = await client.head(url)
                    last_modified = response.headers.get("Last-Modified")

                    if last_modified:
                        from email.utils import parsedate_to_datetime
                        try:
                            mod_date = parsedate_to_datetime(last_modified)
                            age_days = (datetime.now(mod_date.tzinfo) - mod_date).days

                            content_info = {
                                "url": url,
                                "last_modified": last_modified,
                                "age_days": age_days,
                            }

                            if age_days > max_age_days:
                                stale_content.append(content_info)
                            else:
                                fresh_content.append(content_info)
                        except Exception:
                            pass

                except Exception as e:
                    self.logger.warning("Freshness check failed", url=url, error=str(e))

        recommendations = []
        if stale_content:
            recommendations.append(Recommendation(
                title=f"{len(stale_content)} pages haven't been updated in {max_age_days}+ days",
                description="Review these pages for accuracy and consider updating with fresh information",
                priority=Priority.MEDIUM,
                category="content_freshness",
            ))

        return {
            "data": {
                "urls_checked": len(urls),
                "stale_count": len(stale_content),
                "fresh_count": len(fresh_content),
                "stale_content": sorted(stale_content, key=lambda x: x["age_days"], reverse=True)[:20],
            },
            "recommendations": recommendations,
        }

    async def _prioritize_refresh(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a prioritized content refresh queue."""
        # Run decay detection first
        decay_result = await self._detect_decay(params)
        decaying_pages = decay_result["data"].get("decaying_pages", [])

        # Score and prioritize
        refresh_queue = []
        for page in decaying_pages:
            priority_score = page["decay_score"]

            # Boost priority based on decay type
            if page["decay_type"] == "ranking_drop":
                priority_score += 10  # Can be recovered with content update
            elif page["decay_type"] == "visibility_loss":
                priority_score += 15  # Might be AIO-related, high priority

            refresh_queue.append({
                "page": page["page"],
                "priority_score": min(priority_score, 100),
                "decay_type": page["decay_type"],
                "click_loss": abs(page["click_change_pct"]),
                "action": self._suggest_action(page["decay_type"], page["click_change_pct"]),
            })

        # Sort by priority
        refresh_queue.sort(key=lambda x: x["priority_score"], reverse=True)

        return {
            "data": {
                "total_pages": len(refresh_queue),
                "high_priority": len([p for p in refresh_queue if p["priority_score"] >= 70]),
                "medium_priority": len([p for p in refresh_queue if 40 <= p["priority_score"] < 70]),
                "refresh_queue": refresh_queue[:30],
            },
            "recommendations": decay_result.get("recommendations", []),
            "alerts": decay_result.get("alerts", []),
        }

    def _suggest_action(self, decay_type: str, click_change: float) -> str:
        """Suggest action based on decay type."""
        actions = {
            "ranking_drop": "Update content, add fresh information, improve E-E-A-T signals",
            "visibility_loss": "Analyze if AIO is impacting; optimize for AI citation",
            "ctr_decline": "Improve title/meta description; add structured data",
            "general_decline": "Comprehensive content audit and refresh",
        }
        return actions.get(decay_type, "Review and update content")
