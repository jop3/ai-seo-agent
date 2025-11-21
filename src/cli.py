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
def ui(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8080, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
):
    """Start the web chat UI for local development."""
    import uvicorn

    console.print(f"[green]Starting SEO Agent Chat UI on http://{host}:{port}[/green]")
    console.print("[dim]Open your browser to chat with the agents[/dim]")

    uvicorn.run(
        "src.ui.chat:app",
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


# =============================================================================
# AGENT COMMANDS - Conversational interface to agents
# =============================================================================

@app.command()
def chat(
    agent: str = typer.Option("seo-analyst", "--agent", "-a", help="Agent to chat with"),
    task: str = typer.Argument(None, help="Initial task/question"),
):
    """
    Chat with an AI agent.

    Available agents: seo-analyst, agent-tester, monitoring-agent, optimizer

    Examples:
        seo-agent chat "Analyze our top queries for AIO impact"
        seo-agent chat -a optimizer "Generate FAQ for ibuprofen side effects"
    """
    asyncio.run(_chat(agent, task))


async def _chat(agent_name: str, initial_task: str | None):
    from src.azure_agents.definitions import ALL_AGENTS
    from src.azure_agents.runner import LocalAgentRunner, ConversationalAgent

    # Find agent
    agent = next((a for a in ALL_AGENTS if a.name == agent_name), None)
    if not agent:
        console.print(f"[red]Unknown agent: {agent_name}[/red]")
        console.print("Available agents:")
        for a in ALL_AGENTS:
            console.print(f"  - {a.name}: {a.description}")
        return

    console.print(f"\n[green]Starting chat with {agent.name}[/green]")
    console.print(f"[dim]{agent.description}[/dim]")
    console.print("[dim]Type 'exit' to quit, 'clear' to reset history[/dim]\n")

    # Create conversational agent
    runner = LocalAgentRunner()
    conv_agent = ConversationalAgent(agent, runner)

    # Handle initial task
    if initial_task:
        await _process_chat_message(conv_agent, initial_task)

    # Interactive loop
    while True:
        try:
            user_input = console.input("[bold cyan]You:[/bold cyan] ")

            if user_input.lower() == "exit":
                console.print("[yellow]Goodbye![/yellow]")
                break
            elif user_input.lower() == "clear":
                conv_agent.clear_history()
                console.print("[dim]History cleared[/dim]")
                continue
            elif not user_input.strip():
                continue

            await _process_chat_message(conv_agent, user_input)

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break


async def _process_chat_message(conv_agent, message: str):
    from rich.markdown import Markdown

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Thinking...", total=None)

        response = await conv_agent.chat(message)

    if response.success:
        console.print(f"\n[bold green]{conv_agent.agent.name}:[/bold green]")
        console.print(Markdown(response.message))

        if response.tool_calls_made:
            console.print(f"\n[dim]Tools used: {', '.join(response.tool_calls_made)}[/dim]")
        console.print()
    else:
        console.print(f"[red]Error: {response.message}[/red]\n")


@app.command()
def agents():
    """List available agents and their capabilities."""
    from src.azure_agents.definitions import ALL_AGENTS

    for agent in ALL_AGENTS:
        console.print(f"\n[bold cyan]{agent.name}[/bold cyan]")
        console.print(f"  {agent.description}")
        console.print(f"  [dim]Tools:[/dim]")
        for tool in agent.tools:
            console.print(f"    - {tool.name}: {tool.description[:60]}...")


@app.command()
def run_task(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent to use"),
    task: str = typer.Argument(..., help="Task to execute"),
    output_file: str = typer.Option(None, "--output", "-o", help="Save result to file"),
):
    """
    Run a single task with an agent (non-interactive).

    Example:
        seo-agent run-task -a seo-analyst "Check AIO status for these queries: ibuprofen, paracetamol"
    """
    asyncio.run(_run_task(agent, task, output_file))


async def _run_task(agent_name: str, task: str, output_file: str | None):
    import json
    from src.azure_agents.runner import run_agent_task

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        prog_task = progress.add_task(f"Running {agent_name}...", total=None)

        response = await run_agent_task(agent_name, task)

    if response.success:
        console.print(f"\n[green]Task completed successfully[/green]")
        console.print(f"\n{response.message}")

        if output_file:
            result = {
                "success": response.success,
                "message": response.message,
                "data": response.data,
                "tool_calls": response.tool_calls_made,
                "execution_time_ms": response.execution_time_ms,
            }
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            console.print(f"\n[dim]Result saved to {output_file}[/dim]")
    else:
        console.print(f"[red]Task failed: {response.message}[/red]")


# =============================================================================
# AZURE DEPLOYMENT COMMANDS
# =============================================================================

@app.command()
def deploy_agents(
    connection_string: str = typer.Option(..., "--connection-string", "-c", help="Azure AI Project connection string"),
):
    """
    Deploy all agents to Azure AI Agent Service.

    This registers the agent definitions with Azure so they can be
    run on Azure infrastructure.
    """
    asyncio.run(_deploy_agents(connection_string))


async def _deploy_agents(connection_string: str):
    from src.azure_agents.client import AzureAgentClient
    from src.azure_agents.definitions import ALL_AGENTS

    console.print("[yellow]Deploying agents to Azure AI Agent Service...[/yellow]\n")

    try:
        client = AzureAgentClient(project_connection_string=connection_string)

        for agent in ALL_AGENTS:
            with console.status(f"Deploying {agent.name}..."):
                try:
                    info = await client.deploy_agent(agent)
                    console.print(f"[green]  {agent.name}: deployed (ID: {info.agent_id})[/green]")
                except Exception as e:
                    console.print(f"[red]  {agent.name}: failed - {e}[/red]")

        console.print("\n[green]Deployment complete![/green]")

    except ImportError:
        console.print("[red]Azure AI Projects SDK not installed.[/red]")
        console.print("Install with: pip install azure-ai-projects azure-identity")
    except Exception as e:
        console.print(f"[red]Deployment failed: {e}[/red]")


@app.command()
def list_azure_agents(
    connection_string: str = typer.Option(..., "--connection-string", "-c", help="Azure AI Project connection string"),
):
    """List agents deployed to Azure AI Agent Service."""
    asyncio.run(_list_azure_agents(connection_string))


async def _list_azure_agents(connection_string: str):
    from src.azure_agents.client import AzureAgentClient

    try:
        client = AzureAgentClient(project_connection_string=connection_string)
        agents = await client.list_agents()

        if not agents:
            console.print("[yellow]No agents deployed[/yellow]")
            return

        table = Table(title="Deployed Azure Agents")
        table.add_column("Name", style="cyan")
        table.add_column("ID", style="dim")
        table.add_column("Model", style="green")
        table.add_column("Status", style="yellow")

        for agent in agents:
            table.add_row(agent.name, agent.agent_id[:20] + "...", agent.model, agent.status)

        console.print(table)

    except ImportError:
        console.print("[red]Azure AI Projects SDK not installed.[/red]")
    except Exception as e:
        console.print(f"[red]Failed to list agents: {e}[/red]")


if __name__ == "__main__":
    app()
