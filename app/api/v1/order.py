from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.order import OrderCreateRequest, OrderResponse
from app.services import order_service

router = APIRouter(prefix="/api/v1/orders", tags=["订单"])


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    payload: OrderCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    order = await order_service.create_order(db, payload.seat_id, current_user)
    return OrderResponse.model_validate(order)
