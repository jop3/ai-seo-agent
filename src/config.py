"""Application configuration with environment variable support."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AzureSettings(BaseSettings):
    """Azure-specific configuration."""

    model_config = SettingsConfigDict(env_prefix="AZURE_")

    subscription_id: str = ""
    resource_group: str = "ai-seo-agent-rg"
    tenant_id: str = ""
    client_id: str = ""
    client_secret: SecretStr = SecretStr("")

    # Azure OpenAI / AI Foundry
    openai_endpoint: str = ""
    openai_api_key: SecretStr = SecretStr("")
    openai_deployment: str = "gpt-4o"
    openai_api_version: str = "2024-02-15-preview"


class CosmosSettings(BaseSettings):
    """Cosmos DB configuration."""

    model_config = SettingsConfigDict(env_prefix="COSMOS_")

    endpoint: str = ""
    key: SecretStr = SecretStr("")
    database: str = "seo-agent"


class StorageSettings(BaseSettings):
    """Azure Blob Storage configuration."""

    model_config = SettingsConfigDict(env_prefix="STORAGE_")

    connection_string: SecretStr = SecretStr("")
    container: str = "seo-data"


class GoogleSettings(BaseSettings):
    """Google APIs configuration."""

    gsc_credentials_path: str = "./credentials/gsc-service-account.json"
    gsc_property_url: str = ""
    ga4_property_id: str = ""
    ga4_credentials_path: str = "./credentials/ga4-service-account.json"


class SerpSettings(BaseSettings):
    """SERP API configuration."""

    model_config = SettingsConfigDict(env_prefix="SERP_")

    provider: Literal["serpapi", "dataforseo", "brightdata", "scraper"] = "scraper"
    api_key: SecretStr = SecretStr("")


class AhrefsSettings(BaseSettings):
    """Ahrefs API configuration."""

    model_config = SettingsConfigDict(env_prefix="AHREFS_")

    api_key: SecretStr = SecretStr("")


class BingSettings(BaseSettings):
    """Bing Web Search API configuration."""

    model_config = SettingsConfigDict(env_prefix="BING_")

    api_key: SecretStr = SecretStr("")


class OptimizelySettings(BaseSettings):
    """Optimizely CMS configuration."""

    model_config = SettingsConfigDict(env_prefix="OPTIMIZELY_")

    api_key: SecretStr = SecretStr("")
    project_id: str = ""
    base_url: str = "https://cg.optimizely.com"


class AlertSettings(BaseSettings):
    """Alerting configuration."""

    teams_webhook_url: SecretStr = SecretStr("")
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_from: str = ""
    email_to: list[str] = Field(default_factory=list)


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_secret_key: SecretStr = SecretStr("change-me-in-production")
    log_level: str = "INFO"

    # MVP Auth
    api_key: SecretStr = SecretStr("")

    # OpenAI / Local LLM
    openai_api_key: str = ""
    openai_api_base: str = ""
    openai_model: str = "gpt-3.5-turbo"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Sub-configurations
    azure: AzureSettings = Field(default_factory=AzureSettings)
    cosmos: CosmosSettings = Field(default_factory=CosmosSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    google: GoogleSettings = Field(default_factory=GoogleSettings)
    serp: SerpSettings = Field(default_factory=SerpSettings)
    ahrefs: AhrefsSettings = Field(default_factory=AhrefsSettings)
    bing: BingSettings = Field(default_factory=BingSettings)
    optimizely: OptimizelySettings = Field(default_factory=OptimizelySettings)
    alerts: AlertSettings = Field(default_factory=AlertSettings)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
