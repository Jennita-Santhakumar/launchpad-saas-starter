import uuid
from datetime import datetime

from pydantic import Field

from app.core.api_base import APIModel


class EventIngest(APIModel):
    event_type: str = Field(min_length=1, max_length=100)
    metadata: dict = Field(default_factory=dict)


class EventRead(APIModel):
    id: uuid.UUID
    event_type: str
    metadata: dict
    created_at: datetime


class EventTypeSummary(APIModel):
    event_type: str
    count: int


class TimeseriesPoint(APIModel):
    day: datetime
    count: int


class AnalyticsSummaryResponse(APIModel):
    summary: list[EventTypeSummary]
    timeseries: list[TimeseriesPoint]
