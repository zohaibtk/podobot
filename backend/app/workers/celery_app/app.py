from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "podobot",
    broker=str(settings.redis_url),
    backend=str(settings.celery_result_backend_url),
    include=[
        "app.workers.tasks.buffer",
        "app.workers.tasks.health",
    ],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    timezone="UTC",
)
