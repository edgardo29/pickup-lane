from __future__ import annotations

import inspect
import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi.params import Depends
from fastapi.testclient import TestClient

pytestmark = pytest.mark.suite_type("ordinary")


def _install_provider_identity(
    monkeypatch: pytest.MonkeyPatch,
    *,
    uid: str = "firebase-admin",
    email: str = "admin@example.invalid",
    email_verified: bool = True,
    extra_claims: dict[str, object] | None = None,
) -> None:
    import backend.services.auth_service as auth_service

    payload: dict[str, object] = {
        "uid": uid,
        "email": email,
        "email_verified": email_verified,
        "auth_time": 1_700_000_000,
    }
    if extra_claims:
        payload.update(extra_claims)

    def verify_token(token: str) -> dict[str, object]:
        if token != "valid-token":
            raise ValueError("invalid synthetic token")
        return dict(payload)

    monkeypatch.setattr(auth_service, "verify_firebase_token", verify_token)


def _auth_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"Authorization": "Bearer valid-token"}
    if extra:
        headers.update(extra)
    return headers


def _create_user(
    *,
    auth_user_id: str = "firebase-admin",
    email: str = "admin@example.invalid",
    role: str = "admin",
    account_status: str = "active",
    deleted_at: datetime | None = None,
    email_verified_at: datetime | None = None,
) -> uuid.UUID:
    from backend.database import SessionLocal
    from backend.models import User

    user = User(
        id=uuid.uuid4(),
        auth_user_id=auth_user_id,
        role=role,
        email=email,
        email_verified_at=email_verified_at,
        phone=f"+1555{uuid.uuid4().hex[:10]}",
        first_name="Admin",
        last_name="Boundary",
        date_of_birth=date(1988, 6, 7),
        account_status=account_status,
        hosting_status="eligible",
        deleted_at=deleted_at,
    )
    with SessionLocal() as db:
        db.add(user)
        db.commit()
        return user.id


@pytest.mark.requirement("WS03-01-R7", "WS03-01-R8")
def test_active_verified_local_admin_can_access_admin_me(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider_identity(monkeypatch)
    user_id = _create_user(email_verified_at=datetime.now(timezone.utc))

    response = client.get("/admin/me", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json()["user_id"] == str(user_id)
    assert response.json()["role"] == "admin"
    assert response.json()["account_status"] == "active"


@pytest.mark.requirement("WS03-01-R7", "WS03-01-R8")
@pytest.mark.parametrize(
    (
        "provider_verified",
        "local_role",
        "account_status",
        "deleted",
        "create_local_user",
        "expected_status",
        "expected_detail",
    ),
    [
        (False, "admin", "active", False, True, 403, "Verified email required."),
        (True, "admin", "suspended", False, True, 403, "Active account required."),
        (True, "admin", "deleted", True, True, 404, "User not found."),
        (True, "admin", "active", False, False, 404, "User not found."),
        (True, "player", "active", False, True, 403, "Admin access required."),
    ],
)
def test_admin_access_denies_unverified_missing_inactive_deleted_or_non_admin_users(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    provider_verified: bool,
    local_role: str,
    account_status: str,
    deleted: bool,
    create_local_user: bool,
    expected_status: int,
    expected_detail: str,
) -> None:
    _install_provider_identity(monkeypatch, email_verified=provider_verified)
    if create_local_user:
        _create_user(
            role=local_role,
            account_status=account_status,
            deleted_at=datetime.now(timezone.utc) if deleted else None,
            email_verified_at=datetime.now(timezone.utc),
        )

    response = client.get("/admin/me", headers=_auth_headers())

    assert response.status_code == expected_status
    assert response.json()["detail"] == expected_detail


@pytest.mark.requirement("WS03-01-R7", "WS03-01-R8")
def test_firebase_custom_claims_do_not_independently_grant_pickup_lane_admin(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider_identity(
        monkeypatch,
        uid="claim-admin",
        email="claim-admin@example.invalid",
        email_verified=True,
        extra_claims={
            "admin": True,
            "role": "admin",
            "permissions": ["admin:*"],
            "custom_claims": {"pickupLaneAdmin": True},
        },
    )
    _create_user(
        auth_user_id="claim-admin",
        email="claim-admin@example.invalid",
        role="player",
        email_verified_at=datetime.now(timezone.utc),
    )

    response = client.get("/admin/me", headers=_auth_headers())

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required."


@pytest.mark.requirement("WS03-01-R7", "WS03-01-R8")
def test_client_supplied_role_data_does_not_independently_grant_admin(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider_identity(
        monkeypatch,
        uid="client-claim-user",
        email="client-claim-user@example.invalid",
        email_verified=True,
    )
    _create_user(
        auth_user_id="client-claim-user",
        email="client-claim-user@example.invalid",
        role="player",
        email_verified_at=datetime.now(timezone.utc),
    )

    response = client.get(
        "/admin/me?role=admin&is_admin=true",
        headers=_auth_headers({"X-Role": "admin", "X-Admin": "true"}),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required."


@pytest.mark.requirement("WS03-01-R7")
def test_recent_active_admin_wrapper_layers_on_base_active_admin_dependency() -> None:
    import backend.services.auth_service as auth_service

    signature = inspect.signature(auth_service.require_recent_active_admin)
    current_user_default = signature.parameters["current_user"].default
    recent_identity_default = signature.parameters["_identity"].default

    assert isinstance(current_user_default, Depends)
    assert current_user_default.dependency is auth_service.require_active_admin
    assert isinstance(recent_identity_default, Depends)
    assert recent_identity_default.dependency is auth_service.require_recent_authentication
