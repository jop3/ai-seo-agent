"""
Agent Runner - Executes agents locally or routes to Azure AI Agent Service.

This provides a unified interface for running agents regardless of backend.
"""

import asyncio
import importlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx
import structlog

from src.agent_runner.definitions import ALL_TOOLS, AgentDefinition, ToolDefinition
from src.config import get_settings
from src.integrations.openai_client import AzureOpenAIClient

logger = structlog.get_logger()


@dataclass
class Message:
    """A message in the conversation."""
    role: str  # "user", "assistant", "tool"
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None  # For tool messages


@dataclass
class AgentResponse:
    """Response from an agent execution."""
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    tool_calls_made: list[str] = field(default_factory=list)
    conversation: list[Message] = field(default_factory=list)
    execution_time_ms: int = 0


class AgentRunner(ABC):
    """Abstract base for agent runners."""

    @abstractmethod
    async def run(
        self,
        agent: AgentDefinition,
        user_message: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """Run an agent with a user message."""
        pass

    @abstractmethod
    async def run_tool(
        self,
        tool: ToolDefinition,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a specific tool."""
        pass


class LocalAgentRunner(AgentRunner):
    """
    Runs agents locally using Azure OpenAI for LLM + local tool execution.

    This mimics Azure AI Agent Service behavior but runs entirely locally.
    """

    def __init__(
        self,
        openai_client: AzureOpenAIClient | None = None,
        api_base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        max_iterations: int = 10,
    ):
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key or get_settings().api_key.get_secret_value()
        self.max_iterations = max_iterations

        # Initialize OpenAI client
        if openai_client:
            self.openai_client = openai_client
        else:
            settings = get_settings()
            self.openai_client = AzureOpenAIClient(settings.azure)

        # Build tool lookup
        self.tools_by_name = {tool.name: tool for tool in ALL_TOOLS}

    async def run(
        self,
        agent: AgentDefinition,
        user_message: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """
        Run an agent conversation loop.

        1. Send user message to LLM with agent instructions and tools
        2. If LLM requests tool calls, execute them
        3. Send tool results back to LLM
        4. Repeat until LLM gives final response or max iterations reached
        """
        start_time = datetime.utcnow()
        conversation: list[Message] = []
        tool_calls_made: list[str] = []

        # Build messages
        messages = [
            {"role": "system", "content": agent.instructions},
            {"role": "user", "content": user_message},
        ]

        if context:
            messages[0]["content"] += f"\n\nContext:\n{json.dumps(context, indent=2)}"

        conversation.append(Message(role="user", content=user_message))

        # Build tools in OpenAI format
        tools = [tool.to_azure_format() for tool in agent.tools]

        logger.info(
            "Starting agent run",
            agent=agent.name,
            tools_available=len(tools),
        )

        # Conversation loop
        for iteration in range(self.max_iterations):
            logger.debug(f"Agent iteration {iteration + 1}")

            # Call LLM with agent name for model routing
            response = await self._call_llm(messages, tools, agent_name=agent.name)

            # Check if we have tool calls
            if response.get("tool_calls"):
                tool_results = []

                for tool_call in response["tool_calls"]:
                    func_name = tool_call["function"]["name"]
                    func_args = json.loads(tool_call["function"]["arguments"])

                    logger.info(f"Executing tool: {func_name}", args=func_args)
                    tool_calls_made.append(func_name)

                    # Execute the tool
                    try:
                        result = await self.run_tool(
                            self.tools_by_name[func_name],
                            func_args,
                        )
                        tool_results.append({
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "name": func_name,
                            "content": json.dumps(result),
                        })
                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}")
                        tool_results.append({
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "name": func_name,
                            "content": json.dumps({"error": str(e)}),
                        })

                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": response.get("content"),
                    "tool_calls": response["tool_calls"],
                })

                # Add tool results
                messages.extend(tool_results)

                conversation.append(Message(
                    role="assistant",
                    content=response.get("content") or "",
                    tool_calls=response["tool_calls"],
                ))

                for tr in tool_results:
                    conversation.append(Message(
                        role="tool",
                        content=tr["content"],
                        tool_call_id=tr["tool_call_id"],
                        name=tr["name"],
                    ))

            else:
                # No tool calls - final response
                final_content = response.get("content", "")

                conversation.append(Message(
                    role="assistant",
                    content=final_content,
                ))

                execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                return AgentResponse(
                    success=True,
                    message=final_content,
                    data={"iterations": iteration + 1},
                    tool_calls_made=tool_calls_made,
                    conversation=conversation,
                    execution_time_ms=execution_time,
                )

        # Max iterations reached
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return AgentResponse(
            success=False,
            message="Max iterations reached without final response",
            data={"iterations": self.max_iterations},
            tool_calls_made=tool_calls_made,
            conversation=conversation,
            execution_time_ms=execution_time,
        )

    async def run_tool(
        self,
        tool: ToolDefinition,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute a tool by calling handler function or API endpoint.

        Supports two modes:
        1. handler: Direct Python function call (e.g., "src.agents.my_agent:MyAgent.method")
        2. api_endpoint: HTTP POST to local API
        """
        # Prefer handler-based execution
        if tool.handler:
            return await self._execute_handler(tool.handler, parameters)

        # Fall back to API endpoint
        if tool.api_endpoint:
            return await self._execute_api_endpoint(tool, parameters)

        raise ValueError(f"Tool {tool.name} has no handler or api_endpoint defined")

    async def _execute_handler(
        self,
        handler: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a handler function directly."""
        try:
            # Parse handler string: "module.path:ClassName.method"
            module_path, func_path = handler.rsplit(":", 1)

            # Import the module
            module = importlib.import_module(module_path)

            # Navigate to the function/method
            if "." in func_path:
                class_name, method_name = func_path.split(".", 1)
                cls = getattr(module, class_name)
                instance = cls()  # Create instance
                func = getattr(instance, method_name)
            else:
                func = getattr(module, func_path)

            # Call the function (handle both sync and async)
            if asyncio.iscoroutinefunction(func):
                result = await func(**parameters)
            else:
                result = func(**parameters)

            # Ensure result is JSON-serializable
            if hasattr(result, "dict"):  # Pydantic model
                return result.dict()
            elif hasattr(result, "__dict__"):  # Dataclass or object
                return result.__dict__
            elif isinstance(result, (dict, list, str, int, float, bool, type(None))):
                return result if isinstance(result, dict) else {"result": result}
            else:
                return {"result": str(result)}

        except Exception as e:
            logger.error(f"Handler execution failed: {handler}", error=str(e))
            return {"error": f"Handler execution failed: {str(e)}"}

    async def _execute_api_endpoint(
        self,
        tool: ToolDefinition,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool via API endpoint."""
        url = f"{self.api_base_url}{tool.api_endpoint}"

        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                json=parameters,
                headers=headers,
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"API call failed: {response.status_code}",
                    "detail": response.text,
                }

    async def _call_llm(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        """Call LLM with function calling using the unified LLM provider."""
        try:
            # Try to use the new LLM provider system
            from src.llm.provider import get_llm_provider

            provider = get_llm_provider()
            result = await provider.chat(
                messages=messages,
                agent_name=agent_name,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
            )

            return {
                "content": result.get("content"),
                "tool_calls": result.get("tool_calls"),
            }

        except ImportError:
            # Fall back to direct OpenAI/Azure if LLM provider not available
            logger.warning("LLM provider not available, using fallback")
            return await self._call_llm_fallback(messages, tools)

    async def _call_llm_fallback(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Fallback LLM call using direct OpenAI/Azure (for backwards compatibility)."""
        from openai import AsyncAzureOpenAI, AsyncOpenAI

        settings = get_settings()

        # Check if using standard OpenAI API (e.g., Docker Model Runner)
        if settings.openai_api_base:
            client = AsyncOpenAI(
                api_key=settings.openai_api_key or "not-needed",
                base_url=settings.openai_api_base,
            )
            model = settings.openai_model
        else:
            client = AsyncAzureOpenAI(
                api_key=settings.azure.openai_api_key.get_secret_value(),
                api_version=settings.azure.openai_api_version,
                azure_endpoint=settings.azure.openai_endpoint,
            )
            model = settings.azure.openai_deployment

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
        )

        choice = response.choices[0]

        result = {
            "content": choice.message.content,
            "tool_calls": None,
        }

        if choice.message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in choice.message.tool_calls
            ]

        return result


class ConversationalAgent:
    """
    A high-level conversational interface to an agent.

    Maintains conversation history and provides a simple chat interface.
    """

    def __init__(
        self,
        agent: AgentDefinition,
        runner: AgentRunner | None = None,
    ):
        self.agent = agent
        self.runner = runner or LocalAgentRunner()
        self.conversation_history: list[Message] = []

    async def chat(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """Send a message and get a response."""
        # Include conversation history in context
        if self.conversation_history:
            history_context = {
                "previous_messages": [
                    {"role": m.role, "content": m.content}
                    for m in self.conversation_history[-10:]  # Last 10 messages
                ]
            }
            if context:
                context.update(history_context)
            else:
                context = history_context

        response = await self.runner.run(self.agent, message, context)

        # Update history
        self.conversation_history.extend(response.conversation)

        return response

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []


async def run_agent_task(
    agent_name: str,
    task: str,
    context: dict[str, Any] | None = None,
    runner: AgentRunner | None = None,
) -> AgentResponse:
    """
    Convenience function to run a single agent task.

    Args:
        agent_name: Name of the agent (e.g., "seo-analyst")
        task: The task/question for the agent
        context: Optional context data
        runner: Optional custom runner (defaults to LocalAgentRunner)

    Returns:
        AgentResponse with results
    """
    from src.agent_runner.definitions import ALL_AGENTS

    # Find agent by name
    agent = next((a for a in ALL_AGENTS if a.name == agent_name), None)
    if not agent:
        return AgentResponse(
            success=False,
            message=f"Unknown agent: {agent_name}",
        )

    if runner is None:
        runner = LocalAgentRunner()

    return await runner.run(agent, task, context)
