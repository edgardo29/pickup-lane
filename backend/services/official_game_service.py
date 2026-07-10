import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameParticipant,
    Payment,
    User,
    Venue,
)
from backend.schemas.admin_official_game_schema import (
    AdminOfficialGameCreate,
    AdminOfficialGameUpdate,
    AdminOfficialGameVenuePayload,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.game_rules import (
    OFFICIAL_FORCED_FIELDS,
    OPEN_GAME_STATUSES,
    build_game_conflict_detail,
    normalize_game_lifecycle_fields,
    normalize_official_game_invariants,
    validate_game_business_rules,
)
from backend.services.game_service import sync_game_capacity_status
from backend.services.game_credit_service import release_reserved_game_credits
from backend.services.payment_rules import PENDING_PAYMENT_STATUSES
from backend.services.status_history_service import (
    add_participant_status_history_if_changed,
)
from backend.services.venue_service import find_matching_active_venue

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
        "game_status": "active",
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

    record_admin_action(
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
                Payment.payment_status.in_(PENDING_PAYMENT_STATUSES),
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
        add_participant_status_history_if_changed(
            db,
            participant,
            old_participant_status=old_status,
            old_attendance_status=old_attendance_status,
            changed_by_user_id=admin_user_id,
            change_source="admin",
            reason=reason or "Official game details changed by admin.",
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
        or game.game_status not in OPEN_GAME_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published active official games can be edited.",
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

    record_admin_action(
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
