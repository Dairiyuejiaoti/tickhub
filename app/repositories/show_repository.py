from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.show import Show


async def create_show(db: AsyncSession, title: str, venue: str, start_time: datetime) -> Show:
    show = Show(title=title, venue=venue, start_time=start_time)
    db.add(show)
    await db.commit()
    await db.refresh(show)
    return show


async def list_shows(db: AsyncSession, limit: int = 20) -> list[Show]:
    result = await db.execute(select(Show).order_by(Show.start_time).limit(limit))
    return list(result.scalars().all())

async def get_show(db: AsyncSession, show_id: int) -> Show | None:
    return await db.get(Show, show_id)
