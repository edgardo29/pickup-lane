from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_game,
    create_user,
    create_venue,
    set_user_role,
)


def test_admin_can_issue_list_balance_and_reverse_game_credit(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)

    authenticate_as(admin["id"])
    issue_response = client.post(
        "/game-credits/admin/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "official_game_cancelled",
            "source_game_id": game["id"],
            "idempotency_key": "test-credit-issue",
            "note": "Official game cancelled.",
        },
    )

    assert issue_response.status_code == 201, issue_response.text
    credit = issue_response.json()
    assert credit["user_id"] == player["id"]
    assert credit["amount_cents"] == 2500
    assert credit["remaining_cents"] == 2500
    assert credit["credit_status"] == "active"

    balance_response = client.get(f"/game-credits/balance?user_id={player['id']}")
    assert balance_response.status_code == 200, balance_response.text
    assert balance_response.json()["available_credit_cents"] == 2500

    list_response = client.get(f"/game-credits?user_id={player['id']}")
    assert list_response.status_code == 200, list_response.text
    assert len(list_response.json()) == 1

    reverse_response = client.post(
        f"/game-credits/{credit['id']}/admin/reverse",
        json={"idempotency_key": "test-credit-reverse", "note": "Mistake."},
    )
    assert reverse_response.status_code == 200, reverse_response.text
    assert reverse_response.json()["credit_status"] == "reversed"
    assert reverse_response.json()["remaining_cents"] == 0

    balance_after_reverse_response = client.get(
        f"/game-credits/balance?user_id={player['id']}"
    )
    assert balance_after_reverse_response.status_code == 200
    assert balance_after_reverse_response.json()["available_credit_cents"] == 0


def test_regular_user_cannot_issue_game_credit(client: TestClient):
    user = create_user(client)
    player = create_user(client)
    authenticate_as(user["id"])

    response = client.post(
        "/game-credits/admin/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "admin_credit",
        },
    )

    assert response.status_code == 403, response.text


def test_credit_source_must_be_official_game(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(
        client,
        admin["id"],
        venue,
        game_type="community",
        payment_collection_type="external_host",
        host_user_id=admin["id"],
        policy_mode="custom_hosted",
    )

    authenticate_as(admin["id"])
    response = client.post(
        "/game-credits/admin/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "official_game_cancelled",
            "source_game_id": game["id"],
        },
    )

    assert response.status_code == 400, response.text
    assert "official in-app games" in response.text
