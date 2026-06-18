from uuid import UUID

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.models import User
from backend.tests.helpers import (
    create_user,
    run_as_temporary_admin,
    set_user_account_status,
    unique_suffix,
)


def _auth_headers(token: str = "sync-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _stub_firebase_tokens(monkeypatch, token_payloads: dict[str, dict]) -> None:
    def verify_firebase_token(id_token: str) -> dict:
        payload = token_payloads.get(id_token)
        if payload is None:
            raise ValueError("Invalid token")
        return payload

    monkeypatch.setattr(
        "backend.services.auth_service.verify_firebase_token",
        verify_firebase_token,
    )


def test_auth_sync_user_creates_and_returns_existing_user(
    client: TestClient, monkeypatch
):
    suffix = unique_suffix()
    token_payload = {
        "uid": f"firebase-{suffix}",
        "email": f"Firebase-{suffix}@Example.com",
        "email_verified": True,
    }
    _stub_firebase_tokens(monkeypatch, {"sync-token": token_payload})

    create_response = client.post(
        "/auth/sync-user",
        headers=_auth_headers(),
        json={
            "auth_user_id": "forged-auth-id",
            "email": "forged@example.com",
            "email_verified": False,
        },
    )
    assert create_response.status_code == 200, create_response.text
    created_user = create_response.json()
    assert created_user["auth_user_id"] == token_payload["uid"]
    assert created_user["email"] == token_payload["email"].lower()
    assert created_user["first_name"] is None
    assert created_user["date_of_birth"] is None

    settings_response = run_as_temporary_admin(
        client,
        lambda: client.get(f"/user-settings/{created_user['id']}"),
    )
    assert settings_response.status_code == 200, settings_response.text
    settings = settings_response.json()
    assert settings["push_notifications_enabled"] is False
    assert settings["email_notifications_enabled"] is False
    assert settings["sms_notifications_enabled"] is False
    assert settings["marketing_opt_in"] is False
    assert settings["location_permission_status"] == "unknown"

    stats_response = run_as_temporary_admin(
        client,
        lambda: client.get(f"/user-stats/{created_user['id']}"),
    )
    assert stats_response.status_code == 200, stats_response.text
    stats = stats_response.json()
    assert stats["games_played_count"] == 0
    assert stats["games_hosted_completed_count"] == 0
    assert stats["no_show_count"] == 0
    assert stats["late_cancel_count"] == 0
    assert stats["host_cancel_count"] == 0

    existing_response = client.post("/auth/sync-user", headers=_auth_headers())
    assert existing_response.status_code == 200, existing_response.text
    assert existing_response.json()["id"] == created_user["id"]


def test_auth_sync_user_rejects_email_owned_by_another_auth_user(
    client: TestClient, monkeypatch
):
    suffix = unique_suffix()
    shared_email = f"firebase-shared-{suffix}@example.com"
    _stub_firebase_tokens(
        monkeypatch,
        {
            "first-token": {
                "uid": f"firebase-one-{suffix}",
                "email": shared_email,
            },
            "second-token": {
                "uid": f"firebase-two-{suffix}",
                "email": shared_email,
            },
        },
    )

    first_response = client.post(
        "/auth/sync-user",
        headers=_auth_headers("first-token"),
    )
    assert first_response.status_code == 200, first_response.text

    conflict_response = client.post(
        "/auth/sync-user",
        headers=_auth_headers("second-token"),
    )

    assert conflict_response.status_code == 409, conflict_response.text
    assert "email already exists" in conflict_response.text


def test_auth_sync_user_requires_firebase_bearer_token(client: TestClient):
    response = client.post(
        "/auth/sync-user",
        json={
            "auth_user_id": "forged-auth-id",
            "email": "forged@example.com",
        },
    )

    assert response.status_code == 401, response.text


def test_delete_account_restores_previous_status_when_firebase_delete_fails(
    client: TestClient, monkeypatch
):
    user = create_user(client)
    set_user_account_status(user["id"], "suspended")
    _stub_firebase_tokens(
        monkeypatch,
        {
            "delete-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
            },
        },
    )

    def fail_delete_firebase_user(auth_user_id: str) -> None:
        raise RuntimeError("Firebase delete failed")

    monkeypatch.setattr(
        "backend.services.auth_service.delete_firebase_user",
        fail_delete_firebase_user,
    )

    response = client.request(
        "DELETE",
        "/auth/account",
        headers=_auth_headers("delete-token"),
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 502, response.text

    with SessionLocal() as db:
        db_user = db.get(User, UUID(user["id"]))
        assert db_user is not None
        assert db_user.account_status == "suspended"
