from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.observability.timeouts import DependencyMutationTimeoutUnknownError
from backend.schemas.checkout_schema import GameCheckoutPaymentIntentCreate
from backend.services.stripe_service import StripePaymentIntentResult

_STARTS_AT = datetime(2035, 3, 2, 18, 0, tzinfo=timezone.utc)
_ENDS_AT = _STARTS_AT + timedelta(hours=2)


@dataclass
class _CheckoutState:
    user_id: uuid.UUID
    game_id: uuid.UUID
    payment_method_id: uuid.UUID
    credit_id: uuid.UUID


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _count(db: Session, model: type[object]) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _stripe_timeout(operation: str) -> DependencyMutationTimeoutUnknownError:
    return DependencyMutationTimeoutUnknownError(
        provider_kind="stripe",
        operation=operation,
    )


def _create_checkout_state(db: Session) -> _CheckoutState:
    from backend.models import Game, GameCredit, User, UserPaymentMethod, Venue

    unique = uuid.uuid4()
    user = User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04c2-unknown-user-{unique}",
        role="player",
        email=f"ws02-04c2-unknown-user-{unique}@example.invalid",
        first_name="Unknown",
        last_name="Outcome",
        date_of_birth=date(1990, 1, 1),
        account_status="active",
        hosting_status="eligible",
        stripe_customer_id=f"cus_ws02_04c2_unknown_{unique}",
    )
    admin = User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04c2-unknown-admin-{unique}",
        role="admin",
        email=f"ws02-04c2-unknown-admin-{unique}@example.invalid",
        first_name="Unknown",
        last_name="Admin",
        account_status="active",
        hosting_status="eligible",
    )
    db.add_all([user, admin])
    db.flush()

    venue = Venue(
        id=uuid.uuid4(),
        name="C2 Unknown Field",
        address_line_1="2 Retry Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        created_by_user_id=admin.id,
        approved_by_user_id=admin.id,
        approved_at=datetime.now(timezone.utc),
    )
    db.add(venue)
    db.flush()

    game = Game(
        id=uuid.uuid4(),
        game_type="official",
        payment_collection_type="in_app",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="C2 Unknown Game",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=None,
        created_by_user_id=admin.id,
        starts_at=_STARTS_AT,
        ends_at=_ENDS_AT,
        starts_on_local=_STARTS_AT.date(),
        timezone="UTC",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=12,
        price_per_player_cents=1200,
        currency="USD",
        allow_guests=True,
        max_guests_per_booking=0,
        host_guest_max=0,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="official_standard",
        published_at=datetime.now(timezone.utc),
    )
    db.add(game)
    db.flush()

    payment_method = UserPaymentMethod(
        id=uuid.uuid4(),
        user_id=user.id,
        stripe_customer_id=user.stripe_customer_id,
        stripe_payment_method_id=f"pm_ws02_04c2_unknown_{unique}",
        card_fingerprint=f"ws02-04c2-unknown-{unique}",
        card_brand="visa",
        card_last4="4242",
        exp_month=12,
        exp_year=2035,
        method_status="active",
        is_default=True,
    )
    credit = GameCredit(
        id=uuid.uuid4(),
        user_id=user.id,
        amount_cents=700,
        available_cents=700,
        currency="USD",
        credit_status="active",
        credit_reason="support_adjustment",
        source_game_id=game.id,
        source_booking_id=None,
        source_payment_id=None,
        issued_by_user_id=admin.id,
        idempotency_key=f"ws02-04c2-unknown-credit-{unique}",
        note="synthetic C2 unknown-outcome credit",
    )
    db.add_all([payment_method, credit])
    db.commit()
    return _CheckoutState(
        user_id=user.id,
        game_id=game.id,
        payment_method_id=payment_method.id,
        credit_id=credit.id,
    )


def _request(state: _CheckoutState) -> GameCheckoutPaymentIntentCreate:
    return GameCheckoutPaymentIntentCreate(
        guest_count=0,
        payment_method_id=state.payment_method_id,
    )


def _install_common_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.services.checkout_service as checkout_service

    monkeypatch.setattr(checkout_service, "require_stripe_payments_enabled", lambda: None)
    monkeypatch.setattr(checkout_service, "get_stripe_currency", lambda: "USD")

    def saved_payment_method(db, payment_method_id, current_user, *, now):
        del current_user, now
        from backend.models import UserPaymentMethod

        return db.get(UserPaymentMethod, payment_method_id)

    monkeypatch.setattr(
        checkout_service,
        "get_current_user_saved_payment_method_for_checkout",
        saved_payment_method,
    )


@pytest.mark.requirement("WS02-04C2-R4", "WS02-04C2-R5", "WS02-04C2-R6")
def test_create_timeout_preserves_checkpoint_without_confirmation_or_blind_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import Booking, GameCredit, GameCreditUsage, Payment, User
    import backend.services.checkout_service as checkout_service

    _install_common_fakes(monkeypatch)
    create_calls: list[str] = []
    confirm_calls: list[str] = []

    def create_payment_intent(**kwargs):
        create_calls.append(kwargs["idempotency_key"])
        raise _stripe_timeout("stripe.payment_intent.create")

    def confirm_payment_intent(payment_intent_id: str, **kwargs):
        del payment_intent_id, kwargs
        confirm_calls.append("unexpected")
        raise AssertionError("confirm must not run after create timeout")

    monkeypatch.setattr(checkout_service, "create_payment_intent", create_payment_intent)
    monkeypatch.setattr(checkout_service, "confirm_payment_intent", confirm_payment_intent)

    with _session() as db:
        state = _create_checkout_state(db)
        current_user = db.get(User, state.user_id)

        with pytest.raises(DependencyMutationTimeoutUnknownError) as exc_info:
            checkout_service.create_game_checkout_payment_intent_workflow(
                db,
                state.game_id,
                _request(state),
                current_user,
            )
        credit = db.get(GameCredit, state.credit_id)
        payment = db.scalars(select(Payment)).one()
        booking = db.get(Booking, payment.booking_id)
        usage = db.scalars(select(GameCreditUsage)).one()
        assert exc_info.value.operation == "stripe.payment_intent.create"
        assert len(create_calls) == 1
        assert confirm_calls == []
        assert _count(db, Booking) == 1
        assert _count(db, Payment) == 1
        assert _count(db, GameCreditUsage) == 1
        assert booking.booking_status == "pending_payment"
        assert booking.payment_status == "processing"
        assert payment.provider_payment_intent_id is None
        assert payment.payment_status == "requires_payment_method"
        assert usage.usage_status == "reserved"
        assert credit.available_cents == 0


@pytest.mark.requirement("WS02-04C2-R5", "WS02-04C2-R6")
def test_confirmation_unknown_preserves_checkpoint_without_blind_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import Booking, GameCredit, GameCreditUsage, Payment, User
    import backend.services.checkout_service as checkout_service

    _install_common_fakes(monkeypatch)
    events: list[str] = []
    create_calls: list[str] = []

    def create_payment_intent(**kwargs):
        create_calls.append(kwargs["idempotency_key"])
        events.append("create")
        return StripePaymentIntentResult(
            id="pi_ws02_04c2_unknown",
            client_secret="client_secret_after_create",
            status="requires_payment_method",
            latest_charge_id=None,
        )

    def confirm_unknown(payment_intent_id: str, **kwargs):
        del kwargs
        events.append(f"confirm:{payment_intent_id}")
        raise _stripe_timeout("stripe.payment_intent.confirm")

    def retrieve_payment_intent(payment_intent_id: str):
        events.append(f"retrieve:{payment_intent_id}")
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="client_secret_after_retrieve",
            status="requires_payment_method",
            latest_charge_id=None,
        )

    monkeypatch.setattr(checkout_service, "create_payment_intent", create_payment_intent)
    monkeypatch.setattr(checkout_service, "confirm_payment_intent", confirm_unknown)
    monkeypatch.setattr(checkout_service, "retrieve_payment_intent", retrieve_payment_intent)

    with _session() as db:
        state = _create_checkout_state(db)
        current_user = db.get(User, state.user_id)

        with pytest.raises(DependencyMutationTimeoutUnknownError) as exc_info:
            checkout_service.create_game_checkout_payment_intent_workflow(
                db,
                state.game_id,
                _request(state),
                current_user,
            )
        db.rollback()

        payment = db.scalars(select(Payment)).one()
        booking = db.get(Booking, payment.booking_id)
        usage = db.scalars(select(GameCreditUsage)).one()
        credit = db.get(GameCredit, state.credit_id)

        assert exc_info.value.operation == "stripe.payment_intent.confirm"
        assert events == [
            "create",
            "retrieve:pi_ws02_04c2_unknown",
            "confirm:pi_ws02_04c2_unknown",
        ]
        assert payment.provider_payment_intent_id == "pi_ws02_04c2_unknown"
        assert payment.payment_status in {"requires_payment_method", "processing"}
        assert payment.payment_status not in {"succeeded", "failed", "canceled"}
        assert booking.booking_status == "pending_payment"
        assert booking.payment_status == "processing"
        assert booking.expires_at > datetime.now(timezone.utc)
        assert usage.usage_status == "reserved"
        assert usage.payment_id == payment.id
        assert credit.available_cents == 0
        assert create_calls == [payment.idempotency_key]

        monkeypatch.setattr(
            checkout_service,
            "confirm_payment_intent",
            lambda payment_intent_id, **kwargs: StripePaymentIntentResult(
                id=payment_intent_id,
                client_secret="client_secret_after_reentry_confirm",
                status="requires_action",
                latest_charge_id=None,
            ),
        )
        retry_result = checkout_service.create_game_checkout_payment_intent_workflow(
            db,
            state.game_id,
            _request(state),
            current_user,
        )
        usages = db.scalars(select(GameCreditUsage)).all()

        assert retry_result.booking_id == booking.id
        assert retry_result.payment_id == payment.id
        assert events == [
            "create",
            "retrieve:pi_ws02_04c2_unknown",
            "confirm:pi_ws02_04c2_unknown",
            "retrieve:pi_ws02_04c2_unknown",
        ]
        assert create_calls == [payment.idempotency_key]
        assert len(usages) == 1


@pytest.mark.requirement("WS02-04C2-R5", "WS02-04C2-R6")
def test_active_hold_confirmation_decision_is_serialized_after_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import GameCreditUsage, Payment, User
    import backend.services.checkout_service as checkout_service

    _install_common_fakes(monkeypatch)
    with _session() as setup_db:
        state = _create_checkout_state(setup_db)

    original_lock = checkout_service.get_locked_active_game_or_404
    request_label = threading.local()
    events: list[tuple[str, str, str]] = []
    events_lock = threading.Lock()
    first_in_confirmation = threading.Event()
    first_may_finish = threading.Event()
    second_lock_attempted = threading.Event()
    second_lock_acquired = threading.Event()
    provider_status = {"status": "requires_payment_method"}
    provider_id = "pi_ws02_04c2_serialized"
    results: dict[str, object] = {}
    errors: dict[str, BaseException] = {}

    def append_event(kind: str, value: str) -> None:
        label = getattr(request_label, "value", "unknown")
        with events_lock:
            events.append((label, kind, value))

    def locked_game(db, game_id):
        if getattr(request_label, "value", None) == "second":
            second_lock_attempted.set()
        game = original_lock(db, game_id)
        if getattr(request_label, "value", None) == "second":
            second_lock_acquired.set()
        return game

    def create_payment_intent(**kwargs):
        append_event("create", kwargs["idempotency_key"])
        return StripePaymentIntentResult(
            id=provider_id,
            client_secret="client_secret_after_create",
            status=provider_status["status"],
            latest_charge_id=None,
        )

    def retrieve_payment_intent(payment_intent_id: str):
        append_event("retrieve", payment_intent_id)
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret=f"client_secret_after_retrieve_{provider_status['status']}",
            status=provider_status["status"],
            latest_charge_id=None,
        )

    def confirm_payment_intent(payment_intent_id: str, **kwargs):
        del kwargs
        append_event("confirm", payment_intent_id)
        if getattr(request_label, "value", None) == "first":
            first_in_confirmation.set()
            assert first_may_finish.wait(timeout=10)
        provider_status["status"] = "requires_action"
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="client_secret_after_confirm",
            status=provider_status["status"],
            latest_charge_id=None,
        )

    monkeypatch.setattr(checkout_service, "get_locked_active_game_or_404", locked_game)
    monkeypatch.setattr(checkout_service, "create_payment_intent", create_payment_intent)
    monkeypatch.setattr(checkout_service, "retrieve_payment_intent", retrieve_payment_intent)
    monkeypatch.setattr(checkout_service, "confirm_payment_intent", confirm_payment_intent)

    def run_checkout(label: str) -> None:
        request_label.value = label
        try:
            with _session() as db:
                current_user = db.get(User, state.user_id)
                results[label] = checkout_service.create_game_checkout_payment_intent_workflow(
                    db,
                    state.game_id,
                    _request(state),
                    current_user,
                )
        except BaseException as exc:
            errors[label] = exc

    first = threading.Thread(target=run_checkout, args=("first",))
    second = threading.Thread(target=run_checkout, args=("second",))

    first.start()
    assert first_in_confirmation.wait(timeout=10)
    second.start()
    assert second_lock_attempted.wait(timeout=10)
    assert not second_lock_acquired.is_set()
    with events_lock:
        assert [event for event in events if event[0] == "second"] == []

    first_may_finish.set()
    first.join(timeout=10)
    assert not first.is_alive()
    assert "first" not in errors
    second.join(timeout=10)
    assert not second.is_alive()
    assert errors == {}

    first_result = results["first"]
    second_result = results["second"]
    assert second_lock_acquired.is_set()
    assert second_result.booking_id == first_result.booking_id
    assert second_result.payment_id == first_result.payment_id

    with events_lock:
        assert events == [
            ("first", "create", next(value for _, kind, value in events if kind == "create")),
            ("first", "retrieve", provider_id),
            ("first", "confirm", provider_id),
            ("second", "retrieve", provider_id),
        ]

    with _session() as verify_db:
        payments = verify_db.scalars(select(Payment)).all()
        usages = verify_db.scalars(select(GameCreditUsage)).all()

        assert len(payments) == 1
        assert payments[0].provider_payment_intent_id == provider_id
        assert payments[0].payment_status == "requires_action"
        assert len(usages) == 1
        assert usages[0].payment_id == payments[0].id
        assert usages[0].usage_status == "reserved"


@pytest.mark.requirement("WS02-04C2-R6")
def test_stale_checkout_expiration_releases_local_hold_but_keeps_provider_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import Booking, Game, GameCredit, GameCreditUsage, GameParticipant, Payment, User
    import backend.services.checkout_service as checkout_service

    _install_common_fakes(monkeypatch)
    monkeypatch.setattr(
        checkout_service,
        "create_payment_intent",
        lambda **kwargs: StripePaymentIntentResult(
            id="pi_ws02_04c2_expiry",
            client_secret="client_secret_after_create",
            status="requires_payment_method",
            latest_charge_id=None,
        ),
    )
    monkeypatch.setattr(
        checkout_service,
        "retrieve_payment_intent",
        lambda payment_intent_id: StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="client_secret_after_retrieve",
            status="requires_payment_method",
            latest_charge_id=None,
        ),
    )
    monkeypatch.setattr(
        checkout_service,
        "confirm_payment_intent",
        lambda payment_intent_id, **kwargs: (_ for _ in ()).throw(
            _stripe_timeout("stripe.payment_intent.confirm")
        ),
    )

    with _session() as db:
        state = _create_checkout_state(db)
        current_user = db.get(User, state.user_id)

        with pytest.raises(DependencyMutationTimeoutUnknownError):
            checkout_service.create_game_checkout_payment_intent_workflow(
                db,
                state.game_id,
                _request(state),
                current_user,
            )
        db.rollback()

        payment = db.scalars(select(Payment)).one()
        booking = db.get(Booking, payment.booking_id)
        game = db.get(Game, state.game_id)
        later = booking.expires_at + timedelta(seconds=1)
        checkout_service.expire_stale_pending_checkouts(db, game, later)
        db.commit()

        expired_payment = db.get(Payment, payment.id)
        expired_booking = db.get(Booking, booking.id)
        participant = db.scalars(select(GameParticipant)).one()
        usage = db.scalars(select(GameCreditUsage)).one()
        credit = db.get(GameCredit, state.credit_id)

        assert expired_booking.booking_status == "expired"
        assert expired_booking.payment_status == "failed"
        assert participant.participant_status == "cancelled"
        assert expired_payment.payment_status == "canceled"
        assert expired_payment.provider_payment_intent_id == "pi_ws02_04c2_expiry"
        assert usage.usage_status == "released"
        assert credit.available_cents == 700
