from fastapi.testclient import TestClient
from datetime import UTC, datetime, timedelta

from backend.tests.helpers import (
    create_game,
    create_game_participant,
    create_user,
    create_venue,
)


def test_games_create_get_list_update_and_soft_delete(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)

    get_response = client.get(f"/games/{game['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == game["id"]

    list_response = client.get("/games")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == game["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/games/{game['id']}",
        json={"title": "Updated CI Test Match"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["title"] == "Updated CI Test Match"

    delete_response = client.delete(f"/games/{game['id']}")
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["deleted_at"] is not None


def test_games_reject_invalid_schedule(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])

    response = client.post(
        "/games",
        json={
            "game_type": "official",
            "publish_status": "draft",
            "game_status": "scheduled",
            "title": "Bad Schedule",
            "venue_id": venue["id"],
            "venue_name_snapshot": venue["name"],
            "address_snapshot": venue["address_line_1"],
            "city_snapshot": venue["city"],
            "state_snapshot": venue["state"],
            "created_by_user_id": user["id"],
            "starts_at": "2026-01-01T10:00:00Z",
            "ends_at": "2026-01-01T09:00:00Z",
            "format_label": "5v5",
            "environment_type": "indoor",
            "total_spots": 10,
            "price_per_player_cents": 1200,
            "policy_mode": "official_standard",
        },
    )

    assert response.status_code == 400, response.text
    assert "ends_at must be greater than starts_at" in response.text


def test_games_reject_past_start_time(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    starts_at = datetime.now(UTC) - timedelta(hours=1)
    ends_at = starts_at + timedelta(hours=2)

    response = client.post(
        "/games",
        json={
            "game_type": "official",
            "publish_status": "published",
            "game_status": "scheduled",
            "title": "Past Start",
            "venue_id": venue["id"],
            "venue_name_snapshot": venue["name"],
            "address_snapshot": venue["address_line_1"],
            "city_snapshot": venue["city"],
            "state_snapshot": venue["state"],
            "created_by_user_id": user["id"],
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "format_label": "5v5",
            "environment_type": "indoor",
            "total_spots": 10,
            "price_per_player_cents": 1200,
            "policy_mode": "official_standard",
        },
    )

    assert response.status_code == 400, response.text
    assert "start time must be in the future" in response.text


def test_games_reject_total_spots_below_format_minimum(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    starts_at = datetime.now(UTC) + timedelta(days=5)
    ends_at = starts_at + timedelta(hours=2)

    response = client.post(
        "/games",
        json={
            "game_type": "official",
            "publish_status": "published",
            "game_status": "scheduled",
            "title": "Too Few Spots",
            "venue_id": venue["id"],
            "venue_name_snapshot": venue["name"],
            "address_snapshot": venue["address_line_1"],
            "city_snapshot": venue["city"],
            "state_snapshot": venue["state"],
            "created_by_user_id": user["id"],
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "format_label": "7v7",
            "environment_type": "indoor",
            "total_spots": 10,
            "price_per_player_cents": 1200,
            "policy_mode": "official_standard",
        },
    )

    assert response.status_code == 400, response.text
    assert "at least 14" in response.text


def test_host_edit_allows_host_to_update_empty_community_game(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        title="Original Community Game",
    )
    starts_at = datetime.now(UTC) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=2)

    response = client.patch(
        f"/games/{game['id']}/host-edit",
        json={
            "acting_user_id": host["id"],
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "format_label": "7v7",
            "environment_type": "outdoor",
            "total_spots": 14,
            "price_per_player_cents": 2500,
            "venue_name": "New Community Field",
            "address_line_1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60607",
            "neighborhood": "West Loop",
            "game_notes": "Bring a light and dark shirt.",
        },
    )

    assert response.status_code == 200, response.text
    updated_game = response.json()
    assert updated_game["format_label"] == "7v7"
    assert updated_game["price_per_player_cents"] == 2500
    assert updated_game["venue_name_snapshot"] == "New Community Field"
    assert updated_game["game_notes"] == "Bring a light and dark shirt."


def test_host_edit_reuses_existing_matching_venue(client: TestClient):
    host = create_user(client)
    original_venue = create_venue(client, host["id"])
    reusable_venue = create_venue(
        client,
        host["id"],
        name="Reusable Community Field",
        address_line_1="456 Shared Ave",
        city="Chicago",
        state="IL",
        postal_code="60608",
        neighborhood="Pilsen",
    )
    game = create_game(
        client,
        host["id"],
        original_venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )

    response = client.patch(
        f"/games/{game['id']}/host-edit",
        json={
            "acting_user_id": host["id"],
            "venue_name": "Reusable Community Field",
            "address_line_1": "456 Shared Ave",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60608",
            "neighborhood": "Pilsen",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["venue_id"] == reusable_venue["id"]


def test_host_edit_blocks_major_changes_after_players_join(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    create_game_participant(client, player["id"], game["id"])

    price_response = client.patch(
        f"/games/{game['id']}/host-edit",
        json={
            "acting_user_id": host["id"],
            "price_per_player_cents": 1800,
        },
    )
    assert price_response.status_code == 400, price_response.text
    assert "cannot be changed after players have joined" in price_response.text

    notes_response = client.patch(
        f"/games/{game['id']}/host-edit",
        json={
            "acting_user_id": host["id"],
            "game_notes": "Use the north entrance.",
        },
    )
    assert notes_response.status_code == 200, notes_response.text
    assert notes_response.json()["game_notes"] == "Use the north entrance."


def test_join_game_creates_booking_and_participant(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)

    response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"]},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "joined"
    assert body["participant_id"]
    assert body["booking_id"]

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    assert any(
        item["user_id"] == player["id"] and item["participant_status"] == "confirmed"
        for item in participants_response.json()
    )


def test_join_game_with_guests_creates_party_booking_and_guest_participants(
    client: TestClient,
):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)

    response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"], "guest_count": 2},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "joined"
    assert body["booking_id"]

    booking_response = client.get(f"/bookings/{body['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["participant_count"] == 3
    assert booking["payment_status"] == "paid"
    assert booking["total_cents"] == game["price_per_player_cents"] * 3

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    participants = [
        item
        for item in participants_response.json()
        if item["booking_id"] == body["booking_id"]
    ]
    assert len(participants) == 3
    assert sum(item["participant_type"] == "guest" for item in participants) == 2
    assert {item["participant_status"] for item in participants} == {"confirmed"}
    assert all(
        item["guest_of_user_id"] == player["id"]
        for item in participants
        if item["participant_type"] == "guest"
    )

    payments_response = client.get(f"/payments?booking_id={body['booking_id']}")
    assert payments_response.status_code == 200, payments_response.text
    payments = payments_response.json()
    assert len(payments) == 1
    assert payments[0]["payment_status"] == "succeeded"
    assert payments[0]["amount_cents"] == game["price_per_player_cents"] * 3


def test_join_game_rejects_too_many_guests(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue, max_guests_per_booking=2)

    response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"], "guest_count": 3},
    )

    assert response.status_code == 400, response.text
    assert "allows up to 2 guests" in response.text


def test_join_game_waitlists_whole_party_when_not_enough_spots(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)

    for _index in range(8):
        player = create_user(client)
        fill_response = client.post(
            f"/games/{game['id']}/join",
            json={"acting_user_id": player["id"]},
        )
        assert fill_response.status_code == 201, fill_response.text

    waitlisted_player = create_user(client)
    response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": waitlisted_player["id"], "guest_count": 2},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "waitlisted"
    assert body["booking_id"]
    assert body["waitlist_entry_id"]

    waitlist_response = client.get(f"/waitlist-entries/{body['waitlist_entry_id']}")
    assert waitlist_response.status_code == 200, waitlist_response.text
    assert waitlist_response.json()["party_size"] == 3

    booking_response = client.get(f"/bookings/{body['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["participant_count"] == 3
    assert booking["payment_status"] == "unpaid"

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    participants = [
        item
        for item in participants_response.json()
        if item["booking_id"] == body["booking_id"]
    ]
    assert len(participants) == 3
    assert sum(item["participant_type"] == "guest" for item in participants) == 2
    assert {item["participant_status"] for item in participants} == {"waitlisted"}


def test_leave_game_cancels_participant(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"]},
    )
    assert join_response.status_code == 201, join_response.text

    response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": player["id"]},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "left_game"
    assert body["refund_eligible"] is True

    participant_response = client.get(f"/game-participants/{body['participant_id']}")
    assert participant_response.status_code == 200, participant_response.text
    assert participant_response.json()["participant_status"] == "cancelled"


def test_leave_game_cancels_guest_participants_for_booking(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"], "guest_count": 2},
    )
    assert join_response.status_code == 201, join_response.text
    booking_id = join_response.json()["booking_id"]

    response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": player["id"]},
    )

    assert response.status_code == 200, response.text

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    participants = [
        item
        for item in participants_response.json()
        if item["booking_id"] == booking_id
    ]
    assert len(participants) == 3
    assert {item["participant_status"] for item in participants} == {"cancelled"}


def test_remove_guest_keeps_player_joined_and_marks_payment_partially_refunded(
    client: TestClient,
):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"], "guest_count": 2},
    )
    assert join_response.status_code == 201, join_response.text
    booking_id = join_response.json()["booking_id"]

    response = client.post(
        f"/games/{game['id']}/guests/remove",
        json={"acting_user_id": player["id"], "remove_count": 1},
    )

    assert response.status_code == 200, response.text
    assert response.json()["removed_count"] == 1

    booking_response = client.get(f"/bookings/{booking_id}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["participant_count"] == 2
    assert booking["booking_status"] == "partially_cancelled"
    assert booking["payment_status"] == "partially_refunded"

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    participants = [
        item
        for item in participants_response.json()
        if item["booking_id"] == booking_id
    ]
    assert sum(item["participant_status"] == "cancelled" for item in participants) == 1
    assert sum(item["participant_status"] == "confirmed" for item in participants) == 2

    payments_response = client.get(f"/payments?booking_id={booking_id}")
    assert payments_response.status_code == 200, payments_response.text
    assert payments_response.json()[0]["payment_status"] == "partially_refunded"


def test_leave_waitlist_with_guests_keeps_booking_unpaid(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)

    for _index in range(8):
        player = create_user(client)
        fill_response = client.post(
            f"/games/{game['id']}/join",
            json={"acting_user_id": player["id"]},
        )
        assert fill_response.status_code == 201, fill_response.text

    waitlisted_player = create_user(client)
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": waitlisted_player["id"], "guest_count": 2},
    )
    assert join_response.status_code == 201, join_response.text
    booking_id = join_response.json()["booking_id"]

    response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": waitlisted_player["id"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "left_waitlist"

    booking_response = client.get(f"/bookings/{booking_id}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "cancelled"
    assert booking["payment_status"] == "unpaid"
    assert booking["cancel_reason"] == "waitlist_cancelled"


def test_leave_game_promotes_waitlist_party_when_enough_spots_open(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue, format_label="3v3", total_spots=6)
    joined_players = []

    for _index in range(6):
        player = create_user(client)
        fill_response = client.post(
            f"/games/{game['id']}/join",
            json={"acting_user_id": player["id"]},
        )
        assert fill_response.status_code == 201, fill_response.text
        joined_players.append(player)

    waitlisted_player = create_user(client)
    waitlist_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": waitlisted_player["id"]},
    )
    assert waitlist_response.status_code == 201, waitlist_response.text
    waitlist_body = waitlist_response.json()
    assert waitlist_body["status"] == "waitlisted"

    leave_response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": joined_players[0]["id"]},
    )
    assert leave_response.status_code == 200, leave_response.text

    promoted_booking_response = client.get(f"/bookings/{waitlist_body['booking_id']}")
    assert promoted_booking_response.status_code == 200, promoted_booking_response.text
    promoted_booking = promoted_booking_response.json()
    assert promoted_booking["booking_status"] == "confirmed"
    assert promoted_booking["payment_status"] == "paid"

    waitlist_entry_response = client.get(
        f"/waitlist-entries/{waitlist_body['waitlist_entry_id']}"
    )
    assert waitlist_entry_response.status_code == 200, waitlist_entry_response.text
    waitlist_entry = waitlist_entry_response.json()
    assert waitlist_entry["waitlist_status"] == "accepted"
    assert waitlist_entry["promoted_booking_id"] == waitlist_body["booking_id"]

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    promoted_participant = next(
        item
        for item in participants_response.json()
        if item["user_id"] == waitlisted_player["id"]
    )
    assert promoted_participant["participant_status"] == "confirmed"

    payments_response = client.get(f"/payments?booking_id={waitlist_body['booking_id']}")
    assert payments_response.status_code == 200, payments_response.text
    assert payments_response.json()[0]["payment_status"] == "succeeded"

    notifications_response = client.get(f"/notifications?user_id={waitlisted_player['id']}")
    assert notifications_response.status_code == 200, notifications_response.text
    assert any(
        item["notification_type"] == "waitlist_promoted"
        for item in notifications_response.json()
    )


def test_host_can_add_and_remove_host_guests(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        format_label="3v3",
        total_spots=6,
    )
    host_participant = create_game_participant(
        client,
        host["id"],
        game["id"],
        participant_type="host",
        price_cents=0,
    )
    assert host_participant["participant_type"] == "host"

    add_response = client.post(
        f"/games/{game['id']}/guests/add",
        json={"acting_user_id": host["id"], "guest_count": 2},
    )
    assert add_response.status_code == 201, add_response.text
    assert add_response.json()["added_count"] == 2

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    host_guests = [
        item
        for item in participants_response.json()
        if item["participant_type"] == "guest"
        and item["guest_of_user_id"] == host["id"]
        and item["participant_status"] == "confirmed"
    ]
    assert len(host_guests) == 2
    assert all(item["booking_id"] is None for item in host_guests)
    assert all(item["price_cents"] == 0 for item in host_guests)

    remove_response = client.post(
        f"/games/{game['id']}/guests/remove",
        json={"acting_user_id": host["id"], "remove_count": 1},
    )
    assert remove_response.status_code == 200, remove_response.text
    assert remove_response.json()["removed_count"] == 1

    updated_participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert updated_participants_response.status_code == 200, updated_participants_response.text
    updated_host_guests = [
        item
        for item in updated_participants_response.json()
        if item["participant_type"] == "guest" and item["guest_of_user_id"] == host["id"]
    ]
    assert sum(item["participant_status"] == "confirmed" for item in updated_host_guests) == 1
    assert sum(item["participant_status"] == "cancelled" for item in updated_host_guests) == 1
