"""
Teams App Manifest Generator

Generates the manifest.json for deploying as a Teams app
and for importing into Copilot Studio.
"""

import json
from typing import Any
from uuid import uuid4


def generate_teams_manifest(
    app_id: str,
    app_name: str = "SEO Agent",
    app_description: str = "AI-powered SEO optimization for the AI Overview era",
    developer_name: str = "Your Company",
    website_url: str = "https://your-website.com",
    privacy_url: str = "https://your-website.com/privacy",
    terms_url: str = "https://your-website.com/terms",
    bot_id: str | None = None,
    version: str = "1.0.0",
) -> dict[str, Any]:
    """
    Generate a Teams app manifest.

    This manifest can be:
    1. Packaged as a Teams app (.zip with manifest.json + icons)
    2. Imported into Copilot Studio for customization

    Args:
        app_id: Microsoft App ID from Azure Bot registration
        app_name: Display name of the app
        app_description: Short description
        developer_name: Your company name
        website_url: Your website
        privacy_url: Privacy policy URL
        terms_url: Terms of service URL
        bot_id: Bot ID (usually same as app_id)
        version: App version

    Returns:
        Manifest dictionary
    """
    bot_id = bot_id or app_id

    return {
        "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
        "manifestVersion": "1.16",
        "version": version,
        "id": app_id,
        "packageName": "com.seoagent.teams",
        "developer": {
            "name": developer_name,
            "websiteUrl": website_url,
            "privacyUrl": privacy_url,
            "termsOfUseUrl": terms_url
        },
        "name": {
            "short": app_name,
            "full": f"{app_name} - AI Overview Optimization"
        },
        "description": {
            "short": app_description,
            "full": (
                "SEO Agent helps you diagnose and respond to traffic changes caused by "
                "Google's AI Overviews. It analyzes your search performance, identifies "
                "which queries trigger AI Overviews, and generates optimizations to improve "
                "your citation rates. Features include traffic monitoring, schema markup "
                "generation, FAQ creation, and agent-friendliness testing."
            )
        },
        "icons": {
            "color": "color.png",
            "outline": "outline.png"
        },
        "accentColor": "#0078D4",
        "bots": [
            {
                "botId": bot_id,
                "scopes": ["personal", "team", "groupchat"],
                "supportsFiles": False,
                "isNotificationOnly": False,
                "commandLists": [
                    {
                        "scopes": ["personal", "team", "groupchat"],
                        "commands": [
                            {
                                "title": "analyze",
                                "description": "Run full SEO analysis"
                            },
                            {
                                "title": "check",
                                "description": "Check queries for AI Overviews"
                            },
                            {
                                "title": "status",
                                "description": "Show current status"
                            },
                            {
                                "title": "agents",
                                "description": "List available agents"
                            },
                            {
                                "title": "help",
                                "description": "Show help information"
                            }
                        ]
                    }
                ]
            }
        ],
        "permissions": [
            "identity",
            "messageTeamMembers"
        ],
        "validDomains": [
            "*.azurewebsites.net",
            "*.botframework.com"
        ],
        # Copilot Studio integration
        "copilotAgents": {
            "declarativeAgents": [
                {
                    "id": "seoAgent",
                    "name": "SEO Agent",
                    "description": "Analyzes and optimizes for Google AI Overviews",
                    "instructions": (
                        "You are an SEO expert that helps users understand and optimize "
                        "for Google's AI Overviews. You can analyze search performance, "
                        "check which queries trigger AI Overviews, generate schema markup, "
                        "create FAQ content, and provide recommendations to improve citation rates."
                    ),
                    "capabilities": [
                        {
                            "name": "actions",
                            "actions": [
                                {"id": "analyzeQueries"},
                                {"id": "checkAIOStatus"},
                                {"id": "generateSchema"},
                                {"id": "generateFAQ"},
                                {"id": "runMonitoring"}
                            ]
                        }
                    ]
                }
            ]
        },
        # Plugin definition for Copilot
        "plugins": [
            {
                "pluginFile": "ai-plugin.json"
            }
        ]
    }


def generate_ai_plugin_manifest(
    api_base_url: str,
    app_name: str = "SEO Agent",
) -> dict[str, Any]:
    """
    Generate the AI plugin manifest for Copilot Studio.

    This defines the actions/capabilities available to Copilot.
    """
    return {
        "schema_version": "v1",
        "name_for_human": app_name,
        "name_for_model": "seo_agent",
        "description_for_human": "AI-powered SEO optimization for Google AI Overviews",
        "description_for_model": (
            "Use this plugin to analyze search performance, check AI Overview status, "
            "generate schema markup, create FAQ content, and optimize for AI citations. "
            "Call analyzeQueries to get SEO analysis. Call checkAIOStatus with queries "
            "to check if they trigger AI Overviews. Call generateSchema to create "
            "Schema.org markup. Call generateFAQ to create FAQ content."
        ),
        "auth": {
            "type": "api_key",
            "authorization_type": "header",
            "header_name": "X-API-Key"
        },
        "api": {
            "type": "openapi",
            "url": f"{api_base_url}/openapi.json"
        },
        "functions": [
            {
                "name": "analyzeQueries",
                "description": "Run SEO analysis on top queries",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of queries to analyze"
                        }
                    }
                }
            },
            {
                "name": "checkAIOStatus",
                "description": "Check if queries trigger AI Overviews",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "queries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of queries to check"
                        }
                    },
                    "required": ["queries"]
                }
            },
            {
                "name": "generateSchema",
                "description": "Generate Schema.org markup for a page",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Page URL"},
                        "page_type": {"type": "string", "description": "Type of page"}
                    },
                    "required": ["page_type"]
                }
            },
            {
                "name": "generateFAQ",
                "description": "Generate FAQ content for a topic",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "FAQ topic"},
                        "num_faqs": {"type": "integer", "description": "Number of FAQs"}
                    },
                    "required": ["topic"]
                }
            },
            {
                "name": "testPage",
                "description": "Test a page for AI agent friendliness",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Page URL to test"}
                    },
                    "required": ["url"]
                }
            }
        ]
    }


def generate_copilot_studio_package(
    app_id: str,
    api_base_url: str,
    output_dir: str = "./teams-app",
) -> None:
    """
    Generate a complete package for Teams/Copilot Studio deployment.

    Creates:
    - manifest.json
    - ai-plugin.json
    - Placeholder icons

    Args:
        app_id: Microsoft App ID
        api_base_url: Your API's base URL
        output_dir: Directory to write files to
    """
    import os

    os.makedirs(output_dir, exist_ok=True)

    # Write manifest
    manifest = generate_teams_manifest(app_id)
    with open(os.path.join(output_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # Write AI plugin manifest
    ai_plugin = generate_ai_plugin_manifest(api_base_url)
    with open(os.path.join(output_dir, "ai-plugin.json"), "w") as f:
        json.dump(ai_plugin, f, indent=2)

    # Create placeholder icon files (in production, use real icons)
    # Color icon: 192x192 PNG
    # Outline icon: 32x32 PNG
    for icon_name in ["color.png", "outline.png"]:
        icon_path = os.path.join(output_dir, icon_name)
        if not os.path.exists(icon_path):
            # Create a simple placeholder (1x1 transparent PNG)
            # In production, replace with actual icons
            with open(icon_path, "wb") as f:
                # Minimal valid PNG (1x1 transparent)
                f.write(bytes([
                    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
                    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
                    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
                    0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
                    0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
                    0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
                    0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
                    0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
                    0x42, 0x60, 0x82
                ]))

    print(f"Teams app package generated in {output_dir}/")
    print("Next steps:")
    print("1. Replace color.png (192x192) and outline.png (32x32) with real icons")
    print("2. Zip the contents: zip -r seo-agent.zip manifest.json ai-plugin.json *.png")
    print("3. Upload to Teams Admin Center or Copilot Studio")
