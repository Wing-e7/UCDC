from fastapi.testclient import TestClient

from ucdc.consent_api import app as consent_app


def test_ui_index_served():
    with TestClient(consent_app) as client:
        r = client.get("/ui/")
        assert r.status_code == 200
        text = r.text.lower()
        assert "mission control" in text
        assert "trust pact activation flow" in text
