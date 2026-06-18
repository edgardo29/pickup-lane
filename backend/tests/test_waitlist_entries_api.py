from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_game,
    create_user,
    create_venue,
    create_waitlist_entry,
    get_roster_as_admin,
    set_user_role,
)


def test_waitlist_entries_create_get_list_and_update(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    waitlist_entry = create_waitlist_entry(client, user["id"], game["id"])

    authenticate_as(user["id"])
    get_response = client.get(f"/waitlist-entries/{waitlist_entry['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == waitlist_entry["id"]

    list_response = get_roster_as_admin(
        client,
        f"/waitlist-entries?game_id={game['id']}",
    )
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == waitlist_entry["id"] for item in list_response.json())

    authenticate_as(admin["id"])
    patch_response = client.patch(
        f"/waitlist-entries/{waitlist_entry['id']}",
        json={"party_size": 2},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["party_size"] == 2


def test_waitlist_entry_single_read_rejects_non_owner_and_allows_admin(
    client: TestClient,
):
    admin = create_user(client)
    owner = create_user(client)
    other_user = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, owner["id"])
    game = create_game(client, owner["id"], venue)
    waitlist_entry = create_waitlist_entry(client, owner["id"], game["id"])

    authenticate_as(other_user["id"])
    other_response = client.get(f"/waitlist-entries/{waitlist_entry['id']}")
    assert other_response.status_code == 403, other_response.text

    authenticate_as(admin["id"])
    admin_response = client.get(f"/waitlist-entries/{waitlist_entry['id']}")
    assert admin_response.status_code == 200, admin_response.text
    assert admin_response.json()["id"] == waitlist_entry["id"]


def test_waitlist_entries_list_rejects_non_admin_and_allows_admin(
    client: TestClient,
):
    admin = create_user(client)
    user = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    waitlist_entry = create_waitlist_entry(client, user["id"], game["id"])

    authenticate_as(user["id"])
    user_response = client.get(f"/waitlist-entries?game_id={game['id']}")
    assert user_response.status_code == 403, user_response.text

    authenticate_as(admin["id"])
    admin_response = client.get(f"/waitlist-entries?game_id={game['id']}")
    assert admin_response.status_code == 200, admin_response.text
    assert any(item["id"] == waitlist_entry["id"] for item in admin_response.json())


def test_my_waitlist_entries_requires_authentication(client: TestClient):
    response = client.get("/waitlist-entries/me")

    assert response.status_code == 401, response.text


def test_my_waitlist_entries_returns_current_user_safe_rows(client: TestClient):
    user = create_user(client)
    other_user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    my_waitlist_entry = create_waitlist_entry(
        client,
        user["id"],
        game["id"],
        authorized_stripe_payment_method_id="pm_internal_should_not_return",
        authorized_payment_method_brand="visa",
        authorized_payment_method_last4="4242",
        authorized_amount_cents=1300,
    )
    other_waitlist_entry = create_waitlist_entry(
        client,
        other_user["id"],
        game["id"],
        position=2,
    )
    authenticate_as(user["id"])

    response = client.get("/waitlist-entries/me")

    assert response.status_code == 200, response.text
    waitlist_entries = response.json()
    waitlist_entry_ids = {entry["id"] for entry in waitlist_entries}
    assert my_waitlist_entry["id"] in waitlist_entry_ids
    assert other_waitlist_entry["id"] not in waitlist_entry_ids
    assert all(entry["user_id"] == user["id"] for entry in waitlist_entries)
    assert waitlist_entries[0]["authorized_payment_method_brand"] == "visa"
    assert waitlist_entries[0]["authorized_payment_method_last4"] == "4242"
    assert "authorized_stripe_payment_method_id" not in waitlist_entries[0]
    assert "authorized_payment_method_id" not in waitlist_entries[0]


def test_waitlist_entry_scaffold_mutations_reject_non_admin(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    authenticate_as(user["id"])

    create_response = client.post(
        "/waitlist-entries",
        json={
            "game_id": game["id"],
            "user_id": user["id"],
            "party_size": 1,
            "position": 1,
        },
    )
    assert create_response.status_code == 403, create_response.text

    update_response = client.patch(
        "/waitlist-entries/00000000-0000-0000-0000-000000000000",
        json={"party_size": 2},
    )
    assert update_response.status_code == 403, update_response.text


def test_waitlist_entries_reject_duplicate_active_user_and_position(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    first_user = create_user(client)
    second_user = create_user(client)
    venue = create_venue(client, first_user["id"])
    game = create_game(client, first_user["id"], venue)
    create_waitlist_entry(client, first_user["id"], game["id"], position=1)
    authenticate_as(admin["id"])

    duplicate_user_response = client.post(
        "/waitlist-entries",
        json={
            "game_id": game["id"],
            "user_id": first_user["id"],
            "party_size": 1,
            "position": 2,
        },
    )
    assert duplicate_user_response.status_code == 409, duplicate_user_response.text
    assert "already has an active waitlist entry" in duplicate_user_response.text

    duplicate_position_response = client.post(
        "/waitlist-entries",
        json={
            "game_id": game["id"],
            "user_id": second_user["id"],
            "party_size": 1,
            "position": 1,
        },
    )
    assert duplicate_position_response.status_code == 409
    assert "already has an active waitlist entry at this position" in (
        duplicate_position_response.text
    )


def test_waitlist_entries_reject_accepted_without_booking(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    authenticate_as(admin["id"])

    for waitlist_status in ("accepted", "payment_processing", "payment_failed"):
        response = client.post(
            "/waitlist-entries",
            json={
                "game_id": game["id"],
                "user_id": user["id"],
                "party_size": 1,
                "position": 1,
                "waitlist_status": waitlist_status,
            },
        )

        assert response.status_code == 400, response.text
        assert "promoted_booking_id" in response.text


def test_waitlist_entries_accept_promoted_booking(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    authenticate_as(admin["id"])

    response = client.post(
        "/waitlist-entries",
        json={
            "game_id": game["id"],
            "user_id": user["id"],
            "party_size": 1,
            "position": 1,
            "waitlist_status": "accepted",
            "promoted_booking_id": booking["id"],
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["waitlist_status"] == "accepted"
    assert response.json()["promoted_at"] is not None


def test_waitlist_entries_payment_processing_blocks_duplicate_active_user(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    create_waitlist_entry(
        client,
        user["id"],
        game["id"],
        position=1,
        waitlist_status="payment_processing",
        promoted_booking_id=booking["id"],
    )
    authenticate_as(admin["id"])

    response = client.post(
        "/waitlist-entries",
        json={
            "game_id": game["id"],
            "user_id": user["id"],
            "party_size": 1,
            "position": 2,
        },
    )

    assert response.status_code == 409, response.text
    assert "already has an active waitlist entry" in response.text
