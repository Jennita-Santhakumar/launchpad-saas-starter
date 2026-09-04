def test_signup_creates_user_and_returns_tokens(client):
    resp = client.post(
        "/auth/signup", json={"email": "new@example.com", "password": "correct-horse-battery", "name": "New User"}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "access_token" in body and "refresh_token" in body

    me = client.get("/users/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"


def test_signup_rejects_duplicate_email(client):
    payload = {"email": "dupe@example.com", "password": "correct-horse-battery", "name": "Dupe"}
    first = client.post("/auth/signup", json=payload)
    assert first.status_code == 201
    second = client.post("/auth/signup", json=payload)
    assert second.status_code == 409


def test_login_succeeds_with_correct_credentials(client):
    client.post("/auth/signup", json={"email": "login@example.com", "password": "correct-horse-battery", "name": "Login"})
    resp = client.post("/auth/login", json={"email": "login@example.com", "password": "correct-horse-battery"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_rejects_wrong_password(client):
    client.post(
        "/auth/signup", json={"email": "wrongpw@example.com", "password": "correct-horse-battery", "name": "WrongPw"}
    )
    resp = client.post("/auth/login", json={"email": "wrongpw@example.com", "password": "incorrect-password"})
    assert resp.status_code == 401


def test_login_rejects_unknown_email(client):
    resp = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever-password"})
    assert resp.status_code == 401


def test_refresh_rotates_token_and_old_one_is_rejected(client):
    signup = client.post(
        "/auth/signup", json={"email": "refresh@example.com", "password": "correct-horse-battery", "name": "Refresh"}
    )
    original_refresh = signup.json()["refresh_token"]

    refreshed = client.post("/auth/refresh", json={"refresh_token": original_refresh})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != original_refresh

    reused = client.post("/auth/refresh", json={"refresh_token": original_refresh})
    assert reused.status_code == 401


def test_refresh_rejects_garbage_token(client):
    resp = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401


def test_get_me_requires_authentication(client):
    resp = client.get("/users/me")
    assert resp.status_code == 401
