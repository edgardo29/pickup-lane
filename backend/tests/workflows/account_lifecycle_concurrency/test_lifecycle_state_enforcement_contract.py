from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

pytestmark = pytest.mark.suite_type("ordinary")


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _install_provider_identity(
    monkeypatch: pytest.MonkeyPatch,
    *,
    uid: str,
    email: str,
    email_verified: bool = True,
) -> None:
    import backend.services.auth_service as auth_service

    payload = {
        "uid": uid,
        "email": email,
        "email_verified": email_verified,
        "auth_time": 1_700_000_000,
    }

    def verify_token(token: str) -> dict[str, object]:
        if token != "valid-token":
            raise ValueError("invalid synthetic token")
        return dict(payload)

    monkeypatch.setattr(auth_service, "verify_firebase_token", verify_token)


def _install_sync_identity(
    monkeypatch: pytest.MonkeyPatch,
    *,
    uid: str,
    email: str,
    email_verified: bool = True,
) -> None:
    from backend.services.auth_service import VerifiedFirebaseIdentity
    import backend.services.auth_account_service as auth_account_service

    def identity_from_header(authorization: str | None) -> VerifiedFirebaseIdentity:
        assert authorization == "Bearer valid-token"
        return VerifiedFirebaseIdentity(
            auth_user_id=uid,
            email=email,
            email_verified=email_verified,
        )

    monkeypatch.setattr(
        auth_account_service,
        "get_verified_firebase_identity_from_authorization",
        identity_from_header,
    )


def _create_user(
    *,
    auth_user_id: str,
    email: str,
    role: str = "player",
    account_status: str = "active",
    deleted_at: datetime | None = None,
    email_verified_at: datetime | None = None,
) -> uuid.UUID:
    from backend.models import User

    unique = uuid.uuid4().hex
    user = User(
        id=uuid.uuid4(),
        auth_user_id=auth_user_id,
        role=role,
        email=email,
        email_verified_at=email_verified_at,
        phone=f"+1555{unique[:10]}",
        first_name="Lifecycle",
        last_name="State",
        date_of_birth=date(1990, 1, 1),
        account_status=account_status,
        hosting_status="eligible",
        deleted_at=deleted_at,
    )
    with _session() as db:
        db.add(user)
        db.commit()
        return user.id


def _set_user_state(
    user_id: uuid.UUID,
    *,
    account_status: str | None = None,
    role: str | None = None,
) -> None:
    from backend.models import User

    with _session() as db:
        user = db.get(User, user_id)
        assert user is not None
        if account_status is not None:
            user.account_status = account_status
        if role is not None:
            user.role = role
        user.updated_at = datetime.now(timezone.utc)
        db.add(user)
        db.commit()


def _user_snapshot(user_id: uuid.UUID) -> dict[str, object]:
    from backend.models import User

    with _session() as db:
        user = db.get(User, user_id)
        assert user is not None
        return {
            "auth_user_id": user.auth_user_id,
            "email": user.email,
            "role": user.role,
            "account_status": user.account_status,
            "deleted_at": user.deleted_at,
        }


@pytest.mark.requirement("WS03-02-R4", "WS03-02-R6", "WS03-02-R9")
def test_suspension_is_enforced_on_next_request_and_not_undone_by_sync(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.auth_account_service import sync_user_workflow

    uid = f"ws03-02-suspended-{uuid.uuid4()}"
    email = f"ws03-02-suspended-{uuid.uuid4()}@example.invalid"
    _install_provider_identity(monkeypatch, uid=uid, email=email)
    _install_sync_identity(monkeypatch, uid=uid, email=email)
    user_id = _create_user(
        auth_user_id=uid,
        email=email,
        email_verified_at=datetime.now(timezone.utc),
    )

    assert client.get("/my-games", headers=_auth_headers()).status_code == 200

    _set_user_state(user_id, account_status="suspended")
    suspended_response = client.get("/my-games", headers=_auth_headers())

    assert suspended_response.status_code == 403
    assert suspended_response.json()["detail"] == "Active account required."

    with _session() as db:
        synced_user = sync_user_workflow("Bearer valid-token", db)
        assert synced_user.id == user_id
        assert synced_user.account_status == "suspended"

    assert _user_snapshot(user_id)["account_status"] == "suspended"

    _set_user_state(user_id, account_status="active")
    assert client.get("/my-games", headers=_auth_headers()).status_code == 200


@pytest.mark.requirement("WS03-02-R6")
@pytest.mark.parametrize(
    ("account_status", "deleted_at"),
    [
        ("pending_deletion", None),
        ("deleted", datetime.now(timezone.utc)),
    ],
)
def test_terminal_lifecycle_states_are_not_resurrected_by_sync_or_provider_identity(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    account_status: str,
    deleted_at: datetime | None,
) -> None:
    from backend.services.auth_account_service import sync_user_workflow

    uid = f"ws03-02-terminal-{account_status}-{uuid.uuid4()}"
    email = f"ws03-02-terminal-{uuid.uuid4()}@example.invalid"
    _install_provider_identity(monkeypatch, uid=uid, email=email)
    _install_sync_identity(monkeypatch, uid=uid, email=email)
    user_id = _create_user(
        auth_user_id=uid,
        email=email,
        account_status=account_status,
        deleted_at=deleted_at,
        email_verified_at=datetime.now(timezone.utc),
    )
    before = _user_snapshot(user_id)

    response = client.get("/my-games", headers=_auth_headers())

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."

    with _session() as db:
        with pytest.raises(HTTPException) as exc_info:
            sync_user_workflow("Bearer valid-token", db)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "A user with this email already exists."
    assert _user_snapshot(user_id) == before


@pytest.mark.requirement("WS03-02-R9")
def test_admin_role_change_is_seen_on_next_admin_request(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uid = f"ws03-02-admin-fresh-{uuid.uuid4()}"
    email = f"ws03-02-admin-fresh-{uuid.uuid4()}@example.invalid"
    _install_provider_identity(monkeypatch, uid=uid, email=email)
    user_id = _create_user(
        auth_user_id=uid,
        email=email,
        role="admin",
        email_verified_at=datetime.now(timezone.utc),
    )

    first_response = client.get("/admin/me", headers=_auth_headers())
    assert first_response.status_code == 200
    assert first_response.json()["role"] == "admin"

    _set_user_state(user_id, role="player")
    second_response = client.get("/admin/me", headers=_auth_headers())

    assert second_response.status_code == 403
    assert second_response.json()["detail"] == "Admin access required."
