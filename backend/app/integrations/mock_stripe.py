"""In-memory fake of the real `stripe` SDK's surface used when `settings.stripe_mock` is True
(the default - see stripe_client.py). It mirrors just enough of the real SDK's shape
(`customers.create`, `subscriptions.create/retrieve/modify`, `billing_portal.sessions.create`,
`construct_event`) that `app/services/billing_service.py` and `app/api/routes/webhooks.py` are
agnostic to which implementation is wired in - flipping to real Stripe later is an env-var
change (STRIPE_MOCK=false + STRIPE_SECRET_KEY), not a code change.

Webhook signatures are NOT stubbed: `sign_payload`/`construct_event` implement Stripe's real
signing scheme (`t=<ts>,v1=hmac_sha256(secret, f"{t}.{payload}")`), verified with
`hmac.compare_digest` to avoid timing attacks, exactly like the real SDK's `Webhook.construct_event`.
"""

import hashlib
import hmac
import json
import time
import uuid
from typing import Any


class SignatureVerificationError(Exception):
    """Raised when a webhook payload's signature does not match, its header is malformed, or
    its timestamp is stale - mirrors `stripe.error.SignatureVerificationError` closely enough
    that `webhooks.py` doesn't need to know which client is wired in."""


def _sign(secret: str, payload: str, timestamp: int | None = None) -> str:
    ts = timestamp if timestamp is not None else int(time.time())
    signed_payload = f"{ts}.{payload}"
    signature = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={signature}"


class _CustomersAPI:
    def __init__(self, client: "MockStripeClient") -> None:
        self._client = client

    def create(self, *, email: str | None = None, name: str | None = None, metadata: dict | None = None) -> dict:
        customer_id = f"cus_mock_{uuid.uuid4().hex[:16]}"
        customer = {
            "id": customer_id,
            "object": "customer",
            "email": email,
            "name": name,
            "metadata": metadata or {},
            "created": int(time.time()),
        }
        self._client._customers[customer_id] = customer
        return customer

    def retrieve(self, customer_id: str) -> dict:
        customer = self._client._customers.get(customer_id)
        if customer is None:
            raise KeyError(f"No such customer: {customer_id}")
        return customer


class _SubscriptionsAPI:
    def __init__(self, client: "MockStripeClient") -> None:
        self._client = client

    def create(self, *, customer: str, items: list[dict], **_kwargs: Any) -> dict:
        sub_id = f"sub_mock_{uuid.uuid4().hex[:16]}"
        now = int(time.time())
        plan = items[0].get("plan", "free") if items else "free"
        subscription = {
            "id": sub_id,
            "object": "subscription",
            "customer": customer,
            "status": "active",
            "plan": {"id": plan, "nickname": plan},
            "current_period_start": now,
            "current_period_end": now + 30 * 24 * 60 * 60,
            "cancel_at_period_end": False,
        }
        self._client._subscriptions[sub_id] = subscription
        return subscription

    def retrieve(self, subscription_id: str) -> dict:
        subscription = self._client._subscriptions.get(subscription_id)
        if subscription is None:
            raise KeyError(f"No such subscription: {subscription_id}")
        return subscription

    def modify(self, subscription_id: str, **updates: Any) -> dict:
        subscription = self.retrieve(subscription_id)
        if updates.get("cancel_at_period_end"):
            subscription["cancel_at_period_end"] = True
            subscription["status"] = "canceled"
        subscription.update({k: v for k, v in updates.items() if k != "cancel_at_period_end"})
        return subscription


class _BillingPortalSessionsAPI:
    def __init__(self, client: "MockStripeClient") -> None:
        self._client = client

    def create(self, *, customer: str, return_url: str) -> dict:
        session_id = f"bps_mock_{uuid.uuid4().hex[:16]}"
        return {
            "id": session_id,
            "object": "billing_portal.session",
            "customer": customer,
            "return_url": return_url,
            "url": f"https://billing.mock.stripe.local/session/{session_id}",
        }


class _BillingPortalAPI:
    def __init__(self, client: "MockStripeClient") -> None:
        self.sessions = _BillingPortalSessionsAPI(client)


class MockStripeClient:
    def __init__(self, webhook_secret: str) -> None:
        self.webhook_secret = webhook_secret
        self._customers: dict[str, dict] = {}
        self._subscriptions: dict[str, dict] = {}
        self.customers = _CustomersAPI(self)
        self.subscriptions = _SubscriptionsAPI(self)
        self.billing_portal = _BillingPortalAPI(self)

    def sign_payload(self, payload: str, timestamp: int | None = None) -> str:
        return _sign(self.webhook_secret, payload, timestamp)

    def construct_event(self, payload: str, sig_header: str, tolerance_seconds: int = 300) -> dict[str, Any]:
        try:
            parts = dict(item.split("=", 1) for item in sig_header.split(","))
            timestamp = int(parts["t"])
            provided_signature = parts["v1"]
        except (KeyError, ValueError) as exc:
            raise SignatureVerificationError("Malformed Stripe-Signature header") from exc

        signed_payload = f"{timestamp}.{payload}"
        expected_signature = hmac.new(self.webhook_secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_signature, provided_signature):
            raise SignatureVerificationError("Webhook signature does not match payload")

        if abs(time.time() - timestamp) > tolerance_seconds:
            raise SignatureVerificationError("Webhook timestamp is outside the tolerance window")

        return json.loads(payload)

    def emit_subscription_updated(
        self,
        *,
        subscription_id: str,
        status: str = "active",
        current_period_start: int | None = None,
        current_period_end: int | None = None,
    ) -> tuple[str, str]:
        """Test helper: builds and signs a `customer.subscription.updated` event the same way
        Stripe's real servers would, returning `(payload, signature_header)` ready to POST to
        `/webhooks/stripe` - so the full loop (subscribe -> simulated provider-side change ->
        webhook updates our DB) is genuinely exercised end to end."""
        now = int(time.time())
        obj = {
            "id": subscription_id,
            "object": "subscription",
            "status": status,
            "current_period_start": current_period_start if current_period_start is not None else now,
            "current_period_end": current_period_end if current_period_end is not None else now + 30 * 24 * 60 * 60,
        }
        event = {
            "id": f"evt_mock_{uuid.uuid4().hex[:16]}",
            "object": "event",
            "type": "customer.subscription.updated",
            "created": now,
            "data": {"object": obj},
        }
        payload = json.dumps(event)
        signature = self.sign_payload(payload)
        return payload, signature
