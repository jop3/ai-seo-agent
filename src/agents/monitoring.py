"""Monitoring Agent - Watches for changes and triggers alerts."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog

from src.agents.base import AgentContext, BaseAgent
from src.models.agents import (
    AgentResult,
    AgentTask,
    AgentType,
    Alert,
    AlertSeverity,
    AlertType,
)

logger = structlog.get_logger()

# Known Google algorithm update sources
ALGORITHM_UPDATE_SOURCES = [
    "https://status.search.google.com/summary",
    "https://developers.google.com/search/blog",
]

# SEO news RSS feeds
SEO_NEWS_FEEDS = [
    "https://searchengineland.com/feed",
    "https://www.searchenginejournal.com/feed/",
    "https://moz.com/feed",
]


class MonitoringAgent(BaseAgent):
    """
    Monitors for:
    1. Traffic anomalies
    2. Algorithm updates
    3. Competitor changes
    4. AIO status changes
    5. Schema validation issues
    """

    agent_type = AgentType.MONITORING

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute a monitoring task."""
        task_type = task.task_type
        params = task.parameters

        if task_type == "full_monitoring_cycle":
            return await self._full_monitoring_cycle(params)
        elif task_type == "check_traffic_anomalies":
            return await self._check_traffic_anomalies(params)
        elif task_type == "check_algorithm_updates":
            return await self._check_algorithm_updates(params)
        elif task_type == "check_aio_changes":
            return await self._check_aio_changes(params)
        elif task_type == "daily_summary":
            return await self._generate_daily_summary(params)
        else:
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": f"Unknown task type: {task_type}"},
            )

    async def _full_monitoring_cycle(self, params: dict[str, Any]) -> AgentResult:
        """
        Run a full monitoring cycle:
        1. Check for traffic anomalies
        2. Check for algorithm updates
        3. Check AIO status changes on tracked queries
        4. Send alerts for significant findings
        """
        alerts: list[Alert] = []
        data: dict[str, Any] = {
            "cycle_started": datetime.utcnow().isoformat(),
            "checks_performed": [],
        }

        # 1. Traffic anomalies
        if self.context.gsc_client:
            traffic_result = await self._check_traffic_anomalies(params)
            data["traffic_check"] = traffic_result.data
            alerts.extend(traffic_result.alerts)
            data["checks_performed"].append("traffic_anomalies")

        # 2. Algorithm updates
        algo_result = await self._check_algorithm_updates(params)
        data["algorithm_check"] = algo_result.data
        alerts.extend(algo_result.alerts)
        data["checks_performed"].append("algorithm_updates")

        # 3. AIO changes (if queries provided)
        tracked_queries = params.get("tracked_queries", [])
        if tracked_queries and self.context.serp_client:
            aio_result = await self._check_aio_changes({"queries": tracked_queries})
            data["aio_check"] = aio_result.data
            alerts.extend(aio_result.alerts)
            data["checks_performed"].append("aio_changes")

        data["cycle_completed"] = datetime.utcnow().isoformat()
        data["total_alerts"] = len(alerts)

        # Send all alerts
        for alert in alerts:
            await self.send_alert(alert)

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data=data,
            alerts=alerts,
        )

    async def _check_traffic_anomalies(self, params: dict[str, Any]) -> AgentResult:
        """Check for significant traffic changes."""
        if not self.context.gsc_client:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "GSC client not configured"},
            )

        threshold = params.get("threshold_percent", 25)

        changes = await self.context.gsc_client.detect_traffic_changes(
            threshold_percent=threshold,
            comparison_days=params.get("comparison_days", 7),
        )

        alerts = []

        # Alert on significant drops
        significant_drops = [c for c in changes if c.change_percent < -30]

        for drop in significant_drops[:10]:  # Limit alerts
            severity = (
                AlertSeverity.CRITICAL if drop.change_percent < -50
                else AlertSeverity.WARNING
            )

            alerts.append(
                Alert(
                    type=AlertType.TRAFFIC_DROP,
                    severity=severity,
                    title=f"Traffic drop: {drop.query}",
                    message=(
                        f"'{drop.query}' dropped {abs(drop.change_percent):.0f}% "
                        f"({drop.previous_value} → {drop.current_value} clicks)"
                    ),
                    data={
                        "query": drop.query,
                        "previous_clicks": drop.previous_value,
                        "current_clicks": drop.current_value,
                        "change_percent": drop.change_percent,
                    },
                )
            )

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data={
                "total_changes": len(changes),
                "significant_drops": len(significant_drops),
                "threshold_used": threshold,
                "top_drops": [
                    {
                        "query": c.query,
                        "change": c.change_percent,
                    }
                    for c in significant_drops[:20]
                ],
            },
            alerts=alerts,
        )

    async def _check_algorithm_updates(self, params: dict[str, Any]) -> AgentResult:
        """Check for recent Google algorithm updates."""
        alerts = []
        updates_found = []

        # Check Google Search Status
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # This is a simplified check - in production you'd parse the actual status page
                response = await client.get(
                    "https://status.search.google.com/summary",
                    follow_redirects=True,
                )

                if "incident" in response.text.lower() or "issue" in response.text.lower():
                    updates_found.append({
                        "source": "Google Search Status",
                        "type": "potential_issue",
                        "url": "https://status.search.google.com/summary",
                    })

        except Exception as e:
            logger.warning("Failed to check Google status", error=str(e))

        # Check SEO news for algorithm mentions
        keywords = ["algorithm", "update", "core update", "ranking", "ai overview", "sge"]

        for feed_url in SEO_NEWS_FEEDS[:2]:  # Limit to avoid too many requests
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(feed_url)

                    # Simple keyword check in RSS
                    content_lower = response.text.lower()
                    for keyword in keywords:
                        if keyword in content_lower:
                            updates_found.append({
                                "source": feed_url,
                                "type": "news_mention",
                                "keyword": keyword,
                            })
                            break

            except Exception as e:
                logger.warning("Failed to check feed", url=feed_url, error=str(e))

        # Generate alert if updates found
        if updates_found:
            alerts.append(
                Alert(
                    type=AlertType.ALGORITHM_UPDATE,
                    severity=AlertSeverity.INFO,
                    title="Potential algorithm activity detected",
                    message=(
                        f"Found {len(updates_found)} potential update indicators. "
                        "Review sources for details."
                    ),
                    data={"updates": updates_found},
                )
            )

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data={
                "updates_found": len(updates_found),
                "details": updates_found,
            },
            alerts=alerts,
        )

    async def _check_aio_changes(self, params: dict[str, Any]) -> AgentResult:
        """Check for AI Overview status changes on tracked queries."""
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

        # Get previous AIO status from cache
        cache_key = "aio_status_cache"
        previous_status = self.context.cache_get(cache_key) or {}

        # Check current status
        results = await self.context.serp_client.check_queries_for_aio(
            queries[:50],  # Limit API calls
            concurrency=3,
        )

        alerts = []
        changes = []

        for result in results:
            query = result.query
            prev = previous_status.get(query, {})

            # Detect changes
            if not prev:
                # First time seeing this query
                if result.has_aio:
                    changes.append({
                        "query": query,
                        "change": "new_aio",
                        "client_cited": result.client_cited,
                    })

                    if not result.client_cited:
                        alerts.append(
                            Alert(
                                type=AlertType.AIO_DETECTED,
                                severity=AlertSeverity.WARNING,
                                title=f"New AIO detected: {query}",
                                message=(
                                    f"'{query}' now shows an AI Overview. "
                                    f"You are {'cited' if result.client_cited else 'NOT cited'}."
                                ),
                                data={
                                    "query": query,
                                    "competitors": result.competitor_citations[:5],
                                },
                            )
                        )

            else:
                # Check for status changes
                if result.has_aio != prev.get("has_aio"):
                    changes.append({
                        "query": query,
                        "change": "aio_appeared" if result.has_aio else "aio_removed",
                    })

                elif result.has_aio and result.client_cited != prev.get("client_cited"):
                    change_type = "gained_citation" if result.client_cited else "lost_citation"
                    changes.append({
                        "query": query,
                        "change": change_type,
                    })

                    severity = AlertSeverity.INFO if result.client_cited else AlertSeverity.WARNING

                    alerts.append(
                        Alert(
                            type=AlertType.AIO_DETECTED,
                            severity=severity,
                            title=f"AIO citation change: {query}",
                            message=(
                                f"'{query}': You {'gained' if result.client_cited else 'lost'} "
                                f"your AI Overview citation."
                            ),
                            data={"query": query, "now_cited": result.client_cited},
                        )
                    )

            # Update cache
            previous_status[query] = {
                "has_aio": result.has_aio,
                "client_cited": result.client_cited,
                "checked_at": datetime.utcnow().isoformat(),
            }

        # Save updated cache
        self.context.cache_set(cache_key, previous_status)

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data={
                "queries_checked": len(results),
                "queries_with_aio": len([r for r in results if r.has_aio]),
                "client_cited_count": len([r for r in results if r.has_aio and r.client_cited]),
                "changes_detected": len(changes),
                "changes": changes,
            },
            alerts=alerts,
        )

    async def _generate_daily_summary(self, params: dict[str, Any]) -> AgentResult:
        """Generate and send daily summary to Teams."""
        # Gather stats
        stats = {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "total_queries": 0,
            "aio_queries": 0,
            "citation_rate": 0,
            "traffic_alerts": 0,
            "new_recommendations": 0,
            "pages_analyzed": 0,
        }

        # Get traffic data
        if self.context.gsc_client:
            queries = await self.context.gsc_client.get_top_queries(limit=100, days=1)
            stats["total_queries"] = len(queries)
            stats["total_clicks"] = sum(q.clicks for q in queries)
            stats["total_impressions"] = sum(q.impressions for q in queries)

        # Get AIO stats from cache
        aio_cache = self.context.cache_get("aio_status_cache") or {}
        if aio_cache:
            aio_queries = [q for q, data in aio_cache.items() if data.get("has_aio")]
            cited_queries = [q for q, data in aio_cache.items() if data.get("client_cited")]

            stats["aio_queries"] = len(aio_queries)
            stats["citation_rate"] = (
                len(cited_queries) / len(aio_queries) * 100
                if aio_queries
                else 0
            )

        # Send summary to Teams
        if self.context.teams_notifier:
            await self.context.teams_notifier.send_daily_summary(stats)

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data={"summary": stats, "sent_to_teams": bool(self.context.teams_notifier)},
        )
