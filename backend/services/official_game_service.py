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
    AdminAction,
    Booking,
    BookingStatusHistory,
    Game,
    GameCredit,
    GameCreditUsage,
    GameParticipant,
    ParticipantStatusHistory,
    Payment,
    Refund,
    User,
    Venue,
    WaitlistEntry,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_permission_service import (
    PERMISSION_MONEY_CREDIT_MANAGE,
    PERMISSION_MONEY_REFUND,
    require_user_admin_permission,
)
from backend.services.game_service import (
    ACTIVE_JOIN_STATUSES,
    OFFICIAL_FORCED_FIELDS,
    build_game_conflict_detail,
    count_roster_players,
    create_or_reopen_booking_refunded_notification,
    get_next_roster_order,
    normalize_official_game_invariants,
    normalize_game_lifecycle_fields,
    require_game_not_started,
    sync_game_capacity_status,
    validate_game_business_rules,
)
from backend.services.venue_service import find_matching_active_venue
from backend.schemas.admin_official_game_schema import (
    AdminOfficialGameCancelExecute,
    AdminOfficialGameCancellationPreviewRead,
    AdminOfficialGameCancellationResultRead,
    AdminOfficialGameCreate,
    AdminOfficialGameHostAssign,
    AdminOfficialGameHostRemove,
    AdminOfficialGameMoneyRead,
    AdminOfficialGamePlayerAdd,
    AdminOfficialGamePlayerRemovalExecute,
    AdminOfficialGamePlayerRemove,
    AdminOfficialGamePlayerRemovalPreviewRead,
    AdminOfficialGamePlayerRemovalResultRead,
    AdminOfficialGameRemovalRefundRead,
    AdminOfficialGameRemovalParticipantRead,
    AdminOfficialGameUpdate,
    AdminOfficialGameVenuePayload,
)
from backend.services.game_cancellation_service import (
    build_official_game_cancellation_preview,
    execute_official_game_cancellation as execute_official_game_cancellation_workflow,
)
from backend.services.game_credit_service import (
    GameCreditLedgerError,
    release_reserved_game_credits,
    restore_redeemed_game_credits,
)
from backend.services.game_waitlist_service import promote_waitlist_entries
from backend.services.official_game_notification_service import (
    create_official_game_host_assigned_notification,
    create_official_game_host_removed_notification,
    create_official_game_player_added_notification,
    create_official_game_player_removed_notification,
)
from backend.services.stripe_service import (
    StripeConfigError,
    create_refund as create_stripe_refund,
)
from backend.services.support_flag_service import (
    create_support_flag,
    stage_support_flag,
)

PENDING_ADMIN_INVALIDATED_PAYMENT_STATUSES = {
    "requires_payment_method",
    "requires_action",
    "processing",
}
ADMIN_REMOVABLE_PLAYER_STATUSES = {"pending_payment", "confirmed"}
OFFICIAL_HOST_PARTICIPANT_TYPES = {"registered_user", "admin_added"}
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
REMOVAL_PREVIEW_COLLECTED_PAYMENT_STATUSES = {
    "succeeded",
    "partially_refunded",
    "refunded",
    "disputed",
}
REMOVAL_PREVIEW_REFUNDABLE_PAYMENT_STATUSES = {
    "succeeded",
}
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

ADMIN_EDIT_NON_NULL_FIELDS = {
    "title",
    "starts_at",
    "ends_at",
    "timezone",
    "format_label",
    "game_player_group",
    "skill_level",
    "environment_type",
    "total_spots",
    "price_per_player_cents",
    "allow_guests",
    "max_guests_per_booking",
    "waitlist_enabled",
    "is_chat_enabled",
}

ADMIN_EDIT_CHECKOUT_SENSITIVE_FIELDS = {
    "starts_at",
    "ends_at",
    "timezone",
    "format_label",
    "game_player_group",
    "skill_level",
    "environment_type",
    "total_spots",
    "price_per_player_cents",
    "allow_guests",
    "max_guests_per_booking",
    "waitlist_enabled",
}


def build_address_snapshot(venue: Venue) -> str:
    state_line = " ".join(
        value for value in [venue.state.strip(), venue.postal_code.strip()] if value
    )
    city_line = ", ".join(
        value for value in [venue.city.strip(), state_line] if value
    )
    return ", ".join(
        value for value in [venue.address_line_1.strip(), city_line] if value
    )


def clean_required_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required.",
        )
    return cleaned


def build_user_display_name(user: User) -> str:
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return full_name or user.email or "Player"


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


def get_active_venue_or_404(db: Session, venue_id: uuid.UUID) -> Venue:
    venue = db.get(Venue, venue_id)

    if venue is None or venue.deleted_at is not None or not venue.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found.",
        )

    if venue.venue_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Official games require an approved venue.",
        )

    return venue


def get_or_create_admin_venue_from_sources(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    venue_id: uuid.UUID | None,
    venue_request: AdminOfficialGameVenuePayload | None,
) -> Venue:
    if venue_id is not None and venue_request is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Send either venue_id or venue, not both.",
        )

    if venue_id is None and venue_request is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Official games require venue_id or venue.",
        )

    if venue_id is not None:
        return get_active_venue_or_404(db, venue_id)

    assert venue_request is not None
    venue_data = venue_request.model_dump()
    country_code = clean_required_text(venue_data["country_code"], "country_code")
    if len(country_code) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="country_code must be two letters.",
        )

    matching_venue = find_matching_active_venue(
        db,
        name=clean_required_text(venue_data["name"], "venue.name"),
        address_line_1=clean_required_text(
            venue_data["address_line_1"],
            "venue.address_line_1",
        ),
        city=clean_required_text(venue_data["city"], "venue.city"),
        state=clean_required_text(venue_data["state"], "venue.state"),
        postal_code=clean_required_text(
            venue_data["postal_code"],
            "venue.postal_code",
        ),
        country_code=country_code.upper(),
        neighborhood=(venue_data.get("neighborhood") or "").strip() or None,
    )

    if matching_venue is not None:
        if matching_venue.venue_status != "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Official games require an approved venue.",
            )
        return matching_venue

    now = datetime.now(timezone.utc)
    venue = Venue(
        id=uuid.uuid4(),
        name=clean_required_text(venue_data["name"], "venue.name"),
        address_line_1=clean_required_text(
            venue_data["address_line_1"],
            "venue.address_line_1",
        ),
        city=clean_required_text(venue_data["city"], "venue.city"),
        state=clean_required_text(venue_data["state"], "venue.state"),
        postal_code=clean_required_text(
            venue_data["postal_code"],
            "venue.postal_code",
        ),
        country_code=country_code.upper(),
        neighborhood=(venue_data.get("neighborhood") or "").strip() or None,
        venue_status="approved",
        created_by_user_id=admin_user_id,
        approved_by_user_id=admin_user_id,
        approved_at=now,
        is_active=True,
    )
    db.add(venue)
    db.flush()
    return venue


def get_or_create_admin_venue(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    create_request: AdminOfficialGameCreate,
) -> Venue:
    return get_or_create_admin_venue_from_sources(
        db,
        admin_user_id=admin_user_id,
        venue_id=create_request.venue_id,
        venue_request=create_request.venue,
    )


def build_official_game_data(
    *,
    admin_user_id: uuid.UUID,
    create_request: AdminOfficialGameCreate,
    venue: Venue,
) -> dict[str, object]:
    title = create_request.title or f"{venue.name} {create_request.format_label}"

    return {
        "game_type": "official",
        "payment_collection_type": "in_app",
        "publish_status": "published",
        "game_status": "scheduled",
        "title": clean_required_text(title, "title"),
        "description": None,
        "venue_id": venue.id,
        "venue_name_snapshot": venue.name,
        "address_snapshot": build_address_snapshot(venue),
        "city_snapshot": venue.city,
        "state_snapshot": venue.state,
        "neighborhood_snapshot": venue.neighborhood,
        "host_user_id": None,
        "created_by_user_id": admin_user_id,
        "starts_at": create_request.starts_at,
        "ends_at": create_request.ends_at,
        "timezone": create_request.timezone,
        "sport_type": "soccer",
        "format_label": create_request.format_label,
        "game_player_group": create_request.game_player_group,
        "skill_level": create_request.skill_level,
        "environment_type": create_request.environment_type,
        "total_spots": create_request.total_spots,
        "price_per_player_cents": create_request.price_per_player_cents,
        "currency": "USD",
        "minimum_age": None,
        "allow_guests": create_request.allow_guests,
        "max_guests_per_booking": create_request.max_guests_per_booking,
        "host_guest_max": 0,
        "waitlist_enabled": create_request.waitlist_enabled,
        "is_chat_enabled": create_request.is_chat_enabled,
        "policy_mode": "official_standard",
        "custom_rules_text": None,
        "custom_cancellation_text": None,
        "game_notes": create_request.game_notes,
        "parking_notes": create_request.parking_notes,
        "published_at": None,
        "cancelled_at": None,
        "cancelled_by_user_id": None,
        "cancel_reason": None,
        "completed_at": None,
        "completed_by_user_id": None,
    }


def get_replacement_source_official_game(
    db: Session,
    replacement_for_game_id: uuid.UUID | None,
) -> Game | None:
    if replacement_for_game_id is None:
        return None

    source_game = db.get(Game, replacement_for_game_id)
    if (
        source_game is None
        or source_game.deleted_at is not None
        or source_game.game_type != "official"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="replacement_for_game_id must reference an existing official game.",
        )

    return source_game


def build_create_official_game_metadata(
    game: Game,
    source_game: Game | None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "game": {
            "title": game.title,
            "starts_at": game.starts_at,
            "ends_at": game.ends_at,
            "venue_id": game.venue_id,
            "format_label": game.format_label,
            "total_spots": game.total_spots,
            "price_per_player_cents": game.price_per_player_cents,
            "currency": game.currency,
        },
    }

    if source_game is not None:
        metadata["replacement"] = {
            "replacement_for_game_id": str(source_game.id),
            "replacement_for_game_title": source_game.title,
            "replacement_for_game_status": source_game.game_status,
        }

    return metadata


def add_admin_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    action_type: str,
    target_game_id: uuid.UUID,
    target_user_id: uuid.UUID | None = None,
    target_booking_id: uuid.UUID | None = None,
    target_participant_id: uuid.UUID | None = None,
    target_venue_id: uuid.UUID | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AdminAction:
    return record_admin_action(
        db,
        admin_user_id=admin_user_id,
        action_type=action_type,
        target_game_id=target_game_id,
        target_user_id=target_user_id,
        target_booking_id=target_booking_id,
        target_participant_id=target_participant_id,
        target_venue_id=target_venue_id,
        reason=reason,
        metadata=metadata,
    )


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


def count_confirmed_roster_players(db: Session, game_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(GameParticipant)
            .where(
                GameParticipant.game_id == game_id,
                GameParticipant.participant_status == "confirmed",
            )
        )
        or 0
    )


def add_participant_status_history(
    db: Session,
    *,
    participant: GameParticipant,
    old_participant_status: str | None,
    old_attendance_status: str | None,
    admin_user_id: uuid.UUID,
    reason: str | None,
) -> None:
    db.add(
        ParticipantStatusHistory(
            id=uuid.uuid4(),
            participant_id=participant.id,
            old_participant_status=old_participant_status,
            new_participant_status=participant.participant_status,
            old_attendance_status=old_attendance_status,
            new_attendance_status=participant.attendance_status,
            changed_by_user_id=admin_user_id,
            change_source="admin",
            change_reason=reason,
        )
    )


def add_booking_status_history(
    db: Session,
    *,
    booking: Booking,
    old_booking_status: str | None,
    old_payment_status: str | None,
    admin_user_id: uuid.UUID,
    reason: str | None,
) -> None:
    db.add(
        BookingStatusHistory(
            id=uuid.uuid4(),
            booking_id=booking.id,
            old_booking_status=old_booking_status,
            new_booking_status=booking.booking_status,
            old_payment_status=old_payment_status,
            new_payment_status=booking.payment_status,
            changed_by_user_id=admin_user_id,
            change_source="admin",
            change_reason=reason,
        )
    )


def create_official_game(
    db: Session,
    *,
    admin_user: User,
    create_request: AdminOfficialGameCreate,
) -> Game:
    source_game = get_replacement_source_official_game(
        db,
        create_request.replacement_for_game_id,
    )
    venue = get_or_create_admin_venue(
        db,
        admin_user_id=admin_user.id,
        create_request=create_request,
    )
    game_data = normalize_official_game_invariants(
        normalize_game_lifecycle_fields(
            build_official_game_data(
                admin_user_id=admin_user.id,
                create_request=create_request,
                venue=venue,
            )
        ),
        is_create=True,
    )
    validate_game_business_rules(game_data)

    game = Game(id=uuid.uuid4(), **game_data)
    db.add(game)
    db.flush()

    add_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="create_official_game",
        target_game_id=game.id,
        target_venue_id=venue.id,
        reason=create_request.reason,
        metadata=build_create_official_game_metadata(game, source_game),
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


def get_official_game_or_404(
    db: Session,
    game_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> Game:
    if for_update:
        game = db.scalar(
            select(Game).where(Game.id == game_id).with_for_update()
        )
    else:
        game = db.get(Game, game_id)

    if (
        game is None
        or game.deleted_at is not None
        or game.game_type != "official"
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Official game not found.",
        )

    return game


def preview_official_game_cancellation(
    db: Session,
    *,
    game_id: uuid.UUID,
    admin_user: User,
) -> AdminOfficialGameCancellationPreviewRead:
    return build_official_game_cancellation_preview(
        db,
        game_id=game_id,
        admin_user=admin_user,
    )


def execute_official_game_cancellation(
    db: Session,
    *,
    game_id: uuid.UUID,
    admin_user: User,
    cancel_request: AdminOfficialGameCancelExecute,
) -> AdminOfficialGameCancellationResultRead:
    return execute_official_game_cancellation_workflow(
        db,
        game_id=game_id,
        admin_user=admin_user,
        cancel_request=cancel_request,
    )


def list_official_games(
    db: Session,
    *,
    game_status: str | None = None,
    limit: int = 50,
) -> list[Game]:
    statement = (
        select(Game)
        .where(Game.game_type == "official", Game.deleted_at.is_(None))
    )

    if game_status is not None:
        statement = statement.where(Game.game_status == game_status)

    statement = statement.order_by(Game.starts_at.asc(), Game.created_at.asc()).limit(
        limit
    )

    return list(db.scalars(statement).all())


def list_official_game_participants(
    db: Session,
    game_id: uuid.UUID,
) -> list[GameParticipant]:
    get_official_game_or_404(db, game_id)
    return list(
        db.scalars(
            select(GameParticipant)
            .where(GameParticipant.game_id == game_id)
            .order_by(
                GameParticipant.roster_order.asc().nulls_last(),
                GameParticipant.created_at.asc(),
            )
        ).all()
    )


def list_official_game_bookings(
    db: Session,
    game_id: uuid.UUID,
) -> list[Booking]:
    get_official_game_or_404(db, game_id)
    return list(
        db.scalars(
            select(Booking)
            .where(Booking.game_id == game_id)
            .order_by(Booking.created_at.desc())
        ).all()
    )


def list_official_game_waitlist_entries(
    db: Session,
    game_id: uuid.UUID,
) -> list[WaitlistEntry]:
    get_official_game_or_404(db, game_id)
    return list(
        db.scalars(
            select(WaitlistEntry)
            .where(WaitlistEntry.game_id == game_id)
            .order_by(
                WaitlistEntry.position.asc(),
                WaitlistEntry.joined_at.asc(),
                WaitlistEntry.created_at.asc(),
            )
        ).all()
    )


def get_official_game_money(
    db: Session,
    game_id: uuid.UUID,
) -> AdminOfficialGameMoneyRead:
    get_official_game_or_404(db, game_id)

    booking_ids = select(Booking.id).where(Booking.game_id == game_id)
    participant_ids = select(GameParticipant.id).where(GameParticipant.game_id == game_id)
    payment_ids = select(Payment.id).where(
        or_(
            Payment.game_id == game_id,
            Payment.booking_id.in_(booking_ids),
        )
    )
    scoped_credit_usage_ids = select(GameCreditUsage.game_credit_id).where(
        or_(
            GameCreditUsage.game_id == game_id,
            GameCreditUsage.booking_id.in_(booking_ids),
            GameCreditUsage.payment_id.in_(payment_ids),
        )
    )

    payments = list(
        db.scalars(
            select(Payment)
            .where(
                or_(
                    Payment.game_id == game_id,
                    Payment.booking_id.in_(booking_ids),
                )
            )
            .order_by(Payment.created_at.desc(), Payment.id.desc())
        ).all()
    )
    refunds = list(
        db.scalars(
            select(Refund)
            .where(
                or_(
                    Refund.payment_id.in_(payment_ids),
                    Refund.booking_id.in_(booking_ids),
                    Refund.participant_id.in_(participant_ids),
                )
            )
            .order_by(Refund.created_at.desc(), Refund.id.desc())
        ).all()
    )
    credits = list(
        db.scalars(
            select(GameCredit)
            .where(
                or_(
                    GameCredit.source_game_id == game_id,
                    GameCredit.source_booking_id.in_(booking_ids),
                    GameCredit.source_payment_id.in_(payment_ids),
                    GameCredit.id.in_(scoped_credit_usage_ids),
                )
            )
            .order_by(GameCredit.created_at.desc(), GameCredit.id.desc())
        ).all()
    )
    credit_usages = list(
        db.scalars(
            select(GameCreditUsage)
            .where(
                or_(
                    GameCreditUsage.game_id == game_id,
                    GameCreditUsage.booking_id.in_(booking_ids),
                    GameCreditUsage.payment_id.in_(payment_ids),
                )
            )
            .order_by(GameCreditUsage.created_at.desc(), GameCreditUsage.id.desc())
        ).all()
    )

    return AdminOfficialGameMoneyRead(
        payments=payments,
        refunds=refunds,
        credits=credits,
        credit_usages=credit_usages,
    )


def build_effective_official_game_data(
    game: Game,
    update_data: dict[str, Any],
) -> dict[str, object]:
    return {
        "game_type": game.game_type,
        "payment_collection_type": game.payment_collection_type,
        "publish_status": game.publish_status,
        "game_status": game.game_status,
        "title": update_data.get("title", game.title),
        "description": game.description,
        "venue_id": game.venue_id,
        "venue_name_snapshot": game.venue_name_snapshot,
        "address_snapshot": game.address_snapshot,
        "city_snapshot": game.city_snapshot,
        "state_snapshot": game.state_snapshot,
        "neighborhood_snapshot": game.neighborhood_snapshot,
        "host_user_id": game.host_user_id,
        "created_by_user_id": game.created_by_user_id,
        "starts_at": update_data.get("starts_at", game.starts_at),
        "ends_at": update_data.get("ends_at", game.ends_at),
        "timezone": update_data.get("timezone", game.timezone),
        "sport_type": game.sport_type,
        "format_label": update_data.get("format_label", game.format_label),
        "game_player_group": update_data.get(
            "game_player_group", game.game_player_group
        ),
        "skill_level": update_data.get("skill_level", game.skill_level),
        "environment_type": update_data.get(
            "environment_type", game.environment_type
        ),
        "total_spots": update_data.get("total_spots", game.total_spots),
        "price_per_player_cents": update_data.get(
            "price_per_player_cents", game.price_per_player_cents
        ),
        "currency": game.currency,
        "minimum_age": game.minimum_age,
        "allow_guests": update_data.get("allow_guests", game.allow_guests),
        "max_guests_per_booking": update_data.get(
            "max_guests_per_booking", game.max_guests_per_booking
        ),
        "host_guest_max": game.host_guest_max,
        "waitlist_enabled": update_data.get(
            "waitlist_enabled", game.waitlist_enabled
        ),
        "is_chat_enabled": update_data.get("is_chat_enabled", game.is_chat_enabled),
        "policy_mode": game.policy_mode,
        "custom_rules_text": game.custom_rules_text,
        "custom_cancellation_text": game.custom_cancellation_text,
        "game_notes": update_data.get("game_notes", game.game_notes),
        "parking_notes": update_data.get("parking_notes", game.parking_notes),
        "published_at": game.published_at,
        "cancelled_at": game.cancelled_at,
        "cancelled_by_user_id": game.cancelled_by_user_id,
        "cancel_reason": game.cancel_reason,
        "completed_at": game.completed_at,
        "completed_by_user_id": game.completed_by_user_id,
    }


def snapshot_game_fields(game: Game, field_names: set[str]) -> dict[str, Any]:
    return {field_name: getattr(game, field_name) for field_name in sorted(field_names)}


def changed_update_fields(
    game: Game,
    update_data: dict[str, Any],
    field_names: set[str],
) -> set[str]:
    changed_fields: set[str] = set()

    for field_name in field_names:
        if field_name not in update_data:
            continue

        current_value = getattr(game, field_name)
        next_value = update_data[field_name]
        if isinstance(current_value, datetime) and isinstance(next_value, datetime):
            if current_value.astimezone(timezone.utc) != next_value.astimezone(
                timezone.utc
            ):
                changed_fields.add(field_name)
            continue

        if current_value != next_value:
            changed_fields.add(field_name)

    return changed_fields


def expire_pending_checkouts_for_admin_edit(
    db: Session,
    *,
    game: Game,
    admin_user_id: uuid.UUID,
    reason: str | None,
    now: datetime,
) -> int:
    pending_bookings = list(
        db.scalars(
            select(Booking).where(
                Booking.game_id == game.id,
                Booking.booking_status == "pending_payment",
            )
        ).all()
    )
    if not pending_bookings:
        return 0

    pending_booking_ids = [booking.id for booking in pending_bookings]
    pending_participants = list(
        db.scalars(
            select(GameParticipant).where(
                GameParticipant.booking_id.in_(pending_booking_ids),
                GameParticipant.participant_status == "pending_payment",
            )
        ).all()
    )
    pending_payments = list(
        db.scalars(
            select(Payment).where(
                Payment.booking_id.in_(pending_booking_ids),
                Payment.payment_status.in_(PENDING_ADMIN_INVALIDATED_PAYMENT_STATUSES),
            )
        ).all()
    )

    for booking in pending_bookings:
        release_reserved_game_credits(
            db,
            booking.id,
            now=now,
            release_reason="admin_game_updated",
            user_id=booking.buyer_user_id,
        )
        booking.booking_status = "expired"
        booking.payment_status = "failed"
        booking.cancel_reason = reason or "Official game details changed by admin."
        booking.updated_at = now
        db.add(booking)

    for participant in pending_participants:
        old_status = participant.participant_status
        old_attendance_status = participant.attendance_status
        participant.participant_status = "cancelled"
        participant.cancellation_type = "admin_cancelled"
        participant.cancelled_at = participant.cancelled_at or now
        participant.updated_at = now
        db.add(participant)
        db.add(
            ParticipantStatusHistory(
                id=uuid.uuid4(),
                participant_id=participant.id,
                old_participant_status=old_status,
                new_participant_status="cancelled",
                old_attendance_status=old_attendance_status,
                new_attendance_status=participant.attendance_status,
                changed_by_user_id=admin_user_id,
                change_source="admin",
                change_reason=reason or "Official game details changed by admin.",
            )
        )

    for payment in pending_payments:
        payment.payment_status = "canceled"
        payment.failure_code = "admin_game_updated"
        payment.failure_message = "Checkout invalidated after official game details changed."
        payment.failure_reason = reason or "Official game details changed by admin."
        payment.updated_at = now
        db.add(payment)

    return len(pending_bookings)


def update_official_game(
    db: Session,
    *,
    admin_user: User,
    game_id: uuid.UUID,
    update_request: AdminOfficialGameUpdate,
) -> Game:
    game = get_official_game_or_404(db, game_id, for_update=True)
    if (
        game.publish_status != "published"
        or game.game_status not in {"scheduled", "full"}
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published scheduled or full official games can be edited.",
        )

    request_data = update_request.model_dump(exclude_unset=True)
    reason = request_data.pop("reason", None)

    if any(
        field_name in request_data and request_data[field_name] is None
        for field_name in ADMIN_EDIT_NON_NULL_FIELDS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Official game edit fields cannot be null.",
        )

    if request_data == {}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No official game changes provided.",
        )

    if "title" in request_data:
        request_data["title"] = clean_required_text(request_data["title"], "title")
    for text_field in (
        "timezone",
        "format_label",
        "game_player_group",
        "skill_level",
        "environment_type",
    ):
        if text_field in request_data:
            request_data[text_field] = clean_required_text(
                request_data[text_field],
                text_field,
            )

    confirmed_roster_count = count_confirmed_roster_players(db, game.id)
    if (
        "total_spots" in request_data
        and request_data["total_spots"] < confirmed_roster_count
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="total_spots cannot be less than the active roster count.",
        )

    effective_game_data = build_effective_official_game_data(game, request_data)
    effective_game_data = normalize_official_game_invariants(
        normalize_game_lifecycle_fields(effective_game_data, game)
    )
    validate_game_business_rules(effective_game_data)

    if "starts_at" in request_data:
        request_data["starts_at"] = effective_game_data["starts_at"]
    if "ends_at" in request_data:
        request_data["ends_at"] = effective_game_data["ends_at"]
    for field_name in OFFICIAL_FORCED_FIELDS:
        if getattr(game, field_name) != effective_game_data[field_name]:
            request_data[field_name] = effective_game_data[field_name]
    request_data["starts_on_local"] = effective_game_data["starts_on_local"]

    field_names = set(request_data)
    before_values = snapshot_game_fields(game, field_names)
    actual_changed_fields = changed_update_fields(game, request_data, field_names)
    checkout_sensitive_changed_fields = (
        actual_changed_fields & ADMIN_EDIT_CHECKOUT_SENSITIVE_FIELDS
    )

    now = datetime.now(timezone.utc)
    expired_pending_booking_count = 0
    if checkout_sensitive_changed_fields:
        expired_pending_booking_count = expire_pending_checkouts_for_admin_edit(
            db,
            game=game,
            admin_user_id=admin_user.id,
            reason=reason,
            now=now,
        )

    for field_name, field_value in request_data.items():
        setattr(game, field_name, field_value)

    sync_game_capacity_status(db, game)
    game.updated_at = now
    db.add(game)

    add_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="update_official_game",
        target_game_id=game.id,
        reason=reason,
        metadata={
            "changed_fields": sorted(actual_changed_fields),
            "checkout_sensitive_changed_fields": sorted(
                checkout_sensitive_changed_fields
            ),
            "expired_pending_booking_count": expired_pending_booking_count,
            "before": before_values,
            "after": snapshot_game_fields(game, field_names),
        },
    )

    try:
        db.commit()
        db.refresh(game)
        return game
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc


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
        display_name_snapshot=build_user_display_name(player),
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

    add_booking_status_history(
        db,
        booking=booking,
        old_booking_status=None,
        old_payment_status=None,
        admin_user_id=admin_user.id,
        reason=add_request.reason or "Admin added player with waived payment.",
    )
    add_participant_status_history(
        db,
        participant=participant,
        old_participant_status=None,
        old_attendance_status=None,
        admin_user_id=admin_user.id,
        reason=add_request.reason or "Admin added player with waived payment.",
    )

    sync_game_capacity_status(db, game)
    game.updated_at = now
    db.add(game)

    add_admin_action(
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
        if payment.payment_status in REMOVAL_PREVIEW_COLLECTED_PAYMENT_STATUSES
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
        if payment.payment_status in REMOVAL_PREVIEW_REFUNDABLE_PAYMENT_STATUSES
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
        or game.game_status not in {"scheduled", "full"}
    ):
        classification = "blocked_game_state"
        blocking_reasons.append(
            "Players can only be removed from published scheduled or full official games."
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
    add_booking_status_history(
        db,
        booking=booking,
        old_booking_status=old_booking_status,
        old_payment_status=old_payment_status,
        admin_user_id=admin_user.id,
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
    add_participant_status_history(
        db,
        participant=participant,
        old_participant_status=old_participant_status,
        old_attendance_status=old_attendance_status,
        admin_user_id=admin_user_id,
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
            Payment.payment_status.in_(PENDING_ADMIN_INVALIDATED_PAYMENT_STATUSES),
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
        add_booking_status_history(
            db,
            booking=booking,
            old_booking_status=old_booking_status,
            old_payment_status=old_payment_status,
            admin_user_id=admin_user.id,
            reason=remove_request.reason or "Admin removed player from official game.",
        )

    sync_game_capacity_status(db, game)
    game.updated_at = now
    db.add(game)

    add_admin_action(
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

    add_admin_action(
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

    add_admin_action(
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
