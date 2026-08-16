from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.suite_type("ordinary")

SELF_ALLOWED_FIELDS = {
    "id",
    "role",
    "email",
    "email_verified_at",
    "phone",
    "first_name",
    "last_name",
    "date_of_birth",
    "profile_photo_url",
    "home_city",
    "home_state",
    "account_status",
    "hosting_status",
    "member_since",
}
SELF_PROHIBITED_FIELDS = {
    "auth_user_id",
    "stripe_customer_id",
    "created_at",
    "updated_at",
    "deleted_at",
}
ADMIN_OPERATIONAL_FIELDS = {
    "auth_user_id",
    "created_at",
    "updated_at",
    "deleted_at",
}


def _session() -> Session:
    from backend.database import SessionLocal

    return SessionLocal()


def _create_user(
    db: Session,
    *,
    role: str = "player",
    email_prefix: str = "b2-user",
):
    from backend.models import User

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        auth_user_id=f"firebase-{email_prefix}-{user_id}",
        role=role,
        email=f"{email_prefix}-{user_id}@example.invalid",
        email_verified_at=datetime.now(UTC),
        phone=f"+1555{str(user_id.int)[-10:]}",
        first_name="B2",
        last_name="Self",
        date_of_birth=date(1995, 4, 12),
        profile_photo_url="https://cdn.example.invalid/profile.png",
        home_city="Chicago",
        home_state="IL",
        account_status="active",
        hosting_status="eligible",
    )
    db.add(user)
    db.flush()
    return user


def _install_current_user_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import get_current_app_user

    app.dependency_overrides[get_current_app_user] = lambda: user


def _install_synced_user_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import get_synced_current_app_user

    app.dependency_overrides[get_synced_current_app_user] = lambda: user


def _install_active_admin_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import require_active_admin

    app.dependency_overrides[require_active_admin] = lambda: user


def _route(method: str, path: str) -> APIRoute:
    from backend.main import app

    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


def _commit_and_detach(db: Session, *objects: object) -> None:
    db.commit()
    for item in objects:
        db.refresh(item)
        db.expunge(item)


def _assert_self_user_response(data: dict[str, object]) -> None:
    assert set(data) == SELF_ALLOWED_FIELDS
    assert SELF_PROHIBITED_FIELDS.isdisjoint(data)
    assert data["email_verified_at"] is not None
    assert data["member_since"] is not None


@pytest.mark.requirement("WS02-05B2-R3")
def test_self_auth_and_profile_responses_omit_provider_uid_and_audit_fields(
    client: TestClient,
) -> None:
    with _session() as db:
        user = _create_user(db, email_prefix="b2-self")
        user_id = user.id
        _commit_and_detach(db, user)

    _install_synced_user_override(user)
    auth_response = client.get("/auth/me")
    assert auth_response.status_code == 200
    auth_data = auth_response.json()
    _assert_self_user_response(auth_data)
    assert auth_data["id"] == str(user_id)

    _install_current_user_override(user)
    profile_response = client.get("/users/me")
    assert profile_response.status_code == 200
    _assert_self_user_response(profile_response.json())

    update_response = client.patch(
        "/users/me",
        json={"first_name": "Updated", "home_city": "Evanston"},
    )
    assert update_response.status_code == 200
    updated_data = update_response.json()
    _assert_self_user_response(updated_data)
    assert updated_data["first_name"] == "Updated"
    assert updated_data["home_city"] == "Evanston"
    assert updated_data["email_verified_at"] == auth_data["email_verified_at"]


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS02-05B2-R3")
def test_self_account_routes_declare_self_user_response_models() -> None:
    from backend.schemas.user_schema import SelfUserRead

    assert _route("GET", "/auth/me").response_model is SelfUserRead
    assert _route("POST", "/auth/sync-user").response_model is SelfUserRead
    assert _route("DELETE", "/auth/account").response_model is SelfUserRead
    assert _route("GET", "/users/me").response_model is SelfUserRead
    assert _route("PATCH", "/users/me").response_model is SelfUserRead


@pytest.mark.requirement("WS02-05B2-R3")
def test_admin_user_responses_keep_operational_identity_fields_behind_admin(
    client: TestClient,
) -> None:
    from backend.schemas.user_schema import AdminUserRead

    with _session() as db:
        target_user = _create_user(db, email_prefix="b2-admin-target")
        admin = _create_user(db, role="admin", email_prefix="b2-admin-reader")
        target_user_id = target_user.id
        auth_user_id = target_user.auth_user_id
        _commit_and_detach(db, admin)

    _install_active_admin_override(admin)

    detail_response = client.get(f"/users/{target_user_id}")
    assert detail_response.status_code == 200
    detail_data = detail_response.json()
    assert SELF_ALLOWED_FIELDS.issubset(detail_data)
    assert ADMIN_OPERATIONAL_FIELDS.issubset(detail_data)
    assert detail_data["auth_user_id"] == auth_user_id
    assert detail_data["created_at"] is not None
    assert detail_data["updated_at"] is not None

    list_response = client.get("/users")
    assert list_response.status_code == 200
    listed_user = next(item for item in list_response.json() if item["id"] == str(target_user_id))
    assert ADMIN_OPERATIONAL_FIELDS.issubset(listed_user)

    assert _route("GET", "/users").response_model == list[AdminUserRead]
    assert _route("GET", "/users/{user_id}").response_model is AdminUserRead
    assert _route("POST", "/users").response_model is AdminUserRead
    assert _route("PATCH", "/users/{user_id}").response_model is AdminUserRead
    assert _route("DELETE", "/users/{user_id}").response_model is AdminUserRead
