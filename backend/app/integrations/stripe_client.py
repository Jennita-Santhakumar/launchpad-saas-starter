"""Picks the real `stripe` SDK vs `MockStripeClient` based on `settings.stripe_mock`, exposing
one shared interface (`customers`, `subscriptions`, `billing_portal.sessions`,
`construct_event`) so `billing_service.py` and `webhooks.py` are agnostic to which is wired in.

`get_stripe_client()` is cached (a process-wide singleton): in mock mode, `MockStripeClient`
holds in-memory customer/subscription state that must persist across requests within a process
- a fresh instance per call would forget everything the moment it was created.
"""

from functools import lru_cache
from typing import Any

from app.config import get_settings
from app.integrations.mock_stripe import MockStripeClient


class _RealBillingPortalAPI:
    def __init__(self, stripe_module: Any) -> None:
        self.sessions = stripe_module.billing_portal.Session


class RealStripeClient:
    """Thin adapter over the real `stripe` SDK exposing the same surface as MockStripeClient.
    Only exercised when STRIPE_MOCK=false and a real STRIPE_SECRET_KEY is configured - not
    covered by this project's test suite (see README's documented trade-offs)."""

    def __init__(self, api_key: str, webhook_secret: str) -> None:
        import stripe

        stripe.api_key = api_key
        self._stripe = stripe
        self.webhook_secret = webhook_secret
        self.customers = stripe.Customer
        self.subscriptions = stripe.Subscription
        self.billing_portal = _RealBillingPortalAPI(stripe)

    def construct_event(self, payload: str, sig_header: str) -> dict:
        return self._stripe.Webhook.construct_event(payload, sig_header, self.webhook_secret)


@lru_cache
def get_stripe_client() -> MockStripeClient | RealStripeClient:
    settings = get_settings()
    if settings.stripe_mock:
        return MockStripeClient(webhook_secret=settings.stripe_webhook_secret)
    return RealStripeClient(api_key=settings.stripe_secret_key, webhook_secret=settings.stripe_webhook_secret)
