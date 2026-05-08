from fastapi.testclient import TestClient

from backend.tests.helpers import unique_suffix


def test_auth_sync_user_creates_and_returns_existing_user(client: TestClient):
    suffix = unique_suffix()
    payload = {
        "auth_user_id": f"firebase-{suffix}",
        "email": f"firebase-{suffix}@example.com",
    }

    create_response = client.post("/auth/sync-user", json=payload)
    assert create_response.status_code == 200, create_response.text
    created_user = create_response.json()
    assert created_user["auth_user_id"] == payload["auth_user_id"]
    assert created_user["email"] == payload["email"]
    assert created_user["first_name"] is None
    assert created_user["date_of_birth"] is None

    settings_response = client.get(f"/user-settings/{created_user['id']}")
    assert settings_response.status_code == 200, settings_response.text
    settings = settings_response.json()
    assert settings["push_notifications_enabled"] is False
    assert settings["email_notifications_enabled"] is False
    assert settings["sms_notifications_enabled"] is False
    assert settings["marketing_opt_in"] is False
    assert settings["location_permission_status"] == "unknown"

    stats_response = client.get(f"/user-stats/{created_user['id']}")
    assert stats_response.status_code == 200, stats_response.text
    stats = stats_response.json()
    assert stats["games_played_count"] == 0
    assert stats["games_hosted_completed_count"] == 0
    assert stats["no_show_count"] == 0
    assert stats["late_cancel_count"] == 0
    assert stats["host_cancel_count"] == 0

    existing_response = client.post("/auth/sync-user", json=payload)
    assert existing_response.status_code == 200, existing_response.text
    assert existing_response.json()["id"] == created_user["id"]


def test_auth_sync_user_rejects_email_owned_by_another_auth_user(client: TestClient):
    suffix = unique_suffix()

    first_response = client.post(
        "/auth/sync-user",
        json={
            "auth_user_id": f"firebase-one-{suffix}",
            "email": f"firebase-shared-{suffix}@example.com",
        },
    )
    assert first_response.status_code == 200, first_response.text

    conflict_response = client.post(
        "/auth/sync-user",
        json={
            "auth_user_id": f"firebase-two-{suffix}",
            "email": f"firebase-shared-{suffix}@example.com",
        },
    )

    assert conflict_response.status_code == 409, conflict_response.text
    assert "email already exists" in conflict_response.text
