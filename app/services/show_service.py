from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from app import cache
from app.schemas.show import ShowResponse

from app.models.show import Show
from app.repositories import show_repository


async def create_show(db: AsyncSession, title: str, venue: str, start_time: datetime) -> Show:
    return await show_repository.create_show(db, title, venue, start_time)


async def list_shows(db: AsyncSession, limit: int = 20) -> list[Show]:
    return await show_repository.list_shows(db, limit)

SHOW_LIST_KEY = "shows:list"
SHOW_LIST_TTL = 60


async def list_shows(db: AsyncSession) -> list[dict]:
    # ① 先看缓存
    try:
        cached = await cache.get_json(SHOW_LIST_KEY)
        if cached is not None:
            return cached
    except Exception:
        pass          # Redis 挂了 → 降级查库，接口不能因此不可用

    # ② 回源查库
    shows = await show_repository.list_shows(db)
    data = [ShowResponse.model_validate(s).model_dump(mode="json") for s in shows]

    # ③ 回填缓存
    try:
        await cache.set_json(SHOW_LIST_KEY, data, SHOW_LIST_TTL)
    except Exception:
        pass
    return data


async def create_show(db: AsyncSession, title: str, venue: str, start_time) -> Show:
    show = await show_repository.create_show(db, title, venue, start_time)
    try:
        await cache.delete(SHOW_LIST_KEY)    # 写后删缓存，避免脏数据
    except Exception:
        pass
    return show
