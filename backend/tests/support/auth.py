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


def authenticate_as(user_id: str) -> None:
    from backend.main import app
    from backend.services.auth_service import get_current_app_user

    def override_current_user() -> User:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return db_user

    app.dependency_overrides[get_current_app_user] = override_current_user


def authenticate_optional_as(user_id: str) -> None:
    from backend.main import app
    from backend.services.auth_service import get_optional_current_app_user

    def override_current_user() -> User:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return db_user

    app.dependency_overrides[get_optional_current_app_user] = override_current_user


def set_user_role(user_id: str, role: str) -> None:
    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        db_user.role = role
        db.commit()


def run_as_temporary_admin(client: TestClient, request_fn):
    from backend.main import app
    from backend.services.auth_service import get_current_app_user

    had_previous_override = get_current_app_user in app.dependency_overrides
    previous_override = app.dependency_overrides.get(get_current_app_user)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])

    try:
        return request_fn()
    finally:
        if had_previous_override and previous_override is not None:
            app.dependency_overrides[get_current_app_user] = previous_override
        else:
            app.dependency_overrides.pop(get_current_app_user, None)
