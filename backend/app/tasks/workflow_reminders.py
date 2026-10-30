from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.workflow_reminder_service import run_due_reminder_cycle

logger = get_task_logger(__name__)


@celery_app.task(
    name="app.tasks.workflow_reminders.dispatch_due_notifications",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
    acks_late=True,
)
def dispatch_due_notifications(self) -> dict[str, int]:
    """Run one idempotent deadline reminder and escalation cycle."""
    db = SessionLocal()
    try:
        result = run_due_reminder_cycle(db)
        logger.info("Workflow reminder cycle completed: %s", result)
        return result
    finally:
        db.close()
