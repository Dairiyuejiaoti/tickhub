from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.seat_lock import SeatLock
from app.models.user import User
from app.repositories import seat_lock_repository, seat_repository

LOCK_MINUTES = 15


async def lock_seat(db: AsyncSession, show_id: int, seat_id: int, user: User) -> SeatLock:
    seat = await seat_repository.get_seat(db, seat_id)
    if seat is None or seat.show_id != show_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "座位不存在")

    if seat.status == "sold":
        raise HTTPException(status.HTTP_409_CONFLICT, "座位已售出")

    now = datetime.now()
    expire_at = now + timedelta(minutes=LOCK_MINUTES)

    existing = await seat_lock_repository.get_lock_by_seat(db, seat_id)
    if existing is not None:
        if existing.user_id == user.id:
            # 自己锁的：续期
            return await seat_lock_repository.update_lock(db, existing, user.id, expire_at)
        if existing.expire_at > now:
            # 别人锁着且没过期：拒绝
            raise HTTPException(status.HTTP_409_CONFLICT, "座位已被他人锁定")
        # 别人的锁已过期：接管
        return await seat_lock_repository.update_lock(db, existing, user.id, expire_at)

    try:
        return await seat_lock_repository.create_lock(db, user.id, seat_id, expire_at)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "座位已被他人锁定")
