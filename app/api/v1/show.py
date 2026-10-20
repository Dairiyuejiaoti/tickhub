from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.seat import SeatGenerateRequest, SeatResponse, SeatLockResponse
from app.services import seat_service, show_service, seat_lock_service

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.show import ShowCreateRequest, ShowResponse
from app.services import show_service

router = APIRouter(prefix="/api/v1/shows", tags=["场次"])


@router.post("", response_model=ShowResponse, status_code=201)
async def create_show(
    payload: ShowCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShowResponse:
    show = await show_service.create_show(db, payload.title, payload.venue, payload.start_time)
    return ShowResponse.model_validate(show)


@router.get("", response_model=list[ShowResponse])
async def list_shows(db: AsyncSession = Depends(get_db)) -> list[ShowResponse]:
    shows = await show_service.list_shows(db)
    return [ShowResponse.model_validate(s) for s in shows]

@router.post("/{show_id}/seats/generate", status_code=201)
async def generate_seats(
    show_id: int,
    payload: SeatGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    created = await seat_service.generate_seats(
        db, show_id, payload.rows, payload.cols, payload.price
    )
    return {"show_id": show_id, "created": created}


@router.get("/{show_id}/seats", response_model=list[SeatResponse])
async def list_seats(show_id: int, db: AsyncSession = Depends(get_db)) -> list[SeatResponse]:
    seats = await seat_service.list_seats(db, show_id)
    return [SeatResponse.model_validate(s) for s in seats]

@router.post("/{show_id}/seats/{seat_id}/lock", response_model=SeatLockResponse)
async def lock_seat(
    show_id: int,
    seat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SeatLockResponse:
    lock = await seat_lock_service.lock_seat(db, show_id, seat_id, current_user)
    return SeatLockResponse.model_validate(lock)
