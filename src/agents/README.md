# agents/ - Agent Implementations

Individual agent logic. Definitions are in `agent_runner/definitions.py`.

## Agents

| Agent | File | Purpose |
|-------|------|---------|
| SEO Analyst | `seo_analyst.py` | Search Console analysis, AIO detection |
| Trend Analyzer | `trend_analyzer.py` | Trending topics, weekly reports |
| Content Writer | `content_writer.py` | Style analysis, article generation |
| Settings Assistant | `settings_assistant.py` | Help, config, workflows |
| Agent Tester | `agent_tester.py` | Page interpretation for AI agents |
| Optimizer | `optimizer.py` | Schema generation, AIO optimization |
| Monitoring | `monitoring.py` | Traffic anomalies, alerts |

## Base Class

`base.py` - BaseAgent with common functionality and AgentCapability enum.

## Pattern

```python
class MyAgent(BaseAgent):
    name = "my-agent"
    description = "..."

    async def run(self, task: str, context: dict) -> dict:
        # Agent logic
        return {"result": ...}
```
