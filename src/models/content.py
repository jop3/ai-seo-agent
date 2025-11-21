"""Content and page-related data models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class PageType(str, Enum):
    """Types of pages on the site."""

    PRODUCT = "product"
    CATEGORY = "category"
    ARTICLE = "article"
    FAQ = "faq"
    LOCATION = "location"
    LANDING = "landing"
    SERVICE = "service"
    OTHER = "other"


class Page(BaseModel):
    """A page on the client's website."""

    id: str = Field(default_factory=lambda: "")
    url: HttpUrl
    canonical_url: HttpUrl | None = None
    page_type: PageType = PageType.OTHER
    title: str | None = None
    meta_description: str | None = None
    h1: str | None = None
    content_hash: str | None = None  # To detect changes

    # Schema.org data
    schema_markup: list["SchemaMarkup"] = Field(default_factory=list)

    # Metrics
    clicks_30d: int = 0
    impressions_30d: int = 0
    avg_position_30d: float | None = None

    # Optimization status
    last_analyzed: datetime | None = None
    optimization_score: float = 0.0
    pending_recommendations: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SchemaType(str, Enum):
    """Common Schema.org types for pharmacy/e-commerce."""

    PRODUCT = "Product"
    DRUG = "Drug"
    MEDICAL_WEB_PAGE = "MedicalWebPage"
    FAQ_PAGE = "FAQPage"
    HOW_TO = "HowTo"
    ARTICLE = "Article"
    LOCAL_BUSINESS = "LocalBusiness"
    PHARMACY = "Pharmacy"
    ORGANIZATION = "Organization"
    BREADCRUMB_LIST = "BreadcrumbList"
    OFFER = "Offer"
    REVIEW = "Review"
    AGGREGATE_RATING = "AggregateRating"


class SchemaMarkup(BaseModel):
    """Schema.org markup on a page."""

    schema_type: SchemaType
    raw_json: dict[str, Any]
    is_valid: bool = True
    validation_errors: list[str] = Field(default_factory=list)
    completeness_score: float = 0.0  # 0-100, how complete is the markup


class OptimizationType(str, Enum):
    """Types of optimizations."""

    ADD_SCHEMA = "add_schema"
    UPDATE_SCHEMA = "update_schema"
    ADD_FAQ = "add_faq"
    UPDATE_META = "update_meta"
    RESTRUCTURE_CONTENT = "restructure_content"
    ADD_STRUCTURED_DATA = "add_structured_data"
    IMPROVE_AGENT_ACCESS = "improve_agent_access"


class OptimizationStatus(str, Enum):
    """Status of an optimization."""

    SUGGESTED = "suggested"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    DEPLOYED = "deployed"
    VERIFIED = "verified"
    REJECTED = "rejected"
    FAILED = "failed"


class OptimizationSuggestion(BaseModel):
    """A suggested optimization for a page."""

    id: str = Field(default_factory=lambda: "")
    page_id: str
    page_url: HttpUrl
    optimization_type: OptimizationType
    status: OptimizationStatus = OptimizationStatus.SUGGESTED

    title: str
    description: str
    rationale: str  # Why this optimization is recommended

    # The actual change
    current_content: str | None = None
    suggested_content: str | None = None
    diff: str | None = None

    # For schema changes
    schema_type: SchemaType | None = None
    schema_json: dict[str, Any] | None = None

    # Impact estimation
    estimated_traffic_impact: str | None = None
    estimated_aio_impact: str | None = None
    confidence: float = 0.0  # 0-1

    # Workflow
    created_by: str = "system"
    approved_by: str | None = None
    approved_at: datetime | None = None
    deployed_at: datetime | None = None
    verified_at: datetime | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContentTemplate(BaseModel):
    """Template for generating optimized content."""

    id: str = Field(default_factory=lambda: "")
    name: str
    description: str
    page_type: PageType
    template_type: str  # "faq", "schema", "meta", etc.

    # Template content (Jinja2 or similar)
    template: str

    # Variables required
    required_variables: list[str] = Field(default_factory=list)
    optional_variables: list[str] = Field(default_factory=list)

    # Example output
    example_input: dict[str, Any] = Field(default_factory=dict)
    example_output: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
