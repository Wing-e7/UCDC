from fastapi.testclient import TestClient

from ucdc.agent_adapter_api import app as adapter_app
from ucdc.consent_api import app as consent_app


def test_adapter_rejects_expired_consent():
    with TestClient(consent_app) as consent_client, TestClient(adapter_app) as adapter_client:
        consent_resp = consent_client.post(
            "/consents",
            json={
                "user_id": "user-123",
                "agent_id": "example-agent",
                "resources": ["s3://bucket/a"],
                "explanation": "Expire quickly.",
                "ttl_seconds": 60,
            },
        )
        assert consent_resp.status_code == 200, consent_resp.text
        token = consent_resp.json()["consent_token"]

        # Force-expire the DB record to ensure adapter checks DB expiry as well.
        from datetime import datetime, timedelta, timezone

        from ucdc.db import get_sessionmaker
        from ucdc.models import Consent

        SessionLocal = get_sessionmaker()
        with SessionLocal() as db:
            # fetch consent_id via consent issuance response
            consent_id = consent_resp.json()["consent_id"]
            c = db.get(Consent, consent_id)
            assert c is not None
            c.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.add(c)
            db.commit()

        exec_resp = adapter_client.post(
            "/execute",
            json={
                "consent_token": token,
                "job_id": "job-123",
                "job_manifest": {"agent_id": "example-agent", "resources": ["s3://bucket/a"], "data": {}},
            },
        )
        assert exec_resp.status_code == 403

