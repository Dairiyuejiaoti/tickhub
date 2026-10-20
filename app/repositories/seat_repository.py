from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.seat import Seat


async def count_seats(db: AsyncSession, show_id: int) -> int:
    result = await db.execute(
        select(func.count()).select_from(Seat).where(Seat.show_id == show_id)
    )
    return result.scalar_one()


async def bulk_create_seats(db: AsyncSession, seats: list[Seat]) -> int:
    db.add_all(seats)      # 一次性把一批对象交给 session
    await db.commit()      # 一条事务提交，比逐个 commit 快得多
    return len(seats)


async def list_seats(db: AsyncSession, show_id: int) -> list[Seat]:
    result = await db.execute(
        select(Seat).where(Seat.show_id == show_id).order_by(Seat.id)
    )
    return list(result.scalars().all())

async def get_seat(db: AsyncSession, seat_id: int) -> Seat | None:
    return await db.get(Seat, seat_id)
