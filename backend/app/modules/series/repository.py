from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.series.models import Series
from app.modules.series.schemas import SeriesCreateRequest, SeriesUpdateRequest
from app.schemas.pagination import OffsetParams

SERIES_SORTS = {
    "latest": Series.created_at.desc(),
    "updated_at": Series.updated_at.desc(),
    "-updated_at": Series.updated_at.desc(),
    "created_at": Series.created_at.desc(),
    "-created_at": Series.created_at.desc(),
    "name": Series.name.asc(),
    "-name": Series.name.desc(),
}


class SeriesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        *,
        pagination: OffsetParams,
        search: str | None = None,
        status: str | None = None,
        sort: str = "-created_at",
    ) -> tuple[list[Series], int]:
        statement = select(Series)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Series.name.ilike(pattern),
                    Series.audience.ilike(pattern),
                    Series.description.ilike(pattern),
                    Series.guest_name.ilike(pattern),
                )
            )
        if status:
            statement = statement.where(Series.status == status)

        count_statement = select(func.count()).select_from(statement.subquery())
        total = int((await self.session.execute(count_statement)).scalar_one() or 0)
        order_by = SERIES_SORTS.get(sort, Series.created_at.desc())
        result = await self.session.execute(
            statement.order_by(order_by, Series.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        return list(result.scalars().all()), total

    async def get(self, series_id: UUID) -> Series | None:
        return await self.session.get(Series, series_id)

    async def create(self, payload: SeriesCreateRequest) -> Series:
        series = Series(**payload.model_dump())
        self.session.add(series)
        await self.session.flush()
        await self.session.refresh(series)
        return series

    async def update(self, series: Series, payload: SeriesUpdateRequest) -> Series:
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(series, field, value)

        await self.session.flush()
        await self.session.refresh(series)
        return series

    async def delete(self, series_id: UUID) -> bool:
        result = await self.session.execute(delete(Series).where(Series.id == series_id))
        return bool(result.rowcount)
