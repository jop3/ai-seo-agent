"""
SERP Features Agent - Tracks and optimizes for SERP features including AI Overviews.
"""

from datetime import datetime
from typing import Any

import structlog

from src.agents.base import BaseAgent, AgentContext
from src.core.errors import AgentError, ErrorCode
from src.models.agents import (
    AgentTask, AgentResult, AgentType, Recommendation, Alert, Priority, Severity
)

logger = structlog.get_logger()


class SERPFeaturesAgent(BaseAgent):
    """
    Analyzes and optimizes for SERP features.

    Capabilities:
    - Track AI Overview presence and citations
    - Monitor featured snippet ownership
    - Analyze People Also Ask opportunities
    - Track knowledge panel data
    - Identify SERP feature opportunities
    """

    agent_type = AgentType.SERP_FEATURES

    def __init__(self, context: AgentContext):
        self.context = context
        self.logger = logger.bind(agent="serp-features")

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute SERP features analysis task."""
        task_handlers = {
            "track_aio_presence": self._track_aio_presence,
            "analyze_featured_snippets": self._analyze_featured_snippets,
            "find_paa_opportunities": self._find_paa_opportunities,
            "serp_feature_audit": self._serp_feature_audit,
            "track_serp_changes": self._track_serp_changes,
        }

        handler = task_handlers.get(task.task_type)
        if not handler:
            raise AgentError(
                f"Unknown task type: {task.task_type}",
                agent_type="serp-features",
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

    async def _track_aio_presence(self, params: dict[str, Any]) -> dict[str, Any]:
        """Track AI Overview presence and citation status for queries."""
        queries = params.get("queries", [])
        client_domain = params.get("domain", self.context.client_domain)

        if not self.context.serp_client:
            return {"data": {"error": "SERP client not configured"}, "recommendations": []}

        results = []
        citations_gained = []
        citations_lost = []
        recommendations = []
        alerts = []

        for query in queries:
            try:
                serp = await self.context.serp_client.get_serp(query)

                query_result = {
                    "query": query,
                    "has_aio": False,
                    "client_cited": False,
                    "citation_position": None,
                    "total_citations": 0,
                    "aio_content_length": 0,
                    "citation_domains": [],
                }

                if serp and serp.ai_overview:
                    aio = serp.ai_overview
                    citations = aio.get("citations", [])
                    query_result["has_aio"] = True
                    query_result["total_citations"] = len(citations)
                    query_result["aio_content_length"] = len(aio.get("content", ""))

                    # Extract citation domains
                    for i, citation in enumerate(citations):
                        from urllib.parse import urlparse
                        domain = urlparse(citation).netloc
                        query_result["citation_domains"].append({
                            "position": i + 1,
                            "domain": domain,
                            "url": citation,
                        })

                        if client_domain and client_domain in domain:
                            query_result["client_cited"] = True
                            query_result["citation_position"] = i + 1

                results.append(query_result)

            except Exception as e:
                self.logger.warning("AIO tracking failed", query=query, error=str(e))

        # Calculate summary stats
        aio_count = sum(1 for r in results if r["has_aio"])
        cited_count = sum(1 for r in results if r["client_cited"])

        # Generate recommendations based on findings
        uncited_with_aio = [r for r in results if r["has_aio"] and not r["client_cited"]]
        if uncited_with_aio:
            recommendations.append(Recommendation(
                title=f"{len(uncited_with_aio)} AIO queries without your citation",
                description="Create or optimize content for these queries to earn AI Overview citations",
                priority=Priority.HIGH,
                category="aio_optimization",
                estimated_impact="high",
                data={"queries": [r["query"] for r in uncited_with_aio[:10]]},
            ))

        # Alert if cited percentage is low
        if results and aio_count > 0:
            citation_rate = cited_count / aio_count * 100
            if citation_rate < 20:
                alerts.append(Alert(
                    title="Low AI Overview citation rate",
                    message=f"Only {citation_rate:.1f}% of AIOs cite your content",
                    severity=Severity.WARNING,
                    source="serp-features",
                ))

        return {
            "data": {
                "queries_analyzed": len(results),
                "queries_with_aio": aio_count,
                "queries_with_citation": cited_count,
                "citation_rate": round(cited_count / aio_count * 100, 1) if aio_count else 0,
                "results": results,
            },
            "recommendations": recommendations,
            "alerts": alerts,
        }

    async def _analyze_featured_snippets(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze featured snippet opportunities and ownership."""
        queries = params.get("queries", [])
        client_domain = params.get("domain", self.context.client_domain)

        if not self.context.serp_client:
            return {"data": {"error": "SERP client not configured"}, "recommendations": []}

        results = []
        recommendations = []

        for query in queries:
            try:
                serp = await self.context.serp_client.get_serp(query)

                query_result = {
                    "query": query,
                    "has_featured_snippet": False,
                    "snippet_type": None,
                    "snippet_owner": None,
                    "client_owns_snippet": False,
                    "client_organic_position": None,
                }

                if serp:
                    # Check for featured snippet
                    if hasattr(serp, 'featured_snippet') and serp.featured_snippet:
                        fs = serp.featured_snippet
                        query_result["has_featured_snippet"] = True
                        query_result["snippet_type"] = fs.get("type", "paragraph")
                        query_result["snippet_owner"] = fs.get("domain", "")

                        if client_domain and client_domain in fs.get("url", ""):
                            query_result["client_owns_snippet"] = True

                    # Check organic position
                    if hasattr(serp, 'organic_results'):
                        for i, result in enumerate(serp.organic_results[:10]):
                            if client_domain and client_domain in result.get("url", ""):
                                query_result["client_organic_position"] = i + 1
                                break

                results.append(query_result)

            except Exception as e:
                self.logger.warning("Featured snippet analysis failed", query=query, error=str(e))

        # Find opportunities (have snippet but don't own, rank in top 5)
        opportunities = [
            r for r in results
            if r["has_featured_snippet"]
            and not r["client_owns_snippet"]
            and r["client_organic_position"]
            and r["client_organic_position"] <= 5
        ]

        if opportunities:
            recommendations.append(Recommendation(
                title=f"{len(opportunities)} featured snippet steal opportunities",
                description="You rank in top 5 but don't own the snippet. Optimize content format to match snippet type.",
                priority=Priority.HIGH,
                category="featured_snippets",
                data={"opportunities": [
                    {"query": o["query"], "type": o["snippet_type"], "position": o["client_organic_position"]}
                    for o in opportunities[:10]
                ]},
            ))

        return {
            "data": {
                "queries_analyzed": len(results),
                "snippets_found": sum(1 for r in results if r["has_featured_snippet"]),
                "snippets_owned": sum(1 for r in results if r["client_owns_snippet"]),
                "steal_opportunities": len(opportunities),
                "results": results,
            },
            "recommendations": recommendations,
        }

    async def _find_paa_opportunities(self, params: dict[str, Any]) -> dict[str, Any]:
        """Find People Also Ask opportunities."""
        queries = params.get("queries", [])

        if not self.context.serp_client:
            return {"data": {"error": "SERP client not configured"}, "recommendations": []}

        all_paa_questions = []
        question_frequency = {}
        recommendations = []

        for query in queries:
            try:
                serp = await self.context.serp_client.get_serp(query)

                if serp and hasattr(serp, 'people_also_ask'):
                    paa = serp.people_also_ask or []
                    for question in paa:
                        q_text = question.get("question", "") if isinstance(question, dict) else str(question)
                        if q_text:
                            all_paa_questions.append({
                                "question": q_text,
                                "source_query": query,
                            })
                            question_frequency[q_text] = question_frequency.get(q_text, 0) + 1

            except Exception as e:
                self.logger.warning("PAA analysis failed", query=query, error=str(e))

        # Sort questions by frequency (appearing for multiple queries = more important)
        top_questions = sorted(
            question_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )[:20]

        # Categorize questions
        question_types = self._categorize_questions([q for q, _ in top_questions])

        if top_questions:
            recommendations.append(Recommendation(
                title=f"Found {len(top_questions)} recurring PAA questions",
                description="Create FAQ content answering these questions to capture PAA visibility",
                priority=Priority.MEDIUM,
                category="paa_optimization",
                data={"top_questions": [{"question": q, "frequency": f} for q, f in top_questions[:10]]},
            ))

        return {
            "data": {
                "queries_analyzed": len(queries),
                "unique_questions": len(question_frequency),
                "total_paa_found": len(all_paa_questions),
                "top_questions": [{"question": q, "frequency": f} for q, f in top_questions],
                "question_types": question_types,
            },
            "recommendations": recommendations,
        }

    def _categorize_questions(self, questions: list[str]) -> dict[str, int]:
        """Categorize questions by type (what, how, why, etc.)."""
        categories = {
            "what": 0,
            "how": 0,
            "why": 0,
            "when": 0,
            "where": 0,
            "who": 0,
            "which": 0,
            "can/is/does": 0,
            "other": 0,
        }

        for q in questions:
            q_lower = q.lower().strip()
            if q_lower.startswith("what"):
                categories["what"] += 1
            elif q_lower.startswith("how"):
                categories["how"] += 1
            elif q_lower.startswith("why"):
                categories["why"] += 1
            elif q_lower.startswith("when"):
                categories["when"] += 1
            elif q_lower.startswith("where"):
                categories["where"] += 1
            elif q_lower.startswith("who"):
                categories["who"] += 1
            elif q_lower.startswith("which"):
                categories["which"] += 1
            elif any(q_lower.startswith(w) for w in ["can", "is", "does", "do", "are"]):
                categories["can/is/does"] += 1
            else:
                categories["other"] += 1

        return {k: v for k, v in categories.items() if v > 0}

    async def _serp_feature_audit(self, params: dict[str, Any]) -> dict[str, Any]:
        """Comprehensive SERP feature audit for target queries."""
        queries = params.get("queries", [])
        client_domain = params.get("domain", self.context.client_domain)

        if not self.context.serp_client:
            return {"data": {"error": "SERP client not configured"}, "recommendations": []}

        feature_summary = {
            "ai_overview": {"total": 0, "cited": 0},
            "featured_snippet": {"total": 0, "owned": 0},
            "people_also_ask": {"total": 0},
            "local_pack": {"total": 0},
            "knowledge_panel": {"total": 0},
            "image_pack": {"total": 0},
            "video_results": {"total": 0},
            "shopping": {"total": 0},
        }

        query_details = []

        for query in queries:
            try:
                serp = await self.context.serp_client.get_serp(query)
                if not serp:
                    continue

                detail = {"query": query, "features": []}

                # Check each feature type
                if serp.ai_overview:
                    feature_summary["ai_overview"]["total"] += 1
                    detail["features"].append("ai_overview")
                    citations = serp.ai_overview.get("citations", [])
                    if client_domain and any(client_domain in c for c in citations):
                        feature_summary["ai_overview"]["cited"] += 1

                if hasattr(serp, 'featured_snippet') and serp.featured_snippet:
                    feature_summary["featured_snippet"]["total"] += 1
                    detail["features"].append("featured_snippet")
                    if client_domain and client_domain in serp.featured_snippet.get("url", ""):
                        feature_summary["featured_snippet"]["owned"] += 1

                if hasattr(serp, 'people_also_ask') and serp.people_also_ask:
                    feature_summary["people_also_ask"]["total"] += 1
                    detail["features"].append("people_also_ask")

                if hasattr(serp, 'local_pack') and serp.local_pack:
                    feature_summary["local_pack"]["total"] += 1
                    detail["features"].append("local_pack")

                if hasattr(serp, 'knowledge_panel') and serp.knowledge_panel:
                    feature_summary["knowledge_panel"]["total"] += 1
                    detail["features"].append("knowledge_panel")

                query_details.append(detail)

            except Exception as e:
                self.logger.warning("SERP audit failed", query=query, error=str(e))

        recommendations = []

        # Generate recommendations based on gaps
        aio = feature_summary["ai_overview"]
        if aio["total"] > 0 and aio["cited"] / aio["total"] < 0.3:
            recommendations.append(Recommendation(
                title="Low AI Overview citation rate",
                description=f"Cited in only {aio['cited']}/{aio['total']} AIOs. Prioritize AIO-optimized content.",
                priority=Priority.HIGH,
                category="aio_optimization",
            ))

        fs = feature_summary["featured_snippet"]
        if fs["total"] > 0 and fs["owned"] / fs["total"] < 0.2:
            recommendations.append(Recommendation(
                title="Featured snippet ownership opportunity",
                description=f"Own only {fs['owned']}/{fs['total']} snippets. Format content for snippet capture.",
                priority=Priority.MEDIUM,
                category="featured_snippets",
            ))

        return {
            "data": {
                "queries_analyzed": len(queries),
                "feature_summary": feature_summary,
                "query_details": query_details,
            },
            "recommendations": recommendations,
        }

    async def _track_serp_changes(self, params: dict[str, Any]) -> dict[str, Any]:
        """Track changes in SERP features over time (requires historical data)."""
        queries = params.get("queries", [])

        # This would compare current SERP with stored historical data
        # For now, return structure for future implementation
        return {
            "data": {
                "message": "SERP change tracking requires historical data storage",
                "queries": queries,
                "suggestion": "Enable historical storage to track SERP changes over time",
            },
            "recommendations": [
                Recommendation(
                    title="Enable SERP change tracking",
                    description="Configure historical storage to track SERP feature changes and receive alerts",
                    priority=Priority.LOW,
                    category="monitoring",
                ),
            ],
        }
