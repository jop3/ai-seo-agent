"""Agent orchestration system for coordinated SEO analysis."""

from src.orchestrator.engine import (
    AgentOrchestrator,
    Workflow,
    WorkflowStep,
    WorkflowResult,
)
from src.orchestrator.workflows import (
    FULL_AUDIT_WORKFLOW,
    QUICK_CHECK_WORKFLOW,
    CONTENT_WORKFLOW,
    TECHNICAL_WORKFLOW,
    COMPETITIVE_WORKFLOW,
    LOCAL_SEO_WORKFLOW,
    AI_READINESS_WORKFLOW,
    AI_VISIBILITY_AUDIT_WORKFLOW,
    GEO_OPTIMIZATION_WORKFLOW,
    WORKFLOWS,
    get_workflow,
    list_workflows,
)
from src.orchestrator.schemas import (
    WorkflowInput,
    WorkflowTargets,
    WorkflowThresholds,
    WorkflowOptions,
    BusinessInfo,
    AuthorInfo,
    CompetitorConfig,
    create_minimal_config,
    create_full_config,
    EXAMPLE_ECOMMERCE_CONFIG,
    EXAMPLE_LOCAL_BUSINESS_CONFIG,
)
from src.orchestrator.onboarding import (
    OnboardingFlow,
    ConfigManager,
    quick_setup,
)

__all__ = [
    # Engine
    "AgentOrchestrator",
    "Workflow",
    "WorkflowStep",
    "WorkflowResult",
    # Workflows
    "FULL_AUDIT_WORKFLOW",
    "QUICK_CHECK_WORKFLOW",
    "CONTENT_WORKFLOW",
    "TECHNICAL_WORKFLOW",
    "COMPETITIVE_WORKFLOW",
    "LOCAL_SEO_WORKFLOW",
    "AI_READINESS_WORKFLOW",
    "AI_VISIBILITY_AUDIT_WORKFLOW",
    "GEO_OPTIMIZATION_WORKFLOW",
    "WORKFLOWS",
    "get_workflow",
    "list_workflows",
    # Schemas
    "WorkflowInput",
    "WorkflowTargets",
    "WorkflowThresholds",
    "WorkflowOptions",
    "BusinessInfo",
    "AuthorInfo",
    "CompetitorConfig",
    "create_minimal_config",
    "create_full_config",
    "EXAMPLE_ECOMMERCE_CONFIG",
    "EXAMPLE_LOCAL_BUSINESS_CONFIG",
    # Onboarding
    "OnboardingFlow",
    "ConfigManager",
    "quick_setup",
]
