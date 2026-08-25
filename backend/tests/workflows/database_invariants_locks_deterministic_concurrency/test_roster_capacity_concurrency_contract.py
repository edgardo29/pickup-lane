from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from threading import Barrier

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameParticipant,
    Payment,
    User,
    UserPaymentMethod,
    Venue,
    WaitlistEntry,
)
from backend.schemas.game_schema import GameGuestAddCreate, GameJoinCreate

pytestmark = pytest.mark.suite_type("ordinary")

_BASE_TIME = datetime(2035, 6, 1, 18, 0, tzinfo=timezone.utc)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _user(index: int, *, role: str = "player", with_stripe: bool = False) -> User:
    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws04-02b-user-{index}-{unique}",
        role=role,
        email=f"ws04-02b-user-{index}-{unique}@example.invalid",
        first_name="Invariant",
        last_name=f"User{index}",
        date_of_birth=date(1990, 1, 1),
        account_status="active",
        hosting_status="eligible",
        stripe_customer_id=f"cus_ws04_02b_{index}_{unique}" if with_stripe else None,
    )


def _venue(index: int = 1) -> Venue:
    return Venue(
        id=uuid.uuid4(),
        name=f"WS04-02B Field {index}",
        address_line_1="1 Lock Order Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        is_active=True,
    )


def _game(
    host: User,
    venue: Venue,
    index: int,
    *,
    total_spots: int,
    official: bool = False,
    waitlist_enabled: bool = True,
    max_guests_per_booking: int = 2,
    host_guest_max: int = 0,
) -> Game:
    starts_at = _BASE_TIME + timedelta(days=index)
    payment_collection_type = "in_app" if official else "none"
    return Game(
        id=uuid.uuid4(),
        game_type="official" if official else "community",
        payment_collection_type=payment_collection_type,
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title=f"WS04-02B Game {index}",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=None if official else host.id,
        created_by_user_id=host.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        starts_on_local=starts_at.date(),
        timezone="UTC",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=total_spots,
        price_per_player_cents=1200 if official else 0,
        currency="USD",
        allow_guests=True,
        max_guests_per_booking=max_guests_per_booking,
        host_guest_max=host_guest_max,
        waitlist_enabled=waitlist_enabled,
        is_chat_enabled=True,
        policy_mode="official_standard" if official else "custom_hosted",
        published_at=_BASE_TIME - timedelta(days=1),
    )


def _booking(
    user: User,
    game: Game,
    *,
    participant_count: int = 1,
    booking_status: str = "confirmed",
    payment_status: str | None = None,
) -> Booking:
    is_confirmed = booking_status == "confirmed"
    payment_state = payment_status or (
        "paid" if game.payment_collection_type == "in_app" and is_confirmed else "not_required"
    )
    subtotal_cents = game.price_per_player_cents * participant_count
    return Booking(
        id=uuid.uuid4(),
        game_id=game.id,
        buyer_user_id=user.id,
        booking_status=booking_status,
        payment_status=payment_state,
        participant_count=participant_count,
        subtotal_cents=subtotal_cents,
        platform_fee_cents=0,
        discount_cents=0,
        total_cents=subtotal_cents,
        currency="USD",
        price_per_player_snapshot_cents=game.price_per_player_cents,
        platform_fee_snapshot_cents=0,
        booked_at=_BASE_TIME if is_confirmed else None,
    )


def _participant(
    user: User,
    game: Game,
    *,
    booking: Booking,
    status: str,
    roster_order: int | None = None,
) -> GameParticipant:
    return GameParticipant(
        id=uuid.uuid4(),
        game_id=game.id,
        booking_id=booking.id,
        participant_type="registered_user",
        user_id=user.id,
        display_name_snapshot=f"{user.first_name} {user.last_name}",
        participant_status=status,
        attendance_status="unknown" if status == "confirmed" else "not_applicable",
        cancellation_type="none",
        price_cents=game.price_per_player_cents,
        currency="USD",
        roster_order=roster_order,
        joined_at=_BASE_TIME,
        confirmed_at=_BASE_TIME if status == "confirmed" else None,
    )


def _payment_method(user: User, index: int) -> UserPaymentMethod:
    return UserPaymentMethod(
        id=uuid.uuid4(),
        user_id=user.id,
        stripe_customer_id=user.stripe_customer_id or f"cus_ws04_02b_missing_{index}",
        stripe_payment_method_id=f"pm_ws04_02b_{index}_{uuid.uuid4()}",
        card_fingerprint=f"fingerprint_ws04_02b_{index}_{uuid.uuid4()}",
        card_brand="visa",
        card_last4=f"{index:04d}"[-4:],
        exp_month=12,
        exp_year=2035,
        method_status="active",
        is_default=True,
    )


def _active_participant_count(db: Session, game_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(GameParticipant)
            .where(
                GameParticipant.game_id == game_id,
                GameParticipant.participant_status.in_({"confirmed", "pending_payment"}),
            )
        )
        or 0
    )


def _await_contention_start(barrier: Barrier | None) -> None:
    if barrier is not None:
        barrier.wait(timeout=10)


def _join_game(
    game_id: uuid.UUID,
    user_id: uuid.UUID,
    request: GameJoinCreate,
    barrier: Barrier | None = None,
) -> str:
    from backend.services.game_roster_service import join_game_roster_workflow

    with _session() as db:
        user = db.get(User, user_id)
        assert user is not None
        _await_contention_start(barrier)
        try:
            return join_game_roster_workflow(db, game_id, request, user).status
        except HTTPException as exc:
            db.rollback()
            return f"http-{exc.status_code}:{exc.detail}"


@pytest.mark.requirement("WS04-02B-R2", "WS04-02B-R5", "WS04-02B-R8")
def test_concurrent_community_joins_serialize_capacity_on_game_row() -> None:
    with _session() as db:
        host = _user(0)
        joiner_one = _user(1)
        joiner_two = _user(2)
        venue = _venue()
        db.add_all([host, joiner_one, joiner_two, venue])
        db.commit()
        game = _game(host, venue, 1, total_spots=1)
        db.add(game)
        db.commit()
        game_id = game.id
        joiner_ids = [joiner_one.id, joiner_two.id]

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_join_game, game_id, user_id, GameJoinCreate(), barrier)
            for user_id in joiner_ids
        ]
        results = sorted(future.result(timeout=20) for future in futures)

    with _session() as db:
        confirmed_count = _active_participant_count(db, game_id)
        waitlist_count = int(
            db.scalar(
                select(func.count())
                .select_from(WaitlistEntry)
                .where(
                    WaitlistEntry.game_id == game_id,
                    WaitlistEntry.waitlist_status == "active",
                )
            )
            or 0
        )

    assert results == ["joined", "waitlisted"]
    assert confirmed_count == 1
    assert waitlist_count == 1


def _add_guest(
    game_id: uuid.UUID,
    user_id: uuid.UUID,
    barrier: Barrier | None = None,
) -> str:
    from backend.services.game_roster_service import add_booking_game_guests_workflow

    with _session() as db:
        user = db.get(User, user_id)
        assert user is not None
        _await_contention_start(barrier)
        try:
            return add_booking_game_guests_workflow(
                db,
                game_id,
                GameGuestAddCreate(guest_count=1),
                user,
            ).status
        except HTTPException as exc:
            db.rollback()
            return f"http-{exc.status_code}:{exc.detail}"


@pytest.mark.requirement("WS04-02B-R2", "WS04-02B-R5", "WS04-02B-R8")
def test_concurrent_guest_adds_recompute_capacity_under_same_game_lock() -> None:
    with _session() as db:
        host = _user(0)
        player_one = _user(1)
        player_two = _user(2)
        venue = _venue()
        db.add_all([host, player_one, player_two, venue])
        db.commit()
        game = _game(
            host,
            venue,
            2,
            total_spots=3,
            max_guests_per_booking=1,
        )
        db.add(game)
        db.commit()
        booking_one = _booking(player_one, game)
        booking_two = _booking(player_two, game)
        db.add_all([booking_one, booking_two])
        db.commit()
        db.add_all([
            _participant(player_one, game, booking=booking_one, status="confirmed", roster_order=1),
            _participant(player_two, game, booking=booking_two, status="confirmed", roster_order=2),
        ])
        db.commit()
        game_id = game.id
        player_ids = [player_one.id, player_two.id]

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_add_guest, game_id, user_id, barrier)
            for user_id in player_ids
        ]
        results = sorted(future.result(timeout=20) for future in futures)

    with _session() as db:
        assert _active_participant_count(db, game_id) == 3

    assert results == [
        "guests_added",
        "http-400:Not enough spots are available for guests.",
    ]


def _add_host_guest(
    game_id: uuid.UUID,
    host_id: uuid.UUID,
    barrier: Barrier | None = None,
) -> str:
    from backend.services.game_roster_service import add_host_game_guests_workflow

    with _session() as db:
        host = db.get(User, host_id)
        assert host is not None
        _await_contention_start(barrier)
        try:
            return add_host_game_guests_workflow(
                db,
                game_id,
                GameGuestAddCreate(guest_count=1),
                host,
            ).status
        except HTTPException as exc:
            db.rollback()
            return f"http-{exc.status_code}:{exc.detail}"


@pytest.mark.requirement("WS04-02B-R2", "WS04-02B-R5", "WS04-02B-R8")
def test_concurrent_host_guest_adds_recompute_capacity_under_same_game_lock() -> None:
    with _session() as db:
        host = _user(0)
        player = _user(1)
        venue = _venue()
        db.add_all([host, player, venue])
        db.commit()
        game = _game(
            host,
            venue,
            6,
            total_spots=2,
            host_guest_max=2,
        )
        db.add(game)
        db.commit()
        booking = _booking(player, game)
        db.add(booking)
        db.commit()
        db.add(
            _participant(
                player,
                game,
                booking=booking,
                status="confirmed",
                roster_order=1,
            )
        )
        db.commit()
        game_id = game.id
        host_id = host.id

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_add_host_guest, game_id, host_id, barrier)
            for _ in range(2)
        ]
        results = sorted(future.result(timeout=20) for future in futures)

    with _session() as db:
        assert _active_participant_count(db, game_id) == 2

    assert results == [
        "guests_added",
        "http-400:Not enough spots are available for host guests.",
    ]


@pytest.mark.requirement("WS04-02B-R2", "WS04-02B-R3", "WS04-02B-R8")
def test_waitlist_promotion_after_departure_uses_fresh_capacity_under_game_lock() -> None:
    from backend.services.game_roster_service import leave_game_roster_workflow

    with _session() as db:
        host = _user(0)
        departing_user = _user(1)
        waitlisted_user = _user(2)
        venue = _venue()
        db.add_all([host, departing_user, waitlisted_user, venue])
        db.commit()
        game = _game(host, venue, 3, total_spots=1)
        db.add(game)
        db.commit()
        confirmed_booking = _booking(departing_user, game)
        waitlist_booking = _booking(
            waitlisted_user,
            game,
            booking_status="waitlisted",
            payment_status="not_required",
        )
        waitlist_entry = WaitlistEntry(
            id=uuid.uuid4(),
            game_id=game.id,
            user_id=waitlisted_user.id,
            party_size=1,
            position=1,
            waitlist_status="active",
            joined_at=_BASE_TIME,
        )
        db.add_all([confirmed_booking, waitlist_booking])
        db.commit()
        db.add(waitlist_entry)
        db.commit()
        db.add_all([
            _participant(departing_user, game, booking=confirmed_booking, status="confirmed", roster_order=1),
            _participant(waitlisted_user, game, booking=waitlist_booking, status="waitlisted"),
        ])
        db.commit()
        game_id = game.id
        departing_user_id = departing_user.id
        waitlisted_user_id = waitlisted_user.id

    with _session() as db:
        departing_user = db.get(User, departing_user_id)
        assert departing_user is not None
        result = leave_game_roster_workflow(db, game_id, departing_user)

    with _session() as db:
        promoted_participant = db.scalar(
            select(GameParticipant).where(
                GameParticipant.game_id == game_id,
                GameParticipant.user_id == waitlisted_user_id,
            )
        )
        waitlist_entry = db.scalar(
            select(WaitlistEntry).where(
                WaitlistEntry.game_id == game_id,
                WaitlistEntry.user_id == waitlisted_user_id,
            )
        )

    assert result.status == "left_game"
    assert promoted_participant is not None
    assert promoted_participant.participant_status == "confirmed"
    assert promoted_participant.roster_order == 1
    assert waitlist_entry is not None
    assert waitlist_entry.waitlist_status == "accepted"


@pytest.mark.requirement("WS04-02B-R3", "WS04-02B-R4", "WS04-02B-R8")
def test_account_deletion_multi_game_cleanup_promotes_waitlists_in_game_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import game_waitlist_service
    from backend.services.account_deletion_service import cancel_future_roster_activity

    with _session() as db:
        deleted_user = _user(0)
        waitlisted_one = _user(1)
        waitlisted_two = _user(2)
        venue = _venue()
        host = _user(3)
        db.add_all([deleted_user, waitlisted_one, waitlisted_two, venue, host])
        db.commit()
        games = [
            _game(host, venue, 7, total_spots=1),
            _game(host, venue, 8, total_spots=1),
        ]
        db.add_all(games)
        db.commit()
        waitlisted_users = [waitlisted_one, waitlisted_two]
        for index, (game, waitlisted_user) in enumerate(zip(games, waitlisted_users), start=1):
            confirmed_booking = _booking(deleted_user, game)
            waitlist_booking = _booking(
                waitlisted_user,
                game,
                booking_status="waitlisted",
                payment_status="not_required",
            )
            waitlist_entry = WaitlistEntry(
                id=uuid.uuid4(),
                game_id=game.id,
                user_id=waitlisted_user.id,
                party_size=1,
                position=1,
                waitlist_status="active",
                joined_at=_BASE_TIME + timedelta(minutes=index),
            )
            db.add_all([confirmed_booking, waitlist_booking])
            db.commit()
            db.add_all([
                _participant(
                    deleted_user,
                    game,
                    booking=confirmed_booking,
                    status="confirmed",
                    roster_order=1,
                ),
                _participant(
                    waitlisted_user,
                    game,
                    booking=waitlist_booking,
                    status="waitlisted",
                ),
                waitlist_entry,
            ])
            db.commit()
        deleted_user_id = deleted_user.id
        game_ids = [game.id for game in games]
        waitlisted_user_ids = [user.id for user in waitlisted_users]

    original_promote = game_waitlist_service.promote_waitlist_entries
    promoted_game_order: list[uuid.UUID] = []

    def record_promotion_order(db: Session, db_game: Game, now: datetime) -> None:
        promoted_game_order.append(db_game.id)
        original_promote(db, db_game, now)

    monkeypatch.setattr(
        game_waitlist_service,
        "promote_waitlist_entries",
        record_promotion_order,
    )

    with _session() as db:
        cancel_future_roster_activity(
            db,
            user_id=deleted_user_id,
            changed_by_user_id=None,
            now=_BASE_TIME,
        )
        db.commit()

    with _session() as db:
        cancelled_deleted_participants = int(
            db.scalar(
                select(func.count())
                .select_from(GameParticipant)
                .where(
                    GameParticipant.game_id.in_(game_ids),
                    GameParticipant.user_id == deleted_user_id,
                    GameParticipant.participant_status == "cancelled",
                )
            )
            or 0
        )
        promoted_participants = list(
            db.scalars(
                select(GameParticipant)
                .where(
                    GameParticipant.game_id.in_(game_ids),
                    GameParticipant.user_id.in_(waitlisted_user_ids),
                )
                .order_by(GameParticipant.game_id.asc())
            ).all()
        )
        accepted_waitlist_entries = int(
            db.scalar(
                select(func.count())
                .select_from(WaitlistEntry)
                .where(
                    WaitlistEntry.game_id.in_(game_ids),
                    WaitlistEntry.user_id.in_(waitlisted_user_ids),
                    WaitlistEntry.waitlist_status == "accepted",
                )
            )
            or 0
        )

    assert promoted_game_order == sorted(game_ids, key=lambda game_id: game_id.int)
    assert cancelled_deleted_participants == 2
    assert {participant.participant_status for participant in promoted_participants} == {
        "confirmed"
    }
    assert {participant.roster_order for participant in promoted_participants} == {1}
    assert accepted_waitlist_entries == 2


@pytest.mark.requirement("WS04-02B-R3", "WS04-02B-R8", "WS04-02B-R9")
def test_paid_waitlist_promotion_commits_capacity_hold_before_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import game_waitlist_service
    from backend.services.game_service import count_roster_players
    from backend.services.stripe_service import StripePaymentIntentResult

    with _session() as db:
        admin = _user(0, role="admin")
        waitlisted_user = _user(1, with_stripe=True)
        competing_user = _user(2, with_stripe=True)
        venue = _venue()
        db.add_all([admin, waitlisted_user, competing_user, venue])
        db.commit()
        game = _game(admin, venue, 4, total_spots=1, official=True)
        db.add(game)
        db.commit()
        waitlist_booking = _booking(
            waitlisted_user,
            game,
            booking_status="waitlisted",
            payment_status="unpaid",
        )
        waitlisted_payment_method = _payment_method(waitlisted_user, 1)
        competing_payment_method = _payment_method(competing_user, 2)
        waitlist_entry = WaitlistEntry(
            id=uuid.uuid4(),
            game_id=game.id,
            user_id=waitlisted_user.id,
            party_size=1,
            position=1,
            waitlist_status="active",
            auto_charge_consent_at=_BASE_TIME,
            auto_charge_consent_version="ws04-02b-test",
            authorized_payment_method_id=waitlisted_payment_method.id,
            authorized_stripe_payment_method_id=waitlisted_payment_method.stripe_payment_method_id,
            authorized_payment_method_brand=waitlisted_payment_method.card_brand,
            authorized_payment_method_last4=waitlisted_payment_method.card_last4,
            authorized_amount_cents=waitlist_booking.total_cents,
            joined_at=_BASE_TIME,
        )
        db.add(waitlist_booking)
        db.commit()
        db.add_all([waitlisted_payment_method, competing_payment_method])
        db.commit()
        db.add_all([
            waitlist_entry,
        ])
        db.commit()
        db.add(_participant(waitlisted_user, game, booking=waitlist_booking, status="waitlisted"))
        db.commit()
        game_id = game.id
        competing_user_id = competing_user.id
        competing_payment_method_id = competing_payment_method.id

    provider_observed_counts: list[int] = []
    competing_join_statuses: list[str] = []

    def fake_create_payment_intent(**kwargs) -> StripePaymentIntentResult:
        del kwargs
        with _session() as db:
            provider_observed_counts.append(count_roster_players(db, game_id, now=_BASE_TIME))

        competing_join_statuses.append(
            _join_game(
                game_id,
                competing_user_id,
                GameJoinCreate(
                    payment_method_id=competing_payment_method_id,
                    auto_charge_consent_accepted=True,
                    auto_charge_consent_version="ws04-02b-test",
                ),
            )
        )
        return StripePaymentIntentResult(
            id="pi_ws04_02b_waitlist_hold",
            client_secret=None,
            status="requires_confirmation",
            latest_charge_id=None,
        )

    def fake_confirm_payment_intent(payment_intent_id: str, **kwargs) -> StripePaymentIntentResult:
        del kwargs
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret=None,
            status="processing",
            latest_charge_id=None,
        )

    monkeypatch.setattr(game_waitlist_service, "create_payment_intent", fake_create_payment_intent)
    monkeypatch.setattr(game_waitlist_service, "confirm_payment_intent", fake_confirm_payment_intent)

    with _session() as db:
        game = db.get(Game, game_id)
        assert game is not None
        game_waitlist_service.promote_waitlist_entries(db, game, _BASE_TIME)
        db.commit()

    with _session() as db:
        payment = db.scalar(select(Payment).where(Payment.idempotency_key.like("waitlist:%")))
        held_count = count_roster_players(db, game_id, now=_BASE_TIME)
        processing_entry_count = int(
            db.scalar(
                select(func.count())
                .select_from(WaitlistEntry)
                .where(
                    WaitlistEntry.game_id == game_id,
                    WaitlistEntry.waitlist_status == "payment_processing",
                )
            )
            or 0
        )
        active_waitlist_count = int(
            db.scalar(
                select(func.count())
                .select_from(WaitlistEntry)
                .where(
                    WaitlistEntry.game_id == game_id,
                    WaitlistEntry.waitlist_status == "active",
                )
            )
            or 0
        )

    assert provider_observed_counts == [1]
    assert competing_join_statuses == ["waitlisted"]
    assert held_count == 1
    assert processing_entry_count == 1
    assert active_waitlist_count == 1
    assert payment is not None
    assert payment.payment_status == "processing"


@pytest.mark.requirement("WS04-02B-R5", "WS04-02B-R8")
def test_database_unique_constraints_reject_duplicate_active_roster_and_waitlist_facts() -> None:
    with _session() as db:
        host = _user(0)
        user_one = _user(1)
        user_two = _user(2)
        venue = _venue()
        db.add_all([host, user_one, user_two, venue])
        db.commit()
        game = _game(host, venue, 5, total_spots=2)
        db.add(game)
        db.commit()
        game_id = game.id
        user_one_id = user_one.id
        user_two_id = user_two.id

    with _session() as db:
        game = db.get(Game, game_id)
        user_one = db.get(User, user_one_id)
        assert game is not None
        assert user_one is not None
        participant_one = GameParticipant(
            id=uuid.uuid4(),
            game_id=game_id,
            participant_type="registered_user",
            user_id=user_one_id,
            display_name_snapshot="Duplicate User",
            participant_status="confirmed",
            attendance_status="unknown",
            cancellation_type="none",
            price_cents=0,
            currency="USD",
            roster_order=1,
            joined_at=_BASE_TIME,
            confirmed_at=_BASE_TIME,
        )
        participant_two = GameParticipant(
            id=uuid.uuid4(),
            game_id=game_id,
            participant_type="registered_user",
            user_id=user_one_id,
            display_name_snapshot="Duplicate User",
            participant_status="waitlisted",
            attendance_status="not_applicable",
            cancellation_type="none",
            price_cents=0,
            currency="USD",
            joined_at=_BASE_TIME,
        )
        db.add_all([participant_one, participant_two])
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    with _session() as db:
        waitlist_one = WaitlistEntry(
            id=uuid.uuid4(),
            game_id=game_id,
            user_id=user_one_id,
            party_size=1,
            position=1,
            waitlist_status="active",
            joined_at=_BASE_TIME,
        )
        waitlist_two = WaitlistEntry(
            id=uuid.uuid4(),
            game_id=game_id,
            user_id=user_two_id,
            party_size=1,
            position=1,
            waitlist_status="active",
            joined_at=_BASE_TIME,
        )
        db.add_all([waitlist_one, waitlist_two])
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
