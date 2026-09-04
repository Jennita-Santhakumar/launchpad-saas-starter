import json

import pytest

from app.integrations.mock_stripe import MockStripeClient, SignatureVerificationError


@pytest.fixture
def stripe_client() -> MockStripeClient:
    return MockStripeClient(webhook_secret="whsec_test_secret")


def test_customer_and_subscription_lifecycle(stripe_client):
    customer = stripe_client.customers.create(email="a@b.com", name="Acme")
    assert customer["id"].startswith("cus_mock_")

    subscription = stripe_client.subscriptions.create(customer=customer["id"], items=[{"plan": "pro"}])
    assert subscription["id"].startswith("sub_mock_")
    assert subscription["status"] == "active"

    retrieved = stripe_client.subscriptions.retrieve(subscription["id"])
    assert retrieved["id"] == subscription["id"]

    canceled = stripe_client.subscriptions.modify(subscription["id"], cancel_at_period_end=True)
    assert canceled["status"] == "canceled"
    assert canceled["cancel_at_period_end"] is True


def test_subscription_retrieve_unknown_id_raises(stripe_client):
    with pytest.raises(KeyError):
        stripe_client.subscriptions.retrieve("sub_mock_does_not_exist")


def test_billing_portal_session_create(stripe_client):
    session = stripe_client.billing_portal.sessions.create(customer="cus_mock_1", return_url="https://example.com")
    assert session["url"].startswith("https://")


def test_sign_and_construct_event_round_trip(stripe_client):
    payload = json.dumps({"id": "evt_1", "type": "customer.subscription.updated"})
    signature = stripe_client.sign_payload(payload)
    event = stripe_client.construct_event(payload, signature)
    assert event["id"] == "evt_1"


def test_construct_event_rejects_tampered_payload(stripe_client):
    payload = json.dumps({"id": "evt_1"})
    signature = stripe_client.sign_payload(payload)
    tampered_payload = json.dumps({"id": "evt_evil"})
    with pytest.raises(SignatureVerificationError):
        stripe_client.construct_event(tampered_payload, signature)


def test_construct_event_rejects_wrong_secret(stripe_client):
    other_client = MockStripeClient(webhook_secret="whsec_other_secret")
    payload = json.dumps({"id": "evt_1"})
    signature = other_client.sign_payload(payload)
    with pytest.raises(SignatureVerificationError):
        stripe_client.construct_event(payload, signature)


def test_construct_event_rejects_malformed_header(stripe_client):
    with pytest.raises(SignatureVerificationError):
        stripe_client.construct_event("{}", "not-a-signature-header")


def test_construct_event_rejects_stale_timestamp(stripe_client):
    payload = json.dumps({"id": "evt_1"})
    old_signature = stripe_client.sign_payload(payload, timestamp=1)
    with pytest.raises(SignatureVerificationError):
        stripe_client.construct_event(payload, old_signature)


def test_emit_subscription_updated_is_self_consistent(stripe_client):
    payload, signature = stripe_client.emit_subscription_updated(subscription_id="sub_mock_abc", status="past_due")
    event = stripe_client.construct_event(payload, signature)
    assert event["type"] == "customer.subscription.updated"
    assert event["data"]["object"]["status"] == "past_due"
