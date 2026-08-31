from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from threading import Barrier

import pytest
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    DurableJob,
    Game,
    GameParticipant,
    Payment,
    PaymentCompensation,
    PaymentEvent,
    PaymentMethodOperation,
    User,
    UserPaymentMethod,
    Venue,
    WaitlistEntry,
)
from backend.observability.timeouts import PublicTimeoutError
from backend.schemas.checkout_schema import GameCheckoutPaymentIntentCreate
from backend.services.payment_lifecycle_policy import canonical_fingerprint
from backend.services.stripe_service import (
    StripePaymentIntentResult,
    StripePaymentMethodCardResult,
    StripeSetupIntentResult,
)


@dataclass(frozen=True)
class _BookingPaymentState:
    user_id: uuid.UUID
    admin_id: uuid.UUID
    game_id: uuid.UUID
    booking_id: uuid.UUID
    participant_id: uuid.UUID
    payment_id: uuid.UUID


def _session() -> Session:
    from backend.database import SessionLocal

    return SessionLocal()


def _create_booking_payment_state(
    db: Session,
    *,
    now: datetime,
    expires_at: datetime | None,
    total_spots: int = 4,
    payment_status: str = "processing",
    provider_status: str = "processing",
) -> _BookingPaymentState:
    unique = uuid.uuid4()
    user = User(
        id=uuid.uuid4(),
        auth_user_id=f"ws05-02-user-{unique}",
        role="player",
        email=f"ws05-02-user-{unique}@example.invalid",
        first_name="Payment",
        last_name="State",
        account_status="active",
        hosting_status="eligible",
        stripe_customer_id=f"cus_ws05_02_{unique}",
    )
    admin = User(
        id=uuid.uuid4(),
        auth_user_id=f"ws05-02-admin-{unique}",
        role="admin",
        email=f"ws05-02-admin-{unique}@example.invalid",
        first_name="Payment",
        last_name="Admin",
        account_status="active",
        hosting_status="eligible",
    )
    db.add_all([user, admin])
    db.flush()

    venue = Venue(
        id=uuid.uuid4(),
        name="WS05-02 State Field",
        address_line_1="502 State Machine Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        created_by_user_id=admin.id,
        approved_by_user_id=admin.id,
        approved_at=now,
    )
    db.add(venue)
    db.flush()

    starts_at = now + timedelta(days=30)
    game = Game(
        id=uuid.uuid4(),
        game_type="official",
        payment_collection_type="in_app",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="WS05-02 State Machine Game",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=None,
        created_by_user_id=admin.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        starts_on_local=date.fromisoformat(starts_at.date().isoformat()),
        timezone="UTC",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=total_spots,
        price_per_player_cents=1600,
        currency="USD",
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=0,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="official_standard",
        published_at=now,
    )
    db.add(game)
    db.flush()

    booking = Booking(
        id=uuid.uuid4(),
        game_id=game.id,
        buyer_user_id=user.id,
        booking_status="pending_payment",
        payment_status="processing",
        reservation_status="held",
        participant_count=1,
        subtotal_cents=1600,
        platform_fee_cents=0,
        discount_cents=0,
        total_cents=1600,
        currency="USD",
        price_per_player_snapshot_cents=1600,
        platform_fee_snapshot_cents=0,
        expires_at=expires_at,
    )
    db.add(booking)
    db.flush()

    participant = GameParticipant(
        id=uuid.uuid4(),
        game_id=game.id,
        booking_id=booking.id,
        participant_type="registered_user",
        user_id=user.id,
        display_name_snapshot="Payment State",
        participant_status="pending_payment",
        attendance_status="unknown",
        cancellation_type="none",
        price_cents=1600,
        currency="USD",
        joined_at=now,
    )
    payment = Payment(
        id=uuid.uuid4(),
        payer_user_id=user.id,
        booking_id=booking.id,
        game_id=game.id,
        payment_type="booking",
        provider="stripe",
        provider_payment_intent_id=f"pi_ws05_02_{unique}",
        provider_customer_id=user.stripe_customer_id,
        provider_status=provider_status,
        idempotency_key=f"ws05-02-payment-{unique}",
        creation_fingerprint=unique.hex + unique.hex,
        amount_cents=1600,
        currency="USD",
        payment_status=payment_status,
        payment_metadata={
            "user_id": str(user.id),
            "booking_id": str(booking.id),
            "payment_id": "pending",
            "game_id": str(game.id),
        },
    )
    payment.payment_metadata["payment_id"] = str(payment.id)
    payment.creation_fingerprint = canonical_fingerprint(
        {
            "payment_id": str(payment.id),
            "booking_id": str(booking.id),
            "payer_user_id": str(user.id),
            "provider_customer_id": user.stripe_customer_id,
            "amount_cents": payment.amount_cents,
            "currency": payment.currency,
            "game_id": str(booking.game_id),
            "participant_count": booking.participant_count,
            "credit_applied_cents": 0,
            "checkout_total_cents": None,
        }
    )
    db.add_all([participant, payment])
    db.commit()
    return _BookingPaymentState(
        user_id=user.id,
        admin_id=admin.id,
        game_id=game.id,
        booking_id=booking.id,
        participant_id=participant.id,
        payment_id=payment.id,
    )


def _apply_observation(
    db: Session,
    state: _BookingPaymentState,
    *,
    provider_status: str,
    now: datetime,
) -> str:
    from backend.services.stripe_webhook_service import (
        apply_authoritative_payment_intent_observation,
    )

    payment = db.get(Payment, state.payment_id)
    return apply_authoritative_payment_intent_observation(
        db,
        payment=payment,
        observation=StripePaymentIntentResult(
            id=payment.provider_payment_intent_id,
            client_secret=None,
            status=provider_status,
            latest_charge_id=(
                f"ch_{state.payment_id.hex}" if provider_status == "succeeded" else None
            ),
            amount_cents=payment.amount_cents,
            amount_received_cents=(
                payment.amount_cents if provider_status == "succeeded" else None
            ),
            currency=payment.currency,
            customer_id=payment.provider_customer_id,
            metadata=dict(payment.payment_metadata or {}),
        ),
        source=f"test_{provider_status}",
        now=now,
    )


@pytest.mark.requirement("WS05-02-R2", "WS05-02-R5")
def test_unfamiliar_provider_status_is_preserved_without_false_failure() -> None:
    now = datetime(2035, 1, 1, 12, 0, tzinfo=timezone.utc)
    with _session() as db:
        state = _create_booking_payment_state(
            db,
            now=now,
            expires_at=now + timedelta(minutes=2),
        )
        assert (
            _apply_observation(
                db,
                state,
                provider_status="requires_mandate",
                now=now + timedelta(seconds=10),
            )
            == "processed"
        )
        db.commit()

        payment = db.get(Payment, state.payment_id)
        booking = db.get(Booking, state.booking_id)
        assert payment.provider_status == "requires_mandate"
        assert payment.payment_status == "unknown"
        assert booking.booking_status == "pending_payment"
        assert booking.reservation_status == "held"


@pytest.mark.requirement("WS05-02-R2", "WS05-02-R5")
def test_ordinary_provider_cancellation_fails_and_releases_booking() -> None:
    now = datetime(2035, 1, 2, 12, 0, tzinfo=timezone.utc)
    with _session() as db:
        state = _create_booking_payment_state(
            db,
            now=now,
            expires_at=now + timedelta(minutes=2),
        )
        assert (
            _apply_observation(
                db,
                state,
                provider_status="canceled",
                now=now + timedelta(seconds=10),
            )
            == "processed"
        )
        db.commit()

        payment = db.get(Payment, state.payment_id)
        booking = db.get(Booking, state.booking_id)
        participant = db.get(GameParticipant, state.participant_id)
        assert (payment.provider_status, payment.payment_status) == (
            "canceled",
            "canceled",
        )
        assert (booking.booking_status, booking.reservation_status) == (
            "failed",
            "released",
        )
        assert booking.expires_at is None
        assert participant.participant_status == "cancelled"


@pytest.mark.requirement("WS05-02-R2", "WS05-02-R5")
@pytest.mark.parametrize(
    ("payment_status", "provider_status"),
    (
        ("requires_payment_method", "requires_payment_method"),
        ("requires_confirmation", "requires_confirmation"),
        ("requires_action", "requires_action"),
        ("processing", "processing"),
        ("requires_capture", "requires_capture"),
        ("unknown", "requires_mandate"),
    ),
)
def test_exact_expiry_releases_every_unresolved_state_without_rewriting_provider_truth(
    payment_status: str,
    provider_status: str,
) -> None:
    from backend.services.checkout_service import expire_stale_pending_checkouts

    expires_at = datetime(2035, 1, 3, 12, 2, tzinfo=timezone.utc)
    with _session() as db:
        state = _create_booking_payment_state(
            db,
            now=expires_at - timedelta(minutes=2),
            expires_at=expires_at,
            payment_status=payment_status,
            provider_status=provider_status,
        )
        game = db.get(Game, state.game_id)
        expire_stale_pending_checkouts(
            db,
            game,
            expires_at,
            enqueue_reconciliation=False,
        )
        db.commit()

        payment = db.get(Payment, state.payment_id)
        booking = db.get(Booking, state.booking_id)
        participant = db.get(GameParticipant, state.participant_id)
        assert (payment.payment_status, payment.provider_status) == (
            payment_status,
            provider_status,
        )
        assert (booking.booking_status, booking.reservation_status) == (
            "expired",
            "released",
        )
        assert booking.expires_at is None
        assert participant.participant_status == "cancelled"


@pytest.mark.requirement("WS05-02-R3", "WS05-02-R5")
def test_late_success_is_truthful_and_compensation_is_idempotent() -> None:
    from backend.services.checkout_service import expire_stale_pending_checkouts

    expires_at = datetime(2035, 1, 4, 12, 2, tzinfo=timezone.utc)
    with _session() as db:
        state = _create_booking_payment_state(
            db,
            now=expires_at - timedelta(minutes=2),
            expires_at=expires_at,
        )
        expire_stale_pending_checkouts(
            db,
            db.get(Game, state.game_id),
            expires_at,
            enqueue_reconciliation=False,
        )
        db.commit()

        for offset in (1, 2):
            assert (
                _apply_observation(
                    db,
                    state,
                    provider_status="succeeded",
                    now=expires_at + timedelta(seconds=offset),
                )
                == "processed"
            )
            db.commit()

        payment = db.get(Payment, state.payment_id)
        booking = db.get(Booking, state.booking_id)
        assert payment.payment_status == "succeeded"
        assert (booking.booking_status, booking.reservation_status) == (
            "expired",
            "released",
        )
        compensations = db.scalars(select(PaymentCompensation)).all()
        assert len(compensations) == 1
        assert compensations[0].reason == "reservation_expired"
        assert compensations[0].status == "required"


@pytest.mark.requirement("WS05-02-R2", "WS05-02-R5", "WS05-02-R7")
def test_reconcile_timeout_expires_stale_hold_without_rewriting_provider_truth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.payment_transition_service as transition_service

    with _session() as db:
        expires_at = db.scalar(select(func.now())) - timedelta(seconds=1)
        state = _create_booking_payment_state(
            db,
            now=expires_at - timedelta(minutes=2),
            expires_at=expires_at,
            payment_status="processing",
            provider_status="processing",
        )

        def timeout_payment_intent(_payment_intent_id: str):
            raise PublicTimeoutError("Stripe read timed out")

        monkeypatch.setattr(
            transition_service,
            "retrieve_payment_intent",
            timeout_payment_intent,
        )

        assert transition_service.reconcile_payment_intent(db, state.payment_id) == "retry"
        db.commit()

        payment = db.get(Payment, state.payment_id)
        booking = db.get(Booking, state.booking_id)
        participant = db.get(GameParticipant, state.participant_id)
        assert (payment.payment_status, payment.provider_status) == (
            "processing",
            "processing",
        )
        assert (booking.booking_status, booking.reservation_status) == (
            "expired",
            "released",
        )
        assert booking.expires_at is None
        assert participant.participant_status == "cancelled"


@pytest.mark.requirement("WS05-02-R2", "WS05-02-R4", "WS05-02-R5")
def test_stored_webhook_read_timeout_expires_stale_hold_and_keeps_event_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.stripe_webhook_service as webhook_service

    with _session() as db:
        expires_at = db.scalar(select(func.now())) - timedelta(seconds=1)
        state = _create_booking_payment_state(
            db,
            now=expires_at - timedelta(minutes=2),
            expires_at=expires_at,
            payment_status="processing",
            provider_status="processing",
        )
        payment = db.get(Payment, state.payment_id)
        event = PaymentEvent(
            id=uuid.uuid4(),
            payment_id=None,
            provider="stripe",
            provider_event_id=f"evt_ws05_timeout_{uuid.uuid4()}",
            event_type="payment_intent.processing",
            event_envelope={
                "id": f"evt_ws05_timeout_{uuid.uuid4()}",
                "type": "payment_intent.processing",
                "created": int(expires_at.timestamp()),
                "data": {
                    "object": {
                        "id": payment.provider_payment_intent_id,
                        "status": "processing",
                    }
                },
            },
            provider_created_at=expires_at,
            processing_status="pending",
            created_at=expires_at,
        )
        db.add(event)
        db.commit()

        def timeout_payment_intent(_payment_intent_id: str):
            raise PublicTimeoutError("Stripe read timed out")

        monkeypatch.setattr(
            webhook_service,
            "retrieve_payment_intent",
            timeout_payment_intent,
        )

        assert webhook_service.process_stored_stripe_event(db, event.id) == "retry"
        db.commit()

        payment = db.get(Payment, state.payment_id)
        booking = db.get(Booking, state.booking_id)
        event = db.get(PaymentEvent, event.id)
        assert event.payment_id == payment.id
        assert event.processing_status == "pending"
        assert event.processing_error_code == "stripe_payment_intent_read_timeout"
        assert (payment.payment_status, payment.provider_status) == (
            "processing",
            "processing",
        )
        assert (booking.booking_status, booking.reservation_status) == (
            "expired",
            "released",
        )


@pytest.mark.requirement("WS05-02-R2", "WS05-02-R3", "WS05-02-R5")
def test_late_success_after_local_cancellation_preserves_cancellation_outcome() -> None:
    now = datetime(2035, 1, 4, 15, 0, tzinfo=timezone.utc)
    with _session() as db:
        state = _create_booking_payment_state(
            db,
            now=now,
            expires_at=now + timedelta(minutes=2),
            payment_status="failed",
            provider_status="requires_action",
        )
        booking = db.get(Booking, state.booking_id)
        participant = db.get(GameParticipant, state.participant_id)
        booking.booking_status = "cancelled"
        booking.payment_status = "failed"
        booking.reservation_status = "released"
        booking.expires_at = None
        booking.cancelled_at = now
        booking.cancel_reason = "Local cancellation before provider success."
        participant.participant_status = "cancelled"
        participant.attendance_status = "not_applicable"
        participant.cancelled_at = now
        db.add_all([booking, participant])
        db.commit()

        assert (
            _apply_observation(
                db,
                state,
                provider_status="succeeded",
                now=now + timedelta(seconds=30),
            )
            == "processed"
        )
        db.commit()

        payment = db.get(Payment, state.payment_id)
        booking = db.get(Booking, state.booking_id)
        compensation = db.scalar(
            select(PaymentCompensation).where(
                PaymentCompensation.payment_id == state.payment_id
            )
        )
        assert (payment.payment_status, payment.provider_status) == (
            "succeeded",
            "succeeded",
        )
        assert (booking.booking_status, booking.reservation_status) == (
            "cancelled",
            "released",
        )
        assert compensation.reason == "booking_cancelled"
        assert compensation.status == "required"


@pytest.mark.requirement("WS05-02-R2", "WS05-02-R3", "WS05-02-R5")
def test_success_confirms_held_party_but_conflicts_when_total_capacity_is_exceeded() -> None:
    now = datetime(2035, 1, 5, 12, 0, tzinfo=timezone.utc)
    with _session() as db:
        state = _create_booking_payment_state(
            db,
            now=now,
            expires_at=now + timedelta(minutes=2),
            total_spots=1,
        )
        assert (
            _apply_observation(
                db,
                state,
                provider_status="succeeded",
                now=now + timedelta(seconds=10),
            )
            == "processed"
        )
        db.commit()
        booking = db.get(Booking, state.booking_id)
        assert (booking.booking_status, booking.reservation_status) == (
            "confirmed",
            "confirmed",
        )

    with _session() as db:
        state = _create_booking_payment_state(
            db,
            now=now,
            expires_at=now + timedelta(minutes=2),
            total_spots=1,
        )
        db.add(
            GameParticipant(
                id=uuid.uuid4(),
                game_id=state.game_id,
                booking_id=None,
                participant_type="admin_added",
                user_id=state.admin_id,
                display_name_snapshot="Existing Player",
                participant_status="confirmed",
                attendance_status="unknown",
                cancellation_type="none",
                price_cents=0,
                currency="USD",
                roster_order=1,
                joined_at=now,
                confirmed_at=now,
            )
        )
        db.commit()
        assert (
            _apply_observation(
                db,
                state,
                provider_status="succeeded",
                now=now + timedelta(seconds=10),
            )
            == "processed"
        )
        db.commit()

        payment = db.get(Payment, state.payment_id)
        booking = db.get(Booking, state.booking_id)
        participant = db.get(GameParticipant, state.participant_id)
        compensation = db.scalar(
            select(PaymentCompensation).where(
                PaymentCompensation.payment_id == state.payment_id
            )
        )
        assert payment.payment_status == "succeeded"
        assert (booking.booking_status, booking.reservation_status) == (
            "capacity_conflict",
            "capacity_conflict",
        )
        assert participant.participant_status == "cancelled"
        assert compensation.reason == "capacity_conflict"


@pytest.mark.requirement("WS05-02-R4", "WS05-02-R5")
def test_duplicate_webhook_persists_one_event_and_one_internal_job() -> None:
    from backend.services.stripe_webhook_service import (
        record_and_process_stripe_webhook_event,
    )

    event_id = f"evt_ws05_02_{uuid.uuid4()}"
    event_payload = {
        "id": event_id,
        "type": "payment_intent.processing",
        "created": 2_052_000_000,
        "data": {"object": {"id": "pi_unmatched", "status": "processing"}},
    }
    with _session() as db:
        first = record_and_process_stripe_webhook_event(db, event_payload)
        second = record_and_process_stripe_webhook_event(db, event_payload)
        assert first["duplicate"] is False
        assert second["duplicate"] is True
        assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 1
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 1
        job = db.scalar(select(DurableJob))
        event = db.scalar(select(PaymentEvent))
        assert job.payload == {"payment_event_id": str(event.id)}
        assert job.protected_identity == {"payment_event_id": str(event.id)}


@pytest.mark.requirement("WS05-02-R6", "WS05-02-R7")
def test_payment_method_reconcile_leaves_final_state_for_job_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import payment_method_service

    unique = uuid.uuid4()
    operation_key = uuid.uuid4()
    with _session() as db:
        user = User(
            id=uuid.uuid4(),
            auth_user_id=f"ws05-02-operation-user-{unique}",
            role="player",
            email=f"ws05-02-operation-user-{unique}@example.invalid",
            first_name="Durable",
            last_name="Operation",
            account_status="active",
            hosting_status="eligible",
            stripe_customer_id=f"cus_ws05_02_operation_{unique}",
        )
        operation = PaymentMethodOperation(
            id=uuid.uuid4(),
            user_id=user.id,
            operation_kind="setup_create",
            status="provider_unknown",
            request_fingerprint=unique.hex + unique.hex,
            provider_idempotency_key=(
                f"payment-method:{user.id}:{operation_key}:default:0"
            ),
            error_code="setup_create_timeout_unknown",
        )
        db.add(user)
        db.flush()
        db.add(operation)
        db.commit()

        monkeypatch.setattr(
            payment_method_service,
            "create_setup_intent",
            lambda **kwargs: StripeSetupIntentResult(
                id="seti_ws05_02_recovered",
                client_secret=None,
                status="requires_payment_method",
                customer_id=kwargs["customer_id"],
                payment_method_id=None,
            ),
        )
        monkeypatch.setattr(
            payment_method_service,
            "create_saved_payment_method_setup_intent",
            lambda *args, **kwargs: pytest.fail(
                "durable reconciliation must not call the endpoint service"
            ),
        )

        assert (
            payment_method_service.reconcile_payment_method_operation(
                db,
                operation.id,
            )
            == "succeeded"
        )
        assert db.get(PaymentMethodOperation, operation.id).status == "succeeded"

        with _session() as observer:
            assert (
                observer.get(PaymentMethodOperation, operation.id).status
                == "provider_unknown"
            )

        db.commit()
        with _session() as observer:
            resolved = observer.get(PaymentMethodOperation, operation.id)
            assert resolved.status == "succeeded"
            assert resolved.provider_object_id == "seti_ws05_02_recovered"


@pytest.mark.requirement("WS05-02-R6", "WS05-02-R7")
def test_paid_waitlist_reverifies_saved_method_before_any_charge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.game_waitlist_service as waitlist_service

    now = datetime(2035, 1, 6, 12, 0, tzinfo=timezone.utc)
    provider_create_calls: list[str] = []
    with _session() as db:
        state = _create_booking_payment_state(
            db,
            now=now,
            expires_at=now + timedelta(minutes=2),
        )
        booking = db.get(Booking, state.booking_id)
        participant = db.get(GameParticipant, state.participant_id)
        original_payment = db.get(Payment, state.payment_id)
        booking.booking_status = "waitlisted"
        booking.payment_status = "unpaid"
        booking.reservation_status = "not_required"
        booking.expires_at = None
        participant.participant_status = "waitlisted"
        db.delete(original_payment)

        user = db.get(User, state.user_id)
        payment_method = UserPaymentMethod(
            id=uuid.uuid4(),
            user_id=user.id,
            stripe_customer_id=user.stripe_customer_id,
            stripe_payment_method_id=f"pm_ws05_02_waitlist_{state.user_id}",
            card_fingerprint=f"fp_ws05_02_waitlist_{state.user_id}",
            card_brand="visa",
            card_last4="4242",
            exp_month=12,
            exp_year=2038,
            method_status="active",
            is_default=True,
        )
        waitlist_entry = WaitlistEntry(
            id=uuid.uuid4(),
            game_id=state.game_id,
            user_id=state.user_id,
            party_size=1,
            position=1,
            waitlist_status="active",
            auto_charge_consent_at=now,
            auto_charge_consent_version="paid-waitlist-v1",
            authorized_payment_method_id=payment_method.id,
            authorized_stripe_payment_method_id=(
                payment_method.stripe_payment_method_id
            ),
            authorized_payment_method_brand="visa",
            authorized_payment_method_last4="4242",
            authorized_amount_cents=booking.total_cents,
            joined_at=now,
        )
        db.add_all([booking, participant, payment_method, waitlist_entry])
        db.commit()

        monkeypatch.setattr(
            waitlist_service,
            "retrieve_payment_method",
            lambda payment_method_id: StripePaymentMethodCardResult(
                id=payment_method_id,
                customer_id="cus_different_owner",
                card_fingerprint=payment_method.card_fingerprint,
                card_brand="visa",
                card_last4="4242",
                exp_month=12,
                exp_year=2038,
            ),
        )

        def forbidden_create_payment_intent(**kwargs):
            provider_create_calls.append(kwargs["idempotency_key"])
            pytest.fail("a stale or cross-customer saved method must not be charged")

        monkeypatch.setattr(
            waitlist_service,
            "create_payment_intent",
            forbidden_create_payment_intent,
        )

        outcome = waitlist_service.attempt_paid_waitlist_auto_promotion(
            db,
            db.get(Game, state.game_id),
            db.get(WaitlistEntry, waitlist_entry.id),
            db.get(Booking, state.booking_id),
            [db.get(GameParticipant, state.participant_id)],
            now,
        )
        assert outcome == ("failed", 0)
        assert provider_create_calls == []
        assert db.get(UserPaymentMethod, payment_method.id).method_status == "detached"
        assert db.get(Booking, state.booking_id).booking_status == "failed"
        failed_payment = db.scalar(
            select(Payment).where(Payment.booking_id == state.booking_id)
        )
        assert failed_payment.payment_status == "failed"


def _attach_paid_waitlist_processing_state(
    db: Session,
    state: _BookingPaymentState,
    *,
    now: datetime,
    provider_payment_method_id: str,
) -> uuid.UUID:
    payment = db.get(Payment, state.payment_id)
    payment_method = UserPaymentMethod(
        id=uuid.uuid4(),
        user_id=state.user_id,
        stripe_customer_id=payment.provider_customer_id,
        stripe_payment_method_id=provider_payment_method_id,
        card_fingerprint=f"fp_{provider_payment_method_id}_{state.user_id}",
        card_brand="visa",
        card_last4="4242",
        exp_month=12,
        exp_year=2038,
        method_status="active",
        is_default=True,
        created_at=now,
        updated_at=now,
    )
    waitlist_entry = WaitlistEntry(
        id=uuid.uuid4(),
        game_id=state.game_id,
        user_id=state.user_id,
        party_size=1,
        position=1,
        waitlist_status="payment_processing",
        promoted_booking_id=state.booking_id,
        promoted_at=now,
        promotion_expires_at=now + timedelta(minutes=2),
        auto_charge_consent_at=now,
        auto_charge_consent_version="paid-waitlist-v1",
        authorized_payment_method_id=payment_method.id,
        authorized_stripe_payment_method_id=provider_payment_method_id,
        authorized_payment_method_brand="visa",
        authorized_payment_method_last4="4242",
        authorized_amount_cents=1600,
        joined_at=now,
    )
    payment.payment_metadata = {
        **dict(payment.payment_metadata or {}),
        "source": "waitlist_auto_promote",
        "waitlist_entry_id": str(waitlist_entry.id),
        "authorized_amount_cents": 1600,
    }
    db.add_all([payment, payment_method, waitlist_entry])
    db.commit()
    return waitlist_entry.id


@pytest.mark.requirement("WS05-02-R2", "WS05-02-R5", "WS05-02-R7")
def test_paid_waitlist_requires_action_fails_promotion_without_browser_wait() -> None:
    now = datetime(2035, 1, 7, 12, 0, tzinfo=timezone.utc)
    with _session() as db:
        state = _create_booking_payment_state(
            db,
            now=now,
            expires_at=now + timedelta(minutes=2),
            payment_status="processing",
            provider_status="processing",
        )
        payment = db.get(Payment, state.payment_id)
        payment_method = UserPaymentMethod(
            id=uuid.uuid4(),
            user_id=state.user_id,
            stripe_customer_id=payment.provider_customer_id,
            stripe_payment_method_id="pm_ws05_requires_action",
            card_fingerprint=f"fp_ws05_requires_action_{state.user_id}",
            card_brand="visa",
            card_last4="4242",
            exp_month=12,
            exp_year=2038,
            method_status="active",
            is_default=True,
            created_at=now,
            updated_at=now,
        )
        waitlist_entry = WaitlistEntry(
            id=uuid.uuid4(),
            game_id=state.game_id,
            user_id=state.user_id,
            party_size=1,
            position=1,
            waitlist_status="payment_processing",
            promoted_booking_id=state.booking_id,
            promoted_at=now,
            promotion_expires_at=now + timedelta(minutes=2),
            auto_charge_consent_at=now,
            auto_charge_consent_version="paid-waitlist-v1",
            authorized_payment_method_id=payment_method.id,
            authorized_stripe_payment_method_id=(
                payment_method.stripe_payment_method_id
            ),
            authorized_payment_method_brand="visa",
            authorized_payment_method_last4="4242",
            authorized_amount_cents=1600,
            joined_at=now,
        )
        payment.payment_metadata = {
            **dict(payment.payment_metadata or {}),
            "source": "waitlist_auto_promote",
            "waitlist_entry_id": str(waitlist_entry.id),
            "authorized_amount_cents": 1600,
        }
        db.add_all([payment, payment_method, waitlist_entry])
        db.commit()

        assert (
            _apply_observation(
                db,
                state,
                provider_status="requires_action",
                now=now + timedelta(seconds=10),
            )
            == "processed"
        )
        db.commit()

        payment = db.get(Payment, state.payment_id)
        booking = db.get(Booking, state.booking_id)
        participant = db.get(GameParticipant, state.participant_id)
        waitlist_entry = db.get(WaitlistEntry, waitlist_entry.id)
        assert (payment.payment_status, payment.provider_status) == (
            "requires_action",
            "requires_action",
        )
        assert (booking.booking_status, booking.reservation_status) == (
            "failed",
            "released",
        )
        assert participant.participant_status == "removed"
        assert waitlist_entry.waitlist_status == "payment_failed"


@pytest.mark.requirement("WS05-02-R2", "WS05-02-R5", "WS05-02-R7")
@pytest.mark.parametrize("provider_status", ("requires_confirmation", "requires_capture"))
def test_paid_waitlist_unresolved_provider_states_preserve_truth_without_failure(
    provider_status: str,
) -> None:
    now = datetime(2035, 1, 7, 13, 0, tzinfo=timezone.utc)
    with _session() as db:
        state = _create_booking_payment_state(
            db,
            now=now,
            expires_at=now + timedelta(minutes=2),
            payment_status="processing",
            provider_status="processing",
        )
        waitlist_entry_id = _attach_paid_waitlist_processing_state(
            db,
            state,
            now=now,
            provider_payment_method_id=f"pm_ws05_{provider_status}_{state.user_id}",
        )

        assert (
            _apply_observation(
                db,
                state,
                provider_status=provider_status,
                now=now + timedelta(seconds=10),
            )
            == "processed"
        )
        db.commit()

        payment = db.get(Payment, state.payment_id)
        booking = db.get(Booking, state.booking_id)
        participant = db.get(GameParticipant, state.participant_id)
        waitlist_entry = db.get(WaitlistEntry, waitlist_entry_id)
        assert (payment.payment_status, payment.provider_status) == (
            provider_status,
            provider_status,
        )
        assert (booking.booking_status, booking.reservation_status) == (
            "pending_payment",
            "held",
        )
        assert participant.participant_status == "pending_payment"
        assert waitlist_entry.waitlist_status == "payment_processing"
        assert (
            db.scalar(
                select(func.count())
                .select_from(PaymentCompensation)
                .where(PaymentCompensation.payment_id == payment.id)
            )
            == 0
        )


@pytest.mark.requirement("WS05-02-R1", "WS05-02-R2", "WS05-02-R5", "WS05-02-R7")
def test_paid_waitlist_confirmation_uses_fresh_database_time_after_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.game_waitlist_service as waitlist_service

    now = datetime(2035, 1, 7, 14, 0, tzinfo=timezone.utc)
    with _session() as db:
        state = _create_booking_payment_state(
            db,
            now=now,
            expires_at=now + timedelta(minutes=2),
        )
        booking = db.get(Booking, state.booking_id)
        participant = db.get(GameParticipant, state.participant_id)
        original_payment = db.get(Payment, state.payment_id)
        booking.booking_status = "waitlisted"
        booking.payment_status = "unpaid"
        booking.reservation_status = "not_required"
        booking.expires_at = None
        participant.participant_status = "waitlisted"
        db.delete(original_payment)

        user = db.get(User, state.user_id)
        payment_method = UserPaymentMethod(
            id=uuid.uuid4(),
            user_id=user.id,
            stripe_customer_id=user.stripe_customer_id,
            stripe_payment_method_id=f"pm_ws05_waitlist_stale_{state.user_id}",
            card_fingerprint=f"fp_ws05_waitlist_stale_{state.user_id}",
            card_brand="visa",
            card_last4="4242",
            exp_month=12,
            exp_year=2038,
            method_status="active",
            is_default=True,
        )
        waitlist_entry = WaitlistEntry(
            id=uuid.uuid4(),
            game_id=state.game_id,
            user_id=state.user_id,
            party_size=1,
            position=1,
            waitlist_status="active",
            auto_charge_consent_at=now,
            auto_charge_consent_version="paid-waitlist-v1",
            authorized_payment_method_id=payment_method.id,
            authorized_stripe_payment_method_id=(
                payment_method.stripe_payment_method_id
            ),
            authorized_payment_method_brand="visa",
            authorized_payment_method_last4="4242",
            authorized_amount_cents=booking.total_cents,
            joined_at=now,
        )
        db.add_all([booking, participant, payment_method, waitlist_entry])
        db.commit()

        monkeypatch.setattr(
            waitlist_service,
            "retrieve_payment_method",
            lambda payment_method_id: StripePaymentMethodCardResult(
                id=payment_method_id,
                customer_id=user.stripe_customer_id,
                card_fingerprint=payment_method.card_fingerprint,
                card_brand="visa",
                card_last4="4242",
                exp_month=12,
                exp_year=2038,
            ),
        )
        created_metadata: dict[str, str] = {}

        def create_waitlist_payment_intent(**kwargs):
            created_metadata.update(kwargs["metadata"])
            return StripePaymentIntentResult(
                id=f"pi_ws05_waitlist_stale_{state.booking_id.hex}",
                client_secret=None,
                status="requires_confirmation",
                latest_charge_id=None,
                amount_cents=kwargs["amount_cents"],
                amount_received_cents=None,
                currency=kwargs["currency"],
                customer_id=kwargs["customer_id"],
                metadata=kwargs["metadata"],
            )

        def confirm_waitlist_payment_intent(payment_intent_id, **_kwargs):
            return StripePaymentIntentResult(
                id=payment_intent_id,
                client_secret=None,
                status="succeeded",
                latest_charge_id=f"ch_{state.booking_id.hex}",
                amount_cents=booking.total_cents,
                amount_received_cents=booking.total_cents,
                currency=booking.currency,
                customer_id=user.stripe_customer_id,
                metadata=dict(created_metadata),
            )

        monkeypatch.setattr(
            waitlist_service,
            "create_payment_intent",
            create_waitlist_payment_intent,
        )
        monkeypatch.setattr(
            waitlist_service,
            "confirm_payment_intent",
            confirm_waitlist_payment_intent,
        )
        database_times = iter(
            (
                now + timedelta(seconds=10),
                now + timedelta(minutes=3),
            )
        )
        monkeypatch.setattr(
            waitlist_service,
            "get_database_now",
            lambda _db: next(database_times),
        )

        outcome = waitlist_service.attempt_paid_waitlist_auto_promotion(
            db,
            db.get(Game, state.game_id),
            db.get(WaitlistEntry, waitlist_entry.id),
            db.get(Booking, state.booking_id),
            [db.get(GameParticipant, state.participant_id)],
            now,
        )

        payment = db.scalar(select(Payment).where(Payment.booking_id == state.booking_id))
        booking = db.get(Booking, state.booking_id)
        participant = db.get(GameParticipant, state.participant_id)
        waitlist_entry = db.get(WaitlistEntry, waitlist_entry.id)
        compensation = db.scalar(
            select(PaymentCompensation).where(PaymentCompensation.payment_id == payment.id)
        )
        assert outcome == ("failed", 0)
        assert (payment.payment_status, payment.provider_status) == (
            "succeeded",
            "succeeded",
        )
        assert (booking.booking_status, booking.reservation_status) == (
            "expired",
            "released",
        )
        assert participant.participant_status == "removed"
        assert waitlist_entry.waitlist_status == "payment_failed"
        assert compensation.reason == "reservation_expired"


@pytest.mark.requirement("WS05-02-R1", "WS05-02-R6", "WS05-02-R7")
def test_unknown_payment_intent_creation_reuses_checkout_without_provider_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import checkout_service

    now = datetime(2035, 1, 8, 12, 0, tzinfo=timezone.utc)
    with _session() as db:
        state = _create_booking_payment_state(
            db,
            now=now,
            expires_at=now + timedelta(minutes=2),
            payment_status="unknown",
            provider_status=None,
        )
        payment = db.get(Payment, state.payment_id)
        payment.provider_payment_intent_id = None
        db.add(payment)
        db.commit()

        monkeypatch.setattr(
            checkout_service,
            "retrieve_payment_intent",
            lambda _payment_intent_id: pytest.fail(
                "unknown creation replay must not retrieve a missing PaymentIntent id"
            ),
        )

        response = checkout_service.resume_pending_checkout_with_locked_game(
            db,
            db.get(Game, state.game_id),
            GameCheckoutPaymentIntentCreate(guest_count=0),
            db.get(User, state.user_id),
            return_url=None,
            party_size=1,
            subtotal_cents=1600,
            now=now,
        )

        assert response is not None
        assert response.client_secret is None
        assert response.booking_id == state.booking_id
        assert response.payment_id == state.payment_id
        assert response.payment_status == "unknown"
        assert response.stripe_status == "unknown"


@pytest.mark.requirement("WS05-02-R1", "WS05-02-R2", "WS05-02-R5")
def test_checkout_confirmation_uses_fresh_database_time_after_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import checkout_service

    now = datetime(2035, 1, 8, 12, 30, tzinfo=timezone.utc)
    with _session() as db:
        state = _create_booking_payment_state(
            db,
            now=now,
            expires_at=now + timedelta(minutes=2),
            payment_status="requires_payment_method",
            provider_status="requires_payment_method",
        )
        payment = db.get(Payment, state.payment_id)
        payment_method = UserPaymentMethod(
            id=uuid.uuid4(),
            user_id=state.user_id,
            stripe_customer_id=payment.provider_customer_id,
            stripe_payment_method_id=f"pm_ws05_checkout_confirm_{state.user_id}",
            card_fingerprint=f"fp_ws05_checkout_confirm_{state.user_id}",
            card_brand="visa",
            card_last4="4242",
            exp_month=12,
            exp_year=2038,
            method_status="active",
            is_default=True,
            created_at=now,
            updated_at=now,
        )
        db.add(payment_method)
        db.commit()

        monkeypatch.setattr(
            checkout_service,
            "retrieve_payment_intent",
            lambda _payment_intent_id: StripePaymentIntentResult(
                id=payment.provider_payment_intent_id,
                client_secret=None,
                status="requires_payment_method",
                latest_charge_id=None,
                amount_cents=payment.amount_cents,
                amount_received_cents=None,
                currency=payment.currency,
                customer_id=payment.provider_customer_id,
                metadata=dict(payment.payment_metadata or {}),
            ),
        )
        monkeypatch.setattr(
            checkout_service,
            "confirm_payment_intent",
            lambda _payment_intent_id, **_kwargs: StripePaymentIntentResult(
                id=payment.provider_payment_intent_id,
                client_secret=None,
                status="succeeded",
                latest_charge_id=f"ch_{state.payment_id.hex}",
                amount_cents=payment.amount_cents,
                amount_received_cents=payment.amount_cents,
                currency=payment.currency,
                customer_id=payment.provider_customer_id,
                metadata=dict(payment.payment_metadata or {}),
            ),
        )
        database_times = iter(
            (
                now + timedelta(seconds=10),
                now + timedelta(minutes=3),
            )
        )
        monkeypatch.setattr(
            checkout_service,
            "get_database_now",
            lambda _db: next(database_times),
        )

        response = checkout_service.resume_pending_checkout_with_locked_game(
            db,
            db.get(Game, state.game_id),
            GameCheckoutPaymentIntentCreate(
                guest_count=0,
                payment_method_id=payment_method.id,
            ),
            db.get(User, state.user_id),
            return_url=None,
            party_size=1,
            subtotal_cents=1600,
            now=now,
            provider_verified_payment_method_id=payment_method.id,
        )

        payment = db.get(Payment, state.payment_id)
        booking = db.get(Booking, state.booking_id)
        participant = db.get(GameParticipant, state.participant_id)
        compensation = db.scalar(
            select(PaymentCompensation).where(
                PaymentCompensation.payment_id == state.payment_id
            )
        )
        assert response.booking_status == "expired"
        assert (payment.payment_status, payment.provider_status) == (
            "succeeded",
            "succeeded",
        )
        assert (booking.booking_status, booking.reservation_status) == (
            "expired",
            "released",
        )
        assert participant.participant_status == "cancelled"
        assert compensation.reason == "reservation_expired"


def _create_saved_payment_method_pair(
    db: Session,
    *,
    now: datetime,
) -> tuple[User, UserPaymentMethod, UserPaymentMethod]:
    unique = uuid.uuid4()
    user = User(
        id=uuid.uuid4(),
        auth_user_id=f"ws05-02-card-user-{unique}",
        role="player",
        email=f"ws05-02-card-user-{unique}@example.invalid",
        first_name="Saved",
        last_name="Card",
        account_status="active",
        hosting_status="eligible",
        stripe_customer_id=f"cus_ws05_02_card_{unique}",
    )
    default_method = UserPaymentMethod(
        id=uuid.uuid4(),
        user_id=user.id,
        stripe_customer_id=user.stripe_customer_id,
        stripe_payment_method_id=f"pm_ws05_default_{unique}",
        card_fingerprint=f"fp_ws05_default_{unique}",
        card_brand="visa",
        card_last4="4242",
        exp_month=12,
        exp_year=2038,
        method_status="active",
        is_default=True,
        created_at=now,
        updated_at=now,
    )
    secondary_method = UserPaymentMethod(
        id=uuid.uuid4(),
        user_id=user.id,
        stripe_customer_id=user.stripe_customer_id,
        stripe_payment_method_id=f"pm_ws05_secondary_{unique}",
        card_fingerprint=f"fp_ws05_secondary_{unique}",
        card_brand="visa",
        card_last4="1881",
        exp_month=12,
        exp_year=2038,
        method_status="active",
        is_default=False,
        created_at=now,
        updated_at=now,
    )
    db.add_all([user, default_method, secondary_method])
    db.commit()
    return user, default_method, secondary_method


@pytest.mark.requirement("WS05-02-R6", "WS05-02-R7")
def test_set_default_verifies_provider_owner_before_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import payment_method_service

    now = datetime(2035, 1, 8, 13, 0, tzinfo=timezone.utc)
    provider_set_calls: list[str] = []
    with _session() as db:
        user, _default_method, secondary_method = _create_saved_payment_method_pair(
            db,
            now=now,
        )

        monkeypatch.setattr(
            payment_method_service,
            "retrieve_payment_method",
            lambda payment_method_id: StripePaymentMethodCardResult(
                id=payment_method_id,
                customer_id="cus_other_owner",
                card_fingerprint=secondary_method.card_fingerprint,
                card_brand="visa",
                card_last4="1881",
                exp_month=12,
                exp_year=2038,
            ),
        )

        def forbidden_set_default(**kwargs):
            provider_set_calls.append(kwargs["payment_method_id"])
            pytest.fail("provider owner mismatch must block default mutation")

        monkeypatch.setattr(
            payment_method_service,
            "set_customer_default_payment_method",
            forbidden_set_default,
        )

        with pytest.raises(HTTPException) as exc_info:
            payment_method_service.set_default_saved_payment_method(
                db,
                user,
                secondary_method.id,
                uuid.uuid4(),
            )

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert provider_set_calls == []
        assert db.get(UserPaymentMethod, secondary_method.id).method_status == "detached"
        assert db.scalar(select(func.count()).select_from(PaymentMethodOperation)) == 0


@pytest.mark.requirement("WS05-02-R6", "WS05-02-R7")
def test_provider_unknown_card_operation_blocks_conflicting_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import payment_method_service

    now = datetime(2035, 1, 8, 14, 0, tzinfo=timezone.utc)
    with _session() as db:
        user, default_method, _secondary_method = _create_saved_payment_method_pair(
            db,
            now=now,
        )
        operation = PaymentMethodOperation(
            id=uuid.uuid4(),
            user_id=user.id,
            payment_method_id=default_method.id,
            operation_kind="set_default",
            status="provider_unknown",
            request_fingerprint=uuid.uuid4().hex + uuid.uuid4().hex,
            provider_idempotency_key=f"payment-method:{user.id}:{uuid.uuid4()}",
            error_code="set_default_timeout_unknown",
            created_at=now,
            updated_at=now,
        )
        db.add(operation)
        db.commit()

        monkeypatch.setattr(
            payment_method_service,
            "retrieve_payment_method",
            lambda _payment_method_id: pytest.fail(
                "conflicting operation must block provider reads"
            ),
        )
        monkeypatch.setattr(
            payment_method_service,
            "detach_payment_method",
            lambda *_args, **_kwargs: pytest.fail(
                "conflicting operation must block provider mutations"
            ),
        )

        with pytest.raises(HTTPException) as exc_info:
            payment_method_service.detach_saved_payment_method(
                db,
                user,
                default_method.id,
                uuid.uuid4(),
            )

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert db.get(PaymentMethodOperation, operation.id).status == "provider_unknown"
        assert db.get(UserPaymentMethod, default_method.id).method_status == "active"


@pytest.mark.requirement("WS05-02-R6", "WS05-02-R7")
def test_active_payment_method_operation_database_index_blocks_conflicts() -> None:
    now = datetime(2035, 1, 8, 14, 30, tzinfo=timezone.utc)
    with _session() as db:
        user, default_method, secondary_method = _create_saved_payment_method_pair(
            db,
            now=now,
        )
        first_operation = PaymentMethodOperation(
            id=uuid.uuid4(),
            user_id=user.id,
            payment_method_id=default_method.id,
            operation_kind="set_default",
            status="pending",
            request_fingerprint=uuid.uuid4().hex + uuid.uuid4().hex,
            provider_idempotency_key=f"payment-method:{user.id}:{uuid.uuid4()}",
            created_at=now,
            updated_at=now,
        )
        db.add(first_operation)
        db.commit()

        second_operation_id = uuid.uuid4()
        second_operation_fingerprint = uuid.uuid4().hex + uuid.uuid4().hex
        second_operation_key = f"payment-method:{user.id}:{uuid.uuid4()}"
        db.add(
            PaymentMethodOperation(
                id=second_operation_id,
                user_id=user.id,
                payment_method_id=secondary_method.id,
                operation_kind="detach",
                status="provider_unknown",
                request_fingerprint=second_operation_fingerprint,
                provider_idempotency_key=second_operation_key,
                error_code="detach_timeout_unknown",
                created_at=now,
                updated_at=now,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        first_operation = db.get(PaymentMethodOperation, first_operation.id)
        first_operation.status = "succeeded"
        first_operation.resolved_at = now
        first_operation.updated_at = now
        db.add(first_operation)
        db.commit()

        db.add(
            PaymentMethodOperation(
                id=second_operation_id,
                user_id=user.id,
                payment_method_id=secondary_method.id,
                operation_kind="detach",
                status="provider_unknown",
                request_fingerprint=second_operation_fingerprint,
                provider_idempotency_key=second_operation_key,
                error_code="detach_timeout_unknown",
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()

        active_count = db.scalar(
            select(func.count())
            .select_from(PaymentMethodOperation)
            .where(
                PaymentMethodOperation.user_id == user.id,
                PaymentMethodOperation.status.in_({"pending", "provider_unknown"}),
            )
        )
        assert active_count == 1


def _begin_saved_payment_method_operation(
    user_id: uuid.UUID,
    payment_method_id: uuid.UUID,
    operation_kind: str,
    idempotency_key: uuid.UUID,
    barrier: Barrier,
) -> str:
    from backend.services import payment_method_service

    with _session() as db:
        user = db.get(User, user_id)
        assert user is not None
        barrier.wait(timeout=10)
        try:
            operation = payment_method_service.begin_payment_method_operation(
                db,
                user,
                operation_kind=operation_kind,
                idempotency_key=idempotency_key,
                payment_method_id=payment_method_id,
            )
        except HTTPException as exc:
            db.rollback()
            return f"http-{exc.status_code}"
        return f"active:{operation.status}"


@pytest.mark.requirement("WS05-02-R6", "WS05-02-R7")
def test_concurrent_saved_method_operations_cannot_both_become_active() -> None:
    now = datetime(2035, 1, 8, 14, 45, tzinfo=timezone.utc)
    with _session() as db:
        user, default_method, secondary_method = _create_saved_payment_method_pair(
            db,
            now=now,
        )
        user_id = user.id
        operation_inputs = (
            ("set_default", default_method.id, uuid.uuid4()),
            ("detach", secondary_method.id, uuid.uuid4()),
        )

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                _begin_saved_payment_method_operation,
                user_id,
                payment_method_id,
                operation_kind,
                idempotency_key,
                barrier,
            )
            for operation_kind, payment_method_id, idempotency_key in operation_inputs
        ]
        results = sorted(future.result(timeout=20) for future in futures)

    with _session() as db:
        active_count = db.scalar(
            select(func.count())
            .select_from(PaymentMethodOperation)
            .where(
                PaymentMethodOperation.user_id == user_id,
                PaymentMethodOperation.status.in_({"pending", "provider_unknown"}),
            )
        )

    assert results == ["active:pending", "http-409"]
    assert active_count == 1


@pytest.mark.requirement("WS05-02-R6", "WS05-02-R7")
def test_detach_default_uses_distinct_clear_default_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import payment_method_service

    now = datetime(2035, 1, 8, 15, 0, tzinfo=timezone.utc)
    detach_keys: list[str] = []
    clear_keys: list[str] = []
    with _session() as db:
        user, default_method, secondary_method = _create_saved_payment_method_pair(
            db,
            now=now,
        )
        secondary_method.method_status = "detached"
        db.add(secondary_method)
        db.commit()

        monkeypatch.setattr(
            payment_method_service,
            "retrieve_payment_method",
            lambda payment_method_id: StripePaymentMethodCardResult(
                id=payment_method_id,
                customer_id=user.stripe_customer_id,
                card_fingerprint=default_method.card_fingerprint,
                card_brand="visa",
                card_last4="4242",
                exp_month=12,
                exp_year=2038,
            ),
        )
        monkeypatch.setattr(
            payment_method_service,
            "detach_payment_method",
            lambda _payment_method_id, *, idempotency_key=None: detach_keys.append(
                idempotency_key
            ),
        )
        monkeypatch.setattr(
            payment_method_service,
            "clear_customer_default_payment_method",
            lambda *, customer_id, idempotency_key=None: clear_keys.append(
                idempotency_key
            ),
        )
        monkeypatch.setattr(
            payment_method_service,
            "set_customer_default_payment_method",
            lambda **_kwargs: pytest.fail("no replacement default should be set"),
        )

        detached = payment_method_service.detach_saved_payment_method(
            db,
            user,
            default_method.id,
            uuid.uuid4(),
        )

        assert detached.method_status == "detached"
        assert len(detach_keys) == 1
        assert len(clear_keys) == 1
        assert detach_keys[0] != clear_keys[0]
        operations = {
            operation.operation_kind: operation
            for operation in db.scalars(select(PaymentMethodOperation)).all()
        }
        assert operations["detach"].status == "succeeded"
        assert operations["clear_default"].status == "succeeded"
