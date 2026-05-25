from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from firebase_admin import auth
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.firebase_admin_client import (
    FirebaseAdminConfigError,
    initialize_firebase_admin,
)
from backend.models import User
from backend.routes.auth_routes import add_missing_user_context_rows


class BootstrapAdminError(RuntimeError):
    pass


def get_active_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User).where(
            func.lower(User.email) == email,
            User.account_status == "active",
            User.deleted_at.is_(None),
        )
    )


def verify_firebase_user(email: str, user: User) -> None:
    try:
        initialize_firebase_admin()
        firebase_user = auth.get_user_by_email(email)
    except FirebaseAdminConfigError:
        raise
    except auth.UserNotFoundError as exc:
        raise BootstrapAdminError(
            "No Firebase Auth user exists for that email. Create the account first."
        ) from exc

    if firebase_user.disabled:
        raise BootstrapAdminError("That Firebase Auth user is disabled.")

    if user.auth_user_id != firebase_user.uid:
        raise BootstrapAdminError(
            "The app user does not match the Firebase Auth user for that email."
        )


def bootstrap_admin(email: str) -> User:
    normalized_email = email.strip().lower()

    if not normalized_email or "@" not in normalized_email:
        raise BootstrapAdminError("Pass a valid email address.")

    with SessionLocal() as db:
        user = get_active_user_by_email(db, normalized_email)

        if user is None:
            raise BootstrapAdminError(
                "No active app user exists for that email. Sign up and finish "
                "the app profile first."
            )

        if not user.auth_user_id:
            raise BootstrapAdminError(
                "That app user is not linked to a Firebase Auth account."
            )

        verify_firebase_user(normalized_email, user)

        user.role = "admin"
        user.updated_at = datetime.now(timezone.utc)
        db.add(user)
        add_missing_user_context_rows(user, db)
        db.commit()
        db.refresh(user)
        return user


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap an existing Firebase-backed app user as an admin."
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Email address for the existing app user to mark as admin.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        user = bootstrap_admin(args.email)
    except (BootstrapAdminError, FirebaseAdminConfigError) as exc:
        print(f"Admin bootstrap failed: {exc}", file=sys.stderr)
        return 1

    print("Admin bootstrap complete.")
    print(f"email: {user.email}")
    print(f"user_id: {user.id}")
    print(f"role: {user.role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
