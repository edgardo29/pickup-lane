from fastapi.testclient import TestClient
from datetime import UTC, datetime, timedelta

from backend.tests.helpers import (
    authenticate_as,
    create_game,
    create_host_publish_fee,
    create_payment,
    create_user,
    create_venue,
    run_as_temporary_admin,
    set_user_role,
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


def test_host_publish_fee_create_get_list_and_update_waiver(client: TestClient):
    host, game = create_community_game_setup(client)
    host_publish_fee = create_host_publish_fee(client, game["id"], host["id"])

    get_response = run_as_temporary_admin(
        client,
        lambda: client.get(f"/host-publish-fees/{host_publish_fee['id']}"),
    )
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == host_publish_fee["id"]

    list_response = run_as_temporary_admin(
        client,
        lambda: client.get(f"/host-publish-fees?host_user_id={host['id']}"),
    )
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == host_publish_fee["id"] for item in list_response.json())

    patch_response = run_as_temporary_admin(
        client,
        lambda: client.patch(
            f"/host-publish-fees/{host_publish_fee['id']}",
            json={
                "fee_status": "waived",
                "waiver_reason": "admin_comp",
                "amount_cents": 0,
            },
        ),
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["fee_status"] == "waived"
    assert patch_response.json()["waiver_reason"] == "admin_comp"
    assert patch_response.json()["paid_at"] is None


def test_host_publish_fee_me_lists_authenticated_host_fees(client: TestClient):
    host, game = create_community_game_setup(client)
    other_host, other_game = create_community_game_setup(client)
    host_publish_fee = create_host_publish_fee(client, game["id"], host["id"])
    other_host_publish_fee = create_host_publish_fee(
        client,
        other_game["id"],
        other_host["id"],
        waiver_reason="admin_comp",
    )
    authenticate_as(host["id"])

    response = client.get("/host-publish-fees/me")

    assert response.status_code == 200, response.text
    ids = {item["id"] for item in response.json()}
    assert host_publish_fee["id"] in ids
    assert other_host_publish_fee["id"] not in ids


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

    response = run_as_temporary_admin(
        client,
        lambda: client.post(
            "/host-publish-fees",
            json={
                "game_id": game["id"],
                "host_user_id": host["id"],
                "amount_cents": 0,
                "fee_status": "waived",
                "waiver_reason": "first_game_free",
            },
        ),
    )

    assert response.status_code == 400, response.text
    assert "require a community game" in response.text


def test_host_publish_fee_rejects_second_first_free_game(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    first_start = (datetime.now(UTC) + timedelta(days=7)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )
    second_start = first_start + timedelta(days=1)
    first_game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        starts_at=first_start.isoformat(),
        ends_at=(first_start + timedelta(hours=1)).isoformat(),
    )
    second_game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        title="Second Community Game",
        starts_at=second_start.isoformat(),
        ends_at=(second_start + timedelta(hours=1)).isoformat(),
    )
    create_host_publish_fee(client, first_game["id"], host["id"])

    response = run_as_temporary_admin(
        client,
        lambda: client.post(
            "/host-publish-fees",
            json={
                "game_id": second_game["id"],
                "host_user_id": host["id"],
                "amount_cents": 0,
                "fee_status": "waived",
                "waiver_reason": "first_game_free",
            },
        ),
    )

    assert response.status_code == 409, response.text
    assert "already used their first free game" in response.text


def test_host_publish_fee_generic_routes_require_admin_permission(
    client: TestClient,
):
    host, game = create_community_game_setup(client)
    host_publish_fee = create_host_publish_fee(client, game["id"], host["id"])
    authenticate_as(host["id"])

    get_response = client.get(f"/host-publish-fees/{host_publish_fee['id']}")
    list_response = client.get(f"/host-publish-fees?host_user_id={host['id']}")
    create_response = client.post(
        "/host-publish-fees",
        json={
            "game_id": game["id"],
            "host_user_id": host["id"],
            "amount_cents": 0,
            "fee_status": "waived",
            "waiver_reason": "admin_comp",
        },
    )
    patch_response = client.patch(
        f"/host-publish-fees/{host_publish_fee['id']}",
        json={"waiver_reason": "admin_comp"},
    )

    assert get_response.status_code == 403, get_response.text
    assert list_response.status_code == 403, list_response.text
    assert create_response.status_code == 403, create_response.text
    assert patch_response.status_code == 403, patch_response.text


def test_host_publish_fee_generic_routes_reject_moderator(client: TestClient):
    host, game = create_community_game_setup(client)
    host_publish_fee = create_host_publish_fee(client, game["id"], host["id"])
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    authenticate_as(moderator["id"])

    get_response = client.get(f"/host-publish-fees/{host_publish_fee['id']}")
    patch_response = client.patch(
        f"/host-publish-fees/{host_publish_fee['id']}",
        json={"waiver_reason": "admin_comp"},
    )

    assert get_response.status_code == 403, get_response.text
    assert patch_response.status_code == 403, patch_response.text
