from uuid import uuid4

from fastapi.testclient import TestClient


def unique_suffix() -> str:
    return uuid4().hex


def create_user(_client: TestClient | None = None, **overrides: object) -> dict:
    from backend.database import SessionLocal
    from backend.models import User
    from backend.schemas import UserCreate, UserRead

    suffix = unique_suffix()
    payload = {
        "auth_user_id": f"firebase-{suffix}",
        "email": f"user-{suffix}@example.com",
        "phone": f"+1555{suffix[:7]}",
        "first_name": "Test",
        "last_name": "User",
        "date_of_birth": "1995-01-01",
        "home_city": "Chicago",
        "home_state": "IL",
    }
    payload.update(overrides)
    user_payload = UserCreate.model_validate(payload)

    with SessionLocal() as db:
        db_user = User(id=uuid4(), **user_payload.model_dump())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return UserRead.model_validate(db_user).model_dump(mode="json")
