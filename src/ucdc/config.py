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
    # Browser / third-party clients: URLs that resolve from the user machine (not Docker internal DNS).
    public_consent_base_url: str = Field(
        default="http://127.0.0.1:8001",
        validation_alias="UCDC_PUBLIC_CONSENT_BASE_URL",
    )
    public_orchestrator_base_url: str = Field(
        default="http://127.0.0.1:8002",
        validation_alias="UCDC_PUBLIC_ORCHESTRATOR_BASE_URL",
    )
    public_agent_adapter_base_url: str = Field(
        default="http://127.0.0.1:8003",
        validation_alias="UCDC_PUBLIC_AGENT_ADAPTER_BASE_URL",
    )
    # Default agent_id for demo UIs and external clients; must match what the adapter exposes.
    default_agent_id: str = Field(default="example-agent", validation_alias="UCDC_DEFAULT_AGENT_ID")
    # Optional: one-click Staffer CLI from /ui (subprocess in STAFFER_LOCAL_REPO). Off by default; never use in production.
    enable_staffer_local_bridge: bool = Field(default=False, validation_alias="UCDC_ENABLE_STAFFER_LOCAL_BRIDGE")
    staffer_local_repo: str = Field(default="", validation_alias="STAFFER_LOCAL_REPO")
    staffer_cmd_setup: str = Field(default="python run_config.py", validation_alias="UCDC_STAFFER_CMD_SETUP")
    staffer_cmd_setup_new: str = Field(
        default="python run_config.py --overwrite",
        validation_alias="UCDC_STAFFER_CMD_SETUP_NEW",
    )
    staffer_cmd_execute: str = Field(default="python main.py --fresh", validation_alias="UCDC_STAFFER_CMD_EXECUTE")
    staffer_cmd_timeout_setup: int = Field(default=600, ge=30, validation_alias="UCDC_STAFFER_CMD_TIMEOUT_SETUP")
    staffer_cmd_timeout_execute: int = Field(default=3600, ge=60, validation_alias="UCDC_STAFFER_CMD_TIMEOUT_EXECUTE")


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

