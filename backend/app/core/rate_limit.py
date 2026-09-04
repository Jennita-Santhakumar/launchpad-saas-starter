from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import get_settings

settings = get_settings()

# Redis-backed so limits survive multiple workers/restarts. Per-route limits (auth endpoints:
# per-IP via the default key_func; event ingestion: per-workspace via workspace_key_func below)
# are applied with `@limiter.limit(...)` in the route modules.
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)


def workspace_key_func(request: Request) -> str:
    """Rate-limit key for workspace-scoped endpoints (event ingestion) - limits apply
    per-workspace rather than per-IP so one busy tenant can't exhaust another's quota, and a
    shared NAT/proxy IP doesn't get penalized for many tenants at once."""
    workspace_id = request.path_params.get("workspace_id")
    return f"workspace:{workspace_id}" if workspace_id else get_remote_address(request)
