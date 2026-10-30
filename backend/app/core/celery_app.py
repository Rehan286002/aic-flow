from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "aic_flow",
    broker=settings.redis_url,
    include=["app.tasks.workflow_reminders"],
)

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "dispatch-workflow-deadline-reminders": {
            "task": "app.tasks.workflow_reminders.dispatch_due_notifications",
            "schedule": 900.0,
            "options": {"expires": 840},
        },
    },
)
