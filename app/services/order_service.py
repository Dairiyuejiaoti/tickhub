from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.order import OrderItemResponse
from app.models.user import User


from app.models.order import Order
from app.models.user import User
from app.repositories import (
    order_repository,
    seat_lock_repository,
    seat_repository,
)
from app.services.seat_service import invalidate_seat_cache


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
    # 座位已变成 sold、锁已删除，座位图缓存必须失效
    await invalidate_seat_cache(seat.show_id)
    return order

async def list_my_orders(
    db: AsyncSession, user: User, limit: int = 20, offset: int = 0
) -> list[OrderItemResponse]:
    rows = await order_repository.list_orders_by_user(db, user.id, limit, offset)
    return [
        OrderItemResponse(
            id=order.id,
            order_no=order.order_no,
            seat_id=order.seat_id,
            amount=order.amount,
            status=order.status,
            created_at=order.created_at,
            seat_number=seat_number,
        )
        for order, seat_number in rows
    ]
