from fastapi.testclient import TestClient

from backend.tests.helpers import create_game, create_user, create_venue


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
