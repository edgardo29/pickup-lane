from fastapi.testclient import TestClient

from backend.models import AdminAction
from backend.services.admin_action_policy import ADMIN_ACTION_TYPES
from backend.tests.helpers import (
    authenticate_as,
    create_admin_action,
    create_game,
    create_user,
    create_venue,
    set_user_role,
)


def create_admin_action_setup(client: TestClient) -> tuple[dict, dict]:
    admin_user = create_user(client)
    set_user_role(admin_user["id"], "admin")

    target_user = create_user(client)

    return admin_user, target_user


def test_admin_action_create_get_list_and_append_note(client: TestClient):
    admin_user, target_user = create_admin_action_setup(client)

    admin_action = create_admin_action(
        client,
        admin_user["id"],
        target_user_id=target_user["id"],
    )
    assert admin_action["admin_user_id"] == admin_user["id"]
    assert admin_action["target_user_id"] == target_user["id"]
    assert admin_action["target_admin_action_id"] is None

    get_response = client.get(f"/admin/actions/{admin_action['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == admin_action["id"]

    list_by_admin_response = client.get(
        f"/admin/actions?admin_user_id={admin_user['id']}"
    )
    assert list_by_admin_response.status_code == 200, list_by_admin_response.text
    assert any(
        item["id"] == admin_action["id"] for item in list_by_admin_response.json()
    )

    list_by_action_type_response = client.get("/admin/actions?action_type=suspend_user")
    assert list_by_action_type_response.status_code == 200
    assert any(
        item["id"] == admin_action["id"]
        for item in list_by_action_type_response.json()
    )

    note_response = client.post(
        f"/admin/actions/{admin_action['id']}/notes",
        json={
            "note": "Support confirmed the suspension reason.",
            "idempotency_key": "note-1",
        },
    )
    assert note_response.status_code == 201, note_response.text
    note = note_response.json()
    assert note["action_type"] == "append_audit_note"
    assert note["target_admin_action_id"] == admin_action["id"]
    assert note["target_user_id"] == target_user["id"]
    assert note["reason"] == "Support confirmed the suspension reason."
    assert note["metadata"] == {"note_length": len(note["reason"])}

    duplicate_note_response = client.post(
        f"/admin/actions/{admin_action['id']}/notes",
        json={
            "note": "Support confirmed the suspension reason.",
            "idempotency_key": "note-1",
        },
    )
    assert duplicate_note_response.status_code == 201, duplicate_note_response.text
    assert duplicate_note_response.json()["id"] == note["id"]


def test_admin_action_routes_require_authentication(client: TestClient):
    response = client.get("/admin/actions")

    assert response.status_code == 401, response.text


def test_admin_action_reject_non_admin_user(client: TestClient):
    regular_user = create_user(client)
    target_user = create_user(client)

    authenticate_as(regular_user["id"])
    response = client.post(
        "/admin/actions",
        json={
            "action_type": "suspend_user",
            "target_user_id": target_user["id"],
            "reason": "Regular user should not create admin actions.",
        },
    )

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


def test_admin_action_read_rejects_regular_user(client: TestClient):
    regular_user = create_user(client)

    authenticate_as(regular_user["id"])
    response = client.get("/admin/actions")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


def test_moderator_reads_only_support_safe_admin_actions(client: TestClient):
    admin_user = create_user(client)
    set_user_role(admin_user["id"], "admin")
    moderator_user = create_user(client)
    set_user_role(moderator_user["id"], "moderator")
    target_user = create_user(client)
    venue = create_venue(client, target_user["id"])
    game = create_game(client, target_user["id"], venue)

    support_action = create_admin_action(
        client,
        admin_user["id"],
        action_type="hide_unsafe_community_payment_text",
        target_game_id=game["id"],
        target_user_id=target_user["id"],
        reason="Unsafe host payment text hidden.",
        metadata={"source": "ci", "reviewed": True},
    )
    money_action = create_admin_action(
        client,
        admin_user["id"],
        action_type="issue_credit",
        target_user_id=target_user["id"],
        reason="Money-sensitive action.",
        metadata={
            "amount_cents": 500,
            "credit_reason": "admin_credit",
            "game_credit_id": None,
        },
    )

    authenticate_as(moderator_user["id"])
    list_response = client.get("/admin/actions")
    assert list_response.status_code == 200, list_response.text
    listed_ids = {item["id"] for item in list_response.json()}
    assert support_action["id"] in listed_ids
    assert money_action["id"] not in listed_ids

    support_get_response = client.get(f"/admin/actions/{support_action['id']}")
    money_get_response = client.get(f"/admin/actions/{money_action['id']}")
    assert support_get_response.status_code == 200, support_get_response.text
    assert support_get_response.json()["id"] == support_action["id"]
    assert money_get_response.status_code == 404, money_get_response.text

    money_filter_response = client.get("/admin/actions?action_type=issue_credit")
    assert money_filter_response.status_code == 200, money_filter_response.text
    assert money_filter_response.json() == []


def test_moderator_cannot_use_generic_audit_write_routes(client: TestClient):
    admin_user, target_user = create_admin_action_setup(client)
    moderator_user = create_user(client)
    set_user_role(moderator_user["id"], "moderator")
    admin_action = create_admin_action(
        client,
        admin_user["id"],
        target_user_id=target_user["id"],
    )

    authenticate_as(moderator_user["id"])
    create_response = client.post(
        "/admin/actions",
        json={
            "action_type": "remove_sub_post",
            "target_sub_post_id": "00000000-0000-4000-8000-000000000000",
            "reason": "Moderators cannot manually create audit rows.",
        },
    )
    note_response = client.post(
        f"/admin/actions/{admin_action['id']}/notes",
        json={"note": "Moderator note should be rejected."},
    )

    assert create_response.status_code == 403, create_response.text
    assert "Admin access required" in create_response.text
    assert note_response.status_code == 403, note_response.text
    assert "Admin access required" in note_response.text


def test_admin_action_reject_body_admin_user_id(client: TestClient):
    admin_user, target_user = create_admin_action_setup(client)

    authenticate_as(admin_user["id"])
    response = client.post(
        "/admin/actions",
        json={
            "admin_user_id": admin_user["id"],
            "action_type": "suspend_user",
            "target_user_id": target_user["id"],
            "reason": "Client should not choose the audit actor.",
        },
    )

    assert response.status_code == 422, response.text
    assert "admin_user_id" in response.text


def test_admin_action_reject_missing_required_target(client: TestClient):
    admin_user = create_user(client)
    set_user_role(admin_user["id"], "admin")

    authenticate_as(admin_user["id"])
    response = client.post(
        "/admin/actions",
        json={
            "action_type": "suspend_user",
            "reason": "Missing target.",
        },
    )

    assert response.status_code == 400, response.text
    assert "suspend_user requires target field" in response.text


def test_admin_action_reject_invalid_action_type(client: TestClient):
    admin_user, target_user = create_admin_action_setup(client)

    authenticate_as(admin_user["id"])
    response = client.post(
        "/admin/actions",
        json={
            "action_type": "delete_everything",
            "target_user_id": target_user["id"],
            "reason": "Invalid action.",
        },
    )

    assert response.status_code == 400, response.text
    assert "action_type is not supported" in response.text


def test_admin_action_reject_unrelated_target_pollution(client: TestClient):
    admin_user, target_user = create_admin_action_setup(client)

    authenticate_as(admin_user["id"])
    response = client.post(
        "/admin/actions",
        json={
            "action_type": "suspend_user",
            "target_user_id": target_user["id"],
            "target_game_id": "00000000-0000-4000-8000-000000000000",
            "reason": "Bad target pollution.",
        },
    )

    assert response.status_code == 400, response.text
    assert "does not allow target field" in response.text

    notification_response = client.post(
        "/admin/actions",
        json={
            "action_type": "suspend_user",
            "target_user_id": target_user["id"],
            "target_notification_id": "00000000-0000-4000-8000-000000000000",
            "reason": "Bad notification target pollution.",
        },
    )

    assert notification_response.status_code == 400, notification_response.text
    assert "does not allow target field" in notification_response.text


def test_admin_action_reject_missing_target_user(client: TestClient):
    admin_user = create_user(client)
    set_user_role(admin_user["id"], "admin")

    authenticate_as(admin_user["id"])
    response = client.post(
        "/admin/actions",
        json={
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

    authenticate_as(admin_user["id"])
    response = client.post(
        "/admin/actions",
        json={
            "action_type": "cancel_game",
            "target_game_id": "00000000-0000-4000-8000-000000000000",
            "reason": "Missing target game.",
        },
    )

    assert response.status_code == 404, response.text
    assert "Target game not found" in response.text


def test_admin_action_reject_forbidden_metadata(client: TestClient):
    admin_user, target_user = create_admin_action_setup(client)

    authenticate_as(admin_user["id"])
    response = client.post(
        "/admin/actions",
        json={
            "action_type": "suspend_user",
            "target_user_id": target_user["id"],
            "reason": "Bad metadata.",
            "metadata": {"raw_request_body": {"anything": "goes"}},
        },
    )

    assert response.status_code == 400, response.text
    assert "forbidden sensitive field" in response.text


def test_admin_action_reject_nested_forbidden_metadata_key(client: TestClient):
    admin_user, target_user = create_admin_action_setup(client)

    authenticate_as(admin_user["id"])
    response = client.post(
        "/admin/actions",
        json={
            "action_type": "suspend_user",
            "target_user_id": target_user["id"],
            "reason": "Bad nested metadata.",
            "metadata": {
                "before": {
                    "raw_request_body": {
                        "note": "Nested request payload should not be stored."
                    }
                }
            },
        },
    )

    assert response.status_code == 400, response.text
    assert "forbidden sensitive field" in response.text


def test_admin_action_reject_sensitive_metadata_value(client: TestClient):
    admin_user, target_user = create_admin_action_setup(client)

    authenticate_as(admin_user["id"])
    response = client.post(
        "/admin/actions",
        json={
            "action_type": "suspend_user",
            "target_user_id": target_user["id"],
            "reason": "Bad metadata value.",
            "metadata": {
                "before": {
                    "summary": "Support pasted client_secret test value."
                }
            },
        },
    )

    assert response.status_code == 400, response.text
    assert "forbidden sensitive value" in response.text


def test_admin_action_append_note_rejects_note_target(client: TestClient):
    admin_user, target_user = create_admin_action_setup(client)
    admin_action = create_admin_action(
        client,
        admin_user["id"],
        target_user_id=target_user["id"],
    )

    note_response = client.post(
        f"/admin/actions/{admin_action['id']}/notes",
        json={"note": "First note."},
    )
    assert note_response.status_code == 201, note_response.text

    second_note_response = client.post(
        f"/admin/actions/{note_response.json()['id']}/notes",
        json={"note": "Nested note should be rejected."},
    )
    assert second_note_response.status_code == 400, second_note_response.text
    assert "cannot target another audit note" in second_note_response.text


def test_admin_action_reject_direct_append_note_create(client: TestClient):
    admin_user, target_user = create_admin_action_setup(client)
    admin_action = create_admin_action(
        client,
        admin_user["id"],
        target_user_id=target_user["id"],
    )

    response = client.post(
        "/admin/actions",
        json={
            "action_type": "append_audit_note",
            "target_admin_action_id": admin_action["id"],
            "reason": "Do not create notes through generic create.",
        },
    )

    assert response.status_code == 400, response.text
    assert "Use the audit note endpoint" in response.text


def test_admin_action_policy_includes_expected_core_types():
    assert "cancel_game" in ADMIN_ACTION_TYPES
    assert "refund_booking" in ADMIN_ACTION_TYPES
    assert "create_refund" in ADMIN_ACTION_TYPES
    assert "update_refund" in ADMIN_ACTION_TYPES
    assert "create_payment" in ADMIN_ACTION_TYPES
    assert "update_payment" in ADMIN_ACTION_TYPES
    assert "create_game_chat" in ADMIN_ACTION_TYPES
    assert "update_game_chat" in ADMIN_ACTION_TYPES
    assert "create_notification" in ADMIN_ACTION_TYPES
    assert "update_notification" in ADMIN_ACTION_TYPES
    assert "create_platform_notice_campaign" in ADMIN_ACTION_TYPES
    assert "update_platform_notice_campaign" in ADMIN_ACTION_TYPES
    assert "send_platform_notice_campaign" in ADMIN_ACTION_TYPES
    assert "retry_platform_notice_campaign" in ADMIN_ACTION_TYPES
    assert "issue_credit" in ADMIN_ACTION_TYPES
    assert "remove_sub_post" in ADMIN_ACTION_TYPES
    assert "append_audit_note" in ADMIN_ACTION_TYPES


def test_admin_action_model_constraint_includes_policy_types():
    constraint_text = " ".join(
        str(constraint.sqltext)
        for constraint in AdminAction.__table__.constraints
        if constraint.name == "ck_admin_actions_action_type"
    )

    for action_type in ADMIN_ACTION_TYPES:
        assert f"'{action_type}'" in constraint_text
