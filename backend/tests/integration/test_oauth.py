from urllib.parse import parse_qs, urlparse

import pytest


def _params(location: str) -> dict[str, str]:
    parsed = urlparse(location)
    return {k: v[0] for k, v in parse_qs(parsed.query).items()}


@pytest.mark.parametrize(
    ("provider", "userinfo"),
    [
        ("google", {"email": "googler@example.com", "name": "Googler", "oauth_id": "google-sub-123"}),
        ("github", {"email": "hubber@example.com", "name": "Hubber", "oauth_id": "999"}),
    ],
)
def test_oauth_callback_upserts_user_and_issues_tokens(client, monkeypatch, provider, userinfo):
    from app.services import oauth_service

    async def fake_fetch_userinfo(provider_arg, request):
        assert provider_arg == provider
        return userinfo

    monkeypatch.setattr(oauth_service, "fetch_userinfo", fake_fetch_userinfo)

    resp = client.get(f"/auth/oauth/{provider}/callback", follow_redirects=False)
    assert resp.status_code in (302, 307), resp.text
    params = _params(resp.headers["location"])
    assert "/oauth/callback" in resp.headers["location"]
    assert "access_token" in params

    me = client.get("/users/me", headers={"Authorization": f"Bearer {params['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == userinfo["email"]
    assert me.json()["oauth_provider"] == provider


def test_oauth_callback_upserts_same_user_on_repeat_login(client, monkeypatch):
    from app.services import oauth_service

    async def fake_fetch_userinfo(provider_arg, request):
        return {"email": "repeat@example.com", "name": "Repeat", "oauth_id": "repeat-1"}

    monkeypatch.setattr(oauth_service, "fetch_userinfo", fake_fetch_userinfo)

    first = client.get("/auth/oauth/google/callback", follow_redirects=False)
    second = client.get("/auth/oauth/google/callback", follow_redirects=False)
    first_params = _params(first.headers["location"])
    second_params = _params(second.headers["location"])

    first_me = client.get("/users/me", headers={"Authorization": f"Bearer {first_params['access_token']}"})
    second_me = client.get("/users/me", headers={"Authorization": f"Bearer {second_params['access_token']}"})
    assert first_me.json()["id"] == second_me.json()["id"]


def test_oauth_callback_rejects_missing_email(client, monkeypatch):
    from app.services import oauth_service

    async def fake_fetch_userinfo(provider_arg, request):
        return {"email": None, "name": "No Email", "oauth_id": "no-email-1"}

    monkeypatch.setattr(oauth_service, "fetch_userinfo", fake_fetch_userinfo)

    resp = client.get("/auth/oauth/google/callback", follow_redirects=False)
    assert resp.status_code in (302, 307)
    params = _params(resp.headers["location"])
    assert "error" in params


def test_oauth_login_redirects_to_provider(client):
    resp = client.get("/auth/oauth/google/login", follow_redirects=False)
    assert resp.status_code in (302, 307)


def test_oauth_unknown_provider_returns_404(client):
    resp = client.get("/auth/oauth/not-a-real-provider/login", follow_redirects=False)
    assert resp.status_code == 404
