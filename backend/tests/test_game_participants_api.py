from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_game,
    create_game_participant,
    create_user,
    create_venue,
    get_roster_as_admin,
    set_user_role,
)


def test_my_game_participants_requires_authentication(client: TestClient):
    response = client.get("/game-participants/me")

    assert response.status_code == 401, response.text


def test_my_game_participants_returns_current_user_public_safe_rows(
    client: TestClient,
):
    user = create_user(client)
    other_user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    my_participant = create_game_participant(
        client,
        user["id"],
        game["id"],
        booking["id"],
        attendance_notes="Private attendance note.",
    )
    create_game_participant(client, other_user["id"], game["id"])
    authenticate_as(user["id"])

    response = client.get("/game-participants/me")

    assert response.status_code == 200, response.text
    participants = response.json()
    assert [participant["id"] for participant in participants] == [my_participant["id"]]
    assert participants[0]["user_id"] == user["id"]
    assert "attendance_notes" not in participants[0]
    assert "price_cents" not in participants[0]


def test_game_participants_create_get_list_and_update(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    participant = create_game_participant(
        client, user["id"], game["id"], booking["id"]
    )

    authenticate_as(user["id"])
    get_response = client.get(f"/game-participants/{participant['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == participant["id"]

    list_response = get_roster_as_admin(
        client,
        f"/game-participants?game_id={game['id']}",
    )
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == participant["id"] for item in list_response.json())

    authenticate_as(admin["id"])
    patch_response = client.patch(
        f"/game-participants/{participant['id']}",
        json={"attendance_status": "attended", "marked_attendance_by_user_id": user["id"]},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["attendance_status"] == "attended"
    assert patch_response.json()["attendance_decided_at"] is not None


def test_game_participant_single_read_rejects_non_owner_and_allows_admin(
    client: TestClient,
):
    admin = create_user(client)
    owner = create_user(client)
    other_user = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, owner["id"])
    game = create_game(client, owner["id"], venue)
    booking = create_booking(client, owner["id"], game["id"])
    participant = create_game_participant(
        client,
        owner["id"],
        game["id"],
        booking["id"],
    )

    authenticate_as(other_user["id"])
    other_response = client.get(f"/game-participants/{participant['id']}")
    assert other_response.status_code == 403, other_response.text

    authenticate_as(admin["id"])
    admin_response = client.get(f"/game-participants/{participant['id']}")
    assert admin_response.status_code == 200, admin_response.text
    assert admin_response.json()["id"] == participant["id"]


def test_game_participants_list_rejects_non_admin_and_allows_admin(
    client: TestClient,
):
    admin = create_user(client)
    user = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    participant = create_game_participant(
        client,
        user["id"],
        game["id"],
        booking["id"],
    )

    authenticate_as(user["id"])
    user_response = client.get(f"/game-participants?game_id={game['id']}")
    assert user_response.status_code == 403, user_response.text

    authenticate_as(admin["id"])
    admin_response = client.get(f"/game-participants?game_id={game['id']}")
    assert admin_response.status_code == 200, admin_response.text
    assert any(item["id"] == participant["id"] for item in admin_response.json())


def test_game_participant_scaffold_mutations_reject_non_admin(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    authenticate_as(user["id"])

    create_response = client.post(
        "/game-participants",
        json={
            "game_id": game["id"],
            "participant_type": "registered_user",
            "user_id": user["id"],
            "display_name_snapshot": "Test User",
            "participant_status": "confirmed",
            "attendance_status": "unknown",
            "cancellation_type": "none",
            "price_cents": 1200,
            "currency": "USD",
            "roster_order": 1,
        },
    )
    assert create_response.status_code == 403, create_response.text

    update_response = client.patch(
        "/game-participants/00000000-0000-0000-0000-000000000000",
        json={"attendance_status": "attended"},
    )
    assert update_response.status_code == 403, update_response.text


def test_game_participants_reject_guest_without_guest_name(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    authenticate_as(admin["id"])

    response = client.post(
        "/game-participants",
        json={
            "game_id": game["id"],
            "participant_type": "guest",
            "display_name_snapshot": "Guest Player",
            "participant_status": "pending_payment",
            "attendance_status": "unknown",
            "cancellation_type": "none",
            "price_cents": 1200,
            "currency": "USD",
        },
    )

    assert response.status_code == 400, response.text
    assert "guest_name" in response.text
