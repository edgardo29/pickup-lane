from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_booking,
    create_booking_policy_acceptance,
    create_game,
    create_policy_document,
    create_user,
    create_venue,
)


def create_booking_policy_acceptance_setup(
    client: TestClient,
) -> tuple[dict, dict, dict, dict]:
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    policy_document = create_policy_document(
        client,
        policy_type="refund_policy",
    )
    return user, game, booking, policy_document


def test_booking_policy_acceptance_create_get_list_and_update_accepted_at(
    client: TestClient,
):
    _user, _game, booking, policy_document = create_booking_policy_acceptance_setup(
        client
    )
    booking_policy_acceptance = create_booking_policy_acceptance(
        client,
        booking["id"],
        policy_document["id"],
    )

    get_response = client.get(
        f"/booking-policy-acceptances/{booking_policy_acceptance['id']}"
    )
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == booking_policy_acceptance["id"]

    list_by_booking_response = client.get(
        f"/booking-policy-acceptances?booking_id={booking['id']}"
    )
    assert list_by_booking_response.status_code == 200, list_by_booking_response.text
    assert any(
        item["id"] == booking_policy_acceptance["id"]
        for item in list_by_booking_response.json()
    )

    list_by_document_response = client.get(
        f"/booking-policy-acceptances?policy_document_id={policy_document['id']}"
    )
    assert list_by_document_response.status_code == 200, list_by_document_response.text
    assert any(
        item["id"] == booking_policy_acceptance["id"]
        for item in list_by_document_response.json()
    )

    corrected_accepted_at = datetime.now(UTC).isoformat()
    patch_response = client.patch(
        f"/booking-policy-acceptances/{booking_policy_acceptance['id']}",
        json={"accepted_at": corrected_accepted_at},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["accepted_at"] is not None


def test_booking_policy_acceptance_reject_duplicate_booking_policy_document(
    client: TestClient,
):
    _user, _game, booking, policy_document = create_booking_policy_acceptance_setup(
        client
    )
    create_booking_policy_acceptance(client, booking["id"], policy_document["id"])

    response = client.post(
        "/booking-policy-acceptances",
        json={
            "booking_id": booking["id"],
            "policy_document_id": policy_document["id"],
        },
    )

    assert response.status_code == 409, response.text
    assert "This booking has already accepted this policy document" in response.text


def test_booking_policy_acceptance_reject_missing_booking(client: TestClient):
    policy_document = create_policy_document(client)

    response = client.post(
        "/booking-policy-acceptances",
        json={
            "booking_id": "00000000-0000-4000-8000-000000000000",
            "policy_document_id": policy_document["id"],
        },
    )

    assert response.status_code == 404, response.text
    assert "Booking not found" in response.text


def test_booking_policy_acceptance_reject_missing_policy_document(
    client: TestClient,
):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])

    response = client.post(
        "/booking-policy-acceptances",
        json={
            "booking_id": booking["id"],
            "policy_document_id": "00000000-0000-4000-8000-000000000000",
        },
    )

    assert response.status_code == 404, response.text
    assert "Policy document not found" in response.text


def test_booking_policy_acceptance_reject_inactive_policy_document(
    client: TestClient,
):
    _user, _game, booking, _policy_document = create_booking_policy_acceptance_setup(
        client
    )
    inactive_policy_document = create_policy_document(
        client,
        policy_type="refund_policy",
        is_active=False,
    )

    response = client.post(
        "/booking-policy-acceptances",
        json={
            "booking_id": booking["id"],
            "policy_document_id": inactive_policy_document["id"],
        },
    )

    assert response.status_code == 400, response.text
    assert "active, non-retired policy document" in response.text


def test_booking_policy_acceptance_reject_retired_policy_document(
    client: TestClient,
):
    _user, _game, booking, _policy_document = create_booking_policy_acceptance_setup(
        client
    )
    effective_at = datetime.now(UTC)
    retired_policy_document = create_policy_document(
        client,
        policy_type="refund_policy",
        effective_at=effective_at.isoformat(),
        retired_at=(effective_at.replace(year=effective_at.year + 1)).isoformat(),
        is_active=False,
    )

    response = client.post(
        "/booking-policy-acceptances",
        json={
            "booking_id": booking["id"],
            "policy_document_id": retired_policy_document["id"],
        },
    )

    assert response.status_code == 400, response.text
    assert "active, non-retired policy document" in response.text


def test_booking_policy_acceptance_reject_future_effective_policy_document(
    client: TestClient,
):
    _user, _game, booking, _policy_document = create_booking_policy_acceptance_setup(
        client
    )
    future_policy_document = create_policy_document(
        client,
        policy_type="refund_policy",
        effective_at="2999-01-01T00:00:00+00:00",
    )

    response = client.post(
        "/booking-policy-acceptances",
        json={
            "booking_id": booking["id"],
            "policy_document_id": future_policy_document["id"],
        },
    )

    assert response.status_code == 400, response.text
    assert "already effective" in response.text


def test_booking_policy_acceptance_reject_null_accepted_at_update(
    client: TestClient,
):
    _user, _game, booking, policy_document = create_booking_policy_acceptance_setup(
        client
    )
    booking_policy_acceptance = create_booking_policy_acceptance(
        client,
        booking["id"],
        policy_document["id"],
    )

    response = client.patch(
        f"/booking-policy-acceptances/{booking_policy_acceptance['id']}",
        json={"accepted_at": None},
    )

    assert response.status_code == 400, response.text
    assert "accepted_at cannot be null" in response.text
