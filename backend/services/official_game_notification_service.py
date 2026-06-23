"""Official-game admin notification workflows."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Booking, Game, GameParticipant, Notification, User
from backend.services.notification_service import build_game_notification_fields


def resolve_unread_official_game_notification(
    db: Session,
    *,
    game: Game,
    user_id: uuid.UUID,
    notification_type: str,
    read_at: datetime,
) -> None:
    notifications = db.scalars(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.related_game_id == game.id,
            Notification.notification_type == notification_type,
            Notification.is_read.is_(False),
        )
    ).all()

    for notification in notifications:
        notification.is_read = True
        if notification.read_at is None:
            notification.read_at = read_at
        notification.updated_at = read_at
        db.add(notification)


def create_official_game_host_assigned_notification(
    db: Session,
    *,
    game: Game,
    host_participant: GameParticipant,
    admin_user: User,
    now: datetime,
) -> None:
    if host_participant.user_id is None or host_participant.user_id == admin_user.id:
        return

    resolve_unread_official_game_notification(
        db,
        game=game,
        user_id=host_participant.user_id,
        notification_type="game_host_removed",
        read_at=now,
    )
    db.add(
        Notification(
            id=uuid.uuid4(),
            user_id=host_participant.user_id,
            notification_type="game_host_assigned",
            notification_category="game_activity",
            notification_domain="game",
            **build_game_notification_fields(
                game,
                "game_host_assigned",
                event_at=now,
                body="Pickup Lane assigned you as host for this official game.",
            ),
            actor_user_id=admin_user.id,
            related_game_id=game.id,
            related_booking_id=host_participant.booking_id,
            related_participant_id=host_participant.id,
            is_read=False,
            read_at=None,
            created_at=now,
            updated_at=now,
        )
    )


def create_official_game_host_removed_notification(
    db: Session,
    *,
    game: Game,
    removed_host_user_id: uuid.UUID,
    removed_host_participant: GameParticipant | None,
    admin_user: User,
    now: datetime,
) -> None:
    if removed_host_user_id == admin_user.id:
        return

    resolve_unread_official_game_notification(
        db,
        game=game,
        user_id=removed_host_user_id,
        notification_type="game_host_assigned",
        read_at=now,
    )
    db.add(
        Notification(
            id=uuid.uuid4(),
            user_id=removed_host_user_id,
            notification_type="game_host_removed",
            notification_category="game_activity",
            notification_domain="game",
            **build_game_notification_fields(
                game,
                "game_host_removed",
                event_at=now,
                summary="You are no longer listed as host.",
                body="Pickup Lane removed you as host for this official game.",
            ),
            actor_user_id=admin_user.id,
            related_game_id=game.id,
            related_booking_id=(
                removed_host_participant.booking_id
                if removed_host_participant is not None
                else None
            ),
            related_participant_id=(
                removed_host_participant.id
                if removed_host_participant is not None
                else None
            ),
            is_read=False,
            read_at=None,
            created_at=now,
            updated_at=now,
        )
    )


def create_official_game_player_added_notification(
    db: Session,
    *,
    game: Game,
    participant: GameParticipant,
    admin_user: User,
    now: datetime,
) -> None:
    if participant.user_id is None or participant.user_id == admin_user.id:
        return

    resolve_unread_official_game_notification(
        db,
        game=game,
        user_id=participant.user_id,
        notification_type="game_player_removed_by_admin",
        read_at=now,
    )
    db.add(
        Notification(
            id=uuid.uuid4(),
            user_id=participant.user_id,
            notification_type="game_player_added_by_admin",
            notification_category="game_activity",
            notification_domain="game",
            **build_game_notification_fields(
                game,
                "game_player_added_by_admin",
                event_at=now,
                body=(
                    "Pickup Lane added you to this official game. "
                    "No payment was charged."
                ),
            ),
            actor_user_id=admin_user.id,
            related_game_id=game.id,
            related_booking_id=participant.booking_id,
            related_participant_id=participant.id,
            is_read=False,
            read_at=None,
            created_at=now,
            updated_at=now,
        )
    )


def create_official_game_player_removed_notification(
    db: Session,
    *,
    game: Game,
    participant: GameParticipant,
    booking: Booking | None,
    admin_user: User,
    original_participant_status: str,
    original_booking_status: str | None,
    now: datetime,
) -> None:
    if (
        original_participant_status == "pending_payment"
        or original_booking_status == "pending_payment"
    ):
        return

    is_guest_removal = participant.participant_type == "guest"
    recipient_user_id = (
        booking.buyer_user_id
        if is_guest_removal and booking is not None
        else participant.user_id
    )
    if recipient_user_id is None or recipient_user_id == admin_user.id:
        return

    if not is_guest_removal:
        resolve_unread_official_game_notification(
            db,
            game=game,
            user_id=recipient_user_id,
            notification_type="game_player_added_by_admin",
            read_at=now,
        )

    notification_overrides = (
        {
            "title": "Guest removed",
            "summary": "A guest was removed from your booking.",
            "body": "A guest was removed from your booking for this official game.",
        }
        if is_guest_removal
        else {
            "body": (
                "Pickup Lane removed you from this official game. "
                "Any payment or credit updates will be handled separately."
            ),
        }
    )
    db.add(
        Notification(
            id=uuid.uuid4(),
            user_id=recipient_user_id,
            notification_type="game_player_removed_by_admin",
            notification_category="game_activity",
            notification_domain="game",
            **build_game_notification_fields(
                game,
                "game_player_removed_by_admin",
                event_at=now,
                **notification_overrides,
            ),
            actor_user_id=admin_user.id,
            related_game_id=game.id,
            related_booking_id=booking.id if booking is not None else None,
            related_participant_id=participant.id,
            is_read=False,
            read_at=None,
            created_at=now,
            updated_at=now,
        )
    )
