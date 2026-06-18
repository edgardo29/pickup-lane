from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.services.support_flag_service import create_support_flag
from backend.tests.helpers import authenticate_as, create_user, set_user_role


def create_account_delete_support_flag(target_user_id: str):
    with SessionLocal() as db:
        support_flag = create_support_flag(
            db,
            flag_type="account_delete_partial_failure",
            source="account",
            title="Account delete follow-up required",
            summary="Account deletion needs manual follow-up.",
            target_user_id=UUID(target_user_id),
            idempotency_key=f"account-delete-{target_user_id}",
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
    assert resolved_flag["resolution_admin_action_id"] is not None

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
