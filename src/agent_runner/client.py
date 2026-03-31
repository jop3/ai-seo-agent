"""
Azure AI Agent Service Client

This client provides methods to:
1. Deploy agent definitions to Azure AI Agent Service
2. Run agents on Azure AI Agent Service
3. Manage agent lifecycle (create, update, delete)

When running locally, use LocalAgentRunner instead.
When deploying to Azure, use this client to register agents.
"""

import json
from typing import Any
from dataclasses import dataclass

import structlog

from src.agent_runner.definitions import AgentDefinition, ALL_AGENTS
from src.agent_runner.runner import AgentRunner, AgentResponse, Message
from src.config import get_settings

logger = structlog.get_logger()


@dataclass
class AzureAgentInfo:
    """Information about a deployed Azure agent."""
    agent_id: str
    name: str
    model: str
    status: str
    created_at: str
    metadata: dict[str, Any]


class AzureAgentClient(AgentRunner):
    """
    Client for Azure AI Agent Service.

    This integrates with the Azure AI Projects SDK to deploy and run agents
    on Azure infrastructure.

    Prerequisites:
    - Azure AI Hub/Project created
    - Azure OpenAI deployment
    - Proper RBAC permissions
    """

    def __init__(
        self,
        project_connection_string: str | None = None,
        credential: Any = None,
    ):
        """
        Initialize the Azure AI Agent Service client.

        Args:
            project_connection_string: Azure AI Project connection string
            credential: Azure credential (defaults to DefaultAzureCredential)
        """
        self.project_connection_string = project_connection_string
        self._client = None
        self._credential = credential

        # Deployed agent IDs
        self._deployed_agents: dict[str, str] = {}

    def _get_client(self):
        """Lazy initialization of Azure AI Projects client."""
        if self._client is None:
            try:
                from azure.ai.projects import AIProjectClient
                from azure.identity import DefaultAzureCredential

                credential = self._credential or DefaultAzureCredential()

                if self.project_connection_string:
                    self._client = AIProjectClient.from_connection_string(
                        credential=credential,
                        conn_str=self.project_connection_string,
                    )
                else:
                    raise ValueError(
                        "project_connection_string is required for Azure AI Agent Service. "
                        "Use LocalAgentRunner for local execution."
                    )

            except ImportError:
                raise ImportError(
                    "Azure AI Projects SDK not installed. "
                    "Install with: pip install azure-ai-projects azure-identity"
                )

        return self._client

    async def deploy_agent(
        self,
        agent: AgentDefinition,
        update_if_exists: bool = True,
    ) -> AzureAgentInfo:
        """
        Deploy an agent definition to Azure AI Agent Service.

        Args:
            agent: The agent definition to deploy
            update_if_exists: Update if agent already exists

        Returns:
            Information about the deployed agent
        """
        client = self._get_client()

        # Check if agent already exists
        existing = await self._find_agent_by_name(agent.name)

        if existing and update_if_exists:
            logger.info(f"Updating existing agent: {agent.name}")
            # Delete and recreate (Azure doesn't support update well)
            await self.delete_agent(existing.agent_id)

        elif existing and not update_if_exists:
            logger.info(f"Agent already exists: {agent.name}")
            return existing

        # Create the agent
        logger.info(f"Creating agent: {agent.name}")

        azure_agent = client.agents.create_agent(
            model=agent.model,
            name=agent.name,
            instructions=agent.instructions,
            tools=[tool.to_azure_format() for tool in agent.tools],
            metadata={
                "version": agent.version,
                "local_class": agent.local_class,
                **agent.tags,
            },
        )

        self._deployed_agents[agent.name] = azure_agent.id

        return AzureAgentInfo(
            agent_id=azure_agent.id,
            name=azure_agent.name,
            model=azure_agent.model,
            status="ready",
            created_at=azure_agent.created_at.isoformat() if hasattr(azure_agent, 'created_at') else "",
            metadata=azure_agent.metadata or {},
        )

    async def deploy_all_agents(self) -> list[AzureAgentInfo]:
        """Deploy all defined agents to Azure."""
        results = []
        for agent in ALL_AGENTS:
            try:
                info = await self.deploy_agent(agent)
                results.append(info)
            except Exception as e:
                logger.error(f"Failed to deploy agent {agent.name}: {e}")

        return results

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent from Azure."""
        client = self._get_client()

        try:
            client.agents.delete_agent(agent_id)
            logger.info(f"Deleted agent: {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete agent: {e}")
            return False

    async def list_agents(self) -> list[AzureAgentInfo]:
        """List all deployed agents."""
        client = self._get_client()

        agents = client.agents.list_agents()

        return [
            AzureAgentInfo(
                agent_id=a.id,
                name=a.name,
                model=a.model,
                status="ready",
                created_at=a.created_at.isoformat() if hasattr(a, 'created_at') else "",
                metadata=a.metadata or {},
            )
            for a in agents.data
        ]

    async def _find_agent_by_name(self, name: str) -> AzureAgentInfo | None:
        """Find an agent by name."""
        agents = await self.list_agents()
        return next((a for a in agents if a.name == name), None)

    async def run(
        self,
        agent: AgentDefinition,
        user_message: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """
        Run an agent on Azure AI Agent Service.

        This creates a thread, sends the message, and processes the response.
        """
        client = self._get_client()

        # Get or deploy agent
        agent_id = self._deployed_agents.get(agent.name)
        if not agent_id:
            info = await self.deploy_agent(agent)
            agent_id = info.agent_id

        # Create a thread for this conversation
        thread = client.agents.create_thread()

        # Add context to message if provided
        full_message = user_message
        if context:
            full_message += f"\n\nContext:\n```json\n{json.dumps(context, indent=2)}\n```"

        # Add the user message
        client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=full_message,
        )

        # Run the agent
        run = client.agents.create_and_process_run(
            thread_id=thread.id,
            assistant_id=agent_id,
        )

        # Get messages
        messages = client.agents.list_messages(thread_id=thread.id)

        # Parse response
        conversation = []
        final_message = ""
        tool_calls_made = []

        for msg in reversed(messages.data):
            content = msg.content[0].text.value if msg.content else ""
            conversation.append(Message(
                role=msg.role,
                content=content,
            ))
            if msg.role == "assistant":
                final_message = content

        # Get tool calls from run steps
        run_steps = client.agents.list_run_steps(thread_id=thread.id, run_id=run.id)
        for step in run_steps.data:
            if step.type == "tool_calls":
                for tc in step.step_details.tool_calls:
                    tool_calls_made.append(tc.function.name)

        # Cleanup thread
        client.agents.delete_thread(thread.id)

        return AgentResponse(
            success=run.status == "completed",
            message=final_message,
            data={
                "run_id": run.id,
                "thread_id": thread.id,
                "status": run.status,
            },
            tool_calls_made=tool_calls_made,
            conversation=conversation,
        )

    async def run_tool(
        self,
        tool: "ToolDefinition",
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute a tool. For Azure AI Agent Service, tools are executed
        automatically by the service when the agent requests them.

        This method is provided for manual tool execution if needed.
        """
        # For Azure, tools should be Azure Functions or API endpoints
        # that the service can call directly

        if tool.api_endpoint:
            import httpx

            # Assume the tool endpoint is deployed as an Azure Function
            # or accessible API
            settings = get_settings()
            base_url = settings.azure.openai_endpoint.replace("openai.azure.com", "azurewebsites.net")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{base_url}/api/{tool.name}",
                    json=parameters,
                )
                return response.json()

        raise ValueError(f"Tool {tool.name} has no executable endpoint for Azure")


class AgentOrchestrator:
    """
    Orchestrates multiple agents to solve complex tasks.

    Can route tasks to the most appropriate agent and coordinate
    multi-agent workflows.
    """

    def __init__(
        self,
        runner: AgentRunner,
        agents: list[AgentDefinition] | None = None,
    ):
        self.runner = runner
        self.agents = {a.name: a for a in (agents or ALL_AGENTS)}

    async def route_and_run(
        self,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """
        Automatically route a task to the most appropriate agent.
        """
        # Simple keyword-based routing (could be enhanced with LLM)
        task_lower = task.lower()

        if any(kw in task_lower for kw in ["traffic", "drop", "gsc", "search console", "query", "queries"]):
            agent = self.agents["seo-analyst"]
        elif any(kw in task_lower for kw in ["page", "test", "checkout", "agent-friendly", "schema valid"]):
            agent = self.agents["agent-tester"]
        elif any(kw in task_lower for kw in ["monitor", "alert", "watch", "anomaly"]):
            agent = self.agents["monitoring-agent"]
        elif any(kw in task_lower for kw in ["optimize", "generate", "faq", "schema", "improve"]):
            agent = self.agents["optimizer"]
        else:
            # Default to SEO analyst
            agent = self.agents["seo-analyst"]

        logger.info(f"Routing task to agent: {agent.name}")

        return await self.runner.run(agent, task, context)

    async def run_workflow(
        self,
        workflow: list[dict[str, Any]],
        initial_context: dict[str, Any] | None = None,
    ) -> list[AgentResponse]:
        """
        Run a multi-step workflow across agents.

        workflow format:
        [
            {"agent": "seo-analyst", "task": "Analyze top queries"},
            {"agent": "optimizer", "task": "Generate recommendations based on analysis"},
        ]

        Each step's output is added to the context for the next step.
        """
        context = initial_context or {}
        results = []

        for step in workflow:
            agent_name = step["agent"]
            task = step["task"]

            agent = self.agents.get(agent_name)
            if not agent:
                results.append(AgentResponse(
                    success=False,
                    message=f"Unknown agent: {agent_name}",
                ))
                continue

            response = await self.runner.run(agent, task, context)
            results.append(response)

            # Add response to context for next step
            context[f"{agent_name}_result"] = {
                "success": response.success,
                "message": response.message,
                "data": response.data,
            }

        return results
