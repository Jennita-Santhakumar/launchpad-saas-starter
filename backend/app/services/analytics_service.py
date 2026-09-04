from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from app.core.models import UsageEvent


def ingest_event(db: Session, workspace_id: UUID, event_type: str, metadata: dict) -> UsageEvent:
    event = UsageEvent(workspace_id=workspace_id, event_type=event_type, event_metadata=metadata)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_summary(db: Session, workspace_id: UUID, since: datetime | None = None) -> Sequence[Row]:
    query = select(UsageEvent.event_type, func.count().label("count")).where(UsageEvent.workspace_id == workspace_id)
    if since is not None:
        query = query.where(UsageEvent.created_at >= since)
    query = query.group_by(UsageEvent.event_type).order_by(func.count().desc())
    return db.execute(query).all()


def get_timeseries(db: Session, workspace_id: UUID, since: datetime | None = None) -> Sequence[Row]:
    day = func.date_trunc("day", UsageEvent.created_at).label("day")
    query = select(day, func.count().label("count")).where(UsageEvent.workspace_id == workspace_id)
    if since is not None:
        query = query.where(UsageEvent.created_at >= since)
    query = query.group_by(day).order_by(day)
    return db.execute(query).all()
