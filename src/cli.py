"""CLI for AI SEO Agent."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config import get_settings

app = typer.Typer(
    name="seo-agent",
    help="AI SEO Agent - Optimize for the AI Overview era",
)
console = Console()


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
):
    """Start the API server."""
    import uvicorn

    console.print(f"[green]Starting AI SEO Agent API on {host}:{port}[/green]")

    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def analyze(
    queries: Optional[list[str]] = typer.Option(None, "--query", "-q", help="Queries to analyze"),
    full: bool = typer.Option(False, "--full", "-f", help="Run full analysis"),
    limit: int = typer.Option(100, "--limit", "-l", help="Query limit for full analysis"),
):
    """Run SEO analysis."""
    asyncio.run(_analyze(queries, full, limit))


async def _analyze(queries: Optional[list[str]], full: bool, limit: int):
    from src.agents.base import AgentContext
    from src.agents.seo_analyst import SEOAnalystAgent
    from src.api.dependencies import get_agent_context
    from src.models.agents import AgentTask

    settings = get_settings()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing...", total=None)

        # Create context
        from src.integrations.azure_openai import AzureOpenAIClient
        from src.integrations.google_search_console import GoogleSearchConsoleClient
        from src.integrations.serp import get_serp_client
        from src.integrations.teams import TeamsNotifier

        openai_client = AzureOpenAIClient(settings.azure)

        gsc_client = None
        if settings.google.gsc_property_url:
            gsc_client = GoogleSearchConsoleClient(
                credentials_path=settings.google.gsc_credentials_path,
                property_url=settings.google.gsc_property_url,
            )

        serp_client = None
        if settings.google.gsc_property_url:
            from urllib.parse import urlparse
            domain = urlparse(settings.google.gsc_property_url).netloc
            serp_client = get_serp_client(settings.serp, domain)

        teams_notifier = None
        webhook_url = settings.alerts.teams_webhook_url.get_secret_value()
        if webhook_url:
            teams_notifier = TeamsNotifier(webhook_url)

        context = AgentContext(
            settings=settings,
            openai_client=openai_client,
            gsc_client=gsc_client,
            serp_client=serp_client,
            teams_notifier=teams_notifier,
            client_domain=urlparse(settings.google.gsc_property_url).netloc if settings.google.gsc_property_url else "",
            property_url=settings.google.gsc_property_url,
        )

        agent = SEOAnalystAgent(context)

        if full:
            progress.update(task, description="Running full analysis...")

            agent_task = AgentTask(
                agent_type=agent.agent_type,
                task_type="full_analysis",
                parameters={"query_limit": limit},
            )
        elif queries:
            progress.update(task, description="Checking AIO status...")

            agent_task = AgentTask(
                agent_type=agent.agent_type,
                task_type="detect_aio_impact",
                parameters={"queries": queries},
            )
        else:
            console.print("[red]Please provide --query or --full[/red]")
            return

        result = await agent.run(agent_task)

    if result.success:
        console.print("\n[green]Analysis Complete![/green]\n")

        # Display results
        if full:
            data = result.data

            # Summary table
            table = Table(title="Analysis Summary")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Queries Analyzed", str(data.get("total_queries_analyzed", 0)))

            aio = data.get("aio_analysis", {})
            table.add_row("Queries with AIO", str(aio.get("queries_with_aio", 0)))
            table.add_row("Citation Rate", f"{aio.get('citation_rate', 0):.1f}%")

            traffic = data.get("traffic_changes", {})
            table.add_row("Significant Drops", str(traffic.get("significant_drops", 0)))

            console.print(table)

            # Recommendations
            if result.recommendations:
                console.print(f"\n[yellow]Top Recommendations ({len(result.recommendations)}):[/yellow]")
                for i, rec in enumerate(result.recommendations[:10], 1):
                    console.print(f"  {i}. [{rec.priority.value}] {rec.title}")

            # Alerts
            if result.alerts:
                console.print(f"\n[red]Alerts ({len(result.alerts)}):[/red]")
                for alert in result.alerts[:5]:
                    console.print(f"  - [{alert.severity.value}] {alert.title}")

        else:
            data = result.data

            table = Table(title="AIO Check Results")
            table.add_column("Query", style="cyan")
            table.add_column("Has AIO", style="yellow")
            table.add_column("Cited", style="green")

            for check in data.get("results", []):
                table.add_row(
                    check.get("query", ""),
                    "Yes" if check.get("has_aio") else "No",
                    "Yes" if check.get("client_cited") else "No",
                )

            console.print(table)
    else:
        console.print(f"[red]Analysis failed: {result.data.get('error')}[/red]")


@app.command()
def test_page(
    url: str = typer.Argument(..., help="URL to test"),
):
    """Test a page for agent-friendliness."""
    asyncio.run(_test_page(url))


async def _test_page(url: str):
    from src.agents.agent_tester import AgentTesterAgent
    from src.agents.base import AgentContext
    from src.integrations.azure_openai import AzureOpenAIClient
    from src.models.agents import AgentTask

    settings = get_settings()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Testing page...", total=None)

        openai_client = AzureOpenAIClient(settings.azure)

        context = AgentContext(
            settings=settings,
            openai_client=openai_client,
        )

        agent = AgentTesterAgent(context)

        agent_task = AgentTask(
            agent_type=agent.agent_type,
            task_type="interpret_page",
            parameters={"url": url},
        )

        result = await agent.run(agent_task)

    if result.success:
        analysis = result.data.get("page_analysis", {})
        llm = result.data.get("llm_analysis", {})

        console.print("\n[green]Page Analysis Complete![/green]\n")

        # Scores
        table = Table(title=f"Analysis: {url}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Title", analysis.get("title", "N/A"))
        table.add_row("Agent-Friendliness Score", f"{analysis.get('agent_friendliness_score', 0)}/100")
        table.add_row("Agent Can Complete Action", "Yes" if analysis.get("agent_actionable") else "No")
        table.add_row("Schema Types", ", ".join(analysis.get("schema_types", [])) or "None")

        console.print(table)

        # Summary
        if llm.get("summary"):
            console.print(f"\n[yellow]AI Agent Summary:[/yellow]")
            console.print(f"  {llm['summary']}")

        # Recommendations
        if result.recommendations:
            console.print(f"\n[yellow]Recommendations:[/yellow]")
            for rec in result.recommendations:
                console.print(f"  - {rec.title}")
    else:
        console.print(f"[red]Test failed: {result.data.get('error')}[/red]")


@app.command()
def config():
    """Show current configuration."""
    settings = get_settings()

    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Status", style="yellow")

    # Check each config
    configs = [
        ("Environment", settings.app_env, ""),
        ("Azure OpenAI", settings.azure.openai_endpoint[:30] + "..." if settings.azure.openai_endpoint else "Not set", "OK" if settings.azure.openai_endpoint else "Missing"),
        ("GSC Property", settings.google.gsc_property_url or "Not set", "OK" if settings.google.gsc_property_url else "Optional"),
        ("SERP Provider", settings.serp.provider, "OK"),
        ("Teams Webhook", "Configured" if settings.alerts.teams_webhook_url.get_secret_value() else "Not set", "OK" if settings.alerts.teams_webhook_url.get_secret_value() else "Optional"),
        ("Optimizely", "Configured" if settings.optimizely.api_key.get_secret_value() else "Not set", "OK" if settings.optimizely.api_key.get_secret_value() else "Optional"),
    ]

    for name, value, status in configs:
        table.add_row(name, str(value), status)

    console.print(table)


if __name__ == "__main__":
    app()
