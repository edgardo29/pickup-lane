import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import HostProfile, User
from backend.schemas import HostProfileCreate, HostProfileRead, HostProfileUpdate

router = APIRouter(prefix="/host-profiles", tags=["host_profiles"])

VALID_PAYMENT_DUE_TIMINGS = {
    "before_game",
    "at_arrival",
    "after_confirmation",
    "custom",
}


def build_host_profile_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_host_profiles_user_id" in error_text:
        return "This user already has a host profile."

    if "uq_host_profiles_phone_number_e164" in error_text:
        return "This phone number is already attached to a host profile."

    return error_text


def get_active_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return db_user


def validate_host_profile_business_rules(profile_data: dict[str, object]) -> None:
    if profile_data["user_id"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id cannot be null.",
        )

    payment_methods = profile_data["default_payment_methods"]
    if not isinstance(payment_methods, list) or not all(
        isinstance(method, str) for method in payment_methods
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="default_payment_methods must be a list of strings.",
        )

    due_timing = profile_data["default_payment_due_timing"]
    if due_timing is not None and due_timing not in VALID_PAYMENT_DUE_TIMINGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "default_payment_due_timing must be 'before_game', "
                "'at_arrival', 'after_confirmation', or 'custom'."
            ),
        )

    if (
        profile_data["phone_verified_at"] is not None
        and profile_data["phone_number_e164"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="phone_verified_at requires phone_number_e164.",
        )

    if (
        profile_data["host_rules_accepted_at"] is not None
        and profile_data["host_rules_version"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="host_rules_accepted_at requires host_rules_version.",
        )

    if profile_data["host_setup_completed_at"] is not None and (
        profile_data["phone_verified_at"] is None
        or profile_data["host_rules_accepted_at"] is None
        or profile_data["host_age_confirmed_at"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "host_setup_completed_at requires phone verification, "
                "host rules acceptance, and host age confirmation."
            ),
        )


@router.post("", response_model=HostProfileRead, status_code=status.HTTP_201_CREATED)
def create_host_profile(
    host_profile: HostProfileCreate, db: Session = Depends(get_db)
) -> HostProfile:
    profile_data = host_profile.model_dump()
    validate_host_profile_business_rules(profile_data)
    get_active_user_or_404(db, host_profile.user_id)

    new_host_profile = HostProfile(id=uuid.uuid4(), **profile_data)

    try:
        db.add(new_host_profile)
        db.commit()
        db.refresh(new_host_profile)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_host_profile_conflict_detail(exc),
        ) from exc

    return new_host_profile


@router.get(
    "/{host_profile_id}",
    response_model=HostProfileRead,
    status_code=status.HTTP_200_OK,
)
def get_host_profile(
    host_profile_id: uuid.UUID, db: Session = Depends(get_db)
) -> HostProfile:
    db_host_profile = db.get(HostProfile, host_profile_id)

    if db_host_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host profile not found.",
        )

    return db_host_profile


@router.get("", response_model=list[HostProfileRead], status_code=status.HTTP_200_OK)
def list_host_profiles(
    user_id: uuid.UUID | None = None,
    setup_completed: bool | None = None,
    db: Session = Depends(get_db),
) -> list[HostProfile]:
    statement = select(HostProfile)

    if user_id is not None:
        statement = statement.where(HostProfile.user_id == user_id)

    if setup_completed is True:
        statement = statement.where(HostProfile.host_setup_completed_at.is_not(None))
    elif setup_completed is False:
        statement = statement.where(HostProfile.host_setup_completed_at.is_(None))

    host_profiles = db.scalars(
        statement.order_by(HostProfile.created_at.desc())
    ).all()
    return list(host_profiles)


@router.patch(
    "/{host_profile_id}",
    response_model=HostProfileRead,
    status_code=status.HTTP_200_OK,
)
def update_host_profile(
    host_profile_id: uuid.UUID,
    host_profile_update: HostProfileUpdate,
    db: Session = Depends(get_db),
) -> HostProfile:
    db_host_profile = db.get(HostProfile, host_profile_id)

    if db_host_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host profile not found.",
        )

    update_data = host_profile_update.model_dump(exclude_unset=True)
    effective_profile_data = {
        "user_id": update_data.get("user_id", db_host_profile.user_id),
        "phone_number_e164": update_data.get(
            "phone_number_e164", db_host_profile.phone_number_e164
        ),
        "phone_verified_at": update_data.get(
            "phone_verified_at", db_host_profile.phone_verified_at
        ),
        "host_rules_accepted_at": update_data.get(
            "host_rules_accepted_at", db_host_profile.host_rules_accepted_at
        ),
        "host_rules_version": update_data.get(
            "host_rules_version", db_host_profile.host_rules_version
        ),
        "host_setup_completed_at": update_data.get(
            "host_setup_completed_at", db_host_profile.host_setup_completed_at
        ),
        "host_age_confirmed_at": update_data.get(
            "host_age_confirmed_at", db_host_profile.host_age_confirmed_at
        ),
        "default_payment_methods": update_data.get(
            "default_payment_methods", db_host_profile.default_payment_methods
        ),
        "default_payment_instructions": update_data.get(
            "default_payment_instructions",
            db_host_profile.default_payment_instructions,
        ),
        "default_payment_due_timing": update_data.get(
            "default_payment_due_timing",
            db_host_profile.default_payment_due_timing,
        ),
        "default_refund_policy": update_data.get(
            "default_refund_policy", db_host_profile.default_refund_policy
        ),
        "default_game_rules": update_data.get(
            "default_game_rules", db_host_profile.default_game_rules
        ),
        "default_arrival_expectations": update_data.get(
            "default_arrival_expectations",
            db_host_profile.default_arrival_expectations,
        ),
        "default_equipment_notes": update_data.get(
            "default_equipment_notes", db_host_profile.default_equipment_notes
        ),
        "default_behavior_rules": update_data.get(
            "default_behavior_rules", db_host_profile.default_behavior_rules
        ),
        "default_no_show_policy": update_data.get(
            "default_no_show_policy", db_host_profile.default_no_show_policy
        ),
        "default_player_message": update_data.get(
            "default_player_message", db_host_profile.default_player_message
        ),
        "first_free_game_used_at": update_data.get(
            "first_free_game_used_at", db_host_profile.first_free_game_used_at
        ),
    }
    validate_host_profile_business_rules(effective_profile_data)
    get_active_user_or_404(db, effective_profile_data["user_id"])

    for field_name, field_value in update_data.items():
        setattr(db_host_profile, field_name, field_value)

    db_host_profile.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_host_profile)
        db.commit()
        db.refresh(db_host_profile)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_host_profile_conflict_detail(exc),
        ) from exc

    return db_host_profile
