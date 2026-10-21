"""模型包：导入即完成全部表结构注册。

为什么必须在这里集中导入：模型之间有外键（如 seats.show_id → shows.id），
如果某个入口只导入了 Seat 而没导入 Show，SQLAlchemy 解析外键时会报
NoReferencedTableError。集中导入可以避免这种"谁先谁后"的导入顺序问题。
"""

from app.models.order import Order
from app.models.seat import Seat
from app.models.seat_lock import SeatLock
from app.models.show import Show
from app.models.user import User

__all__ = ["Order", "Seat", "SeatLock", "Show", "User"]
