from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.models import SupportFlag
from backend.services.support_flag_service import create_support_flag
from backend.tests.helpers import authenticate_as, create_user, set_user_role


def create_account_delete_support_flag(
    target_user_id: str,
    *,
    idempotency_key: str | None = None,
):
    with SessionLocal() as db:
        support_flag = create_support_flag(
            db,
            flag_type="account_delete_partial_failure",
            source="account",
            title="Account delete follow-up required",
            summary="Account deletion needs manual follow-up.",
            target_user_id=UUID(target_user_id),
            idempotency_key=idempotency_key or f"account-delete-{target_user_id}",
        )
        return support_flag.id


def test_admin_lists_gets_and_resolves_support_flag(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    target_user = create_user(client)
    support_flag_id = create_account_delete_support_flag(target_user["id"])

    authenticate_as(admin["id"])
    list_response = client.get("/admin/support-flags")

    assert list_response.status_code == 200, list_response.text
    support_flags = list_response.json()
    assert any(item["id"] == str(support_flag_id) for item in support_flags)

    get_response = client.get(f"/admin/support-flags/{support_flag_id}")

    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["flag_status"] == "open"

    resolve_response = client.post(
        f"/admin/support-flags/{support_flag_id}/resolve",
        json={
            "outcome": "handled_externally",
            "reason": "Confirmed the remaining cleanup was handled.",
        },
    )

    assert resolve_response.status_code == 200, resolve_response.text
    resolved_flag = resolve_response.json()
    assert resolved_flag["flag_status"] == "resolved"
    assert resolved_flag["resolution_outcome"] == "handled_externally"
    assert {
        "metadata",
        "idempotency_key",
        "source_admin_action_id",
        "created_by_user_id",
        "resolved_by_user_id",
        "resolution_admin_action_id",
    }.isdisjoint(resolved_flag)

    audit_response = client.get(
        f"/admin/actions?target_support_flag_id={support_flag_id}"
    )

    assert audit_response.status_code == 200, audit_response.text
    audit_rows = audit_response.json()
    assert any(row["action_type"] == "resolve_support_flag" for row in audit_rows)


def test_moderator_cannot_read_staff_sensitive_support_flag(client: TestClient):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    target_user = create_user(client)
    support_flag_id = create_account_delete_support_flag(target_user["id"])

    authenticate_as(moderator["id"])
    list_response = client.get("/admin/support-flags")
    get_response = client.get(f"/admin/support-flags/{support_flag_id}")

    assert list_response.status_code == 200, list_response.text
    assert list_response.json() == []
    assert get_response.status_code == 404, get_response.text


def test_idempotent_support_flag_duplicate_keeps_resolved_state_by_default(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    target_user = create_user(client)
    idempotency_key = f"account-delete-default-{target_user['id']}"
    support_flag_id = create_account_delete_support_flag(
        target_user["id"],
        idempotency_key=idempotency_key,
    )

    authenticate_as(admin["id"])
    resolve_response = client.post(
        f"/admin/support-flags/{support_flag_id}/resolve",
        json={
            "outcome": "handled_externally",
            "reason": "Confirmed the cleanup was handled.",
        },
    )
    assert resolve_response.status_code == 200, resolve_response.text

    with SessionLocal() as db:
        duplicate = create_support_flag(
            db,
            flag_type="account_delete_partial_failure",
            source="account",
            title="Account delete failed again",
            summary="Account deletion failed again.",
            target_user_id=UUID(target_user["id"]),
            idempotency_key=idempotency_key,
        )

    assert duplicate.id == support_flag_id
    assert duplicate.flag_status == "resolved"
    assert duplicate.resolution_outcome == "handled_externally"


def test_idempotent_support_flag_can_reopen_resolved_flag(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    target_user = create_user(client)
    idempotency_key = f"account-delete-reopen-{target_user['id']}"
    support_flag_id = create_account_delete_support_flag(
        target_user["id"],
        idempotency_key=idempotency_key,
    )

    authenticate_as(admin["id"])
    resolve_response = client.post(
        f"/admin/support-flags/{support_flag_id}/resolve",
        json={
            "outcome": "handled_externally",
            "reason": "Confirmed the cleanup was handled.",
        },
    )
    assert resolve_response.status_code == 200, resolve_response.text

    with SessionLocal() as db:
        resolved_flag = db.get(SupportFlag, support_flag_id)
        assert resolved_flag is not None
        resolution_admin_action_id = resolved_flag.resolution_admin_action_id

    with SessionLocal() as db:
        reopened = create_support_flag(
            db,
            flag_type="account_delete_partial_failure",
            source="account",
            title="Account delete failed again",
            summary="Account deletion failed again.",
            metadata={"attempt": 2},
            target_user_id=UUID(target_user["id"]),
            idempotency_key=idempotency_key,
            reopen_resolved=True,
        )

    assert reopened.id == support_flag_id
    assert reopened.flag_status == "open"
    assert reopened.title == "Account delete failed again"
    assert reopened.metadata_ == {"attempt": 2}
    assert reopened.resolved_at is None
    assert reopened.resolved_by_user_id is None
    assert reopened.resolution_outcome is None
    assert reopened.resolution_reason is None
    assert reopened.resolution_admin_action_id is None
    assert resolution_admin_action_id is not None

    with SessionLocal() as db:
        stored_flag = db.get(SupportFlag, support_flag_id)

    assert stored_flag is not None
    assert stored_flag.flag_status == "open"

    list_response = client.get("/admin/support-flags")

    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == str(support_flag_id) for item in list_response.json())


def test_support_flag_rejects_unrelated_target():
    with pytest.raises(HTTPException) as exc_info:
        with SessionLocal() as db:
            create_support_flag(
                db,
                flag_type="account_delete_partial_failure",
                source="account",
                title="Bad support flag",
                summary="This flag uses the wrong target.",
                target_game_id=UUID("00000000-0000-0000-0000-000000000001"),
            )

    assert exc_info.value.status_code == 400
    assert "does not allow target field" in exc_info.value.detail
