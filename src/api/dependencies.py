"""FastAPI dependencies for dependency injection."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from src.agents.base import AgentContext
from src.config import Settings, get_settings
from src.integrations.azure_openai import AzureOpenAIClient
from src.integrations.google_search_console import GoogleSearchConsoleClient
from src.integrations.optimizely import OptimizelyClient
from src.integrations.serp import get_serp_client, SerpClient
from src.integrations.teams import TeamsNotifier


async def verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> str:
    """Verify API key for MVP authentication."""
    expected_key = settings.api_key.get_secret_value()

    if not expected_key:
        # No API key configured, allow all (development mode)
        return "development"

    if not x_api_key or x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


@lru_cache
def get_openai_client() -> AzureOpenAIClient:
    """Get Azure OpenAI client."""
    settings = get_settings()
    return AzureOpenAIClient(settings.azure)


def get_gsc_client() -> GoogleSearchConsoleClient | None:
    """Get Google Search Console client if configured."""
    settings = get_settings()

    if not settings.google.gsc_credentials_path or not settings.google.gsc_property_url:
        return None

    return GoogleSearchConsoleClient(
        credentials_path=settings.google.gsc_credentials_path,
        property_url=settings.google.gsc_property_url,
    )


def get_serp_client_dep() -> SerpClient | None:
    """Get SERP client if configured."""
    settings = get_settings()

    # Need property URL for client domain
    if not settings.google.gsc_property_url:
        return None

    # Extract domain from property URL
    from urllib.parse import urlparse
    domain = urlparse(settings.google.gsc_property_url).netloc

    return get_serp_client(settings.serp, domain)


def get_optimizely_client() -> OptimizelyClient | None:
    """Get Optimizely client if configured."""
    settings = get_settings()

    if not settings.optimizely.api_key.get_secret_value():
        return None

    return OptimizelyClient(settings.optimizely)


def get_teams_notifier() -> TeamsNotifier | None:
    """Get Teams notifier if configured."""
    settings = get_settings()

    webhook_url = settings.alerts.teams_webhook_url.get_secret_value()
    if not webhook_url:
        return None

    return TeamsNotifier(webhook_url)


def get_agent_context(
    settings: Settings = Depends(get_settings),
) -> AgentContext:
    """Get the agent context with all dependencies."""
    from urllib.parse import urlparse

    property_url = settings.google.gsc_property_url
    domain = urlparse(property_url).netloc if property_url else ""

    return AgentContext(
        settings=settings,
        openai_client=get_openai_client(),
        gsc_client=get_gsc_client(),
        serp_client=get_serp_client_dep(),
        optimizely_client=get_optimizely_client(),
        teams_notifier=get_teams_notifier(),
        client_domain=domain,
        property_url=property_url,
    )


# Type aliases for cleaner dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings)]
ApiKeyDep = Annotated[str, Depends(verify_api_key)]
AgentContextDep = Annotated[AgentContext, Depends(get_agent_context)]
OpenAIClientDep = Annotated[AzureOpenAIClient, Depends(get_openai_client)]
