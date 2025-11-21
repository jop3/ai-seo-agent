"""
Adaptive Card builder for Teams UI.

Creates rich, interactive cards for Teams conversations.
"""

from typing import Any

from src.azure_agents.definitions import AgentDefinition


class AdaptiveCardBuilder:
    """Builds Adaptive Cards for Teams bot responses."""

    def create_welcome_card(self) -> dict[str, Any]:
        """Create welcome card for new users."""
        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "size": "Large",
                    "weight": "Bolder",
                    "text": "Welcome to SEO Agent!"
                },
                {
                    "type": "TextBlock",
                    "text": "I help you optimize your website for Google's AI Overviews and stay ahead of traffic changes.",
                    "wrap": True
                },
                {
                    "type": "TextBlock",
                    "text": "Here's what I can do:",
                    "weight": "Bolder",
                    "spacing": "Medium"
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Analyze", "value": "Check which queries trigger AI Overviews"},
                        {"title": "Monitor", "value": "Track traffic changes and get alerts"},
                        {"title": "Optimize", "value": "Generate schema markup and FAQs"},
                        {"title": "Test", "value": "Check if AI agents can use your pages"}
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Run Analysis",
                    "data": {"action": "run_analysis"}
                },
                {
                    "type": "Action.Submit",
                    "title": "Show Commands",
                    "data": {"action": "show_help"}
                }
            ]
        }

    def create_help_card(self) -> dict[str, Any]:
        """Create help card with available commands."""
        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "size": "Large",
                    "weight": "Bolder",
                    "text": "SEO Agent Commands"
                },
                {
                    "type": "TextBlock",
                    "text": "You can use these commands or just ask me naturally:",
                    "wrap": True
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "/analyze", "value": "Run full SEO analysis"},
                        {"title": "/check <queries>", "value": "Check queries for AI Overviews"},
                        {"title": "/status", "value": "Show current status"},
                        {"title": "/agents", "value": "List available agents"},
                        {"title": "/help", "value": "Show this help"}
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": "**Natural language examples:**",
                    "spacing": "Medium"
                },
                {
                    "type": "TextBlock",
                    "text": "• \"What's our AIO status for ibuprofen queries?\"\n• \"Generate FAQ for paracetamol side effects\"\n• \"Why did our traffic drop last week?\"",
                    "wrap": True
                }
            ]
        }

    def create_agents_list_card(self, agents: list[AgentDefinition]) -> dict[str, Any]:
        """Create card listing available agents."""
        agent_items = []
        for agent in agents:
            agent_items.append({
                "type": "Container",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": agent.name,
                        "weight": "Bolder"
                    },
                    {
                        "type": "TextBlock",
                        "text": agent.description,
                        "wrap": True,
                        "size": "Small"
                    },
                    {
                        "type": "TextBlock",
                        "text": f"Tools: {', '.join(t.name for t in agent.tools[:3])}...",
                        "size": "Small",
                        "isSubtle": True
                    }
                ],
                "separator": True
            })

        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "size": "Large",
                    "weight": "Bolder",
                    "text": "Available Agents"
                },
                *agent_items
            ]
        }

    def create_response_card(
        self,
        title: str,
        message: str,
        tools_used: list[str] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a general response card."""
        body = [
            {
                "type": "TextBlock",
                "size": "Medium",
                "weight": "Bolder",
                "text": title
            },
            {
                "type": "TextBlock",
                "text": message,
                "wrap": True
            }
        ]

        if tools_used:
            body.append({
                "type": "TextBlock",
                "text": f"Tools used: {', '.join(tools_used)}",
                "size": "Small",
                "isSubtle": True
            })

        actions = []
        if data:
            actions.append({
                "type": "Action.Submit",
                "title": "Show Details",
                "data": {"action": "show_details", "data": data}
            })

        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": body,
            "actions": actions
        }

    def create_analysis_results_card(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create card for analysis results."""
        aio = data.get("aio_analysis", {})
        traffic = data.get("traffic_changes", {})

        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "size": "Large",
                    "weight": "Bolder",
                    "text": "SEO Analysis Results"
                },
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {"type": "TextBlock", "text": "Queries Analyzed", "weight": "Bolder"},
                                {"type": "TextBlock", "text": str(data.get("total_queries_analyzed", 0)), "size": "ExtraLarge"}
                            ]
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {"type": "TextBlock", "text": "With AI Overview", "weight": "Bolder"},
                                {"type": "TextBlock", "text": str(aio.get("queries_with_aio", 0)), "size": "ExtraLarge", "color": "Attention"}
                            ]
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {"type": "TextBlock", "text": "Citation Rate", "weight": "Bolder"},
                                {"type": "TextBlock", "text": f"{aio.get('citation_rate', 0):.1f}%", "size": "ExtraLarge", "color": "Good" if aio.get("citation_rate", 0) > 50 else "Attention"}
                            ]
                        }
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": f"**Traffic Drops:** {traffic.get('significant_drops', 0)} significant drops detected",
                    "separator": True,
                    "spacing": "Medium"
                },
                {
                    "type": "TextBlock",
                    "text": "Top Opportunities:",
                    "weight": "Bolder",
                    "spacing": "Medium"
                },
                {
                    "type": "TextBlock",
                    "text": self._format_opportunities(aio.get("high_risk_queries", [])[:5]),
                    "wrap": True
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Generate Recommendations",
                    "data": {"action": "generate_recommendations", "data": data}
                },
                {
                    "type": "Action.Submit",
                    "title": "View Full Report",
                    "data": {"action": "show_details", "data": data}
                }
            ]
        }

    def create_aio_check_card(
        self,
        queries: list[str],
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create card for AIO check results."""
        results = data.get("results", [])

        result_items = []
        for result in results[:10]:
            status_color = "Good" if result.get("client_cited") else "Attention" if result.get("has_aio") else "Default"
            status_text = "Cited" if result.get("client_cited") else "Not Cited" if result.get("has_aio") else "No AIO"

            result_items.append({
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [{"type": "TextBlock", "text": result.get("query", ""), "wrap": True}]
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [{"type": "TextBlock", "text": "AIO" if result.get("has_aio") else "-", "weight": "Bolder"}]
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [{"type": "TextBlock", "text": status_text, "color": status_color}]
                    }
                ]
            })

        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "size": "Large",
                    "weight": "Bolder",
                    "text": "AI Overview Check Results"
                },
                {
                    "type": "TextBlock",
                    "text": f"Checked {len(results)} queries",
                    "isSubtle": True
                },
                *result_items
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Optimize Not-Cited Queries",
                    "data": {
                        "action": "generate_recommendations",
                        "queries": [r["query"] for r in results if r.get("has_aio") and not r.get("client_cited")]
                    }
                }
            ]
        }

    def create_status_card(self, status: dict[str, Any]) -> dict[str, Any]:
        """Create status summary card."""
        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "size": "Large",
                    "weight": "Bolder",
                    "text": "SEO Agent Status"
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Status", "value": status.get("status", "unknown")},
                        {"title": "Last Analysis", "value": status.get("last_analysis", "never")},
                        {"title": "Tracked Queries", "value": str(status.get("tracked_queries", 0))},
                        {"title": "AIO Queries", "value": str(status.get("aio_queries", 0))},
                        {"title": "Citation Rate", "value": status.get("citation_rate", "N/A")},
                        {"title": "Pending Alerts", "value": str(status.get("pending_alerts", 0))}
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Run Analysis Now",
                    "data": {"action": "run_analysis"}
                }
            ]
        }

    def create_recommendations_card(
        self,
        recommendations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create card for optimization recommendations."""
        rec_items = []
        for i, rec in enumerate(recommendations[:5]):
            rec_items.append({
                "type": "Container",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": f"**{i+1}. {rec.get('title', 'Recommendation')}**",
                        "wrap": True
                    },
                    {
                        "type": "TextBlock",
                        "text": rec.get("description", ""),
                        "wrap": True,
                        "size": "Small"
                    },
                    {
                        "type": "ColumnSet",
                        "columns": [
                            {
                                "type": "Column",
                                "width": "auto",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": f"Priority: {rec.get('priority', 'medium')}",
                                        "size": "Small",
                                        "color": "Attention" if rec.get("priority") == "high" else "Default"
                                    }
                                ]
                            },
                            {
                                "type": "Column",
                                "width": "stretch",
                                "items": []
                            },
                            {
                                "type": "Column",
                                "width": "auto",
                                "items": [
                                    {
                                        "type": "ActionSet",
                                        "actions": [
                                            {
                                                "type": "Action.Submit",
                                                "title": "Approve",
                                                "data": {
                                                    "action": "approve_recommendation",
                                                    "recommendation_id": rec.get("id")
                                                }
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "separator": True
            })

        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "size": "Large",
                    "weight": "Bolder",
                    "text": "Optimization Recommendations"
                },
                {
                    "type": "TextBlock",
                    "text": f"Found {len(recommendations)} recommendations",
                    "isSubtle": True
                },
                *rec_items
            ]
        }

    def create_details_card(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create card showing detailed data."""
        import json

        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "size": "Large",
                    "weight": "Bolder",
                    "text": "Details"
                },
                {
                    "type": "TextBlock",
                    "text": f"```json\n{json.dumps(data, indent=2)[:2000]}\n```",
                    "wrap": True,
                    "fontType": "Monospace"
                }
            ]
        }

    def _format_opportunities(self, queries: list[str]) -> str:
        """Format opportunity queries as bullet list."""
        if not queries:
            return "No high-risk queries identified"
        return "\n".join(f"• {q}" for q in queries[:5])
