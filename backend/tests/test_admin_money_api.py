from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import AdminAction, Notification, Payment, Refund, SupportFlag
from backend.services.game_credit_service import reserve_game_credits
from backend.services.stripe_service import StripeRefundResult
from backend.services.support_flag_service import create_support_flag
from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_game,
    create_payment,
    create_refund,
    create_user,
    create_user_payment_method,
    create_venue,
    set_user_role,
    unique_suffix,
)


def issue_admin_money_detail_credit(
    client: TestClient,
    *,
    admin_id: str,
    user_id: str,
    game_id: str,
    booking_id: str,
    payment_id: str,
    amount_cents: int,
) -> dict:
    authenticate_as(admin_id)
    response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": user_id,
            "amount_cents": amount_cents,
            "credit_reason": "admin_credit",
            "source_game_id": game_id,
            "source_booking_id": booking_id,
            "source_payment_id": payment_id,
            "idempotency_key": f"admin-money-detail-credit-{unique_suffix()}",
            "note": "Admin money detail route coverage.",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def test_admin_can_list_money_payments_by_user_and_status(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    other_player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    other_booking = create_booking(client, other_player["id"], game["id"])
    succeeded_payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    failed_payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="failed",
        failure_code="card_declined",
        failure_message="The card was declined.",
    )
    other_payment = create_payment(
        client,
        other_player["id"],
        booking_id=other_booking["id"],
        amount_cents=other_booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )

    authenticate_as(admin["id"])
    response = client.get(
        f"/admin/money/payments?user_id={player['id']}&payment_status=succeeded"
    )
    booking_response = client.get(
        f"/admin/money/payments?booking_id={booking['id']}&payment_status=all"
    )
    game_response = client.get(
        f"/admin/money/payments?game_id={game['id']}&payment_status=succeeded"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert {item["id"] for item in body} == {succeeded_payment["id"]}
    row = body[0]
    assert row["payer_user_id"] == player["id"]
    assert row["payment_status"] == "succeeded"
    assert set(row) == {
        "id",
        "payer_user_id",
        "booking_id",
        "game_id",
        "payment_type",
        "provider",
        "amount_cents",
        "currency",
        "payment_status",
        "paid_at",
        "failure_code",
        "created_at",
        "updated_at",
    }

    assert booking_response.status_code == 200, booking_response.text
    booking_ids = {item["id"] for item in booking_response.json()}
    assert succeeded_payment["id"] in booking_ids
    assert failed_payment["id"] in booking_ids
    assert other_payment["id"] not in booking_ids

    assert game_response.status_code == 200, game_response.text
    game_payment_ids = {item["id"] for item in game_response.json()}
    assert game_payment_ids == {succeeded_payment["id"], other_payment["id"]}


def test_admin_money_payment_list_rejects_bad_status(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get("/admin/money/payments?payment_status=settled")

    assert response.status_code == 400, response.text


def test_moderator_cannot_list_admin_money_payments(client: TestClient):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")

    authenticate_as(moderator["id"])
    response = client.get("/admin/money/payments")

    assert response.status_code == 403, response.text


def test_admin_can_list_money_refunds_by_user_status_and_context(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    other_player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    other_booking = create_booking(client, other_player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    other_payment = create_payment(
        client,
        other_player["id"],
        booking_id=other_booking["id"],
        amount_cents=other_booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    failed_refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=500,
        refund_status="failed",
    )
    processing_refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=600,
        refund_status="processing",
    )
    other_refund = create_refund(
        client,
        other_payment["id"],
        booking_id=other_booking["id"],
        amount_cents=500,
        refund_status="failed",
    )

    authenticate_as(admin["id"])
    response = client.get(
        f"/admin/money/refunds?user_id={player['id']}&refund_status=failed"
    )
    booking_response = client.get(
        f"/admin/money/refunds?booking_id={booking['id']}&refund_status=all"
    )
    game_response = client.get(
        f"/admin/money/refunds?game_id={game['id']}&refund_status=failed"
    )
    payment_response = client.get(
        f"/admin/money/refunds?payment_id={payment['id']}&refund_status=all"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert {item["id"] for item in body} == {failed_refund["id"]}
    row = body[0]
    assert row["payment_id"] == payment["id"]
    assert row["booking_id"] == booking["id"]
    assert row["refund_status"] == "failed"
    assert set(row) == {
        "id",
        "payment_id",
        "booking_id",
        "participant_id",
        "amount_cents",
        "currency",
        "refund_reason",
        "refund_status",
        "requested_by_user_id",
        "approved_by_user_id",
        "requested_at",
        "approved_at",
        "refunded_at",
        "created_at",
        "updated_at",
    }

    assert booking_response.status_code == 200, booking_response.text
    booking_refund_ids = {item["id"] for item in booking_response.json()}
    assert failed_refund["id"] in booking_refund_ids
    assert processing_refund["id"] in booking_refund_ids
    assert other_refund["id"] not in booking_refund_ids

    assert game_response.status_code == 200, game_response.text
    game_refund_ids = {item["id"] for item in game_response.json()}
    assert game_refund_ids == {failed_refund["id"], other_refund["id"]}

    assert payment_response.status_code == 200, payment_response.text
    payment_refund_ids = {item["id"] for item in payment_response.json()}
    assert payment_refund_ids == {failed_refund["id"], processing_refund["id"]}


def test_admin_money_refund_list_rejects_bad_status(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get("/admin/money/refunds?refund_status=settled")

    assert response.status_code == 400, response.text


def test_moderator_cannot_list_admin_money_refunds(client: TestClient):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")

    authenticate_as(moderator["id"])
    response = client.get("/admin/money/refunds")

    assert response.status_code == 403, response.text


def test_admin_can_get_payment_detail_support_context(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    other_player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    other_booking = create_booking(client, other_player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=500,
        refund_status="processing",
    )
    other_payment = create_payment(
        client,
        other_player["id"],
        booking_id=other_booking["id"],
        amount_cents=other_booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    other_refund = create_refund(
        client,
        other_payment["id"],
        booking_id=other_booking["id"],
        amount_cents=500,
        refund_status="processing",
    )
    credit = issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        booking_id=booking["id"],
        payment_id=payment["id"],
        amount_cents=700,
    )
    other_credit = issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=other_player["id"],
        game_id=game["id"],
        booking_id=other_booking["id"],
        payment_id=other_payment["id"],
        amount_cents=600,
    )

    with SessionLocal() as db:
        usages = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=300,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(payment["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"admin-money-detail:{booking['id']}",
        )
        usage_id = str(usages[0].id)
        db.commit()

    with SessionLocal() as db:
        support_flag = create_support_flag(
            db,
            flag_type="refund_follow_up_required",
            source="stripe",
            title="Refund still processing",
            summary="Payment refund needs staff follow-up before support can close it.",
            severity="urgent",
            target_user_id=UUID(player["id"]),
            target_game_id=UUID(game["id"]),
            target_booking_id=UUID(booking["id"]),
            target_payment_id=UUID(payment["id"]),
            target_refund_id=UUID(refund["id"]),
            idempotency_key=f"admin-money-detail-flag-{payment['id']}",
        )
        support_flag_id = str(support_flag.id)
        official_cancel_flag = create_support_flag(
            db,
            flag_type="official_cancel_partial_failure",
            source="official_game",
            title="Official cancellation follow-up",
            summary="This flag stays in the official cancellation workflow.",
            severity="urgent",
            target_game_id=UUID(game["id"]),
            target_booking_id=UUID(booking["id"]),
            idempotency_key=f"admin-money-detail-official-cancel-{booking['id']}",
        )
        official_cancel_flag_id = str(official_cancel_flag.id)

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/payments/{payment['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["payment"]["id"] == payment["id"]
    assert body["payment"]["booking_id"] == booking["id"]
    assert body["payment"]["payment_status"] == "succeeded"
    assert body["payment"]["provider_charge_id"] == payment["provider_charge_id"]
    assert "idempotency_key" not in body["payment"]
    assert "metadata" not in body["payment"]
    assert body["booking"]["id"] == booking["id"]
    assert body["booking"]["payment_status"] == "paid"
    assert body["game"]["id"] == game["id"]
    assert body["game"]["game_type"] == "official"
    assert {item["id"] for item in body["refunds"]} == {refund["id"]}
    assert other_refund["id"] not in {item["id"] for item in body["refunds"]}
    assert credit["id"] in {item["id"] for item in body["credit_grants"]}
    assert other_credit["id"] not in {
        item["id"] for item in body["credit_grants"]
    }
    assert usage_id in {item["id"] for item in body["credit_usages"]}
    assert support_flag_id in {item["id"] for item in body["support_flags"]}
    assert official_cancel_flag_id not in {
        item["id"] for item in body["support_flags"]
    }
    assert any(
        action["action_type"] == "create_payment"
        and action["target_payment_id"] == payment["id"]
        for action in body["audit_actions"]
    )
    assert any(
        action["action_type"] == "issue_credit"
        and action["target_game_credit_id"] == credit["id"]
        for action in body["audit_actions"]
    )
    assert all("idempotency_key" not in action for action in body["audit_actions"])


def test_moderator_cannot_get_payment_detail(client: TestClient):
    moderator = create_user(client)
    player = create_user(client)
    set_user_role(moderator["id"], "moderator")
    venue = create_venue(client, player["id"])
    game = create_game(client, player["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(client, player["id"], booking_id=booking["id"])

    authenticate_as(moderator["id"])
    response = client.get(f"/admin/money/payments/{payment['id']}")

    assert response.status_code == 403, response.text


def test_admin_payment_detail_missing_payment_returns_404(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get(
        "/admin/money/payments/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404, response.text


def test_admin_can_get_refund_detail_support_context(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    other_player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    other_booking = create_booking(client, other_player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=500,
        refund_status="processing",
    )
    other_payment = create_payment(
        client,
        other_player["id"],
        booking_id=other_booking["id"],
        amount_cents=other_booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    other_refund = create_refund(
        client,
        other_payment["id"],
        booking_id=other_booking["id"],
        amount_cents=500,
        refund_status="processing",
    )
    credit = issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        booking_id=booking["id"],
        payment_id=payment["id"],
        amount_cents=700,
    )
    other_credit = issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=other_player["id"],
        game_id=game["id"],
        booking_id=other_booking["id"],
        payment_id=other_payment["id"],
        amount_cents=600,
    )

    with SessionLocal() as db:
        usages = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=300,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(payment["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"admin-money-refund-detail:{booking['id']}",
        )
        usage_id = str(usages[0].id)
        other_usages = reserve_game_credits(
            db,
            UUID(other_player["id"]),
            amount_cents=300,
            booking_id=UUID(other_booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(other_payment["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"admin-money-refund-detail:{other_booking['id']}",
        )
        other_usage_id = str(other_usages[0].id)
        db.commit()

    with SessionLocal() as db:
        support_flag = create_support_flag(
            db,
            flag_type="refund_follow_up_required",
            source="stripe",
            title="Refund still processing",
            summary="Refund needs staff follow-up before support can close it.",
            severity="urgent",
            target_user_id=UUID(player["id"]),
            target_game_id=UUID(game["id"]),
            target_booking_id=UUID(booking["id"]),
            target_payment_id=UUID(payment["id"]),
            target_refund_id=UUID(refund["id"]),
            idempotency_key=f"admin-money-refund-detail-flag-{refund['id']}",
        )
        support_flag_id = str(support_flag.id)
        official_cancel_flag = create_support_flag(
            db,
            flag_type="official_cancel_partial_failure",
            source="official_game",
            title="Official cancellation follow-up",
            summary="This flag stays in the official cancellation workflow.",
            severity="urgent",
            target_game_id=UUID(game["id"]),
            target_booking_id=UUID(booking["id"]),
            target_refund_id=UUID(refund["id"]),
            idempotency_key=f"admin-money-refund-official-cancel-{refund['id']}",
        )
        official_cancel_flag_id = str(official_cancel_flag.id)

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/refunds/{refund['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["refund"]["id"] == refund["id"]
    assert body["refund"]["payment_id"] == payment["id"]
    assert body["refund"]["refund_status"] == "processing"
    assert body["refund"]["provider_refund_id"] == refund["provider_refund_id"]
    assert body["payment"]["id"] == payment["id"]
    assert body["payment"]["provider_charge_id"] == payment["provider_charge_id"]
    assert body["booking"]["id"] == booking["id"]
    assert body["game"]["id"] == game["id"]
    assert credit["id"] in {item["id"] for item in body["credit_grants"]}
    assert other_credit["id"] not in {
        item["id"] for item in body["credit_grants"]
    }
    assert other_refund["id"] != body["refund"]["id"]
    assert usage_id in {item["id"] for item in body["credit_usages"]}
    assert other_usage_id not in {item["id"] for item in body["credit_usages"]}
    assert support_flag_id in {item["id"] for item in body["support_flags"]}
    assert official_cancel_flag_id not in {
        item["id"] for item in body["support_flags"]
    }
    assert any(
        action["action_type"] == "create_refund"
        and action["target_refund_id"] == refund["id"]
        for action in body["audit_actions"]
    )
    assert any(
        action["action_type"] == "create_payment"
        and action["target_payment_id"] == payment["id"]
        for action in body["audit_actions"]
    )
    assert all(
        action["target_payment_id"] != other_payment["id"]
        and action["target_refund_id"] != other_refund["id"]
        and action["target_game_credit_id"] != other_credit["id"]
        for action in body["audit_actions"]
    )
    assert all("idempotency_key" not in action for action in body["audit_actions"])


def test_moderator_cannot_get_refund_detail(client: TestClient):
    moderator = create_user(client)
    player = create_user(client)
    set_user_role(moderator["id"], "moderator")
    venue = create_venue(client, player["id"])
    game = create_game(client, player["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(client, payment["id"], booking_id=booking["id"])

    authenticate_as(moderator["id"])
    response = client.get(f"/admin/money/refunds/{refund['id']}")

    assert response.status_code == 403, response.text


def test_admin_refund_detail_missing_refund_returns_404(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get(
        "/admin/money/refunds/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404, response.text


def test_admin_can_retry_failed_refund_from_money_detail(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        refund_status="failed",
    )
    provider_refund_id = f"re_{unique_suffix()}"
    stripe_calls = []

    def fake_create_refund(**kwargs):
        stripe_calls.append(kwargs)
        return StripeRefundResult(
            id=provider_refund_id,
            status="succeeded",
            amount_cents=booking["total_cents"],
            currency="USD",
            charge_id=payment["provider_charge_id"],
            payment_intent_id=payment["provider_payment_intent_id"],
        )

    monkeypatch.setattr(
        "backend.services.admin_money_refund_service.create_stripe_refund",
        fake_create_refund,
    )

    payload = {
        "reason": "Retry failed Stripe refund after support review.",
        "idempotency_key": f"admin-money-retry-{unique_suffix()}",
    }

    authenticate_as(admin["id"])
    response = client.post(f"/admin/money/refunds/{refund['id']}/retry", json=payload)
    duplicate_response = client.post(
        f"/admin/money/refunds/{refund['id']}/retry",
        json=payload,
    )

    assert response.status_code == 200, response.text
    assert duplicate_response.status_code == 200, duplicate_response.text
    assert len(stripe_calls) == 1
    assert stripe_calls[0]["charge_id"] == payment["provider_charge_id"]
    assert stripe_calls[0]["amount_cents"] == booking["total_cents"]
    assert stripe_calls[0]["idempotency_key"] == payload["idempotency_key"]

    body = duplicate_response.json()
    assert body["refund"]["id"] == refund["id"]
    assert body["refund"]["provider_refund_id"] == provider_refund_id
    assert body["refund"]["refund_status"] == "succeeded"
    assert body["refund"]["approved_by_user_id"] == admin["id"]
    assert body["payment"]["payment_status"] == "refunded"
    assert body["booking"]["payment_status"] == "refunded"
    assert any(
        action["action_type"] == "update_refund"
        and action["target_refund_id"] == refund["id"]
        and action["reason"] == payload["reason"]
        and action["metadata"]["source"] == "admin_money_refund_retry"
        and action["metadata"]["old_refund_status"] == "failed"
        and action["metadata"]["new_refund_status"] == "succeeded"
        for action in body["audit_actions"]
    )
    assert all(
        flag["flag_type"] != "stripe_refund_failed"
        for flag in body["support_flags"]
    )
    with SessionLocal() as db:
        notification = db.scalar(
            select(Notification).where(
                Notification.user_id == UUID(player["id"]),
                Notification.notification_type == "booking_refunded",
                Notification.related_refund_id == UUID(refund["id"]),
            )
        )
        assert notification is not None
        assert notification.action_key == "view_game"
        assert notification.related_game_id == UUID(game["id"])


def test_admin_refund_retry_failure_creates_money_follow_up(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=500,
        refund_status="failed",
    )
    provider_refund_id = f"re_{unique_suffix()}"

    def fake_create_refund(**kwargs):
        return StripeRefundResult(
            id=provider_refund_id,
            status="failed",
            amount_cents=500,
            currency="USD",
            charge_id=payment["provider_charge_id"],
            payment_intent_id=payment["provider_payment_intent_id"],
        )

    monkeypatch.setattr(
        "backend.services.admin_money_refund_service.create_stripe_refund",
        fake_create_refund,
    )

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/money/refunds/{refund['id']}/retry",
        json={
            "reason": "Retry failed refund and keep follow-up open.",
            "idempotency_key": f"admin-money-retry-failed-{unique_suffix()}",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["refund"]["provider_refund_id"] == provider_refund_id
    assert body["refund"]["refund_status"] == "failed"
    assert body["payment"]["payment_status"] == "succeeded"
    assert body["booking"]["payment_status"] == "paid"
    assert any(
        flag["flag_type"] == "stripe_refund_failed"
        and flag["flag_status"] == "open"
        and flag["target_refund_id"] == refund["id"]
        for flag in body["support_flags"]
    )
    assert any(
        action["action_type"] == "update_refund"
        and action["metadata"]["source"] == "admin_money_refund_retry"
        for action in body["audit_actions"]
    )


def test_admin_refund_retry_processing_creates_follow_up(client: TestClient, monkeypatch):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=500,
        refund_status="failed",
    )
    provider_refund_id = f"re_{unique_suffix()}"

    def fake_create_refund(**kwargs):
        return StripeRefundResult(
            id=provider_refund_id,
            status="processing",
            amount_cents=500,
            currency="USD",
            charge_id=payment["provider_charge_id"],
            payment_intent_id=payment["provider_payment_intent_id"],
        )

    monkeypatch.setattr(
        "backend.services.admin_money_refund_service.create_stripe_refund",
        fake_create_refund,
    )

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/money/refunds/{refund['id']}/retry",
        json={
            "reason": "Retry returned processing and needs follow-up.",
            "idempotency_key": f"admin-money-retry-processing-{unique_suffix()}",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["refund"]["provider_refund_id"] == provider_refund_id
    assert body["refund"]["refund_status"] == "processing"
    assert body["payment"]["payment_status"] == "succeeded"
    assert body["booking"]["payment_status"] == "paid"
    assert any(
        flag["flag_type"] == "refund_follow_up_required"
        and flag["flag_status"] == "open"
        and flag["target_refund_id"] == refund["id"]
        for flag in body["support_flags"]
    )


def test_admin_can_retry_cancelled_refund_from_money_detail(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=500,
        refund_reason="game_cancelled",
        refund_status="cancelled",
    )
    provider_refund_id = f"re_{unique_suffix()}"
    stripe_calls = []

    def fake_create_refund(**kwargs):
        stripe_calls.append(kwargs)
        return StripeRefundResult(
            id=provider_refund_id,
            status="succeeded",
            amount_cents=500,
            currency="USD",
            charge_id=payment["provider_charge_id"],
            payment_intent_id=payment["provider_payment_intent_id"],
        )

    monkeypatch.setattr(
        "backend.services.admin_money_refund_service.create_stripe_refund",
        fake_create_refund,
    )

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/money/refunds/{refund['id']}/retry",
        json={
            "reason": "Retry a cancelled Stripe refund.",
            "idempotency_key": f"admin-money-retry-cancelled-{unique_suffix()}",
        },
    )

    assert response.status_code == 200, response.text
    assert len(stripe_calls) == 1
    body = response.json()
    assert body["refund"]["provider_refund_id"] == provider_refund_id
    assert body["refund"]["refund_status"] == "succeeded"
    assert body["payment"]["payment_status"] == "partially_refunded"
    assert body["booking"]["payment_status"] == "partially_refunded"
    with SessionLocal() as db:
        notification = db.scalar(
            select(Notification).where(
                Notification.user_id == UUID(player["id"]),
                Notification.notification_type == "booking_refunded",
                Notification.related_refund_id == UUID(refund["id"]),
            )
        )
        assert notification is not None
        assert notification.action_key is None


def test_admin_refund_retry_stripe_error_does_not_mutate_money_truth(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=500,
        refund_status="failed",
    )
    stripe_calls = []

    def fake_create_refund(**kwargs):
        stripe_calls.append(kwargs)
        raise RuntimeError("Stripe request timed out.")

    monkeypatch.setattr(
        "backend.services.admin_money_refund_service.create_stripe_refund",
        fake_create_refund,
    )

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/money/refunds/{refund['id']}/retry",
        json={
            "reason": "Retry hit an unknown Stripe transport error.",
            "idempotency_key": f"admin-money-retry-error-{unique_suffix()}",
        },
    )

    assert response.status_code == 502, response.text
    assert response.json()["detail"] == "Stripe refund retry could not be completed."
    assert len(stripe_calls) == 1

    with SessionLocal() as db:
        db_refund = db.get(Refund, UUID(refund["id"]))
        db_payment = db.get(Payment, UUID(payment["id"]))
        retry_actions = db.scalars(
            select(AdminAction).where(AdminAction.target_refund_id == UUID(refund["id"]))
        ).all()
        retry_flags = db.scalars(
            select(SupportFlag).where(SupportFlag.target_refund_id == UUID(refund["id"]))
        ).all()

    assert db_refund is not None
    assert db_refund.refund_status == "failed"
    assert db_refund.provider_refund_id == refund["provider_refund_id"]
    assert db_payment is not None
    assert db_payment.payment_status == "succeeded"
    assert all(
        (action.metadata_ or {}).get("source") != "admin_money_refund_retry"
        for action in retry_actions
    )
    assert all(
        (flag.metadata_ or {}).get("operation") != "admin_money_refund_retry"
        for flag in retry_flags
    )


def test_admin_refund_retry_rejects_invalid_payment_state_before_stripe(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    missing_charge_booking = create_booking(client, player["id"], game["id"])
    missing_charge_payment = create_payment(
        client,
        player["id"],
        booking_id=missing_charge_booking["id"],
        amount_cents=missing_charge_booking["total_cents"],
        payment_status="succeeded",
    )
    missing_charge_refund = create_refund(
        client,
        missing_charge_payment["id"],
        booking_id=missing_charge_booking["id"],
        amount_cents=500,
        refund_status="failed",
    )
    missing_paid_booking = create_booking(client, player["id"], game["id"])
    missing_paid_payment = create_payment(
        client,
        player["id"],
        booking_id=missing_paid_booking["id"],
        amount_cents=missing_paid_booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    missing_paid_refund = create_refund(
        client,
        missing_paid_payment["id"],
        booking_id=missing_paid_booking["id"],
        amount_cents=500,
        refund_status="failed",
    )
    stripe_calls = []

    def fake_create_refund(**kwargs):
        stripe_calls.append(kwargs)
        return StripeRefundResult(
            id=f"re_{unique_suffix()}",
            status="succeeded",
            amount_cents=500,
            currency="USD",
            charge_id=kwargs["charge_id"],
            payment_intent_id=None,
        )

    monkeypatch.setattr(
        "backend.services.admin_money_refund_service.create_stripe_refund",
        fake_create_refund,
    )

    with SessionLocal() as db:
        db_payment = db.get(Payment, UUID(missing_paid_payment["id"]))
        assert db_payment is not None
        db_payment.payment_status = "partially_refunded"
        db_payment.paid_at = None
        db.commit()

    authenticate_as(admin["id"])
    missing_charge_response = client.post(
        f"/admin/money/refunds/{missing_charge_refund['id']}/retry",
        json={
            "reason": "Missing Stripe charge id should block retry.",
            "idempotency_key": f"admin-money-retry-no-charge-{unique_suffix()}",
        },
    )
    missing_paid_response = client.post(
        f"/admin/money/refunds/{missing_paid_refund['id']}/retry",
        json={
            "reason": "Missing paid timestamp should block retry.",
            "idempotency_key": f"admin-money-retry-no-paid-at-{unique_suffix()}",
        },
    )

    assert missing_charge_response.status_code == 400, missing_charge_response.text
    assert (
        missing_charge_response.json()["detail"]
        == "Refund retry requires a Stripe charge id."
    )
    assert missing_paid_response.status_code == 400, missing_paid_response.text
    assert (
        missing_paid_response.json()["detail"]
        == "Refund retry requires a succeeded payment."
    )
    assert stripe_calls == []


def test_admin_refund_retry_rejects_non_retryable_refund(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        refund_status="processing",
    )

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/money/refunds/{refund['id']}/retry",
        json={
            "reason": "This refund is still processing.",
            "idempotency_key": f"admin-money-retry-invalid-{unique_suffix()}",
        },
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Only failed or cancelled refunds can be retried."


def test_moderator_cannot_retry_admin_money_refund(client: TestClient):
    moderator = create_user(client)
    player = create_user(client)
    set_user_role(moderator["id"], "moderator")
    venue = create_venue(client, player["id"])
    game = create_game(client, player["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        refund_status="failed",
    )

    authenticate_as(moderator["id"])
    response = client.post(
        f"/admin/money/refunds/{refund['id']}/retry",
        json={
            "reason": "Moderator cannot retry money refunds.",
            "idempotency_key": f"admin-money-retry-moderator-{unique_suffix()}",
        },
    )

    assert response.status_code == 403, response.text


def test_admin_can_list_money_support_flags_only(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        refund_status="failed",
    )

    with SessionLocal() as db:
        money_flag = create_support_flag(
            db,
            flag_type="stripe_refund_failed",
            source="stripe",
            title="Stripe refund failed",
            summary="Stripe reported a failed refund that needs money follow-up.",
            severity="urgent",
            target_user_id=UUID(player["id"]),
            target_game_id=UUID(game["id"]),
            target_booking_id=UUID(booking["id"]),
            target_payment_id=UUID(payment["id"]),
            target_refund_id=UUID(refund["id"]),
            idempotency_key=f"admin-money-list-money-{refund['id']}",
            metadata={"provider_refund_id": refund["provider_refund_id"]},
        )
        account_flag = create_support_flag(
            db,
            flag_type="account_delete_partial_failure",
            source="account",
            title="Account cleanup follow-up",
            summary="Account cleanup is outside the money support queue.",
            severity="attention",
            target_user_id=UUID(player["id"]),
            idempotency_key=f"admin-money-list-account-{player['id']}",
        )
        official_cancel_flag = create_support_flag(
            db,
            flag_type="official_cancel_partial_failure",
            source="official_game",
            title="Official cancellation follow-up",
            summary="Official cancellation follow-up stays outside this money queue.",
            severity="urgent",
            target_user_id=UUID(player["id"]),
            target_game_id=UUID(game["id"]),
            target_booking_id=UUID(booking["id"]),
            target_payment_id=UUID(payment["id"]),
            target_refund_id=UUID(refund["id"]),
            idempotency_key=f"admin-money-list-official-cancel-{booking['id']}",
        )
        money_flag_id = str(money_flag.id)
        account_flag_id = str(account_flag.id)
        official_cancel_flag_id = str(official_cancel_flag.id)

    authenticate_as(admin["id"])
    response = client.get("/admin/money/support-flags?flag_status=open")

    assert response.status_code == 200, response.text
    body = response.json()
    ids = {item["id"] for item in body}
    assert money_flag_id in ids
    assert account_flag_id not in ids
    assert official_cancel_flag_id not in ids

    money_row = next(item for item in body if item["id"] == money_flag_id)
    assert money_row["flag_type"] == "stripe_refund_failed"
    assert money_row["target_refund_id"] == refund["id"]
    assert "metadata" not in money_row
    assert "idempotency_key" not in money_row
    assert "resolution_reason" not in money_row


def test_admin_money_support_flag_list_rejects_bad_status(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get("/admin/money/support-flags?flag_status=closed")

    assert response.status_code == 400, response.text


def test_admin_can_get_money_support_flag_detail(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        refund_status="failed",
    )
    credit = issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        booking_id=booking["id"],
        payment_id=payment["id"],
        amount_cents=700,
    )

    with SessionLocal() as db:
        usages = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=300,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(payment["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"admin-money-flag-detail:{booking['id']}",
        )
        usage_id = str(usages[0].id)
        db.commit()

    with SessionLocal() as db:
        support_flag = create_support_flag(
            db,
            flag_type="stripe_refund_failed",
            source="stripe",
            title="Stripe refund failed",
            summary="Stripe reported a failed refund that needs money follow-up.",
            severity="critical",
            target_user_id=UUID(player["id"]),
            target_game_id=UUID(game["id"]),
            target_booking_id=UUID(booking["id"]),
            target_payment_id=UUID(payment["id"]),
            target_refund_id=UUID(refund["id"]),
            idempotency_key=f"admin-money-flag-detail-{refund['id']}",
            metadata={"provider_refund_id": refund["provider_refund_id"]},
        )
        support_flag_id = str(support_flag.id)

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/support-flags/{support_flag_id}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["support_flag"]["id"] == support_flag_id
    assert body["support_flag"]["flag_type"] == "stripe_refund_failed"
    assert body["support_flag"]["severity"] == "critical"
    assert "metadata" not in body["support_flag"]
    assert "idempotency_key" not in body["support_flag"]
    assert {item["id"] for item in body["payments"]} == {payment["id"]}
    assert {item["id"] for item in body["refunds"]} == {refund["id"]}
    assert body["booking"]["id"] == booking["id"]
    assert body["game"]["id"] == game["id"]
    assert credit["id"] in {item["id"] for item in body["credit_grants"]}
    assert usage_id in {item["id"] for item in body["credit_usages"]}
    assert any(
        action["action_type"] == "create_refund"
        and action["target_refund_id"] == refund["id"]
        for action in body["audit_actions"]
    )
    assert any(
        action["action_type"] == "issue_credit"
        and action["target_game_credit_id"] == credit["id"]
        for action in body["audit_actions"]
    )


def test_admin_can_resolve_money_support_flag_without_mutating_refund_truth(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        refund_status="failed",
    )

    with SessionLocal() as db:
        support_flag = create_support_flag(
            db,
            flag_type="stripe_refund_failed",
            source="stripe",
            title="Stripe refund failed",
            summary="Staff handled this failed refund externally.",
            severity="urgent",
            target_user_id=UUID(player["id"]),
            target_game_id=UUID(game["id"]),
            target_booking_id=UUID(booking["id"]),
            target_payment_id=UUID(payment["id"]),
            target_refund_id=UUID(refund["id"]),
            idempotency_key=f"admin-money-resolve-flag-{refund['id']}",
        )
        support_flag_id = str(support_flag.id)

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/money/support-flags/{support_flag_id}/resolve",
        json={
            "outcome": "handled_externally",
            "reason": "Stripe refund was handled outside Pickup Lane.",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["support_flag"]["id"] == support_flag_id
    assert body["support_flag"]["flag_status"] == "resolved"
    assert body["support_flag"]["resolution_outcome"] == "handled_externally"
    assert body["support_flag"]["resolved_at"] is not None
    assert "metadata" not in body["support_flag"]
    assert "idempotency_key" not in body["support_flag"]
    assert "resolution_reason" not in body["support_flag"]
    assert {item["id"] for item in body["refunds"]} == {refund["id"]}
    assert body["refunds"][0]["refund_status"] == "failed"
    assert body["payments"][0]["payment_status"] == "succeeded"
    assert body["booking"]["payment_status"] == "paid"
    assert any(
        action["action_type"] == "resolve_support_flag"
        and action["target_support_flag_id"] == support_flag_id
        and action["reason"] == "Stripe refund was handled outside Pickup Lane."
        for action in body["audit_actions"]
    )


def test_moderator_cannot_resolve_money_support_flag(client: TestClient):
    moderator = create_user(client)
    player = create_user(client)
    set_user_role(moderator["id"], "moderator")
    venue = create_venue(client, player["id"])
    game = create_game(client, player["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        refund_status="failed",
    )

    with SessionLocal() as db:
        support_flag = create_support_flag(
            db,
            flag_type="stripe_refund_failed",
            source="stripe",
            title="Stripe refund failed",
            summary="Money follow-up requires admin money access.",
            severity="urgent",
            target_user_id=UUID(player["id"]),
            target_game_id=UUID(game["id"]),
            target_booking_id=UUID(booking["id"]),
            target_payment_id=UUID(payment["id"]),
            target_refund_id=UUID(refund["id"]),
            idempotency_key=f"admin-money-moderator-resolve-{refund['id']}",
        )
        support_flag_id = str(support_flag.id)

    authenticate_as(moderator["id"])
    response = client.post(
        f"/admin/money/support-flags/{support_flag_id}/resolve",
        json={
            "outcome": "handled_externally",
            "reason": "Moderator cannot resolve money support flags.",
        },
    )

    assert response.status_code == 403, response.text


def test_admin_money_support_flag_resolve_hides_non_money_flags(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    with SessionLocal() as db:
        support_flag = create_support_flag(
            db,
            flag_type="account_delete_partial_failure",
            source="account",
            title="Account cleanup follow-up",
            summary="Account cleanup is outside the money support queue.",
            severity="attention",
            target_user_id=UUID(player["id"]),
            idempotency_key=f"admin-money-resolve-non-money-{player['id']}",
        )
        support_flag_id = str(support_flag.id)

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/money/support-flags/{support_flag_id}/resolve",
        json={
            "outcome": "handled_externally",
            "reason": "This is not a direct money support flag.",
        },
    )

    assert response.status_code == 404, response.text


def test_admin_money_support_flag_detail_derives_credit_context(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    other_player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    other_booking = create_booking(client, other_player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=500,
        refund_status="failed",
    )
    other_payment = create_payment(
        client,
        other_player["id"],
        booking_id=other_booking["id"],
        amount_cents=other_booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    other_refund = create_refund(
        client,
        other_payment["id"],
        booking_id=other_booking["id"],
        amount_cents=500,
        refund_status="failed",
    )
    credit = issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        booking_id=booking["id"],
        payment_id=payment["id"],
        amount_cents=700,
    )
    other_credit = issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=other_player["id"],
        game_id=game["id"],
        booking_id=other_booking["id"],
        payment_id=other_payment["id"],
        amount_cents=600,
    )

    with SessionLocal() as db:
        usages = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=300,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(payment["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"admin-money-credit-flag:{booking['id']}",
        )
        other_usages = reserve_game_credits(
            db,
            UUID(other_player["id"]),
            amount_cents=300,
            booking_id=UUID(other_booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(other_payment["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"admin-money-credit-flag:{other_booking['id']}",
        )
        usage_id = str(usages[0].id)
        other_usage_id = str(other_usages[0].id)
        db.commit()

    with SessionLocal() as db:
        support_flag = create_support_flag(
            db,
            flag_type="credit_release_failed",
            source="system",
            title="Credit release failed",
            summary="Credit release needs staff follow-up.",
            severity="urgent",
            target_user_id=UUID(player["id"]),
            target_game_credit_id=UUID(credit["id"]),
            idempotency_key=f"admin-money-credit-flag-detail-{credit['id']}",
        )
        support_flag_id = str(support_flag.id)

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/support-flags/{support_flag_id}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["support_flag"]["target_game_credit_id"] == credit["id"]
    assert body["booking"]["id"] == booking["id"]
    assert body["game"]["id"] == game["id"]
    assert {item["id"] for item in body["payments"]} == {payment["id"]}
    assert {item["id"] for item in body["refunds"]} == {refund["id"]}
    assert credit["id"] in {item["id"] for item in body["credit_grants"]}
    assert other_credit["id"] not in {
        item["id"] for item in body["credit_grants"]
    }
    assert usage_id in {item["id"] for item in body["credit_usages"]}
    assert other_usage_id not in {item["id"] for item in body["credit_usages"]}
    assert other_payment["id"] not in {item["id"] for item in body["payments"]}
    assert other_refund["id"] not in {item["id"] for item in body["refunds"]}
    assert any(
        action["action_type"] == "create_payment"
        and action["target_payment_id"] == payment["id"]
        for action in body["audit_actions"]
    )
    assert any(
        action["action_type"] == "create_refund"
        and action["target_refund_id"] == refund["id"]
        for action in body["audit_actions"]
    )
    assert any(
        action["action_type"] == "issue_credit"
        and action["target_game_credit_id"] == credit["id"]
        for action in body["audit_actions"]
    )
    assert all(
        action["target_payment_id"] != other_payment["id"]
        and action["target_refund_id"] != other_refund["id"]
        and action["target_game_credit_id"] != other_credit["id"]
        for action in body["audit_actions"]
    )


def test_moderator_cannot_read_money_support_flags(client: TestClient):
    moderator = create_user(client)
    player = create_user(client)
    set_user_role(moderator["id"], "moderator")
    venue = create_venue(client, player["id"])
    game = create_game(client, player["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(client, payment["id"], booking_id=booking["id"])

    with SessionLocal() as db:
        support_flag = create_support_flag(
            db,
            flag_type="refund_follow_up_required",
            source="stripe",
            title="Refund follow-up",
            summary="Refund needs staff follow-up.",
            severity="attention",
            target_user_id=UUID(player["id"]),
            target_game_id=UUID(game["id"]),
            target_booking_id=UUID(booking["id"]),
            target_payment_id=UUID(payment["id"]),
            target_refund_id=UUID(refund["id"]),
            idempotency_key=f"admin-money-moderator-flag-{refund['id']}",
        )
        support_flag_id = str(support_flag.id)

    authenticate_as(moderator["id"])
    list_response = client.get("/admin/money/support-flags")
    detail_response = client.get(f"/admin/money/support-flags/{support_flag_id}")

    assert list_response.status_code == 403, list_response.text
    assert detail_response.status_code == 403, detail_response.text


def test_admin_money_support_flag_detail_hides_non_money_flags(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    with SessionLocal() as db:
        support_flag = create_support_flag(
            db,
            flag_type="account_delete_partial_failure",
            source="account",
            title="Account cleanup follow-up",
            summary="Account cleanup is outside the money support queue.",
            severity="attention",
            target_user_id=UUID(player["id"]),
            idempotency_key=f"admin-money-non-money-{player['id']}",
        )
        support_flag_id = str(support_flag.id)

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/support-flags/{support_flag_id}")

    assert response.status_code == 404, response.text


def test_admin_money_support_flag_detail_missing_flag_returns_404(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get(
        "/admin/money/support-flags/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404, response.text


def test_admin_can_list_money_credits_by_user(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    other_player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    other_booking = create_booking(client, other_player["id"], game["id"])
    other_payment = create_payment(
        client,
        other_player["id"],
        booking_id=other_booking["id"],
        amount_cents=other_booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    credit = issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        booking_id=booking["id"],
        payment_id=payment["id"],
        amount_cents=700,
    )
    other_credit = issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=other_player["id"],
        game_id=game["id"],
        booking_id=other_booking["id"],
        payment_id=other_payment["id"],
        amount_cents=900,
    )

    authenticate_as(admin["id"])
    response = client.get(
        f"/admin/money/credits?user_id={player['id']}&credit_status=active"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    ids = {item["id"] for item in body}
    assert credit["id"] in ids
    assert other_credit["id"] not in ids

    credit_row = next(item for item in body if item["id"] == credit["id"])
    assert credit_row["user_id"] == player["id"]
    assert credit_row["remaining_cents"] == 700
    assert "idempotency_key" not in credit_row
    assert "note" not in credit_row

    game_response = client.get(
        f"/admin/money/credits?source_game_id={game['id']}&credit_status=active"
    )
    booking_response = client.get(
        f"/admin/money/credits?source_booking_id={booking['id']}"
    )
    payment_response = client.get(
        f"/admin/money/credits?source_payment_id={payment['id']}"
    )

    assert game_response.status_code == 200, game_response.text
    assert {item["id"] for item in game_response.json()} == {
        credit["id"],
        other_credit["id"],
    }
    assert booking_response.status_code == 200, booking_response.text
    assert {item["id"] for item in booking_response.json()} == {credit["id"]}
    assert payment_response.status_code == 200, payment_response.text
    assert {item["id"] for item in payment_response.json()} == {credit["id"]}


def test_admin_can_get_money_credit_detail_support_context(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    other_player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    other_booking = create_booking(client, other_player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    other_payment = create_payment(
        client,
        other_player["id"],
        booking_id=other_booking["id"],
        amount_cents=other_booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=500,
        refund_status="failed",
    )
    other_refund = create_refund(
        client,
        other_payment["id"],
        booking_id=other_booking["id"],
        amount_cents=500,
        refund_status="failed",
    )
    credit = issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        booking_id=booking["id"],
        payment_id=payment["id"],
        amount_cents=700,
    )
    other_credit = issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=other_player["id"],
        game_id=game["id"],
        booking_id=other_booking["id"],
        payment_id=other_payment["id"],
        amount_cents=600,
    )

    with SessionLocal() as db:
        usages = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=300,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(payment["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"admin-money-credit-detail:{booking['id']}",
        )
        other_usages = reserve_game_credits(
            db,
            UUID(other_player["id"]),
            amount_cents=300,
            booking_id=UUID(other_booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(other_payment["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"admin-money-credit-detail:{other_booking['id']}",
        )
        usage_id = str(usages[0].id)
        other_usage_id = str(other_usages[0].id)
        db.commit()

    with SessionLocal() as db:
        support_flag = create_support_flag(
            db,
            flag_type="credit_release_failed",
            source="system",
            title="Credit release failed",
            summary="Credit release needs staff follow-up.",
            severity="urgent",
            target_user_id=UUID(player["id"]),
            target_game_id=UUID(game["id"]),
            target_booking_id=UUID(booking["id"]),
            target_payment_id=UUID(payment["id"]),
            target_game_credit_id=UUID(credit["id"]),
            idempotency_key=f"admin-money-credit-detail-flag-{credit['id']}",
        )
        support_flag_id = str(support_flag.id)
        official_cancel_flag = create_support_flag(
            db,
            flag_type="official_cancel_partial_failure",
            source="official_game",
            title="Official cancellation follow-up",
            summary="This flag stays in the official cancellation workflow.",
            severity="urgent",
            target_user_id=UUID(player["id"]),
            target_game_id=UUID(game["id"]),
            target_booking_id=UUID(booking["id"]),
            target_payment_id=UUID(payment["id"]),
            target_refund_id=UUID(refund["id"]),
            target_game_credit_id=UUID(credit["id"]),
            idempotency_key=f"admin-money-credit-official-cancel-{credit['id']}",
        )
        official_cancel_flag_id = str(official_cancel_flag.id)
        other_support_flag = create_support_flag(
            db,
            flag_type="credit_release_failed",
            source="system",
            title="Other credit release failed",
            summary="Another booking needs separate credit follow-up.",
            severity="urgent",
            target_user_id=UUID(other_player["id"]),
            target_game_id=UUID(game["id"]),
            target_booking_id=UUID(other_booking["id"]),
            target_payment_id=UUID(other_payment["id"]),
            target_game_credit_id=UUID(other_credit["id"]),
            idempotency_key=f"admin-money-other-credit-flag-{other_credit['id']}",
        )
        other_support_flag_id = str(other_support_flag.id)

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/credits/{credit['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["credit"]["id"] == credit["id"]
    assert body["credit"]["user_id"] == player["id"]
    assert body["credit"]["source_payment_id"] == payment["id"]
    assert "idempotency_key" not in body["credit"]
    assert "note" not in body["credit"]
    assert {item["id"] for item in body["credit_usages"]} == {usage_id}
    assert other_usage_id not in {item["id"] for item in body["credit_usages"]}
    assert all("idempotency_key" not in item for item in body["credit_usages"])
    assert {item["id"] for item in body["payments"]} == {payment["id"]}
    assert {item["id"] for item in body["refunds"]} == {refund["id"]}
    assert body["booking"]["id"] == booking["id"]
    assert body["game"]["id"] == game["id"]
    assert {item["id"] for item in body["support_flags"]} == {support_flag_id}
    assert official_cancel_flag_id not in {
        item["id"] for item in body["support_flags"]
    }
    assert other_support_flag_id not in {
        item["id"] for item in body["support_flags"]
    }
    assert other_payment["id"] not in {item["id"] for item in body["payments"]}
    assert other_refund["id"] not in {item["id"] for item in body["refunds"]}
    assert any(
        action["action_type"] == "issue_credit"
        and action["target_game_credit_id"] == credit["id"]
        for action in body["audit_actions"]
    )
    assert any(
        action["action_type"] == "create_refund"
        and action["target_refund_id"] == refund["id"]
        for action in body["audit_actions"]
    )
    assert all(
        action["target_payment_id"] != other_payment["id"]
        and action["target_refund_id"] != other_refund["id"]
        and action["target_game_credit_id"] != other_credit["id"]
        and action["target_support_flag_id"] != other_support_flag_id
        for action in body["audit_actions"]
    )


def test_moderator_cannot_read_money_credits(client: TestClient):
    moderator = create_user(client)
    admin = create_user(client)
    player = create_user(client)
    set_user_role(moderator["id"], "moderator")
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    credit = issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        booking_id=booking["id"],
        payment_id=payment["id"],
        amount_cents=700,
    )

    authenticate_as(moderator["id"])
    list_response = client.get(f"/admin/money/credits?user_id={player['id']}")
    detail_response = client.get(f"/admin/money/credits/{credit['id']}")

    assert list_response.status_code == 403, list_response.text
    assert detail_response.status_code == 403, detail_response.text


def test_admin_money_credit_list_rejects_bad_status(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get("/admin/money/credits?credit_status=settled")

    assert response.status_code == 400, response.text


def test_admin_money_credit_detail_missing_credit_returns_404(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get(
        "/admin/money/credits/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404, response.text


def test_admin_can_get_user_money_support_summary(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    other_player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=500,
        refund_status="failed",
    )
    credit = issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        booking_id=booking["id"],
        payment_id=payment["id"],
        amount_cents=700,
    )
    active_method = create_user_payment_method(
        client,
        player["id"],
        card_brand="visa",
        card_last4="4242",
        is_default=True,
    )
    inactive_method = create_user_payment_method(
        client,
        player["id"],
        card_brand="mastercard",
        card_last4="4444",
        method_status="detached",
        is_default=False,
    )
    other_booking = create_booking(client, other_player["id"], game["id"])
    other_payment = create_payment(
        client,
        other_player["id"],
        booking_id=other_booking["id"],
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    wrong_user_credit = issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=other_player["id"],
        game_id=game["id"],
        booking_id=other_booking["id"],
        payment_id=other_payment["id"],
        amount_cents=900,
    )
    create_user_payment_method(client, other_player["id"], card_last4="1117")

    with SessionLocal() as db:
        usages = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=300,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(payment["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"admin-money-user-summary:{booking['id']}",
        )
        usage_id = str(usages[0].id)
        db.commit()

    with SessionLocal() as db:
        wrong_user_usages = reserve_game_credits(
            db,
            UUID(other_player["id"]),
            amount_cents=300,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(payment["id"]),
            now=datetime.now(UTC),
            idempotency_scope=(
                f"admin-money-user-summary-wrong-user:{booking['id']}"
            ),
        )
        wrong_user_usage_id = str(wrong_user_usages[0].id)
        db.commit()

    with SessionLocal() as db:
        support_flag = create_support_flag(
            db,
            flag_type="stripe_refund_failed",
            source="stripe",
            title="Stripe refund failed",
            summary="Stripe refund needs user money follow-up.",
            severity="urgent",
            target_user_id=UUID(player["id"]),
            target_game_id=UUID(game["id"]),
            target_booking_id=UUID(booking["id"]),
            target_payment_id=UUID(payment["id"]),
            target_refund_id=UUID(refund["id"]),
            idempotency_key=f"admin-money-user-summary-flag-{refund['id']}",
            metadata={"provider_refund_id": refund["provider_refund_id"]},
        )
        support_flag_id = str(support_flag.id)
        wrong_user_credit_flag = create_support_flag(
            db,
            flag_type="credit_restore_failed",
            source="admin",
            title="Wrong user credit follow-up",
            summary="This wrong-user credit must not leak into selected user summary.",
            severity="attention",
            target_user_id=UUID(other_player["id"]),
            target_game_id=UUID(game["id"]),
            target_game_credit_id=UUID(wrong_user_credit["id"]),
            idempotency_key=(
                f"admin-money-user-summary-wrong-credit-{wrong_user_credit['id']}"
            ),
        )
        wrong_user_credit_flag_id = str(wrong_user_credit_flag.id)

    authenticate_as(admin["id"])
    default_response = client.get(f"/admin/money/users/{player['id']}")
    all_cards_response = client.get(
        f"/admin/money/users/{player['id']}?include_inactive_payment_methods=true"
    )

    assert default_response.status_code == 200, default_response.text
    body = default_response.json()
    assert body["user"]["id"] == player["id"]
    assert body["user"]["email"] == player["email"]
    assert body["user"]["account_status"] == "active"
    assert "auth_user_id" not in body["user"]
    assert "phone" not in body["user"]
    assert "date_of_birth" not in body["user"]
    assert "stripe_customer_id" not in body["user"]
    assert {item["id"] for item in body["payments"]} == {payment["id"]}
    assert other_payment["id"] not in {item["id"] for item in body["payments"]}
    assert {item["id"] for item in body["refunds"]} == {refund["id"]}
    assert credit["id"] in {item["id"] for item in body["credit_grants"]}
    assert wrong_user_credit["id"] not in {
        item["id"] for item in body["credit_grants"]
    }
    assert usage_id in {item["id"] for item in body["credit_usages"]}
    assert wrong_user_usage_id not in {item["id"] for item in body["credit_usages"]}
    assert {item["id"] for item in body["payment_methods"]} == {active_method["id"]}
    method_row = body["payment_methods"][0]
    assert method_row["card_last4"] == "4242"
    assert "stripe_customer_id" not in method_row
    assert "stripe_payment_method_id" not in method_row
    assert "card_fingerprint" not in method_row
    assert support_flag_id in {item["id"] for item in body["support_flags"]}
    assert wrong_user_credit_flag_id not in {
        item["id"] for item in body["support_flags"]
    }
    support_flag_row = next(
        item for item in body["support_flags"] if item["id"] == support_flag_id
    )
    assert "metadata" not in support_flag_row
    assert "idempotency_key" not in support_flag_row
    assert any(
        action["action_type"] == "create_payment"
        and action["target_payment_id"] == payment["id"]
        for action in body["audit_actions"]
    )
    assert wrong_user_credit["id"] not in {
        action["target_game_credit_id"] for action in body["audit_actions"]
    }
    assert all("idempotency_key" not in action for action in body["audit_actions"])

    assert all_cards_response.status_code == 200, all_cards_response.text
    all_card_ids = {item["id"] for item in all_cards_response.json()["payment_methods"]}
    assert active_method["id"] in all_card_ids
    assert inactive_method["id"] in all_card_ids


def test_moderator_cannot_read_admin_money_user_summary(client: TestClient):
    moderator = create_user(client)
    player = create_user(client)
    set_user_role(moderator["id"], "moderator")

    authenticate_as(moderator["id"])
    response = client.get(f"/admin/money/users/{player['id']}")

    assert response.status_code == 403, response.text


def test_admin_money_user_summary_missing_user_returns_404(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get(
        "/admin/money/users/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404, response.text


def test_admin_can_list_safe_saved_card_metadata(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    other_player = create_user(client)
    set_user_role(admin["id"], "admin")
    active_method = create_user_payment_method(
        client,
        player["id"],
        card_brand="visa",
        card_last4="4242",
        exp_month=12,
        exp_year=2030,
        is_default=True,
    )
    detached_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    detached_method = create_user_payment_method(
        client,
        player["id"],
        card_brand="mastercard",
        card_last4="4444",
        exp_month=11,
        exp_year=2031,
        method_status="detached",
        is_default=False,
        detached_at=detached_at,
    )
    other_method = create_user_payment_method(
        client,
        other_player["id"],
        card_brand="discover",
        card_last4="1117",
        is_default=True,
    )

    authenticate_as(admin["id"])
    active_response = client.get(
        f"/admin/money/payment-methods?user_id={player['id']}"
    )
    all_response = client.get(
        f"/admin/money/payment-methods?user_id={player['id']}&include_inactive=true"
    )

    assert active_response.status_code == 200, active_response.text
    active_body = active_response.json()
    assert {item["id"] for item in active_body} == {active_method["id"]}

    active_row = active_body[0]
    assert active_row["user_id"] == player["id"]
    assert active_row["card_brand"] == "visa"
    assert active_row["card_last4"] == "4242"
    assert active_row["exp_month"] == 12
    assert active_row["exp_year"] == 2030
    assert active_row["method_status"] == "active"
    assert active_row["is_default"] is True
    assert active_row["detached_at"] is None
    assert set(active_row) == {
        "id",
        "user_id",
        "card_brand",
        "card_last4",
        "exp_month",
        "exp_year",
        "method_status",
        "is_default",
        "created_at",
        "updated_at",
        "detached_at",
    }

    assert all_response.status_code == 200, all_response.text
    all_body = all_response.json()
    all_ids = {item["id"] for item in all_body}
    assert active_method["id"] in all_ids
    assert detached_method["id"] in all_ids
    assert other_method["id"] not in all_ids
    detached_row = next(
        item for item in all_body if item["id"] == detached_method["id"]
    )
    assert (
        datetime.fromisoformat(detached_row["detached_at"].replace("Z", "+00:00"))
        == detached_at
    )


def test_admin_money_saved_cards_require_user_id(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get("/admin/money/payment-methods")

    assert response.status_code == 422, response.text


def test_moderator_cannot_read_admin_money_saved_cards(client: TestClient):
    moderator = create_user(client)
    player = create_user(client)
    set_user_role(moderator["id"], "moderator")
    create_user_payment_method(client, player["id"])

    authenticate_as(moderator["id"])
    response = client.get(f"/admin/money/payment-methods?user_id={player['id']}")

    assert response.status_code == 403, response.text
