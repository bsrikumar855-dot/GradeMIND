"""
Celery configuration for asynchronous job processing.
"""
import os
import sys
from celery import Celery

# Use Redis URL from environment or fallback to localhost
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "grademind_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.worker.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Standard settings for idempotency and late acks
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)

if (
    os.getenv("TESTING", "False").lower() in ("true", "1", "t")
    or "PYTEST_CURRENT_TEST" in os.environ
    or "pytest" in sys.modules
):
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )
