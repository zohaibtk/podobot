from fastapi import APIRouter

from app.api.v1.endpoints.agents import router as agents_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.briefs import router as briefs_router
from app.api.v1.endpoints.buffer import router as buffer_router
from app.api.v1.endpoints.captions import router as captions_router
from app.api.v1.endpoints.episodes import router as episodes_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.mcp import router as mcp_router
from app.api.v1.endpoints.media import router as media_router
from app.api.v1.endpoints.outlines import router as outlines_router
from app.api.v1.endpoints.profiles import router as profiles_router
from app.api.v1.endpoints.publishing_analytics import router as publishing_analytics_router
from app.api.v1.endpoints.publishing_operations import router as publishing_operations_router
from app.api.v1.endpoints.recordings import router as recordings_router
from app.api.v1.endpoints.research import router as research_router
from app.api.v1.endpoints.research_sources import router as research_sources_router
from app.api.v1.endpoints.schedules import router as schedules_router
from app.api.v1.endpoints.series import router as series_router
from app.api.v1.endpoints.settings import router as settings_router
from app.api.v1.endpoints.strategy import router as strategy_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(health_router, tags=["health"])
router.include_router(buffer_router)
router.include_router(analytics_router)
router.include_router(agents_router)
router.include_router(series_router)
router.include_router(episodes_router)
router.include_router(outlines_router)
router.include_router(briefs_router)
router.include_router(recordings_router)
router.include_router(research_router)
router.include_router(research_sources_router)
router.include_router(media_router)
router.include_router(captions_router)
router.include_router(schedules_router)
router.include_router(publishing_analytics_router)
router.include_router(publishing_operations_router)
router.include_router(profiles_router)
router.include_router(strategy_router)
router.include_router(mcp_router)
router.include_router(settings_router)
