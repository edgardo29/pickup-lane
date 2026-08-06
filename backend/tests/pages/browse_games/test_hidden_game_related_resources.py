from fastapi.testclient import TestClient

from backend.tests.support.assertions import assert_private_no_store
from backend.tests.support.auth import authenticate_as, authenticate_optional_as
from backend.tests.support.api_helpers import create_game, create_venue
from backend.tests.support.factories import create_user


def _create_community_game_detail_as_host(
    client: TestClient,
    *,
    host_user_id: str,
    game_id: str,
) -> dict[str, object]:
    authenticate_as(host_user_id)
    response = client.put(
        f"/community-game-details/games/{game_id}/host-edit",
        json={
            "payment_methods_snapshot": [{"type": "venmo", "value": "@host"}],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_hidden_community_game_detail_list_by_game_id_allows_host_with_private_cache(
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
        public_visibility_status="hidden",
    )
    detail = _create_community_game_detail_as_host(
        client,
        host_user_id=host["id"],
        game_id=game["id"],
    )

    authenticate_optional_as(host["id"])
    response = client.get(f"/community-game-details?game_id={game['id']}")

    assert response.status_code == 200, response.text
    assert_private_no_store(response)
    assert [item["id"] for item in response.json()] == [detail["id"]]


def test_hidden_community_detail_list_by_game_id_returns_404_for_unauthorized_users(
    client: TestClient,
):
    host = create_user(client)
    unrelated_user = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        public_visibility_status="hidden",
    )
    _create_community_game_detail_as_host(
        client,
        host_user_id=host["id"],
        game_id=game["id"],
    )

    anonymous_response = client.get(f"/community-game-details?game_id={game['id']}")
    authenticate_optional_as(unrelated_user["id"])
    unrelated_response = client.get(f"/community-game-details?game_id={game['id']}")

    assert anonymous_response.status_code == 404, anonymous_response.text
    assert unrelated_response.status_code == 404, unrelated_response.text
