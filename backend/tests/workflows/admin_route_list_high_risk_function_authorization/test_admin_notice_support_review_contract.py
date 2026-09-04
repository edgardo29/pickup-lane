from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest

from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    _add_users,
    _auth_headers,
    _client,
    _count_model_rows,
    _install_tokens_for_users,
    _session,
    _user,
)

pytestmark = pytest.mark.suite_type("ordinary")


def _platform_notice_state(notice_id: uuid.UUID) -> dict[str, object]:
    from backend.models import PlatformNotice

    with _session() as db:
        notice = db.get(PlatformNotice, notice_id)
        assert notice is not None
        return {
            "cancelled_at": notice.cancelled_at,
            "cancelled_by_admin_id": notice.cancelled_by_admin_id,
            "cancellation_reason": notice.cancellation_reason,
        }


def _persist_support_review_fixture(
    *,
    admin: Any,
    target: Any,
) -> tuple[uuid.UUID, uuid.UUID]:
    from backend.models import AdminReviewCase, SupportFlag
    from backend.services.admin_review_service import create_case_event

    now = datetime.now(timezone.utc)
    with _session() as db:
        support_flag = SupportFlag(
            id=uuid.uuid4(),
            flag_type="account_delete_partial_failure",
            flag_status="open",
            severity="attention",
            source="account",
            title="Local support flag",
            summary="Local admin authorization fixture.",
            target_user_id=target.id,
            created_by_user_id=admin.id,
            created_at=now,
            updated_at=now,
        )
        review_case = AdminReviewCase(
            id=uuid.uuid4(),
            case_type="user",
            case_status="open",
            case_category="content_moderation",
            priority="attention",
            title="Local review case",
            summary="Local admin review authorization fixture.",
            case_version=1,
            creation_reason="trusted_admin_fixture",
            target_user_id=target.id,
            opened_by_user_id=admin.id,
            created_at=now,
            updated_at=now,
        )
        db.add_all([support_flag, review_case])
        db.flush()
        create_case_event(
            db,
            review_case_id=review_case.id,
            event_type="case_created",
            actor_kind="automation",
            automation_rule_id="trusted_test_fixture",
            automation_rule_version="1",
            event_metadata={"source": "trusted_admin_fixture"},
            created_at=now,
        )
        db.commit()
        return support_flag.id, review_case.id


def _persist_admin_action_fixture(
    *,
    admin: Any,
    target: Any,
    support_flag_id: uuid.UUID,
    review_case_id: uuid.UUID,
) -> uuid.UUID:
    from backend.models import AdminAction

    with _session() as db:
        admin_action = AdminAction(
            id=uuid.uuid4(),
            admin_user_id=admin.id,
            action_type="resolve_support_flag",
            target_user_id=target.id,
            target_support_flag_id=support_flag_id,
            target_review_case_id=review_case_id,
            reason="Local admin read/list action fixture.",
            idempotency_key=f"ws03d-read-action-{uuid.uuid4()}",
            created_at=datetime.now(timezone.utc),
        )
        db.add(admin_action)
        db.commit()
        return admin_action.id


def _close_review_case_for_read_fixture(
    *,
    review_case_id: uuid.UUID,
    admin_id: uuid.UUID,
) -> None:
    from backend.models import User
    from backend.schemas.admin_review_schema import AdminReviewCaseClose
    from backend.services.admin_review_service import close_review_case

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        close_review_case(
            db,
            review_case_id=review_case_id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Closed local read/list fixture.",
                expected_case_version=1,
                idempotency_key=f"ws03d-read-close-{uuid.uuid4()}",
            ),
        )


def _support_flag_state(support_flag_id: uuid.UUID) -> dict[str, object]:
    from backend.models import SupportFlag

    with _session() as db:
        support_flag = db.get(SupportFlag, support_flag_id)
        assert support_flag is not None
        return {
            "flag_status": support_flag.flag_status,
            "resolved_by_user_id": support_flag.resolved_by_user_id,
            "resolution_outcome": support_flag.resolution_outcome,
            "resolution_reason": support_flag.resolution_reason,
        }


def _review_case_state(review_case_id: uuid.UUID) -> dict[str, object]:
    from backend.models import AdminReviewCase

    with _session() as db:
        review_case = db.get(AdminReviewCase, review_case_id)
        assert review_case is not None
        return {
            "case_status": review_case.case_status,
            "closed_by_user_id": review_case.closed_by_user_id,
            "closure_outcome": review_case.closure_outcome,
            "closure_reason": review_case.closure_reason,
        }


@pytest.mark.requirement("WS03-04D-R3", "WS03-04D-R8", "WS03-04D-R10")
def test_platform_notice_create_requires_recent_admin_and_scopes_recipients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, PlatformNotice

    admin = _user("notice-admin", role="admin")
    stale_admin = _user("notice-stale-admin", role="admin")
    target = _user("notice-target")
    _add_users(admin, stale_admin, target)
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "stale-admin-token": stale_admin},
        stale_tokens={"stale-admin-token"},
    )
    client = _client()
    before_notices = _count_model_rows(PlatformNotice)
    before_admin_actions = _count_model_rows(AdminAction)

    stale_response = client.post(
        "/admin/platform-notices",
        json={
            "idempotency_key": f"ws03d-notice-stale-{uuid.uuid4()}",
            "title": "Local authorization notice",
            "message": "This stale admin request must not publish.",
            "audience_type": "selected_users",
            "selected_user_ids": [str(target.id)],
        },
        headers=_auth_headers("stale-admin-token"),
    )
    assert stale_response.status_code == 403
    assert _count_model_rows(PlatformNotice) == before_notices
    assert _count_model_rows(AdminAction) == before_admin_actions

    response = client.post(
        "/admin/platform-notices",
        json={
            "idempotency_key": f"ws03d-notice-create-{uuid.uuid4()}",
            "title": "Local authorization notice",
            "message": "This notice is scoped to one selected local test user.",
            "audience_type": "selected_users",
            "selected_user_ids": [str(target.id)],
        },
        headers=_auth_headers("admin-token"),
    )
    assert response.status_code == 201
    notice = response.json()["notice"]
    assert notice["created_by_admin_id"] == str(admin.id)
    assert notice["selected_recipient_count"] == 1
    assert _count_model_rows(PlatformNotice) == before_notices + 1

    notice_id = uuid.UUID(notice["id"])
    list_response = client.get(
        "/admin/platform-notices?audience_type=selected_users&status=published&limit=1",
        headers=_auth_headers("admin-token"),
    )
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["notices"]] == [str(notice_id)]
    detail_response = client.get(
        f"/admin/platform-notices/{notice_id}",
        headers=_auth_headers("admin-token"),
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == str(notice_id)
    assert detail_response.json()["created_by_admin_id"] == str(admin.id)
    recipients_response = client.get(
        f"/admin/platform-notices/{notice_id}/recipients?limit=1",
        headers=_auth_headers("admin-token"),
    )
    assert recipients_response.status_code == 200
    assert recipients_response.json()["recipients"][0]["user_id"] == str(target.id)

    before_cancel_state = _platform_notice_state(notice_id)
    before_cancel_actions = _count_model_rows(AdminAction)
    stale_cancel = client.post(
        f"/admin/platform-notices/{notice_id}/cancel",
        json={"cancellation_reason": "Stale admin must not cancel this notice."},
        headers=_auth_headers("stale-admin-token"),
    )
    assert stale_cancel.status_code == 403
    assert _platform_notice_state(notice_id) == before_cancel_state
    assert _count_model_rows(AdminAction) == before_cancel_actions

    cancel_response = client.post(
        f"/admin/platform-notices/{notice_id}/cancel",
        json={"cancellation_reason": "Cancel this local test notice."},
        headers=_auth_headers("admin-token"),
    )
    assert cancel_response.status_code == 200
    cancel_body = cancel_response.json()
    assert cancel_body["status"] == "cancelled"
    assert cancel_body["cancelled_by_admin_id"] == str(admin.id)
    assert _platform_notice_state(notice_id)["cancelled_by_admin_id"] == admin.id
    assert _count_model_rows(AdminAction) == before_cancel_actions + 1


@pytest.mark.requirement("WS03-04D-R4", "WS03-04D-R8", "WS03-04D-R10")
def test_support_review_and_admin_action_reads_are_admin_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("support-admin", role="admin")
    ordinary = _user("support-ordinary")
    target = _user("support-target")
    _add_users(admin, ordinary, target)
    support_flag_id, review_case_id = _persist_support_review_fixture(
        admin=admin,
        target=target,
    )
    _close_review_case_for_read_fixture(
        review_case_id=review_case_id,
        admin_id=admin.id,
    )
    admin_action_id = _persist_admin_action_fixture(
        admin=admin,
        target=target,
        support_flag_id=support_flag_id,
        review_case_id=review_case_id,
    )
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "ordinary-token": ordinary},
    )
    client = _client()

    for route in (
        "/admin/support-flags",
        "/admin/review-cases",
        "/admin/actions",
        "/admin/actions/log",
        "/admin/platform-notices",
    ):
        response = client.get(route, headers=_auth_headers("admin-token"))
        assert response.status_code == 200, route

    support_list = client.get(
        "/admin/support-flags?flag_status=open&flag_type=account_delete_partial_failure",
        headers=_auth_headers("admin-token"),
    )
    assert support_list.status_code == 200
    assert [item["id"] for item in support_list.json()] == [str(support_flag_id)]
    support_detail = client.get(
        f"/admin/support-flags/{support_flag_id}",
        headers=_auth_headers("admin-token"),
    )
    assert support_detail.status_code == 200
    assert support_detail.json()["id"] == str(support_flag_id)
    assert support_detail.json()["target_user_id"] == str(target.id)

    review_list = client.get(
        "/admin/review-cases?case_status=closed&case_category=content_moderation&limit=1",
        headers=_auth_headers("admin-token"),
    )
    assert review_list.status_code == 200
    assert [item["id"] for item in review_list.json()["cases"]] == [str(review_case_id)]
    assert review_list.json()["limit"] == 1
    review_detail = client.get(
        f"/admin/review-cases/{review_case_id}",
        headers=_auth_headers("admin-token"),
    )
    assert review_detail.status_code == 200
    assert review_detail.json()["id"] == str(review_case_id)
    assert review_detail.json()["target_user_id"] == str(target.id)

    action_list = client.get(
        (
            "/admin/actions"
            f"?target_support_flag_id={support_flag_id}&action_type=resolve_support_flag"
        ),
        headers=_auth_headers("admin-token"),
    )
    assert action_list.status_code == 200
    assert [item["id"] for item in action_list.json()] == [str(admin_action_id)]
    action_detail = client.get(
        f"/admin/actions/{admin_action_id}",
        headers=_auth_headers("admin-token"),
    )
    assert action_detail.status_code == 200
    assert action_detail.json()["id"] == str(admin_action_id)
    assert action_detail.json()["target_support_flag_id"] == str(support_flag_id)
    assert {
        detail["target_field"] for detail in action_detail.json()["target_details"]
    } >= {"target_user_id", "target_support_flag_id"}

    unsupported_log = client.get(
        "/admin/actions/log?unsupported=1",
        headers=_auth_headers("admin-token"),
    )
    assert unsupported_log.status_code == 400
    assert unsupported_log.json()["detail"]["code"] == (
        "admin_action_log_unsupported_query_param"
    )

    for missing_route in (
        f"/admin/support-flags/{uuid.uuid4()}",
        f"/admin/review-cases/{uuid.uuid4()}",
        f"/admin/actions/{uuid.uuid4()}",
    ):
        missing_response = client.get(
            missing_route,
            headers=_auth_headers("admin-token"),
        )
        assert missing_response.status_code == 404, missing_route

    ordinary_response = client.get(
        "/admin/support-flags",
        headers=_auth_headers("ordinary-token"),
    )
    assert ordinary_response.status_code == 403


@pytest.mark.requirement("WS03-04D-R8", "WS03-04D-R9", "WS03-04D-R10")
def test_support_and_review_mutations_are_admin_only_and_persist_audit_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import (
        AdminAction,
        AdminReviewCaseEvent,
        AdminReviewCaseNote,
    )

    admin = _user("support-review-admin", role="admin")
    ordinary = _user("support-review-ordinary")
    target = _user("support-review-target")
    _add_users(admin, ordinary, target)
    support_flag_id, review_case_id = _persist_support_review_fixture(
        admin=admin,
        target=target,
    )
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "ordinary-token": ordinary},
    )
    client = _client()
    before_flag = _support_flag_state(support_flag_id)
    before_case = _review_case_state(review_case_id)
    before_notes = _count_model_rows(AdminReviewCaseNote)
    before_events = _count_model_rows(AdminReviewCaseEvent)
    before_actions = _count_model_rows(AdminAction)

    ordinary_resolve = client.post(
        f"/admin/support-flags/{support_flag_id}/resolve",
        json={
            "outcome": "no_action_needed",
            "reason": "Ordinary users must not resolve support flags.",
        },
        headers=_auth_headers("ordinary-token"),
    )
    ordinary_note = client.post(
        f"/admin/review-cases/{review_case_id}/notes",
        json={
            "body": "Ordinary users must not add review notes.",
            "expected_case_version": 1,
            "idempotency_key": f"ws03d-ordinary-review-note-{uuid.uuid4()}",
        },
        headers=_auth_headers("ordinary-token"),
    )
    assert ordinary_resolve.status_code == 403
    assert ordinary_note.status_code == 403
    assert _support_flag_state(support_flag_id) == before_flag
    assert _review_case_state(review_case_id) == before_case
    assert _count_model_rows(AdminReviewCaseNote) == before_notes
    assert _count_model_rows(AdminReviewCaseEvent) == before_events
    assert _count_model_rows(AdminAction) == before_actions

    resolve_response = client.post(
        f"/admin/support-flags/{support_flag_id}/resolve",
        json={
            "outcome": "no_action_needed",
            "reason": "Resolved by active admin in local authorization test.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert resolve_response.status_code == 200
    flag_state = _support_flag_state(support_flag_id)
    assert flag_state["flag_status"] == "resolved"
    assert flag_state["resolved_by_user_id"] == admin.id
    assert flag_state["resolution_outcome"] == "no_action_needed"

    note_response = client.post(
        f"/admin/review-cases/{review_case_id}/notes",
        json={
            "body": "Active admin review note.",
            "expected_case_version": 1,
            "idempotency_key": f"ws03d-review-note-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert note_response.status_code == 200
    assert note_response.json()["note"]["author_user_id"] == str(admin.id)
    assert _count_model_rows(AdminReviewCaseNote) == before_notes + 1

    close_response = client.post(
        f"/admin/review-cases/{review_case_id}/close",
        json={
            "outcome": "no_action_needed",
            "reason": "Close local review case after admin review.",
            "expected_case_version": 2,
            "idempotency_key": f"ws03d-review-close-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert close_response.status_code == 200
    case_state = _review_case_state(review_case_id)
    assert case_state["case_status"] == "closed"
    assert case_state["closed_by_user_id"] == admin.id
    assert case_state["closure_outcome"] == "no_action_needed"
    assert _count_model_rows(AdminReviewCaseEvent) == before_events + 2
    assert _count_model_rows(AdminAction) == before_actions + 3
