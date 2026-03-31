# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered SEO optimization platform for the AI Overview era. Helps businesses monitor traffic changes from Google's AI Overviews and optimize for AI agent-driven search.

## Commands

```bash
# Start all services (UI, API, worker, Redis)
docker compose --profile with-ui up -d

# Rebuild after code changes
docker compose --profile with-ui up --build -d

# Run tests
pytest tests/ -v

# Run single test file
pytest tests/test_optimizations.py -v

# Lint
ruff check src/

# Type check
mypy src/
```

## Architecture

### Agent System

The agent system has two layers:

1. **Definitions** (`src/agent_runner/definitions.py`): Declarative agent configs
   - `AgentDefinition`: name, instructions, tools, model
   - `ToolDefinition`: name, parameters, handler reference
   - `ALL_AGENTS` and `ALL_TOOLS` lists

2. **Implementations** (`src/agents/`): Optional Python classes with business logic
   - Handlers referenced in definitions point here
   - Extend `BaseAgent` from `src/agents/base.py`

### LLM Abstraction

Two systems exist (prefer the newer one):

1. **New** - `src/llm/provider.py`: LiteLLM-based, supports 100+ providers
   - Config in `config/llm_settings.json`
   - Per-agent model assignment via Settings UI

2. **Legacy** - `src/integrations/openai_client.py`: Direct OpenAI SDK
   - `OpenAIClient` class (alias `AzureOpenAIClient` deprecated)
   - Still used in some agents

### Web UI

Single FastAPI app at `src/ui/app.py` serving port 8080:
- `/` - Chat (WebSocket at `/ws/{agent_name}`)
- `/dashboard` - Analytics
- `/settings` - LLM and site configuration

HTML templates are embedded in Python, not separate files.

### Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| ui | 8080 | Web interface (Chat, Dashboard, Settings) |
| api | 8000 | REST API |
| redis | 6379 | Cache and task queue |
| worker | - | Celery background tasks |

Local LLM via Docker Model Runner at `http://model-runner.docker.internal/engines/llama.cpp/v1`

## Adding a New Agent

1. Define tools in `src/agent_runner/definitions.py`:
   ```python
   TOOL_MY_ACTION = ToolDefinition(
       name="my_action",
       description="...",
       parameters=ToolParameters(...),
       handler="src.agents.my_agent:MyAgent.my_action",
   )
   ```

2. Define agent in same file:
   ```python
   MY_AGENT = AgentDefinition(
       name="my-agent",
       description="...",
       instructions="...",
       tools=[TOOL_MY_ACTION],
   )
   ```

3. Add to lists: `ALL_AGENTS.append(MY_AGENT)`, `ALL_TOOLS.append(TOOL_MY_ACTION)`

4. Create implementation in `src/agents/my_agent.py`

5. Add to UI dropdown in `src/ui/app.py`

## Key Files

| File | Purpose |
|------|---------|
| `src/agent_runner/definitions.py` | All agent and tool definitions |
| `src/agent_runner/runner.py` | `LocalAgentRunner`, `ConversationalAgent` |
| `src/llm/provider.py` | LLM abstraction with `get_llm_provider()` |
| `src/ui/app.py` | Unified web UI |
| `docker-compose.yml` | Container orchestration |
| `config/llm_settings.json` | LLM provider configuration |

## Code Style

- Python 3.11+
- Ruff for linting (line length 100)
- Pydantic for data models
- Async/await for I/O operations
- structlog for logging
