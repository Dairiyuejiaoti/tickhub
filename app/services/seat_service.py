from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.user import User
from app.schemas.seat import SeatItemResponse

from app.models.seat import Seat
from app.repositories import seat_repository, show_repository


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
    return await seat_repository.bulk_create_seats(db, seats)


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

    rows = await seat_repository.list_seats_with_locks(db, show_id, datetime.now())
    return [
        SeatItemResponse(
            id=seat.id,
            seat_number=seat.seat_number,
            price=seat.price,
            status=seat.status,
            is_locked=lock is not None,
            locked_by_me=bool(lock and lock.user_id == user.id),
            lock_expire_at=lock.expire_at if lock else None,
        )
        for seat, lock in rows
    ]