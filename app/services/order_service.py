from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.user import User
from app.repositories import (
    order_repository,
    seat_lock_repository,
    seat_repository,
)


async def create_order(db: AsyncSession, seat_id: int, user: User) -> Order:
    seat = await seat_repository.get_seat(db, seat_id)
    if seat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "座位不存在")

    if seat.status == "sold":
        raise HTTPException(status.HTTP_409_CONFLICT, "座位已售出")

    lock = await seat_lock_repository.get_lock_by_seat(db, seat_id)
    if lock is None or lock.user_id != user.id or lock.expire_at <= datetime.now():
        raise HTTPException(status.HTTP_409_CONFLICT, "请先锁定该座位")

    # 三步操作在同一个事务里：写订单、座位售出、释放锁
    order = await order_repository.add_order(db, user.id, seat_id, seat.price)
    await seat_repository.mark_sold(db, seat)
    await seat_lock_repository.remove_lock(db, lock)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "该座位已售出")

    await db.refresh(order)
    return order
