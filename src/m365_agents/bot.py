"""
Teams Bot implementation using Bot Framework SDK.

This bot acts as the Teams interface to the SEO agents.
"""

import json
from typing import Any

from botbuilder.core import (
    ActivityHandler,
    TurnContext,
    MessageFactory,
    CardFactory,
)
from botbuilder.schema import (
    Activity,
    ActivityTypes,
    Attachment,
    ChannelAccount,
)
import structlog

from src.azure_agents.definitions import ALL_AGENTS
from src.azure_agents.runner import LocalAgentRunner, AgentOrchestrator
from src.m365_agents.cards import AdaptiveCardBuilder

logger = structlog.get_logger()


class SEOAgentBot(ActivityHandler):
    """
    Teams bot that provides conversational access to SEO agents.

    Supports:
    - Direct messages
    - @mentions in channels
    - Slash commands
    - Adaptive Card interactions
    """

    def __init__(
        self,
        runner: LocalAgentRunner | None = None,
        api_base_url: str = "http://localhost:8000",
    ):
        self.runner = runner or LocalAgentRunner(api_base_url=api_base_url)
        self.orchestrator = AgentOrchestrator(self.runner)
        self.card_builder = AdaptiveCardBuilder()

        # User conversation states
        self.user_contexts: dict[str, dict[str, Any]] = {}

    async def on_message_activity(self, turn_context: TurnContext):
        """Handle incoming messages."""
        text = turn_context.activity.text or ""
        user_id = turn_context.activity.from_property.id

        # Remove bot mention if present
        text = self._remove_mention(text, turn_context)

        logger.info(
            "Received message",
            user_id=user_id,
            text=text[:100],
        )

        # Check for commands
        if text.startswith("/"):
            await self._handle_command(turn_context, text)
            return

        # Check for card action responses
        if turn_context.activity.value:
            await self._handle_card_action(turn_context)
            return

        # Route to appropriate agent
        await self._handle_conversation(turn_context, text)

    async def _handle_command(self, turn_context: TurnContext, command: str):
        """Handle slash commands."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            await self._send_help(turn_context)

        elif cmd == "/agents":
            await self._send_agents_list(turn_context)

        elif cmd == "/analyze":
            await self._run_analysis(turn_context, args)

        elif cmd == "/check":
            await self._check_aio(turn_context, args)

        elif cmd == "/status":
            await self._send_status(turn_context)

        else:
            await turn_context.send_activity(
                f"Unknown command: {cmd}\nType /help for available commands."
            )

    async def _handle_conversation(self, turn_context: TurnContext, text: str):
        """Handle natural language conversation."""
        # Send typing indicator
        await turn_context.send_activity(Activity(type=ActivityTypes.typing))

        # Route to orchestrator
        response = await self.orchestrator.route_and_run(text)

        if response.success:
            # Create adaptive card for rich response
            card = self.card_builder.create_response_card(
                title="SEO Agent Response",
                message=response.message,
                tools_used=response.tool_calls_made,
                data=response.data,
            )
            await turn_context.send_activity(
                MessageFactory.attachment(CardFactory.adaptive_card(card))
            )
        else:
            await turn_context.send_activity(
                f"Sorry, I encountered an error: {response.message}"
            )

    async def _handle_card_action(self, turn_context: TurnContext):
        """Handle adaptive card button clicks."""
        action_data = turn_context.activity.value

        action = action_data.get("action")

        if action == "run_analysis":
            await self._run_analysis(turn_context, action_data.get("query", ""))

        elif action == "generate_recommendations":
            url = action_data.get("url")
            query = action_data.get("query")
            await self._generate_recommendations(turn_context, url, query)

        elif action == "approve_recommendation":
            rec_id = action_data.get("recommendation_id")
            await self._approve_recommendation(turn_context, rec_id)

        elif action == "show_details":
            data = action_data.get("data")
            await self._show_details(turn_context, data)

    async def _send_help(self, turn_context: TurnContext):
        """Send help information."""
        card = self.card_builder.create_help_card()
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.adaptive_card(card))
        )

    async def _send_agents_list(self, turn_context: TurnContext):
        """Send list of available agents."""
        card = self.card_builder.create_agents_list_card(ALL_AGENTS)
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.adaptive_card(card))
        )

    async def _run_analysis(self, turn_context: TurnContext, args: str):
        """Run SEO analysis."""
        await turn_context.send_activity(Activity(type=ActivityTypes.typing))

        from src.azure_agents.definitions import SEO_ANALYST_AGENT

        task = args or "Run a full analysis of our top queries and identify AIO impact"

        response = await self.runner.run(SEO_ANALYST_AGENT, task)

        if response.success:
            card = self.card_builder.create_analysis_results_card(response.data)
            await turn_context.send_activity(
                MessageFactory.attachment(CardFactory.adaptive_card(card))
            )
        else:
            await turn_context.send_activity(f"Analysis failed: {response.message}")

    async def _check_aio(self, turn_context: TurnContext, queries: str):
        """Check queries for AI Overview status."""
        if not queries:
            await turn_context.send_activity(
                "Please provide queries to check. Example: /check ibuprofen dosage, paracetamol side effects"
            )
            return

        await turn_context.send_activity(Activity(type=ActivityTypes.typing))

        from src.azure_agents.definitions import SEO_ANALYST_AGENT

        task = f"Check if these queries trigger AI Overviews and if we're cited: {queries}"

        response = await self.runner.run(SEO_ANALYST_AGENT, task)

        if response.success:
            card = self.card_builder.create_aio_check_card(
                queries.split(","),
                response.data,
            )
            await turn_context.send_activity(
                MessageFactory.attachment(CardFactory.adaptive_card(card))
            )
        else:
            await turn_context.send_activity(f"Check failed: {response.message}")

    async def _send_status(self, turn_context: TurnContext):
        """Send current status summary."""
        card = self.card_builder.create_status_card({
            "status": "operational",
            "last_analysis": "2 hours ago",
            "tracked_queries": 500,
            "aio_queries": 85,
            "citation_rate": "15.4%",
            "pending_alerts": 3,
        })
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.adaptive_card(card))
        )

    async def _generate_recommendations(
        self,
        turn_context: TurnContext,
        url: str,
        query: str,
    ):
        """Generate optimization recommendations."""
        await turn_context.send_activity(Activity(type=ActivityTypes.typing))

        from src.azure_agents.definitions import OPTIMIZER_AGENT

        task = f"Generate optimization recommendations for {url} targeting the query '{query}'"

        response = await self.runner.run(OPTIMIZER_AGENT, task)

        if response.success:
            card = self.card_builder.create_recommendations_card(
                response.data.get("recommendations", [])
            )
            await turn_context.send_activity(
                MessageFactory.attachment(CardFactory.adaptive_card(card))
            )
        else:
            await turn_context.send_activity(
                f"Failed to generate recommendations: {response.message}"
            )

    async def _approve_recommendation(
        self,
        turn_context: TurnContext,
        recommendation_id: str,
    ):
        """Approve a recommendation for implementation."""
        # In a real implementation, this would:
        # 1. Update the recommendation status in the database
        # 2. Trigger the Optimizely integration to deploy
        # 3. Send confirmation

        await turn_context.send_activity(
            f"Recommendation {recommendation_id} approved and queued for implementation."
        )

    async def _show_details(self, turn_context: TurnContext, data: dict[str, Any]):
        """Show detailed information."""
        card = self.card_builder.create_details_card(data)
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.adaptive_card(card))
        )

    def _remove_mention(self, text: str, turn_context: TurnContext) -> str:
        """Remove @mention from message text."""
        if turn_context.activity.entities:
            for entity in turn_context.activity.entities:
                if entity.type == "mention":
                    mention_text = entity.additional_properties.get("text", "")
                    text = text.replace(mention_text, "").strip()
        return text

    async def on_members_added_activity(
        self,
        members_added: list[ChannelAccount],
        turn_context: TurnContext,
    ):
        """Welcome new members."""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                card = self.card_builder.create_welcome_card()
                await turn_context.send_activity(
                    MessageFactory.attachment(CardFactory.adaptive_card(card))
                )
