from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import User, Workspace, WorkspaceMember


class WorkspaceError(Exception):
    """Raised for any user-facing workspace-membership failure (unknown invitee, duplicate
    membership, missing member) - routes translate this into the appropriate HTTP status."""


def create_workspace(db: Session, owner: User, name: str) -> Workspace:
    workspace = Workspace(name=name, owner_id=owner.id)
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role="owner"))
    db.commit()
    db.refresh(workspace)
    return workspace


def list_my_workspaces(db: Session, user_id: UUID) -> list[WorkspaceMember]:
    """Returns the caller's own WorkspaceMember rows (not bare Workspaces), so the route can
    include the caller's role alongside each workspace without a second query per row."""
    return (
        db.execute(select(WorkspaceMember).where(WorkspaceMember.user_id == user_id))
        .scalars()
        .all()
    )


def list_members(db: Session, workspace_id: UUID) -> list[WorkspaceMember]:
    return db.execute(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)).scalars().all()


def invite_member(db: Session, workspace_id: UUID, email: str, role: str) -> WorkspaceMember:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        raise WorkspaceError(f"No user registered with email {email}")
    existing = db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.id
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise WorkspaceError("User is already a member of this workspace")
    member = WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def update_member_role(db: Session, workspace_id: UUID, member_id: UUID, role: str) -> WorkspaceMember:
    member = db.get(WorkspaceMember, member_id)
    if member is None or member.workspace_id != workspace_id:
        raise WorkspaceError("Member not found")
    member.role = role
    db.commit()
    db.refresh(member)
    return member


def remove_member(db: Session, workspace_id: UUID, member_id: UUID) -> None:
    member = db.get(WorkspaceMember, member_id)
    if member is None or member.workspace_id != workspace_id:
        raise WorkspaceError("Member not found")
    if member.role == "owner":
        raise WorkspaceError("Cannot remove the workspace owner")
    db.delete(member)
    db.commit()
