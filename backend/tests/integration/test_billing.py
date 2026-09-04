def _signup_and_create_workspace(client, email):
    signup = client.post("/auth/signup", json={"email": email, "password": "correct-horse-battery", "name": "Owner"})
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    ws = client.post("/workspaces", json={"name": "Billing Co"}, headers=headers)
    return headers, ws.json()["id"]


def test_subscribe_creates_active_subscription(client):
    headers, workspace_id = _signup_and_create_workspace(client, "billing1@example.com")

    resp = client.post(f"/workspaces/{workspace_id}/billing/subscribe", json={"plan": "pro"}, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["plan"] == "pro"
    assert body["status"] == "active"
    assert body["stripe_subscription_id"].startswith("sub_mock_")
    assert body["stripe_customer_id"].startswith("cus_mock_")


def test_cancel_marks_subscription_canceled(client):
    headers, workspace_id = _signup_and_create_workspace(client, "billing2@example.com")
    client.post(f"/workspaces/{workspace_id}/billing/subscribe", json={"plan": "pro"}, headers=headers)

    resp = client.post(f"/workspaces/{workspace_id}/billing/cancel", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "canceled"


def test_cancel_without_subscription_returns_400(client):
    headers, workspace_id = _signup_and_create_workspace(client, "billing3@example.com")
    resp = client.post(f"/workspaces/{workspace_id}/billing/cancel", headers=headers)
    assert resp.status_code == 400


def test_portal_session_requires_existing_customer(client):
    headers, workspace_id = _signup_and_create_workspace(client, "billing4@example.com")
    resp = client.post(f"/workspaces/{workspace_id}/billing/portal", headers=headers)
    assert resp.status_code == 400


def test_portal_session_returns_url_after_subscribing(client):
    headers, workspace_id = _signup_and_create_workspace(client, "billing5@example.com")
    client.post(f"/workspaces/{workspace_id}/billing/subscribe", json={"plan": "pro"}, headers=headers)

    resp = client.post(f"/workspaces/{workspace_id}/billing/portal", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["url"].startswith("https://")


def test_non_admin_member_cannot_subscribe(client):
    owner_signup = client.post(
        "/auth/signup", json={"email": "billing6owner@example.com", "password": "correct-horse-battery", "name": "Owner"}
    )
    owner_headers = {"Authorization": f"Bearer {owner_signup.json()['access_token']}"}
    member_signup = client.post(
        "/auth/signup", json={"email": "billing6member@example.com", "password": "correct-horse-battery", "name": "Member"}
    )
    member_headers = {"Authorization": f"Bearer {member_signup.json()['access_token']}"}

    ws = client.post("/workspaces", json={"name": "Gated Co"}, headers=owner_headers)
    workspace_id = ws.json()["id"]
    client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "billing6member@example.com", "role": "member"},
        headers=owner_headers,
    )

    resp = client.post(f"/workspaces/{workspace_id}/billing/subscribe", json={"plan": "pro"}, headers=member_headers)
    assert resp.status_code == 403
