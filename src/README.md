# src/ - SEO Agent Source Code

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `agent_runner/` | Agent execution engine - definitions, runner, Azure client |
| `agents/` | Individual agent implementations (SEO analyst, content writer, etc.) |
| `llm/` | Multi-provider LLM abstraction (LiteLLM-based) |
| `ui/` | Unified web UI (Chat, Dashboard, Settings) at port 8080 |
| `integrations/` | External APIs (Google Search Console, OpenAI, SERP, etc.) |
| `api/` | FastAPI REST endpoints |

## Less Frequently Used

| Directory | Purpose |
|-----------|---------|
| `core/` | Error handling utilities |
| `models/` | Pydantic data models |
| `frameworks/` | Alternative agent frameworks (LangGraph, CrewAI) |
| `m365_agents/` | Microsoft 365/Teams bot integration |
| `scheduler/` | Celery task scheduling |
| `storage/` | Data persistence |
| `cache/` | Caching layer |
| `multitenancy/` | Multi-tenant support |
| `orchestrator/` | Multi-agent orchestration |

## Entry Points

- `cli.py` - Command-line interface
- `ui/app.py` - Web UI (unified FastAPI app)
- `api/main.py` - REST API server
