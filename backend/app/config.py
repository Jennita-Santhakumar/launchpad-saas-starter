from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    # Database
    database_url: str = "postgresql+psycopg://orbit:orbit@localhost:5432/orbit"

    # Redis (rate-limit storage backend)
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 14

    # OAuth (empty defaults are fine - provider login routes simply won't be usable until set)
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    oauth_redirect_base_url: str = "http://localhost:8020"
    frontend_base_url: str = "http://localhost:5193"

    # Billing (Stripe is mocked by default - see app/integrations/mock_stripe.py)
    stripe_mock: bool = True
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = "whsec_mock_test_secret"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5193"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
