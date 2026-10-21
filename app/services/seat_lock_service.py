from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.seat_lock import SeatLock
from app.models.user import User
from app.repositories import seat_lock_repository, seat_repository
from app.services.seat_service import invalidate_seat_cache
from app.utils.redis_lock import LockBusy, redis_lock

LOCK_MINUTES = 15
LOCK_TTL = 5  # 保护"查+插"这几毫秒，5 秒足够，崩溃也能自动释放


async def lock_seat(db: AsyncSession, show_id: int, seat_id: int, user: User) -> SeatLock:
    try:
        # 锁粒度 = 单个座位：买 A1 的人不会挡住买 B5 的人
        async with redis_lock(f"seat:lock:{seat_id}", ttl=LOCK_TTL):
            return await _lock_seat_inner(db, show_id, seat_id, user)
    except LockBusy:
        raise HTTPException(status.HTTP_409_CONFLICT, "操作过于频繁，请稍后重试")


async def _lock_seat_inner(
    db: AsyncSession, show_id: int, seat_id: int, user: User
) -> SeatLock:
    seat = await seat_repository.get_seat(db, seat_id)
    if seat is None or seat.show_id != show_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "座位不存在")

    if seat.status == "sold":
        raise HTTPException(status.HTTP_409_CONFLICT, "座位已售出")

    now = datetime.now()
    expire_at = now + timedelta(minutes=LOCK_MINUTES)

    existing = await seat_lock_repository.get_lock_by_seat(db, seat_id)
    if existing is not None:
        if existing.expire_at > now and existing.user_id != user.id:
            # 别人锁着且没过期：拒绝
            raise HTTPException(status.HTTP_409_CONFLICT, "座位已被他人锁定")
        # 自己的锁 → 续期；别人的锁已过期 → 接管
        lock = await seat_lock_repository.update_lock(db, existing, user.id, expire_at)
    else:
        try:
            lock = await seat_lock_repository.create_lock(db, user.id, seat_id, expire_at)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "座位已被他人锁定")

    # 锁状态变了，座位列表缓存要失效，否则前端还显示"可点"
    await invalidate_seat_cache(show_id)
    return lock


async def cleanup_expired_locks(db: AsyncSession) -> int:
    """清理过期锁。座位列表是按 expire_at 实时判断的，所以这里不必失效缓存。"""
    return await seat_lock_repository.delete_expired_locks(db, datetime.now())
