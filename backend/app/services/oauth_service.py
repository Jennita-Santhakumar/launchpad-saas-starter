from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.models import User

settings = get_settings()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
oauth.register(
    name="github",
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)


def get_client(provider: str):
    client = oauth.create_client(provider)
    if client is None:
        raise HTTPException(status_code=404, detail=f"Unknown OAuth provider: {provider}")
    return client


async def fetch_userinfo(provider: str, request: Request) -> dict:
    """Completes the authorization-code exchange and normalizes each provider's profile shape
    into {email, name, oauth_id}. Integration tests monkeypatch this function directly (rather
    than mocking every Authlib internal) with realistic provider-shaped payloads, so the upsert
    / JWT-issuance / conflict-handling code downstream is genuinely exercised without ever
    calling google.com or github.com."""
    client = get_client(provider)
    token = await client.authorize_access_token(request)

    if provider == "google":
        userinfo = token.get("userinfo")
        if userinfo is None:
            userinfo = await client.userinfo(token=token)
        return {
            "email": userinfo["email"],
            "name": userinfo.get("name") or userinfo["email"],
            "oauth_id": userinfo["sub"],
        }

    if provider == "github":
        profile_resp = await client.get("user", token=token)
        profile = profile_resp.json()
        email = profile.get("email")
        if not email:
            emails_resp = await client.get("user/emails", token=token)
            emails = emails_resp.json()
            primary = next((e for e in emails if e.get("primary")), emails[0] if emails else None)
            email = primary["email"] if primary else None
        return {
            "email": email,
            "name": profile.get("name") or profile.get("login"),
            "oauth_id": str(profile["id"]),
        }

    raise HTTPException(status_code=404, detail=f"Unknown OAuth provider: {provider}")


def upsert_oauth_user(db: Session, provider: str, email: str, name: str, oauth_id: str) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(email=email, name=name, oauth_provider=provider, oauth_id=oauth_id)
        db.add(user)
    else:
        user.oauth_provider = provider
        user.oauth_id = oauth_id
        user.name = name or user.name
    db.commit()
    db.refresh(user)
    return user
