# llm/ - Multi-Provider LLM Abstraction

LiteLLM-based abstraction for 100+ LLM providers.

## Files

| File | Purpose |
|------|---------|
| `config.py` | Settings models, load/save from `config/llm_settings.json` |
| `provider.py` | `LLMProvider` class, `get_llm_provider()` singleton |

## Supported Providers

- `local` - Docker Model Runner, Ollama (OpenAI-compatible)
- `openai` - GPT-4o, GPT-4o-mini
- `anthropic` - Claude 3 Opus/Sonnet/Haiku
- `azure` - Azure OpenAI Service
- `openrouter` - Multi-provider gateway

## Configuration Hierarchy

1. Agent-specific assignment (`agent_assignments`)
2. Group assignment (`groups`)
3. Default model (`default_model_id`)

## Usage

```python
from src.llm.provider import get_llm_provider

provider = get_llm_provider()
result = await provider.chat(
    messages=[{"role": "user", "content": "Hello"}],
    agent_name="content-writer",  # Optional, for routing
)
```
