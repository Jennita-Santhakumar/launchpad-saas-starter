def _signup(client, email, name="User"):
    resp = client.post("/auth/signup", json={"email": email, "password": "correct-horse-battery", "name": name})
    assert resp.status_code == 201, resp.text
    tokens = resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_workspace_creator_becomes_owner(client):
    headers = _signup(client, "owner@example.com")
    resp = client.post("/workspaces", json={"name": "Acme"}, headers=headers)
    assert resp.status_code == 201

    workspace_id = resp.json()["id"]
    members = client.get(f"/workspaces/{workspace_id}/members", headers=headers)
    assert members.status_code == 200
    roles = {m["role"] for m in members.json()}
    assert roles == {"owner"}


def test_list_my_workspaces_includes_role(client):
    headers = _signup(client, "lister@example.com")
    ws = client.post("/workspaces", json={"name": "Listed Co"}, headers=headers)
    workspace_id = ws.json()["id"]

    resp = client.get("/workspaces", headers=headers)
    assert resp.status_code == 200
    match = next(w for w in resp.json() if w["id"] == workspace_id)
    assert match["role"] == "owner"
    assert match["name"] == "Listed Co"


def test_get_workspace_detail(client):
    headers = _signup(client, "detail@example.com")
    ws = client.post("/workspaces", json={"name": "Detail Co"}, headers=headers)
    workspace_id = ws.json()["id"]

    resp = client.get(f"/workspaces/{workspace_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Detail Co"


def test_get_workspace_detail_404_for_non_member(client):
    owner_headers = _signup(client, "detail-owner@example.com")
    outsider_headers = _signup(client, "detail-outsider@example.com")
    ws = client.post("/workspaces", json={"name": "Secret Co"}, headers=owner_headers)
    workspace_id = ws.json()["id"]

    resp = client.get(f"/workspaces/{workspace_id}", headers=outsider_headers)
    assert resp.status_code == 404


def test_non_member_gets_404_not_403(client):
    owner_headers = _signup(client, "owner2@example.com")
    outsider_headers = _signup(client, "outsider@example.com")

    ws = client.post("/workspaces", json={"name": "Private Co"}, headers=owner_headers)
    workspace_id = ws.json()["id"]

    resp = client.get(f"/workspaces/{workspace_id}/members", headers=outsider_headers)
    assert resp.status_code == 404


def test_owner_can_invite_member_with_role(client):
    owner_headers = _signup(client, "owner3@example.com")
    _signup(client, "invitee@example.com", name="Invitee")

    ws = client.post("/workspaces", json={"name": "Team Co"}, headers=owner_headers)
    workspace_id = ws.json()["id"]

    invite = client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "invitee@example.com", "role": "member"},
        headers=owner_headers,
    )
    assert invite.status_code == 201
    assert invite.json()["role"] == "member"


def test_inviting_unknown_email_returns_400(client):
    owner_headers = _signup(client, "owner3b@example.com")
    ws = client.post("/workspaces", json={"name": "Team Co B"}, headers=owner_headers)
    workspace_id = ws.json()["id"]

    resp = client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "ghost@example.com", "role": "member"},
        headers=owner_headers,
    )
    assert resp.status_code == 400


def test_member_cannot_invite_others(client):
    owner_headers = _signup(client, "owner4@example.com")
    member_headers = _signup(client, "member4@example.com", name="Member")
    _signup(client, "outsider4@example.com")

    ws = client.post("/workspaces", json={"name": "Role Co"}, headers=owner_headers)
    workspace_id = ws.json()["id"]

    client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "member4@example.com", "role": "member"},
        headers=owner_headers,
    )

    resp = client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "outsider4@example.com", "role": "member"},
        headers=member_headers,
    )
    assert resp.status_code == 403


def test_owner_can_update_member_role_and_remove_member(client):
    owner_headers = _signup(client, "owner5@example.com")
    _signup(client, "member5@example.com", name="Member5")

    ws = client.post("/workspaces", json={"name": "Update Co"}, headers=owner_headers)
    workspace_id = ws.json()["id"]

    invited = client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "member5@example.com", "role": "member"},
        headers=owner_headers,
    )
    member_id = invited.json()["id"]

    updated = client.patch(
        f"/workspaces/{workspace_id}/members/{member_id}", json={"role": "admin"}, headers=owner_headers
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "admin"

    removed = client.delete(f"/workspaces/{workspace_id}/members/{member_id}", headers=owner_headers)
    assert removed.status_code == 204

    members = client.get(f"/workspaces/{workspace_id}/members", headers=owner_headers)
    member_ids = {m["id"] for m in members.json()}
    assert member_id not in member_ids
