from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_booking,
    create_game,
    create_game_participant,
    create_payment,
    create_refund,
    create_user,
    create_venue,
    unique_suffix,
)


def create_paid_booking_setup(client: TestClient) -> tuple[dict, dict, dict, dict, dict]:
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    payment = create_payment(
        client,
        user["id"],
        booking_id=booking["id"],
        payment_status="succeeded",
    )
    return user, venue, game, booking, payment


def test_refunds_create_get_list_and_update(client: TestClient):
    user, _venue, _game, booking, payment = create_paid_booking_setup(client)
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        requested_by_user_id=user["id"],
    )

    get_response = client.get(f"/refunds/{refund['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == refund["id"]

    list_response = client.get(f"/refunds?payment_id={payment['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == refund["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/refunds/{refund['id']}",
        json={"refund_status": "approved", "approved_by_user_id": user["id"]},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["refund_status"] == "approved"
    assert patch_response.json()["approved_at"] is not None


def test_refunds_can_scope_to_participant(client: TestClient):
    user, _venue, game, booking, payment = create_paid_booking_setup(client)
    participant = create_game_participant(
        client,
        user["id"],
        game["id"],
        booking_id=booking["id"],
    )

    refund = create_refund(
        client,
        payment["id"],
        participant_id=participant["id"],
        amount_cents=300,
    )

    assert refund["participant_id"] == participant["id"]
    assert refund["booking_id"] is None


def test_refunds_reject_unsucceeded_payment(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    payment = create_payment(client, user["id"], booking_id=booking["id"])

    response = client.post(
        "/refunds",
        json={
            "payment_id": payment["id"],
            "booking_id": booking["id"],
            "provider_refund_id": f"re_{unique_suffix()}",
            "amount_cents": 500,
            "currency": "USD",
            "refund_reason": "player_cancelled",
            "refund_status": "pending",
        },
    )

    assert response.status_code == 400, response.text
    assert "payment that has succeeded" in response.text


def test_refunds_reject_duplicate_provider_refund_id(client: TestClient):
    _user, _venue, _game, booking, payment = create_paid_booking_setup(client)
    provider_refund_id = f"re_{unique_suffix()}"

    create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        provider_refund_id=provider_refund_id,
    )
    response = client.post(
        "/refunds",
        json={
            "payment_id": payment["id"],
            "booking_id": booking["id"],
            "provider_refund_id": provider_refund_id,
            "amount_cents": 100,
            "currency": "USD",
            "refund_reason": "player_cancelled",
            "refund_status": "pending",
        },
    )

    assert response.status_code == 409, response.text
    assert "provider_refund_id already exists" in response.text


def test_refunds_reject_amount_over_remaining_payment(client: TestClient):
    _user, _venue, _game, booking, payment = create_paid_booking_setup(client)

    create_refund(client, payment["id"], booking_id=booking["id"], amount_cents=900)
    response = client.post(
        "/refunds",
        json={
            "payment_id": payment["id"],
            "booking_id": booking["id"],
            "provider_refund_id": f"re_{unique_suffix()}",
            "amount_cents": 500,
            "currency": "USD",
            "refund_reason": "player_cancelled",
            "refund_status": "pending",
        },
    )

    assert response.status_code == 400, response.text
    assert "remaining refundable payment amount" in response.text


def test_refunds_reject_updates_after_terminal_status(client: TestClient):
    _user, _venue, _game, booking, payment = create_paid_booking_setup(client)
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        refund_status="succeeded",
        amount_cents=300,
    )

    response = client.patch(
        f"/refunds/{refund['id']}",
        json={"amount_cents": 200},
    )

    assert response.status_code == 400, response.text
    assert "cannot be updated" in response.text
