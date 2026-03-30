"""Base agent class and context."""

import asyncio
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

from src.config import Settings
from src.core.errors import (
    SEOAgentError,
    AgentError,
    APIError,
    RateLimitError,
    ErrorCode,
)
from src.integrations.openai_client import AzureOpenAIClient
from src.integrations.google_search_console import GoogleSearchConsoleClient
from src.integrations.optimizely import OptimizelyClient
from src.integrations.serp import SerpClient
from src.integrations.teams import TeamsNotifier
from src.integrations.ahrefs import AhrefsClient
from src.integrations.bing import BingClient
from src.integrations.wayback import WaybackClient
from src.models.agents import AgentResult, AgentTask, AgentType, Alert, Recommendation, Severity
from src.cache.page_cache import PageData, get_cache

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
    ahrefs_client: AhrefsClient | None = None
    bing_client: BingClient | None = None
    wayback_client: WaybackClient | None = None

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
        self.page_cache = get_cache()  # Global page cache

    # Page cache helper methods
    def get_cached_page(self, url: str) -> PageData | None:
        """
        Get cached page data if available.

        Returns None if not cached or expired. Agents can use this
        to avoid redundant HTTP requests.

        Example:
            page_data = self.get_cached_page("https://example.com")
            if page_data:
                # Use cached data
                title = page_data.meta_title
            else:
                # Fetch fresh (or use PageAnalyzer agent)
                ...
        """
        return self.page_cache.get(url)

    def cache_page(self, url: str, page_data: PageData, ttl: int | None = None) -> None:
        """
        Cache page data for reuse by other agents.

        Args:
            url: Page URL
            page_data: Extracted page data
            ttl: Time-to-live in seconds (optional)
        """
        self.page_cache.set(url, page_data, ttl=ttl)

    def invalidate_page_cache(self, url: str) -> bool:
        """Invalidate cached page data (force refresh on next access)."""
        return self.page_cache.invalidate(url)

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute the agent task."""
        pass

    async def run(self, task: AgentTask) -> AgentResult:
        """Run the agent with timing, retries, and comprehensive error handling."""
        start_time = time.time()

        self.logger.info(
            "Agent starting task",
            task_id=task.id,
            task_type=task.task_type,
        )

        try:
            # Execute with retry logic for transient failures
            result = await self._execute_with_retry(task)
            result.execution_time_ms = int((time.time() - start_time) * 1000)

            self.logger.info(
                "Agent completed task",
                task_id=task.id,
                success=result.success,
                execution_time_ms=result.execution_time_ms,
                recommendations_count=len(result.recommendations) if result.recommendations else 0,
                alerts_count=len(result.alerts) if result.alerts else 0,
            )

            return result

        except RateLimitError as e:
            self.logger.warning(
                "Agent rate limited",
                task_id=task.id,
                retry_after=e.retry_after,
            )
            return self._create_error_result(
                task, f"Rate limited: {e.message}", ErrorCode.API_RATE_LIMITED, start_time
            )

        except AgentError as e:
            self.logger.error(
                "Agent task failed",
                task_id=task.id,
                error_code=e.code.value,
                error=e.message,
            )
            return self._create_error_result(task, e.message, e.code, start_time)

        except SEOAgentError as e:
            self.logger.error(
                "SEO Agent error",
                task_id=task.id,
                error_code=e.code.value,
                error=e.message,
            )
            return self._create_error_result(task, e.message, e.code, start_time)

        except asyncio.TimeoutError:
            self.logger.error("Agent task timed out", task_id=task.id)
            return self._create_error_result(
                task, "Task timed out", ErrorCode.AGENT_TIMEOUT, start_time
            )

        except Exception as e:
            self.logger.error(
                "Agent task failed with unexpected error",
                task_id=task.id,
                error=str(e),
                traceback=traceback.format_exc(),
            )
            return self._create_error_result(
                task, f"Unexpected error: {str(e)}", ErrorCode.UNKNOWN_ERROR, start_time
            )

    async def _execute_with_retry(self, task: AgentTask) -> AgentResult:
        """Execute task with automatic retry for transient failures."""
        max_attempts = 3
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                return await self.execute(task)
            except (APIError, ConnectionError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < max_attempts:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(
                        "Retrying after transient failure",
                        task_id=task.id,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        wait_seconds=wait_time,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise

        # Should not reach here, but just in case
        raise last_error or AgentError(
            "Max retries exceeded",
            self.agent_type.value if isinstance(self.agent_type, AgentType) else str(self.agent_type),
            task.task_type,
        )

    def _create_error_result(
        self,
        task: AgentTask,
        error_message: str,
        error_code: ErrorCode,
        start_time: float,
    ) -> AgentResult:
        """Create a standardized error result."""
        return AgentResult(
            task_id=task.id,
            agent_type=self.agent_type,
            success=False,
            data={
                "error": error_message,
                "error_code": error_code.value,
            },
            execution_time_ms=int((time.time() - start_time) * 1000),
            alerts=[
                Alert(
                    title=f"Agent task failed: {task.task_type}",
                    message=error_message,
                    severity=Severity.ERROR,
                    source=str(self.agent_type),
                    data={"error_code": error_code.value},
                )
            ],
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

    async def safe_api_call(
        self,
        coro,
        default: Any = None,
        error_message: str = "API call failed",
    ) -> Any:
        """Safely execute an API call with error handling."""
        try:
            return await coro
        except RateLimitError:
            raise  # Propagate rate limits
        except Exception as e:
            self.logger.warning(
                error_message,
                error=str(e),
            )
            return default

    def validate_required_context(self, *required: str) -> None:
        """Validate that required context dependencies are available."""
        missing = []
        for req in required:
            if req == "openai" and not self.context.openai_client:
                missing.append("OpenAI client")
            elif req == "gsc" and not self.context.gsc_client:
                missing.append("Google Search Console client")
            elif req == "serp" and not self.context.serp_client:
                missing.append("SERP client")
            elif req == "teams" and not self.context.teams_notifier:
                missing.append("Teams notifier")
            elif req == "optimizely" and not self.context.optimizely_client:
                missing.append("Optimizely client")

        if missing:
            raise AgentError(
                f"Missing required dependencies: {', '.join(missing)}",
                agent_type=str(self.agent_type),
                code=ErrorCode.AGENT_CONTEXT_MISSING,
            )
