from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Booking, CommunityGameDetail, Game, User, Venue
from backend.schemas.booking_schema import BookingRead
from backend.schemas.community_game_detail_schema import CommunityGameDetailCreate
from backend.schemas.user_schema import UserRead
import backend.services.stripe_service as stripe_service

pytestmark = pytest.mark.suite_type("ordinary")

_NOW = datetime(2035, 8, 1, 15, 0, tzinfo=timezone.utc)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _assert_aware(value: datetime) -> None:
    assert value.tzinfo is not None
    assert value.utcoffset() is not None


def _from_json_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _user(index: int = 1) -> User:
    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws04-02c-user-{index}-{unique}",
        email=f"ws04-02c-user-{index}-{unique}@example.invalid",
        first_name="Value",
        last_name=f"User{index}",
        date_of_birth=date(1990, 1, 1),
    )


def _venue(index: int = 1) -> Venue:
    return Venue(
        id=uuid.uuid4(),
        name=f"WS04-02C Court {index}",
        address_line_1="1 Value Contract Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        venue_status="approved",
        is_active=True,
    )


def _game(host: User, venue: Venue, index: int, *, official: bool = False) -> Game:
    starts_at = _NOW + timedelta(days=index)
    return Game(
        id=uuid.uuid4(),
        game_type="official" if official else "community",
        payment_collection_type="in_app" if official else "none",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title=f"WS04-02C Game {index}",
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
        total_spots=12,
        price_per_player_cents=1200 if official else 0,
        currency="USD",
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=0,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="official_standard" if official else "custom_hosted",
        published_at=_NOW,
    )


def _booking(user: User, game: Game, *, currency: str = "USD") -> Booking:
    return Booking(
        id=uuid.uuid4(),
        game_id=game.id,
        buyer_user_id=user.id,
        participant_count=1,
        subtotal_cents=1200,
        total_cents=1200,
        currency=currency,
        price_per_player_snapshot_cents=1200,
        expires_at=_NOW + timedelta(minutes=15),
    )


@pytest.mark.requirement("WS04-02C-R2", "WS04-02C-R4", "WS04-02C-R8")
def test_postgresql_status_and_timestamp_defaults_round_trip_through_api_schemas() -> None:
    with _session() as db:
        user = _user()
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.role == "player"
        assert user.account_status == "active"
        assert user.hosting_status == "not_eligible"
        _assert_aware(user.member_since)
        _assert_aware(user.created_at)
        _assert_aware(user.updated_at)

        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        _assert_aware(user.updated_at)

        serialized_user = UserRead.model_validate(user).model_dump(mode="json")
        _assert_aware(_from_json_datetime(serialized_user["created_at"]))
        _assert_aware(_from_json_datetime(serialized_user["updated_at"]))

        venue = _venue()
        db.add(venue)
        db.commit()
        game = _game(user, venue, 1, official=True)
        db.add(game)
        db.commit()
        booking = _booking(user, game)
        db.add(booking)
        db.commit()
        db.refresh(booking)

        assert booking.booking_status == "pending_payment"
        assert booking.payment_status == "unpaid"
        assert booking.platform_fee_cents == 0
        assert booking.discount_cents == 0
        assert booking.platform_fee_snapshot_cents == 0
        assert booking.currency == "USD"
        _assert_aware(booking.created_at)
        _assert_aware(booking.updated_at)

        serialized_booking = BookingRead.model_validate(booking).model_dump(mode="json")
        _assert_aware(_from_json_datetime(serialized_booking["created_at"]))
        assert serialized_booking["subtotal_cents"] == 1200
        assert serialized_booking["total_cents"] == 1200
        assert serialized_booking["currency"] == "USD"


@pytest.mark.requirement("WS04-02C-R3", "WS04-02C-R8")
def test_money_currency_constraints_reject_unsupported_currency_at_postgresql_boundary() -> None:
    with _session() as db:
        user = _user()
        venue = _venue()
        db.add_all([user, venue])
        db.commit()
        game = _game(user, venue, 1, official=True)
        db.add(game)
        db.commit()

        db.add(_booking(user, game, currency="EUR"))
        with pytest.raises(IntegrityError) as exc_info:
            db.commit()

        constraint_name = getattr(
            getattr(exc_info.value.orig, "diag", None),
            "constraint_name",
            "",
        )
        assert constraint_name in {"ck_bookings_currency", ""}


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS04-02C-R3", "WS04-02C-R8")
def test_stripe_adapter_sends_integer_cents_without_float_conversion(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakePaymentIntents:
        def __init__(self) -> None:
            self.calls: list[tuple[dict[str, object], dict[str, object]]] = []

        def create(self, payload: dict[str, object], *, options: dict[str, object]):
            self.calls.append((payload, options))
            return SimpleNamespace(
                id="pi_ws04_02c",
                client_secret=None,
                status="requires_payment_method",
                latest_charge=None,
            )

    payment_intents = _FakePaymentIntents()
    fake_client = SimpleNamespace(
        v1=SimpleNamespace(payment_intents=payment_intents)
    )
    monkeypatch.setattr(
        stripe_service,
        "get_stripe_client_pair",
        lambda: stripe_service.StripeClientPair(read=fake_client, mutation=fake_client),
    )

    result = stripe_service.create_payment_intent(
        amount_cents=1234,
        currency="USD",
        idempotency_key="ws04-02c-payment-intent",
        metadata={"booking_id": uuid.uuid4()},
    )

    payload, options = payment_intents.calls[0]
    assert result.id == "pi_ws04_02c"
    assert payload["amount"] == 1234
    assert isinstance(payload["amount"], int)
    assert payload["currency"] == "usd"
    assert options == {"idempotency_key": "ws04-02c-payment-intent"}


@pytest.mark.requirement("WS04-02C-R5", "WS04-02C-R8")
def test_json_defaults_round_trip_as_independent_postgresql_values_and_schema_defaults() -> None:
    create_one = CommunityGameDetailCreate(game_id=uuid.uuid4())
    create_two = CommunityGameDetailCreate(game_id=uuid.uuid4())
    assert create_one.payment_methods_snapshot == []
    assert create_two.payment_methods_snapshot == []
    assert create_one.payment_methods_snapshot is not create_two.payment_methods_snapshot

    with _session() as db:
        user = _user()
        venue = _venue()
        db.add_all([user, venue])
        db.commit()
        first_game = _game(user, venue, 1)
        second_game = _game(user, venue, 2)
        db.add_all([first_game, second_game])
        db.commit()

        first_detail = CommunityGameDetail(id=uuid.uuid4(), game_id=first_game.id)
        second_detail = CommunityGameDetail(id=uuid.uuid4(), game_id=second_game.id)
        db.add_all([first_detail, second_detail])
        db.commit()
        db.refresh(first_detail)
        db.refresh(second_detail)

        assert first_detail.payment_methods_snapshot == []
        assert second_detail.payment_methods_snapshot == []
        assert first_detail.payment_text_moderation_status == "visible"
        _assert_aware(first_detail.created_at)

        first_detail.payment_methods_snapshot = [{"type": "cash_app"}]
        db.commit()
        db.refresh(first_detail)
        db.refresh(second_detail)

        assert first_detail.payment_methods_snapshot == [{"type": "cash_app"}]
        assert second_detail.payment_methods_snapshot == []
