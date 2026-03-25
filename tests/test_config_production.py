import pytest

from ucdc.config import DEFAULT_JWT_SECRET, get_settings, validate_settings_for_startup


def test_production_rejects_default_jwt_secret(monkeypatch):
    monkeypatch.setenv("UCDC_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", DEFAULT_JWT_SECRET)
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            validate_settings_for_startup()
    finally:
        get_settings.cache_clear()
