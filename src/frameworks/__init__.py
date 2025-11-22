"""
Agent Framework Abstraction Layer

Provides a unified interface for multiple agent frameworks:
- Google Agent Development Kit (ADK)
- LangGraph
- Microsoft Agent Framework
- AWS Bedrock AgentCore
- CrewAI
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Protocol


class FrameworkType(str, Enum):
    """Supported agent frameworks."""

    GOOGLE_ADK = "google_adk"
    LANGGRAPH = "langgraph"
    MICROSOFT_AGENT = "microsoft_agent"
    AWS_BEDROCK = "aws_bedrock"
    CREWAI = "crewai"
    # Legacy/Direct LLM (current implementation)
    DIRECT_LLM = "direct_llm"


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    name: str
    role: str
    goal: str
    backstory: Optional[str] = None
    tools: list[str] = None
    llm_config: Optional[dict[str, Any]] = None
    memory: bool = True
    verbose: bool = False


@dataclass
class WorkflowConfig:
    """Configuration for a workflow."""

    name: str
    description: str
    agents: list[AgentConfig]
    tasks: list[dict[str, Any]]
    max_iterations: int = 10
    cache_results: bool = True


@dataclass
class DeploymentConfig:
    """Configuration for framework deployment."""

    target: str  # "vertex-ai", "azure", "aws", "local", etc.
    region: Optional[str] = None
    credentials: Optional[dict[str, Any]] = None
    scaling: Optional[dict[str, Any]] = None


@dataclass
class AgentResult:
    """Result from agent execution."""

    success: bool
    output: Any
    metadata: dict[str, Any]
    error: Optional[str] = None


class AgentFramework(Protocol):
    """Protocol defining the interface for all agent frameworks."""

    @property
    def framework_type(self) -> FrameworkType:
        """Return the framework type."""
        ...

    def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the framework with configuration."""
        ...

    def create_agent(self, agent_config: AgentConfig) -> Any:
        """Create an agent instance."""
        ...

    def create_workflow(self, workflow_config: WorkflowConfig) -> Any:
        """Create a workflow/orchestration."""
        ...

    def execute_agent(self, agent: Any, task: dict[str, Any]) -> AgentResult:
        """Execute a single agent on a task."""
        ...

    def execute_workflow(self, workflow: Any, inputs: dict[str, Any]) -> AgentResult:
        """Execute a multi-agent workflow."""
        ...

    def deploy(self, deployment_config: DeploymentConfig) -> str:
        """Deploy the agent/workflow to a target platform."""
        ...

    def get_metrics(self) -> dict[str, Any]:
        """Get execution metrics and observability data."""
        ...


class BaseAgentFramework(ABC):
    """Base class for agent framework implementations."""

    def __init__(self):
        self._initialized = False
        self._metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_duration_ms": 0.0,
        }

    @property
    @abstractmethod
    def framework_type(self) -> FrameworkType:
        """Return the framework type."""
        pass

    @abstractmethod
    def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the framework with configuration."""
        pass

    @abstractmethod
    def create_agent(self, agent_config: AgentConfig) -> Any:
        """Create an agent instance."""
        pass

    @abstractmethod
    def create_workflow(self, workflow_config: WorkflowConfig) -> Any:
        """Create a workflow/orchestration."""
        pass

    @abstractmethod
    def execute_agent(self, agent: Any, task: dict[str, Any]) -> AgentResult:
        """Execute a single agent on a task."""
        pass

    @abstractmethod
    def execute_workflow(self, workflow: Any, inputs: dict[str, Any]) -> AgentResult:
        """Execute a multi-agent workflow."""
        pass

    def deploy(self, deployment_config: DeploymentConfig) -> str:
        """Deploy the agent/workflow to a target platform."""
        raise NotImplementedError(
            f"{self.framework_type.value} deployment not yet implemented"
        )

    def get_metrics(self) -> dict[str, Any]:
        """Get execution metrics and observability data."""
        return self._metrics.copy()

    def _update_metrics(self, success: bool, duration_ms: float) -> None:
        """Update execution metrics."""
        self._metrics["total_executions"] += 1
        if success:
            self._metrics["successful_executions"] += 1
        else:
            self._metrics["failed_executions"] += 1

        # Update rolling average
        total = self._metrics["total_executions"]
        current_avg = self._metrics["average_duration_ms"]
        self._metrics["average_duration_ms"] = (
            (current_avg * (total - 1) + duration_ms) / total
        )


def get_framework(
    framework_type: FrameworkType,
    config: Optional[dict[str, Any]] = None
) -> AgentFramework:
    """
    Factory function to get an agent framework instance.

    Args:
        framework_type: The type of framework to create
        config: Optional configuration dictionary

    Returns:
        An initialized agent framework instance

    Example:
        >>> framework = get_framework(FrameworkType.GOOGLE_ADK, {
        ...     "project_id": "my-project",
        ...     "location": "us-central1"
        ... })
        >>> agent = framework.create_agent(AgentConfig(
        ...     name="SEO Analyst",
        ...     role="analyzer",
        ...     goal="Analyze SEO performance"
        ... ))
    """
    from src.frameworks.google_adk import GoogleADKFramework
    from src.frameworks.langgraph import LangGraphFramework
    from src.frameworks.microsoft_agent import MicrosoftAgentFramework
    from src.frameworks.aws_bedrock import BedrockAgentCoreFramework
    from src.frameworks.crewai import CrewAIFramework
    from src.frameworks.direct_llm import DirectLLMFramework

    frameworks = {
        FrameworkType.GOOGLE_ADK: GoogleADKFramework,
        FrameworkType.LANGGRAPH: LangGraphFramework,
        FrameworkType.MICROSOFT_AGENT: MicrosoftAgentFramework,
        FrameworkType.AWS_BEDROCK: BedrockAgentCoreFramework,
        FrameworkType.CREWAI: CrewAIFramework,
        FrameworkType.DIRECT_LLM: DirectLLMFramework,
    }

    if framework_type not in frameworks:
        raise ValueError(f"Unsupported framework: {framework_type}")

    framework = frameworks[framework_type]()

    if config:
        framework.initialize(config)

    return framework


__all__ = [
    "FrameworkType",
    "AgentConfig",
    "WorkflowConfig",
    "DeploymentConfig",
    "AgentResult",
    "AgentFramework",
    "BaseAgentFramework",
    "get_framework",
]
