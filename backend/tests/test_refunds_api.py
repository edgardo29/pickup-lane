from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_game,
    create_game_participant,
    create_host_publish_fee,
    create_payment,
    create_refund,
    create_user,
    create_venue,
    set_user_role,
    unique_suffix,
)


def create_money_admin(client: TestClient) -> dict:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    return admin


def create_paid_booking_setup(client: TestClient) -> tuple[dict, dict, dict, dict, dict]:
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    payment = create_payment(
        client,
        user["id"],
        booking_id=booking["id"],
        payment_status="succeeded",
    )
    return user, venue, game, booking, payment


def test_refunds_create_get_list_and_update(client: TestClient):
    user, _venue, _game, booking, payment = create_paid_booking_setup(client)
    admin = create_money_admin(client)
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        requested_by_user_id=user["id"],
    )

    authenticate_as(user["id"])
    get_response = client.get(f"/refunds/{refund['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == refund["id"]

    list_response = client.get(f"/refunds?payment_id={payment['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == refund["id"] for item in list_response.json())

    authenticate_as(admin["id"])
    patch_response = client.patch(
        f"/refunds/{refund['id']}",
        json={"refund_status": "approved", "approved_by_user_id": user["id"]},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["refund_status"] == "approved"
    assert patch_response.json()["approved_at"] is not None

    audit_response = client.get(f"/admin/actions?target_refund_id={refund['id']}")
    assert audit_response.status_code == 200, audit_response.text
    actions_by_type = {
        action["action_type"]: action for action in audit_response.json()
    }
    assert actions_by_type["create_refund"]["target_user_id"] == user["id"]
    assert actions_by_type["create_refund"]["target_booking_id"] == booking["id"]
    assert actions_by_type["create_refund"]["target_payment_id"] == payment["id"]
    assert actions_by_type["create_refund"]["target_refund_id"] == refund["id"]
    assert actions_by_type["create_refund"]["metadata"] == {
        "source": "refund_route_create",
        "refund_status": "pending",
        "refund_reason": "player_cancelled",
        "amount_cents": 500,
        "currency": "USD",
        "host_publish_fee_id": None,
        "origin_workflow": "direct_admin_refund",
    }
    assert actions_by_type["update_refund"]["target_user_id"] == user["id"]
    assert actions_by_type["update_refund"]["target_booking_id"] == booking["id"]
    assert actions_by_type["update_refund"]["target_payment_id"] == payment["id"]
    assert actions_by_type["update_refund"]["target_refund_id"] == refund["id"]
    assert actions_by_type["update_refund"]["metadata"] == {
        "source": "refund_route_update",
        "refund_status": "approved",
        "refund_reason": "player_cancelled",
        "amount_cents": 500,
        "currency": "USD",
        "host_publish_fee_id": None,
        "origin_workflow": "direct_admin_refund",
        "old_refund_status": "pending",
        "new_refund_status": "approved",
        "before": {
            "refund_status": "pending",
            "refund_reason": "player_cancelled",
            "amount_cents": 500,
            "currency": "USD",
        },
        "after": {
            "refund_status": "approved",
            "refund_reason": "player_cancelled",
            "amount_cents": 500,
            "currency": "USD",
        },
    }


def test_refunds_can_scope_to_participant(client: TestClient):
    user, _venue, game, booking, payment = create_paid_booking_setup(client)
    participant = create_game_participant(
        client,
        user["id"],
        game["id"],
        booking_id=booking["id"],
    )

    refund = create_refund(
        client,
        payment["id"],
        participant_id=participant["id"],
        amount_cents=300,
    )

    assert refund["participant_id"] == participant["id"]
    assert refund["booking_id"] is None


def test_refunds_reject_host_publish_fee_creation_without_financial_outcome(
    client: TestClient,
):
    host = create_user(client)
    admin = create_money_admin(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    payment = create_payment(
        client,
        host["id"],
        game_id=game["id"],
        payment_type="community_publish_fee",
        amount_cents=499,
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
        idempotency_key=f"publish-fee-payment-{unique_suffix()}",
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

    authenticate_as(admin["id"])
    response = client.post(
        "/refunds",
        json={
            "payment_id": payment["id"],
            "host_publish_fee_id": host_publish_fee["id"],
            "provider_refund_id": f"re_{unique_suffix()}",
            "amount_cents": 499,
            "currency": "USD",
            "refund_reason": "publish_fee_refund",
            "refund_status": "processing",
        },
    )

    assert response.status_code == 400, response.text
    assert "admin financial outcomes" in response.text


def test_refunds_reject_host_publish_fee_update_without_financial_outcome(
    client: TestClient,
):
    user, _venue, _game, booking, booking_payment = create_paid_booking_setup(client)
    refund = create_refund(
        client,
        booking_payment["id"],
        booking_id=booking["id"],
        amount_cents=booking_payment["amount_cents"],
    )
    admin = create_money_admin(client)
    venue = create_venue(client, user["id"])
    community_game = create_game(
        client,
        user["id"],
        venue,
        game_type="community",
        host_user_id=user["id"],
        policy_mode="custom_hosted",
    )
    publish_payment = create_payment(
        client,
        user["id"],
        game_id=community_game["id"],
        payment_type="community_publish_fee",
        amount_cents=499,
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
        idempotency_key=f"publish-fee-payment-{unique_suffix()}",
    )
    host_publish_fee = create_host_publish_fee(
        client,
        community_game["id"],
        user["id"],
        payment_id=publish_payment["id"],
        amount_cents=499,
        fee_status="paid",
        waiver_reason="none",
    )

    authenticate_as(admin["id"])
    response = client.patch(
        f"/refunds/{refund['id']}",
        json={
            "payment_id": publish_payment["id"],
            "booking_id": None,
            "host_publish_fee_id": host_publish_fee["id"],
            "refund_reason": "publish_fee_refund",
        },
    )

    assert response.status_code == 400, response.text
    assert "admin financial outcomes" in response.text


def test_refunds_reject_unsucceeded_payment(client: TestClient):
    user = create_user(client)
    admin = create_money_admin(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    payment = create_payment(client, user["id"], booking_id=booking["id"])

    authenticate_as(admin["id"])
    response = client.post(
        "/refunds",
        json={
            "payment_id": payment["id"],
            "booking_id": booking["id"],
            "provider_refund_id": f"re_{unique_suffix()}",
            "amount_cents": 500,
            "currency": "USD",
            "refund_reason": "player_cancelled",
            "refund_status": "pending",
        },
    )

    assert response.status_code == 400, response.text
    assert "payment that has succeeded" in response.text


def test_refunds_reject_duplicate_provider_refund_id(client: TestClient):
    _user, _venue, _game, booking, payment = create_paid_booking_setup(client)
    admin = create_money_admin(client)
    provider_refund_id = f"re_{unique_suffix()}"

    create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        provider_refund_id=provider_refund_id,
    )
    authenticate_as(admin["id"])
    response = client.post(
        "/refunds",
        json={
            "payment_id": payment["id"],
            "booking_id": booking["id"],
            "provider_refund_id": provider_refund_id,
            "amount_cents": 100,
            "currency": "USD",
            "refund_reason": "player_cancelled",
            "refund_status": "pending",
        },
    )

    assert response.status_code == 409, response.text
    assert "provider_refund_id already exists" in response.text


def test_refunds_reject_amount_over_remaining_payment(client: TestClient):
    _user, _venue, _game, booking, payment = create_paid_booking_setup(client)
    admin = create_money_admin(client)

    create_refund(client, payment["id"], booking_id=booking["id"], amount_cents=900)
    authenticate_as(admin["id"])
    response = client.post(
        "/refunds",
        json={
            "payment_id": payment["id"],
            "booking_id": booking["id"],
            "provider_refund_id": f"re_{unique_suffix()}",
            "amount_cents": 500,
            "currency": "USD",
            "refund_reason": "player_cancelled",
            "refund_status": "pending",
        },
    )

    assert response.status_code == 400, response.text
    assert "remaining refundable payment amount" in response.text


def test_refunds_reject_updates_after_terminal_status(client: TestClient):
    _user, _venue, _game, booking, payment = create_paid_booking_setup(client)
    admin = create_money_admin(client)
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        refund_status="succeeded",
        amount_cents=300,
    )

    authenticate_as(admin["id"])
    response = client.patch(
        f"/refunds/{refund['id']}",
        json={"amount_cents": 200},
    )

    assert response.status_code == 400, response.text
    assert "cannot be updated" in response.text


def test_refunds_reject_regular_user_mutation(client: TestClient):
    user, _venue, _game, booking, payment = create_paid_booking_setup(client)

    authenticate_as(user["id"])
    response = client.post(
        "/refunds",
        json={
            "payment_id": payment["id"],
            "booking_id": booking["id"],
            "provider_refund_id": f"re_{unique_suffix()}",
            "amount_cents": 500,
            "currency": "USD",
            "refund_reason": "player_cancelled",
            "refund_status": "pending",
        },
    )

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


def test_refunds_reject_regular_user_reading_other_user_refund(client: TestClient):
    user, _venue, _game, booking, payment = create_paid_booking_setup(client)
    other_user = create_user(client)
    other_booking = create_booking(client, other_user["id"], _game["id"])
    other_payment = create_payment(
        client,
        other_user["id"],
        booking_id=other_booking["id"],
        payment_status="succeeded",
    )
    create_refund(client, payment["id"], booking_id=booking["id"])
    other_refund = create_refund(
        client,
        other_payment["id"],
        booking_id=other_booking["id"],
    )

    authenticate_as(user["id"])
    get_response = client.get(f"/refunds/{other_refund['id']}")
    list_response = client.get(f"/refunds?payment_id={other_payment['id']}")

    assert get_response.status_code == 403, get_response.text
    assert "Admin access required" in get_response.text
    assert list_response.status_code == 200, list_response.text
    assert list_response.json() == []
