from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_game,
    create_host_publish_fee,
    create_payment,
    create_user,
    create_venue,
)


def create_community_game_setup(client: TestClient) -> tuple[dict, dict]:
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
    return host, game


def test_host_publish_fee_create_get_list_and_update_failed(client: TestClient):
    host, game = create_community_game_setup(client)
    host_publish_fee = create_host_publish_fee(client, game["id"], host["id"])

    get_response = client.get(f"/host-publish-fees/{host_publish_fee['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == host_publish_fee["id"]

    list_response = client.get(f"/host-publish-fees?host_user_id={host['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == host_publish_fee["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/host-publish-fees/{host_publish_fee['id']}",
        json={
            "fee_status": "failed",
            "waiver_reason": "none",
            "amount_cents": 499,
        },
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["fee_status"] == "failed"
    assert patch_response.json()["failed_at"] is not None


def test_host_publish_fee_supports_paid_publish_payment(client: TestClient):
    host, game = create_community_game_setup(client)
    payment = create_payment(
        client,
        host["id"],
        game_id=game["id"],
        payment_type="community_publish_fee",
        amount_cents=499,
        payment_status="succeeded",
        idempotency_key=f"publish-fee:{game['id']}",
    )
    host_publish_fee = create_host_publish_fee(
        client,
        game["id"],
        host["id"],
        payment_id=payment["id"],
        amount_cents=499,
        fee_status="paid",
        waiver_reason="none",
    )

    assert host_publish_fee["payment_id"] == payment["id"]
    assert host_publish_fee["fee_status"] == "paid"
    assert host_publish_fee["paid_at"] is not None


def test_host_publish_fee_rejects_official_game(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)

    response = client.post(
        "/host-publish-fees",
        json={
            "game_id": game["id"],
            "host_user_id": host["id"],
            "amount_cents": 0,
            "fee_status": "waived",
            "waiver_reason": "first_game_free",
        },
    )

    assert response.status_code == 400, response.text
    assert "require a community game" in response.text


def test_host_publish_fee_rejects_second_first_free_game(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    first_game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    second_game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        title="Second Community Game",
    )
    create_host_publish_fee(client, first_game["id"], host["id"])

    response = client.post(
        "/host-publish-fees",
        json={
            "game_id": second_game["id"],
            "host_user_id": host["id"],
            "amount_cents": 0,
            "fee_status": "waived",
            "waiver_reason": "first_game_free",
        },
    )

    assert response.status_code == 409, response.text
    assert "already used their first free game" in response.text
