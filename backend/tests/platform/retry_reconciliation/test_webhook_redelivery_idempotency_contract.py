from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.suite_type("ordinary")

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _event_payload(provider_event_id: str) -> dict[str, object]:
    return {
        "id": provider_event_id,
        "type": "charge.dispute.created",
        "data": {"object": {"id": "du_synthetic"}},
    }


def _payment_event(provider_event_id: str):
    from backend.models import PaymentEvent

    return PaymentEvent(
        id=uuid.uuid4(),
        payment_id=None,
        provider="stripe",
        provider_event_id=provider_event_id,
        event_type="charge.dispute.created",
        raw_payload=_event_payload(provider_event_id),
        processing_status="ignored",
    )


@pytest.mark.requirement("WS02-04C2-R7")
def test_signed_webhook_route_uses_construction_seam_before_processing() -> None:
    route_source = (_REPO_ROOT / "backend/routes/stripe_webhook_routes.py").read_text()
    service_source = (_REPO_ROOT / "backend/services/stripe_webhook_service.py").read_text()

    assert "payload = await request.body()" in route_source
    assert 'alias="Stripe-Signature"' in route_source
    assert "construct_webhook_event(payload, stripe_signature)" in route_source
    assert "record_and_process_stripe_webhook_event(db, stripe_event)" in route_source
    assert "provider_event_id = event_payload.get(\"id\")" in service_source


@pytest.mark.requirement("WS02-04C2-R7")
def test_webhook_requires_provider_event_id_before_local_event_creation() -> None:
    from backend.models import PaymentEvent
    from backend.services.stripe_webhook_service import record_and_process_stripe_webhook_event

    with _session() as db:
        with pytest.raises(HTTPException) as exc_info:
            record_and_process_stripe_webhook_event(
                db,
                {"type": "payment_intent.succeeded", "data": {"object": {}}},
            )

        assert exc_info.value.status_code == 400
        assert "missing id" in str(exc_info.value.detail)
        assert db.scalars(select(PaymentEvent)).all() == []


@pytest.mark.requirement("WS02-04C2-R7")
def test_existing_provider_event_duplicate_is_idempotent_without_reprocessing() -> None:
    from backend.models import PaymentEvent
    from backend.services.stripe_webhook_service import record_and_process_stripe_webhook_event

    with _session() as db:
        existing = _payment_event("evt_ws02_04c2_duplicate")
        db.add(existing)
        db.commit()

        result = record_and_process_stripe_webhook_event(
            db,
            _event_payload("evt_ws02_04c2_duplicate"),
        )

        events = db.scalars(select(PaymentEvent)).all()
        assert result == {
            "received": True,
            "duplicate": True,
            "processing_status": "ignored",
        }
        assert len(events) == 1
        assert events[0].id == existing.id


@pytest.mark.requirement("WS02-04C2-R7")
def test_provider_event_uniqueness_and_integrity_error_path_are_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import PaymentEvent
    import backend.services.stripe_webhook_service as webhook_service

    def create_conflicting_event(db, event, event_payload, now):
        del event, event_payload, now
        db.add(_payment_event("evt_ws02_04c2_race_duplicate"))
        db.flush()

    monkeypatch.setattr(
        webhook_service,
        "process_stripe_event",
        create_conflicting_event,
    )

    with _session() as db:
        with pytest.raises(IntegrityError):
            db.add_all(
                [
                    _payment_event("evt_ws02_04c2_unique"),
                    _payment_event("evt_ws02_04c2_unique"),
                ]
            )
            db.commit()

    with _session() as db:
        result = webhook_service.record_and_process_stripe_webhook_event(
            db,
            _event_payload("evt_ws02_04c2_race_duplicate"),
        )

        assert result == {
            "received": True,
            "duplicate": True,
            "processing_status": "duplicate",
        }
        assert db.scalars(select(PaymentEvent)).all() == []


@pytest.mark.requirement("WS02-04C2-R7")
def test_no_internal_scheduled_webhook_retry_loop_is_present() -> None:
    source = (_REPO_ROOT / "backend/services/stripe_webhook_service.py").read_text()

    assert "schedule_webhook_retry" not in source
    assert "BackgroundTasks" not in source
    assert "create_task" not in source
    assert "asyncio.gather" not in source
