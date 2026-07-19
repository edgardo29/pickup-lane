from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.models import Game, VenueImage
from backend.tests.helpers import (
    authenticate_as,
    create_game,
    create_user,
    create_venue,
    set_user_account_status,
    set_user_role,
)


def create_active_primary_venue_image(venue_id: str, uploaded_by_user_id: str) -> None:
    now = datetime.now(UTC)
    image_id = uuid4()

    with SessionLocal() as db:
        db.add(
            VenueImage(
                id=image_id,
                venue_id=UUID(venue_id),
                uploaded_by_user_id=UUID(uploaded_by_user_id),
                storage_provider="r2",
                storage_object_key=f"venues/{venue_id}/primary-{image_id}.jpg",
                storage_bucket="pickup-lane-dev-media",
                storage_account_id="test-r2-account",
                content_type="image/jpeg",
                size_bytes=1200,
                etag=f"etag-{image_id}",
                image_role="card",
                image_status="active",
                is_primary=True,
                sort_order=0,
                alt_text="Primary venue photo",
                caption="Primary venue photo",
                upload_requested_at=now,
                upload_completed_at=now,
            )
        )
        db.commit()


def set_game_host(game_id: str, host_user_id: str) -> None:
    with SessionLocal() as db:
        game = db.get(Game, UUID(game_id))
        assert game is not None
        game.host_user_id = UUID(host_user_id)
        db.commit()


def flatten_action_center_items(body: dict) -> list[dict]:
    return [
        item
        for section in body["sections"]
        for item in section["items"]
    ]


def test_action_center_lists_official_games_missing_host(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    create_active_primary_venue_image(venue["id"], admin["id"])

    authenticate_as(admin["id"])
    response = client.get("/admin/action-center")

    assert response.status_code == 200, response.text
    body = response.json()
    items = flatten_action_center_items(body)
    assert body["total_count"] == 1
    assert body["sections"][0]["section_key"] == "official_games"
    assert items[0]["item_id"] == f"official_game_missing_host:{game['id']}"
    assert items[0]["item_type"] == "official_game_missing_host"
    assert items[0]["entity_type"] == "game"
    assert items[0]["entity_id"] == game["id"]
    assert items[0]["entity_label"] == game["title"]
    assert items[0]["action_label"] == "Assign host"
    assert items[0]["action_path"] == f"/admin/official-games/{game['id']}"


def test_action_center_missing_host_item_disappears_when_host_exists(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    create_active_primary_venue_image(venue["id"], admin["id"])
    set_game_host(game["id"], admin["id"])

    authenticate_as(admin["id"])
    response = client.get("/admin/action-center")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_count"] == 0
    assert body["sections"] == []


def test_action_center_lists_and_clears_missing_primary_venue_photo(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    set_game_host(game["id"], admin["id"])

    authenticate_as(admin["id"])
    response = client.get("/admin/action-center")

    assert response.status_code == 200, response.text
    body = response.json()
    items = flatten_action_center_items(body)
    assert body["total_count"] == 1
    assert items[0]["item_id"] == (
        f"official_game_missing_primary_venue_photo:{game['id']}"
    )
    assert items[0]["item_type"] == "official_game_missing_primary_venue_photo"
    assert items[0]["related_entity_type"] == "venue"
    assert items[0]["related_entity_id"] == venue["id"]
    assert items[0]["related_entity_label"] == venue["name"]
    assert items[0]["action_label"] == "Add venue photo"

    create_active_primary_venue_image(venue["id"], admin["id"])
    cleared_response = client.get("/admin/action-center")

    assert cleared_response.status_code == 200, cleared_response.text
    assert cleared_response.json()["total_count"] == 0
    assert cleared_response.json()["sections"] == []


def test_action_center_rejects_regular_user(client: TestClient):
    user = create_user(client)

    authenticate_as(user["id"])
    response = client.get("/admin/action-center")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


def test_action_center_rejects_suspended_admin(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    set_user_account_status(admin["id"], "suspended")

    authenticate_as(admin["id"])
    response = client.get("/admin/action-center")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text
