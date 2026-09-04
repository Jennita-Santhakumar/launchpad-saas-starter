import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import analytics, auth, billing, oauth, users, webhooks, workspaces
from app.config import get_settings
from app.core.rate_limit import limiter

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("orbit")

app = FastAPI(
    title="Orbit",
    description="Multi-tenant SaaS starter kit: auth, billing, and usage analytics.",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Authlib's Starlette OAuth client stores the CSRF `state` param in the session between the
# /login redirect and the /callback exchange.
app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret_key)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(users.router)
app.include_router(workspaces.router)
app.include_router(billing.router)
app.include_router(webhooks.router)
app.include_router(analytics.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
