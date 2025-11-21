"""Workflow API endpoints for orchestrated SEO analysis."""

from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencies import get_agent_context, verify_api_key
from src.orchestrator import (
    AgentOrchestrator,
    WorkflowResult,
    get_workflow,
    list_workflows,
)

logger = structlog.get_logger()
router = APIRouter(dependencies=[Depends(verify_api_key)])


class WorkflowListResponse(BaseModel):
    """Response with list of available workflows."""
    workflows: list[dict[str, Any]]


class WorkflowRunRequest(BaseModel):
    """Request to run a workflow."""
    parameters: dict[str, Any] = {}


class WorkflowRunResponse(BaseModel):
    """Response from workflow execution."""
    workflow_id: str
    workflow_name: str
    success: bool
    duration_ms: int
    steps_completed: int
    steps_failed: int
    total_recommendations: int
    total_alerts: int
    priority_actions: list[dict[str, Any]]
    executive_summary: str


class WorkflowStatusResponse(BaseModel):
    """Response with workflow execution status."""
    job_id: str
    status: str
    result: WorkflowRunResponse | None = None


# In-memory job tracking (would use Redis/DB in production)
_workflow_jobs: dict[str, dict[str, Any]] = {}


@router.get("/", response_model=WorkflowListResponse)
async def get_available_workflows():
    """List all available workflows."""
    return WorkflowListResponse(workflows=list_workflows())


@router.get("/{workflow_id}")
async def get_workflow_details(workflow_id: str):
    """Get details about a specific workflow."""
    workflow = get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "steps": workflow.steps,
    }


@router.post("/{workflow_id}/run", response_model=WorkflowRunResponse)
async def run_workflow_sync(
    workflow_id: str,
    request: WorkflowRunRequest,
    context=Depends(get_agent_context),
):
    """
    Run a workflow synchronously and wait for results.

    Use this for quick workflows or when you need immediate results.
    For long-running workflows, use the async endpoint.
    """
    workflow = get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    logger.info("Running workflow", workflow_id=workflow_id)

    orchestrator = AgentOrchestrator(context)
    result = await orchestrator.run_workflow(workflow, request.parameters)

    return WorkflowRunResponse(
        workflow_id=result.workflow_id,
        workflow_name=result.workflow_name,
        success=result.success,
        duration_ms=result.duration_ms,
        steps_completed=result.steps_completed,
        steps_failed=result.steps_failed,
        total_recommendations=len(result.all_recommendations),
        total_alerts=len(result.all_alerts),
        priority_actions=result.priority_actions,
        executive_summary=result.executive_summary,
    )


@router.post("/{workflow_id}/run/async")
async def run_workflow_async(
    workflow_id: str,
    request: WorkflowRunRequest,
    background_tasks: BackgroundTasks,
    context=Depends(get_agent_context),
):
    """
    Start a workflow in the background.

    Returns a job ID that can be used to check status.
    """
    workflow = get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    import uuid
    job_id = str(uuid.uuid4())

    _workflow_jobs[job_id] = {
        "status": "running",
        "workflow_id": workflow_id,
        "result": None,
    }

    async def run_in_background():
        try:
            orchestrator = AgentOrchestrator(context)
            result = await orchestrator.run_workflow(workflow, request.parameters)
            _workflow_jobs[job_id] = {
                "status": "completed",
                "workflow_id": workflow_id,
                "result": result,
            }
        except Exception as e:
            _workflow_jobs[job_id] = {
                "status": "failed",
                "workflow_id": workflow_id,
                "error": str(e),
            }

    background_tasks.add_task(run_in_background)

    return {"job_id": job_id, "status": "running"}


@router.get("/jobs/{job_id}")
async def get_workflow_job_status(job_id: str):
    """Get the status of an async workflow job."""
    job = _workflow_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    response = {
        "job_id": job_id,
        "status": job["status"],
        "workflow_id": job.get("workflow_id"),
    }

    if job["status"] == "completed" and job.get("result"):
        result: WorkflowResult = job["result"]
        response["result"] = {
            "workflow_name": result.workflow_name,
            "success": result.success,
            "duration_ms": result.duration_ms,
            "steps_completed": result.steps_completed,
            "steps_failed": result.steps_failed,
            "total_recommendations": len(result.all_recommendations),
            "total_alerts": len(result.all_alerts),
            "priority_actions": result.priority_actions,
            "executive_summary": result.executive_summary,
            "agent_summaries": result.agent_summaries,
        }
    elif job["status"] == "failed":
        response["error"] = job.get("error")

    return response


@router.get("/jobs/{job_id}/recommendations")
async def get_job_recommendations(job_id: str):
    """Get all recommendations from a completed workflow job."""
    job = _workflow_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    result: WorkflowResult = job["result"]
    return {
        "job_id": job_id,
        "total": len(result.all_recommendations),
        "recommendations": [r.model_dump() for r in result.all_recommendations],
    }


@router.get("/jobs/{job_id}/alerts")
async def get_job_alerts(job_id: str):
    """Get all alerts from a completed workflow job."""
    job = _workflow_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    result: WorkflowResult = job["result"]
    return {
        "job_id": job_id,
        "total": len(result.all_alerts),
        "alerts": [a.model_dump() for a in result.all_alerts],
    }
