"""
Multi-Engine Tracker Agent - Monitors presence across AI search engines.
"""

import asyncio
from datetime import datetime
from typing import Any

import httpx
import structlog

from src.agents.base import BaseAgent, AgentContext
from src.models.agents import AgentTask, AgentResult, Recommendation, Alert, Priority, Severity

logger = structlog.get_logger()


class MultiEngineTrackerAgent(BaseAgent):
    """
    Tracks presence across multiple AI-powered search engines.

    Supported engines:
    - Google AI Overviews
    - Perplexity
    - ChatGPT Search (when available)
    - Bing Copilot
    - You.com
    """

    def __init__(self, context: AgentContext):
        super().__init__(
            agent_type="multi-engine-tracker",
            description="Tracks presence across AI search engines (Perplexity, ChatGPT, Bing Copilot)",
            context=context,
        )

    async def run(self, task: AgentTask) -> AgentResult:
        """Execute multi-engine tracking task."""
        start_time = datetime.utcnow()

        try:
            if task.task_type == "check_all_engines":
                result = await self._check_all_engines(task.parameters)
            elif task.task_type == "check_perplexity":
                result = await self._check_perplexity(task.parameters)
            elif task.task_type == "check_bing_copilot":
                result = await self._check_bing_copilot(task.parameters)
            elif task.task_type == "check_chatgpt":
                result = await self._check_chatgpt(task.parameters)
            elif task.task_type == "compare_engines":
                result = await self._compare_engines(task.parameters)
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
            logger.error("Multi-engine tracking failed", error=str(e))
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": str(e)},
            )

    async def _check_all_engines(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check presence across all supported engines."""
        queries = params.get("queries", [])
        engines = params.get("engines", ["google_aio", "perplexity", "bing_copilot"])

        if not queries and self.context.gsc_client:
            # Get top queries from GSC
            top = await self.context.gsc_client.get_top_queries(limit=20)
            queries = [q.query for q in top]

        results = {
            "checked_at": datetime.utcnow().isoformat(),
            "queries_checked": len(queries),
            "engines": {},
            "summary": {},
        }
        recommendations = []
        alerts = []

        # Check each engine
        for engine in engines:
            engine_results = await self._check_engine(engine, queries)
            results["engines"][engine] = engine_results

        # Generate summary
        total_citations = 0
        for engine, data in results["engines"].items():
            citations = data.get("citation_count", 0)
            total_citations += citations

        results["summary"] = {
            "total_citations": total_citations,
            "citation_rate": (total_citations / (len(queries) * len(engines)) * 100) if queries and engines else 0,
            "best_engine": max(results["engines"].items(), key=lambda x: x[1].get("citation_count", 0))[0] if results["engines"] else None,
        }

        # Generate alerts and recommendations
        if results["summary"]["citation_rate"] < 10:
            alerts.append(Alert(
                title="Low AI Engine Citation Rate",
                message=f"Your site is only cited in {results['summary']['citation_rate']:.1f}% of AI engine responses",
                severity=Severity.WARNING,
                source=self.agent_type,
            ))
            recommendations.append(Recommendation(
                title="Improve AI Engine Visibility",
                description="Focus on authoritative content, proper schema markup, and clear factual statements to improve AI citations.",
                priority=Priority.HIGH,
                category="ai_visibility",
            ))

        return {
            "data": results,
            "recommendations": recommendations,
            "alerts": alerts,
        }

    async def _check_engine(self, engine: str, queries: list[str]) -> dict[str, Any]:
        """Check a single engine for citations."""
        result = {
            "engine": engine,
            "queries_checked": len(queries),
            "citation_count": 0,
            "citations": [],
        }

        if engine == "google_aio":
            result = await self._check_google_aio(queries)
        elif engine == "perplexity":
            result = await self._check_perplexity_queries(queries)
        elif engine == "bing_copilot":
            result = await self._check_bing_queries(queries)
        elif engine == "chatgpt":
            result = await self._check_chatgpt_queries(queries)

        return result

    async def _check_google_aio(self, queries: list[str]) -> dict[str, Any]:
        """Check Google AI Overviews."""
        result = {
            "engine": "google_aio",
            "queries_checked": len(queries),
            "citation_count": 0,
            "citations": [],
        }

        if not self.context.serp_client:
            result["error"] = "SERP client not configured"
            return result

        for query in queries:
            try:
                serp = await self.context.serp_client.get_serp(query)
                if serp and serp.ai_overview:
                    for citation in serp.ai_overview.get("citations", []):
                        if self.context.client_domain and self.context.client_domain in citation:
                            result["citation_count"] += 1
                            result["citations"].append({
                                "query": query,
                                "url": citation,
                            })
            except Exception as e:
                logger.warning("Google AIO check failed", query=query, error=str(e))

        return result

    async def _check_perplexity_queries(self, queries: list[str]) -> dict[str, Any]:
        """Check Perplexity for citations."""
        result = {
            "engine": "perplexity",
            "queries_checked": len(queries),
            "citation_count": 0,
            "citations": [],
            "note": "Perplexity API integration required for live data",
        }

        # Perplexity has an API but requires separate setup
        # This is a placeholder for the integration
        # In production, would use Perplexity's sonar API

        return result

    async def _check_bing_queries(self, queries: list[str]) -> dict[str, Any]:
        """Check Bing rankings and instant answers."""
        result = {
            "engine": "bing",
            "queries_checked": len(queries),
            "ranking_count": 0,
            "instant_answer_count": 0,
            "rankings": [],
        }

        # Use Bing client if available
        if self.context.bing_client and self.context.bing_client.available:
            tracking = await self.context.bing_client.track_queries(
                queries=queries,
                target_domain=self.context.client_domain or "",
            )

            result["rankings"] = tracking.get("results", [])
            result["ranking_count"] = tracking.get("queries_ranked", 0)
            result["average_position"] = tracking.get("average_position")

            # Count instant answers
            for r in result["rankings"]:
                if r.get("has_instant_answer"):
                    result["instant_answer_count"] += 1

            return result

        # Graceful degradation
        result["available"] = False
        result["error"] = "Bing API key not configured. Add BING_API_KEY to your environment."
        return result

    async def _check_chatgpt_queries(self, queries: list[str]) -> dict[str, Any]:
        """Check ChatGPT Search for citations."""
        result = {
            "engine": "chatgpt",
            "queries_checked": len(queries),
            "citation_count": 0,
            "citations": [],
            "note": "ChatGPT Search API not publicly available yet",
        }

        # ChatGPT's search feature doesn't have a public API yet
        # Would need browser automation or wait for API

        return result

    async def _check_perplexity(self, params: dict[str, Any]) -> dict[str, Any]:
        """Detailed Perplexity check."""
        queries = params.get("queries", [])
        results = await self._check_perplexity_queries(queries)
        return {"data": results, "recommendations": [], "alerts": []}

    async def _check_bing_copilot(self, params: dict[str, Any]) -> dict[str, Any]:
        """Detailed Bing Copilot check."""
        queries = params.get("queries", [])
        results = await self._check_bing_queries(queries)
        return {"data": results, "recommendations": [], "alerts": []}

    async def _check_chatgpt(self, params: dict[str, Any]) -> dict[str, Any]:
        """Detailed ChatGPT check."""
        queries = params.get("queries", [])
        results = await self._check_chatgpt_queries(queries)
        return {"data": results, "recommendations": [], "alerts": []}

    async def _compare_engines(self, params: dict[str, Any]) -> dict[str, Any]:
        """Compare performance across engines."""
        queries = params.get("queries", [])

        all_results = await self._check_all_engines({"queries": queries})

        # Build comparison
        comparison = {
            "queries": queries,
            "by_engine": all_results["data"]["engines"],
            "ranking": sorted(
                all_results["data"]["engines"].items(),
                key=lambda x: x[1].get("citation_count", 0),
                reverse=True,
            ),
        }

        return {
            "data": comparison,
            "recommendations": all_results.get("recommendations", []),
            "alerts": all_results.get("alerts", []),
        }
