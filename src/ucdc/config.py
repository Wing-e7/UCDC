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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def validate_settings_for_startup() -> None:
    """Fail fast if production uses the dev JWT placeholder."""
    s = get_settings()
    if s.ucdc_env.lower() == "production" and s.jwt_secret == DEFAULT_JWT_SECRET:
        raise RuntimeError(
            "UCDC_ENV=production but JWT_SECRET is still the dev placeholder; set a strong JWT_SECRET."
        )

