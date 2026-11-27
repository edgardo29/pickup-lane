"""Community game host-edit workflow and venue handling."""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Game, User, Venue
from backend.schemas.game_schema import GameHostEdit
from backend.services.community_game_detail_service import (
    community_game_has_host_payment_method,
)
from backend.services.game_notification_service import (
    capture_game_updated_structural_snapshot,
    game_updated_changed_field_labels,
    game_updated_structural_snapshot_changed,
    notify_connected_users_game_updated,
)
from backend.services.game_rules import (
    ACTIVE_PLAYER_STATUSES,
    HOST_EDITABLE_GAME_STATUSES,
    LOCATION_FIELDS,
    MAJOR_HOST_EDIT_FIELDS,
    NON_NULL_HOST_EDIT_FIELDS,
    RESERVED_PLAYER_STATUSES,
    build_game_conflict_detail,
    ensure_timezone,
    get_default_host_guest_max,
    host_edit_field_changed,
    normalize_game_lifecycle_fields,
    require_community_start_within_schedule_window,
    require_game_not_started,
    validate_game_business_rules,
)
from backend.services.game_service import count_game_participants
from backend.services.moderation_surfacing_service import surface_community_game_text
from backend.services.venue_service import find_or_create_facility_venue


def create_host_edit_venue(
    db: Session, db_game: Game, game_update: GameHostEdit
) -> Venue:
    venue_name = (game_update.venue_name or "").strip()
    address_line_1 = (game_update.address_line_1 or "").strip()
    city = (game_update.city or "").strip()
    state_value = (game_update.state or "").strip()
    postal_code = (game_update.postal_code or "").strip()
    neighborhood = (game_update.neighborhood or "").strip() or None

    if not all([venue_name, address_line_1, city, state_value, postal_code]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Location edits require venue name, street, city, state, and "
                "postal code."
            ),
        )

    return find_or_create_facility_venue(
        db,
        name=venue_name,
        address_line_1=address_line_1,
        city=city,
        state=state_value,
        postal_code=postal_code,
        country_code="US",
        neighborhood=neighborhood,
        new_venue_fields={
            "venue_status": "approved",
            "created_by_user_id": db_game.host_user_id,
            "approved_by_user_id": db_game.host_user_id,
            "approved_at": datetime.now(UTC),
            "is_active": True,
        },
    )


def build_host_edit_address_snapshot(game_update: GameHostEdit) -> str:
    state_line = " ".join(
        value
        for value in [
            (game_update.state or "").strip(),
            (game_update.postal_code or "").strip(),
        ]
        if value
    )
    city_line = ", ".join(
        value for value in [(game_update.city or "").strip(), state_line] if value
    )
    return ", ".join(
        value
        for value in [(game_update.address_line_1 or "").strip(), city_line]
        if value
    )


# The fields that identify a facility. Neighborhood is descriptive: changing
# it only relabels the game and is not a location change.
FACILITY_FIELDS = LOCATION_FIELDS - {"neighborhood"}


def host_edit_changes_location(
    db: Session, db_game: Game, game_update: GameHostEdit
) -> bool:
    update_data = game_update.model_dump(exclude_unset=True)

    if not FACILITY_FIELDS.intersection(update_data):
        return False

    db_venue = db.get(Venue, db_game.venue_id)
    existing_values = {
        "venue_name": (
            db_venue.name if db_venue is not None else db_game.venue_name_snapshot
        ),
        "address_line_1": (
            db_venue.address_line_1
            if db_venue is not None
            else db_game.address_snapshot.split(",")[0].strip()
        ),
        "city": db_venue.city if db_venue is not None else db_game.city_snapshot,
        "state": db_venue.state if db_venue is not None else db_game.state_snapshot,
        "postal_code": db_venue.postal_code if db_venue is not None else "",
    }

    for field_name in FACILITY_FIELDS:
        if field_name not in update_data:
            continue

        if (update_data[field_name] or "").strip() != existing_values[field_name]:
            return True

    return False


def host_edit_game_workflow(
    db: Session,
    game_id: uuid.UUID,
    game_update: GameHostEdit,
    current_user: User,
) -> Game:
    # Lock the game so a player joining at the same moment waits, and the
    # after-join limits below see the roster as it is when this edit saves.
    db_game = db.scalars(
        select(Game).where(Game.id == game_id).with_for_update()
    ).first()

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    if db_game.game_type != "community":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only community games can be edited by hosts.",
        )

    if db_game.host_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the game host can edit this game.",
        )

    if (
        db_game.publish_status != "published"
        or db_game.game_status not in HOST_EDITABLE_GAME_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published active games can be edited.",
        )

    now = datetime.now(UTC)
    require_game_not_started(db_game, now, "Games cannot be edited after start time.")
    structural_snapshot_before = capture_game_updated_structural_snapshot(db_game)

    update_data = game_update.model_dump(exclude_unset=True)
    if "format_label" in update_data:
        update_data["host_guest_max"] = get_default_host_guest_max(
            update_data["format_label"]
        )

    if any(
        field in update_data and update_data[field] is None
        for field in NON_NULL_HOST_EDIT_FIELDS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host edit fields cannot be null.",
        )

    location_changed = host_edit_changes_location(db, db_game, game_update)
    # Guests the host adds to their own game do not lock it; every place taken,
    # the host's party included, still limits how far capacity can drop.
    active_player_count = count_game_participants(
        db, db_game, ACTIVE_PLAYER_STATUSES, include_host_party=False
    )
    taken_place_count = count_game_participants(
        db, db_game, RESERVED_PLAYER_STATUSES, include_host_party=True
    )

    if active_player_count > 0:
        changed_major_fields = [
            field_name
            for field_name in MAJOR_HOST_EDIT_FIELDS
            if field_name in update_data
            and host_edit_field_changed(db_game, field_name, update_data[field_name])
        ]

        if location_changed or changed_major_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Date, time, location, format, indoor/outdoor, and price "
                    "cannot be changed after players have joined."
                ),
            )

        if (
            "total_spots" in update_data
            and update_data["total_spots"] < db_game.total_spots
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Capacity can only be increased after players have joined.",
            )

    effective_starts_at = ensure_timezone(
        update_data.get("starts_at", db_game.starts_at)
    )
    effective_ends_at = ensure_timezone(update_data.get("ends_at", db_game.ends_at))

    if effective_starts_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game start time must be in the future.",
        )

    if effective_ends_at <= effective_starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ends_at must be greater than starts_at.",
        )

    if host_edit_field_changed(db_game, "starts_at", effective_starts_at):
        require_community_start_within_schedule_window(
            effective_starts_at, db_game.timezone, now
        )

    if "total_spots" in update_data and update_data["total_spots"] < taken_place_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Capacity cannot drop below the places already taken.",
        )

    if location_changed:
        new_venue = create_host_edit_venue(db, db_game, game_update)
        update_data["venue_id"] = new_venue.id
        update_data["venue_name_snapshot"] = new_venue.name
        update_data["address_snapshot"] = build_host_edit_address_snapshot(game_update)
        update_data["city_snapshot"] = new_venue.city
        update_data["state_snapshot"] = new_venue.state
        update_data["neighborhood_snapshot"] = new_venue.neighborhood
        update_data["title"] = (
            f"{new_venue.name} {update_data.get('format_label', db_game.format_label)}"
        )
    elif (
        "format_label" in update_data
        and update_data["format_label"] != db_game.format_label
    ):
        update_data["title"] = (
            f"{db_game.venue_name_snapshot} {update_data['format_label']}"
        )

    # As when publishing, a paid community game has players pay the host and a
    # free one collects nothing, so a price change can turn either into the other.
    if "price_per_player_cents" in update_data:
        update_data["payment_collection_type"] = (
            "external_host" if update_data["price_per_player_cents"] > 0 else "none"
        )
        # Players of a paid game pay the host directly, so the host's payment
        # methods must be saved first (Create Game, Section 3.1).
        if update_data[
            "price_per_player_cents"
        ] > 0 and not community_game_has_host_payment_method(db, game_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Add a host payment method before charging players.",
            )

    # Game Details shows the description, which publishing fills from the game
    # notes, so edited notes replace it too.
    if "game_notes" in update_data:
        update_data["description"] = update_data["game_notes"]

    # The neighborhood describes where the game is without identifying the
    # facility, so the host's entry is kept even when a venue is reused.
    if "neighborhood" in game_update.model_fields_set:
        update_data["neighborhood_snapshot"] = (
            game_update.neighborhood or ""
        ).strip() or None

    effective_game_data = {
        "game_type": db_game.game_type,
        "payment_collection_type": update_data.get(
            "payment_collection_type", db_game.payment_collection_type
        ),
        "publish_status": db_game.publish_status,
        "game_status": db_game.game_status,
        "public_visibility_status": db_game.public_visibility_status,
        "join_enforcement_status": db_game.join_enforcement_status,
        "title": update_data.get("title", db_game.title),
        "description": update_data.get("description", db_game.description),
        "venue_id": update_data.get("venue_id", db_game.venue_id),
        "venue_name_snapshot": update_data.get(
            "venue_name_snapshot", db_game.venue_name_snapshot
        ),
        "address_snapshot": update_data.get(
            "address_snapshot", db_game.address_snapshot
        ),
        "city_snapshot": update_data.get("city_snapshot", db_game.city_snapshot),
        "state_snapshot": update_data.get("state_snapshot", db_game.state_snapshot),
        "neighborhood_snapshot": update_data.get(
            "neighborhood_snapshot", db_game.neighborhood_snapshot
        ),
        "host_user_id": db_game.host_user_id,
        "created_by_user_id": db_game.created_by_user_id,
        "starts_at": effective_starts_at,
        "ends_at": effective_ends_at,
        "timezone": db_game.timezone,
        "sport_type": db_game.sport_type,
        "format_label": update_data.get("format_label", db_game.format_label),
        "game_player_group": update_data.get(
            "game_player_group", db_game.game_player_group
        ),
        "skill_level": update_data.get("skill_level", db_game.skill_level),
        "environment_type": update_data.get(
            "environment_type", db_game.environment_type
        ),
        "total_spots": update_data.get("total_spots", db_game.total_spots),
        "price_per_player_cents": update_data.get(
            "price_per_player_cents", db_game.price_per_player_cents
        ),
        "currency": db_game.currency,
        "allow_guests": db_game.allow_guests,
        "max_guests_per_booking": db_game.max_guests_per_booking,
        "host_guest_max": update_data.get("host_guest_max", db_game.host_guest_max),
        "waitlist_enabled": db_game.waitlist_enabled,
        "is_chat_enabled": db_game.is_chat_enabled,
        "policy_mode": db_game.policy_mode,
        "custom_rules_text": update_data.get(
            "custom_rules_text", db_game.custom_rules_text
        ),
        "custom_cancellation_text": db_game.custom_cancellation_text,
        "game_notes": update_data.get("game_notes", db_game.game_notes),
        "parking_notes": update_data.get("parking_notes", db_game.parking_notes),
        "published_at": db_game.published_at,
        "cancelled_at": db_game.cancelled_at,
        "cancelled_by_user_id": db_game.cancelled_by_user_id,
        "cancellation_source": db_game.cancellation_source,
        "cancel_reason": db_game.cancel_reason,
        "completed_at": db_game.completed_at,
        "completed_by_user_id": db_game.completed_by_user_id,
    }
    effective_game_data = normalize_game_lifecycle_fields(effective_game_data, db_game)
    validate_game_business_rules(effective_game_data)
    if "host_guest_max" in update_data:
        update_data["host_guest_max"] = effective_game_data["host_guest_max"]
    update_data["starts_on_local"] = effective_game_data["starts_on_local"]

    for field_name, field_value in update_data.items():
        if field_name in LOCATION_FIELDS:
            continue

        setattr(db_game, field_name, field_value)

    db_game.updated_at = now
    if game_updated_structural_snapshot_changed(structural_snapshot_before, db_game):
        notify_connected_users_game_updated(
            db,
            db_game=db_game,
            actor_user_id=current_user.id,
            event_at=now,
            changed_field_labels=game_updated_changed_field_labels(
                structural_snapshot_before,
                db_game,
            ),
        )

    try:
        db.add(db_game)
        db.commit()
        db.refresh(db_game)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    surface_community_game_text(db, game_id=db_game.id)
    return db_game
