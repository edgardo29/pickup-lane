from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.schemas.payment_event_schema import PaymentEventUpdate

pytestmark = pytest.mark.suite_type("ordinary")


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _user():
    from backend.models import User

    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04b2a2b2-event-user-{unique}",
        role="player",
        email=f"ws02-04b2a2b2-event-{unique}@example.invalid",
        first_name="Payment",
        last_name="Event",
        account_status="active",
        hosting_status="eligible",
    )


def _payment(user):
    from backend.models import Payment

    return Payment(
        id=uuid.uuid4(),
        payer_user_id=user.id,
        booking_id=None,
        game_id=None,
        payment_type="admin_charge",
        provider="stripe",
        provider_payment_intent_id=f"pi_ws02_04b2a2b2_repair_{uuid.uuid4()}",
        provider_charge_id=None,
        idempotency_key=f"payment-event-repair-{uuid.uuid4()}",
        amount_cents=500,
        currency="USD",
        payment_status="processing",
        paid_at=None,
        payment_metadata={"test": "ws02-04b2a2b2"},
    )


def _payment_event():
    from backend.models import PaymentEvent

    return PaymentEvent(
        id=uuid.uuid4(),
        payment_id=None,
        provider="stripe",
        provider_event_id=f"evt_ws02_04b2a2b2_{uuid.uuid4()}",
        event_type="payment_intent.payment_failed",
        event_envelope={
            "id": "evt_original",
            "data": {"object": {"id": "pi_original"}},
        },
        provider_created_at=datetime.now(timezone.utc),
        processing_status="pending",
    )


@pytest.mark.requirement("WS02-04B2A2B2-R5")
def test_payment_event_repair_schema_allows_only_repair_fields() -> None:
    payment_id = uuid.uuid4()
    assert PaymentEventUpdate(payment_id=payment_id).payment_id == payment_id
    assert PaymentEventUpdate(reprocess=True).reprocess is True

    with pytest.raises(ValidationError):
        PaymentEventUpdate(provider="stripe")
    with pytest.raises(ValidationError):
        PaymentEventUpdate(provider_event_id="evt_changed")
    with pytest.raises(ValidationError):
        PaymentEventUpdate(event_type="payment_intent.succeeded")
    with pytest.raises(ValidationError):
        PaymentEventUpdate(event_envelope={"id": "evt_changed"})
    with pytest.raises(ValidationError):
        PaymentEventUpdate(processing_status="failed")


@pytest.mark.requirement("WS02-04B2A2B2-R5")
def test_payment_event_repair_persists_allowed_fields_without_mutating_provider_metadata() -> None:
    from backend.models import PaymentEvent
    from backend.services.payment_event_service import update_payment_event_record

    with _session() as db:
        user = _user()
        db.add(user)
        db.flush()

        payment = _payment(user)
        event = _payment_event()
        db.add_all([payment, event])
        db.commit()

        result = update_payment_event_record(
            db,
            event.id,
            PaymentEventUpdate(
                payment_id=payment.id,
            ),
        )

        assert result.payment_id == payment.id
        assert result.processing_status == "pending"
        assert result.processing_error_code is None
        assert result.processed_at is None
        assert result.provider == "stripe"
        assert result.provider_event_id == event.provider_event_id
        assert result.event_type == "payment_intent.payment_failed"
        assert result.event_envelope == {
            "id": "evt_original",
            "data": {"object": {"id": "pi_original"}},
        }
        persisted = db.get(PaymentEvent, event.id)
        assert persisted.payment_id == payment.id
        assert persisted.processing_status == "pending"
        assert persisted.provider == "stripe"
        assert persisted.provider_event_id == event.provider_event_id
        assert persisted.event_type == "payment_intent.payment_failed"
        assert persisted.event_envelope == {
            "id": "evt_original",
            "data": {"object": {"id": "pi_original"}},
        }


@pytest.mark.requirement("WS02-04B2A2B2-R5")
def test_rejected_payment_event_repair_does_not_change_persisted_state() -> None:
    from backend.models import PaymentEvent
    from backend.services.payment_event_service import update_payment_event_record

    with _session() as db:
        event = _payment_event()
        db.add(event)
        db.commit()

        with pytest.raises(HTTPException):
            update_payment_event_record(
                db,
                event.id,
                PaymentEventUpdate(payment_id=uuid.uuid4()),
            )
        db.rollback()

        persisted = db.get(PaymentEvent, event.id)
        assert persisted.processing_status == "pending"
        assert persisted.processing_error_code is None
        assert persisted.provider_event_id == event.provider_event_id
        assert persisted.event_envelope == {
            "id": "evt_original",
            "data": {"object": {"id": "pi_original"}},
        }
