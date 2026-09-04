from app.integrations.stripe_client import get_stripe_client


def _signup_and_subscribe(client, email):
    signup = client.post("/auth/signup", json={"email": email, "password": "correct-horse-battery", "name": "Owner"})
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    ws = client.post("/workspaces", json={"name": "Webhook Co"}, headers=headers)
    workspace_id = ws.json()["id"]
    sub = client.post(f"/workspaces/{workspace_id}/billing/subscribe", json={"plan": "pro"}, headers=headers)
    return headers, workspace_id, sub.json()["stripe_subscription_id"]


def test_valid_webhook_updates_subscription(client):
    headers, workspace_id, stripe_subscription_id = _signup_and_subscribe(client, "webhook1@example.com")

    stripe_client = get_stripe_client()
    payload, signature = stripe_client.emit_subscription_updated(
        subscription_id=stripe_subscription_id, status="past_due"
    )

    resp = client.post(
        "/webhooks/stripe",
        content=payload,
        headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text

    sub = client.get(f"/workspaces/{workspace_id}/billing", headers=headers)
    assert sub.json()["status"] == "past_due"


def test_webhook_for_unknown_subscription_is_a_no_op_200(client):
    stripe_client = get_stripe_client()
    payload, signature = stripe_client.emit_subscription_updated(subscription_id="sub_mock_unknown", status="active")

    resp = client.post(
        "/webhooks/stripe",
        content=payload,
        headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200


def test_webhook_rejects_invalid_signature(client):
    payload = '{"id": "evt_evil", "type": "customer.subscription.updated", "data": {"object": {"id": "sub_mock_x"}}}'
    resp = client.post(
        "/webhooks/stripe",
        content=payload,
        headers={"Stripe-Signature": "t=1,v1=deadbeef", "Content-Type": "application/json"},
    )
    assert resp.status_code == 400


def test_webhook_rejects_missing_signature(client):
    resp = client.post("/webhooks/stripe", content="{}", headers={"Content-Type": "application/json"})
    assert resp.status_code == 400


def test_webhook_rejects_tampered_payload(client):
    headers, workspace_id, stripe_subscription_id = _signup_and_subscribe(client, "webhook2@example.com")

    stripe_client = get_stripe_client()
    payload, signature = stripe_client.emit_subscription_updated(
        subscription_id=stripe_subscription_id, status="past_due"
    )
    tampered_payload = payload.replace("past_due", "active   ")

    resp = client.post(
        "/webhooks/stripe",
        content=tampered_payload,
        headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
    )
    assert resp.status_code == 400
