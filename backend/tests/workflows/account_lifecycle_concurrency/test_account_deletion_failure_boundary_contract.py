from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

pytestmark = pytest.mark.suite_type("ordinary")


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _auth_header(token: str = "valid-token") -> str:
    return f"Bearer {token}"


def _install_provider_identity(
    monkeypatch: pytest.MonkeyPatch,
    *,
    uid: str,
    email: str,
) -> None:
    import backend.services.auth_service as auth_service

    payload = {
        "uid": uid,
        "email": email,
        "email_verified": True,
        "auth_time": 1_700_000_000,
    }

    def verify_token(token: str) -> dict[str, object]:
        if token != "valid-token":
            raise ValueError("invalid synthetic token")
        return dict(payload)

    monkeypatch.setattr(auth_service, "verify_firebase_token", verify_token)


def _create_user(
    *,
    auth_user_id: str,
    email: str,
    role: str = "player",
    account_status: str = "active",
) -> uuid.UUID:
    from backend.models import User

    unique = uuid.uuid4().hex
    user = User(
        id=uuid.uuid4(),
        auth_user_id=auth_user_id,
        role=role,
        email=email,
        email_verified_at=datetime.now(timezone.utc),
        phone=f"+1555{unique[:10]}",
        first_name="Deletion",
        last_name="Boundary",
        date_of_birth=date(1990, 1, 1),
        account_status=account_status,
        hosting_status="eligible",
    )
    with _session() as db:
        db.add(user)
        db.commit()
        return user.id


def _user_snapshot(user_id: uuid.UUID) -> dict[str, object]:
    from backend.models import User

    with _session() as db:
        user = db.get(User, user_id)
        assert user is not None
        return {
            "auth_user_id": user.auth_user_id,
            "email": user.email,
            "account_status": user.account_status,
            "role": user.role,
            "deleted_at": user.deleted_at,
        }


def _support_flag_snapshot(user_id: uuid.UUID) -> dict[str, object] | None:
    from backend.models import SupportFlag

    with _session() as db:
        flag = db.scalar(
            select(SupportFlag).where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == user_id,
            )
        )
        if flag is None:
            return None
        return {
            "flag_status": flag.flag_status,
            "severity": flag.severity,
            "title": flag.title,
            "summary": flag.summary,
            "created_by_user_id": flag.created_by_user_id,
            "metadata": flag.metadata_,
        }


def _admin_delete_action_count(user_id: uuid.UUID) -> int:
    from backend.models import AdminAction

    with _session() as db:
        return int(
            db.scalar(
                select(func.count())
                .select_from(AdminAction)
                .where(
                    AdminAction.action_type == "delete_user",
                    AdminAction.target_user_id == user_id,
                )
            )
            or 0
        )


def _delete_payload():
    from backend.schemas.auth_schema import AuthDeleteAccountRequest

    return AuthDeleteAccountRequest(confirmation="DELETE")


@pytest.mark.requirement("WS03-02-R6", "WS03-02-R7")
def test_self_delete_definitive_provider_failure_restores_prior_local_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.account_deletion_service as account_deletion_service
    from backend.services.account_deletion_service import delete_account_workflow

    uid = f"ws03-02-self-fail-{uuid.uuid4()}"
    email = f"ws03-02-self-fail-{uuid.uuid4()}@example.invalid"
    _install_provider_identity(monkeypatch, uid=uid, email=email)
    user_id = _create_user(auth_user_id=uid, email=email)
    staged_states: list[str] = []

    def provider_delete(auth_user_id: str) -> None:
        assert auth_user_id == uid
        staged_states.append(str(_user_snapshot(user_id)["account_status"]))
        raise RuntimeError("synthetic firebase failure")

    monkeypatch.setattr(account_deletion_service, "delete_firebase_user", provider_delete)

    with _session() as db:
        with pytest.raises(HTTPException) as exc_info:
            delete_account_workflow(_delete_payload(), _auth_header(), db)

    assert exc_info.value.status_code == 502
    assert staged_states == ["pending_deletion"]
    assert _user_snapshot(user_id) == {
        "auth_user_id": uid,
        "email": email,
        "account_status": "active",
        "role": "player",
        "deleted_at": None,
    }
    assert _support_flag_snapshot(user_id) is None


@pytest.mark.requirement("WS03-02-R7")
def test_admin_delete_definitive_provider_failure_restores_prior_local_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.admin_user_delete_service as admin_user_delete_service
    from backend.schemas.admin_user_schema import AdminUserDeleteCreate
    from backend.services.admin_user_delete_service import (
        delete_admin_user,
        preview_admin_user_delete_impact,
    )

    admin_id = _create_user(
        auth_user_id=f"ws03-02-admin-delete-actor-{uuid.uuid4()}",
        email=f"ws03-02-admin-delete-actor-{uuid.uuid4()}@example.invalid",
        role="admin",
    )
    target_uid = f"ws03-02-admin-delete-target-{uuid.uuid4()}"
    target_email = f"ws03-02-admin-delete-target-{uuid.uuid4()}@example.invalid"
    target_id = _create_user(auth_user_id=target_uid, email=target_email)
    staged_states: list[str] = []

    def provider_delete(auth_user_id: str) -> None:
        assert auth_user_id == target_uid
        staged_states.append(str(_user_snapshot(target_id)["account_status"]))
        raise RuntimeError("synthetic firebase failure")

    monkeypatch.setattr(admin_user_delete_service, "delete_firebase_user", provider_delete)

    with _session() as db:
        admin_user = db.get(admin_user_delete_service.User, admin_id)
        assert admin_user is not None
        preview = preview_admin_user_delete_impact(db, user_id=target_id)
        payload = AdminUserDeleteCreate(
            preview_token=preview.preview_token,
            reason="provider failure proof",
            idempotency_key=f"admin-delete-{uuid.uuid4()}",
        )

        with pytest.raises(HTTPException) as exc_info:
            delete_admin_user(
                db,
                admin_user=admin_user,
                user_id=target_id,
                payload=payload,
            )

    assert exc_info.value.status_code == 502
    assert staged_states == ["pending_deletion"]
    assert _user_snapshot(target_id) == {
        "auth_user_id": target_uid,
        "email": target_email,
        "account_status": "active",
        "role": "player",
        "deleted_at": None,
    }
    assert _support_flag_snapshot(target_id) is None
    assert _admin_delete_action_count(target_id) == 0


@pytest.mark.requirement("WS03-02-R7")
def test_admin_delete_unknown_provider_outcome_preserves_auth_link_records_support_and_is_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.admin_user_delete_service as admin_user_delete_service
    from backend.observability.timeouts import DependencyMutationTimeoutUnknownError
    from backend.schemas.admin_user_schema import AdminUserDeleteCreate
    from backend.services.admin_user_delete_service import (
        delete_admin_user,
        preview_admin_user_delete_impact,
    )

    admin_id = _create_user(
        auth_user_id=f"ws03-02-admin-unknown-actor-{uuid.uuid4()}",
        email=f"ws03-02-admin-unknown-actor-{uuid.uuid4()}@example.invalid",
        role="admin",
    )
    target_uid = f"ws03-02-admin-unknown-target-{uuid.uuid4()}"
    target_email = f"ws03-02-admin-unknown-target-{uuid.uuid4()}@example.invalid"
    target_id = _create_user(auth_user_id=target_uid, email=target_email)
    provider_calls: list[str] = []

    def unknown_provider_delete(auth_user_id: str) -> None:
        assert auth_user_id == target_uid
        provider_calls.append(auth_user_id)
        raise DependencyMutationTimeoutUnknownError(
            provider_kind="firebase",
            operation="delete_user",
        )

    monkeypatch.setattr(
        admin_user_delete_service,
        "delete_firebase_user",
        unknown_provider_delete,
    )

    with _session() as db:
        admin_user = db.get(admin_user_delete_service.User, admin_id)
        assert admin_user is not None
        preview = preview_admin_user_delete_impact(db, user_id=target_id)
        payload = AdminUserDeleteCreate(
            preview_token=preview.preview_token,
            reason="provider unknown proof",
            idempotency_key=f"admin-delete-unknown-{uuid.uuid4()}",
        )

        with pytest.raises(DependencyMutationTimeoutUnknownError):
            delete_admin_user(
                db,
                admin_user=admin_user,
                user_id=target_id,
                payload=payload,
            )

    assert provider_calls == [target_uid]
    assert _user_snapshot(target_id) == {
        "auth_user_id": target_uid,
        "email": target_email,
        "account_status": "pending_deletion",
        "role": "player",
        "deleted_at": None,
    }
    support_flag = _support_flag_snapshot(target_id)
    assert support_flag is not None
    assert support_flag["flag_status"] == "open"
    assert support_flag["severity"] == "critical"
    assert support_flag["title"] == "Admin account deletion needs follow-up"
    assert support_flag["created_by_user_id"] == admin_id
    assert support_flag["metadata"] == {
        "auth_identity_deleted": "unknown",
        "app_cleanup_completed": False,
        "failure_type": "firebase_delete_outcome_unknown",
    }
    assert _admin_delete_action_count(target_id) == 0

    with _session() as db:
        admin_user = db.get(admin_user_delete_service.User, admin_id)
        assert admin_user is not None
        with pytest.raises(HTTPException) as exc_info:
            delete_admin_user(
                db,
                admin_user=admin_user,
                user_id=target_id,
                payload=payload,
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Accounts pending deletion cannot be deleted by admin."
    assert provider_calls == [target_uid]
    assert _admin_delete_action_count(target_id) == 0


@pytest.mark.requirement("WS03-02-R7")
def test_admin_delete_provider_success_then_local_cleanup_failure_records_support_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.admin_user_delete_service as admin_user_delete_service
    from backend.schemas.admin_user_schema import AdminUserDeleteCreate
    from backend.services.admin_user_delete_service import (
        delete_admin_user,
        preview_admin_user_delete_impact,
    )

    admin_id = _create_user(
        auth_user_id=f"ws03-02-admin-cleanup-actor-{uuid.uuid4()}",
        email=f"ws03-02-admin-cleanup-actor-{uuid.uuid4()}@example.invalid",
        role="admin",
    )
    target_uid = f"ws03-02-admin-cleanup-target-{uuid.uuid4()}"
    target_email = f"ws03-02-admin-cleanup-target-{uuid.uuid4()}@example.invalid"
    target_id = _create_user(auth_user_id=target_uid, email=target_email)
    provider_calls: list[str] = []

    monkeypatch.setattr(
        admin_user_delete_service,
        "delete_firebase_user",
        lambda auth_user_id: provider_calls.append(auth_user_id),
    )

    def fail_local_cleanup(*args, **kwargs) -> None:
        del args, kwargs
        raise RuntimeError("synthetic admin app cleanup failure")

    monkeypatch.setattr(
        admin_user_delete_service,
        "cancel_future_user_activity",
        fail_local_cleanup,
    )

    with _session() as db:
        admin_user = db.get(admin_user_delete_service.User, admin_id)
        assert admin_user is not None
        preview = preview_admin_user_delete_impact(db, user_id=target_id)
        payload = AdminUserDeleteCreate(
            preview_token=preview.preview_token,
            reason="provider success then local failure proof",
            idempotency_key=f"admin-delete-cleanup-{uuid.uuid4()}",
        )

        with pytest.raises(HTTPException) as exc_info:
            delete_admin_user(
                db,
                admin_user=admin_user,
                user_id=target_id,
                payload=payload,
            )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == (
        "Firebase deletion succeeded, but app account cleanup requires support follow-up."
    )
    assert provider_calls == [target_uid]
    snapshot = _user_snapshot(target_id)
    assert snapshot["account_status"] == "pending_deletion"
    assert snapshot["auth_user_id"] is None
    assert snapshot["email"] == target_email
    assert snapshot["role"] == "player"
    assert snapshot["deleted_at"] is None

    support_flag = _support_flag_snapshot(target_id)
    assert support_flag is not None
    assert support_flag["flag_status"] == "open"
    assert support_flag["severity"] == "critical"
    assert support_flag["title"] == "Admin account deletion needs follow-up"
    assert support_flag["created_by_user_id"] == admin_id
    assert support_flag["metadata"] == {
        "auth_identity_deleted": True,
        "app_cleanup_completed": False,
        "failure_type": "app_cleanup_execution_error",
    }
    assert _admin_delete_action_count(target_id) == 0

    with _session() as db:
        admin_user = db.get(admin_user_delete_service.User, admin_id)
        assert admin_user is not None
        with pytest.raises(HTTPException) as repeat_exc_info:
            delete_admin_user(
                db,
                admin_user=admin_user,
                user_id=target_id,
                payload=payload,
            )

    assert repeat_exc_info.value.status_code == 409
    assert (
        repeat_exc_info.value.detail
        == "Accounts pending deletion cannot be deleted by admin."
    )
    assert provider_calls == [target_uid]
    assert _admin_delete_action_count(target_id) == 0


@pytest.mark.requirement("WS03-02-R6", "WS03-02-R7")
def test_self_delete_provider_success_then_local_cleanup_failure_records_support_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.account_deletion_service as account_deletion_service
    from backend.services.account_deletion_service import delete_account_workflow

    uid = f"ws03-02-cleanup-fail-{uuid.uuid4()}"
    email = f"ws03-02-cleanup-fail-{uuid.uuid4()}@example.invalid"
    _install_provider_identity(monkeypatch, uid=uid, email=email)
    user_id = _create_user(auth_user_id=uid, email=email)
    provider_calls: list[str] = []

    monkeypatch.setattr(
        account_deletion_service,
        "delete_firebase_user",
        lambda auth_user_id: provider_calls.append(auth_user_id),
    )

    def fail_local_cleanup(*args, **kwargs) -> None:
        del args, kwargs
        raise RuntimeError("synthetic app cleanup failure")

    monkeypatch.setattr(
        account_deletion_service,
        "cancel_future_user_activity",
        fail_local_cleanup,
    )

    with _session() as db:
        with pytest.raises(HTTPException) as exc_info:
            delete_account_workflow(_delete_payload(), _auth_header(), db)

    assert exc_info.value.status_code == 503
    assert provider_calls == [uid]
    snapshot = _user_snapshot(user_id)
    assert snapshot["account_status"] == "pending_deletion"
    assert snapshot["auth_user_id"] is None

    support_flag = _support_flag_snapshot(user_id)
    assert support_flag is not None
    assert support_flag["flag_status"] == "open"
    assert support_flag["severity"] == "critical"
    assert support_flag["metadata"] == {
        "auth_identity_deleted": True,
        "app_cleanup_completed": False,
        "failure_type": "app_cleanup_execution_error",
    }


@pytest.mark.requirement("WS03-02-R6", "WS03-02-R7")
def test_self_delete_unknown_provider_outcome_preserves_auth_link_and_is_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.account_deletion_service as account_deletion_service
    from backend.observability.timeouts import DependencyMutationTimeoutUnknownError
    from backend.services.account_deletion_service import delete_account_workflow

    uid = f"ws03-02-unknown-{uuid.uuid4()}"
    email = f"ws03-02-unknown-{uuid.uuid4()}@example.invalid"
    _install_provider_identity(monkeypatch, uid=uid, email=email)
    user_id = _create_user(auth_user_id=uid, email=email)
    provider_calls: list[str] = []

    def unknown_provider_delete(auth_user_id: str) -> None:
        provider_calls.append(auth_user_id)
        raise DependencyMutationTimeoutUnknownError(
            provider_kind="firebase",
            operation="delete_user",
        )

    monkeypatch.setattr(
        account_deletion_service,
        "delete_firebase_user",
        unknown_provider_delete,
    )

    with _session() as db:
        with pytest.raises(DependencyMutationTimeoutUnknownError):
            delete_account_workflow(_delete_payload(), _auth_header(), db)

    snapshot = _user_snapshot(user_id)
    assert snapshot["account_status"] == "pending_deletion"
    assert snapshot["auth_user_id"] == uid
    support_flag = _support_flag_snapshot(user_id)
    assert support_flag is not None
    assert support_flag["metadata"] == {
        "auth_identity_deleted": "unknown",
        "app_cleanup_completed": False,
        "failure_type": "firebase_delete_outcome_unknown",
    }

    with _session() as db:
        with pytest.raises(HTTPException) as exc_info:
            delete_account_workflow(_delete_payload(), _auth_header(), db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found."
    assert provider_calls == [uid]


@pytest.mark.requirement("WS03-02-R6", "WS03-02-R7")
def test_successful_self_delete_clears_auth_link_and_repeat_delete_does_not_call_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.account_deletion_service as account_deletion_service
    from backend.services.account_deletion_service import delete_account_workflow

    uid = f"ws03-02-delete-success-{uuid.uuid4()}"
    email = f"ws03-02-delete-success-{uuid.uuid4()}@example.invalid"
    _install_provider_identity(monkeypatch, uid=uid, email=email)
    user_id = _create_user(auth_user_id=uid, email=email)
    provider_calls: list[str] = []

    monkeypatch.setattr(
        account_deletion_service,
        "delete_firebase_user",
        lambda auth_user_id: provider_calls.append(auth_user_id),
    )

    with _session() as db:
        delete_account_workflow(_delete_payload(), _auth_header(), db)

    snapshot = _user_snapshot(user_id)
    assert snapshot["account_status"] == "deleted"
    assert snapshot["auth_user_id"] is None
    assert snapshot["email"] is None
    assert snapshot["deleted_at"] is not None

    with _session() as db:
        with pytest.raises(HTTPException) as exc_info:
            delete_account_workflow(_delete_payload(), _auth_header(), db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found."
    assert provider_calls == [uid]
