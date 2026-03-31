# integrations/ - External Service Clients

API clients for external services.

## Files

| File | Purpose |
|------|---------|
| `openai_client.py` | OpenAI-compatible APIs (OpenAI, Azure, local) |
| `google_search_console.py` | GSC data fetching |
| `serp.py` | SERP API for search results |
| `teams.py` | Microsoft Teams notifications |
| `ahrefs.py` | Backlink analysis |
| `bing.py` | Bing search API |
| `wayback.py` | Wayback Machine historical data |
| `optimizely.py` | A/B testing integration |
| `ai_traffic_tracker.py` | AI-driven traffic analysis |

## OpenAI Client

`OpenAIClient` handles:
- Standard OpenAI API
- Azure OpenAI
- Local models (Docker Model Runner, Ollama)

```python
from src.integrations.openai_client import OpenAIClient
# AzureOpenAIClient is deprecated alias
```

## Note

For new LLM calls, prefer `src/llm/provider.py` (LiteLLM-based).
`openai_client.py` is legacy but still used in some agents.
