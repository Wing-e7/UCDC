"""Local Staffer subprocess bridge (opt-in via env)."""

import sys

from fastapi.testclient import TestClient

from ucdc.consent_api import app as consent_app


def test_local_staffer_status_off_when_not_configured():
    with TestClient(consent_app) as client:
        r = client.get("/local-staffer/status")
        assert r.status_code == 200
        body = r.json()
        assert body["enabled"] is False
        assert body["repo_path"] is None


def test_local_staffer_posts_return_503_when_disabled():
    with TestClient(consent_app) as client:
        for path in ("/local-staffer/setup", "/local-staffer/setup-new", "/local-staffer/execute"):
            r = client.post(path)
            assert r.status_code == 503


def test_local_staffer_setup_runs_stub(monkeypatch, tmp_path):
    stub = tmp_path / "stub.py"
    stub.write_text("print('ok')\n")
    monkeypatch.setenv("UCDC_ENABLE_STAFFER_LOCAL_BRIDGE", "true")
    monkeypatch.setenv("STAFFER_LOCAL_REPO", str(tmp_path))
    monkeypatch.setenv("UCDC_STAFFER_CMD_SETUP", f"{sys.executable} stub.py")

    with TestClient(consent_app) as client:
        r = client.post("/local-staffer/setup")
        assert r.status_code == 200
        out = r.json()
        assert out["ok"] is True
        assert out["returncode"] == 0
        assert "ok" in out["stdout"]
