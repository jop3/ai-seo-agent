"""FastAPI main application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import agents, analysis, health, optimizations, webhooks, workflows
from src.config import get_settings

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    settings = get_settings()
    logger.info(
        "Starting AI SEO Agent API",
        environment=settings.app_env,
        debug=settings.app_debug,
    )

    # Initialize services
    # TODO: Initialize database connections, cache, etc.

    yield

    # Cleanup
    logger.info("Shutting down AI SEO Agent API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="AI SEO Agent",
        description="AI-powered SEO optimization for the AI Overview era",
        version="0.1.0",
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_debug else ["https://your-domain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
    app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["Workflows"])
    app.include_router(optimizations.router, prefix="/api/v1/optimizations", tags=["Optimizations"])
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])

    return app


app = create_app()
