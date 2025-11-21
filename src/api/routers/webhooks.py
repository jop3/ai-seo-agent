"""Webhook endpoints for external integrations."""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from src.agents.monitoring import MonitoringAgent
from src.agents.seo_analyst import SEOAnalystAgent
from src.api.dependencies import AgentContextDep, ApiKeyDep
from src.models.agents import AgentTask

router = APIRouter()


class GSCNotification(BaseModel):
    """Google Search Console notification payload."""
    site_url: str
    notification_type: str
    data: dict[str, Any] = {}


class OptimizelyWebhook(BaseModel):
    """Optimizely webhook payload."""
    event_type: str
    content_id: str | None = None
    content_url: str | None = None
    data: dict[str, Any] = {}


class ScheduledTaskRequest(BaseModel):
    """Request to trigger a scheduled task."""
    task_name: str
    parameters: dict[str, Any] = {}


@router.post("/gsc-notification")
async def handle_gsc_notification(
    notification: GSCNotification,
    background_tasks: BackgroundTasks,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Handle notifications from Google Search Console.

    Can be configured to receive alerts about:
    - Coverage issues
    - Manual actions
    - Security issues
    """
    # Process notification in background
    async def process_notification():
        agent = MonitoringAgent(context)

        # Log and potentially alert on significant notifications
        if notification.notification_type in ["manual_action", "security_issue"]:
            from src.models.agents import Alert, AlertSeverity, AlertType

            alert = Alert(
                type=AlertType.ALGORITHM_UPDATE,
                severity=AlertSeverity.CRITICAL,
                title=f"GSC Alert: {notification.notification_type}",
                message=f"Google Search Console reported: {notification.notification_type}",
                data=notification.data,
            )
            await agent.send_alert(alert)

    background_tasks.add_task(process_notification)

    return {
        "status": "accepted",
        "notification_type": notification.notification_type,
    }


@router.post("/optimizely")
async def handle_optimizely_webhook(
    webhook: OptimizelyWebhook,
    background_tasks: BackgroundTasks,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Handle webhooks from Optimizely CMS.

    Triggers analysis when content is published or updated.
    """
    async def process_webhook():
        if webhook.event_type == "content_published" and webhook.content_url:
            from src.agents.agent_tester import AgentTesterAgent

            # Analyze the updated page
            agent = AgentTesterAgent(context)

            task = AgentTask(
                agent_type=agent.agent_type,
                task_type="interpret_page",
                parameters={"url": webhook.content_url},
            )

            result = await agent.run(task)

            # If score is low, alert
            score = result.data.get("page_analysis", {}).get("agent_friendliness_score", 100)
            if score < 60:
                from src.models.agents import Alert, AlertSeverity, AlertType

                alert = Alert(
                    type=AlertType.AGENT_TEST_FAILURE,
                    severity=AlertSeverity.WARNING,
                    title=f"Low agent-friendliness score on new content",
                    message=f"Published page {webhook.content_url} scored {score}/100 for agent-friendliness",
                    data={"url": webhook.content_url, "score": score},
                )

                if context.teams_notifier:
                    await context.teams_notifier.send_alert(alert)

    background_tasks.add_task(process_webhook)

    return {
        "status": "accepted",
        "event_type": webhook.event_type,
    }


@router.post("/scheduled-task")
async def trigger_scheduled_task(
    request: ScheduledTaskRequest,
    background_tasks: BackgroundTasks,
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Trigger a scheduled task manually.

    Available tasks:
    - full_analysis: Run complete SEO analysis
    - monitoring_cycle: Run monitoring checks
    - daily_summary: Send daily summary to Teams
    """
    valid_tasks = ["full_analysis", "monitoring_cycle", "daily_summary"]

    if request.task_name not in valid_tasks:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid task name. Valid tasks: {valid_tasks}",
        )

    async def run_task():
        if request.task_name == "full_analysis":
            agent = SEOAnalystAgent(context)
            task = AgentTask(
                agent_type=agent.agent_type,
                task_type="full_analysis",
                parameters=request.parameters,
            )
            await agent.run(task)

        elif request.task_name == "monitoring_cycle":
            agent = MonitoringAgent(context)
            task = AgentTask(
                agent_type=agent.agent_type,
                task_type="full_monitoring_cycle",
                parameters=request.parameters,
            )
            await agent.run(task)

        elif request.task_name == "daily_summary":
            agent = MonitoringAgent(context)
            task = AgentTask(
                agent_type=agent.agent_type,
                task_type="daily_summary",
                parameters={},
            )
            await agent.run(task)

    background_tasks.add_task(run_task)

    return {
        "status": "accepted",
        "task_name": request.task_name,
        "message": "Task scheduled for background execution",
    }


@router.post("/test-teams")
async def test_teams_integration(
    context: AgentContextDep,
    _api_key: ApiKeyDep,
) -> dict[str, Any]:
    """
    Test the Teams integration by sending a test message.
    """
    if not context.teams_notifier:
        raise HTTPException(
            status_code=400,
            detail="Teams webhook not configured",
        )

    from src.models.agents import Alert, AlertSeverity, AlertType

    alert = Alert(
        type=AlertType.AIO_DETECTED,
        severity=AlertSeverity.INFO,
        title="Test Alert from AI SEO Agent",
        message="This is a test message to verify Teams integration is working correctly.",
        data={"test": True},
    )

    success = await context.teams_notifier.send_alert(alert)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to send Teams message",
        )

    return {
        "success": True,
        "message": "Test alert sent to Teams",
    }
