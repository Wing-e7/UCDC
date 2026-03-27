from fastapi.testclient import TestClient

from ucdc.orchestrator_api import app as orchestrator_app


def _create_installer(client: TestClient) -> str:
    resp = client.post("/staffer/installers", json={"payload": {"name": "staffer-a"}})
    assert resp.status_code == 200
    return resp.json()["id"]


def test_staffer_installer_happy_path_and_events():
    with TestClient(orchestrator_app) as client:
        installer_id = _create_installer(client)

        submit = client.post(f"/staffer/installers/{installer_id}/submit")
        assert submit.status_code == 200
        assert submit.json()["state"] == "submitted"

        approve = client.post(
            f"/staffer/installers/{installer_id}/approve",
            json={},
            headers={"Idempotency-Key": "approve-happy"},
        )
        assert approve.status_code == 200
        assert approve.json()["state"] == "approved"

        validate = client.post(
            f"/staffer/installers/{installer_id}/validate-launch",
            json={"is_valid": True, "details": {"check": "ok"}},
        )
        assert validate.status_code == 200
        assert validate.json()["state"] == "launch_validated"

        activate = client.post(f"/staffer/installers/{installer_id}/activate")
        assert activate.status_code == 200
        assert activate.json()["state"] == "active"

        events = client.get(f"/staffer/installers/{installer_id}/events")
        assert events.status_code == 200
        event_types = [e["event_type"] for e in events.json()]
        assert "staffer.installer.created" in event_types
        assert "staffer.installer.submitted" in event_types
        assert "staffer.installer.approved" in event_types
        assert "staffer.installer.launch_validated" in event_types
        assert "staffer.installer.activated" in event_types


def test_staffer_installer_invalid_transition():
    with TestClient(orchestrator_app) as client:
        installer_id = _create_installer(client)
        activate = client.post(f"/staffer/installers/{installer_id}/activate")
        assert activate.status_code == 409
        assert "cannot activate from state draft" in activate.json()["detail"].lower()


def test_staffer_installer_rollback():
    with TestClient(orchestrator_app) as client:
        installer_id = _create_installer(client)
        assert client.post(f"/staffer/installers/{installer_id}/submit").status_code == 200
        assert (
            client.post(
                f"/staffer/installers/{installer_id}/approve",
                json={},
                headers={"Idempotency-Key": "approve-rollback"},
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/staffer/installers/{installer_id}/validate-launch",
                json={"is_valid": True, "details": {}},
            ).status_code
            == 200
        )
        assert client.post(f"/staffer/installers/{installer_id}/activate").status_code == 200

        rollback = client.post(f"/staffer/installers/{installer_id}/rollback")
        assert rollback.status_code == 200
        assert rollback.json()["state"] == "rolled_back"


def test_staffer_installer_approval_idempotency():
    with TestClient(orchestrator_app) as client:
        installer_id = _create_installer(client)
        assert client.post(f"/staffer/installers/{installer_id}/submit").status_code == 200

        first = client.post(
            f"/staffer/installers/{installer_id}/approve",
            json={"reason": "looks good"},
            headers={"Idempotency-Key": "approve-idempotent"},
        )
        second = client.post(
            f"/staffer/installers/{installer_id}/approve",
            json={"reason": "looks good"},
            headers={"Idempotency-Key": "approve-idempotent"},
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["state"] == "approved"
        assert second.json()["state"] == "approved"

        events = client.get(f"/staffer/installers/{installer_id}/events")
        approved_events = [e for e in events.json() if e["event_type"] == "staffer.installer.approved"]
        assert len(approved_events) == 1
