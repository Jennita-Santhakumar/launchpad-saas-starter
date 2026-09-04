import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace, require_role
from app.core.db import get_db
from app.core.models import User, WorkspaceMember
from app.schemas.workspace import (
    MemberInvite,
    MemberRead,
    MemberRoleUpdate,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceWithRole,
)
from app.services import workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _to_member_read(member: WorkspaceMember) -> MemberRead:
    return MemberRead(
        id=member.id,
        user_id=member.user_id,
        workspace_id=member.workspace_id,
        role=member.role,
        email=member.user.email,
        name=member.user.name,
    )


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(
    body: WorkspaceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> WorkspaceRead:
    return workspace_service.create_workspace(db, current_user, body.name)


@router.get("", response_model=list[WorkspaceWithRole])
def list_my_workspaces(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[WorkspaceWithRole]:
    memberships = workspace_service.list_my_workspaces(db, current_user.id)
    return [
        WorkspaceWithRole(
            id=m.workspace.id, name=m.workspace.name, owner_id=m.workspace.owner_id,
            created_at=m.workspace.created_at, role=m.role,
        )
        for m in memberships
    ]


@router.get("/{workspace_id}", response_model=WorkspaceRead)
def get_workspace(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> WorkspaceRead:
    return WorkspaceRead(
        id=member.workspace.id, name=member.workspace.name,
        owner_id=member.workspace.owner_id, created_at=member.workspace.created_at,
    )


@router.get("/{workspace_id}/members", response_model=list[MemberRead])
def list_members(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[MemberRead]:
    members = workspace_service.list_members(db, workspace_id)
    return [_to_member_read(m) for m in members]


@router.post("/{workspace_id}/members", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
def invite_member(
    workspace_id: uuid.UUID,
    body: MemberInvite,
    member: WorkspaceMember = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db),
) -> MemberRead:
    try:
        new_member = workspace_service.invite_member(db, workspace_id, body.email, body.role)
    except workspace_service.WorkspaceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_member_read(new_member)


@router.patch("/{workspace_id}/members/{member_id}", response_model=MemberRead)
def update_member_role(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    body: MemberRoleUpdate,
    member: WorkspaceMember = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db),
) -> MemberRead:
    try:
        updated = workspace_service.update_member_role(db, workspace_id, member_id, body.role)
    except workspace_service.WorkspaceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_member_read(updated)


@router.delete("/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db),
) -> None:
    try:
        workspace_service.remove_member(db, workspace_id, member_id)
    except workspace_service.WorkspaceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
