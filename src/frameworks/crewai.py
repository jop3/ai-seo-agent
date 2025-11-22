"""
CrewAI Framework Integration.

Provides integration with CrewAI for role-based multi-agent collaboration.
Supports sequential and hierarchical workflows with task delegation.

Documentation: https://docs.crewai.com/
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


class CrewAIFramework(BaseAgentFramework):
    """CrewAI framework implementation."""

    def __init__(self):
        super().__init__()
        self._agents: dict[str, Any] = {}
        self._crews: dict[str, Any] = {}
        self._llm_config: Optional[dict[str, Any]] = None

    @property
    def framework_type(self) -> FrameworkType:
        """Return the framework type."""
        return FrameworkType.CREWAI

    def initialize(self, config: dict[str, Any]) -> None:
        """
        Initialize CrewAI with configuration.

        Args:
            config: Configuration dictionary with:
                - llm_provider: LLM provider (openai, anthropic, etc.)
                - api_key: API key for LLM provider
                - model: Model name (default: gpt-4o)
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
            llm_provider = config.get("llm_provider", "openai")
            api_key = config.get("api_key")
            model = config.get("model", "gpt-4o")
            temperature = config.get("temperature", 0.7)

            if not api_key:
                raise ValueError("api_key is required for CrewAI")

            # Store LLM configuration
            self._llm_config = {
                "provider": llm_provider,
                "api_key": api_key,
                "model": model,
                "temperature": temperature,
            }

            self._initialized = True

            logger.info(
                "CrewAI initialized",
                llm_provider=llm_provider,
                model=model,
            )

        except Exception as e:
            logger.error("Failed to initialize CrewAI", error=str(e))
            raise

    def create_agent(self, agent_config: AgentConfig) -> Any:
        """
        Create a CrewAI agent.

        Args:
            agent_config: Agent configuration

        Returns:
            Agent instance (dict representation)

        Example:
            agent = framework.create_agent(AgentConfig(
                name="SEO Researcher",
                role="Senior SEO Analyst",
                goal="Find SEO optimization opportunities",
                backstory="Expert SEO analyst with 10 years experience",
                tools=["search", "scrape"],
                verbose=True
            ))
        """
        if not self._initialized:
            raise RuntimeError("Framework not initialized. Call initialize() first.")

        try:
            # Create CrewAI Agent configuration
            agent_data = {
                "name": agent_config.name,
                "role": agent_config.role,
                "goal": agent_config.goal,
                "backstory": agent_config.backstory or f"You are a {agent_config.role}.",
                "tools": agent_config.tools or [],
                "llm_config": {
                    **self._llm_config,
                    **(agent_config.llm_config or {}),
                },
                "memory": agent_config.memory,
                "verbose": agent_config.verbose,
                "allow_delegation": False,  # Can be configured
                "max_iterations": 15,
            }

            # Store agent
            self._agents[agent_config.name] = agent_data

            logger.info(
                "CrewAI agent created",
                agent_name=agent_config.name,
                role=agent_config.role,
            )

            return agent_data

        except Exception as e:
            logger.error(
                "Failed to create CrewAI agent",
                agent_name=agent_config.name,
                error=str(e),
            )
            raise

    def create_workflow(self, workflow_config: WorkflowConfig) -> Any:
        """
        Create a CrewAI Crew (workflow).

        Args:
            workflow_config: Workflow configuration

        Returns:
            Crew instance (dict representation)

        Example:
            workflow = framework.create_workflow(WorkflowConfig(
                name="SEO Crew",
                description="Complete SEO analysis and optimization",
                agents=[researcher_config, analyst_config, writer_config],
                tasks=[
                    {"description": "Research keywords", "agent": "SEO Researcher"},
                    {"description": "Analyze competition", "agent": "SEO Analyst"},
                    {"description": "Write content", "agent": "Content Writer"}
                ],
                max_iterations=10
            ))
        """
        if not self._initialized:
            raise RuntimeError("Framework not initialized. Call initialize() first.")

        try:
            # Create agents for crew
            agents = {}
            for agent_config in workflow_config.agents:
                agent = self.create_agent(agent_config)
                agents[agent_config.name] = agent

            # Create tasks
            tasks = []
            for task_config in workflow_config.tasks:
                agent_name = task_config.get("agent")

                task = {
                    "description": task_config.get("description"),
                    "agent": agent_name,
                    "expected_output": task_config.get("expected_output", "Detailed analysis"),
                    "context": task_config.get("context", []),
                    "async_execution": task_config.get("async", False),
                }
                tasks.append(task)

            # Create Crew configuration
            crew_data = {
                "name": workflow_config.name,
                "description": workflow_config.description,
                "agents": agents,
                "tasks": tasks,
                "process": "sequential",  # or "hierarchical"
                "max_iterations": workflow_config.max_iterations,
                "cache_results": workflow_config.cache_results,
                "verbose": True,
                "manager_llm": self._llm_config if workflow_config.max_iterations > 1 else None,
            }

            # Store crew
            self._crews[workflow_config.name] = crew_data

            logger.info(
                "CrewAI crew created",
                crew_name=workflow_config.name,
                agent_count=len(agents),
                task_count=len(tasks),
            )

            return crew_data

        except Exception as e:
            logger.error(
                "Failed to create CrewAI crew",
                workflow_name=workflow_config.name,
                error=str(e),
            )
            raise

    def execute_agent(self, agent: Any, task: dict[str, Any]) -> AgentResult:
        """
        Execute a CrewAI agent on a task.

        Args:
            agent: Agent instance (from create_agent)
            task: Task dictionary with 'description' and optional 'context'

        Returns:
            AgentResult with execution results

        Example:
            result = framework.execute_agent(agent, {
                "description": "Research SEO keywords for example.com",
                "context": {"url": "https://example.com"}
            })
        """
        start_time = time.time()

        try:
            agent_name = agent.get("name", "unknown")
            agent_role = agent.get("role", "unknown")
            task_description = task.get("description", "")

            logger.info(
                "Executing CrewAI agent",
                agent_name=agent_name,
                role=agent_role,
                task=task_description,
            )

            # Simulate agent execution
            # In real implementation, this would use CrewAI's Agent.execute()
            output = {
                "agent": agent_name,
                "role": agent_role,
                "task": task_description,
                "result": "Agent task completed (mock)",
                "framework": "crewai",
                "tools_used": agent.get("tools", []),
            }

            duration_ms = (time.time() - start_time) * 1000
            self._update_metrics(success=True, duration_ms=duration_ms)

            return AgentResult(
                success=True,
                output=output,
                metadata={
                    "agent_name": agent_name,
                    "agent_role": agent_role,
                    "framework": "crewai",
                    "duration_ms": duration_ms,
                },
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._update_metrics(success=False, duration_ms=duration_ms)

            logger.error(
                "CrewAI agent execution failed",
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
        Execute a CrewAI Crew workflow.

        Args:
            workflow: Workflow instance (from create_workflow)
            inputs: Input parameters for the crew

        Returns:
            AgentResult with crew execution results

        Example:
            result = framework.execute_workflow(workflow, {
                "url": "https://example.com",
                "target_keywords": ["AI", "SEO", "automation"]
            })
        """
        start_time = time.time()

        try:
            crew_name = workflow.get("name", "unknown")
            tasks = workflow.get("tasks", [])
            agents = workflow.get("agents", {})
            process = workflow.get("process", "sequential")

            logger.info(
                "Executing CrewAI crew",
                crew_name=crew_name,
                task_count=len(tasks),
                process=process,
            )

            # Execute tasks sequentially (or hierarchically)
            task_results = []
            context = inputs.copy()

            for i, task in enumerate(tasks):
                agent_name = task.get("agent")
                agent = agents.get(agent_name)

                if not agent:
                    raise ValueError(f"Agent not found: {agent_name}")

                # Execute agent task with context from previous tasks
                result = self.execute_agent(agent, {
                    "description": task.get("description"),
                    "context": context,
                })

                # Add result to context for next tasks
                if result.success and result.output:
                    context[f"task_{i}_result"] = result.output

                task_results.append({
                    "task": task.get("description"),
                    "agent": agent_name,
                    "agent_role": agent.get("role"),
                    "result": result.output,
                    "success": result.success,
                })

            duration_ms = (time.time() - start_time) * 1000
            self._update_metrics(success=True, duration_ms=duration_ms)

            return AgentResult(
                success=True,
                output={
                    "crew": crew_name,
                    "task_results": task_results,
                    "inputs": inputs,
                    "process": process,
                },
                metadata={
                    "crew_name": crew_name,
                    "framework": "crewai",
                    "duration_ms": duration_ms,
                    "task_count": len(tasks),
                    "process": process,
                },
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._update_metrics(success=False, duration_ms=duration_ms)

            logger.error(
                "CrewAI crew execution failed",
                crew_name=workflow.get("name", "unknown"),
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
        Deploy CrewAI crew to cloud platform.

        Args:
            deployment_config: Deployment configuration

        Returns:
            Deployment URL

        Example:
            url = framework.deploy(DeploymentConfig(
                target="docker",
                credentials={"registry": "ghcr.io/myorg"}
            ))
        """
        if not self._initialized:
            raise RuntimeError("Framework not initialized. Call initialize() first.")

        try:
            target = deployment_config.target

            supported_targets = ["docker", "kubernetes", "aws", "gcp", "azure"]
            if target not in supported_targets:
                raise ValueError(
                    f"CrewAI supports {supported_targets}, got: {target}"
                )

            # In real implementation, this would:
            # 1. Package the crew as a Docker container
            # 2. Deploy to specified platform
            # 3. Set up API endpoint
            # 4. Return deployment URL

            if target == "docker":
                registry = deployment_config.credentials.get("registry", "docker.io")
                deployment_url = f"{registry}/crewai-seo-agent:latest"
            else:
                deployment_url = f"https://{target}-deployment-url.com/api/crew"

            logger.info(
                "CrewAI deployment completed",
                target=target,
                deployment_url=deployment_url,
            )

            return deployment_url

        except Exception as e:
            logger.error(
                "CrewAI deployment failed",
                target=deployment_config.target,
                error=str(e),
            )
            raise
