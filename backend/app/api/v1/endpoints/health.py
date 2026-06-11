from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.db.health import check_database
from app.workers.celery_app.health import check_celery_broker

router = APIRouter()


class HealthResponse(BaseModel):
    service: str
    version: str
    status: str


class DependencyHealthResponse(HealthResponse):
    database: str
    redis: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        status="healthy",
    )


@router.get("/health/dependencies", response_model=DependencyHealthResponse)
async def dependency_health() -> DependencyHealthResponse:
    database_status = await check_database()
    redis_status = check_celery_broker()
    overall = (
        "healthy" if database_status == "healthy" and redis_status == "healthy" else "degraded"
    )

    return DependencyHealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        status=overall,
        database=database_status,
        redis=redis_status,
    )
