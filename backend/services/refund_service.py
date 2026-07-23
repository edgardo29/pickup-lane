"""Refund mutation workflows for admin/support routes."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    GameParticipant,
    HostPublishFee,
    Payment,
    Refund,
    User,
)
from backend.schemas.refund_schema import RefundCreate, RefundUpdate
from backend.services.admin_action_service import record_admin_action
from backend.services.auth_service import require_active_admin_user, user_is_active_admin
from backend.services.payment_rules import COLLECTED_PAYMENT_STATUSES
from backend.services.refund_event_service import record_refund_event

VALID_REFUND_REASONS = {
    "player_cancelled",
    "late_cancel",
    "host_cancelled",
    "game_cancelled",
    "weather",
    "admin_refund",
    "duplicate_payment",
    "dispute_resolution",
    "publish_fee_refund",
}
VALID_REFUND_STATUSES = {
    "pending",
    "approved",
    "processing",
    "succeeded",
    "failed",
    "cancelled",
}
VALID_REFUND_ORIGIN_WORKFLOWS = {
    "player_removal",
    "official_game_cancellation",
    "community_publish_fee_refund",
    "direct_admin_refund",
    "official_game_checkout",
    "pending_checkout_expiration",
    "pending_checkout_cancellation",
    "admin_game_update",
}
VALID_PROVIDERS = {"stripe"}
VALID_PROVIDER_REFUND_STATUSES = {
    "processing",
    "succeeded",
    "failed",
    "cancelled",
    "unknown",
}
VALID_CURRENCY = "USD"
REFUNDABLE_PAYMENT_STATUSES = COLLECTED_PAYMENT_STATUSES
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


def get_host_publish_fee_or_404(
    db: Session,
    host_publish_fee_id: uuid.UUID,
) -> HostPublishFee:
    db_host_publish_fee = db.get(HostPublishFee, host_publish_fee_id)

    if db_host_publish_fee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host publish fee not found.",
        )

    return db_host_publish_fee


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
                "'duplicate_payment', 'dispute_resolution', or "
                "'publish_fee_refund'."
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

    if refund_data["origin_workflow"] not in VALID_REFUND_ORIGIN_WORKFLOWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="origin_workflow is not supported.",
        )

    if refund_data["provider"] not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider must be 'stripe'.",
        )

    if (
        refund_data["provider_status"] is not None
        and refund_data["provider_status"] not in VALID_PROVIDER_REFUND_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider_status is not supported.",
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

    has_booking_target = (
        refund_data["booking_id"] is not None
        or refund_data["participant_id"] is not None
    )
    has_host_publish_fee_target = refund_data["host_publish_fee_id"] is not None
    if not has_booking_target and not has_host_publish_fee_target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refunds require booking_id, participant_id, or host_publish_fee_id.",
        )

    if has_booking_target and has_host_publish_fee_target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host publish fee refunds cannot include booking or participant targets.",
        )

    if (
        has_host_publish_fee_target
        and refund_data["refund_reason"] != "publish_fee_refund"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host publish fee refunds require refund_reason 'publish_fee_refund'.",
        )

    if has_booking_target and refund_data["refund_reason"] == "publish_fee_refund":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="publish_fee_refund requires host_publish_fee_id.",
        )


def reject_generic_host_publish_fee_refund_mutation(
    refund_data: dict[str, object],
) -> None:
    if refund_data["host_publish_fee_id"] is None:
        return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            "Host publish fee refunds must be recorded through "
            "admin financial outcomes."
        ),
    )


def validate_refund_status(value: str) -> None:
    if value not in VALID_REFUND_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "refund_status must be 'pending', 'approved', 'processing', "
                "'succeeded', 'failed', or 'cancelled'."
            ),
        )


def validate_refund_reason(value: str) -> None:
    if value not in VALID_REFUND_REASONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "refund_reason must be 'player_cancelled', 'late_cancel', "
                "'host_cancelled', 'game_cancelled', 'weather', 'admin_refund', "
                "'duplicate_payment', 'dispute_resolution', or "
                "'publish_fee_refund'."
            ),
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

    if refund_data["host_publish_fee_id"] is not None:
        db_host_publish_fee = get_host_publish_fee_or_404(
            db,
            refund_data["host_publish_fee_id"],
        )

        if db_payment.payment_type != "community_publish_fee":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Host publish fee refunds require a community publish fee payment.",
            )

        if db_host_publish_fee.payment_id != db_payment.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="host_publish_fee_id must match the payment.",
            )

        if db_host_publish_fee.host_user_id != db_payment.payer_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Host publish fee payment must use the host as payer.",
            )

        return db_payment

    if db_payment.booking_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking or participant refunds require a booking payment.",
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


def refund_audit_snapshot(refund: Refund) -> dict[str, Any]:
    return {
        "refund_status": refund.refund_status,
        "refund_reason": refund.refund_reason,
        "amount_cents": refund.amount_cents,
        "currency": refund.currency,
    }


def refund_audit_metadata(
    refund: Refund,
    *,
    source: str,
    before: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "source": source,
        "refund_status": refund.refund_status,
        "refund_reason": refund.refund_reason,
        "amount_cents": refund.amount_cents,
        "currency": refund.currency,
        "origin_workflow": refund.origin_workflow,
        "host_publish_fee_id": str(refund.host_publish_fee_id)
        if refund.host_publish_fee_id is not None
        else None,
    }

    if before is not None:
        metadata["old_refund_status"] = before["refund_status"]
        metadata["new_refund_status"] = refund.refund_status
        metadata["before"] = before
        metadata["after"] = refund_audit_snapshot(refund)

    return metadata


def create_refund_record(
    db: Session,
    *,
    admin_user: User,
    payload: RefundCreate,
) -> Refund:
    refund_data = normalize_refund_lifecycle_fields(payload.model_dump())
    validate_refund_business_rules(refund_data)
    reject_generic_host_publish_fee_refund_mutation(refund_data)
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
        db.flush()
        admin_action = record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="create_refund",
            target_user_id=db_payment.payer_user_id,
            target_booking_id=new_refund.booking_id,
            target_participant_id=new_refund.participant_id,
            target_payment_id=new_refund.payment_id,
            target_refund_id=new_refund.id,
            target_host_publish_fee_id=new_refund.host_publish_fee_id,
            metadata=refund_audit_metadata(
                new_refund,
                source="refund_route_create",
            ),
        )
        record_refund_event(
            db,
            refund=new_refund,
            event_type=(
                "provider_result_recorded"
                if new_refund.provider_status is not None
                else "local_status_changed"
            ),
            event_source="admin",
            actor_user_id=admin_user.id,
            admin_action_id=admin_action.id,
            provider=new_refund.provider,
            provider_refund_id=new_refund.provider_refund_id,
            provider_charge_id=new_refund.provider_charge_id,
            provider_status=new_refund.provider_status,
            new_refund_status=new_refund.refund_status,
            reason_code="refund_route_create",
            summary="Admin refund record created.",
        )
        db.commit()
        db.refresh(new_refund)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_refund_conflict_detail(exc),
        ) from exc

    return new_refund


def get_refund_for_user_or_404(
    db: Session,
    refund_id: uuid.UUID,
    current_user: User,
) -> Refund:
    db_refund = db.get(Refund, refund_id)

    if db_refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )

    db_payment = get_payment_or_404(db, db_refund.payment_id)
    if db_payment.payer_user_id != current_user.id:
        require_active_admin_user(current_user)

    return db_refund


def list_refunds(
    db: Session,
    current_user: User,
    *,
    payment_id: uuid.UUID | None = None,
    booking_id: uuid.UUID | None = None,
    participant_id: uuid.UUID | None = None,
    host_publish_fee_id: uuid.UUID | None = None,
    refund_status: str | None = None,
    refund_reason: str | None = None,
    requested_by_user_id: uuid.UUID | None = None,
    approved_by_user_id: uuid.UUID | None = None,
) -> list[Refund]:
    can_read_all_money = user_is_active_admin(current_user)
    statement = select(Refund).join(Payment, Refund.payment_id == Payment.id)

    if not can_read_all_money:
        statement = statement.where(Payment.payer_user_id == current_user.id)

    if payment_id is not None:
        statement = statement.where(Refund.payment_id == payment_id)

    if booking_id is not None:
        statement = statement.where(Refund.booking_id == booking_id)

    if participant_id is not None:
        statement = statement.where(Refund.participant_id == participant_id)

    if host_publish_fee_id is not None:
        statement = statement.where(Refund.host_publish_fee_id == host_publish_fee_id)

    if refund_status is not None:
        validate_refund_status(refund_status)
        statement = statement.where(Refund.refund_status == refund_status)

    if refund_reason is not None:
        validate_refund_reason(refund_reason)
        statement = statement.where(Refund.refund_reason == refund_reason)

    if requested_by_user_id is not None:
        statement = statement.where(Refund.requested_by_user_id == requested_by_user_id)

    if approved_by_user_id is not None:
        statement = statement.where(Refund.approved_by_user_id == approved_by_user_id)

    refunds = db.scalars(statement.order_by(Refund.created_at.desc())).all()
    return list(refunds)


def update_refund_record(
    db: Session,
    *,
    admin_user: User,
    refund_id: uuid.UUID,
    payload: RefundUpdate,
) -> Refund:
    db_refund = db.get(Refund, refund_id)

    if db_refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )

    validate_refund_is_editable(db_refund)

    before_snapshot = refund_audit_snapshot(db_refund)
    update_data = payload.model_dump(exclude_unset=True)
    provider_owned_fields = {
        "origin_workflow",
        "provider",
        "provider_refund_id",
        "provider_charge_id",
        "provider_status",
        "provider_status_observed_at",
        "last_refund_event_at",
    }
    protected_fields = sorted(provider_owned_fields.intersection(update_data))
    if protected_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Refund provider snapshot fields and origin_workflow are managed "
                "by refund workflow services."
            ),
        )
    effective_refund_data = {
        "payment_id": update_data.get("payment_id", db_refund.payment_id),
        "booking_id": update_data.get("booking_id", db_refund.booking_id),
        "participant_id": update_data.get("participant_id", db_refund.participant_id),
        "host_publish_fee_id": update_data.get(
            "host_publish_fee_id",
            db_refund.host_publish_fee_id,
        ),
        "origin_workflow": update_data.get(
            "origin_workflow",
            db_refund.origin_workflow,
        ),
        "provider": update_data.get("provider", db_refund.provider),
        "provider_refund_id": update_data.get(
            "provider_refund_id",
            db_refund.provider_refund_id,
        ),
        "provider_charge_id": update_data.get(
            "provider_charge_id",
            db_refund.provider_charge_id,
        ),
        "provider_status": update_data.get(
            "provider_status",
            db_refund.provider_status,
        ),
        "provider_status_observed_at": update_data.get(
            "provider_status_observed_at",
            db_refund.provider_status_observed_at,
        ),
        "last_refund_event_at": update_data.get(
            "last_refund_event_at",
            db_refund.last_refund_event_at,
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
    reject_generic_host_publish_fee_refund_mutation(effective_refund_data)
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
        db.flush()
        admin_action = record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="update_refund",
            target_user_id=db_payment.payer_user_id,
            target_booking_id=db_refund.booking_id,
            target_participant_id=db_refund.participant_id,
            target_payment_id=db_refund.payment_id,
            target_refund_id=db_refund.id,
            target_host_publish_fee_id=db_refund.host_publish_fee_id,
            metadata=refund_audit_metadata(
                db_refund,
                source="refund_route_update",
                before=before_snapshot,
            ),
        )
        record_refund_event(
            db,
            refund=db_refund,
            event_type=(
                "provider_result_recorded"
                if db_refund.provider_status is not None
                else "local_status_changed"
            ),
            event_source="admin",
            actor_user_id=admin_user.id,
            admin_action_id=admin_action.id,
            provider=db_refund.provider,
            provider_refund_id=db_refund.provider_refund_id,
            provider_charge_id=db_refund.provider_charge_id,
            provider_status=db_refund.provider_status,
            previous_refund_status=before_snapshot["refund_status"],
            new_refund_status=db_refund.refund_status,
            reason_code="refund_route_update",
            summary="Admin refund record updated.",
        )
        db.commit()
        db.refresh(db_refund)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_refund_conflict_detail(exc),
        ) from exc

    return db_refund
