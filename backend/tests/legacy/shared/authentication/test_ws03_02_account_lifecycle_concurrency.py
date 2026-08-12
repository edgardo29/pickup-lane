from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier, Lock
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.database import SessionLocal, get_db
from backend.models import SupportFlag, User, UserSettings, UserStats
from backend.observability.timeouts import DependencyMutationTimeoutUnknownError
from backend.schemas.admin_user_schema import (
    AdminUserDeleteCreate,
    AdminUserRoleChangeCreate,
    AdminUserSuspendCreate,
    AdminUserUnsuspendCreate,
)
from backend.schemas.auth_schema import AuthDeleteAccountRequest
import backend.services.account_deletion_service as account_deletion_service
from backend.services.admin_user_account_service import (
    preview_admin_user_suspension,
    suspend_admin_user,
    unsuspend_admin_user,
)
from backend.services.admin_user_delete_service import (
    delete_admin_user,
    preview_admin_user_delete_impact,
)
from backend.services.admin_user_role_service import change_user_role
import backend.services.auth_account_service as auth_account_service
from backend.services.auth_service import (
    VerifiedFirebaseIdentity,
    require_active_admin,
    require_active_user,
)
from backend.tests.support.auth import set_user_role
from backend.tests.support.factories import create_user


def _as_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


def _identity(
    auth_user_id: str,
    email: str,
    *,
    email_verified: bool = True,
) -> VerifiedFirebaseIdentity:
    return VerifiedFirebaseIdentity(
        auth_user_id=auth_user_id,
        email=email,
        email_verified=email_verified,
    )


def _install_sync_identity(
    monkeypatch: pytest.MonkeyPatch,
    identity: VerifiedFirebaseIdentity,
) -> None:
    monkeypatch.setattr(
        auth_account_service,
        "get_verified_firebase_identity_from_authorization",
        lambda _authorization: identity,
    )


def _count_rows(db: Session, model: type, *where_clauses: object) -> int:
    statement = select(func.count()).select_from(model)
    for where_clause in where_clauses:
        statement = statement.where(where_clause)
    return db.scalar(statement) or 0


def _user_snapshot(user_id: str | UUID) -> dict[str, object]:
    with SessionLocal() as db:
        user = db.get(User, _as_uuid(user_id))
        assert user is not None
        return {
            "id": user.id,
            "auth_user_id": user.auth_user_id,
            "email": user.email,
            "role": user.role,
            "account_status": user.account_status,
            "deleted_at": user.deleted_at,
        }


def _support_flag_for_user(user_id: str | UUID) -> SupportFlag | None:
    with SessionLocal() as db:
        return db.scalar(
            select(SupportFlag).where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == _as_uuid(user_id),
            )
        )


def _create_admin_user() -> dict:
    user = create_user()
    set_user_role(user["id"], "admin")
    return user


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _build_auth_probe_client() -> TestClient:
    app = FastAPI()

    @app.get("/active-user-probe")
    def active_user_probe(current_user: User = Depends(require_active_user)):
        return {"id": str(current_user.id)}

    @app.get("/active-admin-probe")
    def active_admin_probe(current_user: User = Depends(require_active_admin)):
        return {"id": str(current_user.id)}

    def override_db():
        with SessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def _stub_firebase_tokens(
    monkeypatch: pytest.MonkeyPatch,
    token_payloads: dict[str, dict[str, object]],
) -> None:
    def verify_firebase_token(id_token: str) -> dict[str, object]:
        payload = token_payloads.get(id_token)
        if payload is None:
            raise ValueError("Invalid token")
        return payload

    monkeypatch.setattr(
        "backend.services.auth_service.verify_firebase_token",
        verify_firebase_token,
    )


def _change_role(
    *,
    admin_user_id: str | UUID,
    user_id: str | UUID,
    role: str,
    idempotency_key: str,
):
    with SessionLocal() as db:
        admin_user = db.get(User, _as_uuid(admin_user_id))
        assert admin_user is not None
        return change_user_role(
            db,
            admin_user=admin_user,
            user_id=_as_uuid(user_id),
            payload=AdminUserRoleChangeCreate(
                role=role,
                reason="WS03-02 lifecycle proof.",
                idempotency_key=idempotency_key,
            ),
        )


def _suspend_user(
    *,
    admin_user_id: str | UUID,
    user_id: str | UUID,
    idempotency_key: str,
):
    with SessionLocal() as db:
        preview = preview_admin_user_suspension(db, user_id=_as_uuid(user_id))
        admin_user = db.get(User, _as_uuid(admin_user_id))
        assert admin_user is not None
        return suspend_admin_user(
            db,
            admin_user=admin_user,
            user_id=_as_uuid(user_id),
            payload=AdminUserSuspendCreate(
                preview_token=preview.preview_token,
                reason="WS03-02 lifecycle proof.",
                idempotency_key=idempotency_key,
            ),
        )


def _unsuspend_user(
    *,
    admin_user_id: str | UUID,
    user_id: str | UUID,
    idempotency_key: str,
):
    with SessionLocal() as db:
        admin_user = db.get(User, _as_uuid(admin_user_id))
        assert admin_user is not None
        return unsuspend_admin_user(
            db,
            admin_user=admin_user,
            user_id=_as_uuid(user_id),
            payload=AdminUserUnsuspendCreate(
                reason="WS03-02 lifecycle proof.",
                idempotency_key=idempotency_key,
            ),
        )


def _install_delete_auth(
    monkeypatch: pytest.MonkeyPatch,
    user_id: str | UUID,
) -> None:
    def authenticated_user(_authorization: str | None, db: Session) -> User:
        user = db.get(User, _as_uuid(user_id))
        assert user is not None
        return user

    monkeypatch.setattr(
        account_deletion_service,
        "get_authenticated_user_from_token",
        authenticated_user,
    )


def test_concurrent_first_login_creates_one_app_user_and_context_rows(
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex
    identity = _identity(
        f"firebase-ws03-02-first-login-{suffix}",
        f"ws03-02-first-login-{suffix}@example.test",
    )
    _install_sync_identity(monkeypatch, identity)

    original_commit_user_sync = auth_account_service.commit_user_sync
    commit_barrier = Barrier(2)
    commit_lock = Lock()
    commit_call_count = 0

    def coordinated_commit_user_sync(db: Session, user: User) -> User:
        nonlocal commit_call_count
        with commit_lock:
            commit_call_count += 1
            should_wait = commit_call_count <= 2
        if should_wait:
            commit_barrier.wait(timeout=10)
        return original_commit_user_sync(db, user)

    monkeypatch.setattr(
        auth_account_service,
        "commit_user_sync",
        coordinated_commit_user_sync,
    )

    def sync_user() -> tuple[str, str | int, str | None, str | None]:
        with SessionLocal() as db:
            try:
                user = auth_account_service.sync_user_workflow(
                    None,
                    db,
                )
                return ("ok", str(user.id), user.account_status, user.email)
            except HTTPException as exc:
                db.rollback()
                return ("http", exc.status_code, exc.detail, None)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: sync_user(), range(2)))

    assert all(result[0] == "ok" for result in results), results
    user_ids = {result[1] for result in results}
    assert len(user_ids) == 1
    assert commit_call_count >= 2

    user_id = UUID(next(iter(user_ids)))
    with SessionLocal() as db:
        assert _count_rows(db, User, User.auth_user_id == identity.auth_user_id) == 1
        assert _count_rows(db, User, User.email == identity.email) == 1
        assert _count_rows(db, UserSettings, UserSettings.user_id == user_id) == 1
        assert _count_rows(db, UserStats, UserStats.user_id == user_id) == 1


def test_repeat_same_uid_sync_preserves_user_and_repairs_context_rows(
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex
    identity = _identity(
        f"firebase-ws03-02-repeat-{suffix}",
        f"ws03-02-repeat-{suffix}@example.test",
    )
    _install_sync_identity(monkeypatch, identity)

    with SessionLocal() as db:
        first_user = auth_account_service.sync_user_workflow(
            None,
            db,
        )
        user_id = first_user.id

    with SessionLocal() as db:
        db.execute(delete(UserSettings).where(UserSettings.user_id == user_id))
        db.execute(delete(UserStats).where(UserStats.user_id == user_id))
        db.commit()

    with SessionLocal() as db:
        second_user = auth_account_service.sync_user_workflow(
            None,
            db,
        )
        assert second_user.id == user_id

    with SessionLocal() as db:
        assert _count_rows(db, User, User.auth_user_id == identity.auth_user_id) == 1
        assert _count_rows(db, UserSettings, UserSettings.user_id == user_id) == 1
        assert _count_rows(db, UserStats, UserStats.user_id == user_id) == 1


def test_same_firebase_uid_email_change_updates_snapshot_without_relink(
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex
    auth_user_id = f"firebase-ws03-02-email-change-{suffix}"
    old_email = f"ws03-02-old-{suffix}@example.test"
    new_email = f"ws03-02-new-{suffix}@example.test"

    _install_sync_identity(monkeypatch, _identity(auth_user_id, old_email))
    with SessionLocal() as db:
        first_user = auth_account_service.sync_user_workflow(
            None,
            db,
        )
        user_id = first_user.id

    _install_sync_identity(monkeypatch, _identity(auth_user_id, new_email))
    with SessionLocal() as db:
        second_user = auth_account_service.sync_user_workflow(
            None,
            db,
        )
        assert second_user.id == user_id
        assert second_user.email == new_email

    with SessionLocal() as db:
        assert _count_rows(db, User, User.auth_user_id == auth_user_id) == 1
        assert _count_rows(db, User, User.email == old_email) == 0
        assert _count_rows(db, User, User.email == new_email) == 1
        assert _count_rows(db, UserSettings, UserSettings.user_id == user_id) == 1
        assert _count_rows(db, UserStats, UserStats.user_id == user_id) == 1


def test_different_firebase_uid_same_email_is_rejected_without_relink(
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex
    email = f"ws03-02-relink-{suffix}@example.test"
    existing = create_user(
        auth_user_id=f"firebase-ws03-02-existing-{suffix}",
        email=email,
    )
    conflicting_identity = _identity(
        f"firebase-ws03-02-conflict-{suffix}",
        email,
    )
    _install_sync_identity(monkeypatch, conflicting_identity)

    with SessionLocal() as db:
        with pytest.raises(HTTPException) as exc_info:
            auth_account_service.sync_user_workflow(None, db)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert exc_info.value.detail == "A user with this email already exists."
    snapshot = _user_snapshot(existing["id"])
    assert snapshot["auth_user_id"] == existing["auth_user_id"]
    with SessionLocal() as db:
        assert (
            _count_rows(
                db,
                User,
                User.auth_user_id == conflicting_identity.auth_user_id,
            )
            == 0
        )
        assert _count_rows(db, User, User.email == email) == 1


@pytest.mark.parametrize(
    ("account_status", "deleted_at"),
    [
        ("pending_deletion", None),
        ("deleted", datetime(2026, 1, 1, tzinfo=UTC)),
    ],
)
def test_auth_sync_rejects_terminal_local_accounts_without_recreating(
    monkeypatch: pytest.MonkeyPatch,
    account_status: str,
    deleted_at: datetime | None,
):
    suffix = uuid4().hex
    auth_user_id = f"firebase-ws03-02-terminal-{suffix}"
    email = f"ws03-02-terminal-{suffix}@example.test"
    existing = create_user(auth_user_id=auth_user_id, email=email)
    with SessionLocal() as db:
        user = db.get(User, UUID(existing["id"]))
        assert user is not None
        user.account_status = account_status
        user.deleted_at = deleted_at
        db.commit()

    _install_sync_identity(monkeypatch, _identity(auth_user_id, email))
    with SessionLocal() as db:
        with pytest.raises(HTTPException) as exc_info:
            auth_account_service.sync_user_workflow(None, db)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert exc_info.value.detail == "A user with this email already exists."
    snapshot = _user_snapshot(existing["id"])
    assert snapshot["account_status"] == account_status
    assert snapshot["auth_user_id"] == auth_user_id
    with SessionLocal() as db:
        assert _count_rows(db, User, User.auth_user_id == auth_user_id) == 1
        assert _count_rows(db, User, User.email == email) == 1


def test_local_status_changes_apply_on_next_request_and_sync_does_not_reactivate(
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex
    admin = _create_admin_user()
    player = create_user(
        auth_user_id=f"firebase-ws03-02-status-{suffix}",
        email=f"ws03-02-status-{suffix}@example.test",
    )
    _stub_firebase_tokens(
        monkeypatch,
        {
            "player-token": {
                "uid": player["auth_user_id"],
                "email": player["email"],
                "email_verified": True,
            }
        },
    )
    client = _build_auth_probe_client()

    active_response = client.get(
        "/active-user-probe",
        headers=_auth_headers("player-token"),
    )
    assert active_response.status_code == status.HTTP_200_OK, active_response.text

    _suspend_user(
        admin_user_id=admin["id"],
        user_id=player["id"],
        idempotency_key=f"ws03-02-suspend-{suffix}",
    )
    suspended_response = client.get(
        "/active-user-probe",
        headers=_auth_headers("player-token"),
    )
    assert suspended_response.status_code == status.HTTP_403_FORBIDDEN
    assert suspended_response.json()["detail"] == "Active account required."

    _install_sync_identity(
        monkeypatch,
        _identity(player["auth_user_id"], player["email"]),
    )
    with SessionLocal() as db:
        synced_user = auth_account_service.sync_user_workflow(
            None,
            db,
        )
        assert synced_user.id == UUID(player["id"])
        assert synced_user.account_status == "suspended"

    still_suspended_response = client.get(
        "/active-user-probe",
        headers=_auth_headers("player-token"),
    )
    assert still_suspended_response.status_code == status.HTTP_403_FORBIDDEN

    _unsuspend_user(
        admin_user_id=admin["id"],
        user_id=player["id"],
        idempotency_key=f"ws03-02-unsuspend-{suffix}",
    )
    restored_response = client.get(
        "/active-user-probe",
        headers=_auth_headers("player-token"),
    )
    assert restored_response.status_code == status.HTTP_200_OK, restored_response.text


def test_admin_role_and_status_are_local_authority_on_next_request(
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex
    acting_admin = _create_admin_user()
    subject_admin = _create_admin_user()
    _stub_firebase_tokens(
        monkeypatch,
        {
            "subject-admin-token": {
                "uid": subject_admin["auth_user_id"],
                "email": subject_admin["email"],
                "email_verified": True,
            }
        },
    )
    client = _build_auth_probe_client()

    admin_response = client.get(
        "/active-admin-probe",
        headers=_auth_headers("subject-admin-token"),
    )
    assert admin_response.status_code == status.HTTP_200_OK, admin_response.text

    _change_role(
        admin_user_id=acting_admin["id"],
        user_id=subject_admin["id"],
        role="player",
        idempotency_key=f"ws03-02-demote-{suffix}",
    )
    demoted_response = client.get(
        "/active-admin-probe",
        headers=_auth_headers("subject-admin-token"),
    )
    assert demoted_response.status_code == status.HTTP_403_FORBIDDEN
    assert demoted_response.json()["detail"] == "Admin access required."

    _change_role(
        admin_user_id=acting_admin["id"],
        user_id=subject_admin["id"],
        role="admin",
        idempotency_key=f"ws03-02-promote-{suffix}",
    )
    promoted_response = client.get(
        "/active-admin-probe",
        headers=_auth_headers("subject-admin-token"),
    )
    assert promoted_response.status_code == status.HTTP_200_OK, promoted_response.text

    _suspend_user(
        admin_user_id=acting_admin["id"],
        user_id=subject_admin["id"],
        idempotency_key=f"ws03-02-suspend-admin-{suffix}",
    )
    suspended_response = client.get(
        "/active-admin-probe",
        headers=_auth_headers("subject-admin-token"),
    )
    assert suspended_response.status_code == status.HTTP_403_FORBIDDEN
    assert suspended_response.json()["detail"] == "Active account required."


def test_self_delete_restores_local_state_when_provider_delete_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex
    user = create_user(
        auth_user_id=f"firebase-ws03-02-provider-fails-{suffix}",
        email=f"ws03-02-provider-fails-{suffix}@example.test",
    )
    _install_delete_auth(monkeypatch, user["id"])

    def fail_provider_delete(_auth_user_id: str) -> None:
        raise RuntimeError("synthetic provider failure")

    monkeypatch.setattr(
        account_deletion_service,
        "delete_firebase_user",
        fail_provider_delete,
    )

    with SessionLocal() as db:
        with pytest.raises(HTTPException) as exc_info:
            account_deletion_service.delete_account_workflow(
                AuthDeleteAccountRequest(confirmation="DELETE"),
                None,
                db,
            )

    assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
    snapshot = _user_snapshot(user["id"])
    assert snapshot["account_status"] == "active"
    assert snapshot["auth_user_id"] == user["auth_user_id"]
    assert snapshot["deleted_at"] is None
    assert _support_flag_for_user(user["id"]) is None


def test_self_delete_records_support_flag_after_provider_success_cleanup_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex
    user = create_user(
        auth_user_id=f"firebase-ws03-02-cleanup-fails-{suffix}",
        email=f"ws03-02-cleanup-fails-{suffix}@example.test",
    )
    deleted_auth_user_ids: list[str] = []
    _install_delete_auth(monkeypatch, user["id"])
    monkeypatch.setattr(
        account_deletion_service,
        "delete_firebase_user",
        lambda auth_user_id: deleted_auth_user_ids.append(auth_user_id),
    )

    def fail_cleanup(
        _user: User,
        _db: Session,
        _now: datetime,
        *,
        changed_by_user_id: UUID | None = None,
    ):
        del changed_by_user_id
        raise RuntimeError("synthetic app cleanup failure")

    monkeypatch.setattr(
        account_deletion_service,
        "cancel_future_user_activity",
        fail_cleanup,
    )

    with SessionLocal() as db:
        with pytest.raises(HTTPException) as exc_info:
            account_deletion_service.delete_account_workflow(
                AuthDeleteAccountRequest(confirmation="DELETE"),
                None,
                db,
            )

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert deleted_auth_user_ids == [user["auth_user_id"]]
    snapshot = _user_snapshot(user["id"])
    assert snapshot["account_status"] == "pending_deletion"
    assert snapshot["auth_user_id"] is None
    support_flag = _support_flag_for_user(user["id"])
    assert support_flag is not None
    assert support_flag.flag_status == "open"
    assert support_flag.severity == "critical"
    assert support_flag.metadata_["auth_identity_deleted"] is True
    assert support_flag.metadata_["app_cleanup_completed"] is False
    assert support_flag.metadata_["failure_type"] == "app_cleanup_execution_error"


def test_self_delete_preserves_auth_link_when_provider_delete_outcome_unknown(
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex
    user = create_user(
        auth_user_id=f"firebase-ws03-02-timeout-{suffix}",
        email=f"ws03-02-timeout-{suffix}@example.test",
    )
    _install_delete_auth(monkeypatch, user["id"])

    def timeout_provider_delete(_auth_user_id: str) -> None:
        raise DependencyMutationTimeoutUnknownError(
            provider_kind="firebase",
            operation="firebase.user.delete",
        )

    monkeypatch.setattr(
        account_deletion_service,
        "delete_firebase_user",
        timeout_provider_delete,
    )

    with SessionLocal() as db:
        with pytest.raises(DependencyMutationTimeoutUnknownError):
            account_deletion_service.delete_account_workflow(
                AuthDeleteAccountRequest(confirmation="DELETE"),
                None,
                db,
            )

    snapshot = _user_snapshot(user["id"])
    assert snapshot["account_status"] == "pending_deletion"
    assert snapshot["auth_user_id"] == user["auth_user_id"]
    support_flag = _support_flag_for_user(user["id"])
    assert support_flag is not None
    assert support_flag.flag_status == "open"
    assert support_flag.metadata_["auth_identity_deleted"] == "unknown"
    assert support_flag.metadata_["app_cleanup_completed"] is False
    assert (
        support_flag.metadata_["failure_type"]
        == "firebase_delete_outcome_unknown"
    )


def test_repeated_self_delete_after_completed_cleanup_is_rejected_without_retry(
    monkeypatch: pytest.MonkeyPatch,
):
    suffix = uuid4().hex
    user = create_user(
        auth_user_id=f"firebase-ws03-02-repeat-delete-{suffix}",
        email=f"ws03-02-repeat-delete-{suffix}@example.test",
    )
    deleted_auth_user_ids: list[str] = []
    _install_delete_auth(monkeypatch, user["id"])
    monkeypatch.setattr(
        account_deletion_service,
        "delete_firebase_user",
        lambda auth_user_id: deleted_auth_user_ids.append(auth_user_id),
    )

    with SessionLocal() as db:
        deleted_user = account_deletion_service.delete_account_workflow(
            AuthDeleteAccountRequest(confirmation="DELETE"),
            None,
            db,
        )
        assert deleted_user.account_status == "deleted"

    with SessionLocal() as db:
        with pytest.raises(HTTPException) as exc_info:
            account_deletion_service.delete_account_workflow(
                AuthDeleteAccountRequest(confirmation="DELETE"),
                None,
                db,
            )

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert (
        exc_info.value.detail
        == "This account cannot be deleted because it is already unlinked."
    )
    assert deleted_auth_user_ids == [user["auth_user_id"]]
    snapshot = _user_snapshot(user["id"])
    assert snapshot["account_status"] == "deleted"
    assert snapshot["auth_user_id"] is None
    assert _support_flag_for_user(user["id"]) is None


def test_last_active_admin_cannot_be_demoted_suspended_or_deleted():
    suffix = uuid4().hex
    admin = _create_admin_user()

    with SessionLocal() as db:
        admin_user = db.get(User, UUID(admin["id"]))
        assert admin_user is not None
        with pytest.raises(HTTPException) as demote_exc:
            change_user_role(
                db,
                admin_user=admin_user,
                user_id=admin_user.id,
                payload=AdminUserRoleChangeCreate(
                    role="player",
                    reason="WS03-02 final admin proof.",
                    idempotency_key=f"ws03-02-last-demote-{suffix}",
                ),
            )
    assert demote_exc.value.status_code == status.HTTP_409_CONFLICT
    assert demote_exc.value.detail == "The last active admin cannot be demoted."

    with SessionLocal() as db:
        admin_user = db.get(User, UUID(admin["id"]))
        assert admin_user is not None
        preview = preview_admin_user_suspension(db, user_id=admin_user.id)
        with pytest.raises(HTTPException) as suspend_exc:
            suspend_admin_user(
                db,
                admin_user=admin_user,
                user_id=admin_user.id,
                payload=AdminUserSuspendCreate(
                    preview_token=preview.preview_token,
                    reason="WS03-02 final admin proof.",
                    idempotency_key=f"ws03-02-last-suspend-{suffix}",
                ),
            )
    assert suspend_exc.value.status_code == status.HTTP_409_CONFLICT
    assert suspend_exc.value.detail == "The last active admin cannot be suspended."

    with SessionLocal() as db:
        admin_user = db.get(User, UUID(admin["id"]))
        assert admin_user is not None
        preview = preview_admin_user_delete_impact(db, user_id=admin_user.id)
        with pytest.raises(HTTPException) as delete_exc:
            delete_admin_user(
                db,
                admin_user=admin_user,
                user_id=admin_user.id,
                payload=AdminUserDeleteCreate(
                    preview_token=preview.preview_token,
                    reason="WS03-02 final admin proof.",
                    idempotency_key=f"ws03-02-last-delete-{suffix}",
                ),
            )
    assert delete_exc.value.status_code == status.HTTP_409_CONFLICT
    assert delete_exc.value.detail == "The last active admin cannot be deleted."
    snapshot = _user_snapshot(admin["id"])
    assert snapshot["role"] == "admin"
    assert snapshot["account_status"] == "active"
    assert snapshot["deleted_at"] is None


def test_concurrent_admin_demotions_cannot_remove_every_active_admin():
    suffix = uuid4().hex
    admin_a = _create_admin_user()
    admin_b = _create_admin_user()
    barrier = Barrier(2)

    def demote(acting_admin_id: str, target_user_id: str, key: str):
        with SessionLocal() as db:
            admin_user = db.get(User, UUID(acting_admin_id))
            assert admin_user is not None
            barrier.wait(timeout=10)
            try:
                result = change_user_role(
                    db,
                    admin_user=admin_user,
                    user_id=UUID(target_user_id),
                    payload=AdminUserRoleChangeCreate(
                        role="player",
                        reason="WS03-02 concurrent final admin proof.",
                        idempotency_key=key,
                    ),
                )
                return ("ok", str(result.user_id), result.role)
            except HTTPException as exc:
                db.rollback()
                return ("http", exc.status_code, exc.detail)

    with ThreadPoolExecutor(max_workers=2) as executor:
        result_a = executor.submit(
            demote,
            admin_a["id"],
            admin_b["id"],
            f"ws03-02-demote-b-{suffix}",
        )
        result_b = executor.submit(
            demote,
            admin_b["id"],
            admin_a["id"],
            f"ws03-02-demote-a-{suffix}",
        )
        results = [result_a.result(timeout=15), result_b.result(timeout=15)]

    assert sum(1 for result in results if result[0] == "ok") == 1, results
    assert any(
        result[0] == "http"
        and result[1] == status.HTTP_409_CONFLICT
        and result[2] == "The last active admin cannot be demoted."
        for result in results
    ), results
    with SessionLocal() as db:
        active_admin_count = _count_rows(
            db,
            User,
            User.role == "admin",
            User.account_status == "active",
            User.deleted_at.is_(None),
        )
    assert active_admin_count == 1
