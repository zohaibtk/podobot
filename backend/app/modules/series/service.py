from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import SeriesStatus
from app.modules.series.repository import SeriesRepository
from app.modules.series.schemas import SeriesCreateRequest, SeriesUpdateRequest
from app.schemas.pagination import OffsetParams, offset_meta


class SeriesService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = SeriesRepository(session)
        self.session = session

    async def list_series(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        status_filter: SeriesStatus | None = None,
        sort: str = "-created_at",
    ):
        pagination = OffsetParams(page=page, page_size=page_size)
        items, total = await self.repository.list(
            pagination=pagination,
            search=search,
            status=status_filter,
            sort=sort,
        )
        return {
            "items": items,
            **offset_meta(total=total, page=page, page_size=page_size),
        }

    async def get_series(self, series_id: UUID):
        series = await self.repository.get(series_id)
        if series is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Series not found",
            )
        return series

    async def create_series(self, payload: SeriesCreateRequest):
        series = await self.repository.create(payload)
        await self.session.commit()
        return series

    async def update_series(self, series_id: UUID, payload: SeriesUpdateRequest):
        series = await self.get_series(series_id)
        updated = await self.repository.update(series, payload)
        await self.session.commit()
        return updated

    async def delete_series(self, series_id: UUID) -> None:
        deleted = await self.repository.delete(series_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Series not found",
            )
        await self.session.commit()
