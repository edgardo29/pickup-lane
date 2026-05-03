from fastapi.testclient import TestClient

from backend.tests.helpers import create_admin_action, create_user, set_user_role


def create_admin_action_setup(client: TestClient) -> tuple[dict, dict]:
    admin_user = create_user(client)
    set_user_role(admin_user["id"], "admin")

    target_user = create_user(client)

    return admin_user, target_user


def test_admin_action_create_get_list_and_update_reason_metadata(
    client: TestClient,
):
    admin_user, target_user = create_admin_action_setup(client)

    admin_action = create_admin_action(
        client,
        admin_user["id"],
        target_user_id=target_user["id"],
    )

    get_response = client.get(f"/admin-actions/{admin_action['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == admin_action["id"]

    list_by_admin_response = client.get(
        f"/admin-actions?admin_user_id={admin_user['id']}"
    )
    assert list_by_admin_response.status_code == 200, list_by_admin_response.text
    assert any(
        item["id"] == admin_action["id"] for item in list_by_admin_response.json()
    )

    list_by_action_type_response = client.get("/admin-actions?action_type=suspend_user")
    assert list_by_action_type_response.status_code == 200
    assert any(
        item["id"] == admin_action["id"]
        for item in list_by_action_type_response.json()
    )

    patch_response = client.patch(
        f"/admin-actions/{admin_action['id']}",
        json={
            "reason": "Corrected CI admin action reason.",
            "metadata": {"source": "ci", "reviewed": True},
        },
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["reason"] == "Corrected CI admin action reason."
    assert patch_response.json()["metadata"] == {"source": "ci", "reviewed": True}


def test_admin_action_reject_non_admin_actor(client: TestClient):
    regular_user = create_user(client)
    target_user = create_user(client)

    response = client.post(
        "/admin-actions",
        json={
            "admin_user_id": regular_user["id"],
            "action_type": "suspend_user",
            "target_user_id": target_user["id"],
            "reason": "Regular user should not create admin actions.",
        },
    )

    assert response.status_code == 400, response.text
    assert "admin or moderator" in response.text


def test_admin_action_reject_missing_target(client: TestClient):
    admin_user = create_user(client)
    set_user_role(admin_user["id"], "admin")

    response = client.post(
        "/admin-actions",
        json={
            "admin_user_id": admin_user["id"],
            "action_type": "suspend_user",
            "reason": "Missing target.",
        },
    )

    assert response.status_code == 400, response.text
    assert "At least one target field must be provided" in response.text


def test_admin_action_reject_invalid_action_type(client: TestClient):
    admin_user, target_user = create_admin_action_setup(client)

    response = client.post(
        "/admin-actions",
        json={
            "admin_user_id": admin_user["id"],
            "action_type": "delete_everything",
            "target_user_id": target_user["id"],
            "reason": "Invalid action.",
        },
    )

    assert response.status_code == 400, response.text
    assert "action_type is not supported" in response.text


def test_admin_action_reject_missing_target_user(client: TestClient):
    admin_user = create_user(client)
    set_user_role(admin_user["id"], "admin")

    response = client.post(
        "/admin-actions",
        json={
            "admin_user_id": admin_user["id"],
            "action_type": "suspend_user",
            "target_user_id": "00000000-0000-4000-8000-000000000000",
            "reason": "Missing target user.",
        },
    )

    assert response.status_code == 404, response.text
    assert "Target user not found" in response.text


def test_admin_action_reject_missing_target_game(client: TestClient):
    admin_user = create_user(client)
    set_user_role(admin_user["id"], "admin")

    response = client.post(
        "/admin-actions",
        json={
            "admin_user_id": admin_user["id"],
            "action_type": "cancel_game",
            "target_game_id": "00000000-0000-4000-8000-000000000000",
            "reason": "Missing target game.",
        },
    )

    assert response.status_code == 404, response.text
    assert "Target game not found" in response.text


def test_admin_action_reject_immutable_field_update(client: TestClient):
    admin_user, target_user = create_admin_action_setup(client)
    admin_action = create_admin_action(
        client,
        admin_user["id"],
        target_user_id=target_user["id"],
    )

    response = client.patch(
        f"/admin-actions/{admin_action['id']}",
        json={"action_type": "unsuspend_user"},
    )

    assert response.status_code == 400, response.text
    assert "Admin action audit fields cannot be changed" in response.text
