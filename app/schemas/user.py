from pydantic import BaseModel, Field


class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=72)


class UserResponse(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}

class UserLoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
