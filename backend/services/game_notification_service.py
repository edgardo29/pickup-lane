"""Game notification helpers for game updates, refunds, and waitlist events."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameParticipant,
    Notification,
    Payment,
    Refund,
    WaitlistEntry,
)
from backend.services.game_rules import (
    GAME_STATUSES_WITH_DISABLED_INBOX_ACTIONS,
    GAME_UPDATED_GAME_STATUSES,
    GAME_UPDATED_PARTICIPANT_STATUSES,
    GAME_UPDATED_PARTICIPANT_TYPES,
    GAME_UPDATED_STRUCTURAL_FIELDS,
    ensure_timezone,
    game_requires_app_player_payment,
)
from backend.services.notification_event_service import (
    build_game_notification_fields,
    reopen_aggregated_notification,
)


def booking_refunded_aggregation_key(game_id: uuid.UUID, booking_id: uuid.UUID) -> str:
    return f"game:{game_id}:booking:{booking_id}:booking_refunded"


def booking_refunded_copy(
    *,
    stripe_refund_processed: bool,
    credit_restored: bool,
    game_cancelled: bool = True,
) -> dict[str, str]:
    if stripe_refund_processed and credit_restored:
        return {
            "title": "Refund and credit processed",
            "summary": "Your refund was processed and your game credit was restored.",
            "body": (
                "Your Stripe refund was processed and your Pickup Lane game credit "
                "was restored "
                + (
                    "for this canceled official game."
                    if game_cancelled
                    else "after your booking was removed from this official game."
                )
            ),
        }

    if credit_restored:
        return {
            "title": "Credit restored",
            "summary": "Your Pickup Lane game credit was restored.",
            "body": (
                "Your Pickup Lane game credit was restored "
                + (
                    "for this canceled official game."
                    if game_cancelled
                    else "after your booking was removed from this official game."
                )
            ),
        }

    return {
        "title": "Refund processed",
        "summary": "Your refund was processed.",
        "body": "Your refund for this official game was processed.",
    }


def game_allows_inbox_action(db_game: Game) -> bool:
    return (
        db_game.deleted_at is None
        and db_game.publish_status == "published"
        and db_game.game_status not in GAME_STATUSES_WITH_DISABLED_INBOX_ACTIONS
    )


def create_or_reopen_booking_refunded_notification(
    db: Session,
    *,
    db_game: Game,
    booking: Booking,
    now: datetime,
    payment: Payment | None = None,
    refund: Refund | None = None,
    stripe_refund_processed: bool,
    credit_restored: bool,
    game_cancelled: bool = True,
    force_action_null: bool = True,
) -> None:
    aggregation_key = booking_refunded_aggregation_key(db_game.id, booking.id)
    copy = booking_refunded_copy(
        stripe_refund_processed=stripe_refund_processed,
        credit_restored=credit_restored,
        game_cancelled=game_cancelled,
    )
    reopen_aggregated_notification(
        db,
        user_id=booking.buyer_user_id,
        notification_type="booking_refunded",
        notification_category="game_activity",
        notification_domain="game",
        aggregation_key=aggregation_key,
        values={
            **build_game_notification_fields(
                db_game,
                "booking_refunded",
                event_at=now,
                force_action_null=force_action_null,
                aggregation_key=aggregation_key,
                **copy,
            ),
            "actor_user_id": None,
            "related_game_id": db_game.id,
            "related_booking_id": booking.id,
            "related_payment_id": payment.id if payment is not None else None,
            "related_refund_id": refund.id if refund is not None else None,
            "related_participant_id": None,
        },
        aggregate_count_mode="clear",
    )


def create_waitlist_promotion_notification(
    db: Session,
    db_game: Game,
    waitlist_entry: WaitlistEntry,
    participant: GameParticipant,
    now: datetime,
    payment: Payment | None = None,
) -> None:
    if game_requires_app_player_payment(db_game):
        body = "Enough spots opened. You were charged and moved to the player list."
    else:
        body = "Enough spots opened. You were moved to the player list."

    db.add(
        Notification(
            id=uuid.uuid4(),
            user_id=waitlist_entry.user_id,
            notification_type="waitlist_promoted",
            notification_category="game_activity",
            notification_domain="game",
            **build_game_notification_fields(
                db_game,
                "waitlist_promoted",
                event_at=now,
                body=body,
            ),
            related_game_id=db_game.id,
            related_booking_id=participant.booking_id,
            related_participant_id=participant.id,
            related_payment_id=payment.id if payment is not None else None,
            is_read=False,
        )
    )


WAITLIST_PAYMENT_FAILED_BODY = (
    "A spot opened, but your payment did not go through, so you were removed "
    "from the waitlist. Update your payment method and try joining again if a "
    "spot is still available."
)


def create_waitlist_payment_failed_notification(
    db: Session,
    db_game: Game,
    booking: Booking,
    payment: Payment | None,
    now: datetime,
) -> None:
    db.add(
        Notification(
            id=uuid.uuid4(),
            user_id=booking.buyer_user_id,
            notification_type="payment_failed",
            notification_category="game_activity",
            notification_domain="game",
            **build_game_notification_fields(
                db_game,
                "payment_failed",
                event_at=now,
                summary="Your waitlist payment did not go through.",
                body=WAITLIST_PAYMENT_FAILED_BODY,
            ),
            related_game_id=db_game.id,
            related_booking_id=booking.id,
            related_payment_id=payment.id if payment is not None else None,
            is_read=False,
            read_at=None,
            created_at=now,
            updated_at=now,
        )
    )


def game_updated_aggregation_key(
    game_id: uuid.UUID,
    recipient_user_id: uuid.UUID,
) -> str:
    return f"game:{game_id}:user:{recipient_user_id}:game_updated"


def capture_game_updated_structural_snapshot(db_game: Game) -> dict[str, object]:
    snapshot = {
        field_name: getattr(db_game, field_name)
        for field_name in GAME_UPDATED_STRUCTURAL_FIELDS
    }

    for field_name in ("starts_at", "ends_at"):
        value = snapshot[field_name]
        if isinstance(value, datetime):
            snapshot[field_name] = ensure_timezone(value)

    return snapshot


def game_updated_structural_snapshot_changed(
    before: dict[str, object],
    db_game: Game,
) -> bool:
    after = capture_game_updated_structural_snapshot(db_game)
    return any(before[field_name] != after[field_name] for field_name in before)


def list_game_updated_recipient_user_ids(
    db: Session,
    db_game: Game,
    actor_user_id: uuid.UUID | None,
) -> list[uuid.UUID]:
    user_ids: set[uuid.UUID] = set()

    if db_game.host_user_id is not None:
        user_ids.add(db_game.host_user_id)

    participant_user_ids = db.scalars(
        select(GameParticipant.user_id).where(
            GameParticipant.game_id == db_game.id,
            GameParticipant.user_id.is_not(None),
            GameParticipant.participant_type.in_(GAME_UPDATED_PARTICIPANT_TYPES),
            GameParticipant.participant_status.in_(GAME_UPDATED_PARTICIPANT_STATUSES),
        )
    ).all()
    user_ids.update(user_id for user_id in participant_user_ids if user_id is not None)

    if actor_user_id is not None:
        user_ids.discard(actor_user_id)

    return sorted(user_ids, key=str)


def notify_connected_users_game_updated(
    db: Session,
    *,
    db_game: Game,
    actor_user_id: uuid.UUID | None,
    event_at: datetime,
) -> None:
    if (
        db_game.publish_status != "published"
        or db_game.game_status not in GAME_UPDATED_GAME_STATUSES
        or db_game.deleted_at is not None
    ):
        return

    recipient_user_ids = list_game_updated_recipient_user_ids(
        db,
        db_game,
        actor_user_id,
    )
    if not recipient_user_ids:
        return

    for recipient_user_id in recipient_user_ids:
        aggregation_key = game_updated_aggregation_key(db_game.id, recipient_user_id)
        notification_fields = build_game_notification_fields(
            db_game,
            "game_updated",
            event_at=event_at,
            aggregation_key=aggregation_key,
        )
        notification_fields.update(
            {
                "actor_user_id": actor_user_id,
                "related_game_id": db_game.id,
            }
        )
        reopen_aggregated_notification(
            db,
            user_id=recipient_user_id,
            notification_type="game_updated",
            notification_category="game_activity",
            notification_domain="game",
            aggregation_key=aggregation_key,
            values=notification_fields,
            aggregate_count_mode="clear",
        )
