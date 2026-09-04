import uuid

from pydantic import EmailStr, Field

from app.core.api_base import APIModel


class SignupRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    name: str = Field(min_length=1, max_length=255)


class LoginRequest(APIModel):
    email: EmailStr
    password: str


class RefreshRequest(APIModel):
    refresh_token: str


class TokenResponse(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRead(APIModel):
    id: uuid.UUID
    email: str
    name: str
    oauth_provider: str | None = None
