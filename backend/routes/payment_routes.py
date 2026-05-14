import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, Game, Payment, User
from backend.schemas import PaymentCreate, PaymentRead, PaymentUpdate

router = APIRouter(prefix="/payments", tags=["payments"])

VALID_PAYMENT_TYPES = {
    "booking",
    "community_publish_fee",
    "refund_adjustment",
    "admin_charge",
}
VALID_PROVIDERS = {"stripe"}
VALID_PAYMENT_STATUSES = {
    "processing",
    "requires_action",
    "succeeded",
    "failed",
    "canceled",
    "refunded",
    "partially_refunded",
    "disputed",
}
VALID_CURRENCY = "USD"
PAID_HISTORY_PAYMENT_STATUSES = {
    "succeeded",
    "refunded",
    "partially_refunded",
    "disputed",
}
POST_SUCCESS_PAYMENT_STATUSES = {"refunded", "partially_refunded", "disputed"}
FAILED_PAYMENT_STATUSES = {"failed", "canceled"}


def build_payment_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_payments_provider_payment_intent_id" in error_text:
        return "A payment with this provider_payment_intent_id already exists."

    if "uq_payments_idempotency_key" in error_text:
        return "A payment with this idempotency_key already exists."

    return error_text


def get_active_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payer user not found.",
        )

    return db_user


def get_booking_or_404(db: Session, booking_id: uuid.UUID) -> Booking:
    db_booking = db.get(Booking, booking_id)

    if db_booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )

    return db_booking


def get_active_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


def validate_payment_business_rules(payment_data: dict[str, object]) -> None:
    for field_name in (
        "payer_user_id",
        "payment_type",
        "provider",
        "idempotency_key",
        "amount_cents",
        "currency",
        "payment_status",
    ):
        if payment_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if payment_data["payment_type"] not in VALID_PAYMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "payment_type must be 'booking', 'community_publish_fee', "
                "'refund_adjustment', or 'admin_charge'."
            ),
        )

    if payment_data["provider"] not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider must be 'stripe'.",
        )

    if payment_data["payment_status"] not in VALID_PAYMENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "payment_status must be 'processing', 'requires_action', "
                "'succeeded', 'failed', 'canceled', 'refunded', "
                "'partially_refunded', or 'disputed'."
            ),
        )

    if payment_data["currency"] != VALID_CURRENCY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="currency must be 'USD'.",
        )

    if payment_data["amount_cents"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount_cents must be greater than or equal to 0.",
        )

    if payment_data["payment_type"] == "booking" and payment_data["booking_id"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking payments require booking_id.",
        )

    if payment_data["payment_type"] == "booking" and payment_data["game_id"] is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking payments cannot include game_id.",
        )

    if (
        payment_data["payment_type"] == "community_publish_fee"
        and payment_data["game_id"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Community publish fee payments require game_id.",
        )

    if (
        payment_data["payment_type"] == "community_publish_fee"
        and payment_data["booking_id"] is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Community publish fee payments cannot include booking_id.",
        )

    if (
        payment_data["payment_type"] in {"refund_adjustment", "admin_charge"}
        and (
            payment_data["booking_id"] is not None
            or payment_data["game_id"] is not None
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Refund adjustment and admin charge payments cannot include "
                "booking_id or game_id."
            ),
        )

    if (
        payment_data["payment_status"] in POST_SUCCESS_PAYMENT_STATUSES
        and payment_data["paid_at"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Refunded, partially_refunded, and disputed payments require "
                "paid_at from an earlier successful payment."
            ),
        )

    if (
        payment_data["payment_status"] in FAILED_PAYMENT_STATUSES
        and payment_data["failure_reason"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed and canceled payments require failure_reason.",
        )


def normalize_payment_lifecycle_fields(
    payment_data: dict[str, object],
    existing_payment: Payment | None = None,
) -> dict[str, object]:
    normalized_data = dict(payment_data)

    # Preserve paid_at for payment states that can only happen after a
    # successful payment, including later refund or dispute history.
    if normalized_data["payment_status"] in PAID_HISTORY_PAYMENT_STATUSES:
        if normalized_data["payment_status"] == "succeeded":
            normalized_data["paid_at"] = (
                normalized_data.get("paid_at")
                or (existing_payment.paid_at if existing_payment is not None else None)
                or datetime.now(timezone.utc)
            )
        else:
            normalized_data["paid_at"] = (
                normalized_data.get("paid_at")
                or (existing_payment.paid_at if existing_payment is not None else None)
            )
    else:
        normalized_data["paid_at"] = None

    return normalized_data


# This route records a Stripe-backed payment attempt or payment result after
# validating the payer and any booking/game references.
@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)) -> Payment:
    payment_data = payment.model_dump()
    payment_data["payment_metadata"] = payment_data.pop("metadata")
    normalized_payment_data = normalize_payment_lifecycle_fields(payment_data)
    validate_payment_business_rules(normalized_payment_data)

    get_active_user_or_404(db, payment.payer_user_id)

    if payment.booking_id is not None:
        db_booking = get_booking_or_404(db, payment.booking_id)

        if db_booking.buyer_user_id != payment.payer_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking payments must use the booking buyer as payer_user_id.",
            )

    if payment.game_id is not None:
        get_active_game_or_404(db, payment.game_id)

    new_payment = Payment(
        id=uuid.uuid4(),
        **normalized_payment_data,
    )

    try:
        db.add(new_payment)
        db.commit()
        db.refresh(new_payment)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_payment_conflict_detail(exc),
        ) from exc

    return new_payment


# This route fetches a single payment record by its internal UUID.
@router.get("/{payment_id}", response_model=PaymentRead, status_code=status.HTTP_200_OK)
def get_payment(payment_id: uuid.UUID, db: Session = Depends(get_db)) -> Payment:
    db_payment = db.get(Payment, payment_id)

    if db_payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    return db_payment


# This route returns payment records currently stored in the app database.
@router.get("", response_model=list[PaymentRead], status_code=status.HTTP_200_OK)
def list_payments(
    payer_user_id: uuid.UUID | None = None,
    booking_id: uuid.UUID | None = None,
    game_id: uuid.UUID | None = None,
    payment_type: str | None = None,
    payment_status: str | None = None,
    db: Session = Depends(get_db),
) -> list[Payment]:
    statement = select(Payment)

    if payer_user_id is not None:
        statement = statement.where(Payment.payer_user_id == payer_user_id)

    if booking_id is not None:
        statement = statement.where(Payment.booking_id == booking_id)

    if game_id is not None:
        statement = statement.where(Payment.game_id == game_id)

    if payment_type is not None:
        if payment_type not in VALID_PAYMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "payment_type must be 'booking', 'community_publish_fee', "
                    "'refund_adjustment', or 'admin_charge'."
                ),
            )
        statement = statement.where(Payment.payment_type == payment_type)

    if payment_status is not None:
        if payment_status not in VALID_PAYMENT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "payment_status must be 'processing', 'requires_action', "
                    "'succeeded', 'failed', 'canceled', 'refunded', "
                    "'partially_refunded', or 'disputed'."
                ),
            )
        statement = statement.where(Payment.payment_status == payment_status)

    payments = db.scalars(statement.order_by(Payment.created_at.desc())).all()
    return list(payments)


# This route applies partial updates to an existing payment record while
# keeping references and payment lifecycle timestamps aligned with status.
@router.patch(
    "/{payment_id}", response_model=PaymentRead, status_code=status.HTTP_200_OK
)
def update_payment(
    payment_id: uuid.UUID,
    payment_update: PaymentUpdate,
    db: Session = Depends(get_db),
) -> Payment:
    db_payment = db.get(Payment, payment_id)

    if db_payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    update_data = payment_update.model_dump(exclude_unset=True)

    if "metadata" in update_data:
        update_data["payment_metadata"] = update_data.pop("metadata")

    effective_payment_data = {
        "payer_user_id": update_data.get("payer_user_id", db_payment.payer_user_id),
        "booking_id": update_data.get("booking_id", db_payment.booking_id),
        "game_id": update_data.get("game_id", db_payment.game_id),
        "payment_type": update_data.get("payment_type", db_payment.payment_type),
        "provider": update_data.get("provider", db_payment.provider),
        "provider_payment_intent_id": update_data.get(
            "provider_payment_intent_id",
            db_payment.provider_payment_intent_id,
        ),
        "provider_charge_id": update_data.get(
            "provider_charge_id", db_payment.provider_charge_id
        ),
        "idempotency_key": update_data.get(
            "idempotency_key", db_payment.idempotency_key
        ),
        "amount_cents": update_data.get("amount_cents", db_payment.amount_cents),
        "currency": update_data.get("currency", db_payment.currency),
        "payment_status": update_data.get("payment_status", db_payment.payment_status),
        "paid_at": update_data.get("paid_at", db_payment.paid_at),
        "failure_reason": update_data.get("failure_reason", db_payment.failure_reason),
        "payment_metadata": update_data.get(
            "payment_metadata", db_payment.payment_metadata
        ),
    }
    effective_payment_data = normalize_payment_lifecycle_fields(
        effective_payment_data, db_payment
    )
    validate_payment_business_rules(effective_payment_data)

    get_active_user_or_404(db, effective_payment_data["payer_user_id"])

    if effective_payment_data["booking_id"] is not None:
        db_booking = get_booking_or_404(db, effective_payment_data["booking_id"])

        if db_booking.buyer_user_id != effective_payment_data["payer_user_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking payments must use the booking buyer as payer_user_id.",
            )

    if effective_payment_data["game_id"] is not None:
        get_active_game_or_404(db, effective_payment_data["game_id"])

    # Lifecycle fields are managed from the fully merged payment state so
    # partial PATCH payloads cannot keep stale timestamps around.
    update_data["paid_at"] = effective_payment_data["paid_at"]

    for field_name, field_value in update_data.items():
        setattr(db_payment, field_name, field_value)

    db_payment.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_payment_conflict_detail(exc),
        ) from exc

    return db_payment
