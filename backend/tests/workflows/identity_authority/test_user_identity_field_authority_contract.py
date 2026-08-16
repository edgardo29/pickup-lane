from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.suite_type("ordinary")


def _install_provider_identity(
    monkeypatch: pytest.MonkeyPatch,
    *,
    uid: str = "firebase-user",
    email: str = "provider-sync@example.invalid",
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


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer valid-token"}


def _create_user(
    *,
    auth_user_id: str = "firebase-user",
    email: str = "profile-user@example.invalid",
    role: str = "player",
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
        first_name="Profile",
        last_name="Owner",
        date_of_birth=date(1990, 1, 1),
        profile_photo_url=None,
        account_status="active",
        hosting_status="eligible",
    )
    with SessionLocal() as db:
        db.add(user)
        db.commit()
        return user.id


def _identity_state(user_id: uuid.UUID) -> dict[str, object]:
    from backend.database import SessionLocal
    from backend.models import User

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        return {
            "auth_user_id": user.auth_user_id,
            "email": user.email,
            "email_verified_at": user.email_verified_at,
            "role": user.role,
            "account_status": user.account_status,
            "deleted_at": user.deleted_at,
            "profile_photo_url": user.profile_photo_url,
        }


@pytest.mark.requirement("WS03-01-R6")
def test_users_me_accepts_only_approved_profile_fields(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider_identity(monkeypatch)
    user_id = _create_user(
        email="profile-user@example.invalid",
        email_verified_at=datetime.now(timezone.utc),
    )

    response = client.patch(
        "/users/me",
        headers=_auth_headers(),
        json={
            "phone": "+15555550123",
            "first_name": "Allowed",
            "last_name": "Profile",
            "date_of_birth": "1992-04-05",
            "home_city": "Austin",
            "home_state": "TX",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user_id)
    assert body["phone"] == "+15555550123"
    assert body["first_name"] == "Allowed"
    assert body["last_name"] == "Profile"
    assert body["date_of_birth"] == "1992-04-05"
    assert body["home_city"] == "Austin"
    assert body["home_state"] == "TX"


@pytest.mark.requirement("WS03-01-R5", "WS03-01-R6")
@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("auth_user_id", "attacker-uid"),
        ("email", "attacker@example.invalid"),
        ("email_verified", True),
        ("email_verified_at", "2030-01-01T00:00:00Z"),
        ("role", "admin"),
        ("account_status", "active"),
        ("deleted_at", "2030-01-01T00:00:00Z"),
        ("created_at", "2030-01-01T00:00:00Z"),
        ("updated_at", "2030-01-01T00:00:00Z"),
        ("auth_time", 1_900_000_000),
        ("last_login_at", "2030-01-01T00:00:00Z"),
        ("profile_photo_url", "https://provider.example.invalid/avatar.png"),
        ("permissions", ["admin:*"]),
        ("owner_user_id", str(uuid.uuid4())),
        ("admin", True),
        ("is_admin", True),
        ("provider_id", "firebase"),
    ],
)
def test_users_me_rejects_identity_provider_admin_and_server_owned_fields(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    field_value: Any,
) -> None:
    _install_provider_identity(monkeypatch)
    user_id = _create_user(email_verified_at=datetime.now(timezone.utc))
    before = _identity_state(user_id)

    response = client.patch(
        "/users/me",
        headers=_auth_headers(),
        json={field_name: field_value},
    )

    assert response.status_code == 422
    assert _identity_state(user_id) == before


@pytest.mark.requirement("WS03-01-R6")
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/users"),
        ("PATCH", f"/users/{uuid.uuid4()}"),
        ("DELETE", f"/users/{uuid.uuid4()}"),
    ],
)
def test_generic_user_mutation_routes_remain_unavailable(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
) -> None:
    _install_provider_identity(monkeypatch, uid="admin-uid", email_verified=True)
    _create_user(
        auth_user_id="admin-uid",
        email="admin@example.invalid",
        role="admin",
        email_verified_at=datetime.now(timezone.utc),
    )

    response = client.request(method, path, headers=_auth_headers(), json={})

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Generic user mutations are disabled. Use dedicated account support workflows."
    )


@pytest.mark.requirement("WS03-01-R5", "WS03-01-R6")
def test_provider_authenticated_sync_owns_email_and_verification_snapshots(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider_identity(
        monkeypatch,
        uid="sync-uid",
        email="current-provider@example.invalid",
        email_verified=True,
    )
    user_id = _create_user(
        auth_user_id="sync-uid",
        email="old-snapshot@example.invalid",
        email_verified_at=None,
    )

    response = client.post("/auth/sync-user", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json()["email"] == "current-provider@example.invalid"
    assert response.json()["email_verified_at"] is not None
    from backend.database import SessionLocal
    from backend.models import User

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        assert user.email == "current-provider@example.invalid"
        assert user.email_verified_at is not None


@pytest.mark.requirement("WS03-01-R5", "WS03-01-R6")
def test_provider_authenticated_sync_conflicts_fail_without_creating_second_identity(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider_identity(
        monkeypatch,
        uid="new-provider-uid",
        email="claimed-email@example.invalid",
        email_verified=True,
    )
    _create_user(
        auth_user_id="existing-provider-uid",
        email="claimed-email@example.invalid",
        email_verified_at=datetime.now(timezone.utc),
    )

    response = client.post("/auth/sync-user", headers=_auth_headers())

    assert response.status_code == 409
    assert response.json()["detail"] == "A user with this email already exists."
    from sqlalchemy import select

    from backend.database import SessionLocal
    from backend.models import User

    with SessionLocal() as db:
        assert (
            db.scalar(
                select(User).where(User.auth_user_id == "new-provider-uid")
            )
            is None
        )
