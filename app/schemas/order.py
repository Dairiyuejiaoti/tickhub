from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class OrderCreateRequest(BaseModel):
    seat_id: int


class OrderResponse(BaseModel):
    id: int
    order_no: str
    seat_id: int
    amount: Decimal
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
class OrderItemResponse(OrderResponse):
    seat_number: str
