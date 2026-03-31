# agent_runner/ - Agent Execution Engine

Runs agents locally or on cloud services. Provider-agnostic.

## Files

| File | Purpose |
|------|---------|
| `definitions.py` | Agent & tool definitions (ALL_AGENTS, ALL_TOOLS) |
| `runner.py` | LocalAgentRunner, ConversationalAgent, tool execution |
| `client.py` | AzureAgentClient for Azure AI Agent Service deployment |

## Key Classes

- `AgentDefinition` - Agent config (name, instructions, tools, model)
- `ToolDefinition` - Tool schema (name, description, parameters, handler)
- `LocalAgentRunner` - Executes agents locally with any LLM
- `ConversationalAgent` - Stateful chat wrapper with history

## Adding New Agents

1. Add tool definitions (TOOL_X) in `definitions.py`
2. Add agent definition (X_AGENT) in `definitions.py`
3. Add to ALL_AGENTS and ALL_TOOLS lists
4. Optionally implement agent class in `src/agents/`
