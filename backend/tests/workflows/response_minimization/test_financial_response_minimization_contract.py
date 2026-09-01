from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.suite_type("ordinary")

CHICAGO = ZoneInfo("America/Chicago")
UUID_PHONE_FALSE_POSITIVE = uuid.UUID("4b340077-7855-4d77-a0fb-558aba611ff5")

PAYMENT_SUMMARY_ALLOWED_FIELDS = {
    "id",
    "payer_user_id",
    "booking_id",
    "game_id",
    "payment_type",
    "amount_cents",
    "currency",
    "payment_status",
    "paid_at",
    "created_at",
}
PAYMENT_PROVIDER_FIELDS = {
    "provider",
    "provider_payment_intent_id",
    "provider_charge_id",
    "idempotency_key",
    "failure_code",
    "failure_message",
    "metadata",
    "payment_metadata",
    "updated_at",
}
REFUND_SUMMARY_ALLOWED_FIELDS = {
    "id",
    "payment_id",
    "booking_id",
    "participant_id",
    "host_publish_fee_id",
    "amount_cents",
    "currency",
    "refund_reason",
    "refund_status",
    "requested_at",
    "refunded_at",
    "created_at",
}
REFUND_PROVIDER_FIELDS = {
    "origin_workflow",
    "provider",
    "provider_refund_id",
    "provider_charge_id",
    "provider_status",
    "provider_status_observed_at",
    "last_refund_event_at",
    "requested_by_user_id",
    "approved_by_user_id",
    "approved_at",
    "updated_at",
}
SAVED_CARD_PROVIDER_FIELDS = {
    "stripe_customer_id",
    "stripe_payment_method_id",
    "card_fingerprint",
    "client_secret",
}
PAYMENT_EVENT_RAW_FIELDS = {"event_envelope", "raw_payload", "payload"}
CHECKOUT_PAYMENT_INTENT_ALLOWED_FIELDS = {
    "client_secret",
    "booking_id",
    "payment_id",
    "amount_cents",
    "currency",
    "stripe_status",
    "subtotal_cents",
    "platform_fee_cents",
    "checkout_total_cents",
    "available_credit_cents",
    "credit_applied_cents",
    "minimum_charge_adjustment_cents",
    "final_amount_due_cents",
    "stripe_amount_cents",
    "payment_required",
    "booking_status",
    "booking_payment_status",
    "reservation_status",
    "payment_status",
    "provider_status",
    "compensation_status",
}
CHECKOUT_STATUS_ALLOWED_FIELDS = {
    "booking_id",
    "booking_status",
    "booking_payment_status",
    "reservation_status",
    "payment_id",
    "payment_status",
    "provider_status",
    "compensation_status",
    "amount_cents",
    "currency",
    "subtotal_cents",
    "platform_fee_cents",
    "checkout_total_cents",
    "available_credit_cents",
    "credit_applied_cents",
    "minimum_charge_adjustment_cents",
    "final_amount_due_cents",
    "stripe_amount_cents",
    "payment_required",
}
CHECKOUT_PROVIDER_INTERNAL_FIELDS = {
    "provider",
    "provider_payment_intent_id",
    "provider_charge_id",
    "provider_event_id",
    "raw_payload",
    "payload",
    "idempotency_key",
    "reconciliation_status",
    "failure_code",
    "failure_message",
    "metadata",
    "payment_metadata",
    "processing_error",
}
SAVED_CARD_ALLOWED_FIELDS = {
    "id",
    "user_id",
    "card_brand",
    "card_last4",
    "exp_month",
    "exp_year",
    "method_status",
    "is_default",
    "created_at",
    "updated_at",
    "detached_at",
}
SETUP_INTENT_ALLOWED_FIELDS = {"client_secret"}


def _session() -> Session:
    from backend.database import SessionLocal

    return SessionLocal()


def _create_user(
    db: Session,
    *,
    role: str = "player",
    email_prefix: str = "b2-money",
):
    from backend.models import User

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        auth_user_id=f"{email_prefix}-{user_id}",
        role=role,
        email=f"{email_prefix}-{user_id}@example.invalid",
        email_verified_at=datetime.now(UTC),
        phone=f"+1555{str(user_id.int)[-10:]}",
        first_name="B2",
        last_name="Money",
        date_of_birth=date(1990, 1, 1),
        account_status="active",
        hosting_status="eligible",
    )
    db.add(user)
    db.flush()
    return user


def _create_venue(db: Session, *, admin_user):
    from backend.models import Venue

    venue = Venue(
        id=uuid.uuid4(),
        name="B2 Money Park",
        address_line_1="400 Summary St",
        city="Chicago",
        state="IL",
        postal_code="60602",
        country_code="US",
        venue_status="approved",
        is_active=True,
        created_by_user_id=admin_user.id,
        approved_by_user_id=admin_user.id,
        approved_at=datetime.now(UTC),
    )
    db.add(venue)
    db.flush()
    return venue


def _create_game(db: Session, *, host_user, admin_user, venue):
    from backend.models import Game

    starts_at = datetime.now(UTC).replace(microsecond=0) + timedelta(days=6)
    game = Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="external_host",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="B2 Financial Game",
        description="Payment response proof.",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot="400 Summary St, Chicago, IL 60602",
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        neighborhood_snapshot=None,
        host_user_id=host_user.id,
        created_by_user_id=admin_user.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        starts_on_local=starts_at.astimezone(CHICAGO).date(),
        timezone="America/Chicago",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=12,
        price_per_player_cents=1800,
        currency="USD",
        minimum_age=18,
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=4,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="custom_hosted",
        published_at=datetime.now(UTC),
    )
    db.add(game)
    db.flush()
    return game


def _create_checkout_game(db: Session, *, admin_user, venue):
    from backend.models import Game

    starts_at = datetime.now(UTC).replace(microsecond=0) + timedelta(days=7)
    game = Game(
        id=uuid.uuid4(),
        game_type="official",
        payment_collection_type="in_app",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="B2 Checkout Response Game",
        description="Checkout response projection proof.",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot="400 Summary St, Chicago, IL 60602",
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        neighborhood_snapshot=None,
        host_user_id=None,
        created_by_user_id=admin_user.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        starts_on_local=starts_at.astimezone(CHICAGO).date(),
        timezone="America/Chicago",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=12,
        price_per_player_cents=1800,
        currency="USD",
        minimum_age=None,
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=0,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="official_standard",
        custom_rules_text=None,
        custom_cancellation_text=None,
        published_at=datetime.now(UTC),
    )
    db.add(game)
    db.flush()
    return game


def _create_saved_card(
    db: Session,
    *,
    user,
    is_default: bool = True,
    card_last4: str = "4242",
    card_brand: str = "visa",
):
    from backend.models import UserPaymentMethod

    customer_id = user.stripe_customer_id or f"cus_{uuid.uuid4().hex}"
    user.stripe_customer_id = customer_id
    db.add(user)
    card = UserPaymentMethod(
        id=uuid.uuid4(),
        user_id=user.id,
        stripe_customer_id=customer_id,
        stripe_payment_method_id=f"pm_{uuid.uuid4().hex}",
        card_fingerprint=f"fingerprint-{uuid.uuid4()}",
        card_brand=card_brand,
        card_last4=card_last4,
        exp_month=12,
        exp_year=2035,
        method_status="active",
        is_default=is_default,
    )
    db.add(card)
    db.flush()
    return card


def _create_financial_rows(db: Session, *, payer, admin):
    from backend.models import (
        Booking,
        Payment,
        PaymentEvent,
        Refund,
    )

    venue = _create_venue(db, admin_user=admin)
    game = _create_game(db, host_user=payer, admin_user=admin, venue=venue)
    now = datetime.now(UTC)
    booking = Booking(
        id=uuid.uuid4(),
        game_id=game.id,
        buyer_user_id=payer.id,
        booking_status="confirmed",
        payment_status="paid",
        participant_count=1,
        subtotal_cents=1800,
        platform_fee_cents=200,
        discount_cents=0,
        total_cents=2000,
        currency="USD",
        price_per_player_snapshot_cents=1800,
        platform_fee_snapshot_cents=200,
        booked_at=now,
    )
    payment = Payment(
        id=uuid.uuid4(),
        payer_user_id=payer.id,
        booking_id=booking.id,
        game_id=None,
        payment_type="booking",
        provider="stripe",
        provider_payment_intent_id=f"pi_{uuid.uuid4().hex}",
        provider_charge_id=f"ch_{uuid.uuid4().hex}",
        idempotency_key=f"idem-{uuid.uuid4()}",
        amount_cents=2000,
        currency="USD",
        payment_status="succeeded",
        paid_at=now,
        failure_code="card_declined",
        failure_message="internal diagnostic should not serialize",
        payment_metadata={"internal": "not ordinary response"},
    )
    refund = Refund(
        id=uuid.uuid4(),
        payment_id=payment.id,
        booking_id=booking.id,
        provider_refund_id=f"re_{uuid.uuid4().hex}",
        origin_workflow="direct_admin_refund",
        provider="stripe",
        provider_status="processing",
        provider_status_observed_at=now,
        provider_charge_id=payment.provider_charge_id,
        last_refund_event_at=now,
        amount_cents=500,
        currency="USD",
        refund_reason="admin_refund",
        refund_status="processing",
        requested_by_user_id=admin.id,
        requested_at=now,
    )
    event = PaymentEvent(
        id=uuid.uuid4(),
        payment_id=payment.id,
        provider="stripe",
        provider_event_id=f"evt_{uuid.uuid4().hex}",
        event_type="payment_intent.succeeded",
        event_envelope={
            "id": "evt_safe_envelope",
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": payment.provider_payment_intent_id}},
        },
        provider_created_at=now,
        processing_status="processed",
        processed_at=now,
    )
    card = _create_saved_card(db, user=payer)
    db.add(booking)
    db.flush()
    db.add(payment)
    db.flush()
    db.add_all([refund, event])
    db.flush()
    return payment, refund, event, card


def _install_current_user_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import get_current_app_user

    app.dependency_overrides[get_current_app_user] = lambda: user


def _install_active_user_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import require_active_user

    app.dependency_overrides[require_active_user] = lambda: user


def _install_verified_user_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import require_verified_user

    app.dependency_overrides[require_verified_user] = lambda: user


def _install_recent_active_user_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import require_recent_active_user

    app.dependency_overrides[require_recent_active_user] = lambda: user


def _install_active_admin_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import require_active_admin

    app.dependency_overrides[require_active_admin] = lambda: user


def _commit_and_detach(db: Session, *objects: object) -> None:
    db.commit()
    for item in objects:
        db.refresh(item)
        db.expunge(item)


def _route(method: str, path: str) -> APIRoute:
    from backend.main import app

    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


@pytest.mark.requirement("WS02-05B2-R4")
def test_ordinary_payment_refund_and_saved_card_responses_omit_provider_internals(
    client: TestClient,
) -> None:
    with _session() as db:
        payer = _create_user(db, email_prefix="b2-money-payer")
        admin = _create_user(db, role="admin", email_prefix="b2-money-admin")
        payment, refund, _event, card = _create_financial_rows(db, payer=payer, admin=admin)
        payment_id = payment.id
        refund_id = refund.id
        card_id = card.id
        _commit_and_detach(db, payer)

    _install_current_user_override(payer)
    payment_response = client.get(f"/payments/{payment_id}")
    assert payment_response.status_code == 200
    payment_data = payment_response.json()
    assert set(payment_data) == PAYMENT_SUMMARY_ALLOWED_FIELDS
    assert PAYMENT_PROVIDER_FIELDS.isdisjoint(payment_data)

    payment_list_response = client.get("/payments")
    assert payment_list_response.status_code == 200
    listed_payment = next(
        item for item in payment_list_response.json() if item["id"] == str(payment_id)
    )
    assert set(listed_payment) == PAYMENT_SUMMARY_ALLOWED_FIELDS

    refund_response = client.get(f"/refunds/{refund_id}")
    assert refund_response.status_code == 200
    refund_data = refund_response.json()
    assert set(refund_data) == REFUND_SUMMARY_ALLOWED_FIELDS
    assert REFUND_PROVIDER_FIELDS.isdisjoint(refund_data)

    refund_list_response = client.get("/refunds")
    assert refund_list_response.status_code == 200
    listed_refund = next(
        item for item in refund_list_response.json() if item["id"] == str(refund_id)
    )
    assert set(listed_refund) == REFUND_SUMMARY_ALLOWED_FIELDS

    _install_active_user_override(payer)
    card_response = client.get(f"/user-payment-methods/{card_id}")
    assert card_response.status_code == 200
    card_data = card_response.json()
    assert SAVED_CARD_PROVIDER_FIELDS.isdisjoint(card_data)
    assert {"id", "user_id", "card_brand", "card_last4", "is_default"}.issubset(
        card_data
    )
    assert card_data["card_last4"] == "4242"

    card_list_response = client.get("/user-payment-methods")
    assert card_list_response.status_code == 200
    listed_card = next(item for item in card_list_response.json() if item["id"] == str(card_id))
    assert SAVED_CARD_PROVIDER_FIELDS.isdisjoint(listed_card)


@pytest.mark.requirement("WS02-05B2-R4")
def test_checkout_payment_intent_and_status_responses_are_product_projections(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import DurableJob
    from backend.services import checkout_service, payment_method_service
    from backend.services.stripe_service import (
        StripePaymentIntentResult,
        StripePaymentMethodCardResult,
    )

    original_build_pending_checkout_rows = checkout_service.build_pending_checkout_rows

    def build_pending_checkout_rows_with_regression_payment_id(*args, **kwargs):
        booking, payment, participants = original_build_pending_checkout_rows(
            *args, **kwargs
        )
        assert payment is not None
        payment.id = UUID_PHONE_FALSE_POSITIVE
        return booking, payment, participants

    monkeypatch.setattr(
        checkout_service,
        "build_pending_checkout_rows",
        build_pending_checkout_rows_with_regression_payment_id,
    )

    with _session() as db:
        payer = _create_user(db, email_prefix="b2-checkout-payer")
        admin = _create_user(db, role="admin", email_prefix="b2-checkout-admin")
        venue = _create_venue(db, admin_user=admin)
        game = _create_checkout_game(db, admin_user=admin, venue=venue)
        card = _create_saved_card(db, user=payer)
        game_id = game.id
        card_id = card.id
        customer_id = card.stripe_customer_id
        card_payment_method_id = card.stripe_payment_method_id
        card_fingerprint = card.card_fingerprint
        _commit_and_detach(db, payer)

    def fake_retrieve_payment_method(payment_method_id: str):
        assert payment_method_id == card_payment_method_id
        return StripePaymentMethodCardResult(
            id=payment_method_id,
            customer_id=customer_id,
            card_fingerprint=card_fingerprint,
            card_brand="visa",
            card_last4="4242",
            exp_month=12,
            exp_year=2035,
        )

    def fake_create_payment_intent(**kwargs):
        return StripePaymentIntentResult(
            id="pi_b2_checkout_synthetic",
            client_secret="pi_b2_checkout_synthetic_secret",
            status="requires_action",
            latest_charge_id=None,
            amount_cents=kwargs["amount_cents"],
            amount_received_cents=None,
            currency=kwargs["currency"],
            customer_id=kwargs["customer_id"],
            metadata=dict(kwargs["metadata"]),
        )

    monkeypatch.setattr(checkout_service, "stripe_payments_enabled", lambda: True)
    monkeypatch.setattr(checkout_service, "get_stripe_currency", lambda: "USD")
    monkeypatch.setattr(
        checkout_service,
        "create_payment_intent",
        fake_create_payment_intent,
    )
    monkeypatch.setattr(
        checkout_service,
        "retrieve_payment_intent",
        lambda _payment_intent_id: fake_create_payment_intent(
            amount_cents=1800,
            currency="USD",
            customer_id=customer_id,
            metadata={},
        ),
    )
    monkeypatch.setattr(
        payment_method_service,
        "retrieve_payment_method",
        fake_retrieve_payment_method,
    )

    _install_verified_user_override(payer)
    response = client.post(
        f"/checkout/games/{game_id}/payment-intent",
        json={"payment_method_id": str(card_id)},
    )
    assert response.status_code == 201
    payment_intent_data = response.json()
    assert set(payment_intent_data) == CHECKOUT_PAYMENT_INTENT_ALLOWED_FIELDS
    assert CHECKOUT_PROVIDER_INTERNAL_FIELDS.isdisjoint(payment_intent_data)
    assert payment_intent_data["client_secret"] == "pi_b2_checkout_synthetic_secret"
    assert payment_intent_data["currency"] == "USD"
    assert payment_intent_data["subtotal_cents"] == 1800
    assert payment_intent_data["checkout_total_cents"] == 1800
    assert payment_intent_data["payment_required"] is True
    assert payment_intent_data["booking_status"] == "pending_payment"
    assert payment_intent_data["booking_payment_status"] == "requires_action"
    assert payment_intent_data["payment_status"] == "requires_action"
    assert payment_intent_data["stripe_status"] == "requires_action"
    assert payment_intent_data["payment_id"] == str(UUID_PHONE_FALSE_POSITIVE)

    with _session() as db:
        reconcile_job = db.scalar(
            select(DurableJob).where(
                DurableJob.payload["payment_id"].as_string()
                == str(UUID_PHONE_FALSE_POSITIVE)
            )
        )
        assert reconcile_job is not None
        assert reconcile_job.payload == {
            "payment_id": str(UUID_PHONE_FALSE_POSITIVE)
        }

    _install_active_user_override(payer)
    status_response = client.get(
        f"/checkout/bookings/{payment_intent_data['booking_id']}/status"
    )
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert set(status_data) == CHECKOUT_STATUS_ALLOWED_FIELDS
    assert CHECKOUT_PROVIDER_INTERNAL_FIELDS.isdisjoint(status_data)
    assert "client_secret" not in status_data
    assert "stripe_status" not in status_data
    assert status_data["booking_id"] == payment_intent_data["booking_id"]
    assert status_data["payment_id"] == payment_intent_data["payment_id"]
    assert status_data["payment_required"] is True
    assert status_data["amount_cents"] == 1800
    assert status_data["booking_payment_status"] == "requires_action"
    assert status_data["payment_status"] == "requires_action"


@pytest.mark.requirement("WS02-05B2-R4")
def test_saved_payment_method_action_responses_are_narrow_contracts(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import payment_method_service
    from backend.services.stripe_service import (
        StripePaymentMethodCardResult,
        StripeSetupIntentResult,
    )

    with _session() as db:
        payer = _create_user(db, email_prefix="b2-card-action-payer")
        original_card = _create_saved_card(db, user=payer)
        customer_id = original_card.stripe_customer_id
        _commit_and_detach(db, payer)

    synced_payment_method_id = "pm_b2_synced_synthetic"
    synced_fingerprint = f"fingerprint-{uuid.uuid4()}"

    monkeypatch.setattr(
        payment_method_service,
        "stripe_payments_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        payment_method_service,
        "create_setup_intent",
        lambda **_kwargs: StripeSetupIntentResult(
            id="seti_b2_synthetic",
            client_secret="seti_b2_synthetic_secret",
            status="requires_payment_method",
            customer_id=customer_id,
            payment_method_id=None,
        ),
    )
    monkeypatch.setattr(
        payment_method_service,
        "retrieve_setup_intent",
        lambda _setup_intent_id: StripeSetupIntentResult(
            id="seti_b2_succeeded",
            client_secret=None,
            status="succeeded",
            customer_id=customer_id,
            payment_method_id=synced_payment_method_id,
        ),
    )
    monkeypatch.setattr(
        payment_method_service,
        "retrieve_payment_method",
        lambda payment_method_id: StripePaymentMethodCardResult(
            id=payment_method_id,
            customer_id=customer_id,
            card_fingerprint=synced_fingerprint,
            card_brand="mastercard",
            card_last4="5555",
            exp_month=11,
            exp_year=2036,
        ),
    )
    monkeypatch.setattr(
        payment_method_service,
        "set_customer_default_payment_method",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        payment_method_service,
        "detach_payment_method",
        lambda _payment_method_id, **_kwargs: None,
    )
    monkeypatch.setattr(
        payment_method_service,
        "clear_customer_default_payment_method",
        lambda **_kwargs: None,
    )

    _install_active_user_override(payer)
    setup_response = client.post(
        "/user-payment-methods/setup-intent",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={"set_as_default": True},
    )
    assert setup_response.status_code == 201
    setup_data = setup_response.json()
    assert set(setup_data) == SETUP_INTENT_ALLOWED_FIELDS
    assert setup_data["client_secret"] == "seti_b2_synthetic_secret"
    assert {
        "id",
        "user_id",
        "stripe_customer_id",
        "stripe_payment_method_id",
        "card_fingerprint",
    }.isdisjoint(setup_data)

    sync_response = client.post(
        "/user-payment-methods/sync",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={"setup_intent_id": "seti_b2_succeeded", "set_as_default": False},
    )
    assert sync_response.status_code == 201
    sync_data = sync_response.json()
    assert set(sync_data) == SAVED_CARD_ALLOWED_FIELDS
    assert SAVED_CARD_PROVIDER_FIELDS.isdisjoint(sync_data)
    assert sync_data["user_id"] == str(payer.id)
    assert sync_data["card_brand"] == "mastercard"
    assert sync_data["card_last4"] == "5555"
    assert sync_data["method_status"] == "active"

    _install_recent_active_user_override(payer)
    default_response = client.patch(
        f"/user-payment-methods/{sync_data['id']}/default",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert default_response.status_code == 200
    default_data = default_response.json()
    assert set(default_data) == SAVED_CARD_ALLOWED_FIELDS
    assert SAVED_CARD_PROVIDER_FIELDS.isdisjoint(default_data)
    assert default_data["id"] == sync_data["id"]
    assert default_data["is_default"] is True

    detach_response = client.delete(
        f"/user-payment-methods/{sync_data['id']}",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert detach_response.status_code == 200
    detach_data = detach_response.json()
    assert set(detach_data) == SAVED_CARD_ALLOWED_FIELDS
    assert SAVED_CARD_PROVIDER_FIELDS.isdisjoint(detach_data)
    assert detach_data["id"] == sync_data["id"]
    assert detach_data["method_status"] == "detached"
    assert detach_data["is_default"] is False
    assert detach_data["detached_at"] is not None


@pytest.mark.requirement("WS02-05B2-R4")
def test_payment_event_http_reads_exclude_raw_provider_payload(
    client: TestClient,
) -> None:
    with _session() as db:
        payer = _create_user(db, email_prefix="b2-event-payer")
        admin = _create_user(db, role="admin", email_prefix="b2-event-admin")
        _payment, _refund, event, _card = _create_financial_rows(db, payer=payer, admin=admin)
        event_id = event.id
        _commit_and_detach(db, admin)

    _install_active_admin_override(admin)
    event_response = client.get(f"/payment-events/{event_id}")
    assert event_response.status_code == 200
    event_data = event_response.json()
    assert PAYMENT_EVENT_RAW_FIELDS.isdisjoint(event_data)
    assert {
        "id",
        "payment_id",
        "provider",
        "provider_event_id",
        "event_type",
        "provider_created_at",
        "processing_status",
        "processed_at",
        "processing_error_code",
        "created_at",
    } == set(event_data)


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS02-05B2-R4")
def test_financial_response_models_split_ordinary_and_admin_surfaces() -> None:
    from backend.schemas import (
        AdminMoneyPaymentDetailRead,
        AdminMoneyPaymentListResponseRead,
        AdminMoneyRefundDetailRead,
        AdminMoneyRefundListResponseRead,
        GameCheckoutPaymentIntentRead,
        GameCheckoutStatusRead,
        PaymentEventRead,
        PaymentSummaryRead,
        RefundSummaryRead,
        UserPaymentMethodRead,
        UserPaymentMethodSetupIntentRead,
    )

    assert (
        _route("POST", "/checkout/games/{game_id}/payment-intent").response_model
        is GameCheckoutPaymentIntentRead
    )
    assert (
        _route("GET", "/checkout/bookings/{booking_id}/status").response_model
        is GameCheckoutStatusRead
    )
    assert _route("GET", "/payments").response_model == list[PaymentSummaryRead]
    assert _route("GET", "/payments/{payment_id}").response_model is PaymentSummaryRead
    assert _route("GET", "/refunds").response_model == list[RefundSummaryRead]
    assert _route("GET", "/refunds/{refund_id}").response_model is RefundSummaryRead
    assert _route("GET", "/payment-events").response_model == list[PaymentEventRead]
    assert _route("GET", "/payment-events/{payment_event_id}").response_model is PaymentEventRead
    assert _route("GET", "/user-payment-methods").response_model == list[
        UserPaymentMethodRead
    ]
    assert (
        _route("POST", "/user-payment-methods/setup-intent").response_model
        is UserPaymentMethodSetupIntentRead
    )
    assert _route("POST", "/user-payment-methods/sync").response_model is (
        UserPaymentMethodRead
    )
    assert (
        _route("GET", "/user-payment-methods/{payment_method_id}").response_model
        is UserPaymentMethodRead
    )
    assert (
        _route("PATCH", "/user-payment-methods/{payment_method_id}/default").response_model
        is UserPaymentMethodRead
    )
    assert (
        _route("DELETE", "/user-payment-methods/{payment_method_id}").response_model
        is UserPaymentMethodRead
    )

    assert _route("GET", "/admin/money/payments").response_model is (
        AdminMoneyPaymentListResponseRead
    )
    assert _route("GET", "/admin/money/payments/{payment_id}").response_model is (
        AdminMoneyPaymentDetailRead
    )
    assert _route("GET", "/admin/money/refunds").response_model is (
        AdminMoneyRefundListResponseRead
    )
    assert _route("GET", "/admin/money/refunds/{refund_id}").response_model is (
        AdminMoneyRefundDetailRead
    )
