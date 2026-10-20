import asyncio

from app.database import Base, engine
from app.models.user import User  # noqa: F401  ← 这行就是"登记"，别删
from app.models.show import Show  # noqa: F401
from app.models.seat import Seat  # noqa: F401
from app.models.seat_lock import SeatLock  # noqa: F401
from app.models.order import Order  # noqa: F401


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()  # 关闭连接池里的连接，避免退出时报 Event loop is closed


asyncio.run(main())
