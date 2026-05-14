import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    AdminAction,
    Booking,
    ChatMessage,
    Game,
    GameParticipant,
    Payment,
    User,
    Venue,
)
from backend.schemas import AdminActionCreate, AdminActionRead, AdminActionUpdate

router = APIRouter(prefix="/admin-actions", tags=["admin_actions"])

VALID_ACTION_TYPES = {
    "cancel_game",
    "refund_booking",
    "mark_no_show",
    "reverse_no_show",
    "suspend_user",
    "unsuspend_user",
    "restrict_hosting",
    "restore_hosting",
    "approve_venue",
    "reject_venue",
    "remove_chat_message",
    "hide_chat_message",
    "update_game",
    "update_booking",
    "update_participant",
}
ADMIN_ALLOWED_ROLES = {"admin", "moderator"}
TARGET_FIELDS = {
    "target_user_id",
    "target_game_id",
    "target_booking_id",
    "target_participant_id",
    "target_payment_id",
    "target_venue_id",
    "target_message_id",
}
IMMUTABLE_ADMIN_ACTION_UPDATE_FIELDS = {
    "admin_user_id",
    "action_type",
    "target_user_id",
    "target_game_id",
    "target_booking_id",
    "target_participant_id",
    "target_payment_id",
    "target_venue_id",
    "target_message_id",
}


def build_admin_action_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "ck_admin_actions_action_type" in error_text:
        return "action_type is not supported."

    if "ck_admin_actions_target_required" in error_text:
        return "At least one target field must be provided."

    return error_text


def get_user_or_404(db: Session, user_id: uuid.UUID, detail: str) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return db_user


def get_existing_record_or_404(
    db: Session,
    model: type,
    record_id: uuid.UUID,
    detail: str,
) -> object:
    db_record = db.get(model, record_id)

    if db_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    deleted_at = getattr(db_record, "deleted_at", None)
    if deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return db_record


def validate_admin_action_business_rules(action_data: dict[str, Any]) -> None:
    for field_name in ("admin_user_id", "action_type"):
        if action_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if action_data["action_type"] not in VALID_ACTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action_type is not supported.",
        )

    has_target = any(action_data[field_name] is not None for field_name in TARGET_FIELDS)
    if not has_target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one target field must be provided.",
        )


def validate_admin_action_references(
    db: Session,
    action_data: dict[str, Any],
) -> None:
    db_admin_user = get_user_or_404(
        db,
        action_data["admin_user_id"],
        "Admin user not found.",
    )

    if db_admin_user.role not in ADMIN_ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="admin_user_id must belong to an admin or moderator user.",
        )

    if action_data["target_user_id"] is not None:
        get_user_or_404(db, action_data["target_user_id"], "Target user not found.")

    if action_data["target_game_id"] is not None:
        get_existing_record_or_404(
            db,
            Game,
            action_data["target_game_id"],
            "Target game not found.",
        )

    if action_data["target_booking_id"] is not None:
        get_existing_record_or_404(
            db,
            Booking,
            action_data["target_booking_id"],
            "Target booking not found.",
        )

    if action_data["target_participant_id"] is not None:
        get_existing_record_or_404(
            db,
            GameParticipant,
            action_data["target_participant_id"],
            "Target participant not found.",
        )

    if action_data["target_payment_id"] is not None:
        get_existing_record_or_404(
            db,
            Payment,
            action_data["target_payment_id"],
            "Target payment not found.",
        )

    if action_data["target_venue_id"] is not None:
        get_existing_record_or_404(
            db,
            Venue,
            action_data["target_venue_id"],
            "Target venue not found.",
        )

    if action_data["target_message_id"] is not None:
        get_existing_record_or_404(
            db,
            ChatMessage,
            action_data["target_message_id"],
            "Target message not found.",
        )


def normalize_admin_action_data(action_data: dict[str, Any]) -> dict[str, Any]:
    normalized_data = dict(action_data)
    normalized_data["metadata_"] = normalized_data.pop("metadata")
    return normalized_data


def validate_admin_action_update_fields(update_data: dict[str, Any]) -> None:
    immutable_fields = IMMUTABLE_ADMIN_ACTION_UPDATE_FIELDS & update_data.keys()

    if immutable_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin action audit fields cannot be changed after creation.",
        )


# This route records one admin/support audit action after validating the actor,
# action type, and optional affected target references.
@router.post("", response_model=AdminActionRead, status_code=status.HTTP_201_CREATED)
def create_admin_action(
    admin_action: AdminActionCreate,
    db: Session = Depends(get_db),
) -> AdminAction:
    action_data = admin_action.model_dump()
    validate_admin_action_business_rules(action_data)
    validate_admin_action_references(db, action_data)

    new_admin_action = AdminAction(
        id=uuid.uuid4(),
        **normalize_admin_action_data(action_data),
    )

    try:
        db.add(new_admin_action)
        db.commit()
        db.refresh(new_admin_action)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_admin_action_conflict_detail(exc),
        ) from exc

    return new_admin_action


# This route fetches a single admin action audit row by its internal UUID.
@router.get(
    "/{admin_action_id}",
    response_model=AdminActionRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_action(
    admin_action_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> AdminAction:
    db_admin_action = db.get(AdminAction, admin_action_id)

    if db_admin_action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin action not found.",
        )

    return db_admin_action


# This route returns admin action audit rows currently stored in the app database.
@router.get("", response_model=list[AdminActionRead], status_code=status.HTTP_200_OK)
def list_admin_actions(
    admin_user_id: uuid.UUID | None = None,
    action_type: str | None = None,
    target_user_id: uuid.UUID | None = None,
    target_game_id: uuid.UUID | None = None,
    target_booking_id: uuid.UUID | None = None,
    target_participant_id: uuid.UUID | None = None,
    target_payment_id: uuid.UUID | None = None,
    target_venue_id: uuid.UUID | None = None,
    target_message_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
) -> list[AdminAction]:
    statement = select(AdminAction)

    if admin_user_id is not None:
        statement = statement.where(AdminAction.admin_user_id == admin_user_id)

    if action_type is not None:
        if action_type not in VALID_ACTION_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="action_type is not supported.",
            )
        statement = statement.where(AdminAction.action_type == action_type)

    if target_user_id is not None:
        statement = statement.where(AdminAction.target_user_id == target_user_id)

    if target_game_id is not None:
        statement = statement.where(AdminAction.target_game_id == target_game_id)

    if target_booking_id is not None:
        statement = statement.where(AdminAction.target_booking_id == target_booking_id)

    if target_participant_id is not None:
        statement = statement.where(
            AdminAction.target_participant_id == target_participant_id
        )

    if target_payment_id is not None:
        statement = statement.where(AdminAction.target_payment_id == target_payment_id)

    if target_venue_id is not None:
        statement = statement.where(AdminAction.target_venue_id == target_venue_id)

    if target_message_id is not None:
        statement = statement.where(AdminAction.target_message_id == target_message_id)

    admin_actions = db.scalars(
        statement.order_by(AdminAction.created_at.desc())
    ).all()
    return list(admin_actions)


# This route allows correcting non-lifecycle audit notes while keeping the actor,
# action type, and target references immutable.
@router.patch(
    "/{admin_action_id}",
    response_model=AdminActionRead,
    status_code=status.HTTP_200_OK,
)
def update_admin_action(
    admin_action_id: uuid.UUID,
    admin_action_update: AdminActionUpdate,
    db: Session = Depends(get_db),
) -> AdminAction:
    db_admin_action = db.get(AdminAction, admin_action_id)

    if db_admin_action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin action not found.",
        )

    update_data = admin_action_update.model_dump(exclude_unset=True)
    validate_admin_action_update_fields(update_data)

    if "reason" in update_data:
        db_admin_action.reason = update_data["reason"]

    if "metadata" in update_data:
        db_admin_action.metadata_ = update_data["metadata"]

    try:
        db.add(db_admin_action)
        db.commit()
        db.refresh(db_admin_action)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_admin_action_conflict_detail(exc),
        ) from exc

    return db_admin_action
