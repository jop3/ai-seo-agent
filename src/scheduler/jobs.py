"""
Scheduled jobs for automated SEO monitoring.

Uses APScheduler for reliable job scheduling with persistence.
"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Callable

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pydantic import BaseModel

from src.config import get_settings

logger = structlog.get_logger()


class JobType(str, Enum):
    """Types of scheduled jobs."""

    FULL_ANALYSIS = "full_analysis"
    AIO_CHECK = "aio_check"
    TRAFFIC_MONITOR = "traffic_monitor"
    COMPETITOR_CHECK = "competitor_check"
    MULTI_ENGINE_CHECK = "multi_engine_check"
    TECHNICAL_AUDIT = "technical_audit"


class ScheduledJob(BaseModel):
    """Configuration for a scheduled job."""

    id: str
    job_type: JobType
    name: str
    description: str
    cron: str | None = None  # Cron expression (e.g., "0 6 * * *" for 6am daily)
    interval_hours: int | None = None  # Or interval in hours
    enabled: bool = True
    parameters: dict[str, Any] = {}
    last_run: datetime | None = None
    next_run: datetime | None = None


# Default job configurations
DEFAULT_JOBS = [
    ScheduledJob(
        id="daily_analysis",
        job_type=JobType.FULL_ANALYSIS,
        name="Daily SEO Analysis",
        description="Full SEO analysis including AIO detection and traffic changes",
        cron="0 6 * * *",  # 6am daily
        parameters={"query_limit": 500},
    ),
    ScheduledJob(
        id="hourly_traffic",
        job_type=JobType.TRAFFIC_MONITOR,
        name="Hourly Traffic Monitor",
        description="Check for significant traffic anomalies",
        interval_hours=1,
        parameters={"threshold_percent": 30},
    ),
    ScheduledJob(
        id="aio_check_4h",
        job_type=JobType.AIO_CHECK,
        name="AIO Status Check",
        description="Check top queries for AI Overview presence",
        interval_hours=4,
        parameters={"query_limit": 100},
    ),
    ScheduledJob(
        id="competitor_daily",
        job_type=JobType.COMPETITOR_CHECK,
        name="Daily Competitor Check",
        description="Monitor competitor AIO citations and rankings",
        cron="0 7 * * *",  # 7am daily
        parameters={},
    ),
    ScheduledJob(
        id="multi_engine_daily",
        job_type=JobType.MULTI_ENGINE_CHECK,
        name="Multi-Engine Check",
        description="Check presence in Perplexity, ChatGPT, Bing Copilot",
        cron="0 8 * * *",  # 8am daily
        parameters={"engines": ["perplexity", "chatgpt", "bing_copilot"]},
    ),
    ScheduledJob(
        id="weekly_audit",
        job_type=JobType.TECHNICAL_AUDIT,
        name="Weekly Technical Audit",
        description="Full technical SEO audit",
        cron="0 3 * * 0",  # 3am Sundays
        parameters={"max_pages": 1000},
    ),
]


class JobScheduler:
    """
    Manages scheduled SEO monitoring jobs.

    Supports both cron expressions and interval-based scheduling.
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            job_defaults={"coalesce": True, "max_instances": 1},
        )
        self.jobs: dict[str, ScheduledJob] = {}
        self._handlers: dict[JobType, Callable] = {}

    def register_handler(self, job_type: JobType, handler: Callable):
        """Register a handler function for a job type."""
        self._handlers[job_type] = handler
        logger.info("Registered job handler", job_type=job_type.value)

    async def _execute_job(self, job_id: str):
        """Execute a scheduled job."""
        job = self.jobs.get(job_id)
        if not job:
            logger.error("Job not found", job_id=job_id)
            return

        handler = self._handlers.get(job.job_type)
        if not handler:
            logger.error("No handler for job type", job_type=job.job_type.value)
            return

        logger.info("Executing scheduled job", job_id=job_id, job_type=job.job_type.value)

        try:
            job.last_run = datetime.utcnow()

            # Execute handler (could be sync or async)
            if asyncio.iscoroutinefunction(handler):
                result = await handler(job.parameters)
            else:
                result = handler(job.parameters)

            logger.info(
                "Job completed successfully",
                job_id=job_id,
                result_summary=str(result)[:200] if result else None,
            )

        except Exception as e:
            logger.error("Job failed", job_id=job_id, error=str(e))
            # Could add alerting here

    def add_job(self, job: ScheduledJob) -> bool:
        """Add a job to the scheduler."""
        if not job.enabled:
            logger.info("Skipping disabled job", job_id=job.id)
            return False

        self.jobs[job.id] = job

        # Create trigger
        if job.cron:
            trigger = CronTrigger.from_crontab(job.cron)
        elif job.interval_hours:
            trigger = IntervalTrigger(hours=job.interval_hours)
        else:
            logger.error("Job has no schedule", job_id=job.id)
            return False

        # Add to APScheduler
        self.scheduler.add_job(
            self._execute_job,
            trigger=trigger,
            args=[job.id],
            id=job.id,
            name=job.name,
            replace_existing=True,
        )

        # Update next run time
        apscheduler_job = self.scheduler.get_job(job.id)
        if apscheduler_job:
            job.next_run = apscheduler_job.next_run_time

        logger.info(
            "Added scheduled job",
            job_id=job.id,
            name=job.name,
            next_run=job.next_run.isoformat() if job.next_run else None,
        )

        return True

    def remove_job(self, job_id: str) -> bool:
        """Remove a job from the scheduler."""
        if job_id in self.jobs:
            del self.jobs[job_id]

        try:
            self.scheduler.remove_job(job_id)
            logger.info("Removed job", job_id=job_id)
            return True
        except Exception:
            return False

    def get_jobs(self) -> list[ScheduledJob]:
        """Get all configured jobs."""
        # Update next run times
        for job_id, job in self.jobs.items():
            apscheduler_job = self.scheduler.get_job(job_id)
            if apscheduler_job:
                job.next_run = apscheduler_job.next_run_time
        return list(self.jobs.values())

    def run_now(self, job_id: str) -> bool:
        """Trigger immediate execution of a job."""
        if job_id not in self.jobs:
            return False

        # Schedule for immediate execution
        self.scheduler.add_job(
            self._execute_job,
            "date",  # One-time trigger
            args=[job_id],
            id=f"{job_id}_manual",
        )

        logger.info("Triggered manual job execution", job_id=job_id)
        return True

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started", job_count=len(self.jobs))

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def load_default_jobs(self):
        """Load default job configurations."""
        for job in DEFAULT_JOBS:
            self.add_job(job)


# Global scheduler instance
_scheduler: JobScheduler | None = None


def get_scheduler() -> JobScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = JobScheduler()
    return _scheduler
