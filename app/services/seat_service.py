from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import cache
from app.models.seat import Seat
from app.models.user import User
from app.repositories import seat_repository, show_repository
from app.schemas.seat import SeatItemResponse

SEAT_CACHE_TTL = 5  # 座位状态变化快，TTL 要短


def seat_list_key(show_id: int) -> str:
    """座位缓存键。集中定义，避免多处手写字符串导致失效不了。"""
    return f"seats:show:{show_id}"


async def invalidate_seat_cache(show_id: int) -> None:
    """座位状态变化后调用。Redis 故障不能影响主流程。"""
    try:
        await cache.delete(seat_list_key(show_id))
    except Exception:
        pass


async def _load_seat_rows(db: AsyncSession, show_id: int) -> list[dict]:
    """座位公共数据：先读缓存，未命中回源并回填。"""
    key = seat_list_key(show_id)

    try:
        cached = await cache.get_json(key)
        if cached is not None:
            return cached
    except Exception:
        pass  # 缓存故障 → 降级查库

    rows = await seat_repository.list_seats_with_locks(db, show_id, datetime.now())
    data = [
        {
            "id": seat.id,
            "seat_number": seat.seat_number,
            "price": str(seat.price),  # Decimal 不能直接进 JSON
            "status": seat.status,
            "lock_user_id": lock.user_id if lock else None,
            "lock_expire_at": lock.expire_at.isoformat() if lock else None,
        }
        for seat, lock in rows
    ]

    try:
        await cache.set_json(key, data, SEAT_CACHE_TTL)
    except Exception:
        pass
    return data


async def generate_seats(
    db: AsyncSession, show_id: int, rows: int, cols: int, price: Decimal
) -> int:
    show = await show_repository.get_show(db, show_id)
    if show is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场次不存在")

    existing = await seat_repository.count_seats(db, show_id)
    if existing > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="该场次座位已生成"
        )

    seats = [
        Seat(show_id=show_id, seat_number=f"{chr(65 + r)}{c}", price=price)
        for r in range(rows)
        for c in range(1, cols + 1)
    ]
    created = await seat_repository.bulk_create_seats(db, seats)
    await invalidate_seat_cache(show_id)  # 新座位要立刻可见
    return created


async def list_seats(db: AsyncSession, show_id: int) -> list[Seat]:
    show = await show_repository.get_show(db, show_id)
    if show is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场次不存在")

    return await seat_repository.list_seats(db, show_id)


async def list_seats_with_status(
    db: AsyncSession, show_id: int, user: User
) -> list[SeatItemResponse]:
    show = await show_repository.get_show(db, show_id)
    if show is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场次不存在")

    data = await _load_seat_rows(db, show_id)
    now = datetime.now()

    result: list[SeatItemResponse] = []
    for item in data:
        raw_expire = item["lock_expire_at"]
        expire_at = datetime.fromisoformat(raw_expire) if raw_expire else None
        # 是否被锁由过期时间实时判断，缓存里有旧锁也不会误判
        is_locked = expire_at is not None and expire_at > now
        result.append(
            SeatItemResponse(
                id=item["id"],
                seat_number=item["seat_number"],
                price=Decimal(item["price"]),
                status=item["status"],
                is_locked=is_locked,
                locked_by_me=bool(is_locked and item["lock_user_id"] == user.id),
                lock_expire_at=expire_at if is_locked else None,
            )
        )
    return result
