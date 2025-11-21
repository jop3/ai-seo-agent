"""
Microsoft 365 Agents SDK Integration

This module enables the SEO agents to run as a Teams bot that can:
1. Respond to direct messages in Teams
2. Be @mentioned in channels
3. Be imported into Copilot Studio
4. Use Adaptive Cards for rich UI

Prerequisites:
- Azure Bot Service registration
- Teams app manifest
- Microsoft App ID and Password
"""

from src.m365_agents.bot import SEOAgentBot
from src.m365_agents.cards import AdaptiveCardBuilder
from src.m365_agents.manifest import generate_teams_manifest

__all__ = [
    "SEOAgentBot",
    "AdaptiveCardBuilder",
    "generate_teams_manifest",
]
