"""
Agent orchestration engine.

Coordinates multiple agents, manages dependencies, and aggregates results.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Type

import structlog
from pydantic import BaseModel

from src.agents.base import BaseAgent, AgentContext
from src.models.agents import (
    AgentType,
    AgentTask,
    AgentResult,
    Recommendation,
    Alert,
    TaskPriority,
)

logger = structlog.get_logger()


class StepStatus(str, Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""

    agent_type: AgentType
    task_type: str
    name: str
    description: str = ""
    depends_on: list[str] = field(default_factory=list)  # Step names this depends on
    parameters: dict[str, Any] = field(default_factory=dict)
    optional: bool = False  # If True, workflow continues even if this fails
    parallel_group: str | None = None  # Steps with same group run in parallel


class Workflow(BaseModel):
    """Definition of a multi-agent workflow."""

    id: str
    name: str
    description: str
    steps: list[dict[str, Any]]  # Serialized WorkflowStep data

    def get_steps(self) -> list[WorkflowStep]:
        """Convert serialized steps to WorkflowStep objects."""
        return [
            WorkflowStep(
                agent_type=AgentType(s["agent_type"]),
                task_type=s["task_type"],
                name=s["name"],
                description=s.get("description", ""),
                depends_on=s.get("depends_on", []),
                parameters=s.get("parameters", {}),
                optional=s.get("optional", False),
                parallel_group=s.get("parallel_group"),
            )
            for s in self.steps
        ]


@dataclass
class StepResult:
    """Result from a single workflow step."""

    step_name: str
    agent_type: AgentType
    status: StepStatus
    result: AgentResult | None = None
    error: str | None = None
    duration_ms: int = 0


class WorkflowResult(BaseModel):
    """Aggregated result from a complete workflow."""

    workflow_id: str
    workflow_name: str
    success: bool
    started_at: datetime
    completed_at: datetime
    duration_ms: int

    # Aggregated data
    steps_completed: int
    steps_failed: int
    steps_skipped: int

    # Combined results from all agents
    all_recommendations: list[Recommendation] = []
    all_alerts: list[Alert] = []

    # Per-agent summaries
    agent_summaries: dict[str, dict[str, Any]] = {}

    # Executive summary (generated)
    executive_summary: str = ""

    # Priority actions
    priority_actions: list[dict[str, Any]] = []

    # Raw step results
    step_results: list[dict[str, Any]] = []


class AgentOrchestrator:
    """
    Orchestrates multiple agents in coordinated workflows.

    Features:
    - Dependency management (run agents in correct order)
    - Parallel execution where possible
    - Result aggregation across agents
    - Executive summary generation
    """

    # Agent class registry
    _agent_classes: dict[AgentType, Type[BaseAgent]] = {}

    def __init__(self, context: AgentContext):
        self.context = context
        self._register_agents()

    def _register_agents(self):
        """Register all available agent classes."""
        # Import here to avoid circular imports
        from src.agents.seo_analyst import SEOAnalystAgent
        from src.agents.monitoring import MonitoringAgent
        from src.agents.optimizer import OptimizationRecommenderAgent
        from src.agents.competitor_monitor import CompetitorMonitorAgent
        from src.agents.content_generator import ContentGeneratorAgent
        from src.agents.multi_engine_tracker import MultiEngineTrackerAgent
        from src.agents.technical_seo import TechnicalSEOAgent
        from src.agents.link_analysis import LinkAnalysisAgent
        from src.agents.serp_features import SERPFeaturesAgent
        from src.agents.content_decay import ContentDecayAgent
        from src.agents.schema_agent import SchemaAgent
        from src.agents.predictive_seo import PredictiveSEOAgent
        from src.agents.local_seo import LocalSEOAgent
        from src.agents.eeat_analyzer import EEATAnalyzerAgent
        from src.agents.multi_platform_seo import MultiPlatformSEOAgent
        from src.agents.ai_content_analyzer import AIContentAnalyzerAgent
        from src.agents.geo_analyzer import GEOAnalyzerAgent

        self._agent_classes = {
            AgentType.SEO_ANALYST: SEOAnalystAgent,
            AgentType.MONITORING: MonitoringAgent,
            AgentType.OPTIMIZATION_RECOMMENDER: OptimizationRecommenderAgent,
            AgentType.COMPETITOR_MONITOR: CompetitorMonitorAgent,
            AgentType.CONTENT_GENERATOR: ContentGeneratorAgent,
            AgentType.MULTI_ENGINE_TRACKER: MultiEngineTrackerAgent,
            AgentType.TECHNICAL_AUDITOR: TechnicalSEOAgent,
            AgentType.LINK_ANALYZER: LinkAnalysisAgent,
            AgentType.SERP_FEATURES: SERPFeaturesAgent,
            AgentType.CONTENT_DECAY: ContentDecayAgent,
            AgentType.SCHEMA_GENERATOR: SchemaAgent,
            AgentType.PREDICTIVE_SEO: PredictiveSEOAgent,
            AgentType.LOCAL_SEO: LocalSEOAgent,
            AgentType.EEAT_ANALYZER: EEATAnalyzerAgent,
            AgentType.MULTI_PLATFORM_SEO: MultiPlatformSEOAgent,
            AgentType.AI_CONTENT_ANALYZER: AIContentAnalyzerAgent,
            AgentType.GEO_ANALYZER: GEOAnalyzerAgent,
        }

    def _get_agent(self, agent_type: AgentType) -> BaseAgent:
        """Get an agent instance by type."""
        agent_class = self._agent_classes.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return agent_class(self.context)

    async def run_workflow(
        self,
        workflow: Workflow,
        parameters: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """
        Execute a complete workflow.

        Args:
            workflow: The workflow definition to execute
            parameters: Global parameters to pass to all steps

        Returns:
            Aggregated results from all workflow steps
        """
        started_at = datetime.utcnow()
        parameters = parameters or {}

        logger.info(
            "Starting workflow",
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            step_count=len(workflow.steps),
        )

        steps = workflow.get_steps()
        step_results: dict[str, StepResult] = {}
        completed_steps: set[str] = set()

        # Build dependency graph
        remaining_steps = {step.name: step for step in steps}

        while remaining_steps:
            # Find steps ready to run (all dependencies satisfied)
            ready_steps = []
            for name, step in remaining_steps.items():
                deps_satisfied = all(
                    dep in completed_steps for dep in step.depends_on
                )
                if deps_satisfied:
                    ready_steps.append(step)

            if not ready_steps:
                # Circular dependency or unresolvable
                logger.error(
                    "Cannot resolve workflow dependencies",
                    remaining=list(remaining_steps.keys()),
                )
                break

            # Group by parallel_group for concurrent execution
            parallel_groups: dict[str | None, list[WorkflowStep]] = {}
            for step in ready_steps:
                group = step.parallel_group
                if group not in parallel_groups:
                    parallel_groups[group] = []
                parallel_groups[group].append(step)

            # Execute each group
            for group, group_steps in parallel_groups.items():
                if group is not None and len(group_steps) > 1:
                    # Run in parallel
                    results = await self._run_steps_parallel(
                        group_steps, parameters, step_results
                    )
                else:
                    # Run sequentially
                    results = []
                    for step in group_steps:
                        result = await self._run_step(step, parameters, step_results)
                        results.append(result)

                # Record results
                for result in results:
                    step_results[result.step_name] = result
                    completed_steps.add(result.step_name)
                    del remaining_steps[result.step_name]

        completed_at = datetime.utcnow()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # Aggregate results
        return self._aggregate_results(
            workflow=workflow,
            step_results=list(step_results.values()),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )

    async def _run_step(
        self,
        step: WorkflowStep,
        global_params: dict[str, Any],
        prior_results: dict[str, StepResult],
    ) -> StepResult:
        """Execute a single workflow step."""
        start_time = datetime.utcnow()

        logger.info(
            "Running workflow step",
            step_name=step.name,
            agent_type=step.agent_type.value,
            task_type=step.task_type,
        )

        try:
            agent = self._get_agent(step.agent_type)

            # Merge parameters: step params override global params
            params = {**global_params, **step.parameters}

            # Inject results from dependencies if needed
            params["_prior_results"] = {
                name: result.result.data if result.result else {}
                for name, result in prior_results.items()
            }

            task = AgentTask(
                agent_type=step.agent_type,
                task_type=step.task_type,
                parameters=params,
                priority=TaskPriority.HIGH,
            )

            result = await agent.run(task)

            duration_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            logger.info(
                "Step completed",
                step_name=step.name,
                success=result.success,
                duration_ms=duration_ms,
            )

            return StepResult(
                step_name=step.name,
                agent_type=step.agent_type,
                status=StepStatus.COMPLETED if result.success else StepStatus.FAILED,
                result=result,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            logger.error(
                "Step failed",
                step_name=step.name,
                error=str(e),
            )

            return StepResult(
                step_name=step.name,
                agent_type=step.agent_type,
                status=StepStatus.FAILED,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def _run_steps_parallel(
        self,
        steps: list[WorkflowStep],
        global_params: dict[str, Any],
        prior_results: dict[str, StepResult],
    ) -> list[StepResult]:
        """Execute multiple steps in parallel."""
        tasks = [
            self._run_step(step, global_params, prior_results)
            for step in steps
        ]
        return await asyncio.gather(*tasks)

    def _aggregate_results(
        self,
        workflow: Workflow,
        step_results: list[StepResult],
        started_at: datetime,
        completed_at: datetime,
        duration_ms: int,
    ) -> WorkflowResult:
        """Aggregate results from all workflow steps."""

        # Count statuses
        completed = sum(1 for r in step_results if r.status == StepStatus.COMPLETED)
        failed = sum(1 for r in step_results if r.status == StepStatus.FAILED)
        skipped = sum(1 for r in step_results if r.status == StepStatus.SKIPPED)

        # Collect all recommendations and alerts
        all_recommendations: list[Recommendation] = []
        all_alerts: list[Alert] = []
        agent_summaries: dict[str, dict[str, Any]] = {}

        for step_result in step_results:
            if step_result.result:
                all_recommendations.extend(step_result.result.recommendations)
                all_alerts.extend(step_result.result.alerts)

                agent_summaries[step_result.step_name] = {
                    "agent_type": step_result.agent_type.value,
                    "status": step_result.status.value,
                    "duration_ms": step_result.duration_ms,
                    "recommendations": len(step_result.result.recommendations),
                    "alerts": len(step_result.result.alerts),
                    "key_findings": self._extract_key_findings(step_result.result),
                }

        # Sort recommendations by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_recommendations.sort(
            key=lambda r: priority_order.get(r.priority.value, 4)
        )

        # Generate priority actions
        priority_actions = self._generate_priority_actions(
            all_recommendations, all_alerts
        )

        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            workflow, step_results, all_recommendations, all_alerts
        )

        return WorkflowResult(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            success=failed == 0,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            steps_completed=completed,
            steps_failed=failed,
            steps_skipped=skipped,
            all_recommendations=all_recommendations,
            all_alerts=all_alerts,
            agent_summaries=agent_summaries,
            executive_summary=executive_summary,
            priority_actions=priority_actions,
            step_results=[
                {
                    "step_name": r.step_name,
                    "agent_type": r.agent_type.value,
                    "status": r.status.value,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                }
                for r in step_results
            ],
        )

    def _extract_key_findings(self, result: AgentResult) -> list[str]:
        """Extract key findings from an agent result."""
        findings = []

        # Look for common summary fields
        data = result.data
        if "summary" in data:
            findings.append(str(data["summary"]))
        if "score" in data:
            findings.append(f"Score: {data['score']}")
        if "issues_found" in data:
            findings.append(f"Issues found: {data['issues_found']}")
        if "opportunities" in data:
            findings.append(f"Opportunities: {len(data['opportunities'])}")

        return findings[:3]  # Limit to top 3

    def _generate_priority_actions(
        self,
        recommendations: list[Recommendation],
        alerts: list[Alert],
    ) -> list[dict[str, Any]]:
        """Generate prioritized action list."""
        actions = []

        # Critical alerts first
        for alert in alerts:
            if alert.severity.value in ("critical", "error"):
                actions.append({
                    "type": "alert",
                    "priority": "critical",
                    "title": alert.title,
                    "description": alert.message,
                    "source": alert.source,
                })

        # High priority recommendations
        for rec in recommendations[:10]:  # Top 10
            if rec.priority.value in ("critical", "high"):
                actions.append({
                    "type": "recommendation",
                    "priority": rec.priority.value,
                    "title": rec.title,
                    "description": rec.description,
                    "estimated_impact": rec.estimated_impact,
                    "effort": rec.implementation_effort,
                    "auto_implementable": rec.auto_implementable,
                })

        return actions[:15]  # Limit to top 15 actions

    def _generate_executive_summary(
        self,
        workflow: Workflow,
        step_results: list[StepResult],
        recommendations: list[Recommendation],
        alerts: list[Alert],
    ) -> str:
        """Generate an executive summary of the workflow results."""
        completed = sum(1 for r in step_results if r.status == StepStatus.COMPLETED)
        total = len(step_results)

        critical_alerts = sum(
            1 for a in alerts if a.severity.value == "critical"
        )
        high_priority_recs = sum(
            1 for r in recommendations if r.priority.value in ("critical", "high")
        )

        summary_parts = [
            f"## {workflow.name} Results\n",
            f"Completed {completed}/{total} analysis steps.\n",
        ]

        if critical_alerts > 0:
            summary_parts.append(
                f"**{critical_alerts} critical alerts** require immediate attention.\n"
            )

        if high_priority_recs > 0:
            summary_parts.append(
                f"Found **{high_priority_recs} high-priority recommendations** "
                f"out of {len(recommendations)} total.\n"
            )

        # Add per-category summaries
        categories: dict[str, int] = {}
        for rec in recommendations:
            cat = rec.category or "General"
            categories[cat] = categories.get(cat, 0) + 1

        if categories:
            summary_parts.append("\n### Recommendations by Category\n")
            for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
                summary_parts.append(f"- {cat}: {count}\n")

        return "".join(summary_parts)

    async def run_single_agent(
        self,
        agent_type: AgentType,
        task_type: str,
        parameters: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Run a single agent task (convenience method)."""
        agent = self._get_agent(agent_type)
        task = AgentTask(
            agent_type=agent_type,
            task_type=task_type,
            parameters=parameters or {},
        )
        return await agent.run(task)
