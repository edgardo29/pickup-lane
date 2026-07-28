from __future__ import annotations

import argparse
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from firebase_admin import auth
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.firebase_admin_client import (
    FirebaseAdminConfigError,
    initialize_firebase_admin,
)
from backend.models import User
from backend.services.auth_account_service import add_missing_user_context_rows


DEFAULT_PASSWORD = "password1"


@dataclass(frozen=True)
class ManualSeedUser:
    email: str
    password: str
    first_name: str
    last_name: str
    date_of_birth: date
    phone_suffix: str

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


def build_seed_users(password: str) -> list[ManualSeedUser]:
    return [
        ManualSeedUser(
            email="infinite_10@live.com",
            password=password,
            first_name="Edgardo",
            last_name="Infante",
            date_of_birth=date(1995, 1, 1),
            phone_suffix="9101",
        ),
        ManualSeedUser(
            email="test2@test.com",
            password=password,
            first_name="Test",
            last_name="Two",
            date_of_birth=date(1996, 2, 2),
            phone_suffix="9102",
        ),
        ManualSeedUser(
            email="test3@test.com",
            password=password,
            first_name="Test",
            last_name="Three",
            date_of_birth=date(1997, 3, 3),
            phone_suffix="9103",
        ),
    ]


def upsert_firebase_user(seed_user: ManualSeedUser) -> str:
    try:
        firebase_user = auth.get_user_by_email(seed_user.email)
        auth.update_user(
            firebase_user.uid,
            password=seed_user.password,
            display_name=seed_user.display_name,
            email_verified=True,
            disabled=False,
        )
        return firebase_user.uid
    except auth.UserNotFoundError:
        firebase_user = auth.create_user(
            email=seed_user.email,
            password=seed_user.password,
            display_name=seed_user.display_name,
            email_verified=True,
            disabled=False,
        )
        return firebase_user.uid


def find_existing_user(
    db: Session,
    *,
    email: str,
    firebase_uid: str,
) -> User | None:
    by_uid = db.scalar(select(User).where(User.auth_user_id == firebase_uid))
    by_email = db.scalar(
        select(User).where(func.lower(User.email) == email.lower())
    )

    if by_uid is not None and by_email is not None and by_uid.id != by_email.id:
        raise RuntimeError(
            "Refusing to merge two local users: one matches the Firebase UID "
            f"and another matches {email}."
        )

    return by_uid or by_email


def upsert_postgres_user(firebase_uid: str, seed_user: ManualSeedUser) -> User:
    timestamp = datetime.now(timezone.utc)

    with SessionLocal() as db:
        user = find_existing_user(
            db,
            email=seed_user.email,
            firebase_uid=firebase_uid,
        )
        created = user is None

        if user is None:
            user = User(id=uuid.uuid4(), role="player")

        user.auth_user_id = firebase_uid
        user.email = seed_user.email
        user.email_verified_at = timestamp
        if not user.phone:
            user.phone = f"+1555900{seed_user.phone_suffix}"
        user.first_name = seed_user.first_name
        user.last_name = seed_user.last_name
        user.date_of_birth = seed_user.date_of_birth
        user.account_status = "active"
        if not user.hosting_status:
            user.hosting_status = "not_eligible"
        user.deleted_at = None
        user.updated_at = timestamp

        db.add(user)
        db.flush()
        add_missing_user_context_rows(user, db)
        db.commit()
        db.refresh(user)

        action = "created" if created else "updated"
        print(
            f"{action}: {seed_user.email} | {seed_user.password} | "
            f"{user.id} | role={user.role}"
        )
        return user


def seed_manual_test_users(password: str) -> None:
    initialize_firebase_admin()
    print("Manual test users ready:")
    print("")

    for seed_user in build_seed_users(password):
        firebase_uid = upsert_firebase_user(seed_user)
        upsert_postgres_user(firebase_uid, seed_user)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create local Firebase/Auth DB users for manual QA."
        )
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help=f"Password to set for every seeded user. Default: {DEFAULT_PASSWORD}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        seed_manual_test_users(args.password)
    except FirebaseAdminConfigError as exc:
        print(f"Firebase Admin is not configured: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
