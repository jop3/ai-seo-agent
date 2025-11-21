#!/usr/bin/env python
"""
CLI commands for workflow onboarding and configuration.

Usage:
    python -m src.cli_onboarding setup          # Interactive setup
    python -m src.cli_onboarding quick <domain> # Quick setup
    python -m src.cli_onboarding list           # List configs
    python -m src.cli_onboarding show <name>    # Show config
    python -m src.cli_onboarding test <name>    # Test config
"""

import asyncio
import json
import sys
from typing import Any

import structlog
import typer

from src.orchestrator.onboarding import OnboardingFlow, ConfigManager, quick_setup
from src.orchestrator import get_workflow, list_workflows

logger = structlog.get_logger()
app = typer.Typer(help="AI SEO Agent - Configuration & Onboarding")


@app.command()
def setup(
    name: str = typer.Option("default", "--name", "-n", help="Configuration name"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save configuration"),
):
    """
    Interactive setup wizard.

    Guides you through configuration with smart questions.
    """
    typer.echo("\n🚀 Starting AI SEO Agent setup wizard...\n")

    flow = OnboardingFlow()
    config = flow.start(interactive=True)

    if save:
        manager = ConfigManager()
        config_path = manager.save(config, name)
        typer.echo(f"\n💾 Configuration saved to: {config_path}")
        typer.echo(f"📝 Config name: '{name}'\n")

    # Show recommended workflows
    typer.echo("📋 Recommended workflows for your site:\n")
    workflows = _recommend_workflows(flow.site_type)
    for wf in workflows:
        typer.echo(f"  • {wf['name']}: {wf['description']}")

    typer.echo("\n✨ Setup complete! You're ready to run workflows.\n")
    typer.echo("Next steps:")
    typer.echo("  1. Test your config: python -m src.cli_onboarding test")
    typer.echo(f"  2. Run a workflow: python -m src.cli run-workflow {workflows[0]['id']} --config {name}")
    typer.echo()


@app.command()
def quick(
    domain: str = typer.Argument(..., help="Your domain (e.g., example.com)"),
    competitors: str = typer.Option(None, "--competitors", "-c", help="Comma-separated competitor domains"),
    business_name: str = typer.Option(None, "--business", "-b", help="Business name"),
    name: str = typer.Option("default", "--name", "-n", help="Configuration name"),
):
    """
    Quick non-interactive setup.

    Creates basic configuration with minimal input.
    """
    competitor_list = competitors.split(",") if competitors else []

    config = quick_setup(
        domain=domain,
        competitors=competitor_list,
        business_name=business_name,
    )

    manager = ConfigManager()
    config_path = manager.save(config, name)

    typer.echo(f"\n✅ Configuration created: '{name}'")
    typer.echo(f"📍 Domain: {domain}")
    if competitor_list:
        typer.echo(f"🎯 Competitors: {len(competitor_list)}")
    typer.echo(f"💾 Saved to: {config_path}\n")


@app.command("list")
def list_configs():
    """List all saved configurations."""
    manager = ConfigManager()
    configs = manager.list_configs()

    if not configs:
        typer.echo("\n⚠️  No saved configurations found.\n")
        typer.echo("Create one with: python -m src.cli_onboarding setup\n")
        return

    typer.echo("\n📋 Saved Configurations:\n")
    for name in configs:
        config = manager.load(name)
        if config:
            typer.echo(f"  • {name}")
            typer.echo(f"    Domain: {config.targets.primary_domain}")
            if config.targets.competitors:
                typer.echo(f"    Competitors: {len(config.targets.competitors)}")
            if config.business_info:
                typer.echo(f"    Business: {config.business_info.name}")
            typer.echo()


@app.command()
def show(
    name: str = typer.Argument("default", help="Configuration name"),
    format: str = typer.Option("summary", "--format", "-f", help="Output format: summary, json, yaml"),
):
    """Show detailed configuration."""
    manager = ConfigManager()
    config = manager.load(name)

    if not config:
        typer.echo(f"\n❌ Configuration '{name}' not found.\n")
        return

    if format == "json":
        typer.echo(json.dumps(config.model_dump(), indent=2))
    elif format == "yaml":
        try:
            import yaml
            typer.echo(yaml.dump(config.model_dump(), default_flow_style=False))
        except ImportError:
            typer.echo("⚠️  PyYAML not installed. Install with: pip install pyyaml")
    else:
        # Summary format
        typer.echo(f"\n📋 Configuration: {name}")
        typer.echo("=" * 70)
        typer.echo(f"\n🌐 Target")
        typer.echo(f"  Domain: {config.targets.primary_domain}")
        typer.echo(f"  URL: {config.targets.property_url}")

        if config.targets.competitors:
            typer.echo(f"\n🎯 Competitors ({len(config.targets.competitors)})")
            for comp in config.targets.competitors:
                typer.echo(f"  • {comp.domain} ({comp.priority} priority)")

        if config.business_info:
            typer.echo(f"\n🏢 Business")
            typer.echo(f"  Name: {config.business_info.name}")
            if config.business_info.description:
                typer.echo(f"  Description: {config.business_info.description}")
            if config.business_info.city:
                typer.echo(f"  Location: {config.business_info.city}, {config.business_info.state}")

        if config.default_author:
            typer.echo(f"\n✍️  Default Author")
            typer.echo(f"  Name: {config.default_author.name}")
            if config.default_author.credentials:
                typer.echo(f"  Credentials: {len(config.default_author.credentials)}")

        if config.targets.target_queries:
            typer.echo(f"\n🔍 Target Queries ({len(config.targets.target_queries)})")
            for q in config.targets.target_queries[:5]:
                typer.echo(f"  • {q}")
            if len(config.targets.target_queries) > 5:
                typer.echo(f"  ... and {len(config.targets.target_queries) - 5} more")

        typer.echo(f"\n⚙️  Options")
        typer.echo(f"  Analysis Depth: {config.options.analysis_depth}")
        typer.echo(f"  Lookback Days: {config.options.days_back}")
        typer.echo(f"  AI Engines: {', '.join(config.options.ai_engines)}")

        typer.echo(f"\n🎚️  Thresholds")
        typer.echo(f"  Traffic Drop Alert: {config.thresholds.traffic_drop_threshold_pct}%")
        typer.echo(f"  Content Decay: {config.thresholds.content_decay_days} days")
        typer.echo(f"  Min E-E-A-T Score: {config.thresholds.min_eeat_score}/100")
        typer.echo()


@app.command()
def test(
    name: str = typer.Argument("default", help="Configuration name"),
):
    """
    Test configuration validity.

    Validates the configuration and checks what features are enabled.
    """
    manager = ConfigManager()
    config = manager.load(name)

    if not config:
        typer.echo(f"\n❌ Configuration '{name}' not found.\n")
        return

    typer.echo(f"\n🧪 Testing configuration: {name}\n")

    # Validate structure
    try:
        params = config.to_params()
        typer.echo("✅ Configuration is valid\n")
    except Exception as e:
        typer.echo(f"❌ Configuration error: {e}\n")
        return

    # Check what's enabled
    typer.echo("📊 Feature Availability:\n")

    features = {
        "Traffic Monitoring": True,  # Always available
        "Technical SEO Audit": True,  # Always available
        "SERP Analysis": True,  # Always available
        "Competitor Analysis": bool(config.targets.competitors),
        "Citation Tracking": bool(config.targets.competitors),
        "Local SEO": bool(config.business_info and config.business_info.street_address),
        "E-E-A-T Analysis": bool(config.default_author or config.business_info),
        "Author Schema": bool(config.default_author),
        "LocalBusiness Schema": bool(config.business_info and config.business_info.street_address),
        "Organization Schema": bool(config.business_info),
        "Social Signals": bool(config.business_info and (
            config.business_info.facebook_url or
            config.business_info.twitter_url or
            config.business_info.linkedin_url
        )),
    }

    for feature, enabled in features.items():
        status = "✅" if enabled else "⊘ "
        typer.echo(f"  {status} {feature}")

    # Recommendations
    typer.echo("\n💡 Recommendations:\n")

    if not config.targets.competitors:
        typer.echo("  • Add competitors for competitive analysis")

    if not config.business_info:
        typer.echo("  • Add business info for better schema recommendations")

    if not config.default_author and config.business_info:
        typer.echo("  • Add author info for E-E-A-T scoring")

    if config.business_info and not config.business_info.street_address:
        typer.echo("  • Add business address for local SEO features")

    typer.echo()


@app.command()
def delete(
    name: str = typer.Argument(..., help="Configuration name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a saved configuration."""
    if not yes:
        confirm = typer.confirm(f"Delete configuration '{name}'?")
        if not confirm:
            typer.echo("Cancelled.")
            return

    manager = ConfigManager()
    if manager.delete(name):
        typer.echo(f"\n✅ Configuration '{name}' deleted.\n")
    else:
        typer.echo(f"\n❌ Configuration '{name}' not found.\n")


@app.command()
def workflows():
    """List all available workflows."""
    typer.echo("\n📋 Available Workflows:\n")

    for wf in list_workflows():
        typer.echo(f"\n  {wf['id']}")
        typer.echo(f"  {wf['name']}")
        typer.echo(f"  {wf['description']}")
        typer.echo(f"  Steps: {wf['steps']}")


def _recommend_workflows(site_type: str | None) -> list[dict[str, Any]]:
    """Recommend workflows based on site type."""
    recommendations = {
        "ecommerce": [
            {"id": "full_audit", "name": "Full Audit", "description": "Monthly comprehensive review"},
            {"id": "content", "name": "Content Analysis", "description": "Product content optimization"},
            {"id": "competitive", "name": "Competitive Analysis", "description": "Track competitors"},
        ],
        "local": [
            {"id": "local_seo", "name": "Local SEO", "description": "Local business optimization"},
            {"id": "quick_check", "name": "Quick Check", "description": "Daily monitoring"},
            {"id": "full_audit", "name": "Full Audit", "description": "Monthly review"},
        ],
        "content": [
            {"id": "content", "name": "Content Analysis", "description": "Content quality and decay"},
            {"id": "ai_readiness", "name": "AI Readiness", "description": "Optimize for AI search"},
            {"id": "full_audit", "name": "Full Audit", "description": "Comprehensive analysis"},
        ],
        "saas": [
            {"id": "technical", "name": "Technical Analysis", "description": "Technical SEO audit"},
            {"id": "ai_readiness", "name": "AI Readiness", "description": "AI search optimization"},
            {"id": "competitive", "name": "Competitive Analysis", "description": "Competitor tracking"},
        ],
    }

    return recommendations.get(site_type, [
        {"id": "quick_check", "name": "Quick Check", "description": "Daily monitoring"},
        {"id": "full_audit", "name": "Full Audit", "description": "Comprehensive analysis"},
    ])


if __name__ == "__main__":
    app()
