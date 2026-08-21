from __future__ import annotations

import uuid

import pytest

from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    _add_users,
    _auth_headers,
    _client,
    _count_model_rows,
    _get_user_role,
    _install_tokens_for_users,
    _session,
    _user,
)

pytestmark = pytest.mark.suite_type("ordinary")


@pytest.mark.requirement("WS03-04D-R3", "WS03-04D-R5")
def test_recent_active_admin_can_change_user_role_and_replay_idempotently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction

    admin = _user("role-success-admin", role="admin")
    target = _user("role-success-target")
    _add_users(admin, target)
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})

    idempotency_key = f"ws03d-role-success-{uuid.uuid4()}"
    payload = {
        "role": "admin",
        "reason": "Promote trusted staff member for admin testing.",
        "idempotency_key": idempotency_key,
    }
    client = _client()
    before_admin_actions = _count_model_rows(AdminAction)

    response = client.patch(
        f"/admin/users/{target.id}/role",
        json=payload,
        headers=_auth_headers("admin-token"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(target.id)
    assert body["previous_role"] == "player"
    assert body["role"] == "admin"
    assert _get_user_role(target.id) == "admin"
    assert _count_model_rows(AdminAction) == before_admin_actions + 1

    replay = client.patch(
        f"/admin/users/{target.id}/role",
        json=payload,
        headers=_auth_headers("admin-token"),
    )
    assert replay.status_code == 200
    assert replay.json()["admin_action_id"] == body["admin_action_id"]
    assert _count_model_rows(AdminAction) == before_admin_actions + 1


@pytest.mark.requirement("WS03-04D-R5", "WS03-04D-R9", "WS03-04D-R10")
def test_user_role_write_rejects_server_controlled_extra_fields_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction

    admin = _user("role-extra-admin", role="admin")
    target = _user("role-extra-target")
    _add_users(admin, target)
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    before_admin_actions = _count_model_rows(AdminAction)

    response = _client().patch(
        f"/admin/users/{target.id}/role",
        json={
            "role": "admin",
            "reason": "Extra caller fields should not be accepted.",
            "idempotency_key": f"ws03d-role-extra-{uuid.uuid4()}",
            "admin_user_id": str(uuid.uuid4()),
        },
        headers=_auth_headers("admin-token"),
    )

    assert response.status_code == 422
    assert _get_user_role(target.id) == "player"
    assert _count_model_rows(AdminAction) == before_admin_actions


def _get_user_account_state(user_id: uuid.UUID) -> dict[str, object]:
    from backend.models import User

    with _session() as db:
        user = db.get(User, user_id)
        assert user is not None
        return {
            "role": user.role,
            "account_status": user.account_status,
            "hosting_status": user.hosting_status,
            "deleted_at": user.deleted_at,
        }


@pytest.mark.requirement("WS03-04D-R5", "WS03-04D-R10")
def test_user_admin_actions_preserve_final_admin_and_current_state_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, Notification

    admin = _user("final-admin", role="admin")
    already_suspended = _user(
        "already-suspended",
        account_status="suspended",
    )
    hosting_restricted = _user(
        "hosting-restricted",
        hosting_status="restricted",
    )
    _add_users(admin, already_suspended, hosting_restricted)
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})

    client = _client()
    before_actions = _count_model_rows(AdminAction)
    before_notifications = _count_model_rows(Notification)
    before_admin_state = _get_user_account_state(admin.id)
    before_suspended_state = _get_user_account_state(already_suspended.id)
    before_hosting_state = _get_user_account_state(hosting_restricted.id)

    final_admin_response = client.patch(
        f"/admin/users/{admin.id}/role",
        json={
            "role": "player",
            "reason": "The last active admin cannot be demoted.",
            "idempotency_key": f"ws03d-final-admin-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    stale_state_suspend = client.post(
        f"/admin/users/{already_suspended.id}/suspend",
        json={
            "preview_token": "s" * 64,
            "reason": "Already suspended accounts must not be resuspended.",
            "idempotency_key": f"ws03d-resuspend-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    stale_state_restrict = client.post(
        f"/admin/users/{hosting_restricted.id}/restrict-hosting",
        json={
            "preview_token": "h" * 64,
            "reason": "Already restricted hosts must not be restricted again.",
            "idempotency_key": f"ws03d-rerestrict-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )

    assert final_admin_response.status_code == 409
    assert stale_state_suspend.status_code == 409
    assert stale_state_restrict.status_code == 409
    assert _get_user_account_state(admin.id) == before_admin_state
    assert _get_user_account_state(already_suspended.id) == before_suspended_state
    assert _get_user_account_state(hosting_restricted.id) == before_hosting_state
    assert _count_model_rows(AdminAction) == before_actions
    assert _count_model_rows(Notification) == before_notifications


@pytest.mark.requirement("WS03-04D-R3", "WS03-04D-R5", "WS03-04D-R10")
def test_recent_admin_user_account_hosting_and_delete_actions_persist_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, Notification
    from backend.services import admin_user_delete_service

    admin = _user("account-actions-admin", role="admin")
    suspend_target = _user("account-actions-suspend")
    hosting_target = _user("account-actions-hosting")
    delete_target = _user("account-actions-delete")
    _add_users(admin, suspend_target, hosting_target, delete_target)
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    firebase_deletes: list[str] = []

    def fake_delete_firebase_user(auth_user_id: str) -> None:
        firebase_deletes.append(auth_user_id)

    monkeypatch.setattr(
        admin_user_delete_service,
        "delete_firebase_user",
        fake_delete_firebase_user,
    )

    client = _client()
    before_actions = _count_model_rows(AdminAction)
    before_notifications = _count_model_rows(Notification)

    suspend_preview = client.post(
        f"/admin/users/{suspend_target.id}/suspension-preview",
        headers=_auth_headers("admin-token"),
    )
    assert suspend_preview.status_code == 200
    suspend_token = suspend_preview.json()["preview_token"]
    suspend_idempotency = f"ws03d-suspend-success-{uuid.uuid4()}"
    suspend = client.post(
        f"/admin/users/{suspend_target.id}/suspend",
        json={
            "preview_token": suspend_token,
            "reason": "Suspend local test account for admin authorization proof.",
            "idempotency_key": suspend_idempotency,
        },
        headers=_auth_headers("admin-token"),
    )
    assert suspend.status_code == 200
    assert suspend.json()["account_status"] == "suspended"
    assert _get_user_account_state(suspend_target.id)["account_status"] == "suspended"

    suspend_replay = client.post(
        f"/admin/users/{suspend_target.id}/suspend",
        json={
            "preview_token": suspend_token,
            "reason": "Suspend local test account for admin authorization proof.",
            "idempotency_key": suspend_idempotency,
        },
        headers=_auth_headers("admin-token"),
    )
    assert suspend_replay.status_code == 200
    assert suspend_replay.json()["admin_action_id"] == suspend.json()["admin_action_id"]

    unsuspend = client.post(
        f"/admin/users/{suspend_target.id}/unsuspend",
        json={
            "reason": "Restore local test account after admin suspension proof.",
            "idempotency_key": f"ws03d-unsuspend-success-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert unsuspend.status_code == 200
    assert unsuspend.json()["account_status"] == "active"
    assert _get_user_account_state(suspend_target.id)["account_status"] == "active"

    hosting_preview = client.post(
        f"/admin/users/{hosting_target.id}/hosting-restriction-preview",
        headers=_auth_headers("admin-token"),
    )
    assert hosting_preview.status_code == 200
    hosting_token = hosting_preview.json()["preview_token"]
    restrict = client.post(
        f"/admin/users/{hosting_target.id}/restrict-hosting",
        json={
            "preview_token": hosting_token,
            "reason": "Restrict local test hosting for admin authorization proof.",
            "idempotency_key": f"ws03d-restrict-hosting-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert restrict.status_code == 200
    assert restrict.json()["hosting_status"] == "restricted"
    assert _get_user_account_state(hosting_target.id)["hosting_status"] == "restricted"

    restore = client.post(
        f"/admin/users/{hosting_target.id}/restore-hosting",
        json={
            "reason": "Restore local test hosting after admin restriction proof.",
            "idempotency_key": f"ws03d-restore-hosting-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert restore.status_code == 200
    assert restore.json()["hosting_status"] == "eligible"
    assert _get_user_account_state(hosting_target.id)["hosting_status"] == "eligible"

    delete_preview = client.post(
        f"/admin/users/{delete_target.id}/delete-preview",
        headers=_auth_headers("admin-token"),
    )
    assert delete_preview.status_code == 200
    delete_token = delete_preview.json()["preview_token"]
    delete_response = client.post(
        f"/admin/users/{delete_target.id}/delete",
        json={
            "preview_token": delete_token,
            "reason": "Delete disposable local test account for admin proof.",
            "idempotency_key": f"ws03d-delete-user-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["account_status"] == "deleted"
    delete_state = _get_user_account_state(delete_target.id)
    assert delete_state["account_status"] == "deleted"
    assert delete_state["deleted_at"] is not None
    assert firebase_deletes == [delete_target.auth_user_id]
    assert _count_model_rows(AdminAction) == before_actions + 5
    assert _count_model_rows(Notification) == before_notifications + 4
