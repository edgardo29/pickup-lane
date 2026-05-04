from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.tests.helpers import create_game, create_game_image, create_user, create_venue


def create_game_image_setup(client: TestClient) -> tuple[dict, dict, dict]:
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    return user, venue, game


def test_game_image_create_get_list_and_update_metadata(client: TestClient):
    user, _venue, game = create_game_image_setup(client)
    game_image = create_game_image(
        client,
        game["id"],
        uploaded_by_user_id=user["id"],
        image_role="card",
        is_primary=True,
        sort_order=0,
    )

    get_response = client.get(f"/game-images/{game_image['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == game_image["id"]

    list_by_game_response = client.get(f"/game-images?game_id={game['id']}")
    assert list_by_game_response.status_code == 200, list_by_game_response.text
    assert any(item["id"] == game_image["id"] for item in list_by_game_response.json())

    list_primary_response = client.get(
        f"/game-images?game_id={game['id']}&image_status=active&is_primary=true"
    )
    assert list_primary_response.status_code == 200, list_primary_response.text
    assert any(item["id"] == game_image["id"] for item in list_primary_response.json())

    patch_response = client.patch(
        f"/game-images/{game_image['id']}",
        json={
            "image_role": "gallery",
            "is_primary": False,
            "sort_order": 1,
        },
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["image_role"] == "gallery"
    assert patch_response.json()["is_primary"] is False
    assert patch_response.json()["sort_order"] == 1


def test_game_image_reject_second_active_primary_for_same_game(client: TestClient):
    user, _venue, game = create_game_image_setup(client)
    create_game_image(
        client,
        game["id"],
        uploaded_by_user_id=user["id"],
        image_role="card",
        image_status="active",
        is_primary=True,
        sort_order=0,
    )

    response = client.post(
        "/game-images",
        json={
            "game_id": game["id"],
            "uploaded_by_user_id": user["id"],
            "image_url": "https://example.com/images/second-primary.jpg",
            "image_role": "card",
            "image_status": "active",
            "is_primary": True,
            "sort_order": 0,
        },
    )

    assert response.status_code == 409, response.text
    assert "This game already has an active primary image" in response.text


def test_game_image_allows_gallery_role_primary_image(client: TestClient):
    user, _venue, game = create_game_image_setup(client)

    game_image = create_game_image(
        client,
        game["id"],
        uploaded_by_user_id=user["id"],
        image_role="gallery",
        image_status="active",
        is_primary=True,
    )

    assert game_image["image_role"] == "gallery"
    assert game_image["is_primary"] is True


def test_game_image_allows_new_primary_after_old_primary_hidden(client: TestClient):
    user, _venue, game = create_game_image_setup(client)
    first_primary = create_game_image(
        client,
        game["id"],
        uploaded_by_user_id=user["id"],
        image_role="card",
        image_status="active",
        is_primary=True,
        sort_order=0,
    )

    patch_response = client.patch(
        f"/game-images/{first_primary['id']}",
        json={"image_status": "hidden"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["image_status"] == "hidden"

    second_primary = create_game_image(
        client,
        game["id"],
        uploaded_by_user_id=user["id"],
        image_role="card",
        image_status="active",
        is_primary=True,
        sort_order=0,
    )

    assert second_primary["is_primary"] is True
    assert second_primary["image_status"] == "active"


def test_game_image_allows_new_primary_after_old_primary_soft_deleted(
    client: TestClient,
):
    user, _venue, game = create_game_image_setup(client)
    first_primary = create_game_image(
        client,
        game["id"],
        uploaded_by_user_id=user["id"],
        image_role="card",
        image_status="active",
        is_primary=True,
        sort_order=0,
    )

    patch_response = client.patch(
        f"/game-images/{first_primary['id']}",
        json={"deleted_at": datetime.now(UTC).isoformat()},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["deleted_at"] is not None
    assert patch_response.json()["image_status"] == "removed"
    assert patch_response.json()["is_primary"] is False

    get_deleted_response = client.get(f"/game-images/{first_primary['id']}")
    assert get_deleted_response.status_code == 404, get_deleted_response.text

    list_response = client.get(f"/game-images?game_id={game['id']}")
    assert list_response.status_code == 200, list_response.text
    assert all(item["id"] != first_primary["id"] for item in list_response.json())

    second_primary = create_game_image(
        client,
        game["id"],
        uploaded_by_user_id=user["id"],
        image_role="card",
        image_status="active",
        is_primary=True,
        sort_order=0,
    )

    assert second_primary["is_primary"] is True
    assert second_primary["image_status"] == "active"


def test_game_image_allows_new_primary_after_old_primary_removed(client: TestClient):
    user, _venue, game = create_game_image_setup(client)
    first_primary = create_game_image(
        client,
        game["id"],
        uploaded_by_user_id=user["id"],
        image_role="card",
        image_status="active",
        is_primary=True,
        sort_order=0,
    )

    patch_response = client.patch(
        f"/game-images/{first_primary['id']}",
        json={"image_status": "removed"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["image_status"] == "removed"
    assert patch_response.json()["is_primary"] is False
    assert patch_response.json()["deleted_at"] is not None

    second_primary = create_game_image(
        client,
        game["id"],
        uploaded_by_user_id=user["id"],
        image_role="card",
        image_status="active",
        is_primary=True,
        sort_order=0,
    )

    assert second_primary["is_primary"] is True
    assert second_primary["image_status"] == "active"


def test_game_image_allows_clearing_uploaded_by_user(client: TestClient):
    user, _venue, game = create_game_image_setup(client)
    game_image = create_game_image(
        client,
        game["id"],
        uploaded_by_user_id=user["id"],
    )

    response = client.patch(
        f"/game-images/{game_image['id']}",
        json={"uploaded_by_user_id": None},
    )

    assert response.status_code == 200, response.text
    assert response.json()["uploaded_by_user_id"] is None


def test_game_image_reject_empty_image_url(client: TestClient):
    user, _venue, game = create_game_image_setup(client)

    response = client.post(
        "/game-images",
        json={
            "game_id": game["id"],
            "uploaded_by_user_id": user["id"],
            "image_url": "   ",
            "image_role": "gallery",
            "image_status": "active",
            "is_primary": False,
            "sort_order": 0,
        },
    )

    assert response.status_code == 400, response.text
    assert "image_url must not be empty" in response.text


def test_game_image_reject_invalid_image_role(client: TestClient):
    user, _venue, game = create_game_image_setup(client)

    response = client.post(
        "/game-images",
        json={
            "game_id": game["id"],
            "uploaded_by_user_id": user["id"],
            "image_url": "https://example.com/images/bad-role.jpg",
            "image_role": "thumbnail",
            "image_status": "active",
            "is_primary": False,
            "sort_order": 0,
        },
    )

    assert response.status_code == 400, response.text
    assert "image_role is not supported" in response.text


def test_game_image_reject_invalid_image_status(client: TestClient):
    user, _venue, game = create_game_image_setup(client)

    response = client.post(
        "/game-images",
        json={
            "game_id": game["id"],
            "uploaded_by_user_id": user["id"],
            "image_url": "https://example.com/images/bad-status.jpg",
            "image_role": "gallery",
            "image_status": "pending",
            "is_primary": False,
            "sort_order": 0,
        },
    )

    assert response.status_code == 400, response.text
    assert "image_status is not supported" in response.text


def test_game_image_reject_negative_sort_order(client: TestClient):
    user, _venue, game = create_game_image_setup(client)

    response = client.post(
        "/game-images",
        json={
            "game_id": game["id"],
            "uploaded_by_user_id": user["id"],
            "image_url": "https://example.com/images/bad-sort.jpg",
            "image_role": "gallery",
            "image_status": "active",
            "is_primary": False,
            "sort_order": -1,
        },
    )

    assert response.status_code == 400, response.text
    assert "sort_order must be greater than or equal to 0" in response.text


def test_game_image_reject_missing_game(client: TestClient):
    user = create_user(client)

    response = client.post(
        "/game-images",
        json={
            "game_id": "00000000-0000-4000-8000-000000000000",
            "uploaded_by_user_id": user["id"],
            "image_url": "https://example.com/images/missing-game.jpg",
            "image_role": "gallery",
            "image_status": "active",
            "is_primary": False,
            "sort_order": 0,
        },
    )

    assert response.status_code == 404, response.text
    assert "Game not found" in response.text


def test_game_image_reject_missing_uploaded_by_user(client: TestClient):
    user, _venue, game = create_game_image_setup(client)

    response = client.post(
        "/game-images",
        json={
            "game_id": game["id"],
            "uploaded_by_user_id": "00000000-0000-4000-8000-000000000000",
            "image_url": "https://example.com/images/missing-user.jpg",
            "image_role": "gallery",
            "image_status": "active",
            "is_primary": False,
            "sort_order": 0,
        },
    )

    assert response.status_code == 404, response.text
    assert "Uploaded by user not found" in response.text
