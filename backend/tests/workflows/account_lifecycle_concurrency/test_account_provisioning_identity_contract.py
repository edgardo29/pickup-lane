from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, func, inspect, select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.suite_type("ordinary")


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _auth_header(token: str) -> str:
    return f"Bearer {token}"


def _install_sync_identities(
    monkeypatch: pytest.MonkeyPatch,
    identities_by_token: dict[str, tuple[str, str, bool]],
) -> None:
    from backend.services.auth_service import VerifiedFirebaseIdentity
    import backend.services.auth_account_service as auth_account_service

    def identity_from_header(authorization: str | None) -> VerifiedFirebaseIdentity:
        assert authorization is not None
        token = authorization.removeprefix("Bearer ").strip()
        uid, email, email_verified = identities_by_token[token]
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
    db: Session,
    *,
    auth_user_id: str,
    email: str,
    role: str = "player",
    account_status: str = "active",
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
        last_name="Identity",
        date_of_birth=date(1990, 1, 1),
        account_status=account_status,
        hosting_status="eligible",
    )
    db.add(user)
    db.commit()
    return user.id


def _count_rows(db: Session, model: type[object], *criteria: object) -> int:
    statement = select(func.count()).select_from(model)
    if criteria:
        statement = statement.where(*criteria)
    return int(db.scalar(statement) or 0)


@pytest.mark.requirement("WS03-02-R1", "WS03-02-R3")
def test_live_database_constraints_pin_identity_and_one_to_one_context_rows() -> None:
    with _session() as db:
        inspector = inspect(db.bind)

        user_unique_constraints = {
            constraint["name"] for constraint in inspector.get_unique_constraints("users")
        }
        user_check_constraints = {
            constraint["name"] for constraint in inspector.get_check_constraints("users")
        }

        assert "uq_users_auth_user_id" in user_unique_constraints
        assert "uq_users_email" in user_unique_constraints
        assert "ck_users_account_status" in user_check_constraints
        assert "ck_users_role" in user_check_constraints

        assert inspector.get_pk_constraint("user_settings")[
            "constrained_columns"
        ] == ["user_id"]
        assert inspector.get_pk_constraint("user_stats")[
            "constrained_columns"
        ] == ["user_id"]
        assert any(
            foreign_key["referred_table"] == "users"
            and foreign_key["constrained_columns"] == ["user_id"]
            for foreign_key in inspector.get_foreign_keys("user_settings")
        )
        assert any(
            foreign_key["referred_table"] == "users"
            and foreign_key["constrained_columns"] == ["user_id"]
            for foreign_key in inspector.get_foreign_keys("user_stats")
        )


@pytest.mark.requirement("WS03-02-R1", "WS03-02-R3", "WS03-02-R4")
def test_same_uid_repeat_sync_preserves_identity_refreshes_snapshots_and_repairs_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import User, UserSettings, UserStats
    from backend.services.auth_account_service import sync_user_workflow

    uid = f"ws03-02-repeat-{uuid.uuid4()}"
    _install_sync_identities(
        monkeypatch,
        {
            "first": (uid, "Old.Provider@example.invalid", False),
            "repeat": (uid, "New.Provider@example.invalid", True),
        },
    )

    with _session() as db:
        first_user = sync_user_workflow(_auth_header("first"), db)
        first_user_id = first_user.id

        db.execute(delete(UserSettings).where(UserSettings.user_id == first_user_id))
        db.execute(delete(UserStats).where(UserStats.user_id == first_user_id))
        db.commit()

        repeated_user = sync_user_workflow(_auth_header("repeat"), db)

        assert repeated_user.id == first_user_id
        assert repeated_user.auth_user_id == uid
        assert repeated_user.email == "new.provider@example.invalid"
        assert repeated_user.email_verified_at is not None
        assert repeated_user.account_status == "active"
        assert repeated_user.role == "player"
        assert _count_rows(db, User, User.auth_user_id == uid) == 1
        assert (
            _count_rows(db, User, User.email == "new.provider@example.invalid") == 1
        )
        assert _count_rows(db, UserSettings, UserSettings.user_id == first_user_id) == 1
        assert _count_rows(db, UserStats, UserStats.user_id == first_user_id) == 1

        sync_user_workflow(_auth_header("repeat"), db)

        assert _count_rows(db, User, User.auth_user_id == uid) == 1
        assert _count_rows(db, UserSettings, UserSettings.user_id == first_user_id) == 1
        assert _count_rows(db, UserStats, UserStats.user_id == first_user_id) == 1


@pytest.mark.requirement("WS03-02-R1", "WS03-02-R5")
def test_different_uid_same_email_conflicts_without_relinking_existing_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import User
    from backend.services.auth_account_service import sync_user_workflow

    existing_uid = f"ws03-02-existing-{uuid.uuid4()}"
    attacking_uid = f"ws03-02-attacker-{uuid.uuid4()}"
    claimed_email = f"claimed-{uuid.uuid4()}@example.invalid"
    _install_sync_identities(
        monkeypatch,
        {"attacker": (attacking_uid, claimed_email, True)},
    )

    with _session() as db:
        existing_id = _create_user(
            db,
            auth_user_id=existing_uid,
            email=claimed_email,
            email_verified_at=datetime.now(timezone.utc),
        )

        with pytest.raises(HTTPException) as exc_info:
            sync_user_workflow(_auth_header("attacker"), db)

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "A user with this email already exists."

        existing_user = db.get(User, existing_id)
        assert existing_user is not None
        assert existing_user.auth_user_id == existing_uid
        assert existing_user.email == claimed_email
        assert _count_rows(db, User, User.auth_user_id == attacking_uid) == 0
        assert _count_rows(db, User, User.email == claimed_email) == 1
