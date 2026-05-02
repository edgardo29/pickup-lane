from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_game,
    create_host_deposit,
    create_payment,
    create_user,
    create_venue,
)


def create_community_game_setup(client: TestClient) -> tuple[dict, dict, dict]:
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        policy_mode="custom_hosted",
        host_user_id=host["id"],
        environment_type="outdoor",
        price_per_player_cents=1000,
    )
    return host, venue, game


def create_host_deposit_payment(
    client: TestClient,
    host_id: str,
    game_id: str,
    **overrides: object,
) -> dict:
    payment_overrides = {
        "payment_type": "host_deposit",
        "amount_cents": 2500,
        "payment_status": "succeeded",
    }
    payment_overrides.update(overrides)

    return create_payment(
        client,
        host_id,
        game_id=game_id,
        **payment_overrides,
    )


def test_host_deposits_create_get_list_and_update(client: TestClient):
    host, _venue, game = create_community_game_setup(client)
    payment = create_host_deposit_payment(client, host["id"], game["id"])
    host_deposit = create_host_deposit(
        client,
        game["id"],
        host["id"],
        deposit_status="paid",
        payment_id=payment["id"],
    )

    get_response = client.get(f"/host-deposits/{host_deposit['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == host_deposit["id"]

    list_response = client.get(f"/host-deposits?game_id={game['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == host_deposit["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/host-deposits/{host_deposit['id']}",
        json={"deposit_status": "held"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["deposit_status"] == "held"
    assert patch_response.json()["paid_at"] is not None


def test_host_deposits_reject_official_game(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)

    response = client.post(
        "/host-deposits",
        json={
            "game_id": game["id"],
            "host_user_id": user["id"],
            "required_amount_cents": 2500,
            "currency": "USD",
            "deposit_status": "required",
        },
    )

    assert response.status_code == 400, response.text
    assert "community games" in response.text


def test_host_deposits_reject_duplicate_game(client: TestClient):
    host, _venue, game = create_community_game_setup(client)

    create_host_deposit(client, game["id"], host["id"])
    response = client.post(
        "/host-deposits",
        json={
            "game_id": game["id"],
            "host_user_id": host["id"],
            "required_amount_cents": 2500,
            "currency": "USD",
            "deposit_status": "required",
        },
    )

    assert response.status_code == 409, response.text
    assert "already has a host deposit" in response.text


def test_host_deposits_reject_mismatched_payment_payer(client: TestClient):
    host, _venue, game = create_community_game_setup(client)
    other_user = create_user(client)
    payment = create_host_deposit_payment(client, other_user["id"], game["id"])

    response = client.post(
        "/host-deposits",
        json={
            "game_id": game["id"],
            "host_user_id": host["id"],
            "required_amount_cents": 2500,
            "currency": "USD",
            "deposit_status": "paid",
            "payment_id": payment["id"],
        },
    )

    assert response.status_code == 400, response.text
    assert "host_user_id as payer_user_id" in response.text


def test_host_deposits_reject_paid_with_unsucceeded_payment(client: TestClient):
    host, _venue, game = create_community_game_setup(client)
    payment = create_host_deposit_payment(
        client,
        host["id"],
        game["id"],
        payment_status="processing",
    )

    response = client.post(
        "/host-deposits",
        json={
            "game_id": game["id"],
            "host_user_id": host["id"],
            "required_amount_cents": 2500,
            "currency": "USD",
            "deposit_status": "paid",
            "payment_id": payment["id"],
        },
    )

    assert response.status_code == 400, response.text
    assert "succeeded payment" in response.text


def test_host_deposits_reject_update_after_terminal_status(client: TestClient):
    host, _venue, game = create_community_game_setup(client)
    payment = create_host_deposit_payment(client, host["id"], game["id"])
    host_deposit = create_host_deposit(
        client,
        game["id"],
        host["id"],
        deposit_status="paid",
        payment_id=payment["id"],
    )

    release_response = client.patch(
        f"/host-deposits/{host_deposit['id']}",
        json={"deposit_status": "released"},
    )
    assert release_response.status_code == 200, release_response.text

    response = client.patch(
        f"/host-deposits/{host_deposit['id']}",
        json={"required_amount_cents": 2000},
    )

    assert response.status_code == 400, response.text
    assert "cannot be updated" in response.text
