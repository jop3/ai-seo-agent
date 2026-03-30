"""External service integrations."""

from src.integrations.google_search_console import GoogleSearchConsoleClient
from src.integrations.serp import SerpClient, get_serp_client
from src.integrations.openai_client import OpenAIClient, AzureOpenAIClient  # AzureOpenAIClient is deprecated alias
from src.integrations.teams import TeamsNotifier
from src.integrations.optimizely import OptimizelyClient
from src.integrations.ahrefs import AhrefsClient, get_ahrefs_client
from src.integrations.bing import BingClient, get_bing_client
from src.integrations.wayback import WaybackClient, get_wayback_client

__all__ = [
    # Google
    "GoogleSearchConsoleClient",
    # SERP providers
    "SerpClient",
    "get_serp_client",
    # LLM Client (OpenAI-compatible APIs)
    "OpenAIClient",
    "AzureOpenAIClient",  # Deprecated alias for backwards compatibility
    # Notifications
    "TeamsNotifier",
    # Experimentation
    "OptimizelyClient",
    # Backlink analysis
    "AhrefsClient",
    "get_ahrefs_client",
    # Bing search
    "BingClient",
    "get_bing_client",
    # Historical data
    "WaybackClient",
    "get_wayback_client",
]
