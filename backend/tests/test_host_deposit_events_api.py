from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_game,
    create_host_deposit,
    create_host_deposit_event,
    create_payment,
    create_user,
    create_venue,
    set_user_role,
)


def create_host_deposit_event_setup(
    client: TestClient,
) -> tuple[dict, dict, dict, dict, dict, dict]:
    host = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
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
    payment = create_payment(
        client,
        host["id"],
        game_id=game["id"],
        payment_type="host_deposit",
        amount_cents=2500,
        payment_status="succeeded",
    )
    host_deposit = create_host_deposit(
        client,
        game["id"],
        host["id"],
        deposit_status="paid",
        payment_id=payment["id"],
    )
    return host, admin, venue, game, payment, host_deposit


def test_host_deposit_event_create_get_list_and_update_reason(client: TestClient):
    _host, admin, _venue, _game, _payment, host_deposit = (
        create_host_deposit_event_setup(client)
    )
    event = create_host_deposit_event(
        client,
        host_deposit["id"],
        changed_by_user_id=admin["id"],
        change_source="admin",
    )

    get_response = client.get(f"/host-deposit-events/{event['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == event["id"]

    list_response = client.get(
        f"/host-deposit-events?host_deposit_id={host_deposit['id']}"
    )
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == event["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/host-deposit-events/{event['id']}",
        json={"reason": "Corrected CI host deposit event reason."},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["reason"] == "Corrected CI host deposit event reason."


def test_host_deposit_event_reject_no_status_change(client: TestClient):
    _host, _admin, _venue, _game, _payment, host_deposit = (
        create_host_deposit_event_setup(client)
    )

    response = client.post(
        "/host-deposit-events",
        json={
            "host_deposit_id": host_deposit["id"],
            "old_status": "paid",
            "new_status": "paid",
            "change_source": "system",
        },
    )

    assert response.status_code == 400, response.text
    assert "must change status" in response.text


def test_host_deposit_event_reject_forfeited_without_reason(client: TestClient):
    _host, _admin, _venue, _game, _payment, host_deposit = (
        create_host_deposit_event_setup(client)
    )

    response = client.post(
        "/host-deposit-events",
        json={
            "host_deposit_id": host_deposit["id"],
            "old_status": "held",
            "new_status": "forfeited",
            "change_source": "system",
        },
    )

    assert response.status_code == 400, response.text
    assert "require reason" in response.text


def test_host_deposit_event_reject_missing_actor(client: TestClient):
    _host, _admin, _venue, _game, _payment, host_deposit = (
        create_host_deposit_event_setup(client)
    )

    response = client.post(
        "/host-deposit-events",
        json={
            "host_deposit_id": host_deposit["id"],
            "old_status": "payment_pending",
            "new_status": "paid",
            "changed_by_user_id": "00000000-0000-4000-8000-000000000000",
            "change_source": "admin",
        },
    )

    assert response.status_code == 404, response.text
    assert "Changed by user not found" in response.text


def test_host_deposit_event_reject_host_source_from_other_user(
    client: TestClient,
):
    _host, _admin, _venue, _game, _payment, host_deposit = (
        create_host_deposit_event_setup(client)
    )
    other_user = create_user(client)

    response = client.post(
        "/host-deposit-events",
        json={
            "host_deposit_id": host_deposit["id"],
            "old_status": "payment_pending",
            "new_status": "paid",
            "changed_by_user_id": other_user["id"],
            "change_source": "host",
        },
    )

    assert response.status_code == 400, response.text
    assert "host user" in response.text


def test_host_deposit_event_admin_source_requires_admin(client: TestClient):
    host, _admin, _venue, _game, _payment, host_deposit = (
        create_host_deposit_event_setup(client)
    )

    response = client.post(
        "/host-deposit-events",
        json={
            "host_deposit_id": host_deposit["id"],
            "old_status": "payment_pending",
            "new_status": "paid",
            "changed_by_user_id": host["id"],
            "change_source": "admin",
        },
    )

    assert response.status_code == 400, response.text
    assert "admin user" in response.text


def test_host_deposit_event_reject_lifecycle_field_update(client: TestClient):
    _host, admin, _venue, _game, _payment, host_deposit = (
        create_host_deposit_event_setup(client)
    )
    event = create_host_deposit_event(
        client,
        host_deposit["id"],
        changed_by_user_id=admin["id"],
        change_source="admin",
    )

    response = client.patch(
        f"/host-deposit-events/{event['id']}",
        json={"new_status": "held"},
    )

    assert response.status_code == 400, response.text
    assert "cannot be changed" in response.text
