"""Microsoft Teams notification integration."""

from datetime import datetime
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models.agents import Alert, AlertSeverity

logger = structlog.get_logger()


class TeamsNotifier:
    """Send notifications to Microsoft Teams via webhooks."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def send_message(self, message: dict[str, Any]) -> bool:
        """Send a raw adaptive card message to Teams."""
        if not self.webhook_url:
            logger.warning("Teams webhook URL not configured")
            return False

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                logger.info("Teams notification sent successfully")
                return True
            else:
                logger.error(
                    "Failed to send Teams notification",
                    status=response.status_code,
                    response=response.text,
                )
                return False

    async def send_alert(self, alert: Alert) -> bool:
        """Send a formatted alert to Teams."""
        color = self._get_severity_color(alert.severity)
        icon = self._get_severity_icon(alert.severity)

        # Adaptive Card format
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Large",
                                "weight": "Bolder",
                                "text": f"{icon} {alert.title}",
                                "color": color,
                            },
                            {
                                "type": "TextBlock",
                                "text": alert.message,
                                "wrap": True,
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Type", "value": alert.type.value},
                                    {"title": "Severity", "value": alert.severity.value},
                                    {
                                        "title": "Time",
                                        "value": alert.created_at.strftime("%Y-%m-%d %H:%M UTC"),
                                    },
                                ],
                            },
                        ],
                        "actions": [
                            {
                                "type": "Action.OpenUrl",
                                "title": "View Dashboard",
                                "url": "https://your-dashboard-url.com",  # TODO: Configure
                            }
                        ],
                    },
                }
            ],
        }

        # Add data details if present
        if alert.data:
            details = "\n".join(f"- **{k}**: {v}" for k, v in alert.data.items())
            card["attachments"][0]["content"]["body"].append(
                {
                    "type": "TextBlock",
                    "text": f"**Details:**\n{details}",
                    "wrap": True,
                    "separator": True,
                }
            )

        return await self.send_message(card)

    async def send_traffic_drop_alert(
        self,
        query: str,
        previous_clicks: int,
        current_clicks: int,
        change_percent: float,
        likely_cause: str | None = None,
    ) -> bool:
        """Send a traffic drop alert."""
        alert = Alert(
            type="traffic_drop",
            severity=AlertSeverity.WARNING if change_percent > -50 else AlertSeverity.CRITICAL,
            title=f"Traffic Drop Detected: {query}",
            message=f"Query '{query}' has dropped {abs(change_percent):.1f}% in clicks.",
            data={
                "query": query,
                "previous_clicks": previous_clicks,
                "current_clicks": current_clicks,
                "change_percent": f"{change_percent:.1f}%",
                "likely_cause": likely_cause or "Unknown",
            },
        )
        return await self.send_alert(alert)

    async def send_aio_detected_alert(
        self,
        query: str,
        client_cited: bool,
        competitors_cited: list[str],
    ) -> bool:
        """Send an alert when AI Overview is detected for a tracked query."""
        severity = AlertSeverity.INFO if client_cited else AlertSeverity.WARNING

        alert = Alert(
            type="aio_detected",
            severity=severity,
            title=f"AI Overview Detected: {query}",
            message=(
                f"Query '{query}' now shows an AI Overview. "
                f"{'You ARE cited!' if client_cited else 'You are NOT cited.'}"
            ),
            data={
                "query": query,
                "client_cited": "Yes" if client_cited else "No",
                "competitors_cited": ", ".join(competitors_cited[:5]) or "None",
            },
        )
        return await self.send_alert(alert)

    async def send_daily_summary(
        self,
        stats: dict[str, Any],
    ) -> bool:
        """Send a daily summary to Teams."""
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Large",
                                "weight": "Bolder",
                                "text": "📊 Daily SEO Agent Summary",
                            },
                            {
                                "type": "TextBlock",
                                "text": datetime.utcnow().strftime("%Y-%m-%d"),
                                "isSubtle": True,
                            },
                            {
                                "type": "ColumnSet",
                                "columns": [
                                    {
                                        "type": "Column",
                                        "width": "stretch",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "text": "Queries Tracked",
                                                "weight": "Bolder",
                                            },
                                            {
                                                "type": "TextBlock",
                                                "text": str(stats.get("total_queries", 0)),
                                                "size": "ExtraLarge",
                                            },
                                        ],
                                    },
                                    {
                                        "type": "Column",
                                        "width": "stretch",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "text": "AIO Queries",
                                                "weight": "Bolder",
                                            },
                                            {
                                                "type": "TextBlock",
                                                "text": str(stats.get("aio_queries", 0)),
                                                "size": "ExtraLarge",
                                                "color": "Attention",
                                            },
                                        ],
                                    },
                                    {
                                        "type": "Column",
                                        "width": "stretch",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "text": "Citation Rate",
                                                "weight": "Bolder",
                                            },
                                            {
                                                "type": "TextBlock",
                                                "text": f"{stats.get('citation_rate', 0):.1f}%",
                                                "size": "ExtraLarge",
                                                "color": "Good" if stats.get("citation_rate", 0) > 50 else "Attention",
                                            },
                                        ],
                                    },
                                ],
                            },
                            {
                                "type": "TextBlock",
                                "text": f"**Traffic Alerts:** {stats.get('traffic_alerts', 0)}",
                                "separator": True,
                            },
                            {
                                "type": "TextBlock",
                                "text": f"**New Recommendations:** {stats.get('new_recommendations', 0)}",
                            },
                            {
                                "type": "TextBlock",
                                "text": f"**Pages Analyzed:** {stats.get('pages_analyzed', 0)}",
                            },
                        ],
                    },
                }
            ],
        }

        return await self.send_message(card)

    def _get_severity_color(self, severity: AlertSeverity) -> str:
        """Get adaptive card color for severity."""
        colors = {
            AlertSeverity.INFO: "Default",
            AlertSeverity.WARNING: "Warning",
            AlertSeverity.ERROR: "Attention",
            AlertSeverity.CRITICAL: "Attention",
        }
        return colors.get(severity, "Default")

    def _get_severity_icon(self, severity: AlertSeverity) -> str:
        """Get icon for severity level."""
        icons = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.CRITICAL: "🚨",
        }
        return icons.get(severity, "📢")
