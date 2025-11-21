"""
Competitor Monitor Agent - Tracks competitor AIO citations, rankings, and content changes.
"""

import asyncio
from datetime import datetime
from typing import Any

import structlog

from src.agents.base import BaseAgent, AgentContext
from src.models.agents import AgentTask, AgentResult, Recommendation, Alert, Priority, Severity

logger = structlog.get_logger()


class CompetitorMonitorAgent(BaseAgent):
    """
    Monitors competitor SEO performance and AI Overview presence.

    Capabilities:
    - Track competitor AIO citations
    - Monitor ranking changes
    - Detect content/schema updates
    - Compare agent-friendliness
    """

    def __init__(self, context: AgentContext):
        super().__init__(
            agent_type="competitor-monitor",
            description="Monitors competitor SEO performance and AI Overview presence",
            context=context,
        )

    async def run(self, task: AgentTask) -> AgentResult:
        """Execute competitor monitoring task."""
        start_time = datetime.utcnow()

        try:
            if task.task_type == "full_competitor_analysis":
                result = await self._full_competitor_analysis(task.parameters)
            elif task.task_type == "check_aio_citations":
                result = await self._check_competitor_aio_citations(task.parameters)
            elif task.task_type == "compare_rankings":
                result = await self._compare_rankings(task.parameters)
            elif task.task_type == "detect_content_changes":
                result = await self._detect_content_changes(task.parameters)
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
            logger.error("Competitor monitor task failed", error=str(e))
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": str(e)},
            )

    async def _full_competitor_analysis(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run full competitor analysis."""
        competitors = params.get("competitors", [])

        # If no competitors specified, try to detect from config or GSC
        if not competitors and self.context.settings:
            competitors = getattr(self.context.settings, "competitors", [])

        results = {
            "analyzed_at": datetime.utcnow().isoformat(),
            "competitors": [],
            "summary": {},
        }
        recommendations = []
        alerts = []

        for competitor in competitors:
            competitor_data = await self._analyze_single_competitor(competitor)
            results["competitors"].append(competitor_data)

            # Check for concerning findings
            if competitor_data.get("aio_citation_rate", 0) > 50:
                alerts.append(Alert(
                    title=f"High AIO Citation Rate: {competitor}",
                    message=f"{competitor} is cited in {competitor_data['aio_citation_rate']:.0f}% of AI Overviews for your queries",
                    severity=Severity.WARNING,
                    source=self.agent_type,
                    data=competitor_data,
                ))

        # Generate summary
        if results["competitors"]:
            avg_citation = sum(c.get("aio_citation_rate", 0) for c in results["competitors"]) / len(results["competitors"])
            results["summary"] = {
                "total_competitors": len(competitors),
                "avg_competitor_aio_citation_rate": avg_citation,
                "top_threat": max(results["competitors"], key=lambda x: x.get("aio_citation_rate", 0), default={}),
            }

            if avg_citation > 30:
                recommendations.append(Recommendation(
                    title="Competitors dominating AI Overviews",
                    description="Your competitors have strong AI Overview presence. Focus on schema optimization and authoritative content.",
                    priority=Priority.HIGH,
                    category="aio_optimization",
                    estimated_impact="high",
                ))

        return {
            "data": results,
            "recommendations": recommendations,
            "alerts": alerts,
        }

    async def _analyze_single_competitor(self, competitor: str) -> dict[str, Any]:
        """Analyze a single competitor."""
        result = {
            "domain": competitor,
            "analyzed_at": datetime.utcnow().isoformat(),
            "aio_citation_rate": 0,
            "avg_position": 0,
            "schema_types": [],
            "content_freshness": "unknown",
        }

        # Check AIO citations for top queries
        if self.context.serp_client and self.context.gsc_client:
            try:
                queries = await self.context.gsc_client.get_top_queries(limit=50)
                citation_count = 0

                for query in queries[:20]:  # Check top 20
                    serp_result = await self.context.serp_client.get_serp(query.query)

                    if serp_result and serp_result.ai_overview:
                        # Check if competitor is cited
                        for citation in serp_result.ai_overview.get("citations", []):
                            if competitor in citation:
                                citation_count += 1
                                break

                        # Track competitor position
                        for i, organic in enumerate(serp_result.organic_results[:10]):
                            if competitor in str(organic.get("url", "")):
                                result["avg_position"] = (result["avg_position"] + (i + 1)) / 2

                result["aio_citation_rate"] = (citation_count / 20) * 100 if queries else 0

            except Exception as e:
                logger.warning("Error analyzing competitor", competitor=competitor, error=str(e))

        # Analyze competitor's schema (simplified - would use actual scraping)
        result["schema_types"] = await self._detect_competitor_schema(competitor)

        return result

    async def _detect_competitor_schema(self, competitor: str) -> list[str]:
        """Detect schema types used by competitor."""
        # In production, would scrape and parse the competitor's pages
        # For now, return common e-commerce schemas
        return ["Organization", "WebSite", "Product", "BreadcrumbList"]

    async def _check_competitor_aio_citations(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check which competitors are being cited in AIOs."""
        queries = params.get("queries", [])
        competitors = params.get("competitors", [])

        citations = {comp: {"count": 0, "queries": []} for comp in competitors}

        if self.context.serp_client:
            for query in queries:
                try:
                    serp = await self.context.serp_client.get_serp(query)
                    if serp and serp.ai_overview:
                        for citation_url in serp.ai_overview.get("citations", []):
                            for comp in competitors:
                                if comp in citation_url:
                                    citations[comp]["count"] += 1
                                    citations[comp]["queries"].append(query)
                except Exception as e:
                    logger.warning("SERP check failed", query=query, error=str(e))

        return {
            "data": {
                "citations": citations,
                "total_queries_checked": len(queries),
            },
            "recommendations": [],
            "alerts": [],
        }

    async def _compare_rankings(self, params: dict[str, Any]) -> dict[str, Any]:
        """Compare rankings with competitors."""
        competitors = params.get("competitors", [])
        queries = params.get("queries", [])

        rankings = {"client": {}, "competitors": {comp: {} for comp in competitors}}

        if self.context.serp_client:
            for query in queries:
                try:
                    serp = await self.context.serp_client.get_serp(query)
                    if serp:
                        for i, result in enumerate(serp.organic_results[:20]):
                            url = str(result.get("url", ""))

                            # Check client
                            if self.context.client_domain and self.context.client_domain in url:
                                rankings["client"][query] = i + 1

                            # Check competitors
                            for comp in competitors:
                                if comp in url:
                                    rankings["competitors"][comp][query] = i + 1
                                    break
                except Exception as e:
                    logger.warning("Ranking check failed", query=query, error=str(e))

        return {
            "data": rankings,
            "recommendations": [],
            "alerts": [],
        }

    async def _detect_content_changes(self, params: dict[str, Any]) -> dict[str, Any]:
        """Detect content changes on competitor sites using Wayback Machine."""
        competitor_urls = params.get("urls", [])
        days_back = params.get("days_back", 30)

        if not competitor_urls:
            return {"data": {"error": "urls list is required"}, "recommendations": []}

        # Use Wayback client (always available - no API key needed)
        if self.context.wayback_client:
            result = await self.context.wayback_client.check_competitor_changes(
                competitor_urls=competitor_urls,
                days_back=days_back,
            )

            recommendations = []
            alerts = []

            pages_with_changes = [r for r in result.get("results", []) if r.get("has_changes")]

            if pages_with_changes:
                # Check for significant changes
                title_changes = []
                content_changes = []

                for page in pages_with_changes:
                    for change in page.get("changes", []):
                        if change.get("type") == "title_change":
                            title_changes.append(page["url"])
                        if change.get("type") == "content_length_change":
                            content_changes.append(page["url"])

                if title_changes:
                    alerts.append(Alert(
                        title=f"{len(title_changes)} competitor pages changed titles",
                        message="Competitors may be optimizing for new keywords",
                        severity=Severity.WARNING,
                        source="competitor-monitor",
                        data={"urls": title_changes[:5]},
                    ))

                recommendations.append(Recommendation(
                    title=f"{len(pages_with_changes)} competitor pages updated recently",
                    description="Review competitor changes to understand their SEO strategy",
                    priority=Priority.MEDIUM,
                    category="competitor_monitoring",
                ))

            return {
                "data": result,
                "recommendations": recommendations,
                "alerts": alerts,
            }

        # Fallback (shouldn't happen as Wayback is always available)
        return {
            "data": {
                "message": "Wayback client not initialized",
            },
            "recommendations": [],
            "alerts": [],
        }
