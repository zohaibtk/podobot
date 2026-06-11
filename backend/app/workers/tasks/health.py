from app.workers.celery_app.app import celery_app


@celery_app.task(name="foundation.health.ping")
def ping() -> str:
    return "pong"
