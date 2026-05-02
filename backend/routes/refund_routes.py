import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, GameParticipant, Payment, Refund, User
from backend.schemas import RefundCreate, RefundRead, RefundUpdate

router = APIRouter(prefix="/refunds", tags=["refunds"])

VALID_REFUND_REASONS = {
    "player_cancelled",
    "late_cancel",
    "host_cancelled",
    "game_cancelled",
    "weather",
    "admin_refund",
    "duplicate_payment",
    "dispute_resolution",
}
VALID_REFUND_STATUSES = {
    "pending",
    "approved",
    "processing",
    "succeeded",
    "failed",
    "cancelled",
}
VALID_CURRENCY = "USD"
REFUNDABLE_PAYMENT_STATUSES = {
    "succeeded",
    "refunded",
    "partially_refunded",
    "disputed",
}
REFUND_AMOUNT_HOLD_STATUSES = {
    "pending",
    "approved",
    "processing",
    "succeeded",
}
TERMINAL_REFUND_STATUSES = {
    "succeeded",
    "failed",
    "cancelled",
}


def build_refund_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_refunds_provider_refund_id" in error_text:
        return "A refund with this provider_refund_id already exists."

    return error_text


def get_payment_or_404(db: Session, payment_id: uuid.UUID) -> Payment:
    db_payment = db.get(Payment, payment_id)

    if db_payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    return db_payment


def get_booking_or_404(db: Session, booking_id: uuid.UUID) -> Booking:
    db_booking = db.get(Booking, booking_id)

    if db_booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )

    return db_booking


def get_participant_or_404(
    db: Session, participant_id: uuid.UUID
) -> GameParticipant:
    db_participant = db.get(GameParticipant, participant_id)

    if db_participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found.",
        )

    return db_participant


def get_active_user_or_404(
    db: Session, user_id: uuid.UUID, detail: str
) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return db_user


def validate_refund_business_rules(refund_data: dict[str, object]) -> None:
    for field_name in (
        "payment_id",
        "amount_cents",
        "currency",
        "refund_reason",
        "refund_status",
    ):
        if refund_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if refund_data["refund_reason"] not in VALID_REFUND_REASONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "refund_reason must be 'player_cancelled', 'late_cancel', "
                "'host_cancelled', 'game_cancelled', 'weather', 'admin_refund', "
                "'duplicate_payment', or 'dispute_resolution'."
            ),
        )

    if refund_data["refund_status"] not in VALID_REFUND_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "refund_status must be 'pending', 'approved', 'processing', "
                "'succeeded', 'failed', or 'cancelled'."
            ),
        )

    if refund_data["currency"] != VALID_CURRENCY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="currency must be 'USD'.",
        )

    if refund_data["amount_cents"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount_cents must be greater than 0.",
        )

    if refund_data["booking_id"] is None and refund_data["participant_id"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refunds require booking_id or participant_id.",
        )


def normalize_refund_lifecycle_fields(
    refund_data: dict[str, object],
    existing_refund: Refund | None = None,
) -> dict[str, object]:
    normalized_data = dict(refund_data)
    now = datetime.now(timezone.utc)

    normalized_data["requested_at"] = (
        normalized_data.get("requested_at")
        or (existing_refund.requested_at if existing_refund is not None else None)
        or now
    )

    # Approval/refund timestamps are derived from status so clients cannot keep
    # stale lifecycle timestamps around after refund status changes.
    if normalized_data["refund_status"] in {"approved", "processing", "succeeded"}:
        normalized_data["approved_at"] = (
            normalized_data.get("approved_at")
            or (existing_refund.approved_at if existing_refund is not None else None)
            or now
        )
    elif normalized_data["refund_status"] in {"failed", "cancelled"}:
        normalized_data["approved_at"] = normalized_data.get("approved_at") or (
            existing_refund.approved_at if existing_refund is not None else None
        )
    else:
        normalized_data["approved_at"] = None

    if normalized_data["refund_status"] == "succeeded":
        normalized_data["refunded_at"] = (
            normalized_data.get("refunded_at")
            or (existing_refund.refunded_at if existing_refund is not None else None)
            or now
        )
    else:
        normalized_data["refunded_at"] = None

    return normalized_data


def validate_refund_references(
    db: Session,
    refund_data: dict[str, object],
) -> Payment:
    db_payment = get_payment_or_404(db, refund_data["payment_id"])

    if (
        db_payment.payment_status not in REFUNDABLE_PAYMENT_STATUSES
        or db_payment.paid_at is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refunds require a payment that has succeeded.",
        )

    if db_payment.booking_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refunds currently require a booking payment.",
        )

    if refund_data["booking_id"] is not None:
        db_booking = get_booking_or_404(db, refund_data["booking_id"])

        if db_booking.id != db_payment.booking_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="booking_id must match the payment booking.",
            )

    if refund_data["participant_id"] is not None:
        db_participant = get_participant_or_404(db, refund_data["participant_id"])

        if db_participant.booking_id != db_payment.booking_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="participant_id must belong to the payment booking.",
            )

        if (
            refund_data["booking_id"] is not None
            and db_participant.booking_id != refund_data["booking_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="participant_id must belong to booking_id.",
            )

    if refund_data["requested_by_user_id"] is not None:
        get_active_user_or_404(
            db,
            refund_data["requested_by_user_id"],
            "Requested by user not found.",
        )

    if refund_data["approved_by_user_id"] is not None:
        get_active_user_or_404(
            db,
            refund_data["approved_by_user_id"],
            "Approved by user not found.",
        )

    return db_payment


def validate_refund_amount_available(
    db: Session,
    payment_id: uuid.UUID,
    payment_amount_cents: int,
    refund_amount_cents: int,
    exclude_refund_id: uuid.UUID | None = None,
) -> None:
    statement = select(func.coalesce(func.sum(Refund.amount_cents), 0)).where(
        Refund.payment_id == payment_id,
        Refund.refund_status.in_(REFUND_AMOUNT_HOLD_STATUSES),
    )

    if exclude_refund_id is not None:
        statement = statement.where(Refund.id != exclude_refund_id)

    existing_refund_total = db.scalar(statement)

    if existing_refund_total + refund_amount_cents > payment_amount_cents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund amount exceeds the remaining refundable payment amount.",
        )


def validate_refund_is_editable(db_refund: Refund) -> None:
    if db_refund.refund_status in TERMINAL_REFUND_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Succeeded, failed, and cancelled refunds cannot be updated.",
        )


# This route records a Stripe-backed refund request or refund result after
# validating the payment and optional booking/participant scope.
@router.post("", response_model=RefundRead, status_code=status.HTTP_201_CREATED)
def create_refund(refund: RefundCreate, db: Session = Depends(get_db)) -> Refund:
    refund_data = normalize_refund_lifecycle_fields(refund.model_dump())
    validate_refund_business_rules(refund_data)
    db_payment = validate_refund_references(db, refund_data)
    if refund_data["refund_status"] in REFUND_AMOUNT_HOLD_STATUSES:
        validate_refund_amount_available(
            db,
            db_payment.id,
            db_payment.amount_cents,
            refund_data["amount_cents"],
        )

    new_refund = Refund(
        id=uuid.uuid4(),
        **refund_data,
    )

    try:
        db.add(new_refund)
        db.commit()
        db.refresh(new_refund)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_refund_conflict_detail(exc),
        ) from exc

    return new_refund


# This route fetches a single refund record by its internal UUID.
@router.get("/{refund_id}", response_model=RefundRead, status_code=status.HTTP_200_OK)
def get_refund(refund_id: uuid.UUID, db: Session = Depends(get_db)) -> Refund:
    db_refund = db.get(Refund, refund_id)

    if db_refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )

    return db_refund


# This route returns refund records currently stored in the app database.
@router.get("", response_model=list[RefundRead], status_code=status.HTTP_200_OK)
def list_refunds(
    payment_id: uuid.UUID | None = None,
    booking_id: uuid.UUID | None = None,
    participant_id: uuid.UUID | None = None,
    refund_status: str | None = None,
    refund_reason: str | None = None,
    requested_by_user_id: uuid.UUID | None = None,
    approved_by_user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
) -> list[Refund]:
    statement = select(Refund)

    if payment_id is not None:
        statement = statement.where(Refund.payment_id == payment_id)

    if booking_id is not None:
        statement = statement.where(Refund.booking_id == booking_id)

    if participant_id is not None:
        statement = statement.where(Refund.participant_id == participant_id)

    if refund_status is not None:
        if refund_status not in VALID_REFUND_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "refund_status must be 'pending', 'approved', 'processing', "
                    "'succeeded', 'failed', or 'cancelled'."
                ),
            )
        statement = statement.where(Refund.refund_status == refund_status)

    if refund_reason is not None:
        if refund_reason not in VALID_REFUND_REASONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "refund_reason must be 'player_cancelled', 'late_cancel', "
                    "'host_cancelled', 'game_cancelled', 'weather', 'admin_refund', "
                    "'duplicate_payment', or 'dispute_resolution'."
                ),
            )
        statement = statement.where(Refund.refund_reason == refund_reason)

    if requested_by_user_id is not None:
        statement = statement.where(Refund.requested_by_user_id == requested_by_user_id)

    if approved_by_user_id is not None:
        statement = statement.where(Refund.approved_by_user_id == approved_by_user_id)

    refunds = db.scalars(statement.order_by(Refund.created_at.desc())).all()
    return list(refunds)


# This route applies partial updates to an existing refund record while keeping
# references, amount limits, and lifecycle timestamps aligned with status.
@router.patch("/{refund_id}", response_model=RefundRead, status_code=status.HTTP_200_OK)
def update_refund(
    refund_id: uuid.UUID,
    refund_update: RefundUpdate,
    db: Session = Depends(get_db),
) -> Refund:
    db_refund = db.get(Refund, refund_id)

    if db_refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )

    validate_refund_is_editable(db_refund)

    update_data = refund_update.model_dump(exclude_unset=True)
    effective_refund_data = {
        "payment_id": update_data.get("payment_id", db_refund.payment_id),
        "booking_id": update_data.get("booking_id", db_refund.booking_id),
        "participant_id": update_data.get("participant_id", db_refund.participant_id),
        "provider_refund_id": update_data.get(
            "provider_refund_id",
            db_refund.provider_refund_id,
        ),
        "amount_cents": update_data.get("amount_cents", db_refund.amount_cents),
        "currency": update_data.get("currency", db_refund.currency),
        "refund_reason": update_data.get("refund_reason", db_refund.refund_reason),
        "refund_status": update_data.get("refund_status", db_refund.refund_status),
        "requested_by_user_id": update_data.get(
            "requested_by_user_id",
            db_refund.requested_by_user_id,
        ),
        "approved_by_user_id": update_data.get(
            "approved_by_user_id",
            db_refund.approved_by_user_id,
        ),
        "requested_at": update_data.get("requested_at", db_refund.requested_at),
        "approved_at": update_data.get("approved_at", db_refund.approved_at),
        "refunded_at": update_data.get("refunded_at", db_refund.refunded_at),
    }
    effective_refund_data = normalize_refund_lifecycle_fields(
        effective_refund_data, db_refund
    )
    validate_refund_business_rules(effective_refund_data)
    db_payment = validate_refund_references(db, effective_refund_data)
    if effective_refund_data["refund_status"] in REFUND_AMOUNT_HOLD_STATUSES:
        validate_refund_amount_available(
            db,
            db_payment.id,
            db_payment.amount_cents,
            effective_refund_data["amount_cents"],
            exclude_refund_id=db_refund.id,
        )

    # Lifecycle fields are managed from the fully merged refund state so partial
    # PATCH payloads cannot leave inconsistent timestamps behind.
    update_data["requested_at"] = effective_refund_data["requested_at"]
    update_data["approved_at"] = effective_refund_data["approved_at"]
    update_data["refunded_at"] = effective_refund_data["refunded_at"]

    for field_name, field_value in update_data.items():
        setattr(db_refund, field_name, field_value)

    db_refund.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_refund)
        db.commit()
        db.refresh(db_refund)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_refund_conflict_detail(exc),
        ) from exc

    return db_refund
