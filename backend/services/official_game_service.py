import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    Booking,
    BookingStatusHistory,
    Game,
    GameParticipant,
    ParticipantStatusHistory,
    Payment,
    User,
    Venue,
)
from backend.routes.game_routes import (
    ACTIVE_JOIN_STATUSES,
    OFFICIAL_FORCED_FIELDS,
    build_game_conflict_detail,
    count_roster_players,
    get_next_roster_order,
    normalize_official_game_invariants,
    normalize_game_lifecycle_fields,
    require_game_not_started,
    sync_game_capacity_status,
    validate_game_business_rules,
)
from backend.routes.venue_routes import find_matching_active_venue
from backend.schemas.admin_official_game_schema import (
    AdminOfficialGameCreate,
    AdminOfficialGameHostAssign,
    AdminOfficialGameHostRemove,
    AdminOfficialGamePlayerAdd,
    AdminOfficialGamePlayerRemove,
    AdminOfficialGameUpdate,
    AdminOfficialGameVenuePayload,
)
from backend.services.game_credit_service import release_reserved_game_credits

PENDING_ADMIN_INVALIDATED_PAYMENT_STATUSES = {
    "requires_payment_method",
    "requires_action",
    "processing",
}
ADMIN_REMOVABLE_PLAYER_STATUSES = {"pending_payment", "confirmed"}
OFFICIAL_HOST_PARTICIPANT_TYPES = {"registered_user", "admin_added"}

ADMIN_EDIT_NON_NULL_FIELDS = {
    "title",
    "starts_at",
    "ends_at",
    "timezone",
    "format_label",
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


def serialize_audit_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, dict):
        return {key: serialize_audit_value(item) for key, item in value.items()}

    if isinstance(value, list):
        return [serialize_audit_value(item) for item in value]

    return value


def get_active_user_or_404(db: Session, user_id: uuid.UUID, detail: str) -> User:
    user = db.get(User, user_id)

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
    action = AdminAction(
        id=uuid.uuid4(),
        admin_user_id=admin_user_id,
        action_type=action_type,
        target_game_id=target_game_id,
        target_user_id=target_user_id,
        target_booking_id=target_booking_id,
        target_participant_id=target_participant_id,
        target_venue_id=target_venue_id,
        reason=reason,
        metadata_=serialize_audit_value(metadata),
    )
    db.add(action)
    return action


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
        metadata={
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
    for text_field in ("timezone", "format_label", "environment_type"):
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
        ).all()
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

    participant = db.get(GameParticipant, participant_id)
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
    booking = db.get(Booking, participant.booking_id) if participant.booking_id else None
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
    game = get_official_game_or_404(db, game_id, for_update=True)
    require_official_host_change_allowed(game, action="assigned")

    host = get_active_user_or_404(db, host_request.host_user_id, "Host not found.")
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

    game.host_user_id = host.id
    game.updated_at = datetime.now(timezone.utc)
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

    game.host_user_id = None
    game.updated_at = datetime.now(timezone.utc)
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
