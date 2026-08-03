from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_user,
    create_user_settings,
    set_user_role,
)


def authenticate_admin(client: TestClient) -> dict:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])
    return admin


def test_user_settings_create_get_and_update(client: TestClient):
    authenticate_admin(client)
    user = create_user(client)
    settings = create_user_settings(client, user["id"])

    get_response = client.get(f"/user-settings/{user['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["user_id"] == settings["user_id"]

    patch_response = client.patch(
        f"/user-settings/{user['id']}",
        json={"marketing_opt_in": True, "selected_city": "Evanston"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["marketing_opt_in"] is True
    assert patch_response.json()["selected_city"] == "Evanston"


def test_user_settings_scaffold_routes_reject_regular_user(client: TestClient):
    user = create_user(client)
    create_user_settings(client, user["id"])
    authenticate_as(user["id"])

    get_response = client.get(f"/user-settings/{user['id']}")
    assert get_response.status_code == 403, get_response.text

    create_response = client.post("/user-settings", json={"user_id": user["id"]})
    assert create_response.status_code == 403, create_response.text

    patch_response = client.patch(
        f"/user-settings/{user['id']}",
        json={"selected_city": "Denied"},
    )
    assert patch_response.status_code == 403, patch_response.text


def test_user_settings_me_reads_and_updates_authenticated_user(client: TestClient):
    current_user = create_user(client)
    other_user = create_user(client)
    create_user_settings(client, current_user["id"])
    other_settings = create_user_settings(client, other_user["id"])
    authenticate_as(current_user["id"])

    get_response = client.get("/user-settings/me")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["user_id"] == current_user["id"]

    patch_response = client.patch(
        "/user-settings/me",
        json={"email_notifications_enabled": True, "selected_city": "Oak Park"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["user_id"] == current_user["id"]
    assert patch_response.json()["email_notifications_enabled"] is True
    assert patch_response.json()["selected_city"] == "Oak Park"

    other_response = client.get(f"/user-settings/{other_user['id']}")
    assert other_response.status_code == 403, other_response.text
    assert other_settings["user_id"] == other_user["id"]


def test_user_settings_me_patch_creates_missing_settings_row(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.patch(
        "/user-settings/me",
        json={"selected_city": "Chicago", "selected_state": "IL"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["user_id"] == user["id"]
    assert response.json()["selected_city"] == "Chicago"
    assert response.json()["selected_state"] == "IL"
    assert response.json()["email_notifications_enabled"] is False


def test_user_settings_reject_duplicate_for_user(client: TestClient):
    authenticate_admin(client)
    user = create_user(client)
    create_user_settings(client, user["id"])

    duplicate_response = client.post("/user-settings", json={"user_id": user["id"]})

    assert duplicate_response.status_code == 409, duplicate_response.text
    assert "Settings already exist" in duplicate_response.text
