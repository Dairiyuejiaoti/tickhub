from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.show import Show
from app.repositories import show_repository


async def create_show(db: AsyncSession, title: str, venue: str, start_time: datetime) -> Show:
    return await show_repository.create_show(db, title, venue, start_time)


async def list_shows(db: AsyncSession, limit: int = 20) -> list[Show]:
    return await show_repository.list_shows(db, limit)
