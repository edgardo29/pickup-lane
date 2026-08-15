from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.schemas.checkout_schema import GameCheckoutPaymentIntentCreate
from backend.services.stripe_service import StripePaymentIntentResult

_STARTS_AT = datetime(2035, 3, 1, 18, 0, tzinfo=timezone.utc)
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


def _create_checkout_state(db: Session) -> _CheckoutState:
    from backend.models import Game, GameCredit, User, UserPaymentMethod, Venue

    unique = uuid.uuid4()
    user = User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04c2-checkout-user-{unique}",
        role="player",
        email=f"ws02-04c2-checkout-user-{unique}@example.invalid",
        first_name="Retry",
        last_name="Checkout",
        date_of_birth=date(1990, 1, 1),
        account_status="active",
        hosting_status="eligible",
        stripe_customer_id=f"cus_ws02_04c2_{unique}",
    )
    admin = User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04c2-checkout-admin-{unique}",
        role="admin",
        email=f"ws02-04c2-checkout-admin-{unique}@example.invalid",
        first_name="Retry",
        last_name="Admin",
        account_status="active",
        hosting_status="eligible",
    )
    db.add_all([user, admin])
    db.flush()

    venue = Venue(
        id=uuid.uuid4(),
        name="C2 Checkout Field",
        address_line_1="1 Retry Way",
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
        title="C2 Checkout Game",
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
        stripe_payment_method_id=f"pm_ws02_04c2_{unique}",
        card_fingerprint=f"ws02-04c2-checkout-{unique}",
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
        idempotency_key=f"ws02-04c2-credit-{unique}",
        note="synthetic C2 checkout credit",
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


def _install_checkout_boundary_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    create_calls: list[str],
    retrieve_calls: list[str],
    confirm_calls: list[str],
    confirm_status: str = "requires_action",
) -> None:
    import backend.services.checkout_service as checkout_service

    monkeypatch.setattr(checkout_service, "require_stripe_payments_enabled", lambda: None)
    monkeypatch.setattr(checkout_service, "get_stripe_currency", lambda: "USD")

    def saved_payment_method(db, payment_method_id, current_user, *, now):
        del current_user, now
        from backend.models import UserPaymentMethod

        return db.get(UserPaymentMethod, payment_method_id)

    def create_payment_intent(**kwargs):
        create_calls.append(kwargs["idempotency_key"])
        return StripePaymentIntentResult(
            id="pi_ws02_04c2_checkpoint",
            client_secret="client_secret_after_create",
            status="requires_payment_method",
            latest_charge_id=None,
        )

    def retrieve_payment_intent(payment_intent_id: str):
        retrieve_calls.append(payment_intent_id)
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="client_secret_after_retrieve",
            status="requires_payment_method",
            latest_charge_id=None,
        )

    def confirm_payment_intent(payment_intent_id: str, **kwargs):
        del kwargs
        confirm_calls.append(payment_intent_id)
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="client_secret_after_confirm",
            status=confirm_status,
            latest_charge_id=None,
        )

    monkeypatch.setattr(
        checkout_service,
        "get_current_user_saved_payment_method_for_checkout",
        saved_payment_method,
    )
    monkeypatch.setattr(checkout_service, "create_payment_intent", create_payment_intent)
    monkeypatch.setattr(checkout_service, "retrieve_payment_intent", retrieve_payment_intent)
    monkeypatch.setattr(checkout_service, "confirm_payment_intent", confirm_payment_intent)


@pytest.mark.requirement("WS02-04C2-R5", "WS02-04C2-R6")
def test_checkout_commits_durable_checkpoint_with_credit_before_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import Booking, GameCredit, GameCreditUsage, GameParticipant, Payment, User
    import backend.services.checkout_service as checkout_service

    create_calls: list[str] = []
    retrieve_calls: list[str] = []
    confirm_calls: list[str] = []
    checkpoint_seen_by_confirm: list[dict[str, object]] = []

    def assert_checkpoint_then_confirm(payment_intent_id: str, **kwargs):
        del kwargs
        confirm_calls.append(payment_intent_id)
        with _session() as independent:
            payment = independent.scalars(
                select(Payment).where(
                    Payment.provider_payment_intent_id == payment_intent_id
                )
            ).one()
            booking = independent.get(Booking, payment.booking_id)
            usages = independent.scalars(
                select(GameCreditUsage).where(GameCreditUsage.booking_id == booking.id)
            ).all()
            credit = independent.get(GameCredit, usages[0].game_credit_id)
            participant_count = independent.scalar(
                select(func.count())
                .select_from(GameParticipant)
                .where(GameParticipant.booking_id == booking.id)
            )
            checkpoint_seen_by_confirm.append(
                {
                    "booking_status": booking.booking_status,
                    "booking_payment_status": booking.payment_status,
                    "payment_status": payment.payment_status,
                    "idempotency_key": payment.idempotency_key,
                    "usage_status": usages[0].usage_status,
                    "available_cents": credit.available_cents,
                    "participant_count": int(participant_count or 0),
                }
            )
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="client_secret_after_confirm",
            status="requires_action",
            latest_charge_id=None,
        )

    _install_checkout_boundary_fakes(
        monkeypatch,
        create_calls=create_calls,
        retrieve_calls=retrieve_calls,
        confirm_calls=confirm_calls,
    )
    monkeypatch.setattr(
        checkout_service,
        "confirm_payment_intent",
        assert_checkpoint_then_confirm,
    )

    with _session() as db:
        state = _create_checkout_state(db)
        current_user = db.get(User, state.user_id)

        result = checkout_service.create_game_checkout_payment_intent_workflow(
            db,
            state.game_id,
            _request(state),
            current_user,
        )

        assert result.payment_required is True
        assert result.credit_applied_cents == 700
        assert result.stripe_amount_cents == 500
        assert create_calls == [db.get(Payment, result.payment_id).idempotency_key]
        assert retrieve_calls == ["pi_ws02_04c2_checkpoint"]
        assert confirm_calls == ["pi_ws02_04c2_checkpoint"]
        assert checkpoint_seen_by_confirm == [
            {
                "booking_status": "pending_payment",
                "booking_payment_status": "processing",
                "payment_status": "requires_payment_method",
                "idempotency_key": db.get(Payment, result.payment_id).idempotency_key,
                "usage_status": "reserved",
                "available_cents": 0,
                "participant_count": 1,
            }
        ]
        assert _count(db, Payment) == 1
        assert _count(db, Booking) == 1
        assert _count(db, GameCreditUsage) == 1


@pytest.mark.requirement("WS02-04C2-R5", "WS02-04C2-R6")
def test_active_hold_reentry_reuses_provider_identity_and_credit_reservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import GameCredit, GameCreditUsage, Payment, User
    import backend.services.checkout_service as checkout_service

    create_calls: list[str] = []
    retrieve_calls: list[str] = []
    confirm_calls: list[str] = []
    _install_checkout_boundary_fakes(
        monkeypatch,
        create_calls=create_calls,
        retrieve_calls=retrieve_calls,
        confirm_calls=confirm_calls,
    )

    with _session() as db:
        state = _create_checkout_state(db)
        current_user = db.get(User, state.user_id)

        first = checkout_service.create_game_checkout_payment_intent_workflow(
            db,
            state.game_id,
            _request(state),
            current_user,
        )
        second = checkout_service.create_game_checkout_payment_intent_workflow(
            db,
            state.game_id,
            _request(state),
            current_user,
        )

        payment = db.get(Payment, first.payment_id)
        credit = db.get(GameCredit, state.credit_id)
        usages = db.scalars(select(GameCreditUsage)).all()

        assert second.booking_id == first.booking_id
        assert second.payment_id == first.payment_id
        assert payment.provider_payment_intent_id == "pi_ws02_04c2_checkpoint"
        assert create_calls == [payment.idempotency_key]
        assert retrieve_calls == [
            "pi_ws02_04c2_checkpoint",
            "pi_ws02_04c2_checkpoint",
        ]
        assert confirm_calls == [
            "pi_ws02_04c2_checkpoint",
            "pi_ws02_04c2_checkpoint",
        ]
        assert len(usages) == 1
        assert usages[0].amount_cents == 700
        assert usages[0].usage_status == "reserved"
        assert credit.available_cents == 0


@pytest.mark.requirement("WS02-04C2-R5")
def test_registry_distinguishes_idempotency_identity_sources() -> None:
    import backend.services.provider_retry_policy as retry_policy

    contexts = {
        policy.workflow_context: policy
        for policy in retry_policy.PROVIDER_OPERATION_RETRY_POLICIES
    }

    assert contexts["saved_card_customer_creation"].idempotency_identity_source == (
        "deterministic user-scoped key user:{user.id}:stripe_customer"
    )
    assert "request-local" in contexts[
        "saved_card_setup_intent_creation"
    ].idempotency_identity_source
    assert "rolls back" in contexts[
        "checkout_initial_create_before_provider_result"
    ].idempotency_identity_source
    assert "rolled back" in contexts[
        "community_publish_fee_initial_create"
    ].idempotency_identity_source
    assert contexts["admin_refund_retry"].identity_survives_replay
    assert contexts["waitlist_auto_promotion_create"].identity_survives_replay
