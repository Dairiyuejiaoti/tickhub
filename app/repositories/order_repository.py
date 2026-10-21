import secrets
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

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
