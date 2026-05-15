from fastapi.testclient import TestClient

from backend.tests.helpers import create_user


def test_users_create_get_list_update_and_soft_delete(client: TestClient):
    user = create_user(client)

    get_response = client.get(f"/users/{user['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == user["id"]

    list_response = client.get("/users")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == user["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/users/{user['id']}",
        json={
            "first_name": "Updated",
            "email_verified_at": "2026-01-01T12:00:00Z",
        },
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["first_name"] == "Updated"
    assert patch_response.json()["email_verified_at"] is not None

    email_patch_response = client.patch(
        f"/users/{user['id']}",
        json={"email": "updated-user@example.com"},
    )
    assert email_patch_response.status_code == 200, email_patch_response.text
    assert email_patch_response.json()["email"] == "updated-user@example.com"
    assert email_patch_response.json()["email_verified_at"] is None

    delete_response = client.delete(f"/users/{user['id']}")
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["deleted_at"] is not None

    missing_response = client.get(f"/users/{user['id']}")
    assert missing_response.status_code == 404


def test_users_reject_duplicate_email(client: TestClient):
    user = create_user(client)

    duplicate_response = client.post(
        "/users",
        json={
            "auth_user_id": "different-auth-id",
            "email": user["email"],
            "phone": "+15550000000",
            "first_name": "Second",
            "last_name": "User",
            "date_of_birth": "1995-01-01",
        },
    )

    assert duplicate_response.status_code == 409, duplicate_response.text
    assert "email already exists" in duplicate_response.text
