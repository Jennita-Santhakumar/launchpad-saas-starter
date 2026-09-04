from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Subscription, Workspace
from app.integrations.stripe_client import get_stripe_client


class BillingError(Exception):
    """Raised for any user-facing billing failure (no active subscription, no billing
    customer on record) - routes translate this into the appropriate HTTP status."""


def subscribe(db: Session, workspace: Workspace, plan: str) -> Subscription:
    client = get_stripe_client()
    subscription = db.execute(
        select(Subscription).where(Subscription.workspace_id == workspace.id)
    ).scalar_one_or_none()

    customer_id = subscription.stripe_customer_id if subscription else None
    if customer_id is None:
        customer = client.customers.create(name=workspace.name, metadata={"workspace_id": str(workspace.id)})
        customer_id = customer["id"]

    stripe_sub = client.subscriptions.create(customer=customer_id, items=[{"plan": plan}])

    if subscription is None:
        subscription = Subscription(workspace_id=workspace.id, plan=plan)
        db.add(subscription)

    subscription.plan = plan
    subscription.stripe_customer_id = customer_id
    subscription.stripe_subscription_id = stripe_sub["id"]
    subscription.status = stripe_sub["status"]
    subscription.current_period_start = datetime.fromtimestamp(stripe_sub["current_period_start"], tz=UTC)
    subscription.current_period_end = datetime.fromtimestamp(stripe_sub["current_period_end"], tz=UTC)
    db.commit()
    db.refresh(subscription)
    return subscription


def cancel(db: Session, workspace_id: UUID) -> Subscription:
    subscription = db.execute(
        select(Subscription).where(Subscription.workspace_id == workspace_id)
    ).scalar_one_or_none()
    if subscription is None or subscription.stripe_subscription_id is None:
        raise BillingError("No active subscription for this workspace")

    client = get_stripe_client()
    stripe_sub = client.subscriptions.modify(subscription.stripe_subscription_id, cancel_at_period_end=True)
    subscription.status = stripe_sub["status"]
    db.commit()
    db.refresh(subscription)
    return subscription


def create_portal_session(subscription: Subscription | None) -> str:
    if subscription is None or subscription.stripe_customer_id is None:
        raise BillingError("No billing customer on record for this workspace")
    client = get_stripe_client()
    session = client.billing_portal.sessions.create(
        customer=subscription.stripe_customer_id, return_url="http://localhost:5193/billing"
    )
    return session["url"]


def apply_subscription_updated_event(db: Session, event: dict) -> Subscription | None:
    obj = event["data"]["object"]
    subscription = db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == obj["id"])
    ).scalar_one_or_none()
    if subscription is None:
        return None
    subscription.status = obj["status"]
    subscription.current_period_start = datetime.fromtimestamp(obj["current_period_start"], tz=UTC)
    subscription.current_period_end = datetime.fromtimestamp(obj["current_period_end"], tz=UTC)
    db.commit()
    db.refresh(subscription)
    return subscription
