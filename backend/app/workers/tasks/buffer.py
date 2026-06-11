import asyncio

from app.db.session import AsyncSessionLocal
from app.modules.schedules.buffer_service import BufferPublishingService
from app.workers.celery_app.app import celery_app
from app.workers.queues.names import PUBLISHING_QUEUE


@celery_app.task(name="buffer.channels.sync", queue=PUBLISHING_QUEUE)
def sync_buffer_channels() -> dict[str, int]:
    return asyncio.run(_sync_buffer_channels())


@celery_app.task(name="buffer.posts.retry_due", queue=PUBLISHING_QUEUE)
def retry_due_buffer_posts(limit: int = 25) -> dict[str, int]:
    return asyncio.run(_retry_due_buffer_posts(limit))


async def _sync_buffer_channels() -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        workspace = await BufferPublishingService(session).sync_channels()
        return {
            "channel_count": len(workspace["channels"]),
            "mapping_count": len(workspace["mappings"]),
        }


async def _retry_due_buffer_posts(limit: int) -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        return await BufferPublishingService(session).retry_due_posts(limit=limit)
