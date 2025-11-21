"""SEO Analyst Agent - Analyzes GSC data and identifies AIO-affected queries."""

import asyncio
from datetime import datetime
from typing import Any

from src.agents.base import AgentContext, BaseAgent
from src.models.agents import (
    AgentResult,
    AgentTask,
    AgentType,
    Alert,
    AlertSeverity,
    AlertType,
    Recommendation,
    RecommendationPriority,
    RecommendationType,
)
from src.models.seo import AIOverviewStatus, Query, QueryClassification


class SEOAnalystAgent(BaseAgent):
    """
    Analyzes search performance data to identify:
    1. Queries affected by AI Overviews
    2. Traffic drops and their likely causes
    3. Optimization opportunities
    """

    agent_type = AgentType.SEO_ANALYST

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute an SEO analysis task."""
        task_type = task.task_type
        params = task.parameters

        if task_type == "full_analysis":
            return await self._full_analysis(params)
        elif task_type == "detect_aio_impact":
            return await self._detect_aio_impact(params)
        elif task_type == "traffic_drop_analysis":
            return await self._traffic_drop_analysis(params)
        elif task_type == "query_classification":
            return await self._classify_queries(params)
        else:
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": f"Unknown task type: {task_type}"},
            )

    async def _full_analysis(self, params: dict[str, Any]) -> AgentResult:
        """
        Comprehensive SEO analysis:
        1. Fetch top queries from GSC
        2. Check which trigger AI Overviews
        3. Identify traffic changes
        4. Generate prioritized recommendations
        """
        recommendations: list[Recommendation] = []
        alerts: list[Alert] = []
        data: dict[str, Any] = {}

        # Step 1: Get top queries from GSC
        if not self.context.gsc_client:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "GSC client not configured"},
            )

        top_queries = await self.context.gsc_client.get_top_queries(
            limit=params.get("query_limit", 500),
            days=params.get("days", 30),
        )

        data["total_queries_analyzed"] = len(top_queries)
        self.logger.info(f"Fetched {len(top_queries)} queries from GSC")

        # Step 2: Classify queries by intent
        query_texts = [q.query for q in top_queries[:200]]  # Limit for API cost
        classifications = await self.context.openai_client.classify_queries(query_texts)

        # Map classifications back
        classification_map = {c["query"]: c for c in classifications}
        for query in top_queries:
            if query.query in classification_map:
                cl = classification_map[query.query]
                query.classification = QueryClassification(cl.get("intent", "informational"))

        # Count by classification
        by_intent = {}
        for q in top_queries:
            intent = q.classification.value
            by_intent[intent] = by_intent.get(intent, 0) + 1
        data["queries_by_intent"] = by_intent

        # Step 3: Check for AI Overviews (top queries only due to API limits)
        aio_results = []
        if self.context.serp_client:
            high_risk_queries = [
                c["query"]
                for c in classifications
                if c.get("aio_risk") == "high"
            ][:50]  # Limit API calls

            if high_risk_queries:
                self.logger.info(f"Checking {len(high_risk_queries)} high-risk queries for AIO")
                aio_results = await self.context.serp_client.check_queries_for_aio(
                    high_risk_queries,
                    concurrency=3,
                )

        # Analyze AIO impact
        queries_with_aio = [r for r in aio_results if r.has_aio]
        queries_cited = [r for r in queries_with_aio if r.client_cited]
        queries_not_cited = [r for r in queries_with_aio if not r.client_cited]

        data["aio_analysis"] = {
            "queries_checked": len(aio_results),
            "queries_with_aio": len(queries_with_aio),
            "client_cited": len(queries_cited),
            "client_not_cited": len(queries_not_cited),
            "citation_rate": (
                len(queries_cited) / len(queries_with_aio) * 100
                if queries_with_aio
                else 0
            ),
        }

        # Step 4: Detect traffic changes
        traffic_changes = await self.context.gsc_client.detect_traffic_changes(
            threshold_percent=params.get("traffic_threshold", 20),
        )

        significant_drops = [c for c in traffic_changes if c.change_percent < -20]
        data["traffic_changes"] = {
            "total_significant_changes": len(traffic_changes),
            "significant_drops": len(significant_drops),
            "top_drops": [
                {
                    "query": c.query,
                    "change": f"{c.change_percent:.1f}%",
                    "previous": c.previous_value,
                    "current": c.current_value,
                }
                for c in significant_drops[:10]
            ],
        }

        # Step 5: Generate recommendations
        # High priority: Queries with AIO where we're not cited
        for result in queries_not_cited[:20]:
            # Find the query's traffic data
            query_data = next(
                (q for q in top_queries if q.query == result.query),
                None,
            )

            recommendations.append(
                Recommendation(
                    type=RecommendationType.CONTENT_STRUCTURE,
                    priority=RecommendationPriority.HIGH,
                    title=f"Optimize for AIO: {result.query}",
                    description=(
                        f"Query '{result.query}' shows an AI Overview but you're not cited. "
                        f"Competitors cited: {', '.join(result.competitor_citations[:3])}"
                    ),
                    affected_query=result.query,
                    estimated_impact="High - Direct AIO citation opportunity",
                    implementation_effort="Medium",
                )
            )

        # Add schema recommendations for informational queries
        informational_queries = [
            q for q in top_queries
            if q.classification == QueryClassification.INFORMATIONAL
            and q.clicks > 10
        ][:10]

        for query in informational_queries:
            recommendations.append(
                Recommendation(
                    type=RecommendationType.FAQ_ADDITION,
                    priority=RecommendationPriority.MEDIUM,
                    title=f"Add FAQ for: {query.query}",
                    description=(
                        f"Add FAQ schema markup addressing '{query.query}' "
                        f"to improve AIO citation chances. "
                        f"Current traffic: {query.clicks} clicks/month"
                    ),
                    affected_query=query.query,
                    estimated_impact="Medium",
                    implementation_effort="Easy",
                    auto_implementable=True,
                )
            )

        # Step 6: Create alerts for significant issues
        if len(queries_not_cited) > 10:
            alerts.append(
                Alert(
                    type=AlertType.AIO_DETECTED,
                    severity=AlertSeverity.WARNING,
                    title="Multiple queries have AIOs without citation",
                    message=(
                        f"{len(queries_not_cited)} of your top queries show AI Overviews "
                        f"but you are not being cited. This may explain traffic drops."
                    ),
                    data={
                        "affected_queries": [r.query for r in queries_not_cited[:10]],
                        "total_affected": len(queries_not_cited),
                    },
                )
            )

        for drop in significant_drops[:5]:
            if drop.change_percent < -50:
                alerts.append(
                    Alert(
                        type=AlertType.TRAFFIC_DROP,
                        severity=AlertSeverity.CRITICAL,
                        title=f"Critical traffic drop: {drop.query}",
                        message=(
                            f"Query '{drop.query}' dropped {abs(drop.change_percent):.0f}% "
                            f"from {drop.previous_value} to {drop.current_value} clicks"
                        ),
                        data={
                            "query": drop.query,
                            "change_percent": drop.change_percent,
                            "previous": drop.previous_value,
                            "current": drop.current_value,
                        },
                    )
                )

        # Send alerts via Teams
        for alert in alerts:
            await self.send_alert(alert)

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data=data,
            recommendations=recommendations,
            alerts=alerts,
        )

    async def _detect_aio_impact(self, params: dict[str, Any]) -> AgentResult:
        """Detect AI Overview impact on specific queries."""
        queries = params.get("queries", [])

        if not queries:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "No queries provided"},
            )

        if not self.context.serp_client:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "SERP client not configured"},
            )

        results = await self.context.serp_client.check_queries_for_aio(queries)
        report = await self.context.serp_client.get_aio_impact_report(queries)

        alerts = []
        for result in results:
            if result.has_aio and not result.client_cited:
                alerts.append(
                    Alert(
                        type=AlertType.AIO_DETECTED,
                        severity=AlertSeverity.WARNING,
                        title=f"AIO without citation: {result.query}",
                        message=f"You are not cited in the AI Overview for '{result.query}'",
                        data={"competitors": result.competitor_citations[:5]},
                    )
                )

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data=report,
            alerts=alerts,
        )

    async def _traffic_drop_analysis(self, params: dict[str, Any]) -> AgentResult:
        """Analyze traffic drops and correlate with AI Overviews."""
        if not self.context.gsc_client:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "GSC client not configured"},
            )

        threshold = params.get("threshold_percent", 20)
        changes = await self.context.gsc_client.detect_traffic_changes(
            threshold_percent=threshold,
        )

        drops = [c for c in changes if c.change_percent < 0]

        # Check if dropped queries now have AIOs
        correlations = []
        if self.context.serp_client and drops:
            drop_queries = [d.query for d in drops[:30] if d.query]
            aio_results = await self.context.serp_client.check_queries_for_aio(
                drop_queries
            )

            for drop in drops:
                aio_result = next(
                    (r for r in aio_results if r.query == drop.query),
                    None,
                )
                if aio_result and aio_result.has_aio:
                    drop.likely_cause = "aio_introduction"
                    correlations.append({
                        "query": drop.query,
                        "traffic_change": drop.change_percent,
                        "has_aio": True,
                        "client_cited": aio_result.client_cited,
                    })

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data={
                "total_drops": len(drops),
                "aio_correlated_drops": len(correlations),
                "correlations": correlations,
                "all_drops": [
                    {
                        "query": d.query,
                        "change": d.change_percent,
                        "likely_cause": d.likely_cause,
                    }
                    for d in drops[:50]
                ],
            },
        )

    async def _classify_queries(self, params: dict[str, Any]) -> AgentResult:
        """Classify queries by intent and AIO risk."""
        queries = params.get("queries", [])

        if not queries:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "No queries provided"},
            )

        classifications = await self.context.openai_client.classify_queries(queries)

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data={
                "classifications": classifications,
                "summary": {
                    "high_risk": len([c for c in classifications if c.get("aio_risk") == "high"]),
                    "medium_risk": len([c for c in classifications if c.get("aio_risk") == "medium"]),
                    "low_risk": len([c for c in classifications if c.get("aio_risk") == "low"]),
                },
            },
        )
