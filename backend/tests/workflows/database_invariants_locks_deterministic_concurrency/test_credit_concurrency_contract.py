from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from backend.models import Booking, Game, GameCredit, GameCreditUsage, User, Venue
from backend.schemas.game_credit_schema import GameCreditReverseCreate

pytestmark = pytest.mark.suite_type("ordinary")

_NOW = datetime(2035, 7, 1, 12, 0, tzinfo=timezone.utc)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _user() -> User:
    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws04-02b-credit-user-{unique}",
        role="player",
        email=f"ws04-02b-credit-user-{unique}@example.invalid",
        first_name="Credit",
        last_name="User",
        account_status="active",
        hosting_status="eligible",
    )


def _admin() -> User:
    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws04-02b-credit-admin-{unique}",
        role="admin",
        email=f"ws04-02b-credit-admin-{unique}@example.invalid",
        first_name="Credit",
        last_name="Admin",
        account_status="active",
        hosting_status="eligible",
    )


def _credit(user_id: uuid.UUID, *, amount_cents: int = 1000) -> GameCredit:
    return GameCredit(
        id=uuid.uuid4(),
        user_id=user_id,
        amount_cents=amount_cents,
        available_cents=amount_cents,
        currency="USD",
        credit_status="active",
        credit_reason="admin_credit",
        idempotency_key=f"ws04-02b-credit-{uuid.uuid4()}",
        created_at=_NOW,
        updated_at=_NOW,
    )


def _venue() -> Venue:
    return Venue(
        id=uuid.uuid4(),
        name="WS04-02B Credit Field",
        address_line_1="1 Credit Lock Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        is_active=True,
    )


def _game(host: User, venue: Venue) -> Game:
    return Game(
        id=uuid.uuid4(),
        game_type="official",
        payment_collection_type="in_app",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="WS04-02B Credit Game",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=None,
        created_by_user_id=host.id,
        starts_at=_NOW,
        ends_at=_NOW.replace(hour=14),
        starts_on_local=_NOW.date(),
        timezone="UTC",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=12,
        price_per_player_cents=1200,
        currency="USD",
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=0,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="official_standard",
        published_at=_NOW,
    )


def _booking(user: User, game: Game) -> Booking:
    return Booking(
        id=uuid.uuid4(),
        game_id=game.id,
        buyer_user_id=user.id,
        booking_status="confirmed",
        payment_status="paid",
        participant_count=1,
        subtotal_cents=1200,
        platform_fee_cents=0,
        discount_cents=0,
        total_cents=1200,
        currency="USD",
        price_per_player_snapshot_cents=1200,
        platform_fee_snapshot_cents=0,
        booked_at=_NOW,
    )


def _await_contention_start(barrier: Barrier | None) -> None:
    if barrier is not None:
        barrier.wait(timeout=10)


def _reserve_credit(
    user_id: uuid.UUID,
    amount_cents: int,
    booking_id: uuid.UUID,
    barrier: Barrier | None = None,
) -> str:
    from backend.services.game_credit_service import (
        GameCreditInsufficientBalanceError,
        reserve_game_credits,
    )

    with _session() as db:
        _await_contention_start(barrier)
        try:
            reserve_game_credits(
                db,
                user_id,
                amount_cents=amount_cents,
                booking_id=booking_id,
                game_id=None,
                now=_NOW,
                idempotency_scope=f"ws04-02b-{booking_id}",
            )
            db.commit()
            return "reserved"
        except GameCreditInsufficientBalanceError:
            db.rollback()
            return "insufficient_balance"


@pytest.mark.requirement("WS04-02B-R7", "WS04-02B-R8")
def test_concurrent_credit_reservations_cannot_overdraw_grant() -> None:
    with _session() as db:
        user = _user()
        venue = _venue()
        db.add_all([user, venue])
        db.commit()
        game = _game(user, venue)
        db.add(game)
        db.commit()
        bookings = [_booking(user, game), _booking(user, game)]
        db.add_all(bookings)
        db.commit()
        credit = _credit(user.id, amount_cents=1000)
        db.add(credit)
        db.commit()
        user_id = user.id
        credit_id = credit.id
        booking_ids = [booking.id for booking in bookings]

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_reserve_credit, user_id, 700, booking_id, barrier)
            for booking_id in booking_ids
        ]
        results = sorted(future.result(timeout=20) for future in futures)

    with _session() as db:
        credit = db.get(GameCredit, credit_id)
        assert credit is not None
        usage_count = int(
            db.scalar(
                select(func.count())
                .select_from(GameCreditUsage)
                .where(GameCreditUsage.game_credit_id == credit_id)
            )
            or 0
        )
        reserved_total = int(
            db.scalar(
                select(func.coalesce(func.sum(GameCreditUsage.amount_cents), 0))
                .where(GameCreditUsage.game_credit_id == credit_id)
            )
            or 0
        )

    assert results == ["insufficient_balance", "reserved"]
    assert credit.available_cents == 300
    assert usage_count == 1
    assert reserved_total == 700


def _release_credit_usage(
    usage_id: uuid.UUID,
    barrier: Barrier | None = None,
) -> tuple[str, uuid.UUID]:
    from backend.services.game_credit_service import release_reserved_game_credit_usage

    with _session() as db:
        _await_contention_start(barrier)
        released = release_reserved_game_credit_usage(
            db,
            usage_id,
            now=_NOW,
            reason_code="ws04-02b-release",
        )
        db.commit()
        return "released", released.id


@pytest.mark.requirement("WS04-02B-R7", "WS04-02B-R8")
def test_concurrent_reserved_credit_release_converges_to_one_released_usage() -> None:
    with _session() as db:
        user = _user()
        venue = _venue()
        db.add_all([user, venue])
        db.commit()
        game = _game(user, venue)
        db.add(game)
        db.commit()
        booking = _booking(user, game)
        db.add(booking)
        db.commit()
        credit = _credit(user.id, amount_cents=1000)
        reserved_usage = GameCreditUsage(
            id=uuid.uuid4(),
            game_credit_id=credit.id,
            booking_id=booking.id,
            game_id=None,
            payment_id=None,
            amount_cents=1000,
            currency="USD",
            usage_type="redeem",
            usage_status="reserved",
            idempotency_key=f"ws04-02b-release-{uuid.uuid4()}",
            reserved_at=_NOW,
            created_at=_NOW,
            updated_at=_NOW,
        )
        credit.available_cents = 0
        credit.credit_status = "active"
        db.add(credit)
        db.commit()
        db.add(reserved_usage)
        db.commit()
        credit_id = credit.id
        usage_id = reserved_usage.id

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_release_credit_usage, usage_id, barrier)
            for _ in range(2)
        ]
        results = [future.result(timeout=20) for future in futures]

    with _session() as db:
        credit = db.get(GameCredit, credit_id)
        usage = db.get(GameCreditUsage, usage_id)
        assert credit is not None
        assert usage is not None

    assert results == [("released", usage_id), ("released", usage_id)]
    assert credit.available_cents == 1000
    assert credit.credit_status == "active"
    assert usage.usage_status == "released"


def _redeem_credit_booking(
    booking_id: uuid.UUID,
    barrier: Barrier | None = None,
) -> str:
    from backend.services.game_credit_service import redeem_reserved_game_credits

    with _session() as db:
        _await_contention_start(barrier)
        redeem_reserved_game_credits(db, booking_id, now=_NOW)
        db.commit()
        return "redeemed"


@pytest.mark.requirement("WS04-02B-R7", "WS04-02B-R8")
def test_concurrent_reserved_credit_redeem_converges_to_one_redeemed_usage() -> None:
    with _session() as db:
        user = _user()
        venue = _venue()
        db.add_all([user, venue])
        db.commit()
        game = _game(user, venue)
        db.add(game)
        db.commit()
        booking = _booking(user, game)
        db.add(booking)
        db.commit()
        credit = _credit(user.id, amount_cents=1000)
        reserved_usage = GameCreditUsage(
            id=uuid.uuid4(),
            game_credit_id=credit.id,
            booking_id=booking.id,
            game_id=None,
            payment_id=None,
            amount_cents=1000,
            currency="USD",
            usage_type="redeem",
            usage_status="reserved",
            idempotency_key=f"ws04-02b-redeem-{uuid.uuid4()}",
            reserved_at=_NOW,
            created_at=_NOW,
            updated_at=_NOW,
        )
        credit.available_cents = 0
        credit.credit_status = "active"
        db.add(credit)
        db.commit()
        db.add(reserved_usage)
        db.commit()
        credit_id = credit.id
        booking_id = booking.id
        usage_id = reserved_usage.id

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_redeem_credit_booking, booking_id, barrier)
            for _ in range(2)
        ]
        results = sorted(future.result(timeout=20) for future in futures)

    with _session() as db:
        credit = db.get(GameCredit, credit_id)
        usage = db.get(GameCreditUsage, usage_id)
        assert credit is not None
        assert usage is not None

    assert results == ["redeemed", "redeemed"]
    assert credit.available_cents == 0
    assert credit.credit_status == "used"
    assert usage.usage_status == "redeemed"


def _restore_credit_usage(
    usage_id: uuid.UUID,
    reason: str,
    barrier: Barrier | None = None,
) -> tuple[str, uuid.UUID | None]:
    from backend.services.game_credit_service import restore_redeemed_game_credit_usage

    with _session() as db:
        _await_contention_start(barrier)
        restored = restore_redeemed_game_credit_usage(
            db,
            usage_id,
            now=_NOW,
            restore_reason=reason,
        )
        db.commit()
        return "restored", restored.id


@pytest.mark.requirement("WS04-02B-R7", "WS04-02B-R8")
def test_concurrent_redeemed_credit_restore_converges_to_one_restore_row() -> None:
    with _session() as db:
        user = _user()
        venue = _venue()
        db.add_all([user, venue])
        db.commit()
        game = _game(user, venue)
        db.add(game)
        db.commit()
        booking = _booking(user, game)
        db.add(booking)
        db.commit()
        credit = _credit(user.id, amount_cents=1000)
        redeemed_usage = GameCreditUsage(
            id=uuid.uuid4(),
            game_credit_id=credit.id,
            booking_id=booking.id,
            game_id=None,
            payment_id=None,
            amount_cents=1000,
            currency="USD",
            usage_type="redeem",
            usage_status="redeemed",
            idempotency_key=f"ws04-02b-redeem-{uuid.uuid4()}",
            reserved_at=_NOW,
            redeemed_at=_NOW,
            created_at=_NOW,
            updated_at=_NOW,
        )
        credit.available_cents = 0
        credit.credit_status = "used"
        db.add(credit)
        db.commit()
        db.add(redeemed_usage)
        db.commit()
        credit_id = credit.id
        usage_id = redeemed_usage.id

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                _restore_credit_usage,
                usage_id,
                "ws04-02b-restore",
                barrier,
            )
            for _ in range(2)
        ]
        results = [
            future.result(timeout=20)
            for future in futures
        ]

    with _session() as db:
        credit = db.get(GameCredit, credit_id)
        assert credit is not None
        restore_ids = list(
            db.scalars(
                select(GameCreditUsage.id).where(
                    GameCreditUsage.original_usage_id == usage_id,
                    GameCreditUsage.usage_type == "restore",
                    GameCreditUsage.usage_status == "restored",
                )
            ).all()
        )

    assert [status for status, _ in results] == ["restored", "restored"]
    assert {restore_id for _, restore_id in results} == set(restore_ids)
    assert len(restore_ids) == 1
    assert credit.available_cents == 1000
    assert credit.credit_status == "active"


def _reverse_credit(
    credit_id: uuid.UUID,
    admin_id: uuid.UUID,
    barrier: Barrier | None = None,
) -> str:
    from backend.services.game_credit_admin_service import reverse_admin_game_credit

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        _await_contention_start(barrier)
        try:
            reverse_admin_game_credit(
                db,
                admin_user=admin,
                game_credit_id=credit_id,
                payload=GameCreditReverseCreate(
                    idempotency_key=f"ws04-02b-reverse-{uuid.uuid4()}",
                    note="ws04-02b reversal concurrency proof",
                ),
            )
            return "reversed"
        except HTTPException as exc:
            db.rollback()
            return f"http-{exc.status_code}:{exc.detail}"


@pytest.mark.requirement("WS04-02B-R7", "WS04-02B-R8")
def test_concurrent_credit_reversal_converges_to_one_reversal_row() -> None:
    with _session() as db:
        admin = _admin()
        user = _user()
        db.add_all([admin, user])
        db.commit()
        credit = _credit(user.id, amount_cents=1000)
        db.add(credit)
        db.commit()
        admin_id = admin.id
        credit_id = credit.id

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_reverse_credit, credit_id, admin_id, barrier)
            for _ in range(2)
        ]
        results = sorted(future.result(timeout=20) for future in futures)

    with _session() as db:
        credit = db.get(GameCredit, credit_id)
        assert credit is not None
        reversal_count = int(
            db.scalar(
                select(func.count())
                .select_from(GameCreditUsage)
                .where(
                    GameCreditUsage.game_credit_id == credit_id,
                    GameCreditUsage.usage_type == "reverse",
                    GameCreditUsage.usage_status == "reversed",
                )
            )
            or 0
        )

    assert results == [
        "http-400:Only active credit with available value can be reversed.",
        "reversed",
    ]
    assert credit.available_cents == 0
    assert credit.credit_status == "reversed"
    assert reversal_count == 1
