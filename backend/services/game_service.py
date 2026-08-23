"""Shared game database helpers and workflow support used by routes and services."""

import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as BinasciiError
from datetime import date, datetime, timedelta, timezone
from json import JSONDecodeError, dumps, loads
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import and_, exists, func, literal, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from backend.models import (
    Booking,
    Game,
    GameImage,
    GameParticipant,
    ParticipantStatusHistory,
    Payment,
    User,
    Venue,
    VenueImage,
    WaitlistEntry,
)
from backend.schemas.game_schema import (
    GameAvailabilityRead,
    GameCardListRead,
    GameCardRead,
    GameCreate,
    GameDetailRead,
    GameTimeGroupRead,
    GameUpdate,
    MyGameCardRead,
    MyGamesListRead,
)
from backend.services.auth_service import user_is_active_admin
from backend.services.admin_review_service import (
    close_open_content_moderation_case_for_game_lifecycle,
)
from backend.services.r2_storage_service import (
    R2StorageConfigError,
    R2StorageError,
    create_object_read_url,
)
from backend.services.game_notification_service import (
    capture_game_updated_structural_snapshot,
    game_updated_structural_snapshot_changed,
    notify_connected_users_game_updated,
)
from backend.services.game_rules import (
    ACTIVE_JOIN_STATUSES,
    ACTIVE_PAYMENT_HOLD_BOOKING_STATUSES,
    ACTIVE_WAITLIST_STATUSES,
    JOIN_WINDOW_MINUTES,
    OFFICIAL_FORCED_FIELDS,
    OPEN_GAME_STATUSES,
    build_game_conflict_detail,
    game_is_publicly_visible,
    get_join_window_closes_at,
    get_default_host_guest_max,
    normalize_game_lifecycle_fields,
    normalize_official_game_invariants,
    reject_direct_official_host_change,
    reject_official_location_change,
    require_game_not_started,
    validate_game_business_rules,
)
from backend.services.query_pagination import (
    DEFAULT_COLLECTION_LIMIT,
    MAX_COLLECTION_LIMIT,
    bounded_collection_limit,
    bounded_collection_offset,
)

BROWSE_GAME_CARD_DEFAULT_LIMIT = 40
BROWSE_GAME_CARD_MAX_LIMIT = 100
BROWSE_DATE_WINDOW_DAYS = 14
BROWSE_TIMEZONE = "America/Chicago"
MY_GAMES_CARD_DEFAULT_LIMIT = 40
MY_GAMES_CARD_MAX_LIMIT = 100
MY_GAMES_CURSOR_DOMAIN = "games"
MY_GAMES_VALID_VIEWS = {"upcoming", "history"}
MY_GAMES_HISTORY_WINDOW_DAYS = 60
MY_GAMES_CONFIRMED_STATUSES = {"confirmed"}
MY_GAMES_CANCELLED_TYPES = {"host_cancelled", "admin_cancelled"}
COMMUNITY_CONTENT_REVIEW_AUTO_CLOSE_STATUSES = {"completed", "expired"}
COMMUNITY_CONTENT_REVIEW_AUTO_CLOSE_REASONS = {
    "completed": "Community Game was completed before moderation review was completed.",
    "expired": "Community Game expired before moderation review was completed.",
}


def build_game_detail_read(
    game: Game,
    current_user: User | None = None,
) -> GameDetailRead:
    is_host_or_admin = current_user is not None and (
        current_user.id == game.host_user_id or user_is_active_admin(current_user)
    )
    return GameDetailRead(
        id=game.id,
        game_type=game.game_type,
        payment_collection_type=game.payment_collection_type,
        publish_status=game.publish_status,
        game_status=game.game_status,
        public_visibility_status=game.public_visibility_status,
        join_enforcement_status=game.join_enforcement_status,
        title=game.title,
        description=game.description,
        venue_id=game.venue_id,
        venue_name_snapshot=game.venue_name_snapshot,
        address_snapshot=game.address_snapshot,
        city_snapshot=game.city_snapshot,
        state_snapshot=game.state_snapshot,
        neighborhood_snapshot=game.neighborhood_snapshot,
        host_user_id=game.host_user_id if is_host_or_admin else None,
        starts_at=game.starts_at,
        ends_at=game.ends_at,
        starts_on_local=game.starts_on_local,
        timezone=game.timezone,
        format_label=game.format_label,
        game_player_group=game.game_player_group,
        skill_level=game.skill_level,
        environment_type=game.environment_type,
        total_spots=game.total_spots,
        price_per_player_cents=game.price_per_player_cents,
        currency=game.currency,
        minimum_age=game.minimum_age,
        allow_guests=game.allow_guests,
        max_guests_per_booking=game.max_guests_per_booking,
        host_guest_max=game.host_guest_max if is_host_or_admin else 0,
        waitlist_enabled=game.waitlist_enabled,
        is_chat_enabled=game.is_chat_enabled,
        custom_rules_text=game.custom_rules_text,
        custom_cancellation_text=game.custom_cancellation_text,
        game_notes=game.game_notes,
        parking_notes=game.parking_notes,
        cancelled_at=game.cancelled_at,
        cancel_reason=game.cancel_reason,
    )


def get_active_venue_or_404(db: Session, venue_id: uuid.UUID) -> Venue:
    db_venue = db.get(Venue, venue_id)

    if db_venue is None or db_venue.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found.",
        )

    return db_venue


def get_active_user_or_404(db: Session, user_id: uuid.UUID, detail: str) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return db_user


def build_game_address_snapshot(venue: Venue) -> str:
    return venue.address_line_1


def build_game_create_data(
    game: GameCreate,
    admin_user: User,
    venue: Venue,
) -> dict[str, object]:
    request_data = game.model_dump()
    game_type = request_data["game_type"]
    is_official = game_type == "official"
    price_per_player_cents = request_data["price_per_player_cents"]
    host_user_id = request_data.get("host_user_id")

    return {
        "game_type": game_type,
        "payment_collection_type": (
            "in_app"
            if is_official
            else "external_host"
            if price_per_player_cents > 0
            else "none"
        ),
        "publish_status": "published",
        "game_status": "active",
        "public_visibility_status": "visible",
        "join_enforcement_status": "open",
        "title": request_data["title"],
        "description": request_data.get("description"),
        "venue_id": venue.id,
        "venue_name_snapshot": venue.name,
        "address_snapshot": build_game_address_snapshot(venue),
        "city_snapshot": venue.city,
        "state_snapshot": venue.state,
        "neighborhood_snapshot": venue.neighborhood,
        "host_user_id": None if is_official else host_user_id or admin_user.id,
        "created_by_user_id": admin_user.id,
        "starts_at": request_data["starts_at"],
        "ends_at": request_data["ends_at"],
        "timezone": request_data["timezone"],
        "sport_type": "soccer",
        "format_label": request_data["format_label"],
        "game_player_group": request_data["game_player_group"],
        "skill_level": request_data["skill_level"],
        "environment_type": request_data["environment_type"],
        "total_spots": request_data["total_spots"],
        "price_per_player_cents": price_per_player_cents,
        "currency": "USD",
        "minimum_age": None if is_official else 18,
        "allow_guests": request_data["allow_guests"],
        "max_guests_per_booking": request_data["max_guests_per_booking"],
        "host_guest_max": None,
        "waitlist_enabled": request_data["waitlist_enabled"],
        "is_chat_enabled": request_data["is_chat_enabled"],
        "policy_mode": "official_standard" if is_official else "custom_hosted",
        "custom_rules_text": request_data.get("custom_rules_text"),
        "custom_cancellation_text": None,
        "game_notes": request_data.get("game_notes"),
        "parking_notes": request_data.get("parking_notes"),
        "published_at": None,
        "cancelled_at": None,
        "cancelled_by_user_id": None,
        "cancellation_source": None,
        "cancel_reason": None,
        "completed_at": None,
        "completed_by_user_id": None,
    }


def create_game_workflow(db: Session, game: GameCreate, admin_user: User) -> Game:
    venue = get_active_venue_or_404(db, game.venue_id)
    game_data = normalize_official_game_invariants(
        build_game_create_data(game, admin_user, venue), is_create=True
    )

    if game_data["host_user_id"] is not None:
        get_active_user_or_404(db, game_data["host_user_id"], "Host user not found.")

    normalized_game_data = normalize_official_game_invariants(
        normalize_game_lifecycle_fields(game_data), is_create=True
    )
    validate_game_business_rules(normalized_game_data)

    new_game = Game(
        id=uuid.uuid4(),
        **normalized_game_data,
    )

    try:
        db.add(new_game)
        db.commit()
        db.refresh(new_game)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return new_game


def get_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


def get_public_game_or_404(
    db: Session,
    game_id: uuid.UUID,
    current_user: User | None = None,
) -> Game:
    db_game = get_game_or_404(db, game_id)
    if game_is_publicly_visible(db_game):
        return db_game

    if current_user is not None and user_can_view_hidden_game(
        db,
        db_game,
        current_user,
        now=datetime.now(timezone.utc),
    ):
        return db_game

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Game not found.",
    )


def user_can_view_hidden_game(
    db: Session,
    db_game: Game,
    current_user: User,
    *,
    now: datetime,
) -> bool:
    return (
        db_game.host_user_id == current_user.id
        or user_is_active_admin(current_user)
        or user_is_active_participant(db, db_game.id, current_user.id, now=now)
        or user_is_active_booking_buyer(db, db_game.id, current_user.id, now=now)
        or user_is_active_waitlist_member(db, db_game.id, current_user.id)
    )


def user_can_view_hidden_game_roster(
    db: Session,
    db_game: Game,
    current_user: User,
    *,
    now: datetime,
) -> bool:
    return (
        db_game.host_user_id == current_user.id
        or user_is_active_admin(current_user)
        or user_is_active_participant(db, db_game.id, current_user.id, now=now)
    )


def user_is_active_participant(
    db: Session,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    now: datetime,
) -> bool:
    participant_id = db.scalar(
        select(GameParticipant.id)
        .outerjoin(Booking, GameParticipant.booking_id == Booking.id)
        .where(
            GameParticipant.game_id == game_id,
            GameParticipant.user_id == user_id,
            or_(
                GameParticipant.participant_status == "confirmed",
                build_capacity_holding_participant_condition(now),
            ),
        )
        .limit(1)
    )
    return participant_id is not None


def user_is_active_booking_buyer(
    db: Session,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    now: datetime,
) -> bool:
    pending_booking_id = db.scalar(
        select(Booking.id)
        .where(
            Booking.game_id == game_id,
            Booking.buyer_user_id == user_id,
            Booking.booking_status == "pending_payment",
            Booking.expires_at.is_not(None),
            Booking.expires_at > now,
            Booking.payment_status.in_(ACTIVE_PAYMENT_HOLD_BOOKING_STATUSES),
        )
        .limit(1)
    )
    if pending_booking_id is not None:
        return True

    confirmed_booking_id = db.scalar(
        select(Booking.id)
        .join(GameParticipant, GameParticipant.booking_id == Booking.id)
        .where(
            Booking.game_id == game_id,
            Booking.buyer_user_id == user_id,
            Booking.booking_status.in_({"confirmed", "partially_cancelled"}),
            GameParticipant.participant_status == "confirmed",
        )
        .limit(1)
    )
    return confirmed_booking_id is not None


def user_is_active_waitlist_member(
    db: Session,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    waitlist_entry_id = db.scalar(
        select(WaitlistEntry.id)
        .where(
            WaitlistEntry.game_id == game_id,
            WaitlistEntry.user_id == user_id,
            WaitlistEntry.waitlist_status.in_(ACTIVE_WAITLIST_STATUSES),
        )
        .limit(1)
    )
    return waitlist_entry_id is not None


def list_games(
    db: Session,
    *,
    limit: int = DEFAULT_COLLECTION_LIMIT,
    offset: int = 0,
) -> list[Game]:
    games = db.scalars(
        select(Game)
        .where(
            Game.deleted_at.is_(None),
            Game.public_visibility_status == "visible",
        )
        .order_by(Game.starts_at.asc(), Game.created_at.asc(), Game.id.asc())
        .offset(bounded_collection_offset(offset))
        .limit(bounded_collection_limit(limit, max_limit=MAX_COLLECTION_LIMIT))
    ).all()
    return list(games)


def list_browse_game_cards(
    db: Session,
    *,
    starts_on: date | None = None,
    limit: int = BROWSE_GAME_CARD_DEFAULT_LIMIT,
    cursor: str | None = None,
) -> GameCardListRead:
    effective_limit = min(limit, BROWSE_GAME_CARD_MAX_LIMIT)
    now = datetime.now(timezone.utc)
    (
        browse_today,
        minimum_browse_date,
        maximum_browse_date,
        browse_date,
        browse_timezone,
    ) = get_browse_date_context(starts_on, now=now)
    cursor_payload = decode_browse_game_card_cursor(cursor) if cursor else None
    validate_browse_game_card_cursor_context(cursor_payload, starts_on=browse_date)

    eligibility_conditions = build_browse_game_eligibility_conditions(
        browse_date,
        now=now,
    )
    statement = select(Game).where(*eligibility_conditions)

    if cursor_payload is not None:
        statement = statement.where(build_browse_game_card_cursor_filter(cursor_payload))

    statement = statement.order_by(
        Game.starts_at.asc(),
        Game.created_at.asc(),
        Game.id.asc(),
    )

    rows = list(db.scalars(statement.limit(effective_limit + 1)).all())
    page_games = rows[:effective_limit]
    has_more = len(rows) > effective_limit
    time_groups = list_browse_time_groups(
        db,
        browse_date=browse_date,
        browse_timezone=browse_timezone,
        now=now,
    )
    (
        participant_counts_by_game_id,
        primary_game_image_urls_by_game_id,
        primary_venue_image_object_key_by_venue_id,
    ) = load_game_card_metadata(db, page_games, now=now)
    games = [
        build_game_card_read(
            game,
            participant_count=participant_counts_by_game_id.get(game.id, 0),
            primary_game_image_url=primary_game_image_urls_by_game_id.get(game.id),
            primary_venue_image_object_key=primary_venue_image_object_key_by_venue_id.get(
                game.venue_id
            ),
            browse_timezone=browse_timezone,
            now=now,
        )
        for game in page_games
    ]

    next_cursor = None
    if has_more and page_games:
        next_cursor = encode_browse_game_card_cursor(
            game=page_games[-1],
            starts_on=browse_date,
        )

    return GameCardListRead(
        browse_today=browse_today,
        browse_timezone=browse_timezone,
        minimum_browse_date=minimum_browse_date,
        maximum_browse_date=maximum_browse_date,
        browse_date=browse_date,
        time_groups=time_groups,
        games=games,
        next_cursor=next_cursor,
        has_more=has_more,
        limit=effective_limit,
    )


def get_browse_date_context(
    starts_on: date | None,
    *,
    now: datetime,
) -> tuple[date, date, date, date, str]:
    browse_timezone = BROWSE_TIMEZONE
    browse_today = now.astimezone(ZoneInfo(browse_timezone)).date()
    minimum_browse_date = browse_today
    maximum_browse_date = browse_today + timedelta(days=BROWSE_DATE_WINDOW_DAYS - 1)
    requested_date = starts_on or browse_today
    browse_date = min(max(requested_date, minimum_browse_date), maximum_browse_date)

    return (
        browse_today,
        minimum_browse_date,
        maximum_browse_date,
        browse_date,
        browse_timezone,
    )


def build_browse_game_eligibility_conditions(
    browse_date: date,
    *,
    now: datetime,
) -> tuple[object, ...]:
    registration_cutoff = now - timedelta(minutes=JOIN_WINDOW_MINUTES)
    return (
        Game.publish_status == "published",
        Game.deleted_at.is_(None),
        Game.public_visibility_status == "visible",
        Game.join_enforcement_status == "open",
        Game.game_status.in_(OPEN_GAME_STATUSES),
        Game.starts_on_local == browse_date,
        Game.starts_at > registration_cutoff,
    )


def list_browse_time_groups(
    db: Session,
    *,
    browse_date: date,
    browse_timezone: str,
    now: datetime,
) -> list[GameTimeGroupRead]:
    local_hour_expr = func.date_trunc(
        literal("hour"),
        func.timezone(browse_timezone, Game.starts_at),
    )
    group_key_expr = func.to_char(
        local_hour_expr,
        literal("HH24:MI"),
    )
    first_start_expr = func.min(Game.starts_at)
    rows = db.execute(
        select(
            group_key_expr.label("group_key"),
            func.count(Game.id).label("total_games"),
            first_start_expr.label("first_starts_at"),
        )
        .where(*build_browse_game_eligibility_conditions(browse_date, now=now))
        .group_by(group_key_expr)
        .order_by(first_start_expr.asc())
    ).all()

    return [
        GameTimeGroupRead(
            group_key=str(row.group_key),
            total_games=int(row.total_games or 0),
        )
        for row in rows
    ]


def load_game_card_metadata(
    db: Session,
    games: list[Game],
    *,
    now: datetime | None = None,
) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, str], dict[uuid.UUID, str]]:
    if not games:
        return {}, {}, {}

    captured_now = now or datetime.now(timezone.utc)
    game_ids = [game.id for game in games]
    venue_ids = {game.venue_id for game in games if game.venue_id is not None}
    participant_counts_by_game_id: dict[uuid.UUID, int] = {}
    primary_game_image_urls_by_game_id: dict[uuid.UUID, str] = {}
    primary_venue_image_object_key_by_venue_id: dict[uuid.UUID, str] = {}

    for game_id, participant_count in db.execute(
        select(GameParticipant.game_id, func.count(GameParticipant.id))
        .outerjoin(Booking, GameParticipant.booking_id == Booking.id)
        .where(
            GameParticipant.game_id.in_(game_ids),
            build_capacity_holding_participant_condition(captured_now),
        )
        .group_by(GameParticipant.game_id)
    ).all():
        participant_counts_by_game_id[game_id] = int(participant_count or 0)

    for game_id, image_url in db.execute(
        select(GameImage.game_id, GameImage.image_url)
        .where(
            GameImage.game_id.in_(game_ids),
            GameImage.image_status == "active",
            GameImage.is_primary.is_(True),
            GameImage.deleted_at.is_(None),
        )
        .order_by(GameImage.game_id.asc(), GameImage.sort_order.asc())
    ).all():
        primary_game_image_urls_by_game_id.setdefault(game_id, image_url)

    if venue_ids:
        for venue_id, storage_object_key in db.execute(
            select(VenueImage.venue_id, VenueImage.storage_object_key)
            .where(
                VenueImage.venue_id.in_(venue_ids),
                VenueImage.image_status == "active",
                VenueImage.is_primary.is_(True),
                VenueImage.deleted_at.is_(None),
            )
            .order_by(VenueImage.venue_id.asc(), VenueImage.sort_order.asc())
        ).all():
            primary_venue_image_object_key_by_venue_id.setdefault(
                venue_id,
                storage_object_key,
            )

    return (
        participant_counts_by_game_id,
        primary_game_image_urls_by_game_id,
        primary_venue_image_object_key_by_venue_id,
    )


def build_game_card_read(
    game: Game,
    *,
    participant_count: int,
    primary_game_image_url: str | None,
    primary_venue_image_object_key: str | None,
    browse_timezone: str | None = None,
    now: datetime | None = None,
) -> GameCardRead:
    captured_now = now or datetime.now(timezone.utc)
    primary_image_url = primary_game_image_url
    if primary_image_url is None and primary_venue_image_object_key is not None:
        try:
            primary_image_url = create_object_read_url(primary_venue_image_object_key)
        except (R2StorageConfigError, R2StorageError):
            primary_image_url = None

    display_title = build_game_card_display_title(game)
    location_label = build_game_card_location_label(game)
    spots_remaining = max(game.total_spots - participant_count, 0)
    availability_status = get_game_availability_status(
        game,
        occupied_spots=participant_count,
        now=captured_now,
    )
    timezone_name = browse_timezone or game.timezone
    return GameCardRead(
        id=game.id,
        game_type=game.game_type,
        game_status=game.game_status,
        public_visibility_status=game.public_visibility_status,
        join_enforcement_status=game.join_enforcement_status,
        title=game.title,
        display_title=display_title,
        venue_name_snapshot=game.venue_name_snapshot,
        city_snapshot=game.city_snapshot,
        state_snapshot=game.state_snapshot,
        location_label=location_label,
        starts_at=game.starts_at,
        ends_at=game.ends_at,
        starts_on_local=game.starts_on_local,
        time_group_key=get_game_time_group_key(game.starts_at, timezone_name),
        timezone=game.timezone,
        format_label=game.format_label,
        game_player_group=game.game_player_group,
        environment_type=game.environment_type,
        total_spots=game.total_spots,
        price_per_player_cents=game.price_per_player_cents,
        currency=game.currency,
        price_label=format_game_card_price(game.price_per_player_cents, game.currency),
        participant_count=participant_count,
        availability=GameAvailabilityRead(
            status=availability_status,
            occupied_spots=participant_count,
            total_spots=game.total_spots,
            spots_remaining=spots_remaining,
        ),
        registration_closes_at=get_join_window_closes_at(game),
        primary_image_url=primary_image_url,
    )


def build_capacity_holding_participant_condition(now: datetime):
    return or_(
        GameParticipant.participant_status == "confirmed",
        and_(
            GameParticipant.participant_status == "pending_payment",
            GameParticipant.booking_id.is_not(None),
            Booking.booking_status == "pending_payment",
            Booking.expires_at.is_not(None),
            Booking.expires_at > now,
            Booking.payment_status.in_(ACTIVE_PAYMENT_HOLD_BOOKING_STATUSES),
        ),
    )


def get_game_availability_status(
    game: Game,
    *,
    occupied_spots: int,
    now: datetime,
) -> str:
    if game.join_enforcement_status == "paused":
        return "paused"

    spots_remaining = max(game.total_spots - occupied_spots, 0)
    if spots_remaining > 0:
        return "open"

    if game_waitlist_is_accepting(game, now=now):
        return "waitlist_open"

    return "full"


def game_waitlist_is_accepting(game: Game, *, now: datetime) -> bool:
    return (
        game.waitlist_enabled
        and game.publish_status == "published"
        and game.game_status in OPEN_GAME_STATUSES
        and game.public_visibility_status == "visible"
        and game.deleted_at is None
        and game.join_enforcement_status == "open"
        and get_join_window_closes_at(game) > now
    )


def build_game_card_display_title(game: Game) -> str:
    if game.game_type == "official":
        return game.venue_name_snapshot or game.title

    return game.title or game.venue_name_snapshot


def build_game_card_location_label(game: Game) -> str:
    return ", ".join(
        part
        for part in (
            game.city_snapshot,
            game.state_snapshot,
        )
        if part
    )


def get_game_time_group_key(starts_at: datetime, timezone_name: str) -> str:
    local_starts_at = starts_at.astimezone(ZoneInfo(timezone_name))
    return local_starts_at.strftime("%H:00")


def format_game_card_price(cents: int, currency: str) -> str:
    if cents <= 0:
        return "Free"

    dollars = cents / 100
    if cents % 100 == 0:
        return f"${int(dollars)}"

    return f"${dollars:.2f}" if currency == "USD" else f"{dollars:.2f} {currency}"


def encode_browse_game_card_cursor(*, game: Game, starts_on: date) -> str:
    payload = {
        "starts_on": starts_on.isoformat(),
        "starts_at": game.starts_at.isoformat(),
        "created_at": game.created_at.isoformat(),
        "id": str(game.id),
    }
    serialized = dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return urlsafe_b64encode(serialized).decode("ascii")


def decode_browse_game_card_cursor(cursor: str | None) -> dict[str, object] | None:
    if cursor is None:
        return None

    try:
        decoded = urlsafe_b64decode(cursor.encode("ascii"))
        payload = loads(decoded.decode("utf-8"))
    except (BinasciiError, JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    required_keys = {"starts_on", "starts_at", "created_at", "id"}
    if not required_keys.issubset(payload.keys()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    return payload


def validate_browse_game_card_cursor_context(
    cursor_payload: dict[str, object] | None,
    *,
    starts_on: date,
) -> None:
    if cursor_payload is None:
        return

    if cursor_payload["starts_on"] != starts_on.isoformat():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor does not match the current query.",
        )


def build_browse_game_card_cursor_filter(cursor_payload: dict[str, object]):
    starts_at = parse_browse_game_card_cursor_datetime(cursor_payload, "starts_at")
    created_at = parse_browse_game_card_cursor_datetime(cursor_payload, "created_at")
    game_id = parse_browse_game_card_cursor_uuid(cursor_payload)

    return or_(
        Game.starts_at > starts_at,
        and_(Game.starts_at == starts_at, Game.created_at > created_at),
        and_(
            Game.starts_at == starts_at,
            Game.created_at == created_at,
            Game.id > game_id,
        ),
    )


def parse_browse_game_card_cursor_datetime(
    cursor_payload: dict[str, object],
    key: str,
) -> datetime:
    value = cursor_payload[key]
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        ) from exc


def parse_browse_game_card_cursor_uuid(
    cursor_payload: dict[str, object],
) -> uuid.UUID:
    value = cursor_payload["id"]
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        ) from exc


def list_my_game_cards(
    db: Session,
    current_user: User,
    *,
    view: str = "upcoming",
    limit: int = MY_GAMES_CARD_DEFAULT_LIMIT,
    cursor: str | None = None,
) -> MyGamesListRead:
    normalized_view = normalize_my_games_view(view)
    effective_limit = min(limit, MY_GAMES_CARD_MAX_LIMIT)
    sort_direction = "asc" if normalized_view == "upcoming" else "desc"
    cursor_payload = decode_my_games_cursor(cursor) if cursor else None
    validate_my_games_cursor_context(
        cursor_payload,
        view=normalized_view,
        sort_direction=sort_direction,
    )
    now = datetime.now(timezone.utc)
    history_cutoff = now - timedelta(days=MY_GAMES_HISTORY_WINDOW_DAYS)
    is_host_relationship = Game.host_user_id == current_user.id
    has_confirmed_participant = exists().where(
        GameParticipant.game_id == Game.id,
        GameParticipant.user_id == current_user.id,
        GameParticipant.participant_status.in_(MY_GAMES_CONFIRMED_STATUSES),
    )
    latest_participant_status_history = aliased(ParticipantStatusHistory)
    latest_participant_status_history_id = (
        select(latest_participant_status_history.id)
        .where(latest_participant_status_history.participant_id == GameParticipant.id)
        .order_by(
            latest_participant_status_history.created_at.desc(),
            latest_participant_status_history.id.desc(),
        )
        .limit(1)
        .correlate(GameParticipant)
        .scalar_subquery()
    )
    has_confirmed_game_cancellation_proof = exists().where(
        GameParticipant.game_id == Game.id,
        GameParticipant.user_id == current_user.id,
        GameParticipant.participant_status == "cancelled",
        GameParticipant.cancellation_type.in_(MY_GAMES_CANCELLED_TYPES),
        GameParticipant.cancelled_at == Game.cancelled_at,
        exists().where(
            ParticipantStatusHistory.participant_id == GameParticipant.id,
            ParticipantStatusHistory.old_participant_status == "confirmed",
            ParticipantStatusHistory.new_participant_status == "cancelled",
            ParticipantStatusHistory.change_source.in_(("host", "admin")),
            ParticipantStatusHistory.created_at == Game.cancelled_at,
            ParticipantStatusHistory.id == latest_participant_status_history_id,
        ),
    )

    statement = select(Game).where(
        Game.publish_status == "published",
        Game.deleted_at.is_(None),
        Game.game_status != "removed",
    )

    if normalized_view == "upcoming":
        statement = statement.where(
            Game.game_status.in_(OPEN_GAME_STATUSES),
            Game.ends_at > now,
            or_(is_host_relationship, has_confirmed_participant),
        )
    else:
        cancelled_history_condition = and_(
            Game.game_status == "cancelled",
            or_(is_host_relationship, has_confirmed_game_cancellation_proof),
        )
        ended_history_condition = and_(
            Game.game_status != "cancelled",
            Game.ends_at <= now,
            or_(is_host_relationship, has_confirmed_participant),
        )
        statement = statement.where(
            Game.ends_at >= history_cutoff,
            or_(cancelled_history_condition, ended_history_condition),
        )

    if cursor_payload is not None:
        statement = statement.where(
            build_my_games_cursor_filter(
                cursor_payload,
                sort_direction=sort_direction,
            )
        )

    if sort_direction == "asc":
        statement = statement.order_by(
            Game.starts_at.asc(),
            Game.created_at.asc(),
            Game.id.asc(),
        )
    else:
        statement = statement.order_by(
            Game.starts_at.desc(),
            Game.created_at.desc(),
            Game.id.desc(),
        )

    games = list(db.scalars(statement.limit(effective_limit + 1)).all())
    page_games = games[:effective_limit]
    has_more = len(games) > effective_limit
    participants_by_game_id = load_my_games_user_participants(
        db,
        page_games,
        current_user,
    )
    (
        participant_counts_by_game_id,
        primary_game_image_urls_by_game_id,
        primary_venue_image_object_key_by_venue_id,
    ) = load_game_card_metadata(db, page_games, now=now)
    items = [
        build_my_game_card_read(
            game,
            participants_by_game_id.get(game.id),
            current_user=current_user,
            participant_count=participant_counts_by_game_id.get(game.id, 0),
            primary_game_image_url=primary_game_image_urls_by_game_id.get(game.id),
            primary_venue_image_object_key=primary_venue_image_object_key_by_venue_id.get(
                game.venue_id
            ),
            bucket=normalized_view,
        )
        for game in page_games
    ]

    next_cursor = None
    if has_more and page_games:
        next_cursor = encode_my_games_cursor(
            game=page_games[-1],
            view=normalized_view,
            sort_direction=sort_direction,
        )

    return MyGamesListRead(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
        limit=effective_limit,
    )


def load_my_games_user_participants(
    db: Session,
    games: list[Game],
    current_user: User,
) -> dict[uuid.UUID, GameParticipant]:
    if not games:
        return {}

    game_ids = [game.id for game in games]
    participants = list(
        db.scalars(
            select(GameParticipant).where(
                GameParticipant.game_id.in_(game_ids),
                GameParticipant.user_id == current_user.id,
            )
        ).all()
    )
    participants.sort(key=get_my_games_participant_priority)
    participants_by_game_id: dict[uuid.UUID, GameParticipant] = {}
    for participant in participants:
        participants_by_game_id.setdefault(participant.game_id, participant)

    return participants_by_game_id


def get_my_games_participant_priority(participant: GameParticipant) -> tuple[int, datetime]:
    if participant.participant_status == "confirmed":
        return (0, participant.created_at)
    if (
        participant.participant_status == "cancelled"
        and participant.cancellation_type in MY_GAMES_CANCELLED_TYPES
    ):
        return (1, participant.created_at)

    return (2, participant.created_at)


def build_my_game_card_read(
    game: Game,
    participant: GameParticipant | None,
    *,
    current_user: User,
    participant_count: int,
    primary_game_image_url: str | None,
    primary_venue_image_object_key: str | None,
    bucket: str,
) -> MyGameCardRead:
    is_host = game.host_user_id == current_user.id
    status_label, status_tone = get_my_game_status(game, participant, is_host, bucket)

    return MyGameCardRead(
        bucket=bucket,
        game=build_game_card_read(
            game,
            participant_count=participant_count,
            primary_game_image_url=primary_game_image_url,
            primary_venue_image_object_key=primary_venue_image_object_key,
        ),
        is_host=is_host,
        participant_id=participant.id if participant is not None else None,
        participant_status=participant.participant_status if participant is not None else None,
        cancellation_type=participant.cancellation_type if participant is not None else None,
        status_label=status_label,
        status_tone=status_tone,
    )


def get_my_game_status(
    game: Game,
    participant: GameParticipant | None,
    is_host: bool,
    bucket: str,
) -> tuple[str, str]:
    if game.game_status == "cancelled":
        return "Cancelled", "cancelled"

    if bucket == "history":
        return ("Hosted", "hosted") if is_host else ("Completed", "completed")

    if is_host:
        return "Hosting", "hosting"

    return "Confirmed", "confirmed"


def normalize_my_games_view(view: str) -> str:
    normalized_view = view.strip().lower()
    if normalized_view not in MY_GAMES_VALID_VIEWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="view must be 'upcoming' or 'history'.",
        )

    return normalized_view


def encode_my_games_cursor(
    *,
    game: Game,
    view: str,
    sort_direction: str,
) -> str:
    payload = {
        "domain": MY_GAMES_CURSOR_DOMAIN,
        "view": view,
        "sort_direction": sort_direction,
        "starts_at": game.starts_at.isoformat(),
        "created_at": game.created_at.isoformat(),
        "id": str(game.id),
    }
    serialized = dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return urlsafe_b64encode(serialized).decode("ascii")


def decode_my_games_cursor(cursor: str | None) -> dict[str, object] | None:
    if cursor is None:
        return None

    try:
        decoded = urlsafe_b64decode(cursor.encode("ascii"))
        payload = loads(decoded.decode("utf-8"))
    except (BinasciiError, JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    required_keys = {
        "domain",
        "view",
        "sort_direction",
        "starts_at",
        "created_at",
        "id",
    }
    if not required_keys.issubset(payload.keys()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    return payload


def validate_my_games_cursor_context(
    cursor_payload: dict[str, object] | None,
    *,
    view: str,
    sort_direction: str,
) -> None:
    if cursor_payload is None:
        return

    if (
        cursor_payload["view"] != view
        or cursor_payload["domain"] != MY_GAMES_CURSOR_DOMAIN
        or cursor_payload["sort_direction"] != sort_direction
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor does not match the current query.",
        )


def build_my_games_cursor_filter(
    cursor_payload: dict[str, object],
    *,
    sort_direction: str,
):
    starts_at = parse_browse_game_card_cursor_datetime(cursor_payload, "starts_at")
    created_at = parse_browse_game_card_cursor_datetime(cursor_payload, "created_at")
    game_id = parse_browse_game_card_cursor_uuid(cursor_payload)

    if sort_direction == "asc":
        return or_(
            Game.starts_at > starts_at,
            and_(Game.starts_at == starts_at, Game.created_at > created_at),
            and_(
                Game.starts_at == starts_at,
                Game.created_at == created_at,
                Game.id > game_id,
            ),
        )

    return or_(
        Game.starts_at < starts_at,
        and_(Game.starts_at == starts_at, Game.created_at < created_at),
        and_(
            Game.starts_at == starts_at,
            Game.created_at == created_at,
            Game.id < game_id,
        ),
    )


def update_game_workflow(
    db: Session,
    game_id: uuid.UUID,
    game_update: GameUpdate,
    admin_user: User | None = None,
) -> Game:
    db_game = get_game_or_404(db, game_id)
    old_game_status = db_game.game_status

    update_data = game_update.model_dump(exclude_unset=True)
    reject_official_location_change(db_game, update_data)
    reject_direct_official_host_change(db_game, update_data)

    now = datetime.now(timezone.utc)
    require_game_not_started(db_game, now, "Games cannot be edited after start time.")
    structural_snapshot_before = capture_game_updated_structural_snapshot(db_game)

    if "format_label" in update_data and "host_guest_max" not in update_data:
        update_data["host_guest_max"] = get_default_host_guest_max(
            update_data["format_label"]
        )

    effective_game_data = {
        "game_type": update_data.get("game_type", db_game.game_type),
        "payment_collection_type": update_data.get(
            "payment_collection_type", db_game.payment_collection_type
        ),
        "publish_status": update_data.get("publish_status", db_game.publish_status),
        "game_status": update_data.get("game_status", db_game.game_status),
        "public_visibility_status": update_data.get(
            "public_visibility_status",
            db_game.public_visibility_status,
        ),
        "join_enforcement_status": update_data.get(
            "join_enforcement_status",
            db_game.join_enforcement_status,
        ),
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
        "host_user_id": update_data.get("host_user_id", db_game.host_user_id),
        "created_by_user_id": update_data.get(
            "created_by_user_id", db_game.created_by_user_id
        ),
        "starts_at": update_data.get("starts_at", db_game.starts_at),
        "ends_at": update_data.get("ends_at", db_game.ends_at),
        "timezone": update_data.get("timezone", db_game.timezone),
        "sport_type": update_data.get("sport_type", db_game.sport_type),
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
        "currency": update_data.get("currency", db_game.currency),
        "minimum_age": update_data.get("minimum_age", db_game.minimum_age),
        "allow_guests": update_data.get("allow_guests", db_game.allow_guests),
        "max_guests_per_booking": update_data.get(
            "max_guests_per_booking", db_game.max_guests_per_booking
        ),
        "host_guest_max": update_data.get("host_guest_max", db_game.host_guest_max),
        "waitlist_enabled": update_data.get(
            "waitlist_enabled", db_game.waitlist_enabled
        ),
        "is_chat_enabled": update_data.get(
            "is_chat_enabled", db_game.is_chat_enabled
        ),
        "policy_mode": update_data.get("policy_mode", db_game.policy_mode),
        "custom_rules_text": update_data.get(
            "custom_rules_text", db_game.custom_rules_text
        ),
        "custom_cancellation_text": update_data.get(
            "custom_cancellation_text", db_game.custom_cancellation_text
        ),
        "game_notes": update_data.get("game_notes", db_game.game_notes),
        "parking_notes": update_data.get("parking_notes", db_game.parking_notes),
        "published_at": update_data.get("published_at", db_game.published_at),
        "cancelled_at": update_data.get("cancelled_at", db_game.cancelled_at),
        "cancelled_by_user_id": update_data.get(
            "cancelled_by_user_id", db_game.cancelled_by_user_id
        ),
        "cancellation_source": update_data.get(
            "cancellation_source",
            db_game.cancellation_source,
        ),
        "cancel_reason": update_data.get("cancel_reason", db_game.cancel_reason),
        "completed_at": update_data.get("completed_at", db_game.completed_at),
        "completed_by_user_id": update_data.get(
            "completed_by_user_id", db_game.completed_by_user_id
        ),
    }
    effective_game_data = normalize_official_game_invariants(
        normalize_game_lifecycle_fields(effective_game_data, db_game)
    )
    validate_game_business_rules(effective_game_data)

    for lifecycle_field in (
        "published_at",
        "cancelled_at",
        "cancelled_by_user_id",
        "cancellation_source",
        "cancel_reason",
        "completed_at",
        "completed_by_user_id",
    ):
        update_data[lifecycle_field] = effective_game_data[lifecycle_field]

    if "host_guest_max" in update_data:
        update_data["host_guest_max"] = effective_game_data["host_guest_max"]
    if effective_game_data["game_type"] == "official":
        for field_name in OFFICIAL_FORCED_FIELDS:
            if (
                field_name in update_data
                or getattr(db_game, field_name) != effective_game_data[field_name]
            ):
                update_data[field_name] = effective_game_data[field_name]
    update_data["starts_on_local"] = effective_game_data["starts_on_local"]

    for field_name, field_value in update_data.items():
        setattr(db_game, field_name, field_value)

    db_game.updated_at = now
    if (
        db_game.game_type == "community"
        and old_game_status != db_game.game_status
        and db_game.game_status in COMMUNITY_CONTENT_REVIEW_AUTO_CLOSE_STATUSES
    ):
        close_open_content_moderation_case_for_game_lifecycle(
            db,
            game_id=db_game.id,
            closure_outcome="no_action_needed",
            closure_reason=COMMUNITY_CONTENT_REVIEW_AUTO_CLOSE_REASONS[
                db_game.game_status
            ],
            lifecycle_action=f"game_{db_game.game_status}",
            trigger_actor_type="admin" if admin_user is not None else "system",
            trigger_actor_user_id=admin_user.id if admin_user is not None else None,
            closed_by_user_id=admin_user.id if admin_user is not None else None,
            previous_game_status=old_game_status,
            new_game_status=db_game.game_status,
            closed_at=now,
        )
    if game_updated_structural_snapshot_changed(structural_snapshot_before, db_game):
        notify_connected_users_game_updated(
            db,
            db_game=db_game,
            actor_user_id=None,
            event_at=now,
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

    return db_game


def delete_game_workflow(
    db: Session,
    game_id: uuid.UUID,
    admin_user: User,
) -> Game:
    db_game = get_game_or_404(db, game_id)

    if db_game.game_type == "official":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Official games must be cancelled instead of deleted.",
        )

    now = datetime.now(timezone.utc)
    old_game_status = db_game.game_status
    db_game.updated_at = now
    db_game.deleted_at = now

    try:
        db.add(db_game)
        if db_game.game_type == "community":
            close_open_content_moderation_case_for_game_lifecycle(
                db,
                game_id=db_game.id,
                closure_outcome="enforcement_applied",
                closure_reason=(
                    "Community Game was deleted by an admin before moderation "
                    "review was completed."
                ),
                lifecycle_action="admin_soft_deleted",
                trigger_actor_type="admin",
                trigger_actor_user_id=admin_user.id,
                closed_by_user_id=admin_user.id,
                previous_game_status=old_game_status,
                new_game_status=old_game_status,
                closed_at=now,
            )
        db.commit()
        db.refresh(db_game)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return db_game


def count_non_host_participants(
    db: Session, game_id: uuid.UUID, participant_statuses: set[str]
) -> int:
    return db.scalar(
        select(func.count())
        .select_from(GameParticipant)
        .where(
            GameParticipant.game_id == game_id,
            GameParticipant.participant_type != "host",
            GameParticipant.participant_status.in_(participant_statuses),
        )
    ) or 0


def game_has_paid_booking_payment(db: Session, game_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(Payment.id)
            .join(Booking, Payment.booking_id == Booking.id)
            .where(
                Booking.game_id == game_id,
                Payment.payment_type == "booking",
                Payment.payment_status == "succeeded",
            )
            .limit(1)
        )
        is not None
    )


def get_existing_active_participant(
    db: Session, game_id: uuid.UUID, user_id: uuid.UUID
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


def count_roster_players(
    db: Session,
    game_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> int:
    captured_now = now or datetime.now(timezone.utc)
    return db.scalar(
        select(func.count())
        .select_from(GameParticipant)
        .outerjoin(Booking, GameParticipant.booking_id == Booking.id)
        .where(
            GameParticipant.game_id == game_id,
            build_capacity_holding_participant_condition(captured_now),
        )
    ) or 0


def get_next_roster_order(db: Session, game_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.max(GameParticipant.roster_order)).where(
                GameParticipant.game_id == game_id,
                GameParticipant.participant_status == "confirmed",
            )
        )
        or 0
    ) + 1


def get_existing_active_waitlist_entry(
    db: Session, game_id: uuid.UUID, user_id: uuid.UUID
) -> WaitlistEntry | None:
    return db.scalars(
        select(WaitlistEntry)
        .where(
            WaitlistEntry.game_id == game_id,
            WaitlistEntry.user_id == user_id,
            WaitlistEntry.waitlist_status.in_(ACTIVE_WAITLIST_STATUSES),
        )
        .limit(1)
    ).first()


def get_next_waitlist_position(db: Session, game_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.max(WaitlistEntry.position)).where(
                WaitlistEntry.game_id == game_id,
                WaitlistEntry.waitlist_status == "active",
            )
        )
        or 0
    ) + 1


def get_booking_participants(
    db: Session,
    game_id: uuid.UUID,
    booking_id: uuid.UUID,
    participant_statuses: set[str],
) -> list[GameParticipant]:
    return list(
        db.scalars(
            select(GameParticipant)
            .where(
                GameParticipant.game_id == game_id,
                GameParticipant.booking_id == booking_id,
                GameParticipant.participant_status.in_(participant_statuses),
            )
            .order_by(
                GameParticipant.participant_type.desc(),
                GameParticipant.roster_order.asc().nulls_last(),
                GameParticipant.joined_at.asc(),
            )
        ).all()
    )


def list_public_game_participants(
    db: Session,
    game_id: uuid.UUID,
    current_user: User | None = None,
    *,
    limit: int = DEFAULT_COLLECTION_LIMIT,
    offset: int = 0,
) -> list[GameParticipant]:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )
    if game_is_publicly_visible(db_game):
        pass
    elif current_user is None or not user_can_view_hidden_game_roster(
        db,
        db_game,
        current_user,
        now=datetime.now(timezone.utc),
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return list(
        db.scalars(
            select(GameParticipant)
            .where(GameParticipant.game_id == game_id)
            .order_by(
                GameParticipant.roster_order.asc().nulls_last(),
                GameParticipant.created_at.asc(),
                GameParticipant.id.asc(),
            )
            .offset(bounded_collection_offset(offset))
            .limit(bounded_collection_limit(limit, max_limit=MAX_COLLECTION_LIMIT))
        ).all()
    )


def list_public_game_participant_counts(
    db: Session,
    *,
    limit: int = DEFAULT_COLLECTION_LIMIT,
    offset: int = 0,
) -> list[dict[str, object]]:
    now = datetime.now(timezone.utc)
    rows = db.execute(
        select(
            GameParticipant.game_id,
            func.count(GameParticipant.id).label("participant_count"),
        )
        .outerjoin(Booking, GameParticipant.booking_id == Booking.id)
        .join(Game, GameParticipant.game_id == Game.id)
        .where(build_capacity_holding_participant_condition(now))
        .where(
            Game.deleted_at.is_(None),
            Game.public_visibility_status == "visible",
        )
        .group_by(GameParticipant.game_id)
        .order_by(GameParticipant.game_id.asc())
        .offset(bounded_collection_offset(offset))
        .limit(bounded_collection_limit(limit, max_limit=MAX_COLLECTION_LIMIT))
    ).all()

    return [
        {"game_id": row.game_id, "participant_count": row.participant_count}
        for row in rows
    ]


def list_current_user_game_participants(
    db: Session,
    current_user: User,
    *,
    limit: int = DEFAULT_COLLECTION_LIMIT,
    offset: int = 0,
) -> list[GameParticipant]:
    return list(
        db.scalars(
            select(GameParticipant)
            .where(GameParticipant.user_id == current_user.id)
            .order_by(
                GameParticipant.joined_at.desc(),
                GameParticipant.created_at.desc(),
                GameParticipant.id.desc(),
            )
            .offset(bounded_collection_offset(offset))
            .limit(bounded_collection_limit(limit, max_limit=MAX_COLLECTION_LIMIT))
        ).all()
    )


def build_booking_participants(
    db_game: Game,
    booking: Booking,
    joining_user: User,
    display_name: str,
    guest_count: int,
    now: datetime,
    *,
    participant_status: str,
    first_roster_order: int | None,
) -> list[GameParticipant]:
    is_confirmed = participant_status == "confirmed"
    participants = [
        GameParticipant(
            id=uuid.uuid4(),
            game_id=db_game.id,
            booking_id=booking.id,
            participant_type="registered_user",
            user_id=joining_user.id,
            display_name_snapshot=display_name,
            participant_status=participant_status,
            attendance_status="unknown" if is_confirmed else "not_applicable",
            cancellation_type="none",
            price_cents=db_game.price_per_player_cents,
            currency=db_game.currency,
            roster_order=first_roster_order,
            joined_at=now,
            confirmed_at=now if is_confirmed else None,
        )
    ]

    for index in range(guest_count):
        roster_order = first_roster_order + index + 1 if first_roster_order else None
        guest_name = f"Guest {index + 1}"
        participants.append(
            GameParticipant(
                id=uuid.uuid4(),
                game_id=db_game.id,
                booking_id=booking.id,
                participant_type="guest",
                user_id=None,
                guest_of_user_id=joining_user.id,
                guest_name=guest_name,
                display_name_snapshot=f"{display_name} guest {index + 1}",
                participant_status=participant_status,
                attendance_status="unknown" if is_confirmed else "not_applicable",
                cancellation_type="none",
                price_cents=db_game.price_per_player_cents,
                currency=db_game.currency,
                roster_order=roster_order,
                joined_at=now,
                confirmed_at=now if is_confirmed else None,
            )
        )

    return participants


def sync_game_capacity_status(db: Session, db_game: Game) -> None:
    db.flush()
