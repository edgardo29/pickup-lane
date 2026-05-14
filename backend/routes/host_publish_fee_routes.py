import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Game, HostPublishFee, Payment, User
from backend.schemas import (
    HostPublishFeeCreate,
    HostPublishFeeRead,
    HostPublishFeeUpdate,
)

router = APIRouter(prefix="/host-publish-fees", tags=["host_publish_fees"])

VALID_FEE_STATUSES = {"pending", "paid", "waived", "failed", "refunded"}
VALID_WAIVER_REASONS = {"none", "first_game_free", "admin_comp"}
VALID_CURRENCY = "USD"


def build_host_publish_fee_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_host_publish_fees_game_id" in error_text:
        return "This game already has a host publish fee."

    if "uq_host_publish_fees_payment_id" in error_text:
        return "This payment is already attached to a host publish fee."

    if "ux_host_publish_fees_one_first_free_per_host" in error_text:
        return "This host has already used their first free game."

    return error_text


def get_active_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


def get_active_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host user not found.",
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


def normalize_host_publish_fee_lifecycle_fields(
    fee_data: dict[str, object],
    existing_fee: HostPublishFee | None = None,
) -> dict[str, object]:
    normalized_data = dict(fee_data)
    now = datetime.now(timezone.utc)

    normalized_data["required_at"] = (
        normalized_data.get("required_at")
        or (existing_fee.required_at if existing_fee is not None else None)
        or now
    )

    if normalized_data["fee_status"] == "paid":
        normalized_data["paid_at"] = (
            normalized_data.get("paid_at")
            or (existing_fee.paid_at if existing_fee is not None else None)
            or now
        )
    else:
        normalized_data["paid_at"] = None

    if normalized_data["fee_status"] == "failed":
        normalized_data["failed_at"] = (
            normalized_data.get("failed_at")
            or (existing_fee.failed_at if existing_fee is not None else None)
            or now
        )
    else:
        normalized_data["failed_at"] = None

    if normalized_data["fee_status"] == "refunded":
        normalized_data["refunded_at"] = (
            normalized_data.get("refunded_at")
            or (existing_fee.refunded_at if existing_fee is not None else None)
            or now
        )
    else:
        normalized_data["refunded_at"] = None

    return normalized_data


def validate_host_publish_fee_business_rules(
    fee_data: dict[str, object],
) -> None:
    for field_name in (
        "game_id",
        "host_user_id",
        "amount_cents",
        "currency",
        "fee_status",
        "waiver_reason",
        "required_at",
    ):
        if fee_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if fee_data["amount_cents"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount_cents must be greater than or equal to 0.",
        )

    if fee_data["currency"] != VALID_CURRENCY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="currency must be 'USD'.",
        )

    if fee_data["fee_status"] not in VALID_FEE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "fee_status must be 'pending', 'paid', 'waived', "
                "'failed', or 'refunded'."
            ),
        )

    if fee_data["waiver_reason"] not in VALID_WAIVER_REASONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "waiver_reason must be 'none', 'first_game_free', "
                "or 'admin_comp'."
            ),
        )

    if fee_data["fee_status"] == "paid" and (
        fee_data["payment_id"] is None
        or fee_data["paid_at"] is None
        or fee_data["amount_cents"] <= 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paid publish fees require payment_id, paid_at, and amount_cents > 0.",
        )

    if fee_data["fee_status"] == "waived" and (
        fee_data["amount_cents"] != 0
        or fee_data["waiver_reason"] == "none"
        or fee_data["payment_id"] is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Waived publish fees require amount_cents 0, a waiver reason, "
                "and no payment_id."
            ),
        )

    if fee_data["fee_status"] == "failed" and fee_data["failed_at"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed publish fees require failed_at.",
        )

    if fee_data["fee_status"] == "refunded" and (
        fee_data["payment_id"] is None or fee_data["refunded_at"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refunded publish fees require payment_id and refunded_at.",
        )


def validate_host_publish_fee_references(
    db: Session,
    fee_data: dict[str, object],
) -> None:
    db_game = get_active_game_or_404(db, fee_data["game_id"])
    get_active_user_or_404(db, fee_data["host_user_id"])

    if db_game.game_type != "community":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host publish fees require a community game.",
        )

    if db_game.host_user_id != fee_data["host_user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="host_user_id must match the game's host_user_id.",
        )

    if fee_data["payment_id"] is not None:
        db_payment = get_payment_or_404(db, fee_data["payment_id"])

        if db_payment.payment_type != "community_publish_fee":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="payment_id must reference a community_publish_fee payment.",
            )

        if db_payment.game_id != fee_data["game_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="payment_id must reference the same game_id.",
            )

        if db_payment.payer_user_id != fee_data["host_user_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="payment_id must use the host as payer_user_id.",
            )


@router.post(
    "", response_model=HostPublishFeeRead, status_code=status.HTTP_201_CREATED
)
def create_host_publish_fee(
    host_publish_fee: HostPublishFeeCreate, db: Session = Depends(get_db)
) -> HostPublishFee:
    fee_data = normalize_host_publish_fee_lifecycle_fields(
        host_publish_fee.model_dump()
    )
    validate_host_publish_fee_business_rules(fee_data)
    validate_host_publish_fee_references(db, fee_data)

    new_host_publish_fee = HostPublishFee(id=uuid.uuid4(), **fee_data)

    try:
        db.add(new_host_publish_fee)
        db.commit()
        db.refresh(new_host_publish_fee)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_host_publish_fee_conflict_detail(exc),
        ) from exc

    return new_host_publish_fee


@router.get(
    "/{host_publish_fee_id}",
    response_model=HostPublishFeeRead,
    status_code=status.HTTP_200_OK,
)
def get_host_publish_fee(
    host_publish_fee_id: uuid.UUID, db: Session = Depends(get_db)
) -> HostPublishFee:
    db_host_publish_fee = db.get(HostPublishFee, host_publish_fee_id)

    if db_host_publish_fee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host publish fee not found.",
        )

    return db_host_publish_fee


@router.get(
    "", response_model=list[HostPublishFeeRead], status_code=status.HTTP_200_OK
)
def list_host_publish_fees(
    game_id: uuid.UUID | None = None,
    host_user_id: uuid.UUID | None = None,
    fee_status: str | None = None,
    db: Session = Depends(get_db),
) -> list[HostPublishFee]:
    statement = select(HostPublishFee)

    if game_id is not None:
        statement = statement.where(HostPublishFee.game_id == game_id)

    if host_user_id is not None:
        statement = statement.where(HostPublishFee.host_user_id == host_user_id)

    if fee_status is not None:
        if fee_status not in VALID_FEE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fee_status is not supported.",
            )
        statement = statement.where(HostPublishFee.fee_status == fee_status)

    host_publish_fees = db.scalars(
        statement.order_by(HostPublishFee.created_at.desc())
    ).all()
    return list(host_publish_fees)


@router.patch(
    "/{host_publish_fee_id}",
    response_model=HostPublishFeeRead,
    status_code=status.HTTP_200_OK,
)
def update_host_publish_fee(
    host_publish_fee_id: uuid.UUID,
    host_publish_fee_update: HostPublishFeeUpdate,
    db: Session = Depends(get_db),
) -> HostPublishFee:
    db_host_publish_fee = db.get(HostPublishFee, host_publish_fee_id)

    if db_host_publish_fee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host publish fee not found.",
        )

    update_data = host_publish_fee_update.model_dump(exclude_unset=True)
    effective_fee_data = {
        "game_id": update_data.get("game_id", db_host_publish_fee.game_id),
        "host_user_id": update_data.get(
            "host_user_id", db_host_publish_fee.host_user_id
        ),
        "payment_id": update_data.get("payment_id", db_host_publish_fee.payment_id),
        "amount_cents": update_data.get(
            "amount_cents", db_host_publish_fee.amount_cents
        ),
        "currency": update_data.get("currency", db_host_publish_fee.currency),
        "fee_status": update_data.get("fee_status", db_host_publish_fee.fee_status),
        "waiver_reason": update_data.get(
            "waiver_reason", db_host_publish_fee.waiver_reason
        ),
        "required_at": update_data.get("required_at", db_host_publish_fee.required_at),
        "paid_at": update_data.get("paid_at", db_host_publish_fee.paid_at),
        "failed_at": update_data.get("failed_at", db_host_publish_fee.failed_at),
        "refunded_at": update_data.get(
            "refunded_at", db_host_publish_fee.refunded_at
        ),
    }
    effective_fee_data = normalize_host_publish_fee_lifecycle_fields(
        effective_fee_data, db_host_publish_fee
    )
    validate_host_publish_fee_business_rules(effective_fee_data)
    validate_host_publish_fee_references(db, effective_fee_data)

    for field_name, field_value in update_data.items():
        setattr(db_host_publish_fee, field_name, field_value)

    db_host_publish_fee.required_at = effective_fee_data["required_at"]
    db_host_publish_fee.paid_at = effective_fee_data["paid_at"]
    db_host_publish_fee.failed_at = effective_fee_data["failed_at"]
    db_host_publish_fee.refunded_at = effective_fee_data["refunded_at"]
    db_host_publish_fee.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_host_publish_fee)
        db.commit()
        db.refresh(db_host_publish_fee)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_host_publish_fee_conflict_detail(exc),
        ) from exc

    return db_host_publish_fee
