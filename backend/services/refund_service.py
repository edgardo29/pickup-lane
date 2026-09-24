"""Refund mutation workflows for admin/support routes."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
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
from backend.services.admin_action_service import (
    load_frozen_audited_rows,
    record_financial_sensitive_read,
    record_sensitive_admin_read_batch,
)
from backend.services.auth_service import (
    require_active_admin_user,
    user_is_active_admin,
)
from backend.services.payment_rules import COLLECTED_PAYMENT_STATUSES
from backend.services.query_pagination import (
    DEFAULT_COLLECTION_LIMIT,
    MAX_COLLECTION_LIMIT,
    bounded_collection_limit,
    bounded_collection_offset,
)
from backend.services.refund_attempt_policy import (
    expected_refund_attempt_numbers,
    refund_attempt_evidence_for_refunds,
    refund_attempt_identity_matches_refund,
)

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
    "unfulfilled_booking",
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


@dataclass(frozen=True)
class RefundPaymentLedger:
    collected_cents: int
    confirmed_returned_cents: int
    reserved_cents: int
    unresolved_attempt_cents: int = 0
    attempt_history_complete: bool = True

    @property
    def available_cents(self) -> int:
        if not self.attempt_history_complete:
            return 0
        return max(
            0,
            self.collected_cents
            - self.confirmed_returned_cents
            - self.reserved_cents
            - self.unresolved_attempt_cents,
        )


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


def get_participant_or_404(db: Session, participant_id: uuid.UUID) -> GameParticipant:
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


def get_active_user_or_404(db: Session, user_id: uuid.UUID, detail: str) -> User:
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
                "'publish_fee_refund', or 'unfulfilled_booking'."
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
    available_cents = get_refund_amount_available(
        db,
        payment_id=payment_id,
        payment_amount_cents=payment_amount_cents,
        exclude_refund_id=exclude_refund_id,
    )
    if refund_amount_cents > available_cents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund amount exceeds the remaining refundable payment amount.",
        )


def get_refund_amount_available(
    db: Session,
    *,
    payment_id: uuid.UUID,
    payment_amount_cents: int,
    exclude_refund_id: uuid.UUID | None = None,
) -> int:
    return get_refund_payment_ledger(
        db,
        payment_id=payment_id,
        payment_amount_cents=payment_amount_cents,
        exclude_refund_id=exclude_refund_id,
    ).available_cents


def get_refund_payment_ledger(
    db: Session,
    *,
    payment_id: uuid.UUID,
    payment_amount_cents: int,
    exclude_refund_id: uuid.UUID | None = None,
) -> RefundPaymentLedger:
    """Return the shared payment-wide refund conservation ledger."""
    refunds = list(
        db.scalars(
            select(Refund)
            .where(Refund.payment_id == payment_id)
            .order_by(Refund.id.asc())
        ).all()
    )
    evidence_by_refund = refund_attempt_evidence_for_refunds(
        db, (refund.id for refund in refunds)
    )
    confirmed_total = 0
    reserved_total = 0
    unresolved_total = 0
    attempt_history_complete = True
    for refund in refunds:
        evidence = evidence_by_refund.get(refund.id, {})
        confirmed_total += sum(
            attempt.amount_cents
            for attempt_number, attempt in evidence.items()
            if attempt.status == "succeeded"
            and refund_attempt_identity_matches_refund(
                refund,
                attempt_number=attempt_number,
                attempt=attempt,
            )
        )
        expected_attempts = expected_refund_attempt_numbers(refund, evidence)
        excludes_current_attempt = refund.id == exclude_refund_id
        current_is_reserved = not excludes_current_attempt and refund.refund_status in {
            "pending",
            "approved",
            "processing",
        }
        if current_is_reserved:
            reserved_total += refund.amount_cents
        for attempt_number in expected_attempts:
            attempt = evidence.get(attempt_number)
            identity_matches = (
                attempt is not None
                and refund_attempt_identity_matches_refund(
                    refund,
                    attempt_number=attempt_number,
                    attempt=attempt,
                )
            )
            if (
                identity_matches
                and attempt.status in TERMINAL_REFUND_STATUSES
            ):
                continue
            # The active current attempt is already held by the Refund row.
            if (
                attempt_number == refund.current_attempt_number
                and (current_is_reserved or excludes_current_attempt)
            ):
                if attempt is not None and not identity_matches:
                    attempt_history_complete = False
                continue
            if not identity_matches:
                attempt_history_complete = False
            unresolved_total += (
                attempt.amount_cents if attempt is not None else refund.amount_cents
            )

    if not attempt_history_complete:
        unresolved_total = max(
            unresolved_total,
            max(0, payment_amount_cents - confirmed_total - reserved_total),
        )

    return RefundPaymentLedger(
        collected_cents=payment_amount_cents,
        confirmed_returned_cents=int(confirmed_total),
        reserved_cents=int(reserved_total),
        unresolved_attempt_cents=int(unresolved_total),
        attempt_history_complete=attempt_history_complete,
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


def get_refund_for_user_or_404(
    db: Session,
    refund_id: uuid.UUID,
    current_user: User,
) -> Refund:
    refund_ref = db.execute(
        select(Refund.id, Payment.payer_user_id)
        .join(Payment, Refund.payment_id == Payment.id)
        .where(Refund.id == refund_id)
    ).one_or_none()
    if refund_ref is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )
    if refund_ref.payer_user_id != current_user.id:
        require_active_admin_user(current_user)
        record_financial_sensitive_read(
            authenticated_admin_id=current_user.id,
            action_type="read_staff_refund_detail",
            target_id=refund_id,
        )

    db_refund = db.get(Refund, refund_id)
    if db_refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )
    get_payment_or_404(db, db_refund.payment_id)
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
    limit: int = DEFAULT_COLLECTION_LIMIT,
    offset: int = 0,
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

    page_query = (
        statement.order_by(Refund.created_at.desc(), Refund.id.desc())
        .offset(bounded_collection_offset(offset))
        .limit(bounded_collection_limit(limit, max_limit=MAX_COLLECTION_LIMIT))
    )
    if not can_read_all_money:
        return list(db.scalars(page_query).all())

    selected_ids = list(db.scalars(page_query.with_only_columns(Refund.id)).all())
    if selected_ids:
        record_sensitive_admin_read_batch(
            authenticated_admin_id=current_user.id,
            action_type="read_staff_refund_list_item",
            target_ids=selected_ids,
        )
    return load_frozen_audited_rows(db, model=Refund, target_ids=selected_ids)
