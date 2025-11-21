"""Base agent class and context."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.config import Settings
from src.integrations.azure_openai import AzureOpenAIClient
from src.integrations.google_search_console import GoogleSearchConsoleClient
from src.integrations.optimizely import OptimizelyClient
from src.integrations.serp import SerpClient
from src.integrations.teams import TeamsNotifier
from src.models.agents import AgentResult, AgentTask, AgentType, Alert, Recommendation

logger = structlog.get_logger()


@dataclass
class AgentContext:
    """Shared context and dependencies for agents."""

    settings: Settings
    openai_client: AzureOpenAIClient
    gsc_client: GoogleSearchConsoleClient | None = None
    serp_client: SerpClient | None = None
    optimizely_client: OptimizelyClient | None = None
    teams_notifier: TeamsNotifier | None = None

    # Runtime data
    client_domain: str = ""
    property_url: str = ""

    # Caches
    _cache: dict[str, Any] = field(default_factory=dict)

    def cache_get(self, key: str) -> Any | None:
        return self._cache.get(key)

    def cache_set(self, key: str, value: Any) -> None:
        self._cache[key] = value


class BaseAgent(ABC):
    """Base class for all AI agents."""

    agent_type: AgentType

    def __init__(self, context: AgentContext):
        self.context = context
        self.logger = logger.bind(agent=self.agent_type.value)

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute the agent task."""
        pass

    async def run(self, task: AgentTask) -> AgentResult:
        """Run the agent with timing and error handling."""
        start_time = time.time()

        self.logger.info(
            "Agent starting task",
            task_id=task.id,
            task_type=task.task_type,
        )

        try:
            result = await self.execute(task)
            result.execution_time_ms = int((time.time() - start_time) * 1000)

            self.logger.info(
                "Agent completed task",
                task_id=task.id,
                success=result.success,
                execution_time_ms=result.execution_time_ms,
            )

            return result

        except Exception as e:
            self.logger.error(
                "Agent task failed",
                task_id=task.id,
                error=str(e),
            )

            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": str(e)},
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def create_recommendation(
        self,
        **kwargs,
    ) -> Recommendation:
        """Helper to create a recommendation."""
        return Recommendation(**kwargs)

    def create_alert(
        self,
        **kwargs,
    ) -> Alert:
        """Helper to create an alert."""
        return Alert(**kwargs)

    async def send_alert(self, alert: Alert) -> bool:
        """Send an alert via Teams if configured."""
        if self.context.teams_notifier:
            return await self.context.teams_notifier.send_alert(alert)
        return False
