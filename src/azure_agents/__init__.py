"""
Azure AI Agent Service Compatibility Layer

This module provides a unified way to define agents that can run:
1. Locally (using our custom implementation)
2. On Azure AI Agent Service (using Azure SDK)

The same agent definitions work in both environments.
"""

from src.azure_agents.definitions import (
    AgentDefinition,
    ToolDefinition,
    SEO_ANALYST_AGENT,
    AGENT_TESTER_AGENT,
    MONITORING_AGENT,
    OPTIMIZER_AGENT,
    ALL_AGENTS,
)
from src.azure_agents.runner import AgentRunner, LocalAgentRunner
from src.azure_agents.client import AzureAgentClient

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
