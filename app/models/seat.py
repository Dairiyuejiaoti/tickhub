from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (UniqueConstraint("show_id", "seat_number", name="uq_show_seat"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"))
    seat_number: Mapped[str] = mapped_column(String(20))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), server_default="available")
