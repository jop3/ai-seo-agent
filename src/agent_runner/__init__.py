"""
Agent Runner - Multi-Provider Agent Execution Layer

This module provides a unified way to define agents that can run:
1. Locally (using our custom implementation with any LLM provider)
2. On Azure AI Agent Service (using Azure SDK)
3. On other cloud AI services

The same agent definitions work across all environments.
"""

from src.agent_runner.definitions import (
    AgentDefinition,
    ToolDefinition,
    SEO_ANALYST_AGENT,
    AGENT_TESTER_AGENT,
    MONITORING_AGENT,
    OPTIMIZER_AGENT,
    ALL_AGENTS,
)
from src.agent_runner.runner import AgentRunner, LocalAgentRunner
from src.agent_runner.client import AzureAgentClient

__all__ = [
    "AgentDefinition",
    "ToolDefinition",
    "SEO_ANALYST_AGENT",
    "AGENT_TESTER_AGENT",
    "MONITORING_AGENT",
    "OPTIMIZER_AGENT",
    "ALL_AGENTS",
    "AgentRunner",
    "LocalAgentRunner",
    "AzureAgentClient",
]
