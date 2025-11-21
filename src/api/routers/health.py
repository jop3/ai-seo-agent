"""Health check endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends

from src.api.dependencies import SettingsDep

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ai-seo-agent",
    }


@router.get("/health/ready")
async def readiness_check(settings: SettingsDep) -> dict[str, Any]:
    """Readiness check with dependency status."""
    checks = {
        "azure_openai": bool(settings.azure.openai_endpoint),
        "gsc": bool(settings.google.gsc_property_url),
        "serp": bool(settings.serp.api_key.get_secret_value()) or settings.serp.provider == "scraper",
        "teams": bool(settings.alerts.teams_webhook_url.get_secret_value()),
        "optimizely": bool(settings.optimizely.api_key.get_secret_value()),
    }

    all_ready = all([checks["azure_openai"]])  # Only OpenAI is required

    return {
        "status": "ready" if all_ready else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """Liveness check."""
    return {"status": "alive"}
