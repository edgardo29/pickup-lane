"""Build test data directly in the test database.

Each function creates one row with sensible defaults, commits it so API
requests can see it, and returns the model. Pass keyword arguments to override
any column.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    CommunityGameDetail,
    Game,
    GameCredit,
    GameParticipant,
    SubPost,
    SubPostPosition,
    SubPostRequest,
    User,
    UserPaymentMethod,
    Venue,
)

CANCELLED_PARTICIPANT_STATUSES = {"cancelled", "late_cancelled", "removed", "refunded"}


def _now() -> datetime:
    return datetime.now(UTC)


def _save(db: Session, row):
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def make_user(db: Session, **overrides) -> User:
    suffix = uuid.uuid4().hex[:12]
    values = {
        "id": uuid.uuid4(),
        "auth_user_id": f"firebase-{suffix}",
        "email": f"user-{suffix}@example.test",
        "first_name": "Test",
        "last_name": f"User {suffix[:4]}",
        "role": "player",
        "account_status": "active",
        "hosting_status": "not_eligible",
    }
    values.update(overrides)
    return _save(db, User(**values))


def make_venue(db: Session, **overrides) -> Venue:
    suffix = uuid.uuid4().hex[:6]
    values = {
        "id": uuid.uuid4(),
        "name": f"Test Park {suffix}",
        "address_line_1": "100 Test Street",
        "city": "Chicago",
        "state": "IL",
        "postal_code": "60601",
        "venue_status": "approved",
        "is_active": True,
    }
    values.update(overrides)
    return _save(db, Venue(**values))


def make_game(
    db: Session,
    *,
    starts_at: datetime,
    game_type: str = "official",
    venue: Venue | None = None,
    created_by: User | None = None,
    host: User | None = None,
    **overrides,
) -> Game:
    """Create a published, active, visible, open game starting at ``starts_at``.

    ``starts_on_local`` is derived from ``starts_at`` in the game's timezone.
    Community games get their own eligible host unless one is given.
    """
    venue = venue or make_venue(db)
    created_by = created_by or make_user(db)
    game_timezone = overrides.get("timezone", "America/Chicago")
    is_official = game_type == "official"
    if not is_official and host is None:
        host = make_user(db, hosting_status="eligible")

    values = {
        "id": uuid.uuid4(),
        "game_type": game_type,
        "payment_collection_type": "in_app" if is_official else "external_host",
        "policy_mode": "official_standard" if is_official else "custom_hosted",
        "publish_status": "published",
        "published_at": _now(),
        "game_status": "active",
        "public_visibility_status": "visible",
        "join_enforcement_status": "open",
        "title": f"Pickup game {uuid.uuid4().hex[:6]}",
        "venue_id": venue.id,
        "venue_name_snapshot": venue.name,
        "address_snapshot": venue.address_line_1,
        "city_snapshot": venue.city,
        "state_snapshot": venue.state,
        "host_user_id": host.id if host else None,
        "created_by_user_id": created_by.id,
        "starts_at": starts_at,
        "ends_at": starts_at + timedelta(hours=1),
        "starts_on_local": starts_at.astimezone(ZoneInfo(game_timezone)).date(),
        "timezone": game_timezone,
        "format_label": "7v7",
        "game_player_group": "coed",
        "skill_level": "intermediate",
        "environment_type": "outdoor",
        "total_spots": 14,
        "price_per_player_cents": 1000,
        "created_at": _now(),
    }
    values.update(overrides)
    return _save(db, Game(**values))


def make_booking(
    db: Session,
    *,
    game: Game,
    buyer: User | None = None,
    **overrides,
) -> Booking:
    """Create a confirmed, paid booking for one player unless overridden."""
    buyer = buyer or make_user(db)
    participant_count = overrides.get("participant_count", 1)
    subtotal = game.price_per_player_cents * participant_count
    values = {
        "id": uuid.uuid4(),
        "game_id": game.id,
        "buyer_user_id": buyer.id,
        "booking_status": "confirmed",
        "payment_status": "paid",
        "reservation_status": "confirmed",
        "participant_count": participant_count,
        "subtotal_cents": subtotal,
        "total_cents": subtotal,
        "price_per_player_snapshot_cents": game.price_per_player_cents,
        "booked_at": _now(),
    }
    values.update(overrides)
    return _save(db, Booking(**values))


def make_held_booking(
    db: Session,
    *,
    game: Game,
    expires_at: datetime,
    payment_status: str = "processing",
    buyer: User | None = None,
    **overrides,
) -> Booking:
    """Create a booking whose spots are temporarily held during checkout."""
    return make_booking(
        db,
        game=game,
        buyer=buyer,
        booking_status="pending_payment",
        payment_status=payment_status,
        reservation_status="held",
        expires_at=expires_at,
        booked_at=None,
        **overrides,
    )


def make_participant(
    db: Session,
    *,
    game: Game,
    booking: Booking | None = None,
    user: User | None = None,
    participant_type: str = "registered_user",
    participant_status: str = "confirmed",
    **overrides,
) -> GameParticipant:
    """Create a roster row. Guests are attached to ``user`` as their owner."""
    user = user or make_user(db)
    is_guest = participant_type == "guest"
    now = _now()
    values = {
        "id": uuid.uuid4(),
        "game_id": game.id,
        "booking_id": booking.id if booking else None,
        "participant_type": participant_type,
        "user_id": None if is_guest else user.id,
        "guest_of_user_id": user.id if is_guest else None,
        "guest_name": "Guest Player" if is_guest else None,
        "display_name_snapshot": "Guest Player" if is_guest else "Test Player",
        "participant_status": participant_status,
        "price_cents": game.price_per_player_cents,
        "confirmed_at": now if participant_status == "confirmed" else None,
        "cancelled_at": now
        if participant_status in CANCELLED_PARTICIPANT_STATUSES
        else None,
    }
    values.update(overrides)
    return _save(db, GameParticipant(**values))


def make_community_game_detail(
    db: Session, *, game: Game, **overrides
) -> CommunityGameDetail:
    """Create the host-provided details for a community game."""
    values = {
        "id": uuid.uuid4(),
        "game_id": game.id,
        "payment_methods_snapshot": [{"type": "venmo", "value": "@test-host"}],
        "payment_instructions_snapshot": "Pay the host before kickoff.",
        "payment_text_moderation_status": "visible",
    }
    values.update(overrides)
    return _save(db, CommunityGameDetail(**values))


def make_saved_card(db: Session, *, user: User, **overrides) -> UserPaymentMethod:
    """Create an active, unexpired saved card linked to ``user``'s Stripe customer.

    ``user`` must already have a ``stripe_customer_id``.
    """
    suffix = uuid.uuid4().hex[:10]
    values = {
        "id": uuid.uuid4(),
        "user_id": user.id,
        "stripe_customer_id": user.stripe_customer_id,
        "stripe_payment_method_id": f"pm_test_{suffix}",
        "card_fingerprint": f"fp_{suffix}",
        "card_brand": "visa",
        "card_last4": "4242",
        "exp_month": 12,
        "exp_year": _now().year + 3,
        "method_status": "active",
        "is_default": True,
    }
    values.update(overrides)
    return _save(db, UserPaymentMethod(**values))


def make_game_credit(
    db: Session, *, user: User, amount_cents: int, **overrides
) -> GameCredit:
    """Create active game credit that ``user`` can spend in full."""
    values = {
        "id": uuid.uuid4(),
        "user_id": user.id,
        "amount_cents": amount_cents,
        "available_cents": amount_cents,
        "credit_status": "active",
        "credit_reason": "admin_credit",
        "idempotency_key": f"test-credit-{uuid.uuid4().hex}",
    }
    values.update(overrides)
    return _save(db, GameCredit(**values))


# Valid production settings, for tests of startup validation. All values are
# synthetic; override or remove (None) one setting per test.
PRODUCTION_DATABASE_URL = (
    "postgresql+psycopg://db.example.invalid:5432/pickup_lane_prod"
)
PRODUCTION_CURSOR_SIGNING_SECRET = "synthetic-cursor-signing-secret-for-settings"


def make_sub_post(
    db: Session, *, owner: User, starts_at: datetime, **overrides
) -> SubPost:
    """Create an active, visible Need a Sub post needing two field players.

    It gets one open field-player position, as posts created in the app do.
    ``starts_on_local`` is derived from ``starts_at`` in Chicago time.
    """
    values = {
        "id": uuid.uuid4(),
        "owner_user_id": owner.id,
        "post_status": "active",
        "public_visibility_status": "visible",
        "sport_type": "soccer",
        "format_label": "7v7",
        "environment_type": "outdoor",
        "skill_level": "intermediate",
        "game_player_group": "coed",
        "starts_at": starts_at,
        "ends_at": starts_at + timedelta(hours=1),
        "starts_on_local": starts_at.astimezone(ZoneInfo("America/Chicago")).date(),
        "timezone": "America/Chicago",
        "location_name": f"Test Field {uuid.uuid4().hex[:6]}",
        "address_line_1": "200 Test Avenue",
        "city": "Chicago",
        "state": "IL",
        "postal_code": "60601",
        "country_code": "US",
        "subs_needed": 2,
        "price_due_at_venue_cents": 0,
        "currency": "USD",
        "expires_at": starts_at,
        "created_at": _now(),
        "updated_at": _now(),
    }
    values.update(overrides)
    post = _save(db, SubPost(**values))
    _save(
        db,
        SubPostPosition(
            id=uuid.uuid4(),
            sub_post_id=post.id,
            position_label="field_player",
            player_group="open",
            spots_needed=post.subs_needed,
            sort_order=0,
        ),
    )
    return post


def make_sub_post_request(
    db: Session,
    *,
    post: SubPost,
    requester: User,
    request_status: str = "confirmed",
    **overrides,
) -> SubPostRequest:
    """Create a request for the post's first position, stamped for its status."""
    position = db.query(SubPostPosition).filter_by(sub_post_id=post.id).first()
    now = _now()
    values = {
        "id": uuid.uuid4(),
        "sub_post_id": post.id,
        "sub_post_position_id": position.id,
        "requester_user_id": requester.id,
        "request_status": request_status,
        "confirmed_at": now if request_status == "confirmed" else None,
        "declined_at": now if request_status == "declined" else None,
        "sub_waitlisted_at": now if request_status == "sub_waitlist" else None,
        "canceled_at": now
        if request_status in {"canceled_by_player", "canceled_by_owner"}
        else None,
        "expired_at": now if request_status == "expired" else None,
        "no_show_reported_at": now if request_status == "no_show_reported" else None,
    }
    values.update(overrides)
    return _save(db, SubPostRequest(**values))


def production_settings_env(**overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": "production",
        "DATABASE_URL": PRODUCTION_DATABASE_URL,
        "ALLOWED_HOSTS": "api.example.invalid",
        "CORS_ALLOWED_ORIGINS": "https://app.example.invalid",
        "ENABLE_API_DOCS": "false",
        "ENABLE_DB_HEALTH": "false",
        "DB_POOL_SIZE": "5",
        "DB_MAX_OVERFLOW": "2",
        "FIREBASE_ADMIN_CREDENTIALS_JSON": (
            '{"type":"service_account","project_id":"pickup-lane-synthetic"}'
        ),
        "FIREBASE_PROJECT_ID": "pickup-lane-synthetic",
        "FIREBASE_APP_CHECK_MODE": "disabled",
        "ENABLE_STRIPE_PAYMENTS": "false",
        "STRIPE_SECRET_KEY": "sk_live_synthetic",
        "STRIPE_PUBLISHABLE_KEY": "pk_live_synthetic",
        "STRIPE_WEBHOOK_SECRET": "whsec_synthetic",
        "R2_ACCOUNT_ID": "synthetic-r2-account",
        "R2_ACCESS_KEY_ID": "synthetic-r2-access-key-id",
        "R2_SECRET_ACCESS_KEY": "synthetic-r2-secret-access-key",
        "R2_BUCKET_NAME": "pickup-lane-synthetic-bucket",
        "R2_ENDPOINT_URL": "https://synthetic-r2-account.r2.cloudflarestorage.com",
        "INBOX_TOKEN_SECRET": "synthetic-independent-inbox-token-secret",
        "CURSOR_SIGNING_SECRET": PRODUCTION_CURSOR_SIGNING_SECRET,
    }
    for name, value in overrides.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env
