from uuid import UUID

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.models import User
from backend.tests.support.factories import create_user

__all__ = [
    "authenticate_as",
    "authenticate_optional_as",
    "run_as_temporary_admin",
    "set_user_role",
]


def authenticate_as(user_id: str, target_app=None) -> None:
    from backend.main import app
    from backend.services.auth_service import (
        VerifiedFirebaseIdentity,
        get_current_app_user,
        get_verified_firebase_identity,
        require_verified_user,
    )

    app_with_overrides = target_app or app

    def override_current_user() -> User:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return db_user

    def override_firebase_identity() -> VerifiedFirebaseIdentity:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return VerifiedFirebaseIdentity(
                auth_user_id=db_user.auth_user_id,
                email=db_user.email,
                email_verified=True,
            )

    app_with_overrides.dependency_overrides[get_current_app_user] = override_current_user
    app_with_overrides.dependency_overrides[get_verified_firebase_identity] = (
        override_firebase_identity
    )
    app_with_overrides.dependency_overrides[require_verified_user] = override_current_user


def authenticate_optional_as(user_id: str, target_app=None) -> None:
    from backend.main import app
    from backend.services.auth_service import get_optional_current_app_user

    app_with_overrides = target_app or app

    def override_current_user() -> User:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return db_user

    app_with_overrides.dependency_overrides[get_optional_current_app_user] = (
        override_current_user
    )


def set_user_role(user_id: str, role: str) -> None:
    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        db_user.role = role
        db.commit()


def run_as_temporary_admin(client: TestClient, request_fn):
    from backend.services.auth_service import (
        get_current_app_user,
        get_verified_firebase_identity,
        require_verified_user,
    )

    app_with_overrides = client.app
    had_previous_override = get_current_app_user in app_with_overrides.dependency_overrides
    previous_override = app_with_overrides.dependency_overrides.get(get_current_app_user)
    had_previous_identity_override = (
        get_verified_firebase_identity in app_with_overrides.dependency_overrides
    )
    previous_identity_override = app_with_overrides.dependency_overrides.get(
        get_verified_firebase_identity
    )
    had_previous_verified_override = (
        require_verified_user in app_with_overrides.dependency_overrides
    )
    previous_verified_override = app_with_overrides.dependency_overrides.get(
        require_verified_user
    )
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"], target_app=app_with_overrides)

    try:
        return request_fn()
    finally:
        if had_previous_override and previous_override is not None:
            app_with_overrides.dependency_overrides[get_current_app_user] = (
                previous_override
            )
        else:
            app_with_overrides.dependency_overrides.pop(get_current_app_user, None)
        if had_previous_identity_override and previous_identity_override is not None:
            app_with_overrides.dependency_overrides[get_verified_firebase_identity] = (
                previous_identity_override
            )
        else:
            app_with_overrides.dependency_overrides.pop(get_verified_firebase_identity, None)
        if had_previous_verified_override and previous_verified_override is not None:
            app_with_overrides.dependency_overrides[require_verified_user] = (
                previous_verified_override
            )
        else:
            app_with_overrides.dependency_overrides.pop(require_verified_user, None)
