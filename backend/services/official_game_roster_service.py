import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import case, or_, select
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
)
from backend.schemas.admin_official_game_schema import (
    AdminOfficialGameHostAssign,
    AdminOfficialGameHostRemove,
    AdminOfficialGamePlayerAdd,
    AdminOfficialGamePlayerRemove,
    AdminOfficialGameUserSearchEligibilityRead,
    AdminOfficialGameUserSearchRead,
    AdminOfficialGameUserSearchResultRead,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.game_rules import (
    ACTIVE_JOIN_STATUSES,
    build_game_conflict_detail,
    ensure_timezone,
    require_game_not_started,
)
from backend.services.game_participant_rules import (
    ACTIVE_ROSTER_PARTICIPANT_STATUSES,
    OFFICIAL_ROSTER_PARTICIPANT_TYPES,
)
from backend.services.game_service import (
    count_roster_players,
    get_next_roster_order,
    sync_game_capacity_status,
)
from backend.services.game_credit_service import release_reserved_game_credits
from backend.services.official_game_notification_service import (
    create_official_game_host_assigned_notification,
    create_official_game_host_removed_notification,
    create_official_game_player_added_notification,
    create_official_game_player_removed_notification,
)
from backend.services.official_game_service import get_official_game_or_404
from backend.services.payment_rules import PENDING_PAYMENT_STATUSES
from backend.services.status_history_service import (
    add_booking_status_history_if_changed,
    add_participant_status_history_if_changed,
)
from backend.services.user_service import get_user_display_name

ADMIN_REMOVABLE_PLAYER_STATUSES = ACTIVE_ROSTER_PARTICIPANT_STATUSES
OFFICIAL_HOST_PARTICIPANT_TYPES = OFFICIAL_ROSTER_PARTICIPANT_TYPES
IMMEDIATE_REMOVAL_BOOKING_PAYMENT_STATUSES = {
    "not_required",
    "unpaid",
    "requires_action",
    "failed",
}
IMMEDIATE_REMOVAL_PAYMENT_STATUSES = {
    "requires_payment_method",
    "requires_action",
    "failed",
    "canceled",
}
IMMEDIATE_REMOVAL_CREDIT_USAGE_STATUSES = {"reserved", "released"}
REMOVAL_PREVIEW_REQUIRED_DETAIL = (
    "Removal impact preview is required before removing this player."
)
USER_SEARCH_MAX_TERMS = 5


def get_active_user_or_404(
    db: Session,
    user_id: uuid.UUID,
    detail: str,
    *,
    for_update: bool = False,
) -> User:
    statement = select(User).where(User.id == user_id)
    if for_update:
        statement = statement.with_for_update()
    user = db.scalar(statement)

    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    if user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is not active.",
        )

    return user


def get_active_participant_for_user(
    db: Session,
    *,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
) -> GameParticipant | None:
    return db.scalars(
        select(GameParticipant)
        .where(
            GameParticipant.game_id == game_id,
            GameParticipant.user_id == user_id,
            GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
        )
        .limit(1)
    ).first()


def list_active_participants_for_user(
    db: Session,
    *,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[GameParticipant]:
    return list(
        db.scalars(
            select(GameParticipant)
            .where(
                GameParticipant.game_id == game_id,
                GameParticipant.user_id == user_id,
                GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
            )
            .order_by(GameParticipant.joined_at.asc())
        ).all()
    )


def get_official_host_roster_participant(
    db: Session,
    *,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
) -> GameParticipant:
    participants = list_active_participants_for_user(
        db,
        game_id=game_id,
        user_id=user_id,
    )

    if len(participants) != 1:
        detail = "Selected host must already be a confirmed roster player for this game."
        if len(participants) > 1:
            detail = "Selected host has multiple active roster rows for this game."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    participant = participants[0]
    if (
        participant.participant_status != "confirmed"
        or participant.participant_type not in OFFICIAL_HOST_PARTICIPANT_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected host must be a confirmed roster player for this game.",
        )

    return participant


def require_official_host_change_allowed(game: Game, *, action: str) -> None:
    if (
        game.publish_status != "published"
        or game.game_status not in {"scheduled", "full"}
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Host can only be {action} for published scheduled or full official games.",
        )

    require_game_not_started(
        game,
        datetime.now(timezone.utc),
        f"Host can only be {action} before the game starts.",
    )


def escape_like_search_term(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def normalize_user_search_terms(query: str) -> list[str]:
    return [
        term
        for term in query.strip().split()[:USER_SEARCH_MAX_TERMS]
        if len(term) >= 3
    ]


def user_search_condition(term: str):
    pattern = f"%{escape_like_search_term(term)}%"
    return or_(
        User.email.ilike(pattern, escape="\\"),
        User.first_name.ilike(pattern, escape="\\"),
        User.last_name.ilike(pattern, escape="\\"),
    )


def get_add_player_eligibility_reason(
    *,
    game: Game,
    user: User,
    active_participant_user_ids: set[uuid.UUID],
    roster_count: int,
    now: datetime,
) -> str | None:
    if (
        game.publish_status != "published"
        or game.game_status not in {"scheduled", "full"}
    ):
        return "game_not_addable"

    if now >= ensure_timezone(game.starts_at):
        return "game_started"

    if user.account_status != "active":
        return "inactive_user"

    if game.host_user_id == user.id:
        return "current_host"

    if user.id in active_participant_user_ids:
        return "already_on_roster"

    if roster_count >= game.total_spots:
        return "game_full"

    return None


def build_user_search_result(
    *,
    game: Game,
    user: User,
    active_participant_user_ids: set[uuid.UUID],
    roster_count: int,
    now: datetime,
) -> AdminOfficialGameUserSearchResultRead:
    reason = get_add_player_eligibility_reason(
        game=game,
        user=user,
        active_participant_user_ids=active_participant_user_ids,
        roster_count=roster_count,
        now=now,
    )
    return AdminOfficialGameUserSearchResultRead(
        user_id=user.id,
        display_name=get_user_display_name(user, fallback="User"),
        email=user.email,
        status=user.account_status,
        eligibility=AdminOfficialGameUserSearchEligibilityRead(
            can_add=reason is None,
            reason=reason,
        ),
    )


def search_official_game_add_player_users(
    db: Session,
    *,
    game_id: uuid.UUID,
    query: str,
    limit: int,
) -> AdminOfficialGameUserSearchRead:
    game = get_official_game_or_404(db, game_id)
    terms = normalize_user_search_terms(query)
    if not terms:
        return AdminOfficialGameUserSearchRead()

    statement = (
        select(User)
        .where(
            User.deleted_at.is_(None),
            *(user_search_condition(term) for term in terms),
        )
        .order_by(
            case((User.account_status == "active", 0), else_=1),
            User.last_name.asc().nulls_last(),
            User.first_name.asc().nulls_last(),
            User.email.asc().nulls_last(),
            User.id.asc(),
        )
        .limit(limit)
    )
    users = list(db.scalars(statement).all())
    if not users:
        return AdminOfficialGameUserSearchRead()

    user_ids = [user.id for user in users]
    active_participant_user_ids = set(
        db.scalars(
            select(GameParticipant.user_id).where(
                GameParticipant.game_id == game.id,
                GameParticipant.user_id.in_(user_ids),
                GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
            )
        ).all()
    )
    roster_count = count_roster_players(db, game.id)
    now = datetime.now(timezone.utc)

    return AdminOfficialGameUserSearchRead(
        results=[
            build_user_search_result(
                game=game,
                user=user,
                active_participant_user_ids=active_participant_user_ids,
                roster_count=roster_count,
                now=now,
            )
            for user in users
        ]
    )


def add_official_game_player(
    db: Session,
    *,
    admin_user: User,
    game_id: uuid.UUID,
    add_request: AdminOfficialGamePlayerAdd,
) -> GameParticipant:
    game = get_official_game_or_404(db, game_id, for_update=True)
    if (
        game.publish_status != "published"
        or game.game_status not in {"scheduled", "full"}
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Players can only be added to published scheduled or full official games.",
        )

    require_game_not_started(
        game,
        datetime.now(timezone.utc),
        "Players can only be added before the game starts.",
    )

    player = get_active_user_or_404(db, add_request.user_id, "Player not found.")
    if game.host_user_id == player.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The game host is already on the roster.",
        )

    existing_participant = get_active_participant_for_user(
        db,
        game_id=game.id,
        user_id=player.id,
    )
    if existing_participant is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected user already has an active roster row for this game.",
        )

    if count_roster_players(db, game.id) >= game.total_spots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add player because the game is already full.",
        )

    now = datetime.now(timezone.utc)
    booking = Booking(
        id=uuid.uuid4(),
        game_id=game.id,
        buyer_user_id=player.id,
        booking_status="confirmed",
        payment_status="not_required",
        participant_count=1,
        subtotal_cents=game.price_per_player_cents,
        platform_fee_cents=0,
        discount_cents=game.price_per_player_cents,
        total_cents=0,
        currency=game.currency,
        price_per_player_snapshot_cents=game.price_per_player_cents,
        platform_fee_snapshot_cents=0,
        booked_at=now,
        expires_at=None,
    )
    participant = GameParticipant(
        id=uuid.uuid4(),
        game_id=game.id,
        booking_id=booking.id,
        participant_type="admin_added",
        user_id=player.id,
        display_name_snapshot=get_user_display_name(player, fallback="Player"),
        participant_status="confirmed",
        attendance_status="unknown",
        cancellation_type="none",
        price_cents=0,
        currency=game.currency,
        roster_order=get_next_roster_order(db, game.id),
        joined_at=now,
        confirmed_at=now,
    )

    db.add(booking)
    db.add(participant)
    db.flush()

    add_booking_status_history_if_changed(
        db,
        booking,
        old_booking_status=None,
        old_payment_status=None,
        changed_by_user_id=admin_user.id,
        change_source="admin",
        reason=add_request.reason or "Admin added player with waived payment.",
    )
    add_participant_status_history_if_changed(
        db,
        participant,
        old_participant_status=None,
        old_attendance_status=None,
        changed_by_user_id=admin_user.id,
        change_source="admin",
        reason=add_request.reason or "Admin added player with waived payment.",
    )

    sync_game_capacity_status(db, game)
    game.updated_at = now
    db.add(game)

    record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="admin_add_player",
        target_game_id=game.id,
        target_user_id=player.id,
        target_booking_id=booking.id,
        target_participant_id=participant.id,
        reason=add_request.reason,
        metadata={
            "payment_handling": "waived",
            "game_price_per_player_cents": game.price_per_player_cents,
            "booking_total_cents": booking.total_cents,
            "discount_cents": booking.discount_cents,
            "created_payment": False,
        },
    )
    create_official_game_player_added_notification(
        db,
        game=game,
        participant=participant,
        admin_user=admin_user,
        now=now,
    )

    try:
        db.commit()
        db.refresh(participant)
        return participant
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc


def list_active_booking_participants(
    db: Session,
    *,
    game_id: uuid.UUID,
    booking_id: uuid.UUID,
) -> list[GameParticipant]:
    return list(
        db.scalars(
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
            .with_for_update()
        ).all()
    )


def require_immediate_official_player_removal_is_safe(
    db: Session,
    *,
    booking: Booking | None,
    participant_ids: set[uuid.UUID],
) -> None:
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=REMOVAL_PREVIEW_REQUIRED_DETAIL,
        )

    payments = list(
        db.scalars(
            select(Payment)
            .where(Payment.booking_id == booking.id)
            .with_for_update()
        ).all()
    )
    payment_ids = [payment.id for payment in payments]
    refund_conditions = [Refund.booking_id == booking.id]
    if payment_ids:
        refund_conditions.append(Refund.payment_id.in_(payment_ids))
    if participant_ids:
        refund_conditions.append(Refund.participant_id.in_(participant_ids))
    refunds_exist = db.scalar(
        select(Refund.id)
        .where(or_(*refund_conditions))
        .with_for_update()
        .limit(1)
    )
    credit_usages = list(
        db.scalars(
            select(GameCreditUsage)
            .where(GameCreditUsage.booking_id == booking.id)
            .with_for_update()
        ).all()
    )

    has_unsafe_payment = any(
        payment.payment_status not in IMMEDIATE_REMOVAL_PAYMENT_STATUSES
        for payment in payments
    )
    has_unsafe_credit_usage = any(
        usage.usage_status not in IMMEDIATE_REMOVAL_CREDIT_USAGE_STATUSES
        for usage in credit_usages
    )
    has_reserved_credit_outside_pending_checkout = (
        booking.booking_status != "pending_payment"
        and any(usage.usage_status == "reserved" for usage in credit_usages)
    )
    booking_payment_status_is_safe = (
        booking.payment_status in IMMEDIATE_REMOVAL_BOOKING_PAYMENT_STATUSES
        or (
            booking.booking_status == "pending_payment"
            and booking.payment_status == "processing"
            and bool(payments)
            and not has_unsafe_payment
        )
    )

    if (
        not booking_payment_status_is_safe
        or refunds_exist is not None
        or has_unsafe_payment
        or has_unsafe_credit_usage
        or has_reserved_credit_outside_pending_checkout
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=REMOVAL_PREVIEW_REQUIRED_DETAIL,
        )


def remove_official_game_player(
    db: Session,
    *,
    admin_user: User,
    game_id: uuid.UUID,
    participant_id: uuid.UUID,
    remove_request: AdminOfficialGamePlayerRemove,
) -> GameParticipant:
    game = get_official_game_or_404(db, game_id, for_update=True)
    if (
        game.publish_status != "published"
        or game.game_status not in {"scheduled", "full"}
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Players can only be removed from published scheduled or full official games.",
        )

    participant = db.scalar(
        select(GameParticipant)
        .where(GameParticipant.id == participant_id)
        .with_for_update()
    )
    if participant is None or participant.game_id != game.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Official game participant not found.",
        )

    if participant.participant_status not in ADMIN_REMOVABLE_PLAYER_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or confirmed roster participants can be removed here.",
        )

    if participant.participant_type == "host":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the host route to remove an official game host.",
        )

    if participant.user_id is not None and participant.user_id == game.host_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Remove host designation before removing this player.",
        )

    now = datetime.now(timezone.utc)
    booking = (
        db.scalar(
            select(Booking)
            .where(Booking.id == participant.booking_id)
            .with_for_update()
        )
        if participant.booking_id
        else None
    )
    original_participant_status = participant.participant_status
    original_booking_status = booking.booking_status if booking is not None else None
    participants_to_remove = [participant]
    if booking is not None and (
        participant.participant_type != "guest"
        or booking.booking_status == "pending_payment"
    ):
        participants_to_remove = list_active_booking_participants(
            db,
            game_id=game.id,
            booking_id=booking.id,
        )

    require_immediate_official_player_removal_is_safe(
        db,
        booking=booking,
        participant_ids={item.id for item in participants_to_remove},
    )

    removed_participant_ids = {item.id for item in participants_to_remove}
    for participant_to_remove in participants_to_remove:
        mark_admin_removed_participant(
            db,
            participant=participant_to_remove,
            admin_user_id=admin_user.id,
            reason=remove_request.reason,
            now=now,
        )

    if booking is not None:
        old_booking_status = booking.booking_status
        old_payment_status = booking.payment_status
        remaining_participants = [
            item
            for item in list_active_booking_participants(
                db,
                game_id=game.id,
                booking_id=booking.id,
            )
            if item.id not in removed_participant_ids
        ]

        if remaining_participants:
            booking.booking_status = "partially_cancelled"
            booking.participant_count = len(remaining_participants)
            booking.subtotal_cents = (
                booking.price_per_player_snapshot_cents * len(remaining_participants)
            )
            booking.discount_cents = min(booking.discount_cents, booking.subtotal_cents)
            booking.total_cents = (
                booking.subtotal_cents
                + booking.platform_fee_cents
                - booking.discount_cents
            )
            booking.cancelled_at = booking.cancelled_at or now
            booking.cancelled_by_user_id = admin_user.id
            booking.cancel_reason = (
                remove_request.reason or "Admin removed player from official game."
            )
        else:
            booking.booking_status = "cancelled"
            if old_booking_status == "pending_payment":
                booking.payment_status = "failed"
                cancel_pending_booking_payments_for_admin_removal(
                    db,
                    booking=booking,
                    reason=remove_request.reason,
                    now=now,
                )
            booking.cancelled_at = booking.cancelled_at or now
            booking.cancelled_by_user_id = admin_user.id
            booking.cancel_reason = (
                remove_request.reason or "Admin removed player from official game."
            )

        booking.updated_at = now
        db.add(booking)
        add_booking_status_history_if_changed(
            db,
            booking,
            old_booking_status=old_booking_status,
            old_payment_status=old_payment_status,
            changed_by_user_id=admin_user.id,
            change_source="admin",
            reason=remove_request.reason or "Admin removed player from official game.",
        )

    sync_game_capacity_status(db, game)
    game.updated_at = now
    db.add(game)

    record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="admin_remove_player",
        target_game_id=game.id,
        target_user_id=participant.user_id,
        target_booking_id=booking.id if booking is not None else None,
        target_participant_id=participant.id,
        reason=remove_request.reason,
        metadata={
            "removed_participant_ids": [item.id for item in participants_to_remove],
            "removed_count": len(participants_to_remove),
            "payment_refund_created": False,
        },
    )
    create_official_game_player_removed_notification(
        db,
        game=game,
        participant=participant,
        booking=booking,
        admin_user=admin_user,
        original_participant_status=original_participant_status,
        original_booking_status=original_booking_status,
        now=now,
    )

    try:
        db.commit()
        db.refresh(participant)
        return participant
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc


def assign_official_game_host(
    db: Session,
    *,
    admin_user: User,
    game_id: uuid.UUID,
    host_request: AdminOfficialGameHostAssign,
) -> Game:
    host = get_active_user_or_404(
        db,
        host_request.host_user_id,
        "Host not found.",
        for_update=True,
    )
    game = get_official_game_or_404(db, game_id, for_update=True)
    require_official_host_change_allowed(game, action="assigned")

    host_participant = get_official_host_roster_participant(
        db,
        game_id=game.id,
        user_id=host.id,
    )

    if game.host_user_id == host.id:
        return game

    old_host_user_id = game.host_user_id
    old_host_participant = None
    if old_host_user_id is not None:
        old_host_participant = get_active_participant_for_user(
            db,
            game_id=game.id,
            user_id=old_host_user_id,
        )

    now = datetime.now(timezone.utc)
    game.host_user_id = host.id
    game.updated_at = now
    db.add(game)

    metadata: dict[str, Any] = {
        "before": {
            "host_user_id": old_host_user_id,
            "host_participant_id": (
                old_host_participant.id if old_host_participant is not None else None
            ),
            "host_participant_type": (
                old_host_participant.participant_type
                if old_host_participant is not None
                else None
            ),
        },
        "after": {
            "host_user_id": host.id,
            "host_participant_id": host_participant.id,
            "host_participant_type": host_participant.participant_type,
        },
    }

    record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="assign_official_host",
        target_game_id=game.id,
        target_user_id=host.id,
        target_participant_id=host_participant.id,
        reason=host_request.reason,
        metadata=metadata,
    )
    if old_host_user_id is not None:
        create_official_game_host_removed_notification(
            db,
            game=game,
            removed_host_user_id=old_host_user_id,
            removed_host_participant=old_host_participant,
            admin_user=admin_user,
            now=now,
        )
    create_official_game_host_assigned_notification(
        db,
        game=game,
        host_participant=host_participant,
        admin_user=admin_user,
        now=now,
    )

    try:
        db.commit()
        db.refresh(game)
        return game
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc


def remove_official_game_host(
    db: Session,
    *,
    admin_user: User,
    game_id: uuid.UUID,
    remove_request: AdminOfficialGameHostRemove,
) -> Game:
    game = get_official_game_or_404(db, game_id, for_update=True)
    require_official_host_change_allowed(game, action="removed")

    if game.host_user_id is None:
        return game

    old_host_user_id = game.host_user_id
    old_host_participant = get_active_participant_for_user(
        db,
        game_id=game.id,
        user_id=old_host_user_id,
    )

    now = datetime.now(timezone.utc)
    game.host_user_id = None
    game.updated_at = now
    db.add(game)

    record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="remove_official_host",
        target_game_id=game.id,
        target_user_id=old_host_user_id,
        target_participant_id=(
            old_host_participant.id if old_host_participant is not None else None
        ),
        reason=remove_request.reason,
        metadata={
            "before": {
                "host_user_id": old_host_user_id,
                "host_participant_id": (
                    old_host_participant.id
                    if old_host_participant is not None
                    else None
                ),
                "host_participant_type": (
                    old_host_participant.participant_type
                    if old_host_participant is not None
                    else None
                ),
            },
            "after": {
                "host_user_id": None,
                "host_participant_id": None,
                "host_participant_type": None,
            },
        },
    )
    create_official_game_host_removed_notification(
        db,
        game=game,
        removed_host_user_id=old_host_user_id,
        removed_host_participant=old_host_participant,
        admin_user=admin_user,
        now=now,
    )

    try:
        db.commit()
        db.refresh(game)
        return game
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc


def mark_admin_removed_participant(
    db: Session,
    *,
    participant: GameParticipant,
    admin_user_id: uuid.UUID,
    reason: str | None,
    now: datetime,
) -> None:
    old_participant_status = participant.participant_status
    old_attendance_status = participant.attendance_status
    participant.participant_status = "removed"
    participant.cancellation_type = "admin_cancelled"
    participant.attendance_status = "not_applicable"
    participant.cancelled_at = participant.cancelled_at or now
    participant.updated_at = now
    db.add(participant)
    add_participant_status_history_if_changed(
        db,
        participant,
        old_participant_status=old_participant_status,
        old_attendance_status=old_attendance_status,
        changed_by_user_id=admin_user_id,
        change_source="admin",
        reason=reason or "Admin removed player from official game.",
    )


def cancel_pending_booking_payments_for_admin_removal(
    db: Session,
    *,
    booking: Booking,
    reason: str | None,
    now: datetime,
) -> None:
    release_reserved_game_credits(
        db,
        booking.id,
        now=now,
        release_reason="admin_player_removed",
        user_id=booking.buyer_user_id,
    )

    pending_payments = db.scalars(
        select(Payment).where(
            Payment.booking_id == booking.id,
            Payment.payment_status.in_(PENDING_PAYMENT_STATUSES),
        )
    ).all()

    for payment in pending_payments:
        payment.payment_status = "canceled"
        payment.failure_code = "admin_player_removed"
        payment.failure_message = (
            "Checkout invalidated after an admin removed the pending player."
        )
        payment.failure_reason = reason or "Admin removed player from official game."
        payment.updated_at = now
        db.add(payment)
