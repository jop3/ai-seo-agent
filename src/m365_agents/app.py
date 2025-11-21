"""
FastAPI app for Microsoft 365 Agents / Bot Framework integration.

This provides the webhook endpoint that Azure Bot Service calls.
"""

from fastapi import FastAPI, Request, Response
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity

from src.m365_agents.bot import SEOAgentBot
from src.config import get_settings

# Bot Framework adapter settings
settings = get_settings()

ADAPTER_SETTINGS = BotFrameworkAdapterSettings(
    app_id=settings.azure.client_id,
    app_password=settings.azure.client_secret.get_secret_value(),
)

ADAPTER = BotFrameworkAdapter(ADAPTER_SETTINGS)
BOT = SEOAgentBot()


# Error handler
async def on_error(context, error):
    """Handle errors in the bot."""
    print(f"Bot error: {error}")
    await context.send_activity("Sorry, something went wrong. Please try again.")


ADAPTER.on_turn_error = on_error


def create_bot_app() -> FastAPI:
    """Create the bot FastAPI app."""
    app = FastAPI(
        title="SEO Agent Bot",
        description="Microsoft Teams bot for SEO Agent",
    )

    @app.post("/api/messages")
    async def messages(request: Request) -> Response:
        """Handle incoming messages from Bot Framework."""
        if "application/json" not in request.headers.get("Content-Type", ""):
            return Response(status_code=415)

        body = await request.json()
        activity = Activity().deserialize(body)

        auth_header = request.headers.get("Authorization", "")

        response = await ADAPTER.process_activity(
            activity,
            auth_header,
            BOT.on_turn,
        )

        if response:
            return Response(
                content=response.body,
                status_code=response.status,
            )

        return Response(status_code=201)

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "bot": "SEO Agent"}

    return app


# Create the app instance
bot_app = create_bot_app()
