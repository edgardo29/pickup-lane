from fastapi.testclient import TestClient

from backend.tests.helpers import create_user, create_user_settings


def test_user_settings_create_get_and_update(client: TestClient):
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


def test_user_settings_reject_duplicate_for_user(client: TestClient):
    user = create_user(client)
    create_user_settings(client, user["id"])

    duplicate_response = client.post("/user-settings", json={"user_id": user["id"]})

    assert duplicate_response.status_code == 409, duplicate_response.text
    assert "Settings already exist" in duplicate_response.text
