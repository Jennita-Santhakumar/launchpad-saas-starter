import uuid
from datetime import datetime

from pydantic import Field

from app.core.api_base import APIModel


class SubscribeRequest(APIModel):
    plan: str = Field(pattern="^(free|pro|enterprise)$")


class SubscriptionRead(APIModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    plan: str
    status: str
    stripe_subscription_id: str | None
    stripe_customer_id: str | None
    current_period_start: datetime | None
    current_period_end: datetime | None


class PortalResponse(APIModel):
    url: str
