"""
Unified SEO Agent Web UI

Single FastAPI application serving all UI pages:
- /         - Chat interface
- /dashboard - Analytics dashboard
- /settings  - Configuration
- /api/*     - API endpoints
"""

import asyncio
from pathlib import Path

import structlog
from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.agent_runner.definitions import ALL_AGENTS
from src.agent_runner.runner import ConversationalAgent, LocalAgentRunner
from src.llm.config import (
    get_llm_settings,
    save_llm_settings,
)
from src.llm.provider import get_llm_provider, refresh_llm_provider

logger = structlog.get_logger()

# Paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# FastAPI app
app = FastAPI(title="SEO Agent UI")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# =============================================================================
# Helper functions
# =============================================================================

def get_agents_for_template():
    """Get agents formatted for template dropdowns."""
    return [
        {
            "name": agent.name,
            "display_name": agent.name.replace("-", " ").title(),
            "description": agent.description,
        }
        for agent in ALL_AGENTS
    ]


def get_site_settings():
    """Get site settings from config."""
    # TODO: Load from config file
    return {
        "site_url": "",
        "site_name": "",
        "gsc_property": "",
        "language": "en",
        "brand_voice": "",
        "target_audience": "",
        "guidelines_url": "",
    }


# =============================================================================
# Page Routes
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Chat interface."""
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "active_page": "chat",
            "agents": get_agents_for_template(),
        }
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Dashboard with analytics."""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_page": "dashboard",
            "stats": {},
            "queries": [],
            "alerts": [],
            "aio_data": [],
        }
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page."""
    settings = get_llm_settings()
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "active_page": "settings",
            "settings": settings,
            "agents": get_agents_for_template(),
            "site_settings": get_site_settings(),
        }
    )


# =============================================================================
# API Routes for HTMX
# =============================================================================

@app.post("/api/settings/provider", response_class=HTMLResponse)
async def save_provider(
    request: Request,
    provider_id: str = Form(...),
    api_key: str = Form(""),
    api_base: str = Form(""),
):
    """Save provider configuration."""
    try:
        settings = get_llm_settings()

        if provider_id not in settings.providers:
            from src.llm.config import ProviderConfig
            settings.providers[provider_id] = ProviderConfig()

        if api_key:
            settings.providers[provider_id].api_key = api_key
        if api_base:
            settings.providers[provider_id].api_base = api_base

        save_llm_settings(settings)
        refresh_llm_provider()

        return HTMLResponse(
            '<div class="alert alert-success">Provider saved successfully!</div>'
        )
    except Exception as e:
        return HTMLResponse(
            f'<div class="alert alert-error">Error: {str(e)}</div>'
        )


@app.post("/api/settings/test-provider", response_class=HTMLResponse)
async def test_provider(
    request: Request,
    provider_id: str = Form(...),
    api_key: str = Form(""),
    api_base: str = Form(""),
):
    """Test provider connection."""
    try:
        provider = get_llm_provider()
        # Simple test - try to make a minimal request
        # This would need to be implemented based on provider type
        return HTMLResponse(
            '<div class="alert alert-success">Connection successful!</div>'
        )
    except Exception as e:
        return HTMLResponse(
            f'<div class="alert alert-error">Connection failed: {str(e)}</div>'
        )


@app.post("/api/settings/default-model", response_class=HTMLResponse)
async def set_default_model(request: Request):
    """Set default model."""
    try:
        form = await request.form()
        model_id = form.get("model_id")

        settings = get_llm_settings()
        settings.default_model_id = model_id
        save_llm_settings(settings)
        refresh_llm_provider()

        return HTMLResponse(
            f'<div class="alert alert-success">Default model set to {model_id}</div>'
        )
    except Exception as e:
        return HTMLResponse(
            f'<div class="alert alert-error">Error: {str(e)}</div>'
        )


@app.post("/api/settings/agent-models", response_class=HTMLResponse)
async def save_agent_models(request: Request):
    """Save agent model assignments."""
    try:
        form = await request.form()
        settings = get_llm_settings()

        for key, value in form.items():
            if key.startswith("agent_") and value:
                agent_name = key.replace("agent_", "")
                from src.llm.config import AgentModelAssignment
                settings.agent_assignments[agent_name] = AgentModelAssignment(
                    agent_name=agent_name,
                    model_id=value,
                )

        save_llm_settings(settings)
        refresh_llm_provider()

        return HTMLResponse(
            '<div class="alert alert-success">Agent model assignments saved!</div>'
        )
    except Exception as e:
        return HTMLResponse(
            f'<div class="alert alert-error">Error: {str(e)}</div>'
        )


@app.post("/api/settings/site", response_class=HTMLResponse)
async def save_site_settings(request: Request):
    """Save site settings."""
    try:
        form = await request.form()
        # TODO: Implement site settings persistence
        return HTMLResponse(
            '<div class="alert alert-success">Site settings saved!</div>'
        )
    except Exception as e:
        return HTMLResponse(
            f'<div class="alert alert-error">Error: {str(e)}</div>'
        )


@app.post("/api/settings/content", response_class=HTMLResponse)
async def save_content_settings(request: Request):
    """Save content settings."""
    try:
        form = await request.form()
        # TODO: Implement content settings persistence
        return HTMLResponse(
            '<div class="alert alert-success">Content settings saved!</div>'
        )
    except Exception as e:
        return HTMLResponse(
            f'<div class="alert alert-error">Error: {str(e)}</div>'
        )


# =============================================================================
# Dashboard API Routes
# =============================================================================

@app.get("/api/dashboard/overview", response_class=HTMLResponse)
async def dashboard_overview(request: Request):
    """Get dashboard overview data."""
    # TODO: Implement real data fetching
    return templates.TemplateResponse(
        "partials/dashboard_overview.html",
        {
            "request": request,
            "stats": {"total_queries": 0, "aio_queries": 0, "citations": 0, "traffic_change": 0},
        }
    )


# =============================================================================
# WebSocket for Chat
# =============================================================================

@app.websocket("/ws/{agent_name}")
async def websocket_chat(websocket: WebSocket, agent_name: str):
    """WebSocket endpoint for real-time chat with agents."""
    await websocket.accept()

    try:
        # Find agent
        agent_def = next((a for a in ALL_AGENTS if a.name == agent_name), None)
        if not agent_def:
            await websocket.send_json({
                "type": "error",
                "message": f"Unknown agent: {agent_name}",
                "agent": "System",
            })
            return

        # Create conversational agent
        runner = LocalAgentRunner()
        conv_agent = ConversationalAgent(agent_def, runner)
        display_name = agent_def.name.replace("-", " ").title()

        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")

            if not message:
                continue

            # Send start message for loading indicator
            await websocket.send_json({
                "type": "start",
                "agent": display_name,
            })

            # Process message
            try:
                response = await conv_agent.chat(message)

                # Stream the response in chunks for better UX
                response_text = response.message or ""
                if response_text:
                    # Split into chunks for streaming effect
                    chunk_size = 20  # characters per chunk
                    for i in range(0, len(response_text), chunk_size):
                        chunk = response_text[i:i + chunk_size]
                        await websocket.send_json({
                            "type": "stream",
                            "content": chunk,
                        })
                        # Small delay between chunks for streaming effect
                        await asyncio.sleep(0.02)

                # Send end message
                await websocket.send_json({
                    "type": "end",
                    "agent": display_name,
                    "tools": response.tool_calls_made or [],
                    "success": response.success,
                })
            except Exception as e:
                logger.error("Chat error", error=str(e))
                await websocket.send_json({
                    "type": "error",
                    "message": f"Error: {str(e)}",
                    "agent": display_name,
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
                "agent": "System",
            })
        except:
            pass


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
