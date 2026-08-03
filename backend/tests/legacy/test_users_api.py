from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_user,
    set_user_account_status,
    set_user_role,
    unique_suffix,
)
from backend.services.user_service import GENERIC_USER_MUTATION_DISABLED_DETAIL


def authenticate_admin(client: TestClient) -> dict:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])
    return admin


def _valid_user_payload() -> dict:
    suffix = unique_suffix()
    return {
        "auth_user_id": f"firebase-route-{suffix}",
        "email": f"route-user-{suffix}@example.com",
        "phone": f"+1555{suffix[:7]}",
        "first_name": "Route",
        "last_name": "User",
        "date_of_birth": "1995-01-01",
        "home_city": "Chicago",
        "home_state": "IL",
    }


def test_users_admin_read_routes_and_generic_mutations_disabled(client: TestClient):
    authenticate_admin(client)
    user = create_user(client)

    get_response = client.get(f"/users/{user['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == user["id"]

    list_response = client.get("/users")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == user["id"] for item in list_response.json())

    create_response = client.post("/users", json=_valid_user_payload())
    assert create_response.status_code == 403, create_response.text
    assert create_response.json()["detail"] == GENERIC_USER_MUTATION_DISABLED_DETAIL

    patch_response = client.patch(
        f"/users/{user['id']}",
        json={"first_name": "Updated"},
    )
    assert patch_response.status_code == 403, patch_response.text
    assert patch_response.json()["detail"] == GENERIC_USER_MUTATION_DISABLED_DETAIL

    delete_response = client.delete(f"/users/{user['id']}")
    assert delete_response.status_code == 403, delete_response.text
    assert delete_response.json()["detail"] == GENERIC_USER_MUTATION_DISABLED_DETAIL

    preserved_response = client.get(f"/users/{user['id']}")
    assert preserved_response.status_code == 200, preserved_response.text
    assert preserved_response.json()["deleted_at"] is None


def test_user_scaffold_routes_reject_regular_user(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    list_response = client.get("/users")
    assert list_response.status_code == 403, list_response.text

    get_response = client.get(f"/users/{user['id']}")
    assert get_response.status_code == 403, get_response.text

    create_response = client.post(
        "/users",
        json=_valid_user_payload(),
    )
    assert create_response.status_code == 403, create_response.text

    patch_response = client.patch(f"/users/{user['id']}", json={"first_name": "Nope"})
    assert patch_response.status_code == 403, patch_response.text

    delete_response = client.delete(f"/users/{user['id']}")
    assert delete_response.status_code == 403, delete_response.text


def test_users_me_reads_and_updates_authenticated_user(client: TestClient):
    current_user = create_user(client)
    other_user = create_user(client)
    authenticate_as(current_user["id"])

    get_response = client.get("/users/me")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == current_user["id"]

    patch_response = client.patch(
        "/users/me",
        json={
            "first_name": "Current",
            "email": "current-profile@example.com",
        },
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["id"] == current_user["id"]
    assert patch_response.json()["first_name"] == "Current"
    assert patch_response.json()["email"] == "current-profile@example.com"
    assert patch_response.json()["email_verified_at"] is None

    other_response = client.get(f"/users/{other_user['id']}")
    assert other_response.status_code == 403, other_response.text


def test_users_me_allows_suspended_user_account_access(client: TestClient):
    user = create_user(client)
    set_user_account_status(user["id"], "suspended")
    authenticate_as(user["id"])

    response = client.get("/users/me")

    assert response.status_code == 200, response.text
    assert response.json()["id"] == user["id"]
    assert response.json()["account_status"] == "suspended"


def test_users_me_rejects_client_managed_stripe_customer_id(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.patch(
        "/users/me",
        json={"stripe_customer_id": "cus_client_supplied"},
    )
    assert response.status_code == 422, response.text
