"""
LLM Configuration Models and Storage

Handles configuration for:
- Provider credentials (API keys, endpoints)
- Model definitions and capabilities
- Agent-to-model assignments
- Group-level model assignments
"""

import json
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()

# Default config file location
CONFIG_DIR = Path("config")
LLM_CONFIG_FILE = CONFIG_DIR / "llm_settings.json"


class ProviderConfig(BaseModel):
    """Configuration for an LLM provider."""

    name: str  # e.g., "azure", "openrouter", "openai", "local"
    enabled: bool = True
    api_key: str = ""  # Will be stored securely
    api_base: str | None = None  # Custom endpoint

    # Provider-specific settings
    azure_deployment: str | None = None
    azure_api_version: str = "2024-02-15-preview"

    # For display in UI
    display_name: str = ""
    description: str = ""


class ModelConfig(BaseModel):
    """Configuration for a specific model."""

    id: str  # e.g., "gpt-4o", "claude-3-opus", "azure/gpt-4o"
    provider: str  # e.g., "openai", "anthropic", "azure", "openrouter"
    display_name: str

    # Capabilities/tags for matching
    capabilities: list[str] = Field(default_factory=list)  # ["reasoning", "coding", "creative", "fast"]

    # Cost info (per 1M tokens)
    input_cost: float = 0.0
    output_cost: float = 0.0

    # Limits
    max_tokens: int = 4096
    context_window: int = 128000

    # For UI grouping
    category: Literal["fast", "balanced", "quality", "reasoning", "local"] = "balanced"

    def get_litellm_model_name(self) -> str:
        """Get the model name in LiteLLM format."""
        # LiteLLM uses format: provider/model or just model for OpenAI
        if self.provider == "openai":
            return self.id
        elif self.provider == "azure":
            return f"azure/{self.id}"
        elif self.provider == "anthropic":
            return f"anthropic/{self.id}"
        elif self.provider == "openrouter":
            return f"openrouter/{self.id}"
        elif self.provider == "vertex_ai":
            return f"vertex_ai/{self.id}"
        elif self.provider == "bedrock":
            return f"bedrock/{self.id}"
        elif self.provider == "local":
            return f"openai/{self.id}"  # Local uses OpenAI-compatible API
        else:
            return self.id


class AgentModelAssignment(BaseModel):
    """Model assignment for a specific agent."""

    agent_name: str
    model_id: str  # References ModelConfig.id
    fallback_model_id: str | None = None

    # Override settings for this agent
    temperature: float | None = None
    max_tokens: int | None = None


class GroupModelAssignment(BaseModel):
    """Model assignment for a group of agents."""

    group_name: str  # e.g., "content", "analysis", "monitoring"
    agent_names: list[str]  # Agents in this group
    model_id: str
    fallback_model_id: str | None = None


class LLMSettings(BaseModel):
    """Complete LLM settings configuration."""

    # Provider configurations
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)

    # Available models
    models: dict[str, ModelConfig] = Field(default_factory=dict)

    # Default model (used when no specific assignment)
    default_model_id: str = "gpt-4o"

    # Group assignments (applied before individual)
    groups: list[GroupModelAssignment] = Field(default_factory=list)

    # Individual agent assignments (highest priority)
    agent_assignments: dict[str, AgentModelAssignment] = Field(default_factory=dict)

    # Global settings
    enable_fallbacks: bool = True
    enable_caching: bool = True
    log_requests: bool = True

    def get_model_for_agent(self, agent_name: str) -> ModelConfig:
        """Get the model configuration for a specific agent."""
        # 1. Check individual assignment
        if agent_name in self.agent_assignments:
            assignment = self.agent_assignments[agent_name]
            if assignment.model_id in self.models:
                return self.models[assignment.model_id]

        # 2. Check group assignments
        for group in self.groups:
            if agent_name in group.agent_names:
                if group.model_id in self.models:
                    return self.models[group.model_id]

        # 3. Fall back to default
        if self.default_model_id in self.models:
            return self.models[self.default_model_id]

        # 4. Return first available model
        if self.models:
            return next(iter(self.models.values()))

        # 5. Return a sensible default
        return ModelConfig(
            id="gpt-4o",
            provider="openai",
            display_name="GPT-4o",
            category="balanced",
        )


def get_default_settings() -> LLMSettings:
    """Get default LLM settings with common providers and models."""
    return LLMSettings(
        providers={
            "openai": ProviderConfig(
                name="openai",
                display_name="OpenAI",
                description="GPT-4, GPT-4o, and other OpenAI models",
                enabled=True,
            ),
            "azure": ProviderConfig(
                name="azure",
                display_name="Azure OpenAI",
                description="Enterprise Azure-hosted OpenAI models",
                enabled=True,
            ),
            "anthropic": ProviderConfig(
                name="anthropic",
                display_name="Anthropic",
                description="Claude models - excellent for writing and analysis",
                enabled=False,
            ),
            "openrouter": ProviderConfig(
                name="openrouter",
                display_name="OpenRouter",
                description="Access 100+ models through one API",
                enabled=False,
            ),
            "local": ProviderConfig(
                name="local",
                display_name="Local / Docker Model Runner",
                description="Local models via Docker Model Runner or Ollama",
                enabled=True,
                api_base="http://model-runner.docker.internal/v1",
            ),
        },
        models={
            # OpenAI models
            "gpt-4o": ModelConfig(
                id="gpt-4o",
                provider="openai",
                display_name="GPT-4o",
                capabilities=["reasoning", "coding", "creative"],
                category="balanced",
                input_cost=2.50,
                output_cost=10.00,
                context_window=128000,
            ),
            "gpt-4o-mini": ModelConfig(
                id="gpt-4o-mini",
                provider="openai",
                display_name="GPT-4o Mini",
                capabilities=["fast", "coding"],
                category="fast",
                input_cost=0.15,
                output_cost=0.60,
                context_window=128000,
            ),
            "o1-preview": ModelConfig(
                id="o1-preview",
                provider="openai",
                display_name="o1 Preview",
                capabilities=["reasoning", "complex"],
                category="reasoning",
                input_cost=15.00,
                output_cost=60.00,
                context_window=128000,
            ),

            # Anthropic models
            "claude-3-opus": ModelConfig(
                id="claude-3-opus-20240229",
                provider="anthropic",
                display_name="Claude 3 Opus",
                capabilities=["reasoning", "creative", "writing"],
                category="quality",
                input_cost=15.00,
                output_cost=75.00,
                context_window=200000,
            ),
            "claude-3-sonnet": ModelConfig(
                id="claude-3-5-sonnet-20241022",
                provider="anthropic",
                display_name="Claude 3.5 Sonnet",
                capabilities=["reasoning", "coding", "creative"],
                category="balanced",
                input_cost=3.00,
                output_cost=15.00,
                context_window=200000,
            ),
            "claude-3-haiku": ModelConfig(
                id="claude-3-haiku-20240307",
                provider="anthropic",
                display_name="Claude 3 Haiku",
                capabilities=["fast"],
                category="fast",
                input_cost=0.25,
                output_cost=1.25,
                context_window=200000,
            ),

            # Local models - IDs must match Docker Model Runner format (ai/ prefix)
            "qwen3-8b": ModelConfig(
                id="ai/qwen3:8B-Q4_0",
                provider="local",
                display_name="Qwen3 8B (Local)",
                capabilities=["reasoning", "coding", "tool_calling"],
                category="local",
                input_cost=0.0,
                output_cost=0.0,
                context_window=32000,
            ),
            "qwen3-14b": ModelConfig(
                id="ai/qwen3:14B-Q6_K",
                provider="local",
                display_name="Qwen3 14B (Local)",
                capabilities=["reasoning", "coding", "tool_calling", "creative"],
                category="local",
                input_cost=0.0,
                output_cost=0.0,
                context_window=32000,
            ),
            "phi-4": ModelConfig(
                id="ai/phi4:latest",
                provider="local",
                display_name="Phi-4 (Local)",
                capabilities=["fast", "reasoning"],
                category="local",
                input_cost=0.0,
                output_cost=0.0,
                context_window=16000,
            ),
            "llama-3": ModelConfig(
                id="ai/llama3.2:latest",
                provider="local",
                display_name="Llama 3.2 (Local)",
                capabilities=["fast", "coding"],
                category="local",
                input_cost=0.0,
                output_cost=0.0,
                context_window=128000,
            ),
        },
        default_model_id="qwen3-8b",  # Default to local Qwen3 with tool calling support
        groups=[
            GroupModelAssignment(
                group_name="content",
                agent_names=["content-writer", "content-generator"],
                model_id="claude-3-sonnet",  # Best for writing
            ),
            GroupModelAssignment(
                group_name="analysis",
                agent_names=["seo-analyst", "trend-analyzer", "competitor-monitor"],
                model_id="gpt-4o-mini",  # Fast and cheap for analysis
            ),
        ],
        agent_assignments={
            "content-writer": AgentModelAssignment(
                agent_name="content-writer",
                model_id="claude-3-opus",  # Highest quality for final content
                fallback_model_id="claude-3-sonnet",
                temperature=0.7,
            ),
        },
    )


def discover_docker_models(api_base: str | None = None) -> list[ModelConfig]:
    """Discover available models from Docker Model Runner."""
    if api_base is None:
        api_base = "http://model-runner.docker.internal/v1"

    models = []
    try:
        # Docker Model Runner uses OpenAI-compatible API
        response = httpx.get(f"{api_base}/models", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            for model in data.get("data", []):
                model_id = model.get("id", "")
                if not model_id:
                    continue

                # Create a clean display name (remove ai/ prefix for display)
                display_name = model_id.replace("ai/", "").replace(":", " ").replace("-", " ").title()

                # Detect capabilities based on model name
                capabilities = ["reasoning"]
                model_lower = model_id.lower()
                if "qwen" in model_lower:
                    capabilities.extend(["coding", "tool_calling"])
                if "code" in model_lower or "coder" in model_lower:
                    capabilities.append("coding")
                if "instruct" in model_lower or "chat" in model_lower:
                    capabilities.append("chat")

                # Docker Model Runner may need ai/ prefix for some models
                # Try both formats - store the one from the API response
                models.append(ModelConfig(
                    id=model_id,  # Use exact ID from Docker Model Runner
                    provider="local",
                    display_name=f"{display_name} (Local)",
                    capabilities=capabilities,
                    category="local",
                    input_cost=0.0,
                    output_cost=0.0,
                    context_window=32000,  # Conservative default
                ))
                logger.debug(f"Discovered model: {model_id}")

        logger.info(f"Discovered {len(models)} models from Docker Model Runner")
    except Exception as e:
        logger.debug(f"Could not discover Docker models: {e}")

    return models


def get_llm_settings() -> LLMSettings:
    """Load LLM settings from config file or return defaults, with dynamic model discovery."""
    if LLM_CONFIG_FILE.exists():
        try:
            with open(LLM_CONFIG_FILE, "r") as f:
                data = json.load(f)
                settings = LLMSettings.model_validate(data)
        except Exception as e:
            logger.error("Failed to load LLM settings", error=str(e))
            settings = get_default_settings()
    else:
        settings = get_default_settings()

    # Discover and add Docker Model Runner models
    local_provider = settings.providers.get("local")
    api_base = local_provider.api_base if local_provider else None
    docker_models = discover_docker_models(api_base)

    for model in docker_models:
        # Use model ID as key, replacing special chars
        key = model.id.replace(":", "-").replace("/", "-").lower()
        if key not in settings.models:
            settings.models[key] = model

    # If we found docker models and default doesn't exist, set first docker model as default
    if docker_models and settings.default_model_id not in settings.models:
        first_key = docker_models[0].id.replace(":", "-").replace("/", "-").lower()
        settings.default_model_id = first_key
        logger.info(f"Set default model to discovered: {first_key}")

    return settings


def save_llm_settings(settings: LLMSettings) -> bool:
    """Save LLM settings to config file."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        with open(LLM_CONFIG_FILE, "w") as f:
            json.dump(settings.model_dump(), f, indent=2)

        logger.info("LLM settings saved", file=str(LLM_CONFIG_FILE))
        return True
    except Exception as e:
        logger.error("Failed to save LLM settings", error=str(e))
        return False


# Redis-based storage for production (optional)
class RedisLLMSettingsStore:
    """Store LLM settings in Redis for multi-instance deployments."""

    SETTINGS_KEY = "llm:settings"

    def __init__(self, redis_url: str):
        import redis
        self.redis = redis.from_url(redis_url)

    def get(self) -> LLMSettings:
        """Get settings from Redis."""
        data = self.redis.get(self.SETTINGS_KEY)
        if data:
            return LLMSettings.model_validate_json(data)
        return get_default_settings()

    def save(self, settings: LLMSettings) -> bool:
        """Save settings to Redis."""
        try:
            self.redis.set(self.SETTINGS_KEY, settings.model_dump_json())
            return True
        except Exception as e:
            logger.error("Failed to save to Redis", error=str(e))
            return False
