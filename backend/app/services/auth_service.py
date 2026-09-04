from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.models import RefreshToken, User
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)

settings = get_settings()


class AuthError(Exception):
    """Raised for any user-facing auth failure (bad credentials, duplicate email, revoked
    refresh token) - routes translate this into the appropriate HTTP status."""


def signup(db: Session, email: str, password: str, name: str) -> User:
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing is not None:
        raise AuthError("Email already registered")
    user = User(email=email, name=name, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or user.password_hash is None or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password")
    return user


def issue_tokens(db: Session, user: User) -> tuple[str, str]:
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_expire_days)
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh), expires_at=expires_at))
    db.commit()
    return access, refresh


def rotate_refresh_token(db: Session, refresh_token: str) -> tuple[str, str]:
    """Redeems a refresh token for a new access/refresh pair, rotating on use: the presented
    token is marked revoked in the same transaction that issues its replacement, so any later
    replay of it (e.g. a stolen token used after the legitimate client already rotated) fails."""
    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:
        raise AuthError("Invalid or expired refresh token") from exc
    if payload.get("type") != "refresh":
        raise AuthError("Invalid token type")

    token_hash = hash_token(refresh_token)
    record = db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).scalar_one_or_none()
    now = datetime.now(UTC)
    if record is None or record.revoked_at is not None or record.expires_at < now:
        raise AuthError("Refresh token has been revoked or expired")

    record.revoked_at = now
    user = db.get(User, UUID(payload["sub"]))
    if user is None:
        raise AuthError("User not found")

    access, new_refresh = issue_tokens(db, user)
    db.commit()
    return access, new_refresh
