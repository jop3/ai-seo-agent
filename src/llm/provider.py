"""
LLM Provider using LiteLLM

Provides a unified interface to call any LLM through LiteLLM.
Handles:
- Provider routing based on agent/task
- Fallback logic
- Cost tracking
- Caching
"""

import os
from typing import Any
from functools import lru_cache

import litellm
import structlog

from src.llm.config import (
    LLMSettings,
    ModelConfig,
    get_llm_settings,
)

logger = structlog.get_logger()

# Configure LiteLLM
litellm.set_verbose = False  # Set to True for debugging


class LLMProvider:
    """
    Unified LLM provider using LiteLLM.

    Automatically routes requests to the appropriate provider based on
    agent assignments and model configuration.
    """

    def __init__(self, settings: LLMSettings | None = None):
        self.settings = settings or get_llm_settings()
        self._configure_providers()

    def _configure_providers(self):
        """Configure LiteLLM with provider credentials."""
        for name, provider in self.settings.providers.items():
            if not provider.enabled:
                continue

            if provider.api_key:
                # Set environment variables for LiteLLM
                if name == "openai":
                    os.environ["OPENAI_API_KEY"] = provider.api_key
                elif name == "anthropic":
                    os.environ["ANTHROPIC_API_KEY"] = provider.api_key
                elif name == "azure":
                    os.environ["AZURE_API_KEY"] = provider.api_key
                    if provider.api_base:
                        os.environ["AZURE_API_BASE"] = provider.api_base
                    os.environ["AZURE_API_VERSION"] = provider.azure_api_version
                elif name == "openrouter":
                    os.environ["OPENROUTER_API_KEY"] = provider.api_key

            if name == "local" and provider.api_base:
                # For local models, we'll handle the base URL per-request
                pass

    def get_model_for_agent(self, agent_name: str) -> ModelConfig:
        """Get the model configuration for a specific agent."""
        return self.settings.get_model_for_agent(agent_name)

    async def chat(
        self,
        messages: list[dict[str, str]],
        agent_name: str | None = None,
        model_override: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            agent_name: Name of the agent making the request (for routing)
            model_override: Override the model selection
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            json_mode: Request JSON output
            tools: Function/tool definitions for function calling
            tool_choice: How to handle tool selection

        Returns:
            Dict with 'content', 'tool_calls', 'model', 'usage'
        """
        # Determine model to use
        if model_override:
            model_config = self.settings.models.get(model_override)
            if not model_config:
                model_config = ModelConfig(
                    id=model_override,
                    provider="openai",
                    display_name=model_override,
                )
        elif agent_name:
            model_config = self.get_model_for_agent(agent_name)
        else:
            model_config = self.settings.models.get(self.settings.default_model_id)
            if not model_config:
                model_config = ModelConfig(
                    id="gpt-4o",
                    provider="openai",
                    display_name="GPT-4o",
                )

        # Check for agent-specific overrides
        if agent_name and agent_name in self.settings.agent_assignments:
            assignment = self.settings.agent_assignments[agent_name]
            if assignment.temperature is not None:
                temperature = assignment.temperature
            if assignment.max_tokens is not None:
                max_tokens = assignment.max_tokens

        # Build LiteLLM model name
        model_name = model_config.get_litellm_model_name()

        # Build kwargs
        kwargs: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Handle local provider (OpenAI-compatible endpoint like Docker Model Runner)
        if model_config.provider == "local":
            provider_config = self.settings.providers.get("local")
            # Default Docker Model Runner endpoint - try simpler v1 endpoint
            api_base = "http://model-runner.docker.internal/v1"
            if provider_config and provider_config.api_base:
                api_base = provider_config.api_base
            kwargs["api_base"] = api_base
            kwargs["api_key"] = "not-needed"
            # Use raw model ID - Docker Model Runner expects just the model name
            kwargs["model"] = model_config.id
            kwargs["custom_llm_provider"] = "openai"

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        if tools:
            kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice

        logger.info(
            "LLM request",
            model=kwargs["model"],
            api_base=kwargs.get("api_base"),
            agent=agent_name,
            provider=model_config.provider,
        )

        try:
            # For local models, use OpenAI client directly (more reliable than LiteLLM)
            if model_config.provider == "local" and kwargs.get("api_base"):
                response = await self._call_local_model(kwargs)
            else:
                # Use LiteLLM's async completion for cloud providers
                response = await litellm.acompletion(**kwargs)

            # Extract response
            choice = response.choices[0]
            result = {
                "content": choice.message.content,
                "tool_calls": None,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
            }

            # Handle tool calls
            if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ]

            logger.debug(
                "LLM response",
                model=response.model,
                tokens=result["usage"]["total_tokens"],
            )

            return result

        except Exception as e:
            logger.error(
                "LLM request failed",
                model=model_name,
                error=str(e),
            )

            # Try fallback if available
            if self.settings.enable_fallbacks and agent_name:
                fallback_model_id = self._get_fallback_model(agent_name, model_config.id)
                if fallback_model_id:
                    logger.info("Trying fallback model", fallback=fallback_model_id)
                    return await self.chat(
                        messages=messages,
                        model_override=fallback_model_id,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        json_mode=json_mode,
                        tools=tools,
                        tool_choice=tool_choice,
                    )

            raise

    async def _call_local_model(self, kwargs: dict[str, Any]) -> Any:
        """Call local model using OpenAI client directly."""
        from openai import AsyncOpenAI

        model_id = kwargs["model"]
        api_base = kwargs["api_base"]

        # Debug: log exact values
        logger.info(
            "Local model call",
            model_id=model_id,
            model_id_repr=repr(model_id),
            api_base=api_base,
        )

        client = AsyncOpenAI(
            api_key="not-needed",
            base_url=api_base,
        )

        # Build the request params
        params = {
            "model": model_id,
            "messages": kwargs["messages"],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000),
        }

        if kwargs.get("tools"):
            params["tools"] = kwargs["tools"]
        if kwargs.get("tool_choice"):
            params["tool_choice"] = kwargs["tool_choice"]

        return await client.chat.completions.create(**params)

    def _get_fallback_model(self, agent_name: str, current_model_id: str) -> str | None:
        """Get fallback model for an agent."""
        # Check individual assignment
        if agent_name in self.settings.agent_assignments:
            assignment = self.settings.agent_assignments[agent_name]
            if assignment.fallback_model_id and assignment.fallback_model_id != current_model_id:
                return assignment.fallback_model_id

        # Check group assignment
        for group in self.settings.groups:
            if agent_name in group.agent_names:
                if group.fallback_model_id and group.fallback_model_id != current_model_id:
                    return group.fallback_model_id

        # Fall back to default if not already using it
        if self.settings.default_model_id != current_model_id:
            return self.settings.default_model_id

        return None

    async def simple_completion(
        self,
        prompt: str,
        agent_name: str | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        """Simple helper for single-turn completions."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        result = await self.chat(messages=messages, agent_name=agent_name, **kwargs)
        return result.get("content", "")

    def get_available_models(self) -> list[ModelConfig]:
        """Get list of available models."""
        return list(self.settings.models.values())

    def get_models_by_category(self, category: str) -> list[ModelConfig]:
        """Get models filtered by category."""
        return [m for m in self.settings.models.values() if m.category == category]

    def get_models_by_capability(self, capability: str) -> list[ModelConfig]:
        """Get models that have a specific capability."""
        return [
            m for m in self.settings.models.values()
            if capability in m.capabilities
        ]


# Singleton instance
_provider_instance: LLMProvider | None = None


def get_llm_provider(refresh: bool = False) -> LLMProvider:
    """Get the singleton LLM provider instance."""
    global _provider_instance

    if _provider_instance is None or refresh:
        _provider_instance = LLMProvider()

    return _provider_instance


def refresh_llm_provider():
    """Refresh the LLM provider with latest settings."""
    global _provider_instance
    _provider_instance = LLMProvider()
