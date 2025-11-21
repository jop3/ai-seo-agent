"""Onboarding API endpoints for guided workflow configuration."""

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.orchestrator.onboarding import ConfigManager, quick_setup
from src.orchestrator.schemas import WorkflowInput

logger = structlog.get_logger()
router = APIRouter()


class QuickSetupRequest(BaseModel):
    """Request for quick setup."""
    domain: str
    competitors: list[str] = []
    business_name: str | None = None


class ConfigSaveRequest(BaseModel):
    """Request to save configuration."""
    name: str = "default"
    config: WorkflowInput


class ConfigResponse(BaseModel):
    """Response with configuration details."""
    name: str
    config: WorkflowInput


class ConfigListResponse(BaseModel):
    """Response with list of configurations."""
    configs: list[str]


class OnboardingQuestions(BaseModel):
    """Structured onboarding questions for frontend."""
    site_type: dict[str, Any]
    basic_info: dict[str, Any]
    competitors: dict[str, Any]
    business_info: dict[str, Any]
    author_info: dict[str, Any]
    thresholds: dict[str, Any]


@router.get("/questions")
async def get_onboarding_questions():
    """
    Get structured onboarding questions for frontend forms.

    Returns a JSON structure that frontends can use to build interactive forms.
    """
    return {
        "site_type": {
            "question": "What type of site are you setting up?",
            "type": "select",
            "required": True,
            "options": [
                {"value": "ecommerce", "label": "E-commerce / Online Store"},
                {"value": "local", "label": "Local Business (restaurant, shop, service)"},
                {"value": "content", "label": "Content / Blog / News Site"},
                {"value": "saas", "label": "SaaS / Software Product"},
                {"value": "corporate", "label": "Corporate / Brand Site"},
                {"value": "other", "label": "Other"},
            ],
            "default": "ecommerce",
        },
        "basic_info": {
            "title": "Basic Information",
            "fields": [
                {
                    "name": "domain",
                    "label": "Your domain",
                    "type": "text",
                    "required": True,
                    "placeholder": "example.com",
                    "help": "Your primary domain without https://",
                },
                {
                    "name": "property_url",
                    "label": "Full site URL",
                    "type": "url",
                    "required": True,
                    "placeholder": "https://example.com",
                    "help": "Complete URL including protocol",
                },
            ],
        },
        "competitors": {
            "title": "Competitors",
            "description": "Add 3-5 main competitors for competitive analysis",
            "type": "array",
            "required": False,
            "fields": [
                {
                    "name": "domain",
                    "label": "Competitor domain",
                    "type": "text",
                    "placeholder": "competitor.com",
                },
                {
                    "name": "priority",
                    "label": "Priority",
                    "type": "select",
                    "options": ["high", "medium", "low"],
                    "default": "medium",
                },
            ],
        },
        "business_info": {
            "title": "Business Information",
            "description": "Improves schema generation and local SEO",
            "required": False,
            "fields": [
                {
                    "name": "name",
                    "label": "Business name",
                    "type": "text",
                    "required": True,
                },
                {
                    "name": "description",
                    "label": "Description",
                    "type": "textarea",
                    "placeholder": "Brief description of your business",
                },
                {
                    "name": "phone",
                    "label": "Phone",
                    "type": "tel",
                    "placeholder": "+1-555-0100",
                },
                {
                    "name": "email",
                    "label": "Email",
                    "type": "email",
                },
                {
                    "name": "street_address",
                    "label": "Street Address",
                    "type": "text",
                    "condition": {"site_type": "local"},
                },
                {
                    "name": "city",
                    "label": "City",
                    "type": "text",
                    "condition": {"site_type": "local"},
                },
                {
                    "name": "state",
                    "label": "State/Province",
                    "type": "text",
                    "condition": {"site_type": "local"},
                },
                {
                    "name": "postal_code",
                    "label": "Postal Code",
                    "type": "text",
                    "condition": {"site_type": "local"},
                },
                {
                    "name": "logo_url",
                    "label": "Logo URL",
                    "type": "url",
                },
            ],
        },
        "author_info": {
            "title": "Default Author",
            "description": "For E-E-A-T analysis and content schema",
            "required": False,
            "condition": {"site_type": ["content", "blog", "ecommerce"]},
            "fields": [
                {
                    "name": "name",
                    "label": "Author name",
                    "type": "text",
                    "required": True,
                },
                {
                    "name": "bio",
                    "label": "Bio",
                    "type": "textarea",
                },
                {
                    "name": "url",
                    "label": "Profile URL",
                    "type": "url",
                },
                {
                    "name": "credentials",
                    "label": "Credentials",
                    "type": "array",
                    "placeholder": "e.g., Certified Expert, Published Author",
                },
            ],
        },
        "thresholds": {
            "title": "Alert Thresholds",
            "description": "Customize when you get alerted (optional)",
            "required": False,
            "fields": [
                {
                    "name": "traffic_drop_threshold_pct",
                    "label": "Traffic drop % to alert",
                    "type": "number",
                    "default": 30.0,
                    "min": 0,
                    "max": 100,
                    "help": "Alert when traffic drops by this percentage",
                },
                {
                    "name": "content_decay_days",
                    "label": "Content decay threshold (days)",
                    "type": "number",
                    "default": 90,
                    "min": 1,
                    "help": "Flag content declining for this many days",
                },
                {
                    "name": "min_eeat_score",
                    "label": "Minimum E-E-A-T score",
                    "type": "number",
                    "default": 60.0,
                    "min": 0,
                    "max": 100,
                    "help": "Alert if E-E-A-T score falls below this",
                },
            ],
        },
    }


@router.post("/quick-setup", response_model=ConfigResponse)
async def quick_onboarding(request: QuickSetupRequest):
    """
    Quick setup with minimal input.

    Creates a basic configuration that can be refined later.
    """
    config = quick_setup(
        domain=request.domain,
        competitors=request.competitors,
        business_name=request.business_name,
    )

    # Save it
    manager = ConfigManager()
    manager.save(config, "default")

    return ConfigResponse(
        name="default",
        config=config,
    )


@router.post("/configs", response_model=ConfigResponse)
async def save_configuration(request: ConfigSaveRequest):
    """Save a workflow configuration."""
    manager = ConfigManager()
    manager.save(request.config, request.name)

    logger.info("Configuration saved", name=request.name)

    return ConfigResponse(
        name=request.name,
        config=request.config,
    )


@router.get("/configs", response_model=ConfigListResponse)
async def list_configurations():
    """List all saved configurations."""
    manager = ConfigManager()
    return ConfigListResponse(configs=manager.list_configs())


@router.get("/configs/{name}", response_model=ConfigResponse)
async def get_configuration(name: str):
    """Get a specific configuration."""
    manager = ConfigManager()
    config = manager.load(name)

    if not config:
        raise HTTPException(status_code=404, detail=f"Configuration '{name}' not found")

    return ConfigResponse(
        name=name,
        config=config,
    )


@router.delete("/configs/{name}")
async def delete_configuration(name: str):
    """Delete a configuration."""
    manager = ConfigManager()
    if not manager.delete(name):
        raise HTTPException(status_code=404, detail=f"Configuration '{name}' not found")

    return {"message": f"Configuration '{name}' deleted"}


@router.post("/configs/{name}/validate")
async def validate_configuration(name: str):
    """
    Validate a configuration and check feature availability.

    Returns what features are enabled with this configuration.
    """
    manager = ConfigManager()
    config = manager.load(name)

    if not config:
        raise HTTPException(status_code=404, detail=f"Configuration '{name}' not found")

    # Check feature availability
    features = {
        "traffic_monitoring": True,
        "technical_audit": True,
        "serp_analysis": True,
        "competitor_analysis": bool(config.targets.competitors),
        "citation_tracking": bool(config.targets.competitors),
        "local_seo": bool(config.business_info and config.business_info.street_address),
        "eeat_analysis": bool(config.default_author or config.business_info),
        "author_schema": bool(config.default_author),
        "local_business_schema": bool(
            config.business_info and config.business_info.street_address
        ),
        "organization_schema": bool(config.business_info),
        "social_signals": bool(
            config.business_info
            and (
                config.business_info.facebook_url
                or config.business_info.twitter_url
                or config.business_info.linkedin_url
            )
        ),
    }

    # Generate recommendations
    recommendations = []

    if not config.targets.competitors:
        recommendations.append({
            "priority": "medium",
            "message": "Add competitors for competitive analysis and citation tracking",
        })

    if not config.business_info:
        recommendations.append({
            "priority": "high",
            "message": "Add business info for better schema recommendations",
        })

    if not config.default_author and config.business_info:
        recommendations.append({
            "priority": "medium",
            "message": "Add author info for E-E-A-T scoring and author schema",
        })

    if config.business_info and not config.business_info.street_address:
        recommendations.append({
            "priority": "medium",
            "message": "Add business address to enable local SEO features",
        })

    return {
        "valid": True,
        "features": features,
        "recommendations": recommendations,
        "completeness_score": sum(1 for v in features.values() if v) / len(features) * 100,
    }


@router.get("/recommendations/{site_type}")
async def get_workflow_recommendations(site_type: str):
    """
    Get recommended workflows for a site type.

    Args:
        site_type: ecommerce, local, content, saas, corporate, other
    """
    recommendations = {
        "ecommerce": [
            {
                "id": "full_audit",
                "name": "Full Audit",
                "description": "Monthly comprehensive review",
                "priority": "high",
                "frequency": "monthly",
            },
            {
                "id": "content",
                "name": "Content Analysis",
                "description": "Product content optimization",
                "priority": "high",
                "frequency": "weekly",
            },
            {
                "id": "competitive",
                "name": "Competitive Analysis",
                "description": "Track competitors",
                "priority": "medium",
                "frequency": "weekly",
            },
            {
                "id": "quick_check",
                "name": "Quick Check",
                "description": "Daily monitoring",
                "priority": "high",
                "frequency": "daily",
            },
        ],
        "local": [
            {
                "id": "local_seo",
                "name": "Local SEO",
                "description": "Local business optimization",
                "priority": "high",
                "frequency": "weekly",
            },
            {
                "id": "quick_check",
                "name": "Quick Check",
                "description": "Daily monitoring",
                "priority": "high",
                "frequency": "daily",
            },
            {
                "id": "full_audit",
                "name": "Full Audit",
                "description": "Monthly comprehensive review",
                "priority": "medium",
                "frequency": "monthly",
            },
        ],
        "content": [
            {
                "id": "content",
                "name": "Content Analysis",
                "description": "Content quality and decay analysis",
                "priority": "high",
                "frequency": "weekly",
            },
            {
                "id": "ai_readiness",
                "name": "AI Readiness",
                "description": "Optimize for AI search engines",
                "priority": "high",
                "frequency": "weekly",
            },
            {
                "id": "full_audit",
                "name": "Full Audit",
                "description": "Comprehensive analysis",
                "priority": "medium",
                "frequency": "monthly",
            },
        ],
        "saas": [
            {
                "id": "technical",
                "name": "Technical Analysis",
                "description": "Technical SEO audit",
                "priority": "high",
                "frequency": "weekly",
            },
            {
                "id": "ai_readiness",
                "name": "AI Readiness",
                "description": "AI search optimization",
                "priority": "high",
                "frequency": "weekly",
            },
            {
                "id": "competitive",
                "name": "Competitive Analysis",
                "description": "Competitor tracking",
                "priority": "medium",
                "frequency": "weekly",
            },
        ],
    }

    default = [
        {
            "id": "quick_check",
            "name": "Quick Check",
            "description": "Daily monitoring",
            "priority": "high",
            "frequency": "daily",
        },
        {
            "id": "full_audit",
            "name": "Full Audit",
            "description": "Comprehensive analysis",
            "priority": "high",
            "frequency": "monthly",
        },
    ]

    return {
        "site_type": site_type,
        "workflows": recommendations.get(site_type, default),
    }
