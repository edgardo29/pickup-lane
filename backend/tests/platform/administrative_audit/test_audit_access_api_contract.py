from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from backend.models import AdminAction, AdminRejectedAttempt, Notification
from backend.observability.correlation import correlation_context
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    _add_users,
    _auth_headers,
    _client,
    _install_tokens_for_users,
    _user,
)

pytestmark = pytest.mark.suite_type("ordinary")


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _persist_audit_fixture(
    actor_id: uuid.UUID, target_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    from backend.services.admin_action_service import record_admin_action

    correlation_id = uuid.uuid4()
    rejected_id = uuid.uuid4()
    with correlation_context(str(correlation_id)), _session() as db:
        action = record_admin_action(
            db,
            admin_user_id=actor_id,
            action_type="suspend_user",
            outcome="succeeded",
            target_user_id=target_id,
            reason="Approved administrative action.",
        )
        db.add(
            AdminRejectedAttempt(
                id=rejected_id,
                admin_user_id=actor_id,
                attempt_type="suspend_user_rejected",
                rejection_mode="domain_rejected_postload",
                response_status_code=409,
                route_method="POST",
                route_path=f"/admin/users/{target_id}/suspend",
                target_user_id=target_id,
                metadata_={"reason_code": "already_suspended"},
            )
        )
        db.commit()
        return action.id, rejected_id, correlation_id


def _persist_notification_audit_fixture(
    actor_id: uuid.UUID,
    target_id: uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID]:
    from backend.services.admin_action_service import record_admin_action

    notification_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    with _session() as db:
        db.add(
            Notification(
                id=notification_id,
                user_id=target_id,
                notification_type="account_security",
                notification_category="app",
                notification_domain="account",
                source_type="account",
                title="Administrative audit access fixture",
                subject_label="Account",
                summary="Administrative audit access fixture.",
                body="Administrative audit access fixture body.",
                action_key="view_profile",
                event_at=now,
                is_read=False,
                read_at=None,
            )
        )
        action = record_admin_action(
            db,
            admin_user_id=actor_id,
            action_type="create_notification",
            outcome="succeeded",
            target_user_id=target_id,
            target_notification_id=notification_id,
        )
        db.commit()
        return notification_id, action.id


@pytest.mark.requirement("WS09-02A-R7")
def test_audit_http_surfaces_are_active_admin_only_private_and_additive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("audit-admin", role="admin")
    ordinary = _user("audit-ordinary")
    suspended = _user("audit-suspended", role="admin", account_status="suspended")
    pending_deletion = _user(
        "audit-pending-deletion",
        role="admin",
        account_status="pending_deletion",
    )
    deleted = _user("audit-deleted", role="admin", account_status="deleted")
    deleted.deleted_at = datetime.now(timezone.utc)
    target = _user("audit-target")
    _add_users(admin, ordinary, suspended, pending_deletion, deleted, target)
    action_id, rejected_id, _correlation_id = _persist_audit_fixture(admin.id, target.id)
    _install_tokens_for_users(
        monkeypatch,
        {
            "admin-token": admin,
            "ordinary-token": ordinary,
            "suspended-token": suspended,
            "pending-token": pending_deletion,
            "deleted-token": deleted,
        },
    )
    client = _client()
    routes = (
        "/admin/actions/log",
        f"/admin/actions/{action_id}",
        "/admin/rejected-attempts",
        f"/admin/rejected-attempts/{rejected_id}",
    )

    for route in routes:
        anonymous = client.get(route)
        assert anonymous.status_code == 401, route
        for token in (
            "ordinary-token",
            "suspended-token",
            "pending-token",
            "deleted-token",
        ):
            denied = client.get(route, headers=_auth_headers(token))
            assert denied.status_code in {403, 404}, (route, token, denied.text)
        allowed = client.get(route, headers=_auth_headers("admin-token"))
        assert allowed.status_code == 200, (route, allowed.text)
        assert allowed.headers["Cache-Control"] == "private, no-store"

    retired_collection = client.get(
        "/admin/actions",
        headers=_auth_headers("admin-token"),
    )
    assert retired_collection.status_code == 405

    detail = client.get(
        f"/admin/actions/{action_id}",
        headers=_auth_headers("admin-token"),
    ).json()
    assert set(detail) == {
        "id",
        "action_type",
        "action_label",
        "admin_label",
        "admin_email",
        "created_at",
        "reason",
        "primary_target",
    }
    assert detail["id"] == str(action_id)
    log = client.get(
        "/admin/actions/log",
        headers=_auth_headers("admin-token"),
    ).json()
    assert set(log["actions"][0]) == {
        "id",
        "action_label",
        "admin_label",
        "target_label",
        "reason_preview",
        "created_at",
    }

    missing_action = client.get(
        f"/admin/actions/{uuid.uuid4()}",
        headers=_auth_headers("admin-token"),
    )
    missing_rejected = client.get(
        f"/admin/rejected-attempts/{uuid.uuid4()}",
        headers=_auth_headers("admin-token"),
    )
    assert missing_action.status_code == 404
    assert missing_rejected.status_code == 404

    retired_create = client.post(
        "/admin/actions",
        headers=_auth_headers("admin-token"),
    )
    retired_note = client.post(
        f"/admin/actions/{action_id}/notes",
        headers=_auth_headers("admin-token"),
    )
    assert retired_create.status_code == 410
    assert retired_note.status_code == 410


@pytest.mark.requirement("WS09-02A-R7")
def test_direct_service_calls_cannot_bypass_binary_active_admin_access() -> None:
    from backend.services.admin_action_display_service import (
        list_admin_action_log,
        serialize_admin_action_detail_read,
    )
    from backend.services.admin_action_service import (
        get_admin_action_for_viewer_or_404,
        list_admin_actions,
    )
    from backend.services.admin_notification_service import (
        get_admin_notification_lookup_detail,
    )
    from backend.services.admin_rejected_attempt_service import (
        get_admin_rejected_attempt_for_viewer_or_404,
        list_admin_rejected_attempts,
    )

    admin = _user("service-admin", role="admin")
    ordinary = _user("service-ordinary")
    suspended = _user("service-suspended", role="admin", account_status="suspended")
    deleted = _user("service-deleted", role="admin")
    deleted.deleted_at = datetime.now(timezone.utc)
    target = _user("service-target")
    _add_users(admin, ordinary, suspended, deleted, target)
    action_id, rejected_id, _correlation_id = _persist_audit_fixture(
        admin.id, target.id
    )
    notification_id, _notification_action_id = _persist_notification_audit_fixture(
        admin.id,
        target.id,
    )

    with _session() as db:
        active_admin = db.get(type(admin), admin.id)
        assert active_admin is not None
        action = get_admin_action_for_viewer_or_404(db, action_id, active_admin)
        assert list_admin_actions(db, viewer_user=active_admin)
        assert list_admin_action_log(db, viewer_user=active_admin).actions
        assert (
            serialize_admin_action_detail_read(
                db,
                action,
                viewer_user=active_admin,
            ).id
            == action_id
        )
        assert list_admin_rejected_attempts(db, viewer_user=active_admin)
        notification_detail = get_admin_notification_lookup_detail(
            db,
            notification_id=notification_id,
            viewer_user=active_admin,
        )
        assert "audit_actions" not in notification_detail.model_dump()
        assert "audit_action_count" not in notification_detail.model_dump()
        assert (
            get_admin_rejected_attempt_for_viewer_or_404(
                db,
                rejected_id,
                active_admin,
            ).id
            == rejected_id
        )

        for denied_user in (ordinary, suspended, deleted):
            for call in (
                lambda user=denied_user: list_admin_actions(db, viewer_user=user),
                lambda user=denied_user: list_admin_action_log(db, viewer_user=user),
                lambda user=denied_user: serialize_admin_action_detail_read(
                    db,
                    action,
                    viewer_user=user,
                ),
                lambda user=denied_user: list_admin_rejected_attempts(
                    db,
                    viewer_user=user,
                ),
                lambda user=denied_user: get_admin_rejected_attempt_for_viewer_or_404(
                    db,
                    rejected_id,
                    user,
                ),
                lambda user=denied_user: get_admin_notification_lookup_detail(
                    db,
                    notification_id=notification_id,
                    viewer_user=user,
                ),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    call()
                assert exc_info.value.status_code == 403

        assert db.get(AdminAction, action_id) is not None
