import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, Game, User
from backend.schemas import BookingCreate, BookingRead, BookingUpdate

router = APIRouter(prefix="/bookings", tags=["bookings"])

VALID_BOOKING_STATUSES = {
    "pending_payment",
    "confirmed",
    "partially_cancelled",
    "cancelled",
    "expired",
    "failed",
}
VALID_PAYMENT_STATUSES = {
    "unpaid",
    "requires_action",
    "processing",
    "paid",
    "failed",
    "partially_refunded",
    "refunded",
    "disputed",
}
VALID_CURRENCY = "USD"
CANCELLED_BOOKING_STATUSES = {"cancelled", "partially_cancelled"}
BOOKED_BOOKING_STATUSES = {"confirmed", "partially_cancelled", "cancelled"}


def build_booking_conflict_detail(exc: IntegrityError) -> str:
    # The bookings table does not currently expose user-facing unique
    # constraints, so fall back to the database error text for now if an
    # integrity issue occurs.
    return str(exc.orig)


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


def validate_booking_business_rules(booking_data: dict[str, object]) -> None:
    if booking_data["booking_status"] not in VALID_BOOKING_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "booking_status must be 'pending_payment', 'confirmed', "
                "'partially_cancelled', 'cancelled', 'expired', or 'failed'."
            ),
        )

    if booking_data["payment_status"] not in VALID_PAYMENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "payment_status must be 'unpaid', 'requires_action', "
                "'processing', 'paid', 'failed', 'partially_refunded', "
                "'refunded', or 'disputed'."
            ),
        )

    if booking_data["currency"] != VALID_CURRENCY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="currency must be 'USD'.",
        )

    if booking_data["participant_count"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="participant_count must be greater than 0.",
        )

    for field_name in (
        "subtotal_cents",
        "platform_fee_cents",
        "discount_cents",
        "total_cents",
        "price_per_player_snapshot_cents",
        "platform_fee_snapshot_cents",
    ):
        if booking_data[field_name] < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} must be greater than or equal to 0.",
            )

    expected_total = (
        booking_data["subtotal_cents"]
        + booking_data["platform_fee_cents"]
        - booking_data["discount_cents"]
    )
    if booking_data["total_cents"] != expected_total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "total_cents must equal subtotal_cents + "
                "platform_fee_cents - discount_cents."
            ),
        )

    if (
        booking_data["booking_status"] == "confirmed"
        and booking_data["payment_status"] != "paid"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmed bookings require payment_status 'paid'.",
        )

    if (
        booking_data["booking_status"] == "failed"
        and booking_data["payment_status"] != "failed"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed bookings require payment_status 'failed'.",
        )

    if (
        booking_data["payment_status"] in {"refunded", "partially_refunded"}
        and booking_data["booking_status"] not in CANCELLED_BOOKING_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Refunded or partially_refunded bookings must have "
                "booking_status 'cancelled' or 'partially_cancelled'."
            ),
        )

    if (
        booking_data["booking_status"] in CANCELLED_BOOKING_STATUSES
        and booking_data["cancelled_by_user_id"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cancelled or partially_cancelled bookings require "
                "cancelled_by_user_id."
            ),
        )


def normalize_booking_lifecycle_fields(
    booking_data: dict[str, object],
    existing_booking: Booking | None = None,
) -> dict[str, object]:
    normalized_data = dict(booking_data)
    now = datetime.now(timezone.utc)

    # Preserve the original booked_at timestamp for any booking state that
    # represents a real reservation, including later cancellations.
    if normalized_data["booking_status"] in BOOKED_BOOKING_STATUSES:
        normalized_data["booked_at"] = (
            normalized_data.get("booked_at")
            or (existing_booking.booked_at if existing_booking is not None else None)
            or now
        )
    else:
        normalized_data["booked_at"] = None

    if normalized_data["booking_status"] in CANCELLED_BOOKING_STATUSES:
        normalized_data["cancelled_at"] = (
            normalized_data.get("cancelled_at")
            or (
                existing_booking.cancelled_at
                if existing_booking is not None
                else None
            )
            or now
        )
    else:
        normalized_data["cancelled_at"] = None
        normalized_data["cancelled_by_user_id"] = None
        normalized_data["cancel_reason"] = None

    return normalized_data


# This route creates the buyer's booking/order row after validating the linked
# game and user references plus the booking's money and lifecycle rules.
@router.post("", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)) -> Booking:
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


# This route fetches a single booking record by its internal UUID.
@router.get("/{booking_id}", response_model=BookingRead, status_code=status.HTTP_200_OK)
def get_booking(booking_id: uuid.UUID, db: Session = Depends(get_db)) -> Booking:
    db_booking = db.get(Booking, booking_id)

    if db_booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )

    return db_booking


# This route returns booking records currently stored in the app database.
@router.get("", response_model=list[BookingRead], status_code=status.HTTP_200_OK)
def list_bookings(
    buyer_user_id: uuid.UUID | None = None,
    game_id: uuid.UUID | None = None,
    booking_status: str | None = None,
    payment_status: str | None = None,
    db: Session = Depends(get_db),
) -> list[Booking]:
    statement = select(Booking)

    if buyer_user_id is not None:
        statement = statement.where(Booking.buyer_user_id == buyer_user_id)

    if game_id is not None:
        statement = statement.where(Booking.game_id == game_id)

    if booking_status is not None:
        if booking_status not in VALID_BOOKING_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "booking_status must be 'pending_payment', 'confirmed', "
                    "'partially_cancelled', 'cancelled', 'expired', or 'failed'."
                ),
            )
        statement = statement.where(Booking.booking_status == booking_status)

    if payment_status is not None:
        if payment_status not in VALID_PAYMENT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "payment_status must be 'unpaid', 'requires_action', "
                    "'processing', 'paid', 'failed', 'partially_refunded', "
                    "'refunded', or 'disputed'."
                ),
            )
        statement = statement.where(Booking.payment_status == payment_status)

    # Show the newest bookings first so buyer and ops views surface the most
    # recent reservation activity without extra frontend sorting logic.
    bookings = db.scalars(statement.order_by(Booking.created_at.desc())).all()
    return list(bookings)


# This route applies partial updates to an existing booking record while
# keeping its money math and lifecycle state internally consistent.
@router.patch("/{booking_id}", response_model=BookingRead, status_code=status.HTTP_200_OK)
def update_booking(
    booking_id: uuid.UUID, booking_update: BookingUpdate, db: Session = Depends(get_db)
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

    # Lifecycle fields are managed from the fully merged booking state so
    # partial PATCH payloads cannot keep stale timestamps or cancel metadata.
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
