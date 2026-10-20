from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.seat_lock import SeatLock


async def get_lock_by_seat(db: AsyncSession, seat_id: int) -> SeatLock | None:
    result = await db.execute(select(SeatLock).where(SeatLock.seat_id == seat_id))
    return result.scalar_one_or_none()


async def create_lock(
    db: AsyncSession, user_id: int, seat_id: int, expire_at: datetime
) -> SeatLock:
    lock = SeatLock(user_id=user_id, seat_id=seat_id, expire_at=expire_at)
    db.add(lock)
    await db.commit()
    await db.refresh(lock)
    return lock


async def update_lock(
    db: AsyncSession, lock: SeatLock, user_id: int, expire_at: datetime
) -> SeatLock:
    lock.user_id = user_id
    lock.expire_at = expire_at
    await db.commit()
    await db.refresh(lock)
    return lock
