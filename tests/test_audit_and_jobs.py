from fastapi.testclient import TestClient

from ucdc.consent_api import app as consent_app
from ucdc.orchestrator_api import app as orchestrator_app


def test_consent_events_and_job_events_include_scheduled_and_cancel():
    with TestClient(consent_app) as consent_client, TestClient(orchestrator_app) as orchestrator_client:
        consent_resp = consent_client.post(
            "/consents",
            json={
                "user_id": "user-123",
                "agent_id": "example-agent",
                "resources": ["s3://bucket/a"],
                "explanation": "audit test",
                "ttl_seconds": 3600,
            },
        )
        assert consent_resp.status_code == 200
        consent_id = consent_resp.json()["consent_id"]
        token = consent_resp.json()["consent_token"]

        ev = consent_client.get(f"/consents/{consent_id}/events")
        assert ev.status_code == 200
        types = [e["event_type"] for e in ev.json()]
        assert "consent.issued" in types

        job_resp = orchestrator_client.post(
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
        assert job_resp.status_code == 200
        job_id = job_resp.json()["job_id"]

        cev = consent_client.get(f"/consents/{consent_id}/events")
        assert cev.status_code == 200
        c_types = [e["event_type"] for e in cev.json()]
        assert "job.scheduled" in c_types

        jev = orchestrator_client.get(f"/jobs/{job_id}/events")
        assert jev.status_code == 200
        assert any(e["event_type"] == "job.scheduled" for e in jev.json())

        get_j = orchestrator_client.get(f"/jobs/{job_id}")
        assert get_j.status_code == 200
        assert get_j.json()["status"] == "scheduled"

        cancel = orchestrator_client.post(f"/jobs/{job_id}/cancel")
        assert cancel.status_code == 200
        assert cancel.json()["status"] == "cancelled"

        jev2 = orchestrator_client.get(f"/jobs/{job_id}/events")
        assert any(e["event_type"] == "job.cancelled" for e in jev2.json())
