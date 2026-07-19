"""Firebase authentication and route dependencies."""

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.firebase_admin_client import (
    FirebaseAdminConfigError,
    verify_firebase_token,
)
from backend.models import User
from backend.services.hosting_access_service import apply_verified_hosting_eligibility
from backend.services.user_service import build_user_conflict_detail

ADMIN_ROLE = "admin"


def get_active_user_by_auth_id(auth_user_id: str, db: Session) -> User | None:
    user = db.scalar(
        select(User).where(
            User.auth_user_id == auth_user_id,
            User.account_status != "pending_deletion",
        )
    )

    if user is None or user.deleted_at is not None:
        return None

    return user


def get_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header.",
        )

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header.",
        )

    return token


def get_decoded_firebase_token(authorization: str | None) -> dict:
    token = get_bearer_token(authorization)

    try:
        decoded_token = verify_firebase_token(token)
    except FirebaseAdminConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        ) from exc

    auth_user_id = decoded_token.get("uid")

    if not auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing a Firebase user id.",
        )

    return decoded_token


def get_auth_user_id_from_token(authorization: str | None) -> str:
    return get_decoded_firebase_token(authorization)["uid"]


def sync_email_verification_from_firebase(
    user: User,
    email_verified: bool,
    db: Session,
) -> bool:
    if not email_verified:
        return False

    now = datetime.now(timezone.utc)
    did_change = False

    if user.email_verified_at is None:
        user.email_verified_at = now
        user.updated_at = now
        did_change = True

    did_change = (
        apply_verified_hosting_eligibility(user, verified_at=now) or did_change
    )
    if did_change:
        db.add(user)

    return did_change


def commit_user_sync(db: Session, user: User) -> User:
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise

    return user


def get_authenticated_user_from_token(
    authorization: str | None, db: Session
) -> User:
    decoded_token = get_decoded_firebase_token(authorization)
    auth_user_id = decoded_token["uid"]
    user = get_active_user_by_auth_id(auth_user_id, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if sync_email_verification_from_firebase(
        user,
        bool(decoded_token.get("email_verified")),
        db,
    ):
        try:
            return commit_user_sync(db, user)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=build_user_conflict_detail(exc),
            ) from exc

    return user


def get_current_app_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    return get_authenticated_user_from_token(authorization, db)


def get_optional_current_app_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    if not authorization:
        return None

    return get_authenticated_user_from_token(authorization, db)


def require_active_account(user: User) -> None:
    if user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active account required.",
        )


def require_active_user(
    current_user: User = Depends(get_current_app_user),
) -> User:
    require_active_account(current_user)
    return current_user


def user_is_active_admin(user: User) -> bool:
    return (
        user.role == ADMIN_ROLE
        and user.account_status == "active"
        and user.deleted_at is None
    )


def require_active_admin_user(user: User) -> None:
    if not user_is_active_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )


def require_active_admin(
    current_user: User = Depends(get_current_app_user),
) -> User:
    require_active_admin_user(current_user)
    return current_user
