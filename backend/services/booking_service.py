"""Booking reads and protected create/update workflows."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Booking, Game, User
from backend.schemas.booking_schema import BookingCreate, BookingUpdate
from backend.services.admin_permission_service import (
    PERMISSION_MONEY_READ,
    require_user_admin_permission,
    user_has_admin_permission,
)
from backend.services.booking_rules import (
    build_booking_conflict_detail,
    normalize_booking_lifecycle_fields,
    validate_booking_business_rules,
    validate_booking_payment_status,
    validate_booking_status,
)


def get_active_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


def get_active_user_or_404(db: Session, user_id: uuid.UUID, detail: str) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return db_user


def create_booking_workflow(db: Session, booking: BookingCreate) -> Booking:
    get_active_game_or_404(db, booking.game_id)
    get_active_user_or_404(db, booking.buyer_user_id, "Buyer user not found.")

    if booking.cancelled_by_user_id is not None:
        get_active_user_or_404(
            db, booking.cancelled_by_user_id, "Cancelled-by user not found."
        )

    normalized_booking_data = normalize_booking_lifecycle_fields(booking.model_dump())
    validate_booking_business_rules(normalized_booking_data)

    new_booking = Booking(
        id=uuid.uuid4(),
        **normalized_booking_data,
    )

    try:
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_booking_conflict_detail(exc),
        ) from exc

    return new_booking


def get_booking_for_user_or_404(
    db: Session,
    booking_id: uuid.UUID,
    current_user: User,
) -> Booking:
    db_booking = db.get(Booking, booking_id)

    if db_booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )

    if db_booking.buyer_user_id != current_user.id:
        require_user_admin_permission(current_user, PERMISSION_MONEY_READ)

    return db_booking


def list_current_user_bookings(db: Session, current_user: User) -> list[Booking]:
    return list(
        db.scalars(
            select(Booking)
            .where(Booking.buyer_user_id == current_user.id)
            .order_by(Booking.created_at.desc())
        ).all()
    )


def list_bookings(
    db: Session,
    current_user: User,
    *,
    buyer_user_id: uuid.UUID | None = None,
    game_id: uuid.UUID | None = None,
    booking_status: str | None = None,
    payment_status: str | None = None,
) -> list[Booking]:
    statement = select(Booking)
    can_read_all_bookings = user_has_admin_permission(current_user, PERMISSION_MONEY_READ)

    if buyer_user_id is not None and buyer_user_id != current_user.id:
        require_user_admin_permission(current_user, PERMISSION_MONEY_READ)
        can_read_all_bookings = True

    if not can_read_all_bookings:
        buyer_user_id = current_user.id

    if buyer_user_id is not None:
        statement = statement.where(Booking.buyer_user_id == buyer_user_id)

    if game_id is not None:
        statement = statement.where(Booking.game_id == game_id)

    if booking_status is not None:
        validate_booking_status(booking_status)
        statement = statement.where(Booking.booking_status == booking_status)

    if payment_status is not None:
        validate_booking_payment_status(payment_status)
        statement = statement.where(Booking.payment_status == payment_status)

    bookings = db.scalars(statement.order_by(Booking.created_at.desc())).all()
    return list(bookings)


def update_booking_workflow(
    db: Session,
    booking_id: uuid.UUID,
    booking_update: BookingUpdate,
) -> Booking:
    db_booking = db.get(Booking, booking_id)

    if db_booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )

    if booking_update.game_id is not None:
        get_active_game_or_404(db, booking_update.game_id)

    if booking_update.buyer_user_id is not None:
        get_active_user_or_404(db, booking_update.buyer_user_id, "Buyer user not found.")

    if booking_update.cancelled_by_user_id is not None:
        get_active_user_or_404(
            db, booking_update.cancelled_by_user_id, "Cancelled-by user not found."
        )

    update_data = booking_update.model_dump(exclude_unset=True)
    effective_booking_data = {
        "game_id": update_data.get("game_id", db_booking.game_id),
        "buyer_user_id": update_data.get("buyer_user_id", db_booking.buyer_user_id),
        "booking_status": update_data.get("booking_status", db_booking.booking_status),
        "payment_status": update_data.get("payment_status", db_booking.payment_status),
        "participant_count": update_data.get(
            "participant_count", db_booking.participant_count
        ),
        "subtotal_cents": update_data.get("subtotal_cents", db_booking.subtotal_cents),
        "platform_fee_cents": update_data.get(
            "platform_fee_cents", db_booking.platform_fee_cents
        ),
        "discount_cents": update_data.get("discount_cents", db_booking.discount_cents),
        "total_cents": update_data.get("total_cents", db_booking.total_cents),
        "currency": update_data.get("currency", db_booking.currency),
        "price_per_player_snapshot_cents": update_data.get(
            "price_per_player_snapshot_cents",
            db_booking.price_per_player_snapshot_cents,
        ),
        "platform_fee_snapshot_cents": update_data.get(
            "platform_fee_snapshot_cents",
            db_booking.platform_fee_snapshot_cents,
        ),
        "booked_at": update_data.get("booked_at", db_booking.booked_at),
        "cancelled_at": update_data.get("cancelled_at", db_booking.cancelled_at),
        "cancelled_by_user_id": update_data.get(
            "cancelled_by_user_id", db_booking.cancelled_by_user_id
        ),
        "cancel_reason": update_data.get("cancel_reason", db_booking.cancel_reason),
        "expires_at": update_data.get("expires_at", db_booking.expires_at),
    }
    effective_booking_data = normalize_booking_lifecycle_fields(
        effective_booking_data, db_booking
    )
    validate_booking_business_rules(effective_booking_data)

    for lifecycle_field in (
        "booked_at",
        "cancelled_at",
        "cancelled_by_user_id",
        "cancel_reason",
    ):
        update_data[lifecycle_field] = effective_booking_data[lifecycle_field]

    for field_name, field_value in update_data.items():
        setattr(db_booking, field_name, field_value)

    db_booking.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_booking_conflict_detail(exc),
        ) from exc

    return db_booking
