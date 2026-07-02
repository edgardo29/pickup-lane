import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as BinasciiError
from datetime import date, datetime
from json import JSONDecodeError, dumps, loads

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameCredit,
    GameCreditUsage,
    GameParticipant,
    Payment,
    Refund,
    VenueImage,
    WaitlistEntry,
)
from backend.schemas.admin_official_game_schema import (
    AdminOfficialGameCardRead,
    AdminOfficialGameListRead,
    AdminOfficialGameMoneyRead,
)
from backend.services.r2_storage_service import (
    R2StorageConfigError,
    R2StorageError,
    create_object_read_url,
)
from backend.services.game_participant_rules import ACTIVE_ROSTER_PARTICIPANT_STATUSES
from backend.services.game_rules import OPEN_GAME_STATUSES
from backend.services.official_game_service import get_official_game_or_404

OFFICIAL_GAME_LIST_DEFAULT_LIMIT = 24
OFFICIAL_GAME_LIST_MAX_LIMIT = 100
OFFICIAL_GAME_LIST_VALID_VIEWS = {"active", "completed", "cancelled"}
OFFICIAL_GAME_LIST_VIEW_STATUSES = {
    "active": OPEN_GAME_STATUSES,
    "completed": {"completed"},
    "cancelled": {"cancelled", "abandoned"},
}
OFFICIAL_GAME_LIST_ASCENDING_VIEWS = {"active"}
OFFICIAL_GAME_LIST_ISSUE_MISSING_HOST = "missing_host"
OFFICIAL_GAME_LIST_ISSUE_MISSING_PHOTO = "missing_photo"


def list_official_games(
    db: Session,
    *,
    view: str = "active",
    search: str | None = None,
    starts_on: date | None = None,
    limit: int = OFFICIAL_GAME_LIST_DEFAULT_LIMIT,
    cursor: str | None = None,
) -> AdminOfficialGameListRead:
    normalized_view = normalize_official_game_list_view(view)
    normalized_search = normalize_official_game_list_search(search)
    effective_limit = min(limit, OFFICIAL_GAME_LIST_MAX_LIMIT)
    sort_direction = get_official_game_list_sort_direction(normalized_view)
    cursor_payload = decode_official_game_list_cursor(cursor) if cursor else None
    validate_official_game_list_cursor_context(
        cursor_payload,
        view=normalized_view,
        search=normalized_search,
        starts_on=starts_on,
        sort_direction=sort_direction,
    )

    statement = select(Game).where(
        Game.game_type == "official",
        Game.publish_status == "published",
        Game.deleted_at.is_(None),
        Game.game_status.in_(OFFICIAL_GAME_LIST_VIEW_STATUSES[normalized_view]),
    )

    if starts_on is not None:
        statement = statement.where(Game.starts_on_local == starts_on)

    if normalized_search is not None:
        search_pattern = f"%{escape_like_search(normalized_search)}%"
        statement = statement.where(
            or_(
                Game.title.ilike(search_pattern, escape="\\"),
                Game.venue_name_snapshot.ilike(search_pattern, escape="\\"),
                Game.city_snapshot.ilike(search_pattern, escape="\\"),
                Game.state_snapshot.ilike(search_pattern, escape="\\"),
            )
        )

    if cursor_payload is not None:
        statement = statement.where(
            build_official_game_list_cursor_filter(
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

    rows = list(db.scalars(statement.limit(effective_limit + 1)).all())
    page_games = rows[:effective_limit]
    has_more = len(rows) > effective_limit
    (
        booked_spots_by_game_id,
        primary_venue_image_object_key_by_venue_id,
    ) = load_official_game_list_card_data(db, page_games)

    games = [
        build_official_game_card_read(
            game,
            booked_spots=booked_spots_by_game_id.get(game.id, 0),
            primary_venue_image_object_key=primary_venue_image_object_key_by_venue_id.get(
                game.venue_id
            ),
            include_operational_issues=normalized_view == "active",
        )
        for game in page_games
    ]

    next_cursor = None
    if has_more and page_games:
        last_game = page_games[-1]
        next_cursor = encode_official_game_list_cursor(
            game=last_game,
            view=normalized_view,
            search=normalized_search,
            starts_on=starts_on,
            sort_direction=sort_direction,
        )

    return AdminOfficialGameListRead(
        games=games,
        next_cursor=next_cursor,
        has_more=has_more,
        limit=effective_limit,
    )


def load_official_game_list_card_data(
    db: Session,
    games: list[Game],
) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, str]]:
    if not games:
        return {}, {}

    game_ids = [game.id for game in games]
    venue_ids = {game.venue_id for game in games if game.venue_id is not None}
    booked_spots_by_game_id: dict[uuid.UUID, int] = {}
    primary_venue_image_object_key_by_venue_id: dict[uuid.UUID, str] = {}

    for game_id, booked_spots in db.execute(
        select(GameParticipant.game_id, func.count(GameParticipant.id))
        .where(
            GameParticipant.game_id.in_(game_ids),
            GameParticipant.participant_status.in_(
                ACTIVE_ROSTER_PARTICIPANT_STATUSES
            ),
        )
        .group_by(GameParticipant.game_id)
    ).all():
        booked_spots_by_game_id[game_id] = int(booked_spots or 0)

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

    return booked_spots_by_game_id, primary_venue_image_object_key_by_venue_id


def normalize_official_game_list_view(view: str) -> str:
    normalized_view = view.strip().lower()
    if normalized_view not in OFFICIAL_GAME_LIST_VALID_VIEWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="view must be 'active', 'completed', or 'cancelled'.",
        )

    return normalized_view


def normalize_official_game_list_search(search: str | None) -> str | None:
    if search is None:
        return None

    normalized_search = search.strip()
    return normalized_search or None


def get_official_game_list_sort_direction(view: str) -> str:
    return "asc" if view in OFFICIAL_GAME_LIST_ASCENDING_VIEWS else "desc"


def escape_like_search(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def encode_official_game_list_cursor(
    *,
    game: Game,
    view: str,
    search: str | None,
    starts_on: date | None,
    sort_direction: str,
) -> str:
    payload = {
        "view": view,
        "search": search,
        "starts_on": starts_on.isoformat() if starts_on is not None else None,
        "sort_direction": sort_direction,
        "starts_at": game.starts_at.isoformat(),
        "created_at": game.created_at.isoformat(),
        "id": str(game.id),
    }
    serialized = dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return urlsafe_b64encode(serialized).decode("ascii")


def decode_official_game_list_cursor(cursor: str | None) -> dict[str, object] | None:
    if cursor is None:
        return None

    try:
        decoded = urlsafe_b64decode(cursor.encode("ascii"))
        payload = loads(decoded.decode("utf-8"))
    except (BinasciiError, UnicodeDecodeError, ValueError, JSONDecodeError) as exc:
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
        "view",
        "search",
        "starts_on",
        "sort_direction",
        "starts_at",
        "created_at",
        "id",
    }
    if not required_keys.issubset(payload):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    return payload


def validate_official_game_list_cursor_context(
    cursor_payload: dict[str, object] | None,
    *,
    view: str,
    search: str | None,
    starts_on: date | None,
    sort_direction: str,
) -> None:
    if cursor_payload is None:
        return

    expected_starts_on = starts_on.isoformat() if starts_on is not None else None
    if (
        cursor_payload["view"] != view
        or cursor_payload["search"] != search
        or cursor_payload["starts_on"] != expected_starts_on
        or cursor_payload["sort_direction"] != sort_direction
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor does not match the current query.",
        )


def parse_official_game_list_cursor_datetime(
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


def parse_official_game_list_cursor_uuid(
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


def build_official_game_list_cursor_filter(
    cursor_payload: dict[str, object],
    *,
    sort_direction: str,
):
    starts_at = parse_official_game_list_cursor_datetime(cursor_payload, "starts_at")
    created_at = parse_official_game_list_cursor_datetime(cursor_payload, "created_at")
    game_id = parse_official_game_list_cursor_uuid(cursor_payload)

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


def build_official_game_card_read(
    game: Game,
    *,
    booked_spots: int,
    primary_venue_image_object_key: str | None,
    include_operational_issues: bool,
) -> AdminOfficialGameCardRead:
    primary_venue_image_url = build_primary_venue_image_url(
        primary_venue_image_object_key
    )
    has_primary_venue_image = primary_venue_image_object_key is not None
    issues: list[str] = []
    if include_operational_issues:
        if game.host_user_id is None:
            issues.append(OFFICIAL_GAME_LIST_ISSUE_MISSING_HOST)
        if not has_primary_venue_image:
            issues.append(OFFICIAL_GAME_LIST_ISSUE_MISSING_PHOTO)

    return AdminOfficialGameCardRead(
        id=game.id,
        title=game.title,
        venue_name_snapshot=game.venue_name_snapshot,
        starts_at=game.starts_at,
        ends_at=game.ends_at,
        starts_on_local=game.starts_on_local,
        timezone=game.timezone,
        city_snapshot=game.city_snapshot,
        state_snapshot=game.state_snapshot,
        format_label=game.format_label,
        game_player_group=game.game_player_group,
        environment_type=game.environment_type,
        price_per_player_cents=game.price_per_player_cents,
        currency=game.currency,
        total_spots=game.total_spots,
        booked_spots=booked_spots,
        host_user_id=game.host_user_id,
        primary_venue_image_url=primary_venue_image_url,
        issues=issues,
    )


def build_primary_venue_image_url(storage_object_key: str | None) -> str | None:
    if storage_object_key is None:
        return None

    try:
        return create_object_read_url(storage_object_key)
    except (R2StorageConfigError, R2StorageError):
        return None


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
    participant_ids = select(GameParticipant.id).where(
        GameParticipant.game_id == game_id
    )
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
            .order_by(
                GameCreditUsage.created_at.desc(),
                GameCreditUsage.id.desc(),
            )
        ).all()
    )

    return AdminOfficialGameMoneyRead(
        payments=payments,
        refunds=refunds,
        credits=credits,
        credit_usages=credit_usages,
    )
