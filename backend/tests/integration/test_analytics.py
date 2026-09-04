def _signup_and_create_workspace(client, email):
    signup = client.post("/auth/signup", json={"email": email, "password": "correct-horse-battery", "name": "Owner"})
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    ws = client.post("/workspaces", json={"name": "Analytics Co"}, headers=headers)
    return headers, ws.json()["id"]


def test_event_ingestion_and_summary_aggregation(client):
    headers, workspace_id = _signup_and_create_workspace(client, "analytics1@example.com")

    for event_type in ("page_view", "page_view", "signup", "page_view"):
        resp = client.post(
            f"/workspaces/{workspace_id}/analytics/events",
            json={"event_type": event_type, "metadata": {"path": "/dashboard"}},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text

    summary_resp = client.get(f"/workspaces/{workspace_id}/analytics/summary", headers=headers)
    assert summary_resp.status_code == 200
    summary = {row["event_type"]: row["count"] for row in summary_resp.json()["summary"]}
    assert summary["page_view"] == 3
    assert summary["signup"] == 1


def test_analytics_timeseries_is_present(client):
    headers, workspace_id = _signup_and_create_workspace(client, "analytics2@example.com")
    client.post(
        f"/workspaces/{workspace_id}/analytics/events",
        json={"event_type": "page_view", "metadata": {}},
        headers=headers,
    )

    resp = client.get(f"/workspaces/{workspace_id}/analytics/summary", headers=headers)
    timeseries = resp.json()["timeseries"]
    assert len(timeseries) >= 1
    assert timeseries[0]["count"] >= 1


def test_event_metadata_round_trips_as_jsonb(client):
    headers, workspace_id = _signup_and_create_workspace(client, "analytics3@example.com")
    resp = client.post(
        f"/workspaces/{workspace_id}/analytics/events",
        json={"event_type": "purchase", "metadata": {"amount": 42, "currency": "usd"}},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["metadata"] == {"amount": 42, "currency": "usd"}


def test_analytics_isolated_per_workspace(client):
    headers_a, workspace_a = _signup_and_create_workspace(client, "analytics4a@example.com")
    headers_b, workspace_b = _signup_and_create_workspace(client, "analytics4b@example.com")

    client.post(
        f"/workspaces/{workspace_a}/analytics/events",
        json={"event_type": "only_in_a", "metadata": {}},
        headers=headers_a,
    )

    resp = client.get(f"/workspaces/{workspace_b}/analytics/summary", headers=headers_b)
    event_types = {row["event_type"] for row in resp.json()["summary"]}
    assert "only_in_a" not in event_types


def test_non_member_cannot_ingest_events(client):
    _headers_owner, workspace_id = _signup_and_create_workspace(client, "analytics5owner@example.com")
    outsider_signup = client.post(
        "/auth/signup",
        json={"email": "analytics5outsider@example.com", "password": "correct-horse-battery", "name": "Outsider"},
    )
    outsider_headers = {"Authorization": f"Bearer {outsider_signup.json()['access_token']}"}

    resp = client.post(
        f"/workspaces/{workspace_id}/analytics/events",
        json={"event_type": "page_view", "metadata": {}},
        headers=outsider_headers,
    )
    assert resp.status_code == 404
