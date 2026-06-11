from sqlalchemy import text

from app.db.session import AsyncSessionLocal


async def check_database() -> str:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return "healthy"
    except Exception:
        return "failed"
