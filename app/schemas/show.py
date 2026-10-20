from datetime import datetime

from pydantic import BaseModel, Field


class ShowCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    venue: str = Field(min_length=1, max_length=100)
    start_time: datetime


class ShowResponse(BaseModel):
    id: int
    title: str
    venue: str
    start_time: datetime
    status: str

    model_config = {"from_attributes": True}
