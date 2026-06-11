from app.workers.celery_app.app import celery_app


def check_celery_broker() -> str:
    try:
        with celery_app.connection_for_read() as connection:
            connection.ensure_connection(max_retries=1)
        return "healthy"
    except Exception:
        return "failed"
