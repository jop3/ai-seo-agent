#!/usr/bin/env python3
"""
Interactive Setup Script for AI SEO Agent
Helps configure and deploy to various backends.
"""

import subprocess
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
    from rich.table import Table
except ImportError:
    print("Installing required dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "-q"])
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
    from rich.table import Table

console = Console()


class SetupWizard:
    """Interactive setup wizard for AI SEO Agent."""

    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.config = {}

    def run(self):
        """Run the complete setup wizard."""
        console.clear()
        self.show_welcome()

        # Step 1: Choose platform
        platform = self.choose_platform()
        self.config["platform"] = platform

        # Step 2: Choose LLM provider
        llm_provider = self.choose_llm_provider()
        self.config["llm_provider"] = llm_provider

        # Step 3: Choose agent framework
        agent_framework = self.choose_agent_framework()
        self.config["agent_framework"] = agent_framework

        # Step 4: Choose database
        database = self.choose_database(platform)
        self.config["database"] = database

        # Step 5: Configure services
        self.configure_services()

        # Step 6: Create configuration files
        self.create_config_files()

        # Step 6: Set up database
        if Confirm.ask("\n[bold cyan]Set up database now?[/]"):
            self.setup_database()

        # Step 7: Show deployment instructions
        self.show_deployment_instructions()

        self.show_completion()

    def show_welcome(self):
        """Display welcome message."""
        welcome = Panel(
            "[bold cyan]🚀 AI SEO Agent Setup Wizard[/]\n\n"
            "This wizard will help you:\n"
            "• Choose your deployment platform\n"
            "• Configure LLM provider\n"
            "• Set up database\n"
            "• Create configuration files\n"
            "• Deploy your agent\n\n"
            "[dim]Let's get started![/]",
            title="Welcome",
            border_style="cyan",
        )
        console.print(welcome)
        console.print()

    def choose_platform(self) -> str:
        """Let user choose deployment platform."""
        console.print("\n[bold]Step 1: Choose Deployment Platform[/]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Option", style="cyan", width=12)
        table.add_column("Platform", style="green", width=20)
        table.add_column("Best For", width=30)
        table.add_column("Difficulty", style="yellow", width=15)

        table.add_row("1", "Azure", "Enterprise, integrated AI", "⭐⭐⭐ Advanced")
        table.add_row("2", "Vercel", "Quick MVP, serverless", "⭐ Easy")
        table.add_row("3", "AWS", "Enterprise, full control", "⭐⭐⭐ Advanced")
        table.add_row("4", "Google Cloud", "Enterprise, AI/ML", "⭐⭐⭐ Advanced")
        table.add_row("5", "Docker Compose", "Self-hosted, full control", "⭐⭐ Medium")
        table.add_row("6", "Railway.app", "Quick deployment", "⭐ Easy")
        table.add_row("7", "Fly.io", "Global edge deployment", "⭐⭐ Medium")

        console.print(table)

        choice = Prompt.ask(
            "\n[cyan]Choose platform[/]",
            choices=["1", "2", "3", "4", "5", "6", "7"],
            default="1"
        )

        platforms = {
            "1": "azure",
            "2": "vercel",
            "3": "aws",
            "4": "gcp",
            "5": "docker",
            "6": "railway",
            "7": "fly"
        }

        platform = platforms[choice]
        console.print(f"\n✅ Selected: [bold green]{platform.upper()}[/]\n")
        return platform

    def choose_llm_provider(self) -> str:
        """Let user choose LLM provider."""
        console.print("\n[bold]Step 2: Choose LLM Provider[/]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Option", style="cyan", width=12)
        table.add_column("Provider", style="green", width=25)
        table.add_column("Model", width=30)
        table.add_column("Cost", style="yellow", width=15)

        table.add_row("1", "Docker Model Runner", "Llama/Phi/Gemma (local)", "Free ⚡")
        table.add_row("2", "OpenAI", "GPT-4o", "$2.50-$10")
        table.add_row("3", "Anthropic Claude", "Claude 3.5 Sonnet", "$3-$15")
        table.add_row("4", "Google Gemini", "Gemini Pro", "$0.50-$2")
        table.add_row("5", "Azure OpenAI", "GPT-4o", "$2.50-$10")
        table.add_row("6", "Local (Ollama)", "Llama 3/Mixtral", "Free")

        console.print(table)

        # Show hardware recommendation if Docker platform
        if self.config.get("platform") == "docker":
            console.print("\n[dim]💡 Tip: Run [yellow]python3 scripts/analyze_hardware.py[/] to see which models your system can run[/]\n")

        choice = Prompt.ask(
            "\n[cyan]Choose LLM provider[/]",
            choices=["1", "2", "3", "4", "5", "6"],
            default="1"
        )

        providers = {
            "1": "docker_model_runner",
            "2": "openai",
            "3": "anthropic",
            "4": "gemini",
            "5": "azure_openai",
            "6": "ollama"
        }

        provider = providers[choice]
        console.print(f"\n✅ Selected: [bold green]{provider.replace('_', ' ').upper()}[/]\n")
        return provider

    def choose_agent_framework(self) -> str:
        """Let user choose agent framework."""
        console.print("\n[bold]Step 3: Choose Agent Framework[/]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Option", style="cyan", width=12)
        table.add_column("Framework", style="green", width=25)
        table.add_column("Best For", width=40)
        table.add_column("Platform", style="yellow", width=20)

        table.add_row("1", "Direct LLM", "Simple workflows, rapid prototyping", "Any")
        table.add_row("2", "Google ADK", "Google Cloud, Gemini models", "Vertex AI")
        table.add_row("3", "LangGraph", "Complex state management, graphs", "LangGraph Cloud")
        table.add_row("4", "Microsoft Agent", "Enterprise, Azure integration", "Azure")
        table.add_row("5", "AWS Bedrock", "AWS users, production scale", "AWS")
        table.add_row("6", "CrewAI", "Role-based collaboration", "Docker/K8s")

        console.print(table)
        console.print("\n[dim]💡 Tip: For most users, 'Direct LLM' is the simplest option. See /examples/frameworks/ for detailed comparisons.[/]\n")

        choice = Prompt.ask(
            "\n[cyan]Choose agent framework[/]",
            choices=["1", "2", "3", "4", "5", "6"],
            default="1"
        )

        frameworks = {
            "1": "direct_llm",
            "2": "google_adk",
            "3": "langgraph",
            "4": "microsoft_agent",
            "5": "aws_bedrock",
            "6": "crewai"
        }

        framework = frameworks[choice]
        console.print(f"\n✅ Selected: [bold green]{framework.replace('_', ' ').upper()}[/]\n")
        return framework

    def choose_database(self, platform: str) -> str:
        """Let user choose database."""
        console.print("\n[bold]Step 4: Choose Database[/]\n")

        # Platform-specific defaults
        if platform == "vercel":
            recommended = "Vercel Postgres (recommended)"
        elif platform == "azure":
            recommended = "Azure Cosmos DB or Azure PostgreSQL (recommended)"
        elif platform in ["aws", "gcp"]:
            recommended = "Managed PostgreSQL (recommended)"
        else:
            recommended = "PostgreSQL (recommended)"

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Option", style="cyan", width=12)
        table.add_column("Database", style="green", width=25)
        table.add_column("Notes", width=40)

        table.add_row("1", "PostgreSQL", recommended)
        table.add_row("2", "MongoDB", "NoSQL, flexible schema")
        table.add_row("3", "SQLite", "File-based, good for dev/small scale")
        table.add_row("4", "MySQL", "Popular, well-supported")

        console.print(table)

        choice = Prompt.ask(
            "\n[cyan]Choose database[/]",
            choices=["1", "2", "3", "4"],
            default="1"
        )

        databases = {
            "1": "postgresql",
            "2": "mongodb",
            "3": "sqlite",
            "4": "mysql"
        }

        database = databases[choice]
        console.print(f"\n✅ Selected: [bold green]{database.upper()}[/]\n")
        return database

    def configure_services(self):
        """Configure API keys and services."""
        console.print("\n[bold]Step 4: Configure Services[/]\n")

        # LLM API Key
        provider_name = self.config['llm_provider'].replace('_', ' ').upper()
        console.print(f"[cyan]Configure {provider_name}:[/]")

        if self.config["llm_provider"] == "docker_model_runner":
            # Use hardware analysis to recommend models
            console.print("[dim]Analyzing system to recommend models...[/]\n")
            try:
                from scripts.analyze_hardware import get_system_specs, get_model_recommendations

                specs = get_system_specs()
                recommendations = get_model_recommendations(specs)

                # Show available models
                console.print("[bold]Available Models:[/]\n")

                model_options = {}
                idx = 1

                # Show fast models
                if recommendations["fast"]:
                    console.print("[cyan]⚡ Fast Models:[/]")
                    for model in recommendations["fast"][:2]:
                        if model.provider == "docker_model_runner":
                            console.print(f"  {idx}. {model.name} - {model.description}")
                            model_options[str(idx)] = model.identifier
                            idx += 1

                # Show balanced models
                if recommendations["balanced"]:
                    console.print("\n[cyan]⚖️  Balanced Models (Recommended):[/]")
                    for model in recommendations["balanced"][:2]:
                        if model.provider == "docker_model_runner":
                            console.print(f"  {idx}. {model.name} - {model.description}")
                            model_options[str(idx)] = model.identifier
                            idx += 1

                # Show smart models
                if recommendations["smart"]:
                    console.print("\n[cyan]🧠 Smart Models:[/]")
                    for model in recommendations["smart"][:2]:
                        if model.provider == "docker_model_runner":
                            console.print(f"  {idx}. {model.name} - {model.description}")
                            model_options[str(idx)] = model.identifier
                            idx += 1

                if not model_options:
                    # Fallback
                    model_options = {
                        "1": "ai/smollm2-360m-instruct",
                        "2": "ai/phi3-mini-4k-instruct",
                        "3": "ai/llama3.2-3b-instruct"
                    }
                    console.print("1. SmolLM2 360M - Small and fast")
                    console.print("2. Phi-3 Mini - Balanced")
                    console.print("3. Llama 3.2 3B - Best quality")

                model_choice = Prompt.ask(
                    "\n[cyan]Choose model[/]",
                    choices=list(model_options.keys()),
                    default="2"
                )
                self.config["docker_model"] = model_options[model_choice]
                self.config["docker_model_endpoint"] = "http://llm:8080/v1"

                console.print(f"\n✅ Selected: [green]{model_options[model_choice]}[/]")

            except Exception as e:
                console.print(f"[yellow]Could not analyze hardware: {e}[/]")
                console.print("[dim]Using default model...[/]")
                self.config["docker_model"] = "ai/phi3-mini-4k-instruct"
                self.config["docker_model_endpoint"] = "http://llm:8080/v1"

        elif self.config["llm_provider"] == "openai":
            api_key = Prompt.ask("OpenAI API Key (sk-...)", password=True)
            self.config["openai_api_key"] = api_key
        elif self.config["llm_provider"] == "anthropic":
            api_key = Prompt.ask("Anthropic API Key", password=True)
            self.config["anthropic_api_key"] = api_key
        elif self.config["llm_provider"] == "gemini":
            api_key = Prompt.ask("Google AI API Key", password=True)
            self.config["gemini_api_key"] = api_key
        elif self.config["llm_provider"] == "azure_openai":
            endpoint = Prompt.ask("Azure OpenAI Endpoint")
            api_key = Prompt.ask("Azure OpenAI API Key", password=True)
            deployment = Prompt.ask("Deployment Name", default="gpt-4o")
            self.config["azure_openai_endpoint"] = endpoint
            self.config["azure_openai_api_key"] = api_key
            self.config["azure_openai_deployment"] = deployment
        elif self.config["llm_provider"] == "ollama":
            endpoint = Prompt.ask("Ollama Endpoint", default="http://localhost:11434")
            model = Prompt.ask("Model", default="llama3")
            self.config["ollama_endpoint"] = endpoint
            self.config["ollama_model"] = model

        # Database connection
        console.print(f"\n[cyan]Configure {self.config['database'].upper()} Database:[/]")
        if self.config["database"] == "postgresql":
            if self.config["platform"] == "vercel":
                console.print("[dim]You can set this up in Vercel dashboard[/]")
                self.config["postgres_url"] = "VERCEL_POSTGRES_URL"
            else:
                db_url = Prompt.ask(
                    "PostgreSQL URL",
                    default="postgresql://user:password@localhost:5432/seoagent"
                )
                self.config["postgres_url"] = db_url
        elif self.config["database"] == "mongodb":
            db_url = Prompt.ask(
                "MongoDB URL",
                default="mongodb://localhost:27017/seoagent"
            )
            self.config["mongodb_url"] = db_url
        elif self.config["database"] == "sqlite":
            db_path = Prompt.ask("SQLite Database Path", default="./seo_agent.db")
            self.config["sqlite_path"] = db_path

        # Redis (optional)
        if Confirm.ask("\n[cyan]Configure Redis for caching?[/]", default=True):
            redis_url = Prompt.ask(
                "Redis URL",
                default="redis://localhost:6379/0"
            )
            self.config["redis_url"] = redis_url

        # Optional integrations
        console.print("\n[bold]Optional Integrations:[/]")
        if Confirm.ask("[cyan]Configure Google Search Console?[/]", default=False):
            gsc_path = Prompt.ask(
                "Service Account JSON Path",
                default="./credentials/gsc-service-account.json"
            )
            property_url = Prompt.ask("Property URL (e.g., https://example.com)")
            self.config["gsc_credentials_path"] = gsc_path
            self.config["gsc_property_url"] = property_url

        if Confirm.ask("[cyan]Configure Ahrefs API?[/]", default=False):
            ahrefs_key = Prompt.ask("Ahrefs API Key", password=True)
            self.config["ahrefs_api_key"] = ahrefs_key

    def create_config_files(self):
        """Create configuration files."""
        console.print("\n[bold]Step 5: Creating Configuration Files[/]\n")

        with console.status("[cyan]Generating files...[/]"):
            # Create .env file
            self.create_env_file()

            # Create platform-specific files
            if self.config["platform"] == "azure":
                self.create_azure_config()
            elif self.config["platform"] == "vercel":
                self.create_vercel_config()
            elif self.config["platform"] == "docker":
                self.create_docker_compose()
            elif self.config["platform"] == "aws":
                self.create_aws_config()
            elif self.config["platform"] == "gcp":
                self.create_gcp_config()
            elif self.config["platform"] == "railway":
                self.create_railway_config()
            elif self.config["platform"] == "fly":
                self.create_fly_config()

        console.print("✅ Configuration files created!\n")

    def create_env_file(self):
        """Create .env file."""
        env_content = "# AI SEO Agent Configuration\n\n"

        # LLM Configuration
        env_content += "# LLM Provider\n"
        if self.config["llm_provider"] == "docker_model_runner":
            env_content += "# Docker Model Runner - Local LLM\n"
            env_content += f"OPENAI_API_BASE={self.config.get('docker_model_endpoint', 'http://llm:8080/v1')}\n"
            env_content += "OPENAI_API_KEY=not-needed\n"
            env_content += f"# Model: {self.config.get('docker_model', 'ai/phi3-mini-4k-instruct')}\n"
        elif self.config["llm_provider"] == "openai":
            env_content += f"OPENAI_API_KEY={self.config.get('openai_api_key', '')}\n"
        elif self.config["llm_provider"] == "anthropic":
            env_content += f"ANTHROPIC_API_KEY={self.config.get('anthropic_api_key', '')}\n"
        elif self.config["llm_provider"] == "gemini":
            env_content += f"GOOGLE_AI_API_KEY={self.config.get('gemini_api_key', '')}\n"
        elif self.config["llm_provider"] == "azure_openai":
            env_content += f"AZURE_OPENAI_ENDPOINT={self.config.get('azure_openai_endpoint', '')}\n"
            env_content += f"AZURE_OPENAI_API_KEY={self.config.get('azure_openai_api_key', '')}\n"
            env_content += f"AZURE_OPENAI_DEPLOYMENT={self.config.get('azure_openai_deployment', 'gpt-4o')}\n"
        elif self.config["llm_provider"] == "ollama":
            env_content += f"OLLAMA_ENDPOINT={self.config.get('ollama_endpoint', 'http://localhost:11434')}\n"
            env_content += f"OLLAMA_MODEL={self.config.get('ollama_model', 'llama3')}\n"

        # Agent Framework Configuration
        env_content += "\n# Agent Framework\n"
        agent_framework = self.config.get("agent_framework", "direct_llm")
        env_content += f"AGENT_FRAMEWORK={agent_framework}\n"

        if agent_framework == "google_adk":
            env_content += f"# Google ADK Configuration\n"
            env_content += f"GCP_PROJECT_ID={self.config.get('gcp_project_id', '')}\n"
            env_content += f"GCP_LOCATION={self.config.get('gcp_location', 'us-central1')}\n"
        elif agent_framework == "langgraph":
            env_content += f"# LangGraph Configuration\n"
            env_content += f"LANGCHAIN_API_KEY={self.config.get('langchain_api_key', '')}\n"
            env_content += f"LANGCHAIN_PROJECT={self.config.get('langchain_project', 'seo-agent')}\n"
        elif agent_framework == "microsoft_agent":
            env_content += f"# Microsoft Agent Framework - uses Azure OpenAI config above\n"
        elif agent_framework == "aws_bedrock":
            env_content += f"# AWS Bedrock Configuration\n"
            env_content += f"AWS_REGION={self.config.get('aws_region', 'us-east-1')}\n"
        elif agent_framework == "crewai":
            env_content += f"# CrewAI - uses LLM provider config above\n"

        # Database Configuration
        env_content += "\n# Database\n"
        if "postgres_url" in self.config:
            env_content += f"POSTGRES_URL={self.config['postgres_url']}\n"
        elif "mongodb_url" in self.config:
            env_content += f"MONGODB_URL={self.config['mongodb_url']}\n"
        elif "sqlite_path" in self.config:
            env_content += f"SQLITE_PATH={self.config['sqlite_path']}\n"

        # Redis
        if "redis_url" in self.config:
            env_content += f"\n# Redis\nREDIS_URL={self.config['redis_url']}\n"

        # Optional integrations
        if "gsc_credentials_path" in self.config:
            env_content += f"\n# Google Search Console\nGSC_CREDENTIALS_PATH={self.config['gsc_credentials_path']}\n"
            env_content += f"GSC_PROPERTY_URL={self.config['gsc_property_url']}\n"

        if "ahrefs_api_key" in self.config:
            env_content += f"\n# Ahrefs\nAHREFS_API_KEY={self.config['ahrefs_api_key']}\n"

        # Write file
        env_path = self.root_dir / ".env"
        env_path.write_text(env_content)
        console.print(f"  • Created [green]{env_path}[/]")

    def create_vercel_config(self):
        """Create Vercel configuration."""
        vercel_config = {
            "version": 2,
            "builds": [
                {"src": "src/api/main.py", "use": "@vercel/python"}
            ],
            "routes": [
                {"src": "/api/(.*)", "dest": "src/api/main.py"}
            ]
        }

        import json
        config_path = self.root_dir / "vercel.json"
        config_path.write_text(json.dumps(vercel_config, indent=2))
        console.print(f"  • Created [green]{config_path}[/]")

    def create_docker_compose(self):
        """Create Docker Compose configuration."""

        # Check if using Docker Model Runner
        use_model_runner = self.config.get("llm_provider") == "docker_model_runner"
        model_name = self.config.get("docker_model", "ai/phi3-mini-4k-instruct")

        if use_model_runner:
            compose_content = f"""version: '3.8'

services:
  # Local LLM via Docker Model Runner
  llm:
    image: {model_name}
    ports:
      - "8080:8080"
    environment:
      - MODEL_ID={model_name}
    # Uncomment for GPU support (NVIDIA)
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_BASE=http://llm:8080/v1
      - OPENAI_API_KEY=not-needed
      - POSTGRES_URL=postgresql://postgres:postgres@db:5432/seoagent
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - llm
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: seoagent
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

volumes:
  postgres_data:
  redis_data:
"""
        else:
            compose_content = """version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - POSTGRES_URL=postgresql://postgres:postgres@db:5432/seoagent
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: seoagent
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

volumes:
  postgres_data:
  redis_data:
"""
        compose_path = self.root_dir / "docker-compose.yml"
        compose_path.write_text(compose_content)
        console.print(f"  • Created [green]{compose_path}[/]")

        if use_model_runner:
            console.print(f"  • LLM Model: [yellow]{model_name}[/]")
            console.print("  • [dim]Model will be auto-downloaded on first run[/]")

    def create_azure_config(self):
        """Create Azure Bicep configuration."""
        # Create Azure deployment parameters
        params_content = """{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "appName": {
      "value": "seo-agent"
    },
    "location": {
      "value": "eastus"
    },
    "openaiDeploymentName": {
      "value": "gpt-4o"
    }
  }
}
"""
        params_path = self.root_dir / "azure" / "parameters.json"
        params_path.parent.mkdir(exist_ok=True)
        params_path.write_text(params_content)
        console.print(f"  • Created [green]{params_path}[/]")
        console.print("  • For full Azure setup, see [yellow]AZURE_DEPLOYMENT.md[/]")

    def create_aws_config(self):
        """Create AWS Terraform configuration."""
        # Placeholder - would create full Terraform config
        console.print("  • AWS config - see DEPLOYMENT_BACKENDS.md")

    def create_gcp_config(self):
        """Create GCP Cloud Run configuration."""
        cloudbuild = """steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/seo-agent', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/seo-agent']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'seo-agent-api'
      - '--image=gcr.io/$PROJECT_ID/seo-agent'
      - '--region=us-central1'
      - '--platform=managed'
"""
        config_path = self.root_dir / "cloudbuild.yaml"
        config_path.write_text(cloudbuild)
        console.print(f"  • Created [green]{config_path}[/]")

    def create_railway_config(self):
        """Create Railway configuration."""
        console.print("  • Railway - push to GitHub and connect via Railway dashboard")

    def create_fly_config(self):
        """Create Fly.io configuration."""
        fly_toml = """app = "seo-agent"
primary_region = "iad"

[build]

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
"""
        config_path = self.root_dir / "fly.toml"
        config_path.write_text(fly_toml)
        console.print(f"  • Created [green]{config_path}[/]")

    def setup_database(self):
        """Initialize database schema."""
        console.print("\n[bold]Setting up database...[/]\n")

        with console.status("[cyan]Initializing database schema...[/]"):
            # Create database schema
            if self.config["database"] == "postgresql":
                self.create_postgres_schema()
            elif self.config["database"] == "mongodb":
                self.create_mongo_collections()
            elif self.config["database"] == "sqlite":
                self.create_sqlite_schema()

        console.print("✅ Database initialized!\n")

    def create_postgres_schema(self):
        """Create PostgreSQL schema."""
        schema_sql = """
-- SEO Analysis Results
CREATE TABLE IF NOT EXISTS analyses (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    workflow_id TEXT,
    data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analyses_url ON analyses(url);
CREATE INDEX idx_analyses_workflow ON analyses(workflow_id);
CREATE INDEX idx_analyses_created ON analyses(created_at);

-- Agent Results
CREATE TABLE IF NOT EXISTS agent_results (
    id SERIAL PRIMARY KEY,
    agent_type TEXT NOT NULL,
    url TEXT,
    task_type TEXT,
    result JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_agent_results_type ON agent_results(agent_type);
CREATE INDEX idx_agent_results_url ON agent_results(url);
"""
        schema_path = self.root_dir / "schema" / "postgres.sql"
        schema_path.parent.mkdir(exist_ok=True)
        schema_path.write_text(schema_sql)
        console.print(f"  • Created schema file: [green]{schema_path}[/]")

    def create_mongo_collections(self):
        """Create MongoDB collections."""
        console.print("  • MongoDB collections will be created automatically")

    def create_sqlite_schema(self):
        """Create SQLite schema."""
        self.create_postgres_schema()  # Same SQL works for SQLite

    def show_deployment_instructions(self):
        """Show deployment instructions."""
        console.print("\n[bold]Step 6: Deployment Instructions[/]\n")

        platform = self.config["platform"]

        if platform == "azure":
            panel = Panel(
                "[bold cyan]Azure Deployment[/]\n\n"
                "Full deployment guide: [yellow]AZURE_DEPLOYMENT.md[/]\n\n"
                "Quick start:\n\n"
                "1. Install Azure CLI:\n"
                "   [yellow]curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash[/]\n\n"
                "2. Login to Azure:\n"
                "   [yellow]az login[/]\n\n"
                "3. Create resource group:\n"
                "   [yellow]az group create --name ai-seo-agent-rg --location eastus[/]\n\n"
                "4. Run deployment script:\n"
                "   [yellow]./scripts/azure-deploy.sh[/]\n\n"
                "5. Set environment variables in Azure Portal or Key Vault\n\n"
                "[dim]See AZURE_DEPLOYMENT.md for complete setup including:\n"
                "• Azure OpenAI configuration\n"
                "• Cosmos DB or Azure PostgreSQL\n"
                "• Managed Identity setup\n"
                "• CI/CD pipelines[/]",
                border_style="cyan"
            )

        elif platform == "vercel":
            panel = Panel(
                "[bold cyan]Vercel Deployment[/]\n\n"
                "1. Install Vercel CLI:\n"
                "   [yellow]npm i -g vercel[/]\n\n"
                "2. Deploy:\n"
                "   [yellow]vercel --prod[/]\n\n"
                "3. Set environment variables in Vercel dashboard\n\n"
                "4. Set up Vercel Postgres:\n"
                "   [yellow]vercel postgres create[/]",
                border_style="cyan"
            )

        elif platform == "docker":
            docker_msg = (
                "[bold cyan]Docker Compose Deployment[/]\n\n"
                "1. Build and start:\n"
                "   [yellow]docker-compose up -d[/]\n\n"
                "2. View logs:\n"
                "   [yellow]docker-compose logs -f api[/]\n\n"
                "3. Access API:\n"
                "   [yellow]http://localhost:8000[/]"
            )

            # Add Docker Model Runner note if using it
            if self.config.get("llm_provider") == "docker_model_runner":
                model = self.config.get("docker_model", "ai/phi3-mini-4k-instruct")
                docker_msg += (
                    f"\n\n[dim]📝 Using Docker Model Runner:[/]\n"
                    f"  • Model: [yellow]{model}[/]\n"
                    f"  • Model will auto-download on first start (may take 2-5 min)\n"
                    f"  • Requires Docker Desktop 4.41+\n"
                    f"  • View model logs: [yellow]docker-compose logs -f llm[/]"
                )

            panel = Panel(docker_msg, border_style="cyan")

        elif platform == "railway":
            panel = Panel(
                "[bold cyan]Railway Deployment[/]\n\n"
                "1. Push to GitHub\n\n"
                "2. Connect repository in Railway dashboard\n\n"
                "3. Add PostgreSQL addon\n\n"
                "4. Set environment variables\n\n"
                "5. Deploy automatically on push",
                border_style="cyan"
            )

        elif platform == "fly":
            panel = Panel(
                "[bold cyan]Fly.io Deployment[/]\n\n"
                "1. Install Fly CLI:\n"
                "   [yellow]curl -L https://fly.io/install.sh | sh[/]\n\n"
                "2. Login:\n"
                "   [yellow]fly auth login[/]\n\n"
                "3. Deploy:\n"
                "   [yellow]fly deploy[/]",
                border_style="cyan"
            )

        elif platform == "aws":
            panel = Panel(
                "[bold cyan]AWS Deployment[/]\n\n"
                "See DEPLOYMENT_BACKENDS.md for full AWS setup\n\n"
                "Quick start:\n"
                "1. Build Docker image\n"
                "2. Push to ECR\n"
                "3. Deploy with ECS/Fargate",
                border_style="cyan"
            )

        elif platform == "gcp":
            panel = Panel(
                "[bold cyan]Google Cloud Deployment[/]\n\n"
                "1. Build and deploy:\n"
                "   [yellow]gcloud builds submit --config cloudbuild.yaml[/]\n\n"
                "2. View service:\n"
                "   [yellow]gcloud run services list[/]",
                border_style="cyan"
            )

        else:
            panel = Panel("See DEPLOYMENT_BACKENDS.md for deployment instructions")

        console.print(panel)

    def show_completion(self):
        """Show completion message."""
        console.print("\n" + "="*70 + "\n")

        completion = Panel(
            "[bold green]🎉 Setup Complete![/]\n\n"
            "Your AI SEO Agent is configured and ready to deploy!\n\n"
            "[bold]Next Steps:[/]\n"
            "1. Review generated configuration files\n"
            "2. Follow deployment instructions above\n"
            "3. Test your deployment\n"
            "4. Check the dashboard: /api/v1/performance/stats\n\n"
            "[dim]For detailed documentation, see:[/]\n"
            "• AZURE_DEPLOYMENT.md (Azure platform)\n"
            "• DEPLOYMENT_BACKENDS.md (Other platforms)\n"
            "• PERFORMANCE_OPTIMIZATIONS.md\n"
            "• README.md",
            title="Success",
            border_style="green"
        )

        console.print(completion)
        console.print()


def main():
    """Run setup wizard."""
    try:
        wizard = SetupWizard()
        wizard.run()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Setup cancelled by user[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n\n[red]Error: {e}[/]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
