"""SEO-related data models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class QueryClassification(str, Enum):
    """Classification of search query intent."""

    INFORMATIONAL = "informational"  # "what is ibuprofen"
    NAVIGATIONAL = "navigational"  # "apoteket stockholm"
    TRANSACTIONAL = "transactional"  # "buy paracetamol online"
    COMMERCIAL = "commercial"  # "best pain reliever for headache"
    LOCAL = "local"  # "pharmacy near me"


class AIOverviewStatus(str, Enum):
    """Status of AI Overview presence for a query."""

    PRESENT = "present"  # AIO shown
    ABSENT = "absent"  # No AIO
    PARTIAL = "partial"  # AIO sometimes shown
    UNKNOWN = "unknown"  # Not yet checked


class Query(BaseModel):
    """A search query being tracked."""

    id: str = Field(default_factory=lambda: "")
    query: str
    property_url: str
    classification: QueryClassification = QueryClassification.INFORMATIONAL
    aio_status: AIOverviewStatus = AIOverviewStatus.UNKNOWN
    aio_citation_present: bool = False
    avg_position: float | None = None
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SERPResult(BaseModel):
    """A single SERP result."""

    position: int
    url: HttpUrl
    title: str
    snippet: str
    is_featured: bool = False
    is_aio_citation: bool = False


class AIOverviewResult(BaseModel):
    """AI Overview analysis for a query."""

    query: str
    has_aio: bool
    aio_content: str | None = None
    citations: list[str] = Field(default_factory=list)
    client_cited: bool = False
    client_citation_position: int | None = None
    competitor_citations: list[str] = Field(default_factory=list)
    organic_results: list[SERPResult] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class TrafficData(BaseModel):
    """Traffic metrics from GSC/GA4."""

    property_url: str
    date: datetime
    query: str | None = None
    page: str | None = None
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    position: float | None = None
    # GA4 metrics
    sessions: int | None = None
    users: int | None = None
    conversions: int | None = None
    revenue: float | None = None


class TrafficChange(BaseModel):
    """Traffic change detection."""

    query: str | None = None
    page: str | None = None
    metric: str  # clicks, impressions, ctr, position
    previous_value: float
    current_value: float
    change_percent: float
    period_start: datetime
    period_end: datetime
    is_significant: bool = False
    likely_cause: str | None = None  # "aio_introduction", "ranking_drop", etc.


class PageAnalysis(BaseModel):
    """Analysis of a page's SEO status."""

    url: HttpUrl
    title: str | None = None
    meta_description: str | None = None
    h1: str | None = None
    word_count: int = 0
    schema_types: list[str] = Field(default_factory=list)
    schema_valid: bool = False
    schema_errors: list[str] = Field(default_factory=list)

    # Agent interpretation
    agent_summary: str | None = None  # How an LLM interprets this page
    agent_extractable_data: dict[str, Any] = Field(default_factory=dict)
    agent_actionable: bool = False  # Can an agent complete a transaction?

    # Scores
    aio_optimization_score: float = 0.0  # 0-100
    agent_friendliness_score: float = 0.0  # 0-100

    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
