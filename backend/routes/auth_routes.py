import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.firebase_admin_client import (
    FirebaseAdminConfigError,
    delete_firebase_user,
    firebase_email_exists,
    verify_firebase_token,
)
from backend.models import (
    Game,
    GameParticipant,
    User,
    UserPaymentMethod,
    UserSettings,
    UserStats,
    WaitlistEntry,
)
from backend.routes.user_routes import build_conflict_detail
from backend.schemas import (
    AuthDeleteAccountRequest,
    AuthEmailAvailabilityRead,
    AuthSyncUserRequest,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])


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


def sync_email_verification_from_firebase(
    user: User,
    email_verified: bool,
    db: Session,
) -> bool:
    if not email_verified or user.email_verified_at is not None:
        return False

    user.email_verified_at = datetime.now(timezone.utc)
    user.updated_at = user.email_verified_at
    db.add(user)
    return True


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
                detail=build_conflict_detail(exc),
            ) from exc

    return user


def get_current_app_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    return get_authenticated_user_from_token(authorization, db)


def get_auth_user_id_from_token(authorization: str | None) -> str:
    return get_decoded_firebase_token(authorization)["uid"]


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


def cancel_future_user_activity(user: User, db: Session, now: datetime) -> None:
    future_participants = db.scalars(
        select(GameParticipant)
        .join(Game, GameParticipant.game_id == Game.id)
        .where(
            GameParticipant.user_id == user.id,
            Game.starts_at > now,
            GameParticipant.participant_status.in_(
                ["pending_payment", "confirmed", "waitlisted"]
            ),
        )
    ).all()

    for participant in future_participants:
        participant.participant_status = "cancelled"
        participant.cancellation_type = "on_time"
        participant.cancelled_at = participant.cancelled_at or now
        participant.updated_at = now
        db.add(participant)

    participant_snapshots = db.scalars(
        select(GameParticipant).where(GameParticipant.user_id == user.id)
    ).all()

    for participant in participant_snapshots:
        participant.display_name_snapshot = "Deleted User"
        participant.updated_at = now
        db.add(participant)

    waitlist_entries = db.scalars(
        select(WaitlistEntry).where(
            WaitlistEntry.user_id == user.id,
            WaitlistEntry.waitlist_status.in_(["active", "promoted", "accepted"]),
        )
    ).all()

    for waitlist_entry in waitlist_entries:
        waitlist_entry.waitlist_status = "cancelled"
        waitlist_entry.cancelled_at = waitlist_entry.cancelled_at or now
        waitlist_entry.updated_at = now
        db.add(waitlist_entry)

    hosted_games = db.scalars(
        select(Game).where(
            Game.host_user_id == user.id,
            Game.starts_at > now,
            Game.game_status.in_(["scheduled", "full"]),
        )
    ).all()

    for game in hosted_games:
        game.game_status = "cancelled"
        game.cancelled_at = game.cancelled_at or now
        game.cancelled_by_user_id = user.id
        game.cancel_reason = "Host account deleted."
        game.updated_at = now
        db.add(game)

    payment_methods = db.scalars(
        select(UserPaymentMethod).where(UserPaymentMethod.user_id == user.id)
    ).all()

    for payment_method in payment_methods:
        db.delete(payment_method)

    settings = db.get(UserSettings, user.id)

    if settings is not None:
        settings.push_notifications_enabled = False
        settings.email_notifications_enabled = False
        settings.sms_notifications_enabled = False
        settings.marketing_opt_in = False
        settings.location_permission_status = "unknown"
        settings.selected_city = None
        settings.selected_state = None
        settings.updated_at = now
        db.add(settings)


def anonymize_user(user: User, now: datetime) -> None:
    user.auth_user_id = None
    user.email = None
    user.phone = None
    user.first_name = "Deleted"
    user.last_name = "User"
    user.date_of_birth = None
    user.profile_photo_url = None
    user.home_city = None
    user.home_state = None
    user.account_status = "deleted"
    user.hosting_status = "not_eligible"
    user.hosting_suspended_until = None
    user.stripe_customer_id = None
    user.deleted_at = now
    user.updated_at = now


def has_complete_profile(user: User) -> bool:
    return bool(user.first_name and user.last_name and user.date_of_birth)


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


@router.get(
    "/email-availability",
    response_model=AuthEmailAvailabilityRead,
    status_code=status.HTTP_200_OK,
)
def check_email_availability(
    email: str = Query(..., min_length=3), db: Session = Depends(get_db)
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


@router.get("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
def get_current_app_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    return get_authenticated_user_from_token(authorization, db)


@router.post(
    "/sync-user",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
def sync_user(payload: AuthSyncUserRequest, db: Session = Depends(get_db)) -> User:
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
                    detail=build_conflict_detail(exc),
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
                        detail=build_conflict_detail(exc),
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
            detail=build_conflict_detail(exc),
        ) from exc

    return new_user


@router.delete("/unfinished-account", status_code=status.HTTP_204_NO_CONTENT)
def cleanup_unfinished_account(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> None:
    auth_user_id = get_auth_user_id_from_token(authorization)
    user = get_active_user_by_auth_id(auth_user_id, db)

    if user is not None:
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
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_conflict_detail(exc),
        ) from exc


@router.delete("/account", response_model=UserRead, status_code=status.HTTP_200_OK)
def delete_account(
    payload: AuthDeleteAccountRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if payload.confirmation.strip().upper() != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Type "delete" to confirm account deletion.',
        )

    user = get_authenticated_user_from_token(authorization, db)
    now = datetime.now(timezone.utc)
    auth_user_id = user.auth_user_id

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
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_conflict_detail(exc),
        ) from exc

    try:
        delete_firebase_user(auth_user_id)
    except FirebaseAdminConfigError as exc:
        user.account_status = "active"
        user.updated_at = datetime.now(timezone.utc)
        db.add(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        user.account_status = "active"
        user.updated_at = datetime.now(timezone.utc)
        db.add(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Firebase could not delete this account. Please try again.",
        ) from exc

    now = datetime.now(timezone.utc)
    cancel_future_user_activity(user, db, now)
    anonymize_user(user, now)
    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_conflict_detail(exc),
        ) from exc

    return user
