from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import SupportFlag, User, UserPaymentMethod
from backend.tests.helpers import (
    create_user,
    create_user_payment_method,
    run_as_temporary_admin,
    set_user_account_status,
    set_user_hosting_status,
    set_user_role,
    unique_suffix,
)


def _auth_headers(token: str = "sync-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _stub_firebase_tokens(monkeypatch, token_payloads: dict[str, dict]) -> None:
    def verify_firebase_token(id_token: str) -> dict:
        payload = token_payloads.get(id_token)
        if payload is None:
            raise ValueError("Invalid token")
        return payload

    monkeypatch.setattr(
        "backend.services.auth_service.verify_firebase_token",
        verify_firebase_token,
    )


def test_auth_sync_user_creates_and_returns_existing_user(
    client: TestClient, monkeypatch
):
    suffix = unique_suffix()
    token_payload = {
        "uid": f"firebase-{suffix}",
        "email": f"Firebase-{suffix}@Example.com",
        "email_verified": True,
    }
    _stub_firebase_tokens(monkeypatch, {"sync-token": token_payload})

    create_response = client.post(
        "/auth/sync-user",
        headers=_auth_headers(),
        json={
            "auth_user_id": "forged-auth-id",
            "email": "forged@example.com",
            "email_verified": False,
        },
    )
    assert create_response.status_code == 200, create_response.text
    created_user = create_response.json()
    assert created_user["auth_user_id"] == token_payload["uid"]
    assert created_user["email"] == token_payload["email"].lower()
    assert created_user["first_name"] is None
    assert created_user["date_of_birth"] is None
    assert created_user["hosting_status"] == "eligible"

    settings_response = run_as_temporary_admin(
        client,
        lambda: client.get(f"/user-settings/{created_user['id']}"),
    )
    assert settings_response.status_code == 200, settings_response.text
    settings = settings_response.json()
    assert settings["push_notifications_enabled"] is False
    assert settings["email_notifications_enabled"] is False
    assert settings["sms_notifications_enabled"] is False
    assert settings["marketing_opt_in"] is False
    assert settings["location_permission_status"] == "unknown"

    stats_response = run_as_temporary_admin(
        client,
        lambda: client.get(f"/user-stats/{created_user['id']}"),
    )
    assert stats_response.status_code == 200, stats_response.text
    stats = stats_response.json()
    assert stats["games_played_count"] == 0
    assert stats["games_hosted_completed_count"] == 0
    assert stats["no_show_count"] == 0
    assert stats["late_cancel_count"] == 0
    assert stats["host_cancel_count"] == 0

    existing_response = client.post("/auth/sync-user", headers=_auth_headers())
    assert existing_response.status_code == 200, existing_response.text
    assert existing_response.json()["id"] == created_user["id"]


def test_auth_sync_promotes_verified_user_to_hosting_eligible(
    client: TestClient,
    monkeypatch,
):
    suffix = unique_suffix()
    auth_user_id = f"firebase-host-{suffix}"
    email = f"host-{suffix}@example.com"
    _stub_firebase_tokens(
        monkeypatch,
        {
            "unverified-token": {
                "uid": auth_user_id,
                "email": email,
                "email_verified": False,
            },
            "verified-token": {
                "uid": auth_user_id,
                "email": email,
                "email_verified": True,
            },
        },
    )

    unverified_response = client.post(
        "/auth/sync-user",
        headers=_auth_headers("unverified-token"),
    )
    verified_response = client.post(
        "/auth/sync-user",
        headers=_auth_headers("verified-token"),
    )

    assert unverified_response.status_code == 200, unverified_response.text
    assert unverified_response.json()["email_verified_at"] is None
    assert unverified_response.json()["hosting_status"] == "not_eligible"
    assert verified_response.status_code == 200, verified_response.text
    assert verified_response.json()["email_verified_at"] is not None
    assert verified_response.json()["hosting_status"] == "eligible"

    set_user_hosting_status(verified_response.json()["id"], "restricted")
    restricted_response = client.post(
        "/auth/sync-user",
        headers=_auth_headers("verified-token"),
    )
    assert restricted_response.status_code == 200, restricted_response.text
    assert restricted_response.json()["hosting_status"] == "restricted"


def test_auth_sync_user_rejects_email_owned_by_another_auth_user(
    client: TestClient, monkeypatch
):
    suffix = unique_suffix()
    shared_email = f"firebase-shared-{suffix}@example.com"
    _stub_firebase_tokens(
        monkeypatch,
        {
            "first-token": {
                "uid": f"firebase-one-{suffix}",
                "email": shared_email,
            },
            "second-token": {
                "uid": f"firebase-two-{suffix}",
                "email": shared_email,
            },
        },
    )

    first_response = client.post(
        "/auth/sync-user",
        headers=_auth_headers("first-token"),
    )
    assert first_response.status_code == 200, first_response.text

    conflict_response = client.post(
        "/auth/sync-user",
        headers=_auth_headers("second-token"),
    )

    assert conflict_response.status_code == 409, conflict_response.text
    assert "email already exists" in conflict_response.text


def test_auth_sync_user_requires_firebase_bearer_token(client: TestClient):
    response = client.post(
        "/auth/sync-user",
        json={
            "auth_user_id": "forged-auth-id",
            "email": "forged@example.com",
        },
    )

    assert response.status_code == 401, response.text


def test_delete_account_rejects_last_active_admin(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    set_user_role(user["id"], "admin")
    _stub_firebase_tokens(
        monkeypatch,
        {
            "delete-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
            },
        },
    )
    deleted_auth_user_ids: list[str] = []
    monkeypatch.setattr(
        "backend.services.auth_service.delete_firebase_user",
        deleted_auth_user_ids.append,
    )

    response = client.request(
        "DELETE",
        "/auth/account",
        headers=_auth_headers("delete-token"),
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "The last active admin cannot be deleted."
    assert deleted_auth_user_ids == []

    with SessionLocal() as db:
        db_user = db.get(User, UUID(user["id"]))
        assert db_user is not None
        assert db_user.account_status == "active"
        assert db_user.auth_user_id == user["auth_user_id"]


def test_delete_account_allows_admin_when_another_active_admin_exists(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    second_admin = create_user(client)
    set_user_role(user["id"], "admin")
    set_user_role(second_admin["id"], "admin")
    _stub_firebase_tokens(
        monkeypatch,
        {
            "delete-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
            },
        },
    )
    deleted_auth_user_ids: list[str] = []
    monkeypatch.setattr(
        "backend.services.auth_service.delete_firebase_user",
        deleted_auth_user_ids.append,
    )

    response = client.request(
        "DELETE",
        "/auth/account",
        headers=_auth_headers("delete-token"),
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["account_status"] == "deleted"
    assert deleted_auth_user_ids == [user["auth_user_id"]]


def test_cleanup_unfinished_account_rejects_last_active_admin(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    set_user_role(user["id"], "admin")
    with SessionLocal() as db:
        db_user = db.get(User, UUID(user["id"]))
        assert db_user is not None
        db_user.first_name = None
        db_user.last_name = None
        db_user.date_of_birth = None
        db.commit()
    _stub_firebase_tokens(
        monkeypatch,
        {
            "delete-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
            },
        },
    )
    deleted_auth_user_ids: list[str] = []
    monkeypatch.setattr(
        "backend.services.auth_service.delete_firebase_user",
        deleted_auth_user_ids.append,
    )

    response = client.delete(
        "/auth/unfinished-account",
        headers=_auth_headers("delete-token"),
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "The last active admin cannot be deleted."
    assert deleted_auth_user_ids == []

    with SessionLocal() as db:
        assert db.get(User, UUID(user["id"])) is not None


def test_cleanup_unfinished_account_quarantines_after_database_commit_failure(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    with SessionLocal() as db:
        db_user = db.get(User, UUID(user["id"]))
        assert db_user is not None
        db_user.first_name = None
        db_user.last_name = None
        db_user.date_of_birth = None
        db.commit()
    _stub_firebase_tokens(
        monkeypatch,
        {
            "delete-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
            },
        },
    )
    deleted_auth_user_ids: list[str] = []
    monkeypatch.setattr(
        "backend.services.auth_service.delete_firebase_user",
        deleted_auth_user_ids.append,
    )
    original_commit = Session.commit
    commit_count = 0

    def fail_cleanup_commit(db_session: Session) -> None:
        nonlocal commit_count
        commit_count += 1
        if commit_count == 1:
            raise SQLAlchemyError("forced unfinished-account cleanup failure")
        original_commit(db_session)

    monkeypatch.setattr(Session, "commit", fail_cleanup_commit)

    response = client.delete(
        "/auth/unfinished-account",
        headers=_auth_headers("delete-token"),
    )

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == (
        "Firebase cleanup succeeded, but app account cleanup requires "
        "support follow-up."
    )
    assert deleted_auth_user_ids == [user["auth_user_id"]]
    with SessionLocal() as db:
        db_user = db.get(User, UUID(user["id"]))
        support_flag = db.scalar(
            select(SupportFlag).where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == UUID(user["id"]),
            )
        )
        assert db_user is not None
        assert db_user.account_status == "pending_deletion"
        assert db_user.auth_user_id is None
        assert support_flag is not None
        assert support_flag.metadata_["failure_type"] == (
            "unfinished_account_cleanup_commit_error"
        )


def test_delete_account_restores_previous_status_when_firebase_delete_fails(
    client: TestClient, monkeypatch
):
    user = create_user(client)
    set_user_account_status(user["id"], "suspended")
    _stub_firebase_tokens(
        monkeypatch,
        {
            "delete-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
            },
        },
    )

    def fail_delete_firebase_user(auth_user_id: str) -> None:
        raise RuntimeError("Firebase delete failed")

    monkeypatch.setattr(
        "backend.services.auth_service.delete_firebase_user",
        fail_delete_firebase_user,
    )

    response = client.request(
        "DELETE",
        "/auth/account",
        headers=_auth_headers("delete-token"),
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 502, response.text

    with SessionLocal() as db:
        db_user = db.get(User, UUID(user["id"]))
        assert db_user is not None
        assert db_user.account_status == "suspended"


def test_delete_account_records_partial_failure_when_firebase_restore_fails(
    client: TestClient, monkeypatch
):
    user = create_user(client)
    set_user_account_status(user["id"], "suspended")
    _stub_firebase_tokens(
        monkeypatch,
        {
            "delete-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
            },
        },
    )

    def fail_delete_firebase_user(auth_user_id: str) -> None:
        raise RuntimeError("Firebase delete failed")

    monkeypatch.setattr(
        "backend.services.auth_service.delete_firebase_user",
        fail_delete_firebase_user,
    )
    original_commit = Session.commit
    commit_count = 0

    def fail_restore_commit(db_session: Session) -> None:
        nonlocal commit_count
        commit_count += 1
        if commit_count == 2:
            raise SQLAlchemyError("forced self-delete restore failure")
        original_commit(db_session)

    monkeypatch.setattr(Session, "commit", fail_restore_commit)

    response = client.request(
        "DELETE",
        "/auth/account",
        headers=_auth_headers("delete-token"),
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == (
        "Firebase deletion failed, and app account restoration requires "
        "support follow-up."
    )

    with SessionLocal() as db:
        db_user = db.get(User, UUID(user["id"]))
        support_flag = db.scalar(
            select(SupportFlag).where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == UUID(user["id"]),
            )
        )
        assert db_user is not None
        assert db_user.account_status == "pending_deletion"
        assert db_user.auth_user_id == user["auth_user_id"]
        assert db_user.deleted_at is None
        assert support_flag is not None
        assert support_flag.flag_status == "open"
        assert support_flag.severity == "critical"
        assert support_flag.metadata_ == {
            "auth_identity_deleted": False,
            "app_cleanup_completed": False,
            "restore_failed": True,
            "previous_account_status": "suspended",
        }


def test_delete_account_records_partial_failure_when_saved_card_detach_fails(
    client: TestClient, monkeypatch
):
    user = create_user(client)
    payment_method = create_user_payment_method(client, user["id"])
    _stub_firebase_tokens(
        monkeypatch,
        {
            "delete-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
            },
        },
    )
    deleted_auth_user_ids: list[str] = []
    monkeypatch.setattr(
        "backend.services.auth_service.delete_firebase_user",
        deleted_auth_user_ids.append,
    )

    def fail_detach_payment_method(stripe_payment_method_id: str) -> None:
        assert stripe_payment_method_id == payment_method["stripe_payment_method_id"]
        raise RuntimeError("Stripe detach failed")

    monkeypatch.setattr(
        "backend.services.account_deletion_service.detach_payment_method",
        fail_detach_payment_method,
    )

    response = client.request(
        "DELETE",
        "/auth/account",
        headers=_auth_headers("delete-token"),
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == (
        "Firebase deletion succeeded, but app account cleanup requires "
        "support follow-up."
    )
    assert deleted_auth_user_ids == [user["auth_user_id"]]

    with SessionLocal() as db:
        db_user = db.get(User, UUID(user["id"]))
        db_payment_method = db.get(UserPaymentMethod, UUID(payment_method["id"]))
        support_flag = db.scalar(
            select(SupportFlag).where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == UUID(user["id"]),
            )
        )
        assert db_user is not None
        assert db_user.account_status == "pending_deletion"
        assert db_user.auth_user_id is None
        assert db_user.deleted_at is None
        assert db_payment_method is not None
        assert db_payment_method.method_status == "active"
        assert support_flag is not None
        assert support_flag.flag_status == "open"
        assert support_flag.severity == "critical"
        assert support_flag.metadata_ == {
            "auth_identity_deleted": True,
            "app_cleanup_completed": False,
            "saved_payment_method_cleanup_failed": True,
            "saved_payment_method_failure_count": 1,
            "failed_saved_payment_method_ids": [payment_method["id"]],
            "detached_saved_payment_method_ids": [],
            "failure_types": ["stripe_detach_error"],
        }


def test_delete_account_checkpoints_partial_multi_card_detach_for_retry(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    detached_method = create_user_payment_method(client, user["id"])
    failed_method = create_user_payment_method(
        client,
        user["id"],
        is_default=False,
    )
    _stub_firebase_tokens(
        monkeypatch,
        {
            "delete-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
            },
        },
    )
    monkeypatch.setattr(
        "backend.services.auth_service.delete_firebase_user",
        lambda _auth_user_id: None,
    )

    def partially_detach(stripe_payment_method_id: str) -> None:
        if stripe_payment_method_id == failed_method["stripe_payment_method_id"]:
            raise RuntimeError("Stripe detach failed")

    monkeypatch.setattr(
        "backend.services.account_deletion_service.detach_payment_method",
        partially_detach,
    )

    response = client.request(
        "DELETE",
        "/auth/account",
        headers=_auth_headers("delete-token"),
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 503, response.text

    with SessionLocal() as db:
        db_detached_method = db.get(
            UserPaymentMethod,
            UUID(detached_method["id"]),
        )
        db_failed_method = db.get(
            UserPaymentMethod,
            UUID(failed_method["id"]),
        )
        support_flag = db.scalar(
            select(SupportFlag).where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == UUID(user["id"]),
            )
        )
        assert db_detached_method is not None
        assert db_detached_method.method_status == "detached"
        assert db_detached_method.detached_at is not None
        assert db_failed_method is not None
        assert db_failed_method.method_status == "active"
        assert support_flag is not None
        assert support_flag.metadata_["detached_saved_payment_method_ids"] == [
            detached_method["id"]
        ]
        assert support_flag.metadata_["failed_saved_payment_method_ids"] == [
            failed_method["id"]
        ]

    retry_detach_calls: list[str] = []
    monkeypatch.setattr(
        "backend.services.account_deletion_service.detach_payment_method",
        retry_detach_calls.append,
    )
    from backend.services.account_deletion_service import (
        detach_account_saved_payment_methods,
    )

    with SessionLocal() as db:
        retry_result = detach_account_saved_payment_methods(
            db,
            user_id=UUID(user["id"]),
        )
        db.commit()

    assert retry_result.has_blocking_failures is False
    assert retry_detach_calls == [failed_method["stripe_payment_method_id"]]


def test_delete_account_records_partial_failure_when_final_cleanup_commit_fails(
    client: TestClient, monkeypatch
):
    user = create_user(client)
    _stub_firebase_tokens(
        monkeypatch,
        {
            "delete-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
            },
        },
    )
    deleted_auth_user_ids: list[str] = []
    monkeypatch.setattr(
        "backend.services.auth_service.delete_firebase_user",
        deleted_auth_user_ids.append,
    )
    original_commit = Session.commit
    commit_count = 0

    def fail_final_commit(db_session: Session) -> None:
        nonlocal commit_count
        commit_count += 1
        if commit_count == 4:
            raise SQLAlchemyError("forced self-delete cleanup failure")
        original_commit(db_session)

    monkeypatch.setattr(Session, "commit", fail_final_commit)

    response = client.request(
        "DELETE",
        "/auth/account",
        headers=_auth_headers("delete-token"),
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == (
        "Firebase deletion succeeded, but app account cleanup requires "
        "support follow-up."
    )
    assert deleted_auth_user_ids == [user["auth_user_id"]]

    with SessionLocal() as db:
        db_user = db.get(User, UUID(user["id"]))
        support_flag = db.scalar(
            select(SupportFlag).where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == UUID(user["id"]),
            )
        )
        assert db_user is not None
        assert db_user.account_status == "pending_deletion"
        assert db_user.auth_user_id is None
        assert db_user.deleted_at is None
        assert support_flag is not None
        assert support_flag.flag_status == "open"
        assert support_flag.severity == "critical"
        assert support_flag.metadata_ == {
            "auth_identity_deleted": True,
            "app_cleanup_completed": False,
            "failure_type": "app_cleanup_commit_error",
        }


def test_delete_account_records_partial_failure_when_cleanup_execution_raises(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    _stub_firebase_tokens(
        monkeypatch,
        {
            "delete-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
            },
        },
    )
    monkeypatch.setattr(
        "backend.services.auth_service.delete_firebase_user",
        lambda _auth_user_id: None,
    )

    def fail_cleanup(*_args, **_kwargs):
        raise RuntimeError("forced cleanup execution failure")

    monkeypatch.setattr(
        "backend.services.auth_service.cancel_future_user_activity",
        fail_cleanup,
    )

    response = client.request(
        "DELETE",
        "/auth/account",
        headers=_auth_headers("delete-token"),
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 503, response.text
    with SessionLocal() as db:
        db_user = db.get(User, UUID(user["id"]))
        support_flag = db.scalar(
            select(SupportFlag).where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == UUID(user["id"]),
            )
        )
        assert db_user is not None
        assert db_user.account_status == "pending_deletion"
        assert db_user.auth_user_id is None
        assert support_flag is not None
        assert support_flag.metadata_["failure_type"] == (
            "app_cleanup_execution_error"
        )


def test_delete_account_surfaces_recovery_record_commit_failure(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    _stub_firebase_tokens(
        monkeypatch,
        {
            "delete-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
            },
        },
    )
    monkeypatch.setattr(
        "backend.services.auth_service.delete_firebase_user",
        lambda _auth_user_id: None,
    )

    def fail_cleanup(*_args, **_kwargs):
        raise RuntimeError("forced cleanup execution failure")

    monkeypatch.setattr(
        "backend.services.auth_service.cancel_future_user_activity",
        fail_cleanup,
    )
    original_commit = Session.commit
    commit_count = 0

    def fail_recovery_commit(db_session: Session) -> None:
        nonlocal commit_count
        commit_count += 1
        if commit_count == 4:
            raise SQLAlchemyError("forced recovery record commit failure")
        original_commit(db_session)

    monkeypatch.setattr(Session, "commit", fail_recovery_commit)

    response = client.request(
        "DELETE",
        "/auth/account",
        headers=_auth_headers("delete-token"),
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == (
        "Account deletion recovery state could not be recorded."
    )
    with SessionLocal() as db:
        db_user = db.get(User, UUID(user["id"]))
        support_flag = db.scalar(
            select(SupportFlag).where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == UUID(user["id"]),
            )
        )
        assert db_user is not None
        assert db_user.account_status == "pending_deletion"
        assert db_user.auth_user_id is None
        assert support_flag is None
