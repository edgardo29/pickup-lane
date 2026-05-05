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
