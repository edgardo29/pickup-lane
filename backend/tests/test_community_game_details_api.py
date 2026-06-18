from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_community_game_detail,
    create_game,
    create_user,
    create_venue,
    run_as_temporary_admin,
)


def test_community_game_detail_create_get_list_and_update(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    detail = create_community_game_detail(client, game["id"])

    get_response = client.get(f"/community-game-details/{detail['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == detail["id"]

    list_response = client.get(f"/community-game-details?game_id={game['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == detail["id"] for item in list_response.json())

    patch_response = run_as_temporary_admin(
        client,
        lambda: client.patch(
            f"/community-game-details/{detail['id']}",
            json={
                "payment_methods_snapshot": [
                    {"type": "zelle", "value": "zelle@example.com"}
                ],
                "payment_instructions_snapshot": "Pay the host after confirmation.",
            },
        ),
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["payment_methods_snapshot"] == [
        {"type": "zelle", "value": "zelle@example.com"}
    ]
    assert (
        patch_response.json()["payment_instructions_snapshot"]
        == "Pay the host after confirmation."
    )


def test_community_game_detail_rejects_official_game(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)

    response = run_as_temporary_admin(
        client,
        lambda: client.post(
            "/community-game-details",
            json={
                "game_id": game["id"],
                "payment_methods_snapshot": [{"type": "venmo", "value": "@host"}],
            },
        ),
    )

    assert response.status_code == 400, response.text
    assert "require a community game" in response.text


def test_community_game_detail_rejects_duplicate_game(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    create_community_game_detail(client, game["id"])

    response = run_as_temporary_admin(
        client,
        lambda: client.post(
            "/community-game-details",
            json={
                "game_id": game["id"],
                "payment_methods_snapshot": [{"type": "cash", "value": "Cash"}],
            },
        ),
    )

    assert response.status_code == 409, response.text
    assert "already has community game details" in response.text


def test_community_game_detail_generic_create_requires_admin(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )

    response = client.post(
        "/community-game-details",
        json={
            "game_id": game["id"],
            "payment_methods_snapshot": [{"type": "venmo", "value": "@host"}],
        },
    )

    assert response.status_code == 401, response.text


def test_community_game_detail_host_upsert_creates_and_updates(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    authenticate_as(host["id"])

    create_response = client.put(
        f"/community-game-details/games/{game['id']}/host-edit",
        json={
            "payment_methods_snapshot": [{"type": "venmo", "value": "@host"}],
            "payment_instructions_snapshot": "Pay after joining.",
        },
    )
    assert create_response.status_code == 200, create_response.text
    detail = create_response.json()
    assert detail["game_id"] == game["id"]
    assert detail["payment_methods_snapshot"] == [{"type": "venmo", "value": "@host"}]

    update_response = client.put(
        f"/community-game-details/games/{game['id']}/host-edit",
        json={
            "payment_methods_snapshot": [
                {"type": "zelle", "value": "zelle@example.com"}
            ],
            "payment_instructions_snapshot": None,
        },
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["id"] == detail["id"]
    assert update_response.json()["payment_methods_snapshot"] == [
        {"type": "zelle", "value": "zelle@example.com"}
    ]
    assert update_response.json()["payment_instructions_snapshot"] is None


def test_community_game_detail_host_upsert_rejects_non_host(client: TestClient):
    host = create_user(client)
    other_user = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    authenticate_as(other_user["id"])

    response = client.put(
        f"/community-game-details/games/{game['id']}/host-edit",
        json={"payment_methods_snapshot": [{"type": "venmo", "value": "@host"}]},
    )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Only the game host can edit this game."


def test_community_game_detail_host_upsert_rejects_request_game_id(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    authenticate_as(host["id"])

    response = client.put(
        f"/community-game-details/games/{game['id']}/host-edit",
        json={
            "game_id": game["id"],
            "payment_methods_snapshot": [{"type": "venmo", "value": "@host"}],
        },
    )

    assert response.status_code == 422, response.text
