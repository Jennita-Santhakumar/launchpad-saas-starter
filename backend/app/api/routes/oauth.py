from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.db import get_db
from app.services import auth_service, oauth_service

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])
settings = get_settings()


@router.get("/{provider}/login")
async def oauth_login(provider: str, request: Request):
    client = oauth_service.get_client(provider)
    redirect_uri = f"{settings.oauth_redirect_base_url}/auth/oauth/{provider}/callback"
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback")
async def oauth_callback(provider: str, request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    """Completes the OAuth exchange, then hands off to the SPA the same way a form POST would:
    a redirect back to the frontend's callback route carrying the issued tokens (or an error
    message) as query params - the browser never sees a bare JSON response mid-flow."""
    callback_url = f"{settings.frontend_base_url}/oauth/callback"
    try:
        info = await oauth_service.fetch_userinfo(provider, request)
        if not info.get("email"):
            raise ValueError("OAuth provider did not return an email address")
        user = oauth_service.upsert_oauth_user(db, provider, info["email"], info["name"], info["oauth_id"])
        access, refresh = auth_service.issue_tokens(db, user)
    except Exception as exc:  # noqa: BLE001 - any failure in the exchange becomes a user-facing redirect, not a 500
        return RedirectResponse(f"{callback_url}?{urlencode({'error': str(exc)})}")
    return RedirectResponse(f"{callback_url}?{urlencode({'access_token': access, 'refresh_token': refresh})}")
