# AI SEO Agent - Developer Quick Reference

## Quick Start

```bash
# Start all services (API, worker, UI, Redis)
docker compose --profile with-ui up -d

# Access UI at http://localhost:8080
```

## Project Structure

```
src/
├── agent_runner/    # Agent execution (definitions.py has ALL_AGENTS)
├── agents/          # Agent implementations
├── llm/             # Multi-provider LLM (LiteLLM)
├── ui/              # Web UI (app.py = unified)
├── integrations/    # External APIs
├── api/             # REST endpoints
└── cli.py           # CLI entry point
```

## Key Files

| File | What's There |
|------|-------------|
| `src/agent_runner/definitions.py` | All agent & tool definitions |
| `src/ui/app.py` | Unified web UI |
| `src/llm/provider.py` | LLM abstraction |
| `config/llm_settings.json` | LLM configuration |
| `docker-compose.yml` | Container setup |

## Adding a New Agent

1. Create `src/agents/my_agent.py`
2. Add tools to `src/agent_runner/definitions.py`
3. Add agent definition to `definitions.py`
4. Add to `ALL_AGENTS` list
5. Add to UI dropdown in `src/ui/app.py`

## Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| ui | 8080 | Web interface |
| api | 8000 | REST API |
| redis | 6379 | Cache/queue |
| worker | - | Background tasks |

## Local LLM

Using Docker Model Runner with Phi-4:
- Endpoint: `http://model-runner.docker.internal/engines/llama.cpp/v1`
- Configure in Settings UI or `config/llm_settings.json`
