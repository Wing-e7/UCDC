from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings

# Used to reject production deployments that forget to rotate the dev placeholder.
DEFAULT_JWT_SECRET = "dev-change-me-dev-change-me-dev-change-me"


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/ucdc",
        validation_alias="DATABASE_URL",
    )
    jwt_secret: str = Field(
        default=DEFAULT_JWT_SECRET,
        validation_alias="JWT_SECRET",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias="JWT_ALGORITHM",
    )
    consent_issuer: str = Field(
        default="ucdc",
        validation_alias="CONSENT_ISSUER",
    )
    log_level: str = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
    )
    # "dev" | "test" allow placeholder JWT; "production" requires a non-default JWT_SECRET.
    ucdc_env: str = Field(default="dev", validation_alias="UCDC_ENV")
    agent_adapter_base_url: str = Field(
        default="http://127.0.0.1:8003",
        validation_alias="AGENT_ADAPTER_BASE_URL",
    )
    agent_adapter_timeout_seconds: float = Field(
        default=30.0,
        validation_alias="AGENT_ADAPTER_TIMEOUT_SECONDS",
    )
    # Comma-separated origins for browser demos (e.g. http://localhost:8001). Use "*" for dev only.
    cors_origins: str = Field(default="*", validation_alias="CORS_ORIGINS")
    # Run Alembic on startup. Keep enabled for one service only in Compose.
    run_db_migrations: bool = Field(default=True, validation_alias="RUN_DB_MIGRATIONS")
    # When true, POST /jobs returns 202 and a worker drains `queued` jobs (see job_worker).
    ucdc_async_jobs: bool = Field(default=False, validation_alias="UCDC_ASYNC_JOBS")
    # Used when no row exists in agent_entitlements for (user_id, agent_id).
    default_max_concurrent_jobs: int = Field(default=10, ge=1, validation_alias="UCDC_DEFAULT_MAX_CONCURRENT_JOBS")
    worker_poll_seconds: float = Field(default=1.0, ge=0.1, validation_alias="UCDC_WORKER_POLL_SECONDS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def cors_allow_origins() -> list[str]:
    raw = (get_settings().cors_origins or "").strip()
    if raw == "*" or not raw:
        return ["*"]
    return [p.strip() for p in raw.split(",") if p.strip()]


def validate_settings_for_startup() -> None:
    """Fail fast if production uses the dev JWT placeholder."""
    s = get_settings()
    if s.ucdc_env.lower() == "production" and s.jwt_secret == DEFAULT_JWT_SECRET:
        raise RuntimeError(
            "UCDC_ENV=production but JWT_SECRET is still the dev placeholder; set a strong JWT_SECRET."
        )

