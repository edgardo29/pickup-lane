from fastapi.testclient import TestClient

from backend.services.admin_permission_service import (
    ADMIN_PERMISSIONS,
    ADMIN_ROLE,
    MODERATOR_PERMISSIONS,
    MODERATOR_ROLE,
    ROLE_DATA_SCOPES,
)
from backend.tests.helpers import (
    authenticate_as,
    create_user,
    set_user_account_status,
    set_user_role,
)


def test_admin_me_returns_admin_permissions(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get("/admin/me")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user_id"] == admin["id"]
    assert body["role"] == ADMIN_ROLE
    assert body["account_status"] == "active"
    assert set(body["permissions"]) == ADMIN_PERMISSIONS
    assert set(body["data_scopes"]) == ROLE_DATA_SCOPES[ADMIN_ROLE]


def test_admin_me_returns_moderator_permissions(client: TestClient):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")

    authenticate_as(moderator["id"])
    response = client.get("/admin/me")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user_id"] == moderator["id"]
    assert body["role"] == MODERATOR_ROLE
    assert set(body["permissions"]) == MODERATOR_PERMISSIONS
    assert set(body["data_scopes"]) == ROLE_DATA_SCOPES[MODERATOR_ROLE]


def test_admin_me_rejects_regular_user(client: TestClient):
    user = create_user(client)

    authenticate_as(user["id"])
    response = client.get("/admin/me")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


def test_admin_me_rejects_suspended_admin(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    set_user_account_status(admin["id"], "suspended")

    authenticate_as(admin["id"])
    response = client.get("/admin/me")

    assert response.status_code == 403, response.text
    assert "Active account required" in response.text


def test_admin_route_rejects_suspended_admin(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    set_user_account_status(admin["id"], "suspended")

    authenticate_as(admin["id"])
    response = client.get("/admin/official-games")

    assert response.status_code == 403, response.text
    assert "Active account required" in response.text


def test_moderator_cannot_access_money_admin_route(client: TestClient):
    moderator = create_user(client)
    target_user = create_user(client)
    set_user_role(moderator["id"], "moderator")

    authenticate_as(moderator["id"])
    response = client.get(f"/game-credits/balance?user_id={target_user['id']}")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text
