from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from backend.services.stripe_service import StripePaymentIntentResult
from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_game_participant,
    create_payment,
    create_user,
    create_user_payment_method,
    create_venue,
    mock_checkout_payment_method_verification,
    set_user_role,
)


def build_official_game_payload(**overrides: object) -> dict:
    starts_at = datetime.now(UTC) + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)
    payload = {
        "title": "Admin Official Match",
        "venue": {
            "name": "Admin Test Field",
            "address_line_1": "500 Admin Ave",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "country_code": "US",
            "neighborhood": "Loop",
        },
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "timezone": "America/Chicago",
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 10,
        "price_per_player_cents": 1500,
        "reason": "Create official game for test coverage.",
    }
    payload.update(overrides)
    return payload


def test_admin_can_create_official_game_without_initial_host(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )

    assert response.status_code == 201, response.text
    game = response.json()["game"]
    assert game["game_type"] == "official"
    assert game["payment_collection_type"] == "in_app"
    assert game["policy_mode"] == "official_standard"
    assert game["publish_status"] == "published"
    assert game["created_by_user_id"] == admin["id"]
    assert game["host_user_id"] is None
    assert game["minimum_age"] is None
    assert game["host_guest_max"] == 0

    audit_response = client.get("/admin/actions?action_type=create_official_game")
    assert audit_response.status_code == 200, audit_response.text
    assert any(
        action["target_game_id"] == game["id"] and action["target_user_id"] is None
        for action in audit_response.json()
    )


def test_admin_can_create_official_game_from_existing_venue(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(venue_id=venue["id"], venue=None),
    )

    assert response.status_code == 201, response.text
    assert response.json()["game"]["venue_id"] == venue["id"]


def test_admin_can_list_and_get_official_games(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    list_response = client.get("/admin/official-games?game_status=scheduled")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == game["id"] for item in list_response.json()["games"])

    get_response = client.get(f"/admin/official-games/{game['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["game"]["id"] == game["id"]


def test_admin_can_list_official_game_participants_from_admin_route(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        price_cents=1500,
    )

    response = client.get(f"/admin/official-games/{game['id']}/participants")

    assert response.status_code == 200, response.text
    assert any(item["id"] == participant["id"] for item in response.json())


def test_admin_lookup_routes_return_users_and_venues(client: TestClient):
    admin = create_user(client, first_name="Admin", last_name="Lookup")
    player = create_user(client, first_name="Player", last_name="Lookup")
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"], name="Lookup Field")

    authenticate_as(admin["id"])
    users_response = client.get("/admin/lookups/users?query=lookup")
    venues_response = client.get("/admin/lookups/venues?query=lookup")

    assert users_response.status_code == 200, users_response.text
    assert {user["id"] for user in users_response.json()} >= {
        admin["id"],
        player["id"],
    }
    assert venues_response.status_code == 200, venues_response.text
    assert any(item["id"] == venue["id"] for item in venues_response.json())


def test_admin_can_update_official_game_details(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    starts_at = datetime.now(UTC) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=1, minutes=30)

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    update_response = client.patch(
        f"/admin/official-games/{game['id']}",
        json={
            "title": "Updated Official Match",
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "total_spots": 12,
            "price_per_player_cents": 1000,
            "game_notes": "Bring both shirts.",
            "parking_notes": "Use the north lot.",
            "reason": "Update match details.",
        },
    )

    assert update_response.status_code == 200, update_response.text
    updated_game = update_response.json()["game"]
    assert updated_game["title"] == "Updated Official Match"
    assert updated_game["venue_id"] == game["venue_id"]
    assert updated_game["venue_name_snapshot"] == game["venue_name_snapshot"]
    assert updated_game["total_spots"] == 12
    assert updated_game["price_per_player_cents"] == 1000
    assert updated_game["game_notes"] == "Bring both shirts."
    assert updated_game["parking_notes"] == "Use the north lot."

    audit_response = client.get(
        f"/admin/actions?action_type=update_official_game&target_game_id={game['id']}"
    )
    assert audit_response.status_code == 200, audit_response.text
    audit_rows = audit_response.json()
    assert len(audit_rows) == 1
    assert "price_per_player_cents" in audit_rows[0]["metadata"]["changed_fields"]
    assert audit_rows[0]["target_venue_id"] is None


def test_admin_official_game_update_rejects_capacity_below_roster(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(format_label="3v3", total_spots=10),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    for index in range(7):
        player = create_user(client)
        create_game_participant(
            client,
            player["id"],
            game["id"],
            price_cents=1500,
            roster_order=index + 1,
        )

    response = client.patch(
        f"/admin/official-games/{game['id']}",
        json={"total_spots": 6, "reason": "Reduce capacity."},
    )

    assert response.status_code == 400, response.text
    assert "active roster count" in response.text


def test_admin_official_game_update_invalidates_pending_checkout(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    def fake_create_payment_intent(**kwargs):
        return StripePaymentIntentResult(
            id="pi_admin_update_pending",
            client_secret="pi_admin_update_pending_secret",
            status="requires_payment_method",
        )

    def fake_confirm_payment_intent(payment_intent_id, **kwargs):
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="pi_admin_update_pending_secret",
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

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    authenticate_as(player["id"])
    payment_method = create_user_payment_method(
        client,
        player["id"],
        stripe_customer_id="cus_admin_update_pending",
        stripe_payment_method_id="pm_admin_update_pending",
    )
    mock_checkout_payment_method_verification(monkeypatch, payment_method)
    checkout_response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={
            "guest_count": 0,
            "payment_method_id": payment_method["id"],
        },
    )
    assert checkout_response.status_code == 201, checkout_response.text
    checkout = checkout_response.json()

    authenticate_as(admin["id"])
    update_response = client.patch(
        f"/admin/official-games/{game['id']}",
        json={
            "price_per_player_cents": 1000,
            "reason": "Late discount.",
        },
    )
    assert update_response.status_code == 200, update_response.text

    booking_response = client.get(f"/bookings/{checkout['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "expired"
    assert booking["payment_status"] == "failed"

    payment_response = client.get(f"/payments/{checkout['payment_id']}")
    assert payment_response.status_code == 200, payment_response.text
    payment = payment_response.json()
    assert payment["payment_status"] == "canceled"
    assert payment["failure_code"] == "admin_game_updated"

    participants_response = client.get(
        f"/game-participants?booking_id={checkout['booking_id']}"
    )
    assert participants_response.status_code == 200, participants_response.text
    assert {
        participant["participant_status"]
        for participant in participants_response.json()
    } == {"cancelled"}

    audit_response = client.get(
        f"/admin/actions?action_type=update_official_game&target_game_id={game['id']}"
    )
    assert audit_response.status_code == 200, audit_response.text
    audit_metadata = audit_response.json()[0]["metadata"]
    assert (
        "price_per_player_cents"
        in audit_metadata["checkout_sensitive_changed_fields"]
    )
    assert audit_metadata["expired_pending_booking_count"] == 1


def test_admin_official_game_update_rejects_removed_edit_fields(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    venue = create_venue(client, admin["id"])

    for payload, rejected_field in (
        ({"venue_id": venue["id"]}, "venue_id"),
        ({"minimum_age": 21}, "minimum_age"),
        ({"host_guest_max": 4}, "host_guest_max"),
        ({"description": "Internal edit"}, "description"),
    ):
        update_response = client.patch(
            f"/admin/official-games/{game['id']}",
            json=payload,
        )
        assert update_response.status_code == 422, update_response.text
        assert rejected_field in update_response.text


def test_admin_can_add_player_with_waived_payment(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    add_response = client.post(
        f"/admin/official-games/{game['id']}/players",
        json={
            "user_id": player["id"],
            "reason": "Comp player for helping run warmups.",
        },
    )

    assert add_response.status_code == 201, add_response.text
    participant = add_response.json()
    assert participant["participant_type"] == "admin_added"
    assert participant["participant_status"] == "confirmed"
    assert participant["user_id"] == player["id"]
    assert participant["price_cents"] == 0

    booking_response = client.get(f"/bookings/{participant['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "confirmed"
    assert booking["payment_status"] == "not_required"
    assert booking["subtotal_cents"] == game["price_per_player_cents"]
    assert booking["discount_cents"] == game["price_per_player_cents"]
    assert booking["total_cents"] == 0

    payments_response = client.get(f"/payments?booking_id={participant['booking_id']}")
    assert payments_response.status_code == 200, payments_response.text
    assert payments_response.json() == []

    audit_response = client.get(
        f"/admin/actions?action_type=admin_add_player&target_game_id={game['id']}"
    )
    assert audit_response.status_code == 200, audit_response.text
    audit_rows = audit_response.json()
    assert len(audit_rows) == 1
    assert audit_rows[0]["target_user_id"] == player["id"]
    assert audit_rows[0]["metadata"]["payment_handling"] == "waived"
    assert audit_rows[0]["metadata"]["created_payment"] is False


def test_admin_official_game_add_player_rejects_duplicate_and_full_game(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(format_label="3v3", total_spots=6),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    add_response = client.post(
        f"/admin/official-games/{game['id']}/players",
        json={"user_id": player["id"]},
    )
    assert add_response.status_code == 201, add_response.text

    duplicate_response = client.post(
        f"/admin/official-games/{game['id']}/players",
        json={"user_id": player["id"]},
    )
    assert duplicate_response.status_code == 400, duplicate_response.text
    assert "already has an active roster row" in duplicate_response.text

    for index in range(5):
        extra_player = create_user(client)
        create_game_participant(
            client,
            extra_player["id"],
            game["id"],
            price_cents=1500,
            roster_order=index + 2,
        )

    full_response = client.post(
        f"/admin/official-games/{game['id']}/players",
        json={"user_id": create_user(client)["id"]},
    )
    assert full_response.status_code == 400, full_response.text
    assert "already full" in full_response.text


def test_admin_can_remove_admin_added_player(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    add_response = client.post(
        f"/admin/official-games/{game['id']}/players",
        json={"user_id": player["id"], "reason": "Waive payment."},
    )
    assert add_response.status_code == 201, add_response.text
    participant = add_response.json()

    remove_response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/participants/{participant['id']}",
        json={"reason": "Player cannot make it."},
    )

    assert remove_response.status_code == 200, remove_response.text
    removed_participant = remove_response.json()
    assert removed_participant["participant_status"] == "removed"
    assert removed_participant["cancellation_type"] == "admin_cancelled"
    assert removed_participant["attendance_status"] == "not_applicable"

    booking_response = client.get(f"/bookings/{participant['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "cancelled"
    assert booking["payment_status"] == "not_required"
    assert booking["cancelled_by_user_id"] == admin["id"]

    audit_response = client.get(
        f"/admin/actions?action_type=admin_remove_player&target_game_id={game['id']}"
    )
    assert audit_response.status_code == 200, audit_response.text
    audit_rows = audit_response.json()
    assert len(audit_rows) == 1
    assert audit_rows[0]["target_participant_id"] == participant["id"]
    assert audit_rows[0]["metadata"]["payment_refund_created"] is False


def test_admin_remove_paid_player_does_not_refund_payment(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=1300,
        payment_status="succeeded",
    )

    remove_response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/participants/{participant['id']}",
        json={"reason": "Admin support removal."},
    )

    assert remove_response.status_code == 200, remove_response.text
    payment_response = client.get(f"/payments/{payment['id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "succeeded"

    booking_response = client.get(f"/bookings/{booking['id']}")
    assert booking_response.status_code == 200, booking_response.text
    updated_booking = booking_response.json()
    assert updated_booking["booking_status"] == "cancelled"
    assert updated_booking["payment_status"] == "paid"


def test_admin_remove_pending_checkout_party_invalidates_payment(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    def fake_create_payment_intent(**kwargs):
        return StripePaymentIntentResult(
            id="pi_admin_remove_pending",
            client_secret="pi_admin_remove_pending_secret",
            status="requires_payment_method",
        )

    def fake_confirm_payment_intent(payment_intent_id, **kwargs):
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="pi_admin_remove_pending_secret",
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

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    authenticate_as(player["id"])
    payment_method = create_user_payment_method(
        client,
        player["id"],
        stripe_customer_id="cus_admin_remove_pending",
        stripe_payment_method_id="pm_admin_remove_pending",
    )
    mock_checkout_payment_method_verification(monkeypatch, payment_method)
    checkout_response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={
            "guest_count": 1,
            "payment_method_id": payment_method["id"],
        },
    )
    assert checkout_response.status_code == 201, checkout_response.text
    checkout = checkout_response.json()
    participants_response = client.get(
        f"/game-participants?booking_id={checkout['booking_id']}"
    )
    assert participants_response.status_code == 200, participants_response.text
    pending_participants = participants_response.json()
    guest = next(
        participant
        for participant in pending_participants
        if participant["participant_type"] == "guest"
    )

    authenticate_as(admin["id"])
    remove_response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/participants/{guest['id']}",
        json={"reason": "Clear pending hold."},
    )

    assert remove_response.status_code == 200, remove_response.text
    booking_response = client.get(f"/bookings/{checkout['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    assert booking_response.json()["booking_status"] == "cancelled"
    assert booking_response.json()["payment_status"] == "failed"

    payment_response = client.get(f"/payments/{checkout['payment_id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "canceled"
    assert payment_response.json()["failure_code"] == "admin_player_removed"

    removed_participants_response = client.get(
        f"/game-participants?booking_id={checkout['booking_id']}"
    )
    assert removed_participants_response.status_code == 200
    assert {
        participant["participant_status"]
        for participant in removed_participants_response.json()
    } == {"removed"}


def test_admin_can_assign_change_and_remove_official_game_host(client: TestClient):
    admin = create_user(client)
    first_host = create_user(client)
    second_host = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    assert game["host_user_id"] is None

    assign_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={
            "host_user_id": first_host["id"],
            "reason": "Assign first host.",
        },
    )
    assert assign_response.status_code == 200, assign_response.text
    assert assign_response.json()["game"]["host_user_id"] == first_host["id"]

    change_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={
            "host_user_id": second_host["id"],
            "reason": "Change host.",
        },
    )
    assert change_response.status_code == 200, change_response.text
    assert change_response.json()["game"]["host_user_id"] == second_host["id"]

    first_host_participants_response = client.get(
        f"/game-participants?game_id={game['id']}&user_id={first_host['id']}"
    )
    assert first_host_participants_response.status_code == 200
    assert first_host_participants_response.json()[0]["participant_status"] == "removed"

    second_host_participants_response = client.get(
        f"/game-participants?game_id={game['id']}&user_id={second_host['id']}"
    )
    assert second_host_participants_response.status_code == 200
    assert second_host_participants_response.json()[0]["participant_type"] == "host"
    assert second_host_participants_response.json()[0]["participant_status"] == "confirmed"

    remove_response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/host",
        json={"reason": "No host yet."},
    )
    assert remove_response.status_code == 200, remove_response.text
    assert remove_response.json()["game"]["host_user_id"] is None

    second_host_after_remove_response = client.get(
        f"/game-participants?game_id={game['id']}&user_id={second_host['id']}"
    )
    assert second_host_after_remove_response.status_code == 200
    assert second_host_after_remove_response.json()[0]["participant_status"] == "removed"

    assign_audit_response = client.get(
        f"/admin/actions?action_type=assign_official_host&target_game_id={game['id']}"
    )
    assert assign_audit_response.status_code == 200, assign_audit_response.text
    assert len(assign_audit_response.json()) == 2

    remove_audit_response = client.get(
        f"/admin/actions?action_type=remove_official_host&target_game_id={game['id']}"
    )
    assert remove_audit_response.status_code == 200, remove_audit_response.text
    assert len(remove_audit_response.json()) == 1


def test_admin_official_game_host_rejects_active_player(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    create_game_participant(client, player["id"], game["id"], price_cents=1500)

    response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": player["id"]},
    )

    assert response.status_code == 400, response.text
    assert "already has an active roster row" in response.text


def test_admin_official_game_host_rejects_full_game_without_current_host(
    client: TestClient,
):
    admin = create_user(client)
    host = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    for index in range(game["total_spots"]):
        player = create_user(client)
        create_game_participant(
            client,
            player["id"],
            game["id"],
            price_cents=1500,
            roster_order=index + 1,
        )

    response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": host["id"]},
    )

    assert response.status_code == 400, response.text
    assert "already full" in response.text


def test_admin_can_remove_official_game_host_without_body(client: TestClient):
    admin = create_user(client)
    host = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    assign_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": host["id"]},
    )
    assert assign_response.status_code == 200, assign_response.text

    response = client.delete(f"/admin/official-games/{game['id']}/host")

    assert response.status_code == 200, response.text
    assert response.json()["game"]["host_user_id"] is None


def test_admin_official_game_list_rejects_invalid_status_filter(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get("/admin/official-games?game_status=weird")

    assert response.status_code == 400, response.text
    assert "game_status must be" in response.text


def test_admin_official_game_routes_reject_non_admin(client: TestClient):
    user = create_user(client)

    authenticate_as(user["id"])
    response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )

    assert response.status_code == 403, response.text

    patch_response = client.patch(
        "/admin/official-games/00000000-0000-0000-0000-000000000000",
        json={"title": "Nope"},
    )
    assert patch_response.status_code == 403, patch_response.text

    add_player_response = client.post(
        "/admin/official-games/00000000-0000-0000-0000-000000000000/players",
        json={"user_id": user["id"]},
    )
    assert add_player_response.status_code == 403, add_player_response.text

    participants_response = client.get(
        "/admin/official-games/00000000-0000-0000-0000-000000000000/participants"
    )
    assert participants_response.status_code == 403, participants_response.text

    lookup_users_response = client.get("/admin/lookups/users")
    assert lookup_users_response.status_code == 403, lookup_users_response.text

    lookup_venues_response = client.get("/admin/lookups/venues")
    assert lookup_venues_response.status_code == 403, lookup_venues_response.text


def test_admin_official_game_create_rejects_client_managed_invariants(
    client: TestClient,
):
    admin = create_user(client)
    host = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    for payload, rejected_field in (
        (build_official_game_payload(game_type="community"), "game_type"),
        (build_official_game_payload(host_user_id=host["id"]), "host_user_id"),
        (build_official_game_payload(minimum_age=18), "minimum_age"),
        (build_official_game_payload(host_guest_max=4), "host_guest_max"),
        (build_official_game_payload(description="Internal edit"), "description"),
    ):
        response = client.post("/admin/official-games", json=payload)
        assert response.status_code == 422, response.text
        assert rejected_field in response.text


def test_admin_official_game_update_rejects_client_managed_invariants(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    response = client.patch(
        f"/admin/official-games/{game['id']}",
        json={"game_type": "community"},
    )

    assert response.status_code == 422, response.text
    assert "game_type" in response.text


def test_admin_official_game_create_requires_one_venue_source(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(venue_id=venue["id"]),
    )

    assert response.status_code == 400, response.text
    assert "either venue_id or venue" in response.text
