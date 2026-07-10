import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameCreditUsage,
    GameParticipant,
    Payment,
    Refund,
    User,
    WaitlistEntry,
)
from backend.schemas.admin_official_game_schema import (
    AdminOfficialGamePlayerRemovalExecute,
    AdminOfficialGamePlayerRemovalPreviewRead,
    AdminOfficialGamePlayerRemovalResultRead,
    AdminOfficialGameRemovalParticipantRead,
    AdminOfficialGameRemovalRefundRead,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_permission_service import (
    PERMISSION_MONEY_CREDIT_MANAGE,
    PERMISSION_MONEY_REFUND,
    require_user_admin_permission,
)
from backend.services.game_credit_service import (
    GameCreditLedgerError,
    restore_redeemed_game_credits,
)
from backend.services.game_notification_service import (
    create_or_reopen_booking_refunded_notification,
)
from backend.services.game_rules import (
    ACTIVE_JOIN_STATUSES,
    OPEN_GAME_STATUSES,
    build_game_conflict_detail,
)
from backend.services.game_waitlist_service import promote_waitlist_entries
from backend.services.official_game_notification_service import (
    create_official_game_player_removed_notification,
)
from backend.services.official_game_roster_service import (
    ADMIN_REMOVABLE_PLAYER_STATUSES,
    IMMEDIATE_REMOVAL_PAYMENT_STATUSES,
    cancel_pending_booking_payments_for_admin_removal,
    mark_admin_removed_participant,
)
from backend.services.official_game_service import (
    clean_required_text,
    get_official_game_or_404,
)
from backend.services.payment_rules import (
    COLLECTED_PAYMENT_STATUSES,
    SUCCEEDED_PAYMENT_STATUSES,
)
from backend.services.status_history_service import (
    add_booking_status_history_if_changed,
)
from backend.services.stripe_service import (
    StripeConfigError,
    create_refund as create_stripe_refund,
)
from backend.services.support_flag_service import (
    create_support_flag,
    stage_support_flag,
)

REMOVAL_PREVIEW_ACTIVE_REFUND_STATUSES = {
    "pending",
    "approved",
    "processing",
}
REMOVAL_PREVIEW_REFUND_HOLD_STATUSES = {
    *REMOVAL_PREVIEW_ACTIVE_REFUND_STATUSES,
    "succeeded",
}
REMOVAL_PREVIEW_ACTIVE_WAITLIST_STATUSES = {"active", "payment_processing"}
REMOVAL_EXECUTION_OUTCOMES = {
    "remove_only",
    "release_pending_hold_and_remove_party",
    "refund_cash_and_remove_party",
    "restore_credit_and_remove_party",
    "refund_cash_restore_credit_and_remove_party",
}


def list_booking_participants_for_removal_preview(
    db: Session,
    *,
    game_id: uuid.UUID,
    booking_id: uuid.UUID,
    for_update: bool = False,
) -> list[GameParticipant]:
    statement = (
        select(GameParticipant)
        .where(
            GameParticipant.game_id == game_id,
            GameParticipant.booking_id == booking_id,
            GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
        )
        .order_by(
            GameParticipant.participant_type.asc(),
            GameParticipant.roster_order.asc().nulls_last(),
            GameParticipant.created_at.asc(),
        )
    )
    if for_update:
        statement = statement.with_for_update()

    return list(
        db.scalars(statement).all()
    )


def build_removal_preview_participant(
    participant: GameParticipant,
    *,
    selected_participant_id: uuid.UUID,
) -> AdminOfficialGameRemovalParticipantRead:
    return AdminOfficialGameRemovalParticipantRead(
        id=participant.id,
        display_name=participant.display_name_snapshot,
        participant_type=participant.participant_type,
        participant_status=participant.participant_status,
        price_cents=participant.price_cents,
        is_selected=participant.id == selected_participant_id,
    )


def removal_preview_snapshot_token(
    *,
    game: Game,
    participant: GameParticipant,
    affected_participants: list[GameParticipant],
    booking: Booking | None,
    payments: list[Payment],
    refunds: list[Refund],
    credit_usages: list[GameCreditUsage],
    active_waitlist_entries: list[WaitlistEntry],
) -> str:
    snapshot = {
        "game": {
            "id": str(game.id),
            "publish_status": game.publish_status,
            "game_status": game.game_status,
            "total_spots": game.total_spots,
            "waitlist_enabled": game.waitlist_enabled,
            "host_user_id": str(game.host_user_id) if game.host_user_id else None,
            "updated_at": game.updated_at.isoformat(),
        },
        "selected_participant": {
            "id": str(participant.id),
            "booking_id": (
                str(participant.booking_id) if participant.booking_id else None
            ),
            "participant_type": participant.participant_type,
            "participant_status": participant.participant_status,
            "price_cents": participant.price_cents,
            "updated_at": participant.updated_at.isoformat(),
        },
        "affected_participants": [
            {
                "id": str(item.id),
                "participant_type": item.participant_type,
                "participant_status": item.participant_status,
                "price_cents": item.price_cents,
                "updated_at": item.updated_at.isoformat(),
            }
            for item in affected_participants
        ],
        "booking": (
            {
                "id": str(booking.id),
                "booking_status": booking.booking_status,
                "payment_status": booking.payment_status,
                "participant_count": booking.participant_count,
                "subtotal_cents": booking.subtotal_cents,
                "platform_fee_cents": booking.platform_fee_cents,
                "discount_cents": booking.discount_cents,
                "total_cents": booking.total_cents,
                "updated_at": booking.updated_at.isoformat(),
            }
            if booking is not None
            else None
        ),
        "payments": [
            {
                "id": str(payment.id),
                "payment_status": payment.payment_status,
                "amount_cents": payment.amount_cents,
                "provider_charge_id": payment.provider_charge_id,
                "updated_at": payment.updated_at.isoformat(),
            }
            for payment in payments
        ],
        "refunds": [
            {
                "id": str(refund.id),
                "payment_id": str(refund.payment_id),
                "refund_status": refund.refund_status,
                "amount_cents": refund.amount_cents,
                "updated_at": refund.updated_at.isoformat(),
            }
            for refund in refunds
        ],
        "credit_usages": [
            {
                "id": str(usage.id),
                "usage_type": usage.usage_type,
                "usage_status": usage.usage_status,
                "amount_cents": usage.amount_cents,
                "updated_at": usage.updated_at.isoformat(),
            }
            for usage in credit_usages
        ],
        "waitlist_entries": [
            {
                "id": str(entry.id),
                "waitlist_status": entry.waitlist_status,
                "party_size": entry.party_size,
                "position": entry.position,
                "updated_at": entry.updated_at.isoformat(),
            }
            for entry in active_waitlist_entries
        ],
    }
    encoded_snapshot = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded_snapshot).hexdigest()


def preview_official_game_player_removal(
    db: Session,
    *,
    game_id: uuid.UUID,
    participant_id: uuid.UUID,
    for_update: bool = False,
) -> AdminOfficialGamePlayerRemovalPreviewRead:
    game = get_official_game_or_404(db, game_id, for_update=for_update)
    participant_statement = select(GameParticipant).where(
        GameParticipant.id == participant_id
    )
    if for_update:
        participant_statement = participant_statement.with_for_update()
    participant = db.scalar(participant_statement)
    if participant is None or participant.game_id != game.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Official game participant not found.",
        )

    booking = None
    if participant.booking_id:
        booking_statement = select(Booking).where(Booking.id == participant.booking_id)
        if for_update:
            booking_statement = booking_statement.with_for_update()
        booking = db.scalar(booking_statement)
    affected_participants = [participant]
    removal_scope = "single_participant"
    if booking is not None and (
        participant.participant_type != "guest"
        or booking.booking_status == "pending_payment"
    ):
        affected_participants = list_booking_participants_for_removal_preview(
            db,
            game_id=game.id,
            booking_id=booking.id,
            for_update=for_update,
        )
        removal_scope = "booking_party"

    if not affected_participants:
        affected_participants = [participant]

    payment_statement = None
    if booking is not None:
        payment_statement = (
            select(Payment)
            .where(Payment.booking_id == booking.id)
            .order_by(Payment.created_at.asc(), Payment.id.asc())
        )
        if for_update:
            payment_statement = payment_statement.with_for_update()
    payments = (
        list(db.scalars(payment_statement).all())
        if payment_statement is not None
        else []
    )
    payment_ids = [payment.id for payment in payments]
    participant_ids = [item.id for item in affected_participants]
    refund_conditions = []
    if booking is not None:
        refund_conditions.append(Refund.booking_id == booking.id)
    if payment_ids:
        refund_conditions.append(Refund.payment_id.in_(payment_ids))
    if participant_ids:
        refund_conditions.append(Refund.participant_id.in_(participant_ids))
    refund_statement = None
    if refund_conditions:
        refund_statement = (
            select(Refund)
            .where(or_(*refund_conditions))
            .order_by(Refund.created_at.asc(), Refund.id.asc())
        )
        if for_update:
            refund_statement = refund_statement.with_for_update()
    refunds = (
        list(db.scalars(refund_statement).all())
        if refund_statement is not None
        else []
    )
    credit_usage_statement = None
    if booking is not None:
        credit_usage_statement = (
            select(GameCreditUsage)
            .where(GameCreditUsage.booking_id == booking.id)
            .order_by(GameCreditUsage.created_at.asc(), GameCreditUsage.id.asc())
        )
        if for_update:
            credit_usage_statement = credit_usage_statement.with_for_update()
    credit_usages = (
        list(db.scalars(credit_usage_statement).all())
        if credit_usage_statement is not None
        else []
    )

    refund_holds_by_payment_id: dict[uuid.UUID, int] = {}
    for refund in refunds:
        if refund.refund_status in REMOVAL_PREVIEW_REFUND_HOLD_STATUSES:
            refund_holds_by_payment_id[refund.payment_id] = (
                refund_holds_by_payment_id.get(refund.payment_id, 0)
                + refund.amount_cents
            )

    cash_collected_cents = sum(
        payment.amount_cents
        for payment in payments
        if payment.payment_status in COLLECTED_PAYMENT_STATUSES
    )
    cash_refunded_cents = sum(
        refund.amount_cents
        for refund in refunds
        if refund.refund_status == "succeeded"
    )
    cash_refund_pending_cents = sum(
        refund.amount_cents
        for refund in refunds
        if refund.refund_status in REMOVAL_PREVIEW_ACTIVE_REFUND_STATUSES
    )
    cash_refundable_cents = sum(
        max(
            payment.amount_cents
            - refund_holds_by_payment_id.get(payment.id, 0),
            0,
        )
        for payment in payments
        if payment.payment_status in SUCCEEDED_PAYMENT_STATUSES
    )

    credit_totals = {
        usage_status: sum(
            usage.amount_cents
            for usage in credit_usages
            if usage.usage_status == usage_status
        )
        for usage_status in {
            "reserved",
            "redeemed",
            "released",
            "restored",
            "reversed",
        }
    }
    credit_restorable_cents = max(
        credit_totals["redeemed"] - credit_totals["restored"],
        0,
    )

    affected_capacity_count = sum(
        item.participant_status in ADMIN_REMOVABLE_PLAYER_STATUSES
        for item in affected_participants
    )
    active_roster_count = int(
        db.scalar(
            select(func.count(GameParticipant.id)).where(
                GameParticipant.game_id == game.id,
                GameParticipant.participant_status.in_(
                    ADMIN_REMOVABLE_PLAYER_STATUSES
                ),
            )
        )
        or 0
    )
    available_spots_after_removal = max(
        game.total_spots - (active_roster_count - affected_capacity_count),
        0,
    )
    waitlist_statement = (
        select(WaitlistEntry)
        .where(
            WaitlistEntry.game_id == game.id,
            WaitlistEntry.waitlist_status.in_(
                REMOVAL_PREVIEW_ACTIVE_WAITLIST_STATUSES
            ),
        )
        .order_by(WaitlistEntry.position.asc(), WaitlistEntry.created_at.asc())
    )
    if for_update:
        waitlist_statement = waitlist_statement.with_for_update()
    active_waitlist_entries = list(db.scalars(waitlist_statement).all())
    next_active_waitlist_entry = next(
        (
            entry
            for entry in active_waitlist_entries
            if entry.waitlist_status == "active"
        ),
        None,
    )

    classification = "remove_only"
    automatic_outcome_available = True
    blocking_reasons: list[str] = []
    allowed_outcomes = ["remove_only"]
    required_permissions: list[str] = []

    if (
        game.publish_status != "published"
        or game.game_status not in OPEN_GAME_STATUSES
    ):
        classification = "blocked_game_state"
        blocking_reasons.append(
            "Players can only be removed from published active official games."
        )
    elif participant.participant_status not in ADMIN_REMOVABLE_PLAYER_STATUSES:
        classification = "blocked_participant_status"
        blocking_reasons.append(
            "Only pending or confirmed roster participants can be removed here."
        )
    elif (
        participant.participant_type == "host"
        or (
            participant.user_id is not None
            and participant.user_id == game.host_user_id
        )
    ):
        classification = "blocked_host"
        blocking_reasons.append(
            "Remove the host designation before removing this player."
        )
    elif booking is None:
        classification = "blocked_missing_booking"
        blocking_reasons.append(
            "This roster row has no booking record, so its money impact cannot be verified."
        )
    elif any(payment.payment_status == "processing" for payment in payments):
        classification = "payment_processing"
        blocking_reasons.append(
            "A payment is processing. Wait for a final payment state before removal."
        )
    elif booking.payment_status == "processing" and not payments:
        classification = "manual_review_required"
        blocking_reasons.append(
            "The booking is processing but has no payment record to verify."
        )
    elif any(
        refund.refund_status in REMOVAL_PREVIEW_ACTIVE_REFUND_STATUSES
        for refund in refunds
    ):
        classification = "refund_in_progress"
        blocking_reasons.append(
            "A refund is already pending or processing for this booking."
        )
    elif any(payment.payment_status == "disputed" for payment in payments):
        classification = "manual_review_required"
        blocking_reasons.append(
            "This booking has a disputed payment and requires money support review."
        )
    elif any(
        payment.payment_status in {"partially_refunded", "refunded"}
        for payment in payments
    ):
        classification = "manual_review_required"
        blocking_reasons.append(
            "This booking already has a refunded payment state and requires money support review."
        )
    elif (
        removal_scope == "single_participant"
        and (
            cash_collected_cents > 0
            or credit_totals["redeemed"] > 0
            or bool(refunds)
        )
    ):
        classification = "manual_review_required"
        blocking_reasons.append(
            "Payment and credit are stored for the whole booking, so one paid "
            "guest cannot be allocated automatically."
        )
    elif refunds:
        classification = "manual_review_required"
        blocking_reasons.append(
            "Existing refund history requires money support review before another removal outcome."
        )
    elif credit_totals["restored"] > 0 or credit_totals["reversed"] > 0:
        classification = "manual_review_required"
        blocking_reasons.append(
            "Existing restored or reversed credit requires money support review."
        )
    elif (
        credit_totals["reserved"] > 0
        and booking.booking_status != "pending_payment"
    ):
        classification = "manual_review_required"
        blocking_reasons.append(
            "Reserved credit exists outside a pending checkout and requires money support review."
        )
    elif (
        booking.booking_status == "pending_payment"
        and cash_collected_cents == 0
        and credit_totals["redeemed"] == 0
        and all(
            payment.payment_status in IMMEDIATE_REMOVAL_PAYMENT_STATUSES
            for payment in payments
        )
    ):
        classification = "release_pending_hold"
        allowed_outcomes = ["release_pending_hold_and_remove_party"]
    elif cash_refundable_cents > 0 and credit_restorable_cents > 0:
        classification = "refund_cash_and_restore_credit"
        allowed_outcomes = ["refund_cash_restore_credit_and_remove_party"]
        required_permissions = [
            PERMISSION_MONEY_REFUND,
            PERMISSION_MONEY_CREDIT_MANAGE,
        ]
    elif cash_refundable_cents > 0:
        classification = "refund_cash"
        allowed_outcomes = ["refund_cash_and_remove_party"]
        required_permissions = [PERMISSION_MONEY_REFUND]
    elif credit_restorable_cents > 0:
        classification = "restore_credit"
        allowed_outcomes = ["restore_credit_and_remove_party"]
        required_permissions = [PERMISSION_MONEY_CREDIT_MANAGE]
    elif (
        booking.payment_status
        in {"paid", "partially_refunded", "refunded", "credit_restored", "disputed"}
        or cash_collected_cents > 0
        or credit_totals["redeemed"] > 0
    ):
        classification = "manual_review_required"
        blocking_reasons.append(
            "The settled booking state does not have a safe automatic refund or credit outcome."
        )

    if blocking_reasons:
        automatic_outcome_available = False
        allowed_outcomes = []
        required_permissions = []

    next_waitlist_party_size = (
        next_active_waitlist_entry.party_size
        if next_active_waitlist_entry is not None
        else None
    )
    preview_token = removal_preview_snapshot_token(
        game=game,
        participant=participant,
        affected_participants=affected_participants,
        booking=booking,
        payments=payments,
        refunds=refunds,
        credit_usages=credit_usages,
        active_waitlist_entries=active_waitlist_entries,
    )
    return AdminOfficialGamePlayerRemovalPreviewRead(
        game_id=game.id,
        selected_participant_id=participant.id,
        selected_participant_name=participant.display_name_snapshot,
        booking_id=booking.id if booking is not None else None,
        buyer_user_id=booking.buyer_user_id if booking is not None else None,
        removal_scope=removal_scope,
        classification=classification,
        automatic_outcome_available=automatic_outcome_available,
        preview_token=preview_token,
        blocking_reasons=blocking_reasons,
        allowed_outcomes=allowed_outcomes,
        required_permissions=required_permissions,
        affected_participants=[
            build_removal_preview_participant(
                item,
                selected_participant_id=participant.id,
            )
            for item in affected_participants
        ],
        booking_status=booking.booking_status if booking is not None else None,
        booking_payment_status=booking.payment_status if booking is not None else None,
        booking_total_cents=booking.total_cents if booking is not None else 0,
        currency=booking.currency if booking is not None else participant.currency,
        payment_statuses=sorted(
            {payment.payment_status for payment in payments}
        ),
        refund_statuses=sorted({refund.refund_status for refund in refunds}),
        cash_collected_cents=cash_collected_cents,
        cash_refunded_cents=cash_refunded_cents,
        cash_refund_pending_cents=cash_refund_pending_cents,
        cash_refundable_cents=cash_refundable_cents,
        credit_reserved_cents=credit_totals["reserved"],
        credit_redeemed_cents=credit_totals["redeemed"],
        credit_released_cents=credit_totals["released"],
        credit_restored_cents=credit_totals["restored"],
        credit_reversed_cents=credit_totals["reversed"],
        credit_restorable_cents=credit_restorable_cents,
        spots_opened=affected_capacity_count,
        available_spots_after_removal=available_spots_after_removal,
        active_waitlist_entry_count=len(active_waitlist_entries),
        active_waitlist_player_count=sum(
            entry.party_size for entry in active_waitlist_entries
        ),
        next_waitlist_party_size=next_waitlist_party_size,
        waitlist_promotion_possible=bool(
            game.waitlist_enabled
            and next_waitlist_party_size is not None
            and next_waitlist_party_size <= available_spots_after_removal
        ),
    )


def map_admin_removal_refund_status(provider_status: str) -> str:
    normalized_status = provider_status.strip().lower()
    if normalized_status == "succeeded":
        return "succeeded"
    if normalized_status == "failed":
        return "failed"
    if normalized_status in {"canceled", "cancelled"}:
        return "cancelled"
    return "processing"


def create_admin_removal_refund_record(
    db: Session,
    *,
    admin_user: User,
    booking: Booking,
    payment: Payment,
    now: datetime,
    provider_refund_id: str | None,
    refund_status: str,
) -> Refund:
    refund = Refund(
        id=uuid.uuid4(),
        payment_id=payment.id,
        booking_id=booking.id,
        participant_id=None,
        provider_refund_id=provider_refund_id,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        refund_reason="admin_refund",
        refund_status=refund_status,
        requested_by_user_id=admin_user.id,
        approved_by_user_id=admin_user.id,
        requested_at=now,
        approved_at=(
            now
            if refund_status in {"approved", "processing", "succeeded"}
            else None
        ),
        refunded_at=now if refund_status == "succeeded" else None,
        created_at=now,
        updated_at=now,
    )
    db.add(refund)
    return refund


def execute_admin_removal_refunds(
    db: Session,
    *,
    admin_user: User,
    game: Game,
    booking: Booking,
    payments: list[Payment],
    now: datetime,
) -> tuple[list[Refund], list[dict[str, Any]]]:
    refunds: list[Refund] = []
    support_flags: list[dict[str, Any]] = []

    for payment in payments:
        if payment.payment_status != "succeeded":
            continue

        if not payment.provider_charge_id:
            refund = create_admin_removal_refund_record(
                db,
                admin_user=admin_user,
                booking=booking,
                payment=payment,
                now=now,
                provider_refund_id=None,
                refund_status="failed",
            )
            refunds.append(refund)
            support_flags.append(
                {
                    "flag_type": "missing_stripe_charge_id",
                    "title": "Removal refund is missing a Stripe charge",
                    "summary": (
                        "A paid official-game booking was removed, but its "
                        "payment has no Stripe charge id for refund."
                    ),
                    "target_payment_id": payment.id,
                    "target_refund_id": refund.id,
                }
            )
            continue

        try:
            provider_refund = create_stripe_refund(
                charge_id=payment.provider_charge_id,
                amount_cents=payment.amount_cents,
                currency=payment.currency,
                idempotency_key=(
                    f"admin_remove:{game.id}:booking:{booking.id}:"
                    f"payment:{payment.id}:refund"
                ),
                metadata={
                    "source": "admin_official_player_removal",
                    "game_id": str(game.id),
                    "booking_id": str(booking.id),
                    "payment_id": str(payment.id),
                    "admin_user_id": str(admin_user.id),
                },
            )
            refund_status = map_admin_removal_refund_status(
                provider_refund.status
            )
            refund = create_admin_removal_refund_record(
                db,
                admin_user=admin_user,
                booking=booking,
                payment=payment,
                now=now,
                provider_refund_id=provider_refund.id,
                refund_status=refund_status,
            )
        except StripeConfigError:
            refund = create_admin_removal_refund_record(
                db,
                admin_user=admin_user,
                booking=booking,
                payment=payment,
                now=now,
                provider_refund_id=None,
                refund_status="failed",
            )
            refund_status = "failed"
        except Exception:
            refund = create_admin_removal_refund_record(
                db,
                admin_user=admin_user,
                booking=booking,
                payment=payment,
                now=now,
                provider_refund_id=None,
                refund_status="failed",
            )
            refund_status = "failed"

        refunds.append(refund)
        if refund_status == "succeeded":
            payment.payment_status = "refunded"
            payment.updated_at = now
            db.add(payment)
        elif refund_status == "processing":
            support_flags.append(
                {
                    "flag_type": "refund_follow_up_required",
                    "title": "Removal refund needs follow-up",
                    "summary": (
                        "A paid official-game player was removed while the "
                        "Stripe refund remained processing."
                    ),
                    "target_payment_id": payment.id,
                    "target_refund_id": refund.id,
                }
            )
        else:
            support_flags.append(
                {
                    "flag_type": "stripe_refund_failed",
                    "title": "Removal refund failed",
                    "summary": (
                        "A paid official-game player was removed, but the "
                        "Stripe refund did not complete."
                    ),
                    "target_payment_id": payment.id,
                    "target_refund_id": refund.id,
                }
            )

    return refunds, support_flags


def record_credit_return_failure(
    db: Session,
    *,
    admin_user: User,
    game_id: uuid.UUID,
    booking_id: uuid.UUID,
    detail: str,
    operation: str = "restore",
) -> None:
    is_release = operation == "release"
    create_support_flag(
        db,
        flag_type="credit_release_failed" if is_release else "credit_restore_failed",
        source="official_game",
        title=(
            "Player-removal credit release failed"
            if is_release
            else "Player-removal credit restore failed"
        ),
        summary=(
            "Pickup Lane could not release reserved credit before removing an "
            "official-game booking."
            if is_release
            else (
                "Pickup Lane could not restore redeemed credit before removing "
                "an official-game booking."
            )
        ),
        metadata={
            "operation": "admin_official_player_removal",
            "credit_operation": operation,
            "detail": detail,
        },
        idempotency_key=(
            f"admin_remove:{booking_id}:credit_{operation}_failed"
        ),
        created_by_user_id=admin_user.id,
        reopen_resolved=True,
        target_user_id=None,
        target_game_id=game_id,
        target_booking_id=booking_id,
        target_payment_id=None,
        target_refund_id=None,
        target_game_credit_id=None,
        target_venue_id=None,
        target_venue_image_id=None,
        target_notification_id=None,
    )


def execute_official_game_player_removal(
    db: Session,
    *,
    admin_user: User,
    game_id: uuid.UUID,
    participant_id: uuid.UUID,
    execute_request: AdminOfficialGamePlayerRemovalExecute,
) -> AdminOfficialGamePlayerRemovalResultRead:
    reason = clean_required_text(execute_request.reason, "reason")
    if len(reason) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason must be 1000 characters or fewer.",
        )

    preview = preview_official_game_player_removal(
        db,
        game_id=game_id,
        participant_id=participant_id,
        for_update=True,
    )
    expected_outcome = (
        preview.allowed_outcomes[0] if len(preview.allowed_outcomes) == 1 else None
    )
    if (
        execute_request.preview_token != preview.preview_token
        or execute_request.outcome != expected_outcome
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Removal impact changed. Review the latest preview before confirming.",
        )

    if (
        execute_request.outcome not in REMOVAL_EXECUTION_OUTCOMES
        or not preview.automatic_outcome_available
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This removal outcome cannot be executed automatically.",
        )

    for permission in preview.required_permissions:
        require_user_admin_permission(admin_user, permission)

    if preview.booking_id is None or preview.removal_scope != "booking_party":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paid removal execution requires an unambiguous booking party.",
        )

    game = db.get(Game, game_id)
    booking = db.get(Booking, preview.booking_id)
    participant = db.get(GameParticipant, participant_id)
    if game is None or booking is None or participant is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Removal records changed. Review the latest preview.",
        )

    participants_to_remove = list_booking_participants_for_removal_preview(
        db,
        game_id=game.id,
        booking_id=booking.id,
        for_update=True,
    )
    payments = list(
        db.scalars(
            select(Payment)
            .where(Payment.booking_id == booking.id)
            .order_by(Payment.created_at.asc(), Payment.id.asc())
            .with_for_update()
        ).all()
    )
    now = datetime.now(timezone.utc)
    old_booking_status = booking.booking_status
    old_payment_status = booking.payment_status
    original_participant_status = participant.participant_status

    restored_credit_usages: list[GameCreditUsage] = []
    if execute_request.outcome in {
        "restore_credit_and_remove_party",
        "refund_cash_restore_credit_and_remove_party",
    }:
        try:
            restored_credit_usages = restore_redeemed_game_credits(
                db,
                booking.id,
                now=now,
                restore_reason="admin_player_removed",
                user_id=booking.buyer_user_id,
            )
        except GameCreditLedgerError as exc:
            db.rollback()
            record_credit_return_failure(
                db,
                admin_user=admin_user,
                game_id=game_id,
                booking_id=preview.booking_id,
                detail=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Game credit could not be restored. No player was removed; "
                    "support follow-up was created."
                ),
            ) from exc

    refunds: list[Refund] = []
    support_flag_specs: list[dict[str, Any]] = []
    if execute_request.outcome in {
        "refund_cash_and_remove_party",
        "refund_cash_restore_credit_and_remove_party",
    }:
        refunds, support_flag_specs = execute_admin_removal_refunds(
            db,
            admin_user=admin_user,
            game=game,
            booking=booking,
            payments=payments,
            now=now,
        )

    if execute_request.outcome == "release_pending_hold_and_remove_party":
        try:
            cancel_pending_booking_payments_for_admin_removal(
                db,
                booking=booking,
                reason=reason,
                now=now,
            )
        except GameCreditLedgerError as exc:
            db.rollback()
            record_credit_return_failure(
                db,
                admin_user=admin_user,
                game_id=game_id,
                booking_id=preview.booking_id,
                detail=str(exc),
                operation="release",
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Reserved game credit could not be released. No player was "
                    "removed; support follow-up was created."
                ),
            ) from exc

    for participant_to_remove in participants_to_remove:
        mark_admin_removed_participant(
            db,
            participant=participant_to_remove,
            admin_user_id=admin_user.id,
            reason=reason,
            now=now,
        )

    refund_statuses = {refund.refund_status for refund in refunds}
    successful_refunds = [
        refund for refund in refunds if refund.refund_status == "succeeded"
    ]
    credit_restored_cents = sum(
        usage.amount_cents for usage in restored_credit_usages
    )
    booking.booking_status = "cancelled"
    if execute_request.outcome == "release_pending_hold_and_remove_party":
        booking.payment_status = "failed"
    elif refunds and refund_statuses == {"succeeded"}:
        booking.payment_status = "refunded"
    elif credit_restored_cents > 0 and not refunds:
        booking.payment_status = "credit_restored"
    booking.cancelled_at = booking.cancelled_at or now
    booking.cancelled_by_user_id = admin_user.id
    booking.cancel_reason = reason
    booking.updated_at = now
    db.add(booking)
    add_booking_status_history_if_changed(
        db,
        booking,
        old_booking_status=old_booking_status,
        old_payment_status=old_payment_status,
        changed_by_user_id=admin_user.id,
        change_source="admin",
        reason=reason,
    )
    game.updated_at = now
    db.add(game)

    db.flush()
    waitlist_candidates = list(
        db.scalars(
            select(WaitlistEntry)
            .where(
                WaitlistEntry.game_id == game.id,
                WaitlistEntry.waitlist_status == "active",
            )
            .order_by(WaitlistEntry.position.asc(), WaitlistEntry.id.asc())
        ).all()
    )
    waitlist_status_before = {
        entry.id: entry.waitlist_status for entry in waitlist_candidates
    }
    promote_waitlist_entries(db, game, now)
    db.flush()
    waitlist_advanced_entry_ids = [
        entry.id
        for entry in waitlist_candidates
        if waitlist_status_before[entry.id] == "active"
        and entry.waitlist_status in {"accepted", "payment_processing"}
    ]

    refund_follow_up_required = any(
        refund.refund_status != "succeeded" for refund in refunds
    )
    audit_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="admin_remove_player",
        target_game_id=game.id,
        target_user_id=participant.user_id,
        target_booking_id=booking.id,
        target_participant_id=participant.id,
        target_payment_id=payments[0].id if payments else None,
        target_refund_id=refunds[0].id if refunds else None,
        reason=reason,
        metadata={
            "removed_participant_ids": [
                item.id for item in participants_to_remove
            ],
            "removed_count": len(participants_to_remove),
            "payment_refund_created": bool(refunds),
            "removal_outcome": execute_request.outcome,
            "refund_created_count": len(refunds),
            "refund_failed_count": sum(
                refund.refund_status in {"failed", "cancelled"}
                for refund in refunds
            ),
            "refund_processing_count": sum(
                refund.refund_status == "processing" for refund in refunds
            ),
            "refund_follow_up_required": refund_follow_up_required,
            "credit_restored_count": len(restored_credit_usages),
            "credit_restored_cents": credit_restored_cents,
            "waitlist_advanced_entry_ids": waitlist_advanced_entry_ids,
        },
    )

    support_flags = []
    for flag_spec in support_flag_specs:
        support_flags.append(
            stage_support_flag(
                db,
                flag_type=flag_spec["flag_type"],
                source="official_game",
                title=flag_spec["title"],
                summary=flag_spec["summary"],
                metadata={
                    "operation": "admin_official_player_removal",
                    "outcome": execute_request.outcome,
                },
                idempotency_key=(
                    f"admin_remove:{booking.id}:{flag_spec['target_payment_id']}:"
                    f"{flag_spec['flag_type']}"
                ),
                source_admin_action_id=audit_action.id,
                created_by_user_id=admin_user.id,
                reopen_resolved=True,
                target_user_id=booking.buyer_user_id,
                target_game_id=game.id,
                target_booking_id=booking.id,
                target_payment_id=flag_spec["target_payment_id"],
                target_refund_id=flag_spec["target_refund_id"],
                target_game_credit_id=None,
                target_venue_id=None,
                target_venue_image_id=None,
                target_notification_id=None,
            )
        )

    create_official_game_player_removed_notification(
        db,
        game=game,
        participant=participant,
        booking=booking,
        admin_user=admin_user,
        original_participant_status=original_participant_status,
        original_booking_status=old_booking_status,
        now=now,
    )
    for refund in successful_refunds:
        payment = next(
            item for item in payments if item.id == refund.payment_id
        )
        create_or_reopen_booking_refunded_notification(
            db,
            db_game=game,
            booking=booking,
            payment=payment,
            refund=refund,
            now=now,
            stripe_refund_processed=True,
            credit_restored=credit_restored_cents > 0,
            game_cancelled=False,
            force_action_null=False,
        )
    if credit_restored_cents > 0 and not successful_refunds:
        create_or_reopen_booking_refunded_notification(
            db,
            db_game=game,
            booking=booking,
            now=now,
            stripe_refund_processed=False,
            credit_restored=True,
            game_cancelled=False,
            force_action_null=False,
        )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return AdminOfficialGamePlayerRemovalResultRead(
        game_id=game.id,
        selected_participant_id=participant.id,
        booking_id=booking.id,
        outcome=execute_request.outcome,
        removed_participant_ids=[item.id for item in participants_to_remove],
        booking_status=booking.booking_status,
        booking_payment_status=booking.payment_status,
        refunds=[
            AdminOfficialGameRemovalRefundRead(
                id=refund.id,
                payment_id=refund.payment_id,
                amount_cents=refund.amount_cents,
                currency=refund.currency,
                refund_status=refund.refund_status,
            )
            for refund in refunds
        ],
        credit_restored_count=len(restored_credit_usages),
        credit_restored_cents=credit_restored_cents,
        refund_follow_up_required=refund_follow_up_required,
        support_flag_ids=[flag.id for flag in support_flags],
        waitlist_advanced_entry_ids=waitlist_advanced_entry_ids,
    )
