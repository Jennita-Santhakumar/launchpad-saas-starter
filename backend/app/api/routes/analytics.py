import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace
from app.core.db import get_db
from app.core.models import WorkspaceMember
from app.core.rate_limit import limiter, workspace_key_func
from app.schemas.analytics import AnalyticsSummaryResponse, EventIngest, EventRead, EventTypeSummary, TimeseriesPoint
from app.services import analytics_service

router = APIRouter(prefix="/workspaces/{workspace_id}/analytics", tags=["analytics"])


@router.post("/events", response_model=EventRead, status_code=201)
@limiter.limit("100/minute", key_func=workspace_key_func)
def ingest_event(
    request: Request,
    workspace_id: uuid.UUID,
    body: EventIngest,
    member: WorkspaceMember = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> EventRead:
    event = analytics_service.ingest_event(db, workspace_id, body.event_type, body.metadata)
    return EventRead(id=event.id, event_type=event.event_type, metadata=event.event_metadata, created_at=event.created_at)


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_summary(
    workspace_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    member: WorkspaceMember = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> AnalyticsSummaryResponse:
    since = datetime.now(UTC) - timedelta(days=days)
    summary_rows = analytics_service.get_summary(db, workspace_id, since)
    timeseries_rows = analytics_service.get_timeseries(db, workspace_id, since)
    return AnalyticsSummaryResponse(
        summary=[EventTypeSummary(event_type=r.event_type, count=r.count) for r in summary_rows],
        timeseries=[TimeseriesPoint(day=r.day, count=r.count) for r in timeseries_rows],
    )
