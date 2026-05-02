import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Game, HostDeposit, Payment, Refund, User
from backend.schemas import HostDepositCreate, HostDepositRead, HostDepositUpdate

router = APIRouter(prefix="/host-deposits", tags=["host_deposits"])

VALID_DEPOSIT_STATUSES = {
    "required",
    "payment_pending",
    "paid",
    "held",
    "released",
    "refunded",
    "forfeited",
    "waived",
}
VALID_CURRENCY = "USD"
PAYMENT_REQUIRED_DEPOSIT_STATUSES = {
    "paid",
    "held",
    "released",
    "refunded",
    "forfeited",
}
PAID_HISTORY_DEPOSIT_STATUSES = {
    "paid",
    "held",
    "released",
    "refunded",
    "forfeited",
}
TERMINAL_DEPOSIT_STATUSES = {
    "released",
    "refunded",
    "forfeited",
    "waived",
}


def build_host_deposit_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_host_deposits_game_id" in error_text:
        return "This game already has a host deposit."

    if "uq_host_deposits_payment_id" in error_text:
        return "This payment is already attached to a host deposit."

    if "uq_host_deposits_refund_id" in error_text:
        return "This refund is already attached to a host deposit."

    return error_text


def get_active_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


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


def get_payment_or_404(db: Session, payment_id: uuid.UUID) -> Payment:
    db_payment = db.get(Payment, payment_id)

    if db_payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    return db_payment


def get_refund_or_404(db: Session, refund_id: uuid.UUID) -> Refund:
    db_refund = db.get(Refund, refund_id)

    if db_refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )

    return db_refund


def validate_host_deposit_business_rules(deposit_data: dict[str, object]) -> None:
    for field_name in (
        "game_id",
        "host_user_id",
        "required_amount_cents",
        "currency",
        "deposit_status",
    ):
        if deposit_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if deposit_data["deposit_status"] not in VALID_DEPOSIT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "deposit_status must be 'required', 'payment_pending', 'paid', "
                "'held', 'released', 'refunded', 'forfeited', or 'waived'."
            ),
        )

    if deposit_data["currency"] != VALID_CURRENCY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="currency must be 'USD'.",
        )

    if deposit_data["required_amount_cents"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="required_amount_cents must be greater than or equal to 0.",
        )

    if (
        deposit_data["deposit_status"] in PAYMENT_REQUIRED_DEPOSIT_STATUSES
        and deposit_data["payment_id"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Paid, held, released, refunded, and forfeited deposits require "
                "payment_id."
            ),
        )

    if deposit_data["deposit_status"] == "refunded" and deposit_data["refund_id"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refunded deposits require refund_id.",
        )

    if (
        deposit_data["deposit_status"] == "forfeited"
        and deposit_data["decision_reason"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forfeited deposits require decision_reason.",
        )

    if deposit_data["deposit_status"] == "waived" and deposit_data["payment_id"] is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Waived deposits cannot include payment_id.",
        )

    if deposit_data["deposit_status"] != "refunded" and deposit_data["refund_id"] is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only refunded deposits may include refund_id.",
        )


def normalize_host_deposit_lifecycle_fields(
    deposit_data: dict[str, object],
    existing_host_deposit: HostDeposit | None = None,
) -> dict[str, object]:
    normalized_data = dict(deposit_data)
    now = datetime.now(timezone.utc)

    # Deposit lifecycle timestamps are derived from status instead of trusting
    # clients to keep old and new lifecycle states aligned.
    if normalized_data["deposit_status"] in PAID_HISTORY_DEPOSIT_STATUSES:
        normalized_data["paid_at"] = (
            normalized_data.get("paid_at")
            or (
                existing_host_deposit.paid_at
                if existing_host_deposit is not None
                else None
            )
            or now
        )
    else:
        normalized_data["paid_at"] = None

    if normalized_data["deposit_status"] == "released":
        normalized_data["released_at"] = (
            normalized_data.get("released_at")
            or (
                existing_host_deposit.released_at
                if existing_host_deposit is not None
                else None
            )
            or now
        )
    else:
        normalized_data["released_at"] = None

    if normalized_data["deposit_status"] == "forfeited":
        normalized_data["forfeited_at"] = (
            normalized_data.get("forfeited_at")
            or (
                existing_host_deposit.forfeited_at
                if existing_host_deposit is not None
                else None
            )
            or now
        )
    else:
        normalized_data["forfeited_at"] = None

    if normalized_data["deposit_status"] == "refunded":
        normalized_data["refunded_at"] = (
            normalized_data.get("refunded_at")
            or (
                existing_host_deposit.refunded_at
                if existing_host_deposit is not None
                else None
            )
            or now
        )
    else:
        normalized_data["refunded_at"] = None

    return normalized_data


def validate_host_deposit_references(
    db: Session,
    deposit_data: dict[str, object],
) -> None:
    db_game = get_active_game_or_404(db, deposit_data["game_id"])
    get_active_user_or_404(db, deposit_data["host_user_id"], "Host user not found.")

    if db_game.game_type != "community":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host deposits can only be created for community games.",
        )

    if db_game.host_user_id != deposit_data["host_user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="host_user_id must match the game host_user_id.",
        )

    if deposit_data["payment_id"] is not None:
        db_payment = get_payment_or_404(db, deposit_data["payment_id"])

        if db_payment.payment_type != "host_deposit":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Host deposit payment_id must reference a host_deposit payment.",
            )

        if db_payment.game_id != deposit_data["game_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="payment_id must belong to game_id.",
            )

        if db_payment.payer_user_id != deposit_data["host_user_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="payment_id must use host_user_id as payer_user_id.",
            )

        if (
            deposit_data["deposit_status"] in PAID_HISTORY_DEPOSIT_STATUSES
            and db_payment.payment_status != "succeeded"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Paid, held, released, refunded, and forfeited deposits "
                    "require a succeeded payment."
                ),
            )

    if deposit_data["refund_id"] is not None:
        db_refund = get_refund_or_404(db, deposit_data["refund_id"])

        if db_refund.payment_id != deposit_data["payment_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="refund_id must belong to payment_id.",
            )

        if db_refund.refund_status != "succeeded":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refunded deposits require a succeeded refund.",
            )

    if deposit_data["decision_by_user_id"] is not None:
        get_active_user_or_404(
            db,
            deposit_data["decision_by_user_id"],
            "Decision by user not found.",
        )


def validate_host_deposit_is_editable(db_host_deposit: HostDeposit) -> None:
    if db_host_deposit.deposit_status in TERMINAL_DEPOSIT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Released, refunded, forfeited, and waived host deposits "
                "cannot be updated."
            ),
        )


# This route records the host deposit lifecycle row for one community game
# after validating the game host and optional payment/refund references.
@router.post("", response_model=HostDepositRead, status_code=status.HTTP_201_CREATED)
def create_host_deposit(
    host_deposit: HostDepositCreate,
    db: Session = Depends(get_db),
) -> HostDeposit:
    deposit_data = normalize_host_deposit_lifecycle_fields(host_deposit.model_dump())
    validate_host_deposit_business_rules(deposit_data)
    validate_host_deposit_references(db, deposit_data)

    new_host_deposit = HostDeposit(
        id=uuid.uuid4(),
        **deposit_data,
    )

    try:
        db.add(new_host_deposit)
        db.commit()
        db.refresh(new_host_deposit)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_host_deposit_conflict_detail(exc),
        ) from exc

    return new_host_deposit


# This route fetches a single host deposit record by its internal UUID.
@router.get(
    "/{host_deposit_id}",
    response_model=HostDepositRead,
    status_code=status.HTTP_200_OK,
)
def get_host_deposit(
    host_deposit_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> HostDeposit:
    db_host_deposit = db.get(HostDeposit, host_deposit_id)

    if db_host_deposit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host deposit not found.",
        )

    return db_host_deposit


# This route returns host deposit records currently stored in the app database.
@router.get("", response_model=list[HostDepositRead], status_code=status.HTTP_200_OK)
def list_host_deposits(
    game_id: uuid.UUID | None = None,
    host_user_id: uuid.UUID | None = None,
    payment_id: uuid.UUID | None = None,
    refund_id: uuid.UUID | None = None,
    deposit_status: str | None = None,
    decision_by_user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
) -> list[HostDeposit]:
    statement = select(HostDeposit)

    if game_id is not None:
        statement = statement.where(HostDeposit.game_id == game_id)

    if host_user_id is not None:
        statement = statement.where(HostDeposit.host_user_id == host_user_id)

    if payment_id is not None:
        statement = statement.where(HostDeposit.payment_id == payment_id)

    if refund_id is not None:
        statement = statement.where(HostDeposit.refund_id == refund_id)

    if deposit_status is not None:
        if deposit_status not in VALID_DEPOSIT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "deposit_status must be 'required', 'payment_pending', 'paid', "
                    "'held', 'released', 'refunded', 'forfeited', or 'waived'."
                ),
            )
        statement = statement.where(HostDeposit.deposit_status == deposit_status)

    if decision_by_user_id is not None:
        statement = statement.where(
            HostDeposit.decision_by_user_id == decision_by_user_id
        )

    host_deposits = db.scalars(
        statement.order_by(HostDeposit.created_at.desc())
    ).all()
    return list(host_deposits)


# This route applies partial updates to an existing host deposit while keeping
# payment/refund references and lifecycle timestamps aligned with status.
@router.patch(
    "/{host_deposit_id}",
    response_model=HostDepositRead,
    status_code=status.HTTP_200_OK,
)
def update_host_deposit(
    host_deposit_id: uuid.UUID,
    host_deposit_update: HostDepositUpdate,
    db: Session = Depends(get_db),
) -> HostDeposit:
    db_host_deposit = db.get(HostDeposit, host_deposit_id)

    if db_host_deposit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host deposit not found.",
        )

    validate_host_deposit_is_editable(db_host_deposit)

    update_data = host_deposit_update.model_dump(exclude_unset=True)
    effective_deposit_data = {
        "game_id": update_data.get("game_id", db_host_deposit.game_id),
        "host_user_id": update_data.get("host_user_id", db_host_deposit.host_user_id),
        "required_amount_cents": update_data.get(
            "required_amount_cents",
            db_host_deposit.required_amount_cents,
        ),
        "currency": update_data.get("currency", db_host_deposit.currency),
        "deposit_status": update_data.get(
            "deposit_status",
            db_host_deposit.deposit_status,
        ),
        "payment_id": update_data.get("payment_id", db_host_deposit.payment_id),
        "refund_id": update_data.get("refund_id", db_host_deposit.refund_id),
        "paid_at": update_data.get("paid_at", db_host_deposit.paid_at),
        "released_at": update_data.get("released_at", db_host_deposit.released_at),
        "forfeited_at": update_data.get("forfeited_at", db_host_deposit.forfeited_at),
        "refunded_at": update_data.get("refunded_at", db_host_deposit.refunded_at),
        "decision_by_user_id": update_data.get(
            "decision_by_user_id",
            db_host_deposit.decision_by_user_id,
        ),
        "decision_reason": update_data.get(
            "decision_reason",
            db_host_deposit.decision_reason,
        ),
    }
    effective_deposit_data = normalize_host_deposit_lifecycle_fields(
        effective_deposit_data,
        db_host_deposit,
    )
    validate_host_deposit_business_rules(effective_deposit_data)
    validate_host_deposit_references(db, effective_deposit_data)

    # Lifecycle timestamps are derived from the fully merged deposit state so
    # partial PATCH payloads cannot leave stale timestamps behind.
    update_data["paid_at"] = effective_deposit_data["paid_at"]
    update_data["released_at"] = effective_deposit_data["released_at"]
    update_data["forfeited_at"] = effective_deposit_data["forfeited_at"]
    update_data["refunded_at"] = effective_deposit_data["refunded_at"]

    for field_name, field_value in update_data.items():
        setattr(db_host_deposit, field_name, field_value)

    db_host_deposit.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_host_deposit)
        db.commit()
        db.refresh(db_host_deposit)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_host_deposit_conflict_detail(exc),
        ) from exc

    return db_host_deposit
