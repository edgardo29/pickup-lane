"""Firebase authentication and route dependencies."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.firebase_admin_client import (
    FirebaseAdminConfigError,
    FirebaseIdentityUnavailableError,
    verify_firebase_token,
)
from backend.models import User
from backend.observability.timeouts import PublicTimeoutError
from backend.settings import get_settings
from backend.services.hosting_access_service import apply_verified_hosting_eligibility
from backend.services.user_service import build_user_conflict_detail

ADMIN_ROLE = "admin"
RECENT_AUTH_REQUIRED_CODE = "AUTH.RECENT_AUTH_REQUIRED"
RECENT_AUTH_REQUIRED_MESSAGE = "Confirm your identity to continue."


@dataclass(frozen=True)
class VerifiedFirebaseIdentity:
    auth_user_id: str
    email: str | None
    email_verified: bool
    authenticated_at: datetime | None = None
    provider_account_active: bool = True


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


def get_verified_firebase_identity_from_authorization(
    authorization: str | None,
) -> VerifiedFirebaseIdentity:
    token = get_bearer_token(authorization)

    try:
        decoded_token = verify_firebase_token(token)
    except FirebaseAdminConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication provider is not configured.",
        ) from exc
    except PublicTimeoutError:
        raise
    except FirebaseIdentityUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication provider is unavailable.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        ) from exc

    auth_user_id = decoded_token.get("uid")

    if not isinstance(auth_user_id, str) or not auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing a Firebase user id.",
        )

    email = decoded_token.get("email")
    if not isinstance(email, str) or not email.strip():
        email = None

    return VerifiedFirebaseIdentity(
        auth_user_id=auth_user_id,
        email=email.strip().lower() if isinstance(email, str) else None,
        email_verified=bool(decoded_token.get("email_verified")),
        authenticated_at=parse_provider_authenticated_at(decoded_token),
        provider_account_active=True,
    )


def get_verified_firebase_identity(
    authorization: str | None = Header(default=None),
) -> VerifiedFirebaseIdentity:
    return get_verified_firebase_identity_from_authorization(authorization)


def get_decoded_firebase_token(authorization: str | None) -> dict:
    identity = get_verified_firebase_identity_from_authorization(authorization)
    return {
        "uid": identity.auth_user_id,
        "email": identity.email,
        "email_verified": identity.email_verified,
    }


def parse_provider_authenticated_at(decoded_token: dict) -> datetime | None:
    auth_time = decoded_token.get("auth_time")
    if isinstance(auth_time, bool) or not isinstance(auth_time, int | float):
        return None
    if not math.isfinite(auth_time) or auth_time < 0:
        return None

    try:
        authenticated_at = datetime.fromtimestamp(auth_time, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None

    return authenticated_at


def is_recent_authentication(
    identity: VerifiedFirebaseIdentity,
    *,
    now: datetime,
    window: timedelta,
) -> bool:
    authenticated_at = identity.authenticated_at
    if authenticated_at is None:
        return False

    if authenticated_at.tzinfo is None:
        return False

    authenticated_at = authenticated_at.astimezone(timezone.utc)
    now = now.astimezone(timezone.utc)
    age = now - authenticated_at
    return timedelta(0) <= age <= window


def recent_authentication_window() -> timedelta:
    return timedelta(seconds=get_settings().recent_authentication_window_seconds)


def recent_authentication_error_detail() -> dict[str, str]:
    return {
        "code": RECENT_AUTH_REQUIRED_CODE,
        "message": RECENT_AUTH_REQUIRED_MESSAGE,
    }


def require_recent_authentication(
    identity: VerifiedFirebaseIdentity = Depends(get_verified_firebase_identity),
) -> VerifiedFirebaseIdentity:
    if not is_recent_authentication(
        identity,
        now=datetime.now(timezone.utc),
        window=recent_authentication_window(),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=recent_authentication_error_detail(),
        )

    return identity


def get_auth_user_id_from_token(authorization: str | None) -> str:
    return get_verified_firebase_identity_from_authorization(authorization).auth_user_id


def sync_primary_email_from_firebase(
    user: User,
    email: str | None,
    db: Session,
) -> bool:
    if not email:
        return False

    normalized_email = email.strip().lower()
    if not normalized_email or user.email == normalized_email:
        return False

    email_owner = db.scalar(
        select(User).where(
            User.email == normalized_email,
            User.id != user.id,
        )
    )
    if email_owner is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    user.email = normalized_email
    user.updated_at = datetime.now(timezone.utc)
    db.add(user)
    return True


def sync_firebase_identity_snapshots(
    user: User,
    identity: VerifiedFirebaseIdentity,
    db: Session,
) -> bool:
    did_change = sync_primary_email_from_firebase(user, identity.email, db)
    return (
        sync_email_verification_from_firebase(
            user,
            identity.email_verified,
            db,
        )
        or did_change
    )


def get_auth_user_id_from_decoded_token(decoded_token: dict) -> str:
    auth_user_id = decoded_token.get("uid")
    if not isinstance(auth_user_id, str) or not auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing a Firebase user id.",
        )
    return auth_user_id


def sync_email_verification_from_firebase(
    user: User,
    email_verified: bool,
    db: Session,
) -> bool:
    if not email_verified:
        if user.email_verified_at is None:
            return False

        user.email_verified_at = None
        user.updated_at = datetime.now(timezone.utc)
        db.add(user)
        return True

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
    authorization: str | None,
    db: Session,
    *,
    sync_snapshots: bool = False,
) -> User:
    identity = get_verified_firebase_identity_from_authorization(authorization)
    return get_authenticated_user_from_identity(
        identity,
        db,
        sync_snapshots=sync_snapshots,
    )


def get_current_app_user(
    identity: VerifiedFirebaseIdentity = Depends(get_verified_firebase_identity),
    db: Session = Depends(get_db),
) -> User:
    return get_authenticated_user_from_identity(identity, db, sync_snapshots=False)


def get_synced_current_app_user(
    identity: VerifiedFirebaseIdentity = Depends(get_verified_firebase_identity),
    db: Session = Depends(get_db),
) -> User:
    return get_authenticated_user_from_identity(identity, db, sync_snapshots=True)


def get_authenticated_user_from_identity(
    identity: VerifiedFirebaseIdentity,
    db: Session,
    *,
    sync_snapshots: bool = False,
) -> User:
    user = get_active_user_by_auth_id(identity.auth_user_id, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if sync_snapshots and sync_firebase_identity_snapshots(user, identity, db):
        try:
            return commit_user_sync(db, user)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=build_user_conflict_detail(exc),
            ) from exc

    return user


def get_current_app_user_from_authorization(
    authorization: str | None,
    db: Session,
) -> User:
    return get_authenticated_user_from_token(authorization, db)


def get_optional_current_app_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    if not authorization:
        return None

    return get_authenticated_user_from_token(authorization, db, sync_snapshots=False)


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


def require_recent_app_user(
    current_user: User = Depends(get_current_app_user),
    _identity: VerifiedFirebaseIdentity = Depends(require_recent_authentication),
) -> User:
    return current_user


def require_recent_active_user(
    current_user: User = Depends(require_active_user),
    _identity: VerifiedFirebaseIdentity = Depends(require_recent_authentication),
) -> User:
    return current_user


def require_verified_user(
    current_user: User = Depends(require_active_user),
    identity: VerifiedFirebaseIdentity = Depends(get_verified_firebase_identity),
    db: Session = Depends(get_db),
) -> User:
    if sync_firebase_identity_snapshots(current_user, identity, db):
        try:
            current_user = commit_user_sync(db, current_user)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=build_user_conflict_detail(exc),
            ) from exc

    if not identity.provider_account_active or not identity.email or not identity.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verified email required.",
        )
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
    current_user: User = Depends(require_verified_user),
) -> User:
    require_active_admin_user(current_user)
    return current_user


def require_recent_active_admin(
    current_user: User = Depends(require_active_admin),
    _identity: VerifiedFirebaseIdentity = Depends(require_recent_authentication),
) -> User:
    return current_user
