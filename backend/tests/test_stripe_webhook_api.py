from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import Booking, GameParticipant
from backend.services.stripe_service import StripePaymentIntentResult
from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_game,
    create_payment,
    create_refund,
    create_user,
    create_user_payment_method,
    create_venue,
    mock_checkout_payment_method_verification,
    unique_suffix,
)


def create_pending_checkout(
    client: TestClient,
    monkeypatch,
    *,
    guest_count: int = 1,
    price_per_player_cents: int = 1500,
) -> dict:
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(
        client,
        user["id"],
        venue,
        price_per_player_cents=price_per_player_cents,
    )
    payment_intent_id = f"pi_{unique_suffix()}"
    payment_method = create_user_payment_method(
        client,
        user["id"],
        stripe_customer_id="cus_webhook_saved_card",
        stripe_payment_method_id="pm_webhook_saved_card",
    )
    mock_checkout_payment_method_verification(monkeypatch, payment_method)

    def fake_create_payment_intent(**kwargs):
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret=f"{payment_intent_id}_secret",
            status="requires_payment_method",
        )

    def fake_confirm_payment_intent(payment_intent_id, **kwargs):
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret=f"{payment_intent_id}_secret",
            status="processing",
        )

    monkeypatch.setattr(
        "backend.routes.checkout_routes.create_payment_intent",
        fake_create_payment_intent,
    )
    monkeypatch.setattr(
        "backend.routes.checkout_routes.confirm_payment_intent",
        fake_confirm_payment_intent,
    )
    authenticate_as(user["id"])
    response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={
            "guest_count": guest_count,
            "payment_method_id": payment_method["id"],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "user": user,
        "game": game,
        "payment_intent_id": payment_intent_id,
        "booking_id": body["booking_id"],
        "payment_id": body["payment_id"],
        "amount_cents": body["amount_cents"],
        "currency": body["currency"],
    }


def build_payment_intent_event(
    checkout: dict,
    *,
    event_type: str,
    event_id: str | None = None,
    amount_cents: int | None = None,
    currency: str = "usd",
    status: str | None = None,
    metadata: dict[str, str] | None = None,
    last_payment_error: dict | None = None,
) -> dict:
    event_id = event_id or f"evt_{unique_suffix()}"
    status = status or event_type.rsplit(".", maxsplit=1)[-1]
    if metadata is None:
        intent_metadata = {
            "user_id": checkout["user"]["id"],
            "game_id": checkout["game"]["id"],
            "booking_id": checkout["booking_id"],
            "payment_id": checkout["payment_id"],
        }
    else:
        intent_metadata = metadata
    intent = {
        "id": checkout["payment_intent_id"],
        "object": "payment_intent",
        "amount": amount_cents if amount_cents is not None else checkout["amount_cents"],
        "amount_received": (
            amount_cents if event_type == "payment_intent.succeeded" else 0
        ),
        "currency": currency,
        "status": status,
        "metadata": intent_metadata,
        "latest_charge": "ch_test_webhook",
    }
    if last_payment_error is not None:
        intent["last_payment_error"] = last_payment_error

    return {
        "id": event_id,
        "object": "event",
        "type": event_type,
        "data": {"object": intent},
    }


def build_refund_event(
    *,
    refund: dict,
    payment: dict,
    booking: dict,
    event_type: str,
    event_id: str | None = None,
    amount_cents: int | None = None,
    currency: str = "usd",
    status: str = "succeeded",
    metadata: dict[str, str] | None = None,
) -> dict:
    event_id = event_id or f"evt_{unique_suffix()}"
    refund_metadata = (
        metadata
        if metadata is not None
        else {
            "source": "official_game_cancel",
            "booking_id": booking["id"],
            "payment_id": payment["id"],
        }
    )
    refund_payload = {
        "id": refund["provider_refund_id"],
        "object": "refund",
        "amount": amount_cents if amount_cents is not None else refund["amount_cents"],
        "currency": currency,
        "charge": payment["provider_charge_id"],
        "payment_intent": payment["provider_payment_intent_id"],
        "status": status,
        "metadata": refund_metadata,
    }
    return {
        "id": event_id,
        "object": "event",
        "type": event_type,
        "data": {"object": refund_payload},
    }


def create_refund_webhook_setup(client: TestClient) -> tuple[dict, dict, dict]:
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    payment = create_payment(
        client,
        user["id"],
        booking_id=booking["id"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    with SessionLocal() as db:
        db_booking = db.get(Booking, UUID(booking["id"]))
        assert db_booking is not None
        db_booking.booking_status = "cancelled"
        db_booking.payment_status = "paid"
        db_booking.cancelled_at = datetime.now(timezone.utc)
        db.add(db_booking)
        db.commit()

    return user, booking, payment


def post_stripe_event(client: TestClient, monkeypatch, event_payload: dict):
    monkeypatch.setattr(
        "backend.routes.stripe_webhook_routes.construct_webhook_event",
        lambda payload, signature: deepcopy(event_payload),
    )
    return client.post(
        "/stripe/webhook",
        content=b"{}",
        headers={"Stripe-Signature": "test_signature"},
    )


def test_stripe_webhook_rejects_missing_signature(client: TestClient):
    response = client.post("/stripe/webhook", content=b"{}")

    assert response.status_code == 400, response.text
    assert "Stripe-Signature" in response.text


def test_stripe_webhook_rejects_invalid_signature(
    client: TestClient, monkeypatch
):
    def fake_construct_webhook_event(payload, signature):
        raise ValueError("bad signature")

    monkeypatch.setattr(
        "backend.routes.stripe_webhook_routes.construct_webhook_event",
        fake_construct_webhook_event,
    )

    response = client.post(
        "/stripe/webhook",
        content=b"{}",
        headers={"Stripe-Signature": "bad_signature"},
    )

    assert response.status_code == 400, response.text
    assert "Invalid Stripe webhook signature" in response.text


def test_stripe_webhook_succeeded_confirms_booking_and_participants(
    client: TestClient, monkeypatch
):
    checkout = create_pending_checkout(client, monkeypatch, guest_count=1)
    event = build_payment_intent_event(
        checkout,
        event_type="payment_intent.succeeded",
        status="succeeded",
    )

    response = post_stripe_event(client, monkeypatch, event)

    assert response.status_code == 200, response.text
    assert response.json()["processing_status"] == "processed"

    payment_response = client.get(f"/payments/{checkout['payment_id']}")
    assert payment_response.status_code == 200, payment_response.text
    payment = payment_response.json()
    assert payment["payment_status"] == "succeeded"
    assert payment["paid_at"] is not None
    assert payment["provider_charge_id"] == "ch_test_webhook"

    booking_response = client.get(f"/bookings/{checkout['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "confirmed"
    assert booking["payment_status"] == "paid"
    assert booking["booked_at"] is not None
    assert booking["expires_at"] is None

    participants_response = client.get(
        f"/game-participants?booking_id={checkout['booking_id']}"
    )
    assert participants_response.status_code == 200, participants_response.text
    participants = participants_response.json()
    assert len(participants) == 2
    assert {participant["participant_status"] for participant in participants} == {
        "confirmed"
    }
    assert sorted(participant["roster_order"] for participant in participants) == [1, 2]

    checkout_status_response = client.get(
        f"/checkout/bookings/{checkout['booking_id']}/status"
    )
    assert checkout_status_response.status_code == 200, checkout_status_response.text
    checkout_status = checkout_status_response.json()
    assert checkout_status["booking_status"] == "confirmed"
    assert checkout_status["booking_payment_status"] == "paid"
    assert checkout_status["payment_status"] == "succeeded"

    events_response = client.get(f"/payment-events?provider_event_id={event['id']}")
    assert events_response.status_code == 200, events_response.text
    events = events_response.json()
    assert len(events) == 1
    assert events[0]["payment_id"] == checkout["payment_id"]
    assert events[0]["processing_status"] == "processed"


def test_stripe_webhook_duplicate_event_is_idempotent(
    client: TestClient, monkeypatch
):
    checkout = create_pending_checkout(client, monkeypatch)
    event = build_payment_intent_event(
        checkout,
        event_type="payment_intent.succeeded",
        event_id="evt_duplicate_success",
        status="succeeded",
    )

    first_response = post_stripe_event(client, monkeypatch, event)
    second_response = post_stripe_event(client, monkeypatch, event)

    assert first_response.status_code == 200, first_response.text
    assert second_response.status_code == 200, second_response.text
    assert second_response.json()["duplicate"] is True

    events_response = client.get("/payment-events?provider_event_id=evt_duplicate_success")
    assert events_response.status_code == 200, events_response.text
    assert len(events_response.json()) == 1

    participants_response = client.get(
        f"/game-participants?booking_id={checkout['booking_id']}"
    )
    assert participants_response.status_code == 200, participants_response.text
    participants = participants_response.json()
    assert sorted(participant["roster_order"] for participant in participants) == [1, 2]


def test_stripe_webhook_succeeded_amount_mismatch_does_not_confirm_booking(
    client: TestClient, monkeypatch
):
    checkout = create_pending_checkout(client, monkeypatch)
    event = build_payment_intent_event(
        checkout,
        event_type="payment_intent.succeeded",
        amount_cents=checkout["amount_cents"] - 100,
        status="succeeded",
    )

    response = post_stripe_event(client, monkeypatch, event)

    assert response.status_code == 200, response.text
    assert response.json()["processing_status"] == "failed"

    booking_response = client.get(f"/bookings/{checkout['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "pending_payment"
    assert booking["payment_status"] == "processing"

    payment_response = client.get(f"/payments/{checkout['payment_id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "processing"

    events_response = client.get(f"/payment-events?provider_event_id={event['id']}")
    assert events_response.status_code == 200, events_response.text
    event_row = events_response.json()[0]
    assert event_row["processing_status"] == "failed"
    assert "amount" in event_row["processing_error"]


def test_stripe_webhook_succeeded_missing_metadata_does_not_confirm_booking(
    client: TestClient, monkeypatch
):
    checkout = create_pending_checkout(client, monkeypatch)
    event = build_payment_intent_event(
        checkout,
        event_type="payment_intent.succeeded",
        metadata={},
        status="succeeded",
    )

    response = post_stripe_event(client, monkeypatch, event)

    assert response.status_code == 200, response.text
    assert response.json()["processing_status"] == "failed"

    booking_response = client.get(f"/bookings/{checkout['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "pending_payment"
    assert booking["payment_status"] == "processing"

    payment_response = client.get(f"/payments/{checkout['payment_id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "processing"

    events_response = client.get(f"/payment-events?provider_event_id={event['id']}")
    assert events_response.status_code == 200, events_response.text
    event_row = events_response.json()[0]
    assert event_row["processing_status"] == "failed"
    assert "metadata" in event_row["processing_error"]


def test_stripe_webhook_succeeded_participant_mismatch_does_not_mark_payment_succeeded(
    client: TestClient, monkeypatch
):
    checkout = create_pending_checkout(client, monkeypatch, guest_count=1)
    with SessionLocal() as db:
        participant = db.scalars(
            select(GameParticipant)
            .where(
                GameParticipant.booking_id == UUID(checkout["booking_id"]),
                GameParticipant.participant_status == "pending_payment",
            )
            .limit(1)
        ).first()
        assert participant is not None
        participant.participant_status = "cancelled"
        participant.cancellation_type = "payment_failed"
        participant.cancelled_at = datetime.now(timezone.utc)
        db.add(participant)
        db.commit()

    event = build_payment_intent_event(
        checkout,
        event_type="payment_intent.succeeded",
        status="succeeded",
    )

    response = post_stripe_event(client, monkeypatch, event)

    assert response.status_code == 200, response.text
    assert response.json()["processing_status"] == "failed"

    booking_response = client.get(f"/bookings/{checkout['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "pending_payment"
    assert booking["payment_status"] == "processing"

    payment_response = client.get(f"/payments/{checkout['payment_id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "processing"

    events_response = client.get(f"/payment-events?provider_event_id={event['id']}")
    assert events_response.status_code == 200, events_response.text
    event_row = events_response.json()[0]
    assert event_row["processing_status"] == "failed"
    assert "participant count" in event_row["processing_error"]


def test_stripe_webhook_failed_payment_marks_booking_failed_and_clears_hold(
    client: TestClient, monkeypatch
):
    checkout = create_pending_checkout(client, monkeypatch)
    event = build_payment_intent_event(
        checkout,
        event_type="payment_intent.payment_failed",
        status="requires_payment_method",
        last_payment_error={
            "code": "card_declined",
            "message": "Your card was declined.",
        },
    )

    response = post_stripe_event(client, monkeypatch, event)

    assert response.status_code == 200, response.text
    assert response.json()["processing_status"] == "processed"

    payment_response = client.get(f"/payments/{checkout['payment_id']}")
    assert payment_response.status_code == 200, payment_response.text
    payment = payment_response.json()
    assert payment["payment_status"] == "failed"
    assert payment["failure_code"] == "card_declined"
    assert payment["failure_message"] == "Your card was declined."

    booking_response = client.get(f"/bookings/{checkout['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "failed"
    assert booking["payment_status"] == "failed"

    participants_response = client.get(
        f"/game-participants?booking_id={checkout['booking_id']}"
    )
    assert participants_response.status_code == 200, participants_response.text
    participants = participants_response.json()
    assert {participant["participant_status"] for participant in participants} == {
        "cancelled"
    }
    assert {participant["cancellation_type"] for participant in participants} == {
        "payment_failed"
    }


def test_stripe_webhook_canceled_payment_expires_booking_hold(
    client: TestClient, monkeypatch
):
    checkout = create_pending_checkout(client, monkeypatch)
    event = build_payment_intent_event(
        checkout,
        event_type="payment_intent.canceled",
        status="canceled",
    )

    response = post_stripe_event(client, monkeypatch, event)

    assert response.status_code == 200, response.text
    assert response.json()["processing_status"] == "processed"

    payment_response = client.get(f"/payments/{checkout['payment_id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "canceled"

    booking_response = client.get(f"/bookings/{checkout['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "expired"
    assert booking["payment_status"] == "failed"


def test_stripe_webhook_refund_updated_succeeded_marks_payment_refunded(
    client: TestClient, monkeypatch
):
    user, booking, payment = create_refund_webhook_setup(client)
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        provider_refund_id=f"re_{unique_suffix()}",
        amount_cents=payment["amount_cents"],
        refund_reason="game_cancelled",
        refund_status="processing",
        requested_by_user_id=user["id"],
        approved_by_user_id=user["id"],
    )
    event = build_refund_event(
        refund=refund,
        payment=payment,
        booking=booking,
        event_type="refund.updated",
        status="succeeded",
    )

    response = post_stripe_event(client, monkeypatch, event)

    assert response.status_code == 200, response.text
    assert response.json()["processing_status"] == "processed"

    refund_response = client.get(f"/refunds/{refund['id']}")
    assert refund_response.status_code == 200, refund_response.text
    updated_refund = refund_response.json()
    assert updated_refund["refund_status"] == "succeeded"
    assert updated_refund["refunded_at"] is not None

    payment_response = client.get(f"/payments/{payment['id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "refunded"

    booking_response = client.get(f"/bookings/{booking['id']}")
    assert booking_response.status_code == 200, booking_response.text
    assert booking_response.json()["payment_status"] == "refunded"

    events_response = client.get(f"/payment-events?provider_event_id={event['id']}")
    assert events_response.status_code == 200, events_response.text
    event_row = events_response.json()[0]
    assert event_row["payment_id"] == payment["id"]
    assert event_row["processing_status"] == "processed"


def test_stripe_webhook_refund_failed_preserves_paid_payment(
    client: TestClient, monkeypatch
):
    user, booking, payment = create_refund_webhook_setup(client)
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        provider_refund_id=f"re_{unique_suffix()}",
        amount_cents=payment["amount_cents"],
        refund_reason="game_cancelled",
        refund_status="processing",
        requested_by_user_id=user["id"],
        approved_by_user_id=user["id"],
    )
    event = build_refund_event(
        refund=refund,
        payment=payment,
        booking=booking,
        event_type="refund.failed",
        status="failed",
    )

    response = post_stripe_event(client, monkeypatch, event)

    assert response.status_code == 200, response.text
    assert response.json()["processing_status"] == "processed"

    refund_response = client.get(f"/refunds/{refund['id']}")
    assert refund_response.status_code == 200, refund_response.text
    assert refund_response.json()["refund_status"] == "failed"

    payment_response = client.get(f"/payments/{payment['id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "succeeded"

    booking_response = client.get(f"/bookings/{booking['id']}")
    assert booking_response.status_code == 200, booking_response.text
    assert booking_response.json()["payment_status"] == "paid"


def test_stripe_webhook_refund_updated_recovers_missing_internal_refund(
    client: TestClient, monkeypatch
):
    user, booking, payment = create_refund_webhook_setup(client)
    provider_refund_id = f"re_{unique_suffix()}"
    refund = {
        "provider_refund_id": provider_refund_id,
        "amount_cents": payment["amount_cents"],
    }
    event = build_refund_event(
        refund=refund,
        payment=payment,
        booking=booking,
        event_type="refund.updated",
        status="succeeded",
        metadata={
            "source": "official_game_cancel",
            "booking_id": booking["id"],
            "payment_id": payment["id"],
            "admin_user_id": user["id"],
        },
    )

    response = post_stripe_event(client, monkeypatch, event)

    assert response.status_code == 200, response.text
    assert response.json()["processing_status"] == "processed"

    refunds_response = client.get(f"/refunds?payment_id={payment['id']}")
    assert refunds_response.status_code == 200, refunds_response.text
    refunds = [
        item
        for item in refunds_response.json()
        if item["provider_refund_id"] == provider_refund_id
    ]
    assert len(refunds) == 1
    assert refunds[0]["refund_status"] == "succeeded"
    assert refunds[0]["booking_id"] == booking["id"]

    payment_response = client.get(f"/payments/{payment['id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "refunded"


def test_stripe_webhook_unmatched_refund_is_saved_and_ignored(
    client: TestClient, monkeypatch
):
    _user, booking, payment = create_refund_webhook_setup(client)
    refund = {
        "provider_refund_id": "re_missing_internal_refund",
        "amount_cents": payment["amount_cents"],
    }
    event = build_refund_event(
        refund=refund,
        payment=payment,
        booking=booking,
        event_type="refund.updated",
        event_id="evt_unmatched_refund",
        status="succeeded",
        metadata={},
    )

    response = post_stripe_event(client, monkeypatch, event)

    assert response.status_code == 200, response.text
    assert response.json()["processing_status"] == "ignored"

    events_response = client.get(
        "/payment-events?provider_event_id=evt_unmatched_refund"
    )
    assert events_response.status_code == 200, events_response.text
    event_row = events_response.json()[0]
    assert event_row["processing_status"] == "ignored"
    assert event_row["payment_id"] is None


def test_stripe_webhook_unknown_event_is_saved_and_ignored(
    client: TestClient, monkeypatch
):
    event = {
        "id": "evt_unknown_webhook",
        "object": "event",
        "type": "charge.refunded",
        "data": {"object": {"id": "ch_unhandled"}},
    }

    response = post_stripe_event(client, monkeypatch, event)

    assert response.status_code == 200, response.text
    assert response.json()["processing_status"] == "ignored"

    events_response = client.get("/payment-events?provider_event_id=evt_unknown_webhook")
    assert events_response.status_code == 200, events_response.text
    event_row = events_response.json()[0]
    assert event_row["processing_status"] == "ignored"
    assert event_row["payment_id"] is None


def test_stripe_webhook_unmatched_payment_intent_is_saved_and_ignored(
    client: TestClient, monkeypatch
):
    checkout = {
        "user": {"id": "00000000-0000-0000-0000-000000000001"},
        "game": {"id": "00000000-0000-0000-0000-000000000002"},
        "booking_id": "00000000-0000-0000-0000-000000000003",
        "payment_id": "00000000-0000-0000-0000-000000000004",
        "payment_intent_id": "pi_missing_internal_payment",
        "amount_cents": 3000,
        "currency": "USD",
    }
    event = build_payment_intent_event(
        checkout,
        event_type="payment_intent.succeeded",
        event_id="evt_unmatched_intent",
        status="succeeded",
    )

    response = post_stripe_event(client, monkeypatch, event)

    assert response.status_code == 200, response.text
    assert response.json()["processing_status"] == "ignored"

    events_response = client.get("/payment-events?provider_event_id=evt_unmatched_intent")
    assert events_response.status_code == 200, events_response.text
    event_row = events_response.json()[0]
    assert event_row["processing_status"] == "ignored"
    assert event_row["payment_id"] is None
