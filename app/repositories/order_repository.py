import secrets
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.seat import Seat

from app.models.order import Order


def generate_order_no() -> str:
    """业务单号：时间戳 + 8 位随机，约 22 字符。"""
    return f"{datetime.now():%Y%m%d%H%M%S}{secrets.token_hex(4)}"


async def add_order(
    db: AsyncSession, user_id: int, seat_id: int, amount: Decimal
) -> Order:
    order = Order(
        order_no=generate_order_no(),
        user_id=user_id,
        seat_id=seat_id,
        amount=amount,
    )
    db.add(order)
    await db.flush()      # 只把 SQL 发出去拿 id，不提交事务
    return order


async def list_orders_by_user(
    db: AsyncSession, user_id: int, limit: int = 20, offset: int = 0
) -> list[tuple[Order, str]]:
    stmt = (
        select(Order, Seat.seat_number)
        .join(Seat, Seat.id == Order.seat_id)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.all())
