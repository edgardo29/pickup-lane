from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_user,
    set_user_account_status,
    set_user_role,
    soft_delete_user,
)


def test_admin_me_returns_active_admin_access(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get("/admin/me")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user_id"] == admin["id"]
    assert body["role"] == "admin"
    assert body["account_status"] == "active"
    assert "permissions" not in body
    assert "data_scopes" not in body


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
    assert "Admin access required" in response.text


def test_admin_me_rejects_pending_deletion_admin(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    set_user_account_status(admin["id"], "pending_deletion")

    authenticate_as(admin["id"])
    response = client.get("/admin/me")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


def test_admin_me_rejects_soft_deleted_admin(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    soft_delete_user(admin["id"])

    authenticate_as(admin["id"])
    response = client.get("/admin/me")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


def test_admin_route_rejects_suspended_admin(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    set_user_account_status(admin["id"], "suspended")

    authenticate_as(admin["id"])
    response = client.get("/admin/official-games")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


def test_admin_route_rejects_pending_deletion_admin(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    set_user_account_status(admin["id"], "pending_deletion")

    authenticate_as(admin["id"])
    response = client.get("/admin/official-games")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


def test_admin_route_rejects_soft_deleted_admin(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    soft_delete_user(admin["id"])

    authenticate_as(admin["id"])
    response = client.get("/admin/official-games")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


def test_player_cannot_access_money_admin_route(client: TestClient):
    player = create_user(client)
    target_user = create_user(client)

    authenticate_as(player["id"])
    response = client.get(f"/game-credits/balance?user_id={target_user['id']}")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text
