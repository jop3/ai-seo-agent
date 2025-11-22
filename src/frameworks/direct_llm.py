"""
Direct LLM Framework Integration.

Provides backward compatibility with the existing direct LLM implementation.
No agent framework - just direct LLM API calls.

This is the legacy/default implementation.
"""

import time
from typing import Any, Optional

import structlog

from src.frameworks import (
    AgentConfig,
    AgentResult,
    BaseAgentFramework,
    DeploymentConfig,
    FrameworkType,
    WorkflowConfig,
)

logger = structlog.get_logger()


class DirectLLMFramework(BaseAgentFramework):
    """Direct LLM implementation (no agent framework)."""

    def __init__(self):
        super().__init__()
        self._llm_provider: Optional[str] = None
        self._llm_config: Optional[dict[str, Any]] = None
        self._agents: dict[str, Any] = {}
        self._workflows: dict[str, Any] = {}

    @property
    def framework_type(self) -> FrameworkType:
        """Return the framework type."""
        return FrameworkType.DIRECT_LLM

    def initialize(self, config: dict[str, Any]) -> None:
        """
        Initialize Direct LLM with configuration.

        Args:
            config: Configuration dictionary with:
                - llm_provider: LLM provider (openai, anthropic, azure_openai, etc.)
                - api_key: API key for LLM provider
                - model: Model name
                - endpoint: Optional custom endpoint
                - temperature: Temperature (default: 0.7)

        Example:
            framework.initialize({
                "llm_provider": "openai",
                "api_key": "sk-...",
                "model": "gpt-4o",
                "temperature": 0.7
            })
        """
        try:
            self._llm_provider = config.get("llm_provider", "openai")
            api_key = config.get("api_key")
            model = config.get("model")
            endpoint = config.get("endpoint")
            temperature = config.get("temperature", 0.7)

            if not api_key and self._llm_provider not in ["docker_model_runner", "ollama"]:
                raise ValueError(f"api_key is required for {self._llm_provider}")

            # Store LLM configuration
            self._llm_config = {
                "provider": self._llm_provider,
                "api_key": api_key,
                "model": model,
                "endpoint": endpoint,
                "temperature": temperature,
            }

            self._initialized = True

            logger.info(
                "Direct LLM initialized",
                provider=self._llm_provider,
                model=model,
            )

        except Exception as e:
            logger.error("Failed to initialize Direct LLM", error=str(e))
            raise

    def create_agent(self, agent_config: AgentConfig) -> Any:
        """
        Create a simple agent (just a configuration, no framework).

        Args:
            agent_config: Agent configuration

        Returns:
            Agent configuration dict

        Example:
            agent = framework.create_agent(AgentConfig(
                name="SEO Agent",
                role="analyzer",
                goal="Analyze SEO metrics",
                llm_config={"temperature": 0.8}
            ))
        """
        if not self._initialized:
            raise RuntimeError("Framework not initialized. Call initialize() first.")

        try:
            # Create simple agent configuration (no framework object)
            agent_data = {
                "name": agent_config.name,
                "role": agent_config.role,
                "goal": agent_config.goal,
                "backstory": agent_config.backstory or "",
                "tools": agent_config.tools or [],
                "llm_config": {
                    **self._llm_config,
                    **(agent_config.llm_config or {}),
                },
                "memory": agent_config.memory,
                "verbose": agent_config.verbose,
            }

            # Store agent
            self._agents[agent_config.name] = agent_data

            logger.info(
                "Direct LLM agent created",
                agent_name=agent_config.name,
                role=agent_config.role,
            )

            return agent_data

        except Exception as e:
            logger.error(
                "Failed to create Direct LLM agent",
                agent_name=agent_config.name,
                error=str(e),
            )
            raise

    def create_workflow(self, workflow_config: WorkflowConfig) -> Any:
        """
        Create a simple workflow (sequential task execution).

        Args:
            workflow_config: Workflow configuration

        Returns:
            Workflow configuration dict

        Example:
            workflow = framework.create_workflow(WorkflowConfig(
                name="SEO Pipeline",
                description="Sequential SEO analysis",
                agents=[agent1_config, agent2_config],
                tasks=[
                    {"description": "Analyze", "agent": "SEO Agent"},
                    {"description": "Report", "agent": "Reporter"}
                ]
            ))
        """
        if not self._initialized:
            raise RuntimeError("Framework not initialized. Call initialize() first.")

        try:
            # Create agents for workflow
            agents = {}
            for agent_config in workflow_config.agents:
                agent = self.create_agent(agent_config)
                agents[agent_config.name] = agent

            # Create simple sequential workflow
            workflow_data = {
                "name": workflow_config.name,
                "description": workflow_config.description,
                "agents": agents,
                "tasks": workflow_config.tasks,
                "max_iterations": workflow_config.max_iterations,
                "cache_results": workflow_config.cache_results,
                "execution_mode": "sequential",
            }

            # Store workflow
            self._workflows[workflow_config.name] = workflow_data

            logger.info(
                "Direct LLM workflow created",
                workflow_name=workflow_config.name,
                agent_count=len(agents),
                task_count=len(workflow_config.tasks),
            )

            return workflow_data

        except Exception as e:
            logger.error(
                "Failed to create Direct LLM workflow",
                workflow_name=workflow_config.name,
                error=str(e),
            )
            raise

    def execute_agent(self, agent: Any, task: dict[str, Any]) -> AgentResult:
        """
        Execute an agent task via direct LLM API call.

        Args:
            agent: Agent instance (from create_agent)
            task: Task dictionary with 'description' and optional 'context'

        Returns:
            AgentResult with execution results

        Example:
            result = framework.execute_agent(agent, {
                "description": "Analyze SEO for example.com",
                "context": {"url": "https://example.com"}
            })
        """
        start_time = time.time()

        try:
            agent_name = agent.get("name", "unknown")
            agent_role = agent.get("role", "unknown")
            agent_goal = agent.get("goal", "")
            task_description = task.get("description", "")
            context = task.get("context", {})

            logger.info(
                "Executing Direct LLM agent",
                agent_name=agent_name,
                task=task_description,
            )

            # Build prompt from agent config and task
            system_prompt = f"""You are a {agent_role}.
Your goal: {agent_goal}
{agent.get('backstory', '')}

Task: {task_description}
"""

            if context:
                system_prompt += f"\nContext: {context}"

            # Simulate LLM API call
            # In real implementation, this would call OpenAI/Anthropic/etc API
            llm_config = agent.get("llm_config", {})
            provider = llm_config.get("provider", "openai")
            model = llm_config.get("model", "gpt-4o")

            output = {
                "agent": agent_name,
                "role": agent_role,
                "task": task_description,
                "result": f"Direct LLM execution completed (mock)\nProvider: {provider}\nModel: {model}",
                "framework": "direct_llm",
                "provider": provider,
                "model": model,
            }

            duration_ms = (time.time() - start_time) * 1000
            self._update_metrics(success=True, duration_ms=duration_ms)

            return AgentResult(
                success=True,
                output=output,
                metadata={
                    "agent_name": agent_name,
                    "framework": "direct_llm",
                    "duration_ms": duration_ms,
                    "provider": provider,
                    "model": model,
                },
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._update_metrics(success=False, duration_ms=duration_ms)

            logger.error(
                "Direct LLM agent execution failed",
                error=str(e),
            )

            return AgentResult(
                success=False,
                output=None,
                metadata={"duration_ms": duration_ms},
                error=str(e),
            )

    def execute_workflow(self, workflow: Any, inputs: dict[str, Any]) -> AgentResult:
        """
        Execute a workflow via sequential direct LLM calls.

        Args:
            workflow: Workflow instance (from create_workflow)
            inputs: Input parameters for the workflow

        Returns:
            AgentResult with workflow execution results

        Example:
            result = framework.execute_workflow(workflow, {
                "url": "https://example.com",
                "keywords": ["AI", "SEO"]
            })
        """
        start_time = time.time()

        try:
            workflow_name = workflow.get("name", "unknown")
            tasks = workflow.get("tasks", [])
            agents = workflow.get("agents", {})

            logger.info(
                "Executing Direct LLM workflow",
                workflow_name=workflow_name,
                task_count=len(tasks),
            )

            # Execute tasks sequentially
            task_results = []
            context = inputs.copy()

            for i, task in enumerate(tasks):
                agent_name = task.get("agent")
                agent = agents.get(agent_name)

                if not agent:
                    raise ValueError(f"Agent not found: {agent_name}")

                # Execute task with accumulated context
                result = self.execute_agent(agent, {
                    "description": task.get("description"),
                    "context": context,
                })

                # Add result to context
                if result.success and result.output:
                    context[f"task_{i}_result"] = result.output.get("result")

                task_results.append({
                    "task": task.get("description"),
                    "agent": agent_name,
                    "result": result.output,
                    "success": result.success,
                })

            duration_ms = (time.time() - start_time) * 1000
            self._update_metrics(success=True, duration_ms=duration_ms)

            return AgentResult(
                success=True,
                output={
                    "workflow": workflow_name,
                    "task_results": task_results,
                    "inputs": inputs,
                },
                metadata={
                    "workflow_name": workflow_name,
                    "framework": "direct_llm",
                    "duration_ms": duration_ms,
                    "task_count": len(tasks),
                    "provider": self._llm_provider,
                },
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._update_metrics(success=False, duration_ms=duration_ms)

            logger.error(
                "Direct LLM workflow execution failed",
                workflow_name=workflow.get("name", "unknown"),
                error=str(e),
            )

            return AgentResult(
                success=False,
                output=None,
                metadata={"duration_ms": duration_ms},
                error=str(e),
            )

    def deploy(self, deployment_config: DeploymentConfig) -> str:
        """
        Deploy to any platform (Direct LLM is platform-agnostic).

        Args:
            deployment_config: Deployment configuration

        Returns:
            Deployment URL/info

        Example:
            url = framework.deploy(DeploymentConfig(
                target="docker",
                credentials={}
            ))
        """
        if not self._initialized:
            raise RuntimeError("Framework not initialized. Call initialize() first.")

        try:
            target = deployment_config.target

            logger.info(
                "Direct LLM deployment (platform-agnostic)",
                target=target,
                provider=self._llm_provider,
            )

            # Direct LLM can deploy anywhere - just needs LLM API access
            deployment_url = f"{target}://deployed-seo-agent"

            return deployment_url

        except Exception as e:
            logger.error(
                "Direct LLM deployment failed",
                target=deployment_config.target,
                error=str(e),
            )
            raise
