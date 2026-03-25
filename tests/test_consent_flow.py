from fastapi.testclient import TestClient

from ucdc.agent_adapter_api import app as adapter_app
from ucdc.consent_api import app as consent_app
from ucdc.orchestrator_api import app as orchestrator_app


def test_consent_to_job_happy_path(monkeypatch):
    def _fake_execute(base_url, consent_token, job_id, job_manifest, timeout_seconds=30.0):
        return {"job_id": job_id, "status": "completed", "result": {}}

    monkeypatch.setattr("ucdc.job_execution.call_adapter_execute", _fake_execute)

    with (
        TestClient(consent_app) as consent_client,
        TestClient(orchestrator_app) as orchestrator_client,
        TestClient(adapter_app) as adapter_client,
    ):

        consent_resp = consent_client.post(
            "/consents",
            json={
                "user_id": "user-123",
                "agent_id": "example-agent",
                "resources": ["s3://bucket/a"],
                "explanation": "Run a demo job with user consent.",
                "ttl_seconds": 3600,
            },
        )
        assert consent_resp.status_code == 200, consent_resp.text
        body = consent_resp.json()
        token = body["consent_token"]
        consent_id = body["consent_id"]

        job_resp = orchestrator_client.post(
            "/jobs",
            json={
                "consent_token": token,
                "job_manifest": {
                    "agent_id": "example-agent",
                    "resources": ["s3://bucket/a"],
                    "data": {"example": "value"},
                },
            },
        )
        assert job_resp.status_code == 200, job_resp.text
        job_body = job_resp.json()
        assert job_body["status"] == "completed"
        assert isinstance(job_body["job_id"], str)

        # Revoke consent and ensure scheduling fails.
        revoke_resp = consent_client.post(f"/consents/{consent_id}/revoke")
        assert revoke_resp.status_code == 200, revoke_resp.text

        job_resp_after_revoke = orchestrator_client.post(
            "/jobs",
            json={
                "consent_token": token,
                "job_manifest": {
                    "agent_id": "example-agent",
                    "resources": ["s3://bucket/a"],
                    "data": {},
                },
            },
        )
        assert job_resp_after_revoke.status_code == 403

        # Adapter should also reject execution after revocation (parity enforcement).
        exec_resp = adapter_client.post(
            "/execute",
            json={
                "consent_token": token,
                "job_id": job_body["job_id"],
                "job_manifest": {
                    "agent_id": "example-agent",
                    "resources": ["s3://bucket/a"],
                    "data": {},
                },
            },
        )
        assert exec_resp.status_code == 403


def test_consent_to_job_rejects_resource_mismatch():
    with (
        TestClient(consent_app) as consent_client,
        TestClient(orchestrator_app) as orchestrator_client,
        TestClient(adapter_app) as adapter_client,
    ):

        consent_resp = consent_client.post(
            "/consents",
            json={
                "user_id": "user-123",
                "agent_id": "example-agent",
                "resources": ["s3://bucket/a"],
                "explanation": "Run a demo job with user consent.",
                "ttl_seconds": 3600,
            },
        )
        token = consent_resp.json()["consent_token"]

        job_resp = orchestrator_client.post(
            "/jobs",
            json={
                "consent_token": token,
                "job_manifest": {
                    "agent_id": "example-agent",
                    "resources": ["s3://bucket/DIFFERENT"],
                    "data": {},
                },
            },
        )
        assert job_resp.status_code == 403

        exec_resp = adapter_client.post(
            "/execute",
            json={
                "consent_token": token,
                "job_id": "job-123",
                "job_manifest": {
                    "agent_id": "example-agent",
                    "resources": ["s3://bucket/DIFFERENT"],
                    "data": {},
                },
            },
        )
        assert exec_resp.status_code == 403

