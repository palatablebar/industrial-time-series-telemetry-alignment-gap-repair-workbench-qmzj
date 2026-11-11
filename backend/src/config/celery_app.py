"""Celery app used by backend (producer) and worker (consumer)."""
from celery import Celery

from src.config.settings import settings

celery_app = Celery(
    "tsalign",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["src.tasks.run_alignment"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    worker_hijack_root_logger=False,
    task_acks_late=False,
)

app = celery_app
celery = celery_app
