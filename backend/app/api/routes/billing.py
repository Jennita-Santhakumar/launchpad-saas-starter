import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, require_role
from app.core.db import get_db
from app.core.models import Subscription, WorkspaceMember
from app.schemas.billing import PortalResponse, SubscribeRequest, SubscriptionRead
from app.services import billing_service

router = APIRouter(prefix="/workspaces/{workspace_id}/billing", tags=["billing"])


@router.post("/subscribe", response_model=SubscriptionRead)
def subscribe(
    workspace_id: uuid.UUID,
    body: SubscribeRequest,
    member: WorkspaceMember = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db),
) -> SubscriptionRead:
    return billing_service.subscribe(db, member.workspace, body.plan)


@router.post("/cancel", response_model=SubscriptionRead)
def cancel(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db),
) -> SubscriptionRead:
    try:
        return billing_service.cancel(db, workspace_id)
    except billing_service.BillingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=SubscriptionRead | None)
def get_subscription(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> Subscription | None:
    return db.execute(select(Subscription).where(Subscription.workspace_id == workspace_id)).scalar_one_or_none()


@router.post("/portal", response_model=PortalResponse)
def portal(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db),
) -> PortalResponse:
    subscription = db.execute(select(Subscription).where(Subscription.workspace_id == workspace_id)).scalar_one_or_none()
    try:
        url = billing_service.create_portal_session(subscription)
    except billing_service.BillingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PortalResponse(url=url)
