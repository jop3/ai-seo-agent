"""Agent-related data models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Types of agents in the system."""

    SEO_ANALYST = "seo_analyst"
    AGENT_TESTER = "agent_tester"
    COMPETITOR_WATCHER = "competitor_watcher"
    OPTIMIZATION_RECOMMENDER = "optimization_recommender"
    MONITORING = "monitoring"
    REPORT_GENERATOR = "report_generator"
    # Extended agent types
    COMPETITOR_MONITOR = "competitor_monitor"
    CONTENT_GENERATOR = "content_generator"
    MULTI_ENGINE_TRACKER = "multi_engine_tracker"
    TECHNICAL_AUDITOR = "technical_auditor"
    LINK_ANALYZER = "link_analyzer"
    SERP_FEATURES = "serp_features"
    CONTENT_DECAY = "content_decay"
    SCHEMA_GENERATOR = "schema_generator"
    PREDICTIVE_SEO = "predictive_seo"
    LOCAL_SEO = "local_seo"
    EEAT_ANALYZER = "eeat_analyzer"
    MULTI_PLATFORM_SEO = "multi_platform_seo"
    AI_CONTENT_ANALYZER = "ai_content_analyzer"
    GEO_ANALYZER = "geo_analyzer"
    # E-commerce specialized agents
    ECOMMERCE_SEO = "ecommerce_seo"
    AI_VISIBILITY_CONTROL = "ai_visibility_control"
    VISUAL_SEARCH = "visual_search"
    PRODUCT_FEED_ANALYZER = "product_feed_analyzer"
    CONVERSATIONAL_COMMERCE = "conversational_commerce"
    # AI Mode & Citation agents
    AI_MODE_TRACKER = "ai_mode_tracker"
    BRAND_MENTION_ANALYZER = "brand_mention_analyzer"
    AI_CITATION_OPTIMIZER = "ai_citation_optimizer"


class TaskStatus(str, Enum):
    """Status of an agent task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Priority levels for tasks."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentTask(BaseModel):
    """A task for an agent to execute."""

    id: str = Field(default_factory=lambda: "")
    agent_type: AgentType
    task_type: str  # e.g., "analyze_query", "check_aio", "test_page"
    parameters: dict[str, Any] = Field(default_factory=dict)
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentResult(BaseModel):
    """Result from an agent execution."""

    id: str = Field(default_factory=lambda: "")
    task_id: str
    agent_type: AgentType
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    recommendations: list["Recommendation"] = Field(default_factory=list)
    alerts: list["Alert"] = Field(default_factory=list)
    tokens_used: int = 0
    execution_time_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RecommendationType(str, Enum):
    """Types of optimization recommendations."""

    SCHEMA_MARKUP = "schema_markup"
    CONTENT_STRUCTURE = "content_structure"
    META_TAGS = "meta_tags"
    FAQ_ADDITION = "faq_addition"
    HEADING_OPTIMIZATION = "heading_optimization"
    INTERNAL_LINKING = "internal_linking"
    PAGE_SPEED = "page_speed"
    AGENT_ACCESSIBILITY = "agent_accessibility"


class RecommendationPriority(str, Enum):
    """Priority for recommendations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Recommendation(BaseModel):
    """An optimization recommendation."""

    id: str = Field(default_factory=lambda: "")
    type: RecommendationType | None = None
    priority: RecommendationPriority = RecommendationPriority.MEDIUM
    title: str
    description: str
    category: str | None = None  # Flexible category for agents
    affected_url: str | None = None
    affected_query: str | None = None
    current_state: str | None = None
    recommended_state: str | None = None
    estimated_impact: str | None = None  # "High", "Medium", "Low"
    implementation_effort: str | None = None  # "Easy", "Medium", "Hard"
    auto_implementable: bool = False
    implementation_code: str | None = None  # Schema, HTML, etc.
    status: str = "pending"  # pending, approved, implemented, rejected
    data: dict[str, Any] = Field(default_factory=dict)  # Extra data from agents
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AlertSeverity(str, Enum):
    """Severity levels for alerts."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of alerts."""

    TRAFFIC_DROP = "traffic_drop"
    AIO_DETECTED = "aio_detected"
    RANKING_CHANGE = "ranking_change"
    COMPETITOR_CHANGE = "competitor_change"
    ALGORITHM_UPDATE = "algorithm_update"
    SCHEMA_ERROR = "schema_error"
    AGENT_TEST_FAILURE = "agent_test_failure"


class Alert(BaseModel):
    """An alert to notify the team."""

    id: str = Field(default_factory=lambda: "")
    type: AlertType | None = None
    severity: AlertSeverity = AlertSeverity.INFO
    title: str
    message: str
    source: str | None = None  # Source agent/component
    data: dict[str, Any] = Field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    sent_to_teams: bool = False
    sent_to_email: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Type aliases for convenience in agents
Priority = RecommendationPriority
Severity = AlertSeverity
