"""
Input schemas and configuration for workflow orchestration.

Defines all the parameters workflows need for full functionality.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class CompetitorConfig(BaseModel):
    """Configuration for a competitor."""
    domain: str = Field(..., description="Competitor domain (e.g., competitor.com)")
    name: str | None = Field(None, description="Display name")
    priority: str = Field("medium", description="Priority level: high, medium, low")


class BusinessInfo(BaseModel):
    """Business information for local SEO and schema."""
    name: str = Field(..., description="Business/brand name")
    legal_name: str | None = Field(None, description="Legal business name")
    url: str = Field(..., description="Main website URL")
    description: str | None = Field(None, description="Business description")

    # Contact info
    phone: str | None = None
    email: str | None = None

    # Location (for local SEO)
    street_address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    # Social profiles
    facebook_url: str | None = None
    twitter_url: str | None = None
    linkedin_url: str | None = None
    instagram_url: str | None = None
    youtube_url: str | None = None

    # Publishing info
    logo_url: str | None = Field(None, description="URL to company logo")
    publisher_logo_url: str | None = Field(None, description="URL to publisher logo (for articles)")

    # Industry/category
    industry: str | None = Field(None, description="Industry/vertical")
    business_type: str | None = Field(None, description="LocalBusiness schema type")


class AuthorInfo(BaseModel):
    """Author information for E-E-A-T and content schema."""
    name: str
    url: str | None = None
    email: str | None = None
    bio: str | None = None
    credentials: list[str] = Field(default_factory=list, description="Professional credentials")
    social_profiles: dict[str, str] = Field(default_factory=dict)


class WorkflowTargets(BaseModel):
    """Target URLs and queries for analysis."""

    # Primary targets
    primary_domain: str = Field(..., description="Main domain to analyze (e.g., example.com)")
    property_url: str = Field(..., description="Full property URL (e.g., https://example.com)")

    # Competitors
    competitors: list[CompetitorConfig] = Field(
        default_factory=list,
        description="List of competitor domains to compare against"
    )

    # Queries to analyze
    target_queries: list[str] = Field(
        default_factory=list,
        description="Specific queries to analyze (if empty, uses GSC top queries)"
    )
    query_limit: int = Field(
        100,
        description="Max queries to fetch from GSC if target_queries is empty"
    )

    # Pages to analyze
    target_pages: list[str] = Field(
        default_factory=list,
        description="Specific pages/URLs to analyze (if empty, crawls site)"
    )
    max_pages: int = Field(
        1000,
        description="Max pages to crawl if target_pages is empty"
    )


class WorkflowThresholds(BaseModel):
    """Thresholds and limits for workflow execution."""

    # Traffic thresholds
    traffic_drop_threshold_pct: float = Field(
        30.0,
        description="Traffic drop % to trigger alert"
    )
    traffic_anomaly_sigma: float = Field(
        2.0,
        description="Standard deviations for anomaly detection"
    )

    # Content thresholds
    content_decay_days: int = Field(
        90,
        description="Days of declining traffic to flag content decay"
    )
    min_traffic_for_decay: int = Field(
        100,
        description="Minimum clicks to consider for decay analysis"
    )

    # Ranking thresholds
    ranking_drop_threshold: int = Field(
        5,
        description="Position drop to trigger alert"
    )

    # E-E-A-T thresholds
    min_eeat_score: float = Field(
        60.0,
        description="Minimum acceptable E-E-A-T score (0-100)"
    )

    # Competitor thresholds
    competitor_gap_threshold_pct: float = Field(
        20.0,
        description="% gap in visibility/traffic vs competitors to alert"
    )

    # Technical thresholds
    max_page_load_time_ms: int = Field(
        3000,
        description="Max acceptable page load time"
    )
    min_mobile_score: int = Field(
        90,
        description="Minimum mobile score (0-100)"
    )


class WorkflowOptions(BaseModel):
    """Additional options for workflow execution."""

    # Analysis depth
    analysis_depth: str = Field(
        "standard",
        description="Analysis depth: quick, standard, deep"
    )

    # Time ranges
    days_back: int = Field(
        30,
        description="Days of historical data to analyze"
    )
    forecast_days: int = Field(
        30,
        description="Days to forecast into future"
    )

    # AI engine tracking
    ai_engines: list[str] = Field(
        default_factory=lambda: ["perplexity", "chatgpt", "bing_copilot", "gemini"],
        description="AI engines to check for citations"
    )

    # Integrations
    use_ahrefs: bool = Field(
        True,
        description="Use Ahrefs API if available"
    )
    use_bing: bool = Field(
        True,
        description="Use Bing API if available"
    )
    check_wayback: bool = Field(
        True,
        description="Check Wayback Machine for changes"
    )

    # Notifications
    send_teams_notification: bool = Field(
        True,
        description="Send results to Teams webhook"
    )

    # Concurrency
    max_concurrent_requests: int = Field(
        5,
        description="Max concurrent API requests"
    )


class WorkflowInput(BaseModel):
    """Complete input configuration for workflow execution."""

    # Required: What to analyze
    targets: WorkflowTargets

    # Optional: Business context
    business_info: BusinessInfo | None = Field(
        None,
        description="Business information for local SEO and schema generation"
    )

    # Optional: Author info for content
    default_author: AuthorInfo | None = Field(
        None,
        description="Default author for E-E-A-T and content schema"
    )

    # Optional: Thresholds
    thresholds: WorkflowThresholds = Field(
        default_factory=WorkflowThresholds,
        description="Alert and analysis thresholds"
    )

    # Optional: Execution options
    options: WorkflowOptions = Field(
        default_factory=WorkflowOptions,
        description="Workflow execution options"
    )

    # Optional: Custom parameters for specific agents
    custom_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom parameters passed to specific agents"
    )

    def to_params(self) -> dict[str, Any]:
        """Convert to flat parameter dictionary for agents."""
        params: dict[str, Any] = {
            # Targets
            "domain": self.targets.primary_domain,
            "property_url": self.targets.property_url,
            "competitors": [c.domain for c in self.targets.competitors],
            "competitor_configs": [c.model_dump() for c in self.targets.competitors],
            "target_queries": self.targets.target_queries,
            "query_limit": self.targets.query_limit,
            "target_pages": self.targets.target_pages,
            "max_pages": self.targets.max_pages,

            # Thresholds
            "threshold_percent": self.thresholds.traffic_drop_threshold_pct,
            "traffic_anomaly_sigma": self.thresholds.traffic_anomaly_sigma,
            "content_decay_days": self.thresholds.content_decay_days,
            "min_traffic_for_decay": self.thresholds.min_traffic_for_decay,
            "ranking_drop_threshold": self.thresholds.ranking_drop_threshold,
            "min_eeat_score": self.thresholds.min_eeat_score,

            # Options
            "days_back": self.options.days_back,
            "forecast_days": self.options.forecast_days,
            "engines": self.options.ai_engines,
            "use_ahrefs": self.options.use_ahrefs,
            "use_bing": self.options.use_bing,
            "check_wayback": self.options.check_wayback,
            "max_concurrent": self.options.max_concurrent_requests,
        }

        # Add business info if present
        if self.business_info:
            params["business_info"] = self.business_info.model_dump()
            params["business_name"] = self.business_info.name
            params["business_url"] = self.business_info.url

        # Add author info if present
        if self.default_author:
            params["default_author"] = self.default_author.model_dump()
            params["author_name"] = self.default_author.name

        # Merge custom params
        params.update(self.custom_params)

        return params


# =============================================================================
# Preset Configurations
# =============================================================================

def create_minimal_config(
    domain: str,
    property_url: str,
) -> WorkflowInput:
    """Create minimal configuration with just domain."""
    return WorkflowInput(
        targets=WorkflowTargets(
            primary_domain=domain,
            property_url=property_url,
        )
    )


def create_full_config(
    domain: str,
    property_url: str,
    competitors: list[str],
    business_name: str,
    business_description: str | None = None,
    author_name: str | None = None,
) -> WorkflowInput:
    """Create full configuration with common parameters."""
    business_info = BusinessInfo(
        name=business_name,
        url=property_url,
        description=business_description,
    )

    default_author = None
    if author_name:
        default_author = AuthorInfo(name=author_name)

    return WorkflowInput(
        targets=WorkflowTargets(
            primary_domain=domain,
            property_url=property_url,
            competitors=[
                CompetitorConfig(domain=c, priority="high")
                for c in competitors
            ],
        ),
        business_info=business_info,
        default_author=default_author,
    )


# =============================================================================
# Example Configurations
# =============================================================================

EXAMPLE_ECOMMERCE_CONFIG = WorkflowInput(
    targets=WorkflowTargets(
        primary_domain="mystore.com",
        property_url="https://mystore.com",
        competitors=[
            CompetitorConfig(domain="competitor1.com", name="Competitor A", priority="high"),
            CompetitorConfig(domain="competitor2.com", name="Competitor B", priority="medium"),
        ],
        target_queries=["best widgets", "buy widgets online", "widget reviews"],
        query_limit=200,
        max_pages=5000,
    ),
    business_info=BusinessInfo(
        name="My Store",
        legal_name="My Store Inc.",
        url="https://mystore.com",
        description="Leading online store for widgets",
        phone="+1-555-0100",
        email="support@mystore.com",
        street_address="123 Main St",
        city="San Francisco",
        state="CA",
        postal_code="94102",
        country="US",
        logo_url="https://mystore.com/logo.png",
        industry="E-commerce",
        facebook_url="https://facebook.com/mystore",
        twitter_url="https://twitter.com/mystore",
    ),
    default_author=AuthorInfo(
        name="John Smith",
        url="https://mystore.com/authors/john-smith",
        bio="Senior product reviewer with 10 years experience",
        credentials=["Certified Widget Expert", "Industry Analyst"],
    ),
    thresholds=WorkflowThresholds(
        traffic_drop_threshold_pct=25.0,
        content_decay_days=60,
        min_eeat_score=70.0,
    ),
    options=WorkflowOptions(
        analysis_depth="deep",
        days_back=90,
        ai_engines=["perplexity", "chatgpt", "bing_copilot"],
    ),
)


EXAMPLE_LOCAL_BUSINESS_CONFIG = WorkflowInput(
    targets=WorkflowTargets(
        primary_domain="mypizzeria.com",
        property_url="https://mypizzeria.com",
        competitors=[
            CompetitorConfig(domain="competitor-pizza.com", priority="high"),
        ],
        target_queries=["pizza near me", "best pizza delivery", "italian restaurant"],
        query_limit=50,
    ),
    business_info=BusinessInfo(
        name="Mario's Pizzeria",
        url="https://mypizzeria.com",
        description="Authentic Italian pizza since 1985",
        phone="+1-555-7777",
        email="info@mypizzeria.com",
        street_address="456 Pizza Ave",
        city="Chicago",
        state="IL",
        postal_code="60601",
        country="US",
        latitude=41.8781,
        longitude=-87.6298,
        business_type="Restaurant",
        logo_url="https://mypizzeria.com/logo.png",
        facebook_url="https://facebook.com/mariospizzeria",
        instagram_url="https://instagram.com/mariospizzeria",
    ),
    options=WorkflowOptions(
        analysis_depth="standard",
        days_back=30,
    ),
)
