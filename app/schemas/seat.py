from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


class SeatGenerateRequest(BaseModel):
    rows: int = Field(default=2, ge=1, le=26, description="排数，1-26 对应 A-Z")
    cols: int = Field(default=5, ge=1, le=50, description="每排座位数")
    price: Decimal = Field(default=Decimal("100.00"), gt=0)


class SeatResponse(BaseModel):
    id: int
    seat_number: str
    price: Decimal
    status: str

    model_config = {"from_attributes": True}

class SeatLockResponse(BaseModel):
    seat_id: int
    expire_at: datetime
    user_id: int

    model_config = {"from_attributes": True}

class SeatItemResponse(SeatResponse):
    is_locked: bool = False
    locked_by_me: bool = False
    lock_expire_at: datetime | None = None
