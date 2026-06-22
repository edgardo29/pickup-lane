"""Authentication dependencies and permission checks shared across route modules."""

import uuid
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.firebase_admin_client import (
    FirebaseAdminConfigError,
    delete_firebase_user,
    firebase_email_exists,
    verify_firebase_token,
)
from backend.models import (
    User,
    UserSettings,
    UserStats,
)
from backend.schemas import (
    AuthDeleteAccountRequest,
    AuthEmailAvailabilityRead,
    AuthSyncUserRequest,
)
from backend.services.admin_permission_service import user_has_admin_permission
from backend.services.hosting_access_service import (
    HOSTING_STATUS_ELIGIBLE,
    HOSTING_STATUS_NOT_ELIGIBLE,
    apply_verified_hosting_eligibility,
)
from backend.services.account_deletion_service import (
    anonymize_user,
    cancel_future_user_activity,
    detach_account_saved_payment_methods,
    lock_user_and_active_admins_for_account_removal,
    record_account_delete_partial_failure,
    require_account_removal_preserves_active_admin,
)
from backend.services.user_service import build_user_conflict_detail


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


def add_missing_user_context_rows(user: User, db: Session) -> bool:
    did_add_row = False

    if db.get(UserSettings, user.id) is None:
        db.add(
            UserSettings(
                user_id=user.id,
                push_notifications_enabled=False,
                email_notifications_enabled=False,
                sms_notifications_enabled=False,
                marketing_opt_in=False,
                location_permission_status="unknown",
            )
        )
        did_add_row = True

    if db.get(UserStats, user.id) is None:
        db.add(
            UserStats(
                user_id=user.id,
                games_played_count=0,
                games_hosted_completed_count=0,
                no_show_count=0,
                late_cancel_count=0,
                host_cancel_count=0,
                last_calculated_at=datetime.now(timezone.utc),
            )
        )
        did_add_row = True

    return did_add_row


def commit_user_sync(db: Session, user: User) -> User:
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise

    return user


def check_email_availability_workflow(
    email: str,
    db: Session,
) -> AuthEmailAvailabilityRead:
    normalized_email = email.strip().lower()

    if not normalized_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required.",
        )

    existing_user = db.scalar(
        select(User).where(
            func.lower(User.email) == normalized_email,
            User.deleted_at.is_(None),
            User.account_status != "pending_deletion",
        )
    )

    if existing_user is not None:
        return AuthEmailAvailabilityRead(email=normalized_email, available=False)

    try:
        exists_in_firebase = firebase_email_exists(normalized_email)
    except FirebaseAdminConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not check email availability. Please try again.",
        ) from exc

    return AuthEmailAvailabilityRead(
        email=normalized_email,
        available=not exists_in_firebase,
    )


def has_complete_profile(user: User) -> bool:
    return bool(user.first_name and user.last_name and user.date_of_birth)


def build_sync_user_payload_from_token(authorization: str | None) -> AuthSyncUserRequest:
    decoded_token = get_decoded_firebase_token(authorization)
    email = decoded_token.get("email")

    if not isinstance(email, str) or not email.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication token is missing an email address.",
        )

    return AuthSyncUserRequest(
        auth_user_id=decoded_token["uid"],
        email=email.strip().lower(),
        email_verified=bool(decoded_token.get("email_verified")),
    )


def hard_delete_incomplete_user(user: User, db: Session) -> None:
    if has_complete_profile(user):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed accounts must use account deletion.",
        )

    db.delete(user)


def get_user_after_idempotent_conflict(
    payload: AuthSyncUserRequest, db: Session
) -> User | None:
    existing_user = get_active_user_by_auth_id(payload.auth_user_id, db)

    if existing_user is None or existing_user.email != payload.email:
        return None

    return existing_user


def sync_user_workflow(authorization: str | None, db: Session) -> User:
    payload = build_sync_user_payload_from_token(authorization)
    existing_user = get_active_user_by_auth_id(payload.auth_user_id, db)

    if existing_user is not None:
        should_commit = False

        if existing_user.email != payload.email:
            email_owner = db.scalar(
                select(User).where(
                    User.email == payload.email,
                    User.id != existing_user.id,
                )
            )

            if email_owner is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A user with this email already exists.",
                )

            existing_user.email = payload.email
            existing_user.updated_at = datetime.now(timezone.utc)
            db.add(existing_user)
            should_commit = True

        should_commit = (
            sync_email_verification_from_firebase(
                existing_user,
                payload.email_verified,
                db,
            )
            or should_commit
        )
        should_commit = add_missing_user_context_rows(existing_user, db) or should_commit

        if should_commit:
            try:
                return commit_user_sync(db, existing_user)
            except IntegrityError as exc:
                fresh_user = get_user_after_idempotent_conflict(payload, db)
                if fresh_user is not None:
                    return fresh_user

                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=build_user_conflict_detail(exc),
                ) from exc

        return existing_user

    email_owner = db.scalar(select(User).where(User.email == payload.email))

    if email_owner is not None:
        if (
            email_owner.auth_user_id == payload.auth_user_id
            and email_owner.deleted_at is None
            and email_owner.account_status != "pending_deletion"
        ):
            should_commit = sync_email_verification_from_firebase(
                email_owner,
                payload.email_verified,
                db,
            )
            should_commit = add_missing_user_context_rows(email_owner, db) or should_commit

            if should_commit:
                try:
                    return commit_user_sync(db, email_owner)
                except IntegrityError as exc:
                    fresh_user = get_user_after_idempotent_conflict(payload, db)
                    if fresh_user is not None:
                        return fresh_user

                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=build_user_conflict_detail(exc),
                    ) from exc

            return email_owner

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    new_user = User(
        id=uuid.uuid4(),
        auth_user_id=payload.auth_user_id,
        email=payload.email,
        email_verified_at=(
            datetime.now(timezone.utc) if payload.email_verified else None
        ),
        hosting_status=(
            HOSTING_STATUS_ELIGIBLE
            if payload.email_verified
            else HOSTING_STATUS_NOT_ELIGIBLE
        ),
    )

    try:
        db.add(new_user)
        add_missing_user_context_rows(new_user, db)
        new_user = commit_user_sync(db, new_user)
    except IntegrityError as exc:
        db.rollback()
        # Firebase sign-up and onAuthStateChanged can sync the same account in
        # quick succession during local dev. If another request created the row
        # first, return that row instead of treating the idempotent sync as a
        # hard conflict.
        existing_user = get_user_after_idempotent_conflict(payload, db)

        if existing_user is not None:
            if add_missing_user_context_rows(existing_user, db):
                try:
                    return commit_user_sync(db, existing_user)
                except IntegrityError:
                    db.rollback()

            fresh_user = get_user_after_idempotent_conflict(payload, db)
            if fresh_user is not None:
                return fresh_user

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_conflict_detail(exc),
        ) from exc

    return new_user


def cleanup_unfinished_account_workflow(
    authorization: str | None,
    db: Session,
) -> None:
    auth_user_id = get_auth_user_id_from_token(authorization)
    user = get_active_user_by_auth_id(auth_user_id, db)
    user_id = user.id if user is not None else None

    if user is not None:
        user, active_admin_count = lock_user_and_active_admins_for_account_removal(
            db,
            user_id=user.id,
        )
        require_account_removal_preserves_active_admin(
            user,
            active_admin_count=active_admin_count,
        )
        hard_delete_incomplete_user(user, db)

    try:
        delete_firebase_user(auth_user_id)
    except FirebaseAdminConfigError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Firebase could not clean up this sign-up. Please try again.",
        ) from exc

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        if user_id is not None:
            record_account_delete_partial_failure(
                db,
                user_id=user_id,
                created_by_user_id=user_id,
                metadata={
                    "auth_identity_deleted": True,
                    "app_cleanup_completed": False,
                    "failure_type": "unfinished_account_cleanup_commit_error",
                },
                summary=(
                    "Firebase cleanup succeeded, but the unfinished app account "
                    "could not be removed."
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Firebase cleanup succeeded, but app account cleanup requires "
                "support follow-up."
            ),
        ) from exc


def restore_self_delete_staged_account_after_firebase_failure(
    db: Session,
    *,
    user: User,
    previous_account_status: str,
    response_status_code: int,
    response_detail: str,
) -> None:
    user.account_status = previous_account_status
    user.updated_at = datetime.now(timezone.utc)
    db.add(user)
    try:
        db.commit()
    except SQLAlchemyError as restore_exc:
        db.rollback()
        record_account_delete_partial_failure(
            db,
            user_id=user.id,
            created_by_user_id=user.id,
            clear_auth_link=False,
            metadata={
                "auth_identity_deleted": False,
                "app_cleanup_completed": False,
                "restore_failed": True,
                "previous_account_status": previous_account_status,
            },
            summary=(
                "Firebase deletion failed, and the staged app account status "
                "could not be restored."
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Firebase deletion failed, and app account restoration requires "
                "support follow-up."
            ),
        ) from restore_exc

    raise HTTPException(
        status_code=response_status_code,
        detail=response_detail,
    )


def delete_account_workflow(
    payload: AuthDeleteAccountRequest,
    authorization: str | None,
    db: Session,
) -> User:
    if payload.confirmation.strip().upper() != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Type "delete" to confirm account deletion.',
        )

    authenticated_user = get_authenticated_user_from_token(authorization, db)
    user, active_admin_count = lock_user_and_active_admins_for_account_removal(
        db,
        user_id=authenticated_user.id,
    )
    require_account_removal_preserves_active_admin(
        user,
        active_admin_count=active_admin_count,
    )
    now = datetime.now(timezone.utc)
    auth_user_id = user.auth_user_id
    previous_account_status = user.account_status

    if not auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This account cannot be deleted because it is already unlinked.",
        )

    user.account_status = "pending_deletion"
    user.updated_at = now
    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_conflict_detail(exc),
        ) from exc

    try:
        delete_firebase_user(auth_user_id)
    except FirebaseAdminConfigError as exc:
        restore_self_delete_staged_account_after_firebase_failure(
            db,
            user=user,
            previous_account_status=previous_account_status,
            response_status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            response_detail=str(exc),
        )
    except Exception as exc:
        restore_self_delete_staged_account_after_firebase_failure(
            db,
            user=user,
            previous_account_status=previous_account_status,
            response_status_code=status.HTTP_502_BAD_GATEWAY,
            response_detail="Firebase could not delete this account. Please try again.",
        )

    checkpoint_at = datetime.now(timezone.utc)
    user.auth_user_id = None
    user.updated_at = checkpoint_at
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except SQLAlchemyError as exc:
        db.rollback()
        record_account_delete_partial_failure(
            db,
            user_id=user.id,
            created_by_user_id=user.id,
            metadata={
                "auth_identity_deleted": True,
                "app_cleanup_completed": False,
                "failure_type": "auth_unlink_checkpoint_commit_error",
            },
            summary=(
                "Firebase deletion succeeded, but the app auth unlink did not "
                "commit."
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Firebase deletion succeeded, but app account cleanup requires "
                "support follow-up."
            ),
        ) from exc

    payment_method_result = detach_account_saved_payment_methods(
        db,
        user_id=user.id,
    )
    if payment_method_result.has_blocking_failures:
        record_account_delete_partial_failure(
            db,
            user_id=user.id,
            created_by_user_id=user.id,
            metadata=payment_method_result.support_metadata(
                auth_identity_deleted=True
            ),
            detached_payment_method_ids=(
                payment_method_result.detached_saved_payment_method_ids
            ),
            summary=(
                "Firebase deletion succeeded, but app account cleanup requires "
                "support follow-up."
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Firebase deletion succeeded, but app account cleanup requires "
                "support follow-up."
            ),
        )

    try:
        db.commit()
        db.refresh(user)
    except SQLAlchemyError as exc:
        db.rollback()
        record_account_delete_partial_failure(
            db,
            user_id=user.id,
            created_by_user_id=user.id,
            metadata={
                **payment_method_result.support_metadata(
                    auth_identity_deleted=True
                ),
                "failure_type": "saved_payment_method_checkpoint_commit_error",
            },
            detached_payment_method_ids=(
                payment_method_result.detached_saved_payment_method_ids
            ),
            summary=(
                "Firebase deletion succeeded, but saved-card cleanup state did "
                "not commit."
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Firebase deletion succeeded, but app account cleanup requires "
                "support follow-up."
            ),
        ) from exc

    now = datetime.now(timezone.utc)
    try:
        cancel_future_user_activity(
            user,
            db,
            now,
            changed_by_user_id=user.id,
        )
        anonymize_user(user, now)
        db.add(user)
    except Exception as exc:
        db.rollback()
        record_account_delete_partial_failure(
            db,
            user_id=user.id,
            created_by_user_id=user.id,
            metadata={
                "auth_identity_deleted": True,
                "app_cleanup_completed": False,
                "failure_type": "app_cleanup_execution_error",
            },
            summary=(
                "Firebase deletion succeeded, but app account cleanup failed "
                "before the final commit."
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Firebase deletion succeeded, but app account cleanup requires "
                "support follow-up."
            ),
        ) from exc

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        record_account_delete_partial_failure(
            db,
            user_id=user.id,
            created_by_user_id=user.id,
            metadata={
                "auth_identity_deleted": True,
                "app_cleanup_completed": False,
                "failure_type": "app_cleanup_commit_error",
            },
            summary=(
                "Firebase deletion succeeded, but final app account cleanup did "
                "not commit."
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Firebase deletion succeeded, but app account cleanup requires "
                "support follow-up."
            ),
        ) from exc

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


def require_user_admin_permission(user: User, permission: str) -> None:
    require_active_account(user)

    if not user_has_admin_permission(user, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )


def require_user_any_admin_permission(user: User, permissions: tuple[str, ...]) -> None:
    require_active_account(user)

    if not any(user_has_admin_permission(user, permission) for permission in permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )


def require_admin_permission(permission: str):
    def dependency(current_user: User = Depends(get_current_app_user)) -> User:
        require_user_admin_permission(current_user, permission)
        return current_user

    return dependency


def require_any_admin_permission(*permissions: str):
    def dependency(current_user: User = Depends(get_current_app_user)) -> User:
        require_user_any_admin_permission(current_user, permissions)
        return current_user

    return dependency
