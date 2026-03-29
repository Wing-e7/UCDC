from fastapi.testclient import TestClient

from ucdc.consent_api import app as consent_app


def test_ui_index_served():
    with TestClient(consent_app) as client:
        r = client.get("/ui/")
        assert r.status_code == 200
        text = r.text.lower()
        assert "the staffer" in text
        assert "your 4-step flow" in text
        assert "your staffer on this device" in text


def test_public_config_exposes_urls_without_secrets():
    with TestClient(consent_app) as client:
        r = client.get("/public-config")
        assert r.status_code == 200
        data = r.json()
        assert "consent_base_url" in data
        assert "orchestrator_base_url" in data
        assert "agent_adapter_base_url" in data
        assert "default_agent_id" in data
        assert "staffer_local_bridge" in data
        assert data["staffer_local_bridge"] is False
        assert "jwt" not in str(data).lower()
