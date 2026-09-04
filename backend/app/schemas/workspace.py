import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.core.api_base import APIModel


class WorkspaceCreate(APIModel):
    name: str = Field(min_length=1, max_length=255)


class WorkspaceRead(APIModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: datetime


class WorkspaceWithRole(WorkspaceRead):
    role: str


class MemberInvite(APIModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^(owner|admin|member)$")


class MemberRoleUpdate(APIModel):
    role: str = Field(pattern="^(owner|admin|member)$")


class MemberRead(APIModel):
    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    role: str
    email: str | None = None
    name: str | None = None
