from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from backend.tests.support.api_helpers import create_game, create_venue
from backend.tests.support.factories import create_user
from backend.tests.support.time import local_date_string


def test_browse_game_cards_caps_limit(client: TestClient):
    response = client.get(
        "/games/browse",
        params={
            "starts_on": (datetime.now(UTC) + timedelta(days=7)).date().isoformat(),
            "limit": 500,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["limit"] == 100


def test_browse_game_cards_default_limit_and_route_validation(client: TestClient):
    starts_on = (datetime.now(UTC) + timedelta(days=7)).date().isoformat()

    default_response = client.get(
        "/games/browse",
        params={"starts_on": starts_on},
    )
    rejected_min_response = client.get(
        "/games/browse",
        params={"starts_on": starts_on, "limit": 0},
    )
    invalid_cursor_response = client.get(
        "/games/browse",
        params={"starts_on": starts_on, "cursor": "x" * 2000},
    )
    oversized_cursor_response = client.get(
        "/games/browse",
        params={"starts_on": starts_on, "cursor": "x" * 2001},
    )

    assert default_response.status_code == 200, default_response.text
    assert default_response.json()["limit"] == 40
    assert rejected_min_response.status_code == 422, rejected_min_response.text
    assert invalid_cursor_response.status_code == 400, invalid_cursor_response.text
    assert oversized_cursor_response.status_code == 422, oversized_cursor_response.text


def test_browse_game_cards_invalid_cursor_returns_400(client: TestClient):
    response = client.get(
        "/games/browse",
        params={
            "starts_on": (datetime.now(UTC) + timedelta(days=7)).date().isoformat(),
            "cursor": "not-a-valid-browse-cursor",
        },
    )

    assert response.status_code == 400, response.text
    assert "cursor is invalid" in response.text


def test_browse_game_cards_include_backend_owned_display_location_and_price_labels(
    client: TestClient,
):
    admin = create_user(client)
    community_host = create_user(client)
    venue = create_venue(client, admin["id"], name="Riverfront Field")
    browse_local_start = (
        datetime.now(ZoneInfo("America/Chicago")) + timedelta(days=7)
    ).replace(hour=18, minute=0, second=0, microsecond=0)
    starts_at = browse_local_start.astimezone(UTC)
    official_game = create_game(
        client,
        admin["id"],
        venue,
        game_type="official",
        title="Internal Official Title",
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=1)).isoformat(),
        price_per_player_cents=1200,
    )
    community_game = create_game(
        client,
        community_host["id"],
        venue,
        game_type="community",
        host_user_id=community_host["id"],
        policy_mode="custom_hosted",
        payment_collection_type="external_host",
        title="Neighborhood Kickabout",
        starts_at=(starts_at + timedelta(hours=1)).isoformat(),
        ends_at=(starts_at + timedelta(hours=2)).isoformat(),
        price_per_player_cents=0,
    )

    response = client.get(
        "/games/browse",
        params={"starts_on": local_date_string(starts_at, "America/Chicago")},
    )

    assert response.status_code == 200, response.text
    games_by_id = {game["id"]: game for game in response.json()["games"]}
    assert games_by_id[official_game["id"]]["display_title"] == "Riverfront Field"
    assert games_by_id[official_game["id"]]["location_label"] == "Chicago, IL"
    assert games_by_id[official_game["id"]]["price_label"] == "$12"
    assert (
        games_by_id[community_game["id"]]["display_title"]
        == "Neighborhood Kickabout"
    )
    assert games_by_id[community_game["id"]]["location_label"] == "Chicago, IL"
    assert games_by_id[community_game["id"]]["price_label"] == "Free"
