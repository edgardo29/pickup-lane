from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import (
    AdminAction,
    AdminFinancialOutcome,
    AdminTargetNotice,
    GameCredit,
    GameCreditUsage,
    HostPublishEntitlement,
    HostPublishFee,
    CommunityPublishAttempt,
    MoneyIssue,
    MoneyIssueEvent,
    Notification,
    Payment,
    Refund,
    RefundEvent,
)
from backend.services.admin_money_issue_service import (
    stage_credit_money_issue,
    stage_refund_money_issue,
)
from backend.services.game_credit_service import (
    GameCreditLedgerError,
    redeem_reserved_game_credits,
    reserve_game_credits,
)
from backend.services.stripe_service import StripeRefundResult
from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_game,
    create_host_publish_fee,
    create_payment,
    create_refund,
    create_user,
    create_user_payment_method,
    create_venue,
    set_user_role,
    unique_suffix,
)


def create_paid_publish_fee_setup(
    client: TestClient,
) -> tuple[dict, dict, dict, dict]:
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
    return host, game, payment, host_publish_fee


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


def create_refund_money_issue_for_test(
    db,
    *,
    refund_id: str,
    issue_type: str = "refund_failed",
    reason_code: str = "test_refund_issue",
):
    refund = db.get(Refund, UUID(refund_id))
    assert refund is not None
    payment = db.get(Payment, refund.payment_id)
    issue = stage_refund_money_issue(
        db,
        refund=refund,
        payment=payment,
        issue_type=issue_type,
        reason_code=reason_code,
        summary="Test money issue.",
    )
    return issue


def create_credit_money_issue_for_test(
    db,
    *,
    credit_usage_id: str,
    issue_type: str = "credit_release_failed",
    reason_code: str = "test_credit_issue",
):
    usage = db.get(GameCreditUsage, UUID(credit_usage_id))
    assert usage is not None
    credit = db.get(GameCredit, usage.game_credit_id)
    issue = stage_credit_money_issue(
        db,
        credit_usage=usage,
        game_credit=credit,
        issue_type=issue_type,
        origin_workflow="official_game_cancellation",
        reason_code=reason_code,
        summary="Test credit money issue.",
    )
    return issue


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
        f"/admin/money/payments?q={booking['id']}&payment_status=all"
    )
    game_response = client.get(
        f"/admin/money/payments?q={game['id']}&payment_status=succeeded"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert {item["id"] for item in body["items"]} == {succeeded_payment["id"]}
    row = body["items"][0]
    assert row["payer_user_id"] == player["id"]
    assert row["payment_status"] == "succeeded"
    assert row["is_fully_refunded"] is False
    assert set(row) == {
        "id",
        "payer_user_id",
        "booking_id",
        "game_id",
        "payment_type",
        "provider",
        "provider_payment_intent_id",
        "provider_charge_id",
        "amount_cents",
        "currency",
        "payment_status",
        "paid_at",
        "failure_code",
        "is_fully_refunded",
        "reserved_credit_cents",
        "redeemed_credit_cents",
        "open_money_issue_count",
        "display",
        "created_at",
    }

    assert booking_response.status_code == 200, booking_response.text
    booking_ids = {item["id"] for item in booking_response.json()["items"]}
    assert succeeded_payment["id"] in booking_ids
    assert failed_payment["id"] in booking_ids
    assert other_payment["id"] not in booking_ids

    assert game_response.status_code == 200, game_response.text
    game_payment_ids = {item["id"] for item in game_response.json()["items"]}
    assert game_payment_ids == {succeeded_payment["id"], other_payment["id"]}


def test_admin_money_payment_list_rejects_bad_status(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get("/admin/money/payments?payment_status=settled")

    assert response.status_code == 400, response.text


def test_admin_money_payment_list_rejects_removed_raw_filters(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/payments?booking_id={uuid4()}")

    assert response.status_code == 400, response.text


def test_admin_money_payment_search_finds_publish_fee_id(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    _host, _game, payment, host_publish_fee = create_paid_publish_fee_setup(client)

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/payments?q={host_publish_fee['id']}")

    assert response.status_code == 200, response.text
    assert {item["id"] for item in response.json()["items"]} == {payment["id"]}


def test_player_cannot_list_admin_money_payments(client: TestClient):
    player = create_user(client)
    authenticate_as(player["id"])
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
        f"/admin/money/refunds?q={booking['id']}&refund_status=all"
    )
    payment_response = client.get(
        f"/admin/money/refunds?payment_id={payment['id']}&refund_status=all"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert {item["id"] for item in body["items"]} == {failed_refund["id"]}
    row = body["items"][0]
    assert row["payment_id"] == payment["id"]
    assert row["booking_id"] == booking["id"]
    assert row["refund_status"] == "failed"
    assert set(row) == {
        "id",
        "payment_id",
        "booking_id",
        "participant_id",
        "host_publish_fee_id",
        "game_id",
        "target_user_id",
        "origin_workflow",
        "provider",
        "provider_refund_id",
        "provider_charge_id",
        "provider_status",
        "provider_status_observed_at",
        "amount_cents",
        "currency",
        "refund_reason",
        "refund_status",
        "requested_by_user_id",
        "approved_by_user_id",
        "requested_at",
        "approved_at",
        "refunded_at",
        "last_refund_event_at",
        "linked_issue",
        "display",
        "created_at",
        "updated_at",
    }
    assert row["game_id"] == game["id"]
    assert row["target_user_id"] == player["id"]

    assert booking_response.status_code == 200, booking_response.text
    booking_refund_ids = {item["id"] for item in booking_response.json()["items"]}
    assert failed_refund["id"] in booking_refund_ids
    assert processing_refund["id"] in booking_refund_ids
    assert other_refund["id"] not in booking_refund_ids

    assert payment_response.status_code == 200, payment_response.text
    payment_refund_ids = {item["id"] for item in payment_response.json()["items"]}
    assert payment_refund_ids == {failed_refund["id"], processing_refund["id"]}


def test_admin_money_refund_list_rejects_removed_created_window_filter(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    created_from = (
        datetime(2026, 1, 4, tzinfo=UTC).isoformat().replace("+00:00", "Z")
    )

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/refunds?created_from={created_from}")

    assert response.status_code == 400, response.text


def test_admin_money_refund_list_omits_resolved_issue_and_rejects_issue_filter(
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
        amount_cents=500,
        refund_status="failed",
    )

    with SessionLocal() as db:
        db_payment = db.get(Payment, UUID(payment["id"]))
        db_refund = db.get(Refund, UUID(refund["id"]))
        assert db_payment is not None
        assert db_refund is not None
        money_issue = stage_refund_money_issue(
            db,
            refund=db_refund,
            payment=db_payment,
            issue_type="refund_failed",
            reason_code="stripe_refund_failed",
            summary="Stripe reported the refund failed.",
            now=datetime.now(UTC),
        )
        money_issue_id = str(money_issue.id)
        db.commit()

    authenticate_as(admin["id"])
    resolve_response = client.post(
        f"/admin/money/issues/{money_issue_id}/resolve",
        json={
            "resolution_reason_code": "invalid_issue",
            "resolution_note": "Duplicate issue created during setup.",
            "idempotency_key": f"resolve-refund-list-issue-{unique_suffix()}",
        },
    )
    response = client.get(
        f"/admin/money/refunds?payment_id={payment['id']}"
    )
    rejected_filter_response = client.get(
        f"/admin/money/refunds?payment_id={payment['id']}&issue_status=resolved"
    )

    assert resolve_response.status_code == 200, resolve_response.text
    assert response.status_code == 200, response.text
    rows = response.json()["items"]
    assert {item["id"] for item in rows} == {refund["id"]}
    assert rows[0]["linked_issue"] is None
    assert rejected_filter_response.status_code == 400, rejected_filter_response.text


def test_admin_money_refund_list_rejects_bad_status(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get("/admin/money/refunds?refund_status=settled")

    assert response.status_code == 400, response.text


def test_admin_money_refund_detail_returns_structured_actions(client: TestClient):
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
        refund_status="failed",
        provider_refund_id=f"re_{unique_suffix()}",
        provider_charge_id=payment["provider_charge_id"],
    )

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/refunds/{refund['id']}")

    assert response.status_code == 200, response.text
    actions = {
        action["action_code"]: action
        for action in response.json()["available_actions"]
    }
    assert actions["retry_refund"]["enabled"] is True
    assert actions["retry_refund"]["blockers"] == []
    assert actions["check_provider_status"]["enabled"] is True
    assert set(actions) == {
        "retry_refund",
        "check_provider_status",
        "open_provider_reference",
        "open_money_issue",
    }


def test_player_cannot_list_admin_money_refunds(client: TestClient):
    player = create_user(client)
    authenticate_as(player["id"])
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
        money_issue = create_refund_money_issue_for_test(
            db,
            refund_id=refund["id"],
            issue_type="refund_processing_overdue",
        )
        money_issue_id = str(money_issue.id)
        db.commit()

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/payments/{payment['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["payment"]["id"] == payment["id"]
    assert body["payment"]["booking_id"] == booking["id"]
    assert body["payment"]["payment_status"] == "succeeded"
    assert body["payment"]["provider_charge_id"] == payment["provider_charge_id"]
    assert body["payment"]["idempotency_key"] == payment["idempotency_key"]
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
    assert money_issue_id in {item["id"] for item in body["linked_money_issues"]}
    assert any(
        action["action_type"] == "create_payment"
        and action["target_payment_id"] == payment["id"]
        for action in body["admin_actions"]
    )
    assert any(
        action["action_type"] == "issue_credit"
        and action["target_game_credit_id"] == credit["id"]
        for action in body["admin_actions"]
    )
    assert all("idempotency_key" not in action for action in body["admin_actions"])


def test_admin_payment_detail_orders_open_linked_issues_first(
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
    open_refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=300,
        refund_status="failed",
    )
    resolved_refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=200,
        refund_status="failed",
    )

    with SessionLocal() as db:
        open_issue = create_refund_money_issue_for_test(
            db,
            refund_id=open_refund["id"],
            issue_type="refund_failed",
            reason_code="open_refund_issue",
        )
        resolved_issue = create_refund_money_issue_for_test(
            db,
            refund_id=resolved_refund["id"],
            issue_type="refund_failed",
            reason_code="resolved_refund_issue",
        )
        later = datetime.now(UTC) + timedelta(minutes=5)
        resolved_issue.status = "resolved"
        resolved_issue.resolved_at = later
        resolved_issue.resolved_by_user_id = UUID(admin["id"])
        resolved_issue.resolution_reason_code = "invalid_issue"
        resolved_issue.resolution_note = "Resolved test issue."
        resolved_issue.last_activity_at = later
        resolved_issue.updated_at = later
        open_issue_id = str(open_issue.id)
        resolved_issue_id = str(resolved_issue.id)
        db.commit()

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/payments/{payment['id']}")

    assert response.status_code == 200, response.text
    issue_ids = [item["id"] for item in response.json()["linked_money_issues"]]
    assert open_issue_id in issue_ids
    assert resolved_issue_id in issue_ids
    assert issue_ids.index(open_issue_id) < issue_ids.index(resolved_issue_id)


def test_admin_payment_detail_includes_publish_fee_context(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    host, game, payment, host_publish_fee = create_paid_publish_fee_setup(client)

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/payments/{payment['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["booking"] is None
    assert body["game"]["id"] == game["id"]
    assert body["payer"]["id"] == host["id"]
    assert body["payer"]["email"] == host["email"]
    assert body["host_publish_fee"]["id"] == host_publish_fee["id"]
    assert body["host_publish_fee"]["payment_id"] == payment["id"]
    assert body["publish_host"]["id"] == host["id"]
    assert body["publish_host"]["email"] == host["email"]
    assert body["community_publish_attempt"] is None


def test_admin_payment_detail_includes_publish_attempt_context(client: TestClient):
    admin = create_user(client)
    host = create_user(client)
    set_user_role(admin["id"], "admin")
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
        payment_status="processing",
        provider_charge_id=f"ch_{unique_suffix()}",
        idempotency_key=f"publish-attempt-payment-{unique_suffix()}",
    )
    with SessionLocal() as db:
        publish_attempt = CommunityPublishAttempt(
            id=uuid4(),
            host_user_id=UUID(host["id"]),
            payment_id=UUID(payment["id"]),
            created_game_id=None,
            attempt_status="processing",
            publish_payload={},
            starts_on_local=datetime.now(UTC).date(),
            amount_cents=499,
            currency="USD",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(publish_attempt)
        db.commit()
        publish_attempt_id = str(publish_attempt.id)

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/payments/{payment['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["host_publish_fee"] is None
    assert body["payer"]["id"] == host["id"]
    assert body["payer"]["email"] == host["email"]
    assert body["community_publish_attempt"]["id"] == publish_attempt_id
    assert body["community_publish_attempt"]["payment_id"] == payment["id"]
    assert body["publish_host"]["id"] == host["id"]


def test_player_cannot_get_payment_detail(client: TestClient):
    player = create_user(client)
    venue = create_venue(client, player["id"])
    game = create_game(client, player["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(client, player["id"], booking_id=booking["id"])

    authenticate_as(player["id"])
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
        money_issue = create_refund_money_issue_for_test(
            db,
            refund_id=refund["id"],
            issue_type="refund_processing_overdue",
        )
        money_issue_id = str(money_issue.id)
        db.commit()

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/refunds/{refund['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["refund"]["id"] == refund["id"]
    assert body["refund"]["payment_id"] == payment["id"]
    assert body["refund"]["refund_status"] == "processing"
    assert body["refund"]["provider_refund_id"] == refund["provider_refund_id"]
    assert body["current_provider_snapshot"]["provider_refund_id"] == (
        refund["provider_refund_id"]
    )
    assert body["payment_summary"]["id"] == payment["id"]
    assert body["payment_summary"]["provider_charge_id"] == payment["provider_charge_id"]
    assert body["user_summary"]["id"] == player["id"]
    assert body["booking_summary"]["id"] == booking["id"]
    assert body["game_summary"]["id"] == game["id"]
    assert credit["id"] in {
        item["id"] for item in body["credit_context"]["credit_grants"]
    }
    assert other_credit["id"] not in {
        item["id"] for item in body["credit_context"]["credit_grants"]
    }
    assert other_refund["id"] != body["refund"]["id"]
    assert usage_id in {
        item["id"] for item in body["credit_context"]["credit_usages"]
    }
    assert other_usage_id not in {
        item["id"] for item in body["credit_context"]["credit_usages"]
    }
    assert body["linked_money_issue"]["id"] == money_issue_id
    assert any(
        event["reason_code"] == "refund_route_create"
        for event in body["recent_refund_events"]
    )


def test_player_cannot_get_refund_detail(client: TestClient):
    player = create_user(client)
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

    authenticate_as(player["id"])
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
    assert body["payment_summary"]["payment_status"] == "succeeded"
    assert body["booking_summary"]["payment_status"] == "refunded"
    assert body["linked_money_issue"] is None
    provider_event = next(
        event
        for event in body["recent_refund_events"]
        if event["event_type"] == "provider_result_recorded"
        and event["new_refund_status"] == "succeeded"
    )
    assert provider_event["idempotency_key"] is None
    assert (provider_event["metadata"] or {}).get("admin_reason") is None
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


def test_admin_refund_retry_failure_creates_money_issue(
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
    with SessionLocal() as db:
        money_issue = create_refund_money_issue_for_test(
            db,
            refund_id=refund["id"],
        )
        money_issue_id = str(money_issue.id)
        db.commit()
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
    assert body["payment_summary"]["payment_status"] == "succeeded"
    assert body["booking_summary"]["payment_status"] == "paid"
    assert body["linked_money_issue"]["issue_type"] == "refund_failed"
    assert body["linked_money_issue"]["status"] == "open"
    assert any(
        event["event_type"] == "provider_result_recorded"
        and event["new_refund_status"] == "failed"
        for event in body["recent_refund_events"]
    )


def test_admin_refund_retry_processing_records_refund_event(
    client: TestClient, monkeypatch
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
    with SessionLocal() as db:
        money_issue = create_refund_money_issue_for_test(
            db,
            refund_id=refund["id"],
        )
        money_issue_id = str(money_issue.id)
        db.commit()
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
    assert body["payment_summary"]["payment_status"] == "succeeded"
    assert body["booking_summary"]["payment_status"] == "paid"
    assert body["linked_money_issue"]["id"] == money_issue_id
    assert body["linked_money_issue"]["recommended_action_code"] == (
        "verify_provider_refund"
    )
    assert any(
        event["event_type"] == "provider_result_recorded"
        and event["new_refund_status"] == "processing"
        for event in body["recent_refund_events"]
    )
    with SessionLocal() as db:
        linked_event = db.scalars(
            select(MoneyIssueEvent).where(
                MoneyIssueEvent.money_issue_id == UUID(money_issue_id),
                MoneyIssueEvent.event_type == "refund_outcome_linked",
                MoneyIssueEvent.reason_code == "admin_retry_processing",
            )
        ).first()
        assert linked_event is not None
        assert linked_event.event_source == "admin"


def test_admin_refund_reconcile_records_terminal_provider_result(
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
        refund_status="processing",
    )

    def fake_retrieve_refund(provider_refund_id):
        return StripeRefundResult(
            id=provider_refund_id,
            status="succeeded",
            amount_cents=500,
            currency="USD",
            charge_id=payment["provider_charge_id"],
            payment_intent_id=payment["provider_payment_intent_id"],
        )

    monkeypatch.setattr(
        "backend.services.admin_money_refund_service.retrieve_stripe_refund",
        fake_retrieve_refund,
    )

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/money/refunds/{refund['id']}/reconcile",
        json={
            "reason": "Check provider status.",
            "idempotency_key": f"admin-money-reconcile-succeeded-{unique_suffix()}",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["refund"]["refund_status"] == "succeeded"
    assert any(
        event["event_type"] == "provider_result_recorded"
        and event["event_source"] == "reconciliation"
        and event["new_refund_status"] == "succeeded"
        for event in body["recent_refund_events"]
    )


def test_admin_refund_reconcile_processing_before_threshold_does_not_open_issue(
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
        refund_status="processing",
    )

    with SessionLocal() as db:
        db_refund = db.get(Refund, UUID(refund["id"]))
        assert db_refund is not None
        recent = datetime.now(UTC) - timedelta(hours=1)
        db_refund.requested_at = recent
        db_refund.approved_at = recent
        db_refund.created_at = recent
        db_refund.updated_at = recent
        db.commit()

    def fake_retrieve_refund(provider_refund_id):
        return StripeRefundResult(
            id=provider_refund_id,
            status="processing",
            amount_cents=500,
            currency="USD",
            charge_id=payment["provider_charge_id"],
            payment_intent_id=payment["provider_payment_intent_id"],
        )

    monkeypatch.setattr(
        "backend.services.admin_money_refund_service.retrieve_stripe_refund",
        fake_retrieve_refund,
    )

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/money/refunds/{refund['id']}/reconcile",
        json={
            "reason": "Check provider status before threshold.",
            "idempotency_key": f"admin-money-reconcile-fresh-{unique_suffix()}",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["refund"]["refund_status"] == "processing"
    assert body["linked_money_issue"] is None


def test_admin_refund_reconcile_processing_after_threshold_opens_overdue_issue(
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
        refund_status="processing",
    )

    with SessionLocal() as db:
        db_refund = db.get(Refund, UUID(refund["id"]))
        assert db_refund is not None
        old = datetime.now(UTC) - timedelta(hours=25)
        db_refund.requested_at = old
        db_refund.approved_at = old
        db_refund.created_at = old
        db_refund.updated_at = old
        for refund_event in db.scalars(
            select(RefundEvent).where(RefundEvent.refund_id == db_refund.id)
        ).all():
            refund_event.occurred_at = old
            refund_event.created_at = old
        db.commit()

    def fake_retrieve_refund(provider_refund_id):
        return StripeRefundResult(
            id=provider_refund_id,
            status="processing",
            amount_cents=500,
            currency="USD",
            charge_id=payment["provider_charge_id"],
            payment_intent_id=payment["provider_payment_intent_id"],
        )

    monkeypatch.setattr(
        "backend.services.admin_money_refund_service.retrieve_stripe_refund",
        fake_retrieve_refund,
    )

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/money/refunds/{refund['id']}/reconcile",
        json={
            "reason": "Check overdue provider status.",
            "idempotency_key": f"admin-money-reconcile-overdue-{unique_suffix()}",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["refund"]["refund_status"] == "processing"
    assert body["linked_money_issue"]["issue_type"] == "refund_processing_overdue"
    assert body["linked_money_issue"]["latest_reason_code"] == (
        "processing_threshold_reached"
    )
    assert any(
        event["event_type"] == "reconciliation_checked"
        and event["reason_code"] == "processing_threshold_reached"
        for event in body["recent_refund_events"]
    )


def test_admin_refund_reconcile_missing_provider_reference_records_unknown(
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
        provider_refund_id=None,
        amount_cents=500,
        refund_status="processing",
    )

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/money/refunds/{refund['id']}/reconcile",
        json={
            "reason": "Check provider status without stored provider reference.",
            "idempotency_key": f"admin-money-reconcile-missing-{unique_suffix()}",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["linked_money_issue"]["issue_type"] == (
        "refund_missing_provider_reference"
    )
    assert any(
        event["event_type"] == "provider_outcome_unknown"
        and event["event_source"] == "reconciliation"
        for event in body["recent_refund_events"]
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
    assert body["payment_summary"]["payment_status"] == "succeeded"
    assert body["booking_summary"]["payment_status"] == "partially_refunded"
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
        retry_issues = db.scalars(
            select(MoneyIssue).where(MoneyIssue.target_refund_id == UUID(refund["id"]))
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
    assert retry_issues == []


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
        db_payment.payment_status = "processing"
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


def test_admin_refund_retry_rejects_uncertain_provider_outcome_before_stripe(
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
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        refund_status="failed",
        provider_refund_id=f"re_{unique_suffix()}",
        provider_status="processing",
        provider_status_observed_at=datetime.now(UTC).isoformat(),
        provider_charge_id=payment["provider_charge_id"],
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

    authenticate_as(admin["id"])
    detail_response = client.get(f"/admin/money/refunds/{refund['id']}")
    retry_response = client.post(
        f"/admin/money/refunds/{refund['id']}/retry",
        json={
            "reason": "Provider result is still uncertain.",
            "idempotency_key": f"admin-money-retry-uncertain-{unique_suffix()}",
        },
    )

    assert detail_response.status_code == 200, detail_response.text
    actions = {
        action["action_code"]: action
        for action in detail_response.json()["available_actions"]
    }
    assert actions["retry_refund"]["enabled"] is False
    assert (
        "Refund provider outcome is still uncertain."
        in actions["retry_refund"]["blockers"]
    )
    assert retry_response.status_code == 400, retry_response.text
    assert (
        retry_response.json()["detail"]
        == "Refund provider outcome is still uncertain. Check provider status before retrying."
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


def test_player_cannot_retry_admin_money_refund(client: TestClient):
    player = create_user(client)
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

    authenticate_as(player["id"])
    response = client.post(
        f"/admin/money/refunds/{refund['id']}/retry",
        json={
            "reason": "Player cannot retry money refunds.",
            "idempotency_key": f"admin-money-retry-player-{unique_suffix()}",
        },
    )

    assert response.status_code == 403, response.text


def test_admin_financial_outcome_refunds_publish_fee(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    host, game, payment, host_publish_fee = create_paid_publish_fee_setup(client)
    provider_refund_id = f"re_{unique_suffix()}"
    stripe_calls = []

    def fake_create_refund(**kwargs):
        stripe_calls.append(kwargs)
        return StripeRefundResult(
            id=provider_refund_id,
            status="succeeded",
            amount_cents=499,
            currency="USD",
            charge_id=payment["provider_charge_id"],
            payment_intent_id=payment["provider_payment_intent_id"],
        )

    monkeypatch.setattr(
        "backend.services.admin_financial_outcome_service.create_stripe_refund",
        fake_create_refund,
    )

    payload = {
        "outcome": "refund",
        "reason": "Refund publish fee after admin review.",
        "idempotency_key": f"publish-fee-refund-{unique_suffix()}",
        "host_publish_fee_id": host_publish_fee["id"],
    }

    authenticate_as(admin["id"])
    response = client.post("/admin/money/financial-outcomes", json=payload)
    duplicate_response = client.post("/admin/money/financial-outcomes", json=payload)

    assert response.status_code == 201, response.text
    assert duplicate_response.status_code == 201, duplicate_response.text
    assert len(stripe_calls) == 1
    assert stripe_calls[0]["charge_id"] == payment["provider_charge_id"]
    assert stripe_calls[0]["amount_cents"] == 499
    assert stripe_calls[0]["metadata"]["source"] == (
        "community_publish_fee_financial_outcome"
    )

    body = duplicate_response.json()
    assert body["outcome"] == "refund"
    assert body["applied_status"] == "applied"
    assert body["host_user_id"] == host["id"]
    assert body["host_publish_fee_id"] == host_publish_fee["id"]
    assert body["payment_id"] == payment["id"]
    assert body["refund_id"] is not None
    assert body["amount_cents"] == 499

    with SessionLocal() as db:
        db_refund = db.get(Refund, UUID(body["refund_id"]))
        db_payment = db.get(Payment, UUID(payment["id"]))
        db_fee = db.get(HostPublishFee, UUID(host_publish_fee["id"]))
        notice = db.scalar(
            select(AdminTargetNotice).where(
                AdminTargetNotice.notice_type == "publish_fee_refunded",
                AdminTargetNotice.recipient_user_id == UUID(host["id"]),
                AdminTargetNotice.target_game_id == UUID(game["id"]),
            )
        )
        notification = (
            db.scalar(
                select(Notification).where(
                    Notification.user_id == UUID(host["id"]),
                    Notification.notification_type == "admin_notice",
                    Notification.title == "Publish fee refunded",
                )
            )
            if notice is not None
            else None
        )
        actions = db.scalars(
            select(AdminAction).where(
                AdminAction.target_financial_outcome_id == UUID(body["id"])
            )
        ).all()

    assert db_refund is not None
    assert db_refund.host_publish_fee_id == UUID(host_publish_fee["id"])
    assert db_refund.provider_refund_id == provider_refund_id
    assert db_refund.refund_reason == "publish_fee_refund"
    assert db_refund.refund_status == "succeeded"
    assert db_payment is not None
    assert db_payment.payment_status == "succeeded"
    assert db_fee is not None
    assert db_fee.fee_status == "refunded"
    assert notice is not None
    assert str(notice.admin_action_id) == body["admin_action_id"]
    assert notice.notice_metadata["financial_outcome_id"] == body["id"]
    assert notification is not None
    assert notification.aggregation_key == f"admin_target_notice:{notice.id}"
    assert {action.action_type for action in actions} == {
        "create_financial_outcome",
        "apply_financial_outcome",
    }

    list_response = client.get(
        f"/admin/money/refunds?q={host_publish_fee['id']}"
    )
    assert list_response.status_code == 200, list_response.text
    assert {item["id"] for item in list_response.json()["items"]} == {
        body["refund_id"]
    }


def test_admin_financial_outcome_credit_creates_publish_entitlement(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    host, game, payment, host_publish_fee = create_paid_publish_fee_setup(client)

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/money/financial-outcomes",
        json={
            "outcome": "credit",
            "reason": "Give the host a replacement publish credit.",
            "idempotency_key": f"publish-fee-credit-{unique_suffix()}",
            "host_publish_fee_id": host_publish_fee["id"],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["outcome"] == "credit"
    assert body["applied_status"] == "applied"
    assert body["host_user_id"] == host["id"]
    assert body["host_publish_fee_id"] == host_publish_fee["id"]
    assert body["payment_id"] == payment["id"]
    assert body["host_publish_entitlement_id"] is not None

    entitlement_id = UUID(body["host_publish_entitlement_id"])
    with SessionLocal() as db:
        entitlement = db.get(HostPublishEntitlement, entitlement_id)
        outcome = db.get(AdminFinancialOutcome, UUID(body["id"]))
        apply_action = db.scalar(
            select(AdminAction).where(
                AdminAction.action_type == "apply_financial_outcome",
                AdminAction.target_financial_outcome_id == UUID(body["id"]),
                AdminAction.target_host_publish_entitlement_id == entitlement_id,
            )
        )
        notice = db.scalar(
            select(AdminTargetNotice).where(
                AdminTargetNotice.notice_type == "publish_credit_added",
                AdminTargetNotice.recipient_user_id == UUID(host["id"]),
                AdminTargetNotice.target_game_id == UUID(game["id"]),
            )
        )
        notification = (
            db.scalar(
                select(Notification).where(
                    Notification.user_id == UUID(host["id"]),
                    Notification.notification_type == "admin_notice",
                    Notification.title == "Publish credit added",
                )
            )
            if notice is not None
            else None
        )

    assert entitlement is not None
    assert entitlement.host_user_id == UUID(host["id"])
    assert entitlement.entitlement_type == "refund_replacement"
    assert entitlement.status == "available"
    assert entitlement.source == "financial_outcome"
    assert entitlement.source_financial_outcome_id == UUID(body["id"])
    assert entitlement.source_admin_action_id is not None
    assert outcome is not None
    assert outcome.host_publish_entitlement_id == entitlement.id
    assert apply_action is not None
    assert notice is not None
    assert str(notice.admin_action_id) == body["admin_action_id"]
    assert notice.notice_metadata["financial_outcome_id"] == body["id"]
    assert notification is not None
    assert notification.aggregation_key == f"admin_target_notice:{notice.id}"


def test_admin_financial_outcome_processing_refund_records_pending_refund(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    _host, _game, payment, host_publish_fee = create_paid_publish_fee_setup(client)
    provider_refund_id = f"re_{unique_suffix()}"

    def fake_create_refund(**kwargs):
        return StripeRefundResult(
            id=provider_refund_id,
            status="processing",
            amount_cents=499,
            currency="USD",
            charge_id=payment["provider_charge_id"],
            payment_intent_id=payment["provider_payment_intent_id"],
        )

    monkeypatch.setattr(
        "backend.services.admin_financial_outcome_service.create_stripe_refund",
        fake_create_refund,
    )

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/money/financial-outcomes",
        json={
            "outcome": "refund",
            "reason": "Refund is pending Stripe completion.",
            "idempotency_key": f"publish-fee-processing-{unique_suffix()}",
            "host_publish_fee_id": host_publish_fee["id"],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["outcome"] == "refund"
    assert body["applied_status"] == "pending"

    with SessionLocal() as db:
        refund = db.get(Refund, UUID(body["refund_id"]))
        money_issue = db.scalar(
            select(MoneyIssue).where(
                MoneyIssue.target_refund_id == UUID(body["refund_id"]),
            )
        )

    assert refund is not None
    assert refund.provider_refund_id == provider_refund_id
    assert refund.refund_status == "processing"
    assert money_issue is None


def test_admin_can_list_money_issues(client: TestClient):
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
        refund_status="failed",
    )

    with SessionLocal() as db:
        money_issue = create_refund_money_issue_for_test(
            db,
            refund_id=refund["id"],
        )
        money_issue_id = str(money_issue.id)
        db.commit()

    authenticate_as(admin["id"])
    response = client.get("/admin/money/issues?status=open")

    assert response.status_code == 200, response.text
    body = response.json()
    assert money_issue_id in {item["id"] for item in body["items"]}
    row = next(item for item in body["items"] if item["id"] == money_issue_id)
    assert row["issue_type"] == "refund_failed"
    assert row["status"] == "open"
    assert row["target_refund_id"] == refund["id"]
    assert row["display"]["user_email"] == player["email"]
    assert row["display"]["game_label"] == game["title"]
    assert row["display"]["context_label"].startswith("Booking ")
    assert row["last_activity_at"] is not None
    assert "metadata" not in row


def test_admin_money_issue_search_uses_controlled_lookup_paths(client: TestClient):
    admin = create_user(client)
    player = create_user(
        client,
        email=f"money-issue-search-{unique_suffix()}@example.com",
        first_name="MoneyIssue",
        last_name="Searchable",
    )
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(
        client,
        admin["id"],
        venue,
        title=f"ProviderSearchGame{unique_suffix()}",
    )
    booking = create_booking(client, player["id"], game["id"])
    provider_charge_id = f"ch_issue_search_{unique_suffix()}"
    provider_refund_id = f"re_issue_search_{unique_suffix()}"
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        payment_status="succeeded",
        provider_charge_id=provider_charge_id,
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        refund_status="failed",
        provider_refund_id=provider_refund_id,
        provider_charge_id=provider_charge_id,
    )

    with SessionLocal() as db:
        money_issue = create_refund_money_issue_for_test(
            db,
            refund_id=refund["id"],
        )
        money_issue_id = str(money_issue.id)
        operation_key = money_issue.operation_key
        db.commit()

    authenticate_as(admin["id"])
    issue_id_response = client.get(f"/admin/money/issues?q={money_issue_id}")
    operation_key_response = client.get(f"/admin/money/issues?q={operation_key}")
    user_id_response = client.get(f"/admin/money/issues?q={player['id']}")
    user_email_response = client.get(f"/admin/money/issues?q={player['email']}")
    game_response = client.get(f"/admin/money/issues?q={game['title']}")
    refund_response = client.get(f"/admin/money/issues?q={provider_refund_id}")
    charge_response = client.get(f"/admin/money/issues?q={provider_charge_id}")

    assert issue_id_response.status_code == 200, issue_id_response.text
    assert operation_key_response.status_code == 200, operation_key_response.text
    assert user_id_response.status_code == 200, user_id_response.text
    assert user_email_response.status_code == 200, user_email_response.text
    assert game_response.status_code == 200, game_response.text
    assert refund_response.status_code == 200, refund_response.text
    assert charge_response.status_code == 200, charge_response.text
    assert money_issue_id in {item["id"] for item in issue_id_response.json()["items"]}
    assert money_issue_id in {
        item["id"] for item in operation_key_response.json()["items"]
    }
    assert money_issue_id in {item["id"] for item in user_id_response.json()["items"]}
    assert money_issue_id in {
        item["id"] for item in user_email_response.json()["items"]
    }
    assert money_issue_id not in {item["id"] for item in game_response.json()["items"]}
    assert money_issue_id not in {item["id"] for item in refund_response.json()["items"]}
    assert money_issue_id not in {item["id"] for item in charge_response.json()["items"]}


def test_admin_money_issue_list_rejects_bad_status(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get("/admin/money/issues?status=closed")

    assert response.status_code == 400, response.text


def test_admin_money_issue_list_rejects_bad_issue_type(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get("/admin/money/issues?issue_type=refund_anything")

    assert response.status_code == 400, response.text


def test_admin_money_issue_list_rejects_removed_filters(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/issues?game_id={uuid4()}")

    assert response.status_code == 400, response.text


def test_admin_can_get_money_issue_detail(client: TestClient):
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
        refund_status="failed",
    )

    with SessionLocal() as db:
        money_issue = create_refund_money_issue_for_test(
            db,
            refund_id=refund["id"],
        )
        refund_event = db.scalars(
            select(RefundEvent)
            .where(RefundEvent.refund_id == UUID(refund["id"]))
            .order_by(RefundEvent.occurred_at.desc(), RefundEvent.id.desc())
        ).first()
        assert refund_event is not None
        refund_event_id = str(refund_event.id)
        money_issue_id = str(money_issue.id)
        db.commit()

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/issues/{money_issue_id}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["money_issue"]["id"] == money_issue_id
    assert body["money_issue"]["issue_type"] == "refund_failed"
    assert body["refund"]["id"] == refund["id"]
    assert body["payment"]["id"] == payment["id"]
    assert body["booking"]["id"] == booking["id"]
    assert body["game"]["id"] == game["id"]
    assert refund_event_id in {
        event["id"] for event in body["recent_refund_events"]
    }
    assert any(event["event_type"] == "issue_opened" for event in body["events"])


def test_admin_can_resolve_money_issue_without_mutating_refund_truth(client: TestClient):
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
        refund_status="failed",
    )

    with SessionLocal() as db:
        money_issue = create_refund_money_issue_for_test(
            db,
            refund_id=refund["id"],
        )
        money_issue_id = str(money_issue.id)
        db.commit()

    authenticate_as(admin["id"])
    payload = {
        "resolution_reason_code": "handled_externally",
        "resolution_note": "Stripe refund was handled outside Pickup Lane.",
        "resolution_external_reference": "stripe-dashboard-case-1",
        "idempotency_key": f"admin-money-issue-resolve-{unique_suffix()}",
    }
    response = client.post(
        f"/admin/money/issues/{money_issue_id}/resolve",
        json=payload,
    )
    duplicate_response = client.post(
        f"/admin/money/issues/{money_issue_id}/resolve",
        json=payload,
    )

    assert response.status_code == 200, response.text
    assert duplicate_response.status_code == 200, duplicate_response.text
    body = duplicate_response.json()
    assert body["money_issue"]["id"] == money_issue_id
    assert body["money_issue"]["status"] == "resolved"
    assert body["money_issue"]["resolution_reason_code"] == "handled_externally"
    assert body["money_issue"]["resolution_external_reference"] == "stripe-dashboard-case-1"
    assert body["refund"]["refund_status"] == "failed"
    assert body["payment"]["payment_status"] == "succeeded"
    assert body["booking"]["payment_status"] == "paid"
    assert sum(event["event_type"] == "issue_resolved" for event in body["events"]) == 1


def test_admin_money_issue_handled_externally_requires_note(client: TestClient):
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
        refund_status="failed",
    )

    with SessionLocal() as db:
        money_issue = create_refund_money_issue_for_test(
            db,
            refund_id=refund["id"],
        )
        money_issue_id = str(money_issue.id)
        db.commit()

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/money/issues/{money_issue_id}/resolve",
        json={
            "resolution_reason_code": "handled_externally",
            "resolution_external_reference": "stripe-dashboard-case-2",
            "idempotency_key": f"admin-money-issue-resolve-{unique_suffix()}",
        },
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "handled_externally requires resolution_note."


def test_player_cannot_read_or_resolve_money_issues(client: TestClient):
    player = create_user(client)
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
        money_issue = create_refund_money_issue_for_test(
            db,
            refund_id=refund["id"],
        )
        money_issue_id = str(money_issue.id)
        db.commit()

    authenticate_as(player["id"])
    list_response = client.get("/admin/money/issues")
    detail_response = client.get(f"/admin/money/issues/{money_issue_id}")
    resolve_response = client.post(
        f"/admin/money/issues/{money_issue_id}/resolve",
        json={
            "resolution_reason_code": "handled_externally",
            "idempotency_key": f"admin-money-issue-player-{unique_suffix()}",
        },
    )

    assert list_response.status_code == 403, list_response.text
    assert detail_response.status_code == 403, detail_response.text
    assert resolve_response.status_code == 403, resolve_response.text


def test_admin_money_issue_detail_missing_issue_returns_404(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get(
        "/admin/money/issues/00000000-0000-0000-0000-000000000000"
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
    body = response.json()["items"]
    ids = {item["id"] for item in body}
    assert credit["id"] in ids
    assert other_credit["id"] not in ids

    credit_row = next(item for item in body if item["id"] == credit["id"])
    assert credit_row["user_id"] == player["id"]
    assert credit_row["available_cents"] == 700
    assert credit_row["open_money_issue_count"] == 0
    assert set(credit_row) == {
        "id",
        "user_id",
        "amount_cents",
        "available_cents",
        "reserved_cents",
        "currency",
        "credit_status",
        "credit_reason",
        "source_game_id",
        "source_booking_id",
        "source_payment_id",
        "reversed_at",
        "open_money_issue_count",
        "display",
        "created_at",
    }

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
    assert {item["id"] for item in game_response.json()["items"]} == {
        credit["id"],
        other_credit["id"],
    }
    assert booking_response.status_code == 200, booking_response.text
    assert {item["id"] for item in booking_response.json()["items"]} == {
        credit["id"]
    }
    assert payment_response.status_code == 200, payment_response.text
    assert {item["id"] for item in payment_response.json()["items"]} == {
        credit["id"]
    }


def test_admin_money_credit_search_finds_usage_id(client: TestClient):
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
            idempotency_scope=f"admin-money-credit-search:{booking['id']}",
        )
        usage_id = str(usages[0].id)
        db.commit()

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/credits?q={usage_id}")

    assert response.status_code == 200, response.text
    assert {item["id"] for item in response.json()["items"]} == {credit["id"]}


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
        money_issue = create_credit_money_issue_for_test(
            db,
            credit_usage_id=usage_id,
        )
        money_issue_id = str(money_issue.id)
        restore_money_issue = create_credit_money_issue_for_test(
            db,
            credit_usage_id=usage_id,
            issue_type="credit_restore_failed",
            reason_code="test_credit_restore_issue",
        )
        restore_money_issue_id = str(restore_money_issue.id)
        refund_money_issue = create_refund_money_issue_for_test(
            db,
            refund_id=refund["id"],
            issue_type="refund_failed",
            reason_code="same_booking_refund_issue",
        )
        refund_money_issue_id = str(refund_money_issue.id)
        other_money_issue = create_credit_money_issue_for_test(
            db,
            credit_usage_id=other_usage_id,
        )
        other_money_issue_id = str(other_money_issue.id)
        db.commit()

    authenticate_as(admin["id"])
    response = client.get(f"/admin/money/credits/{credit['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["credit"]["id"] == credit["id"]
    assert body["credit"]["user_id"] == player["id"]
    assert body["credit"]["source_payment_id"] == payment["id"]
    assert body["credit"]["open_money_issue_count"] == 2
    assert {item["id"] for item in body["credit_usages"]} == {usage_id}
    assert other_usage_id not in {item["id"] for item in body["credit_usages"]}
    assert {item["id"] for item in body["payments"]} == {payment["id"]}
    assert {item["id"] for item in body["refunds"]} == {refund["id"]}
    assert body["booking"]["id"] == booking["id"]
    assert body["game"]["id"] == game["id"]
    assert {item["id"] for item in body["linked_money_issues"]} == {
        money_issue_id,
        restore_money_issue_id,
    }
    assert refund_money_issue_id not in {
        item["id"] for item in body["linked_money_issues"]
    }
    assert other_money_issue_id not in {
        item["id"] for item in body["linked_money_issues"]
    }
    assert any(
        action["action_type"] == "issue_credit"
        and action["target_game_credit_id"] == credit["id"]
        for action in body["admin_actions"]
    )
    assert other_payment["id"] not in {item["id"] for item in body["payments"]}
    assert other_refund["id"] not in {item["id"] for item in body["refunds"]}


def test_admin_money_issue_credit_release_retry_only_releases_target_usage(
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
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        booking_id=booking["id"],
        payment_id=payment["id"],
        amount_cents=500,
    )
    issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        booking_id=booking["id"],
        payment_id=payment["id"],
        amount_cents=500,
    )

    with SessionLocal() as db:
        usages = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=800,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(payment["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"admin-money-credit-release-target:{booking['id']}",
        )
        target_usage_id = str(usages[0].id)
        target_credit_id = str(usages[0].game_credit_id)
        target_credit_amount = db.get(
            GameCredit,
            usages[0].game_credit_id,
        ).amount_cents
        untouched_usage_id = str(usages[1].id)
        untouched_credit_id = str(usages[1].game_credit_id)
        untouched_available_before = db.get(
            GameCredit,
            usages[1].game_credit_id,
        ).available_cents
        money_issue = create_credit_money_issue_for_test(
            db,
            credit_usage_id=target_usage_id,
            issue_type="credit_release_failed",
        )
        money_issue_id = str(money_issue.id)
        db.commit()

    authenticate_as(admin["id"])
    payload = {
        "reason": "Release only the credit usage tied to this issue.",
        "idempotency_key": f"admin-money-credit-release-{unique_suffix()}",
    }
    response = client.post(
        f"/admin/money/issues/{money_issue_id}/retry-credit",
        json=payload,
    )
    duplicate_response = client.post(
        f"/admin/money/issues/{money_issue_id}/retry-credit",
        json=payload,
    )

    assert response.status_code == 200, response.text
    assert duplicate_response.status_code == 200, duplicate_response.text
    with SessionLocal() as db:
        target_usage = db.get(GameCreditUsage, UUID(target_usage_id))
        untouched_usage = db.get(GameCreditUsage, UUID(untouched_usage_id))
        refreshed_target_credit = db.get(GameCredit, UUID(target_credit_id))
        refreshed_untouched_credit = db.get(GameCredit, UUID(untouched_credit_id))

    assert target_usage.usage_status == "released"
    assert untouched_usage.usage_status == "reserved"
    assert refreshed_target_credit.available_cents == target_credit_amount
    assert refreshed_untouched_credit.available_cents == untouched_available_before


def test_admin_money_issue_credit_retry_failure_records_target_usage(
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
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        booking_id=booking["id"],
        payment_id=payment["id"],
        amount_cents=500,
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
            idempotency_scope=f"admin-money-credit-retry-failure:{booking['id']}",
        )
        target_usage_id = str(usages[0].id)
        money_issue = create_credit_money_issue_for_test(
            db,
            credit_usage_id=target_usage_id,
            issue_type="credit_release_failed",
        )
        money_issue_id = str(money_issue.id)
        db.commit()

    def fail_credit_release(*args, **kwargs):
        del args, kwargs
        raise GameCreditLedgerError("Credit release failed.")

    monkeypatch.setattr(
        "backend.services.admin_money_issue_service.release_reserved_game_credit_usage",
        fail_credit_release,
    )

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/money/issues/{money_issue_id}/retry-credit",
        json={
            "reason": "Retry release and preserve target usage on failure.",
            "idempotency_key": f"admin-money-credit-release-fail-{unique_suffix()}",
        },
    )

    assert response.status_code == 409, response.text
    with SessionLocal() as db:
        admin_action = db.scalars(
            select(AdminAction).where(
                AdminAction.action_type == "retry_money_issue_credit",
                AdminAction.target_money_issue_id == UUID(money_issue_id),
                AdminAction.target_credit_usage_id == UUID(target_usage_id),
            )
        ).one()

    assert admin_action.target_credit_usage_id == UUID(target_usage_id)


def test_admin_money_issue_credit_restore_retry_only_restores_target_usage(
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
        payment_status="succeeded",
        provider_charge_id=f"ch_{unique_suffix()}",
    )
    issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        booking_id=booking["id"],
        payment_id=payment["id"],
        amount_cents=500,
    )
    issue_admin_money_detail_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        booking_id=booking["id"],
        payment_id=payment["id"],
        amount_cents=500,
    )

    with SessionLocal() as db:
        usages = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=800,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(payment["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"admin-money-credit-restore-target:{booking['id']}",
        )
        redeem_reserved_game_credits(
            db,
            UUID(booking["id"]),
            now=datetime.now(UTC),
            user_id=UUID(player["id"]),
        )
        target_usage_id = str(usages[0].id)
        target_credit_id = str(usages[0].game_credit_id)
        target_credit_amount = db.get(
            GameCredit,
            usages[0].game_credit_id,
        ).amount_cents
        untouched_usage_id = str(usages[1].id)
        untouched_credit_id = str(usages[1].game_credit_id)
        untouched_available_before = db.get(
            GameCredit,
            usages[1].game_credit_id,
        ).available_cents
        money_issue = create_credit_money_issue_for_test(
            db,
            credit_usage_id=target_usage_id,
            issue_type="credit_restore_failed",
        )
        money_issue_id = str(money_issue.id)
        db.commit()

    authenticate_as(admin["id"])
    payload = {
        "reason": "Restore only the credit usage tied to this issue.",
        "idempotency_key": f"admin-money-credit-restore-{unique_suffix()}",
    }
    response = client.post(
        f"/admin/money/issues/{money_issue_id}/retry-credit",
        json=payload,
    )
    duplicate_response = client.post(
        f"/admin/money/issues/{money_issue_id}/retry-credit",
        json=payload,
    )

    assert response.status_code == 200, response.text
    assert duplicate_response.status_code == 200, duplicate_response.text
    with SessionLocal() as db:
        restores = db.scalars(
            select(GameCreditUsage).where(
                GameCreditUsage.booking_id == UUID(booking["id"]),
                GameCreditUsage.usage_type == "restore",
            )
        ).all()
        refreshed_target_credit = db.get(GameCredit, UUID(target_credit_id))
        refreshed_untouched_credit = db.get(GameCredit, UUID(untouched_credit_id))

    assert {str(usage.original_usage_id) for usage in restores} == {target_usage_id}
    assert untouched_usage_id not in {str(usage.original_usage_id) for usage in restores}
    assert refreshed_target_credit.available_cents == target_credit_amount
    assert refreshed_untouched_credit.available_cents == untouched_available_before


def test_player_cannot_read_money_credits(client: TestClient):
    player = create_user(client)
    admin = create_user(client)
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

    authenticate_as(player["id"])
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


def test_admin_money_credit_list_rejects_removed_filters(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    reason_response = client.get("/admin/money/credits?credit_reason=admin_credit")
    issue_response = client.get("/admin/money/credits?has_open_issue=true")

    assert reason_response.status_code == 400, reason_response.text
    assert issue_response.status_code == 400, issue_response.text


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
        money_issue = create_refund_money_issue_for_test(
            db,
            refund_id=refund["id"],
        )
        money_issue_id = str(money_issue.id)
        wrong_user_money_issue = create_credit_money_issue_for_test(
            db,
            credit_usage_id=wrong_user_usage_id,
            issue_type="credit_restore_failed",
        )
        wrong_user_money_issue_id = str(wrong_user_money_issue.id)
        db.commit()

    authenticate_as(admin["id"])
    default_response = client.get(f"/admin/money/users/{player['id']}")
    all_cards_response = client.get(
        f"/admin/money/users/{player['id']}?include_inactive_payment_methods=true"
    )

    assert default_response.status_code == 200, default_response.text
    body = default_response.json()
    assert body["user"]["id"] == player["id"]
    assert body["user"]["name"] == "Test User"
    assert body["user"]["email"] == player["email"]
    assert body["user"]["account_status"] == "active"
    assert set(body["user"]) == {
        "id",
        "name",
        "email",
        "account_status",
        "created_at",
    }
    assert "auth_user_id" not in body["user"]
    assert "phone" not in body["user"]
    assert "date_of_birth" not in body["user"]
    assert "stripe_customer_id" not in body["user"]
    assert body["snapshot"]["available_credit_cents"] == 400
    assert body["snapshot"]["open_money_issue_count"] == 1
    assert {item["id"] for item in body["recent_payments"]["items"]} == {
        payment["id"]
    }
    assert other_payment["id"] not in {
        item["id"] for item in body["recent_payments"]["items"]
    }
    assert {item["id"] for item in body["recent_refunds"]["items"]} == {
        refund["id"]
    }
    assert credit["id"] in {item["id"] for item in body["recent_credits"]["items"]}
    assert wrong_user_credit["id"] not in {
        item["id"] for item in body["recent_credits"]["items"]
    }
    payment_preview = body["recent_payments"]["items"][0]
    assert set(payment_preview) == {
        "id",
        "booking_id",
        "game_id",
        "payment_type",
        "amount_cents",
        "currency",
        "payment_status",
        "paid_at",
        "is_fully_refunded",
        "context_label",
        "created_at",
    }
    refund_preview = body["recent_refunds"]["items"][0]
    assert set(refund_preview) == {
        "id",
        "payment_id",
        "booking_id",
        "participant_id",
        "host_publish_fee_id",
        "amount_cents",
        "currency",
        "refund_reason",
        "refund_status",
        "refunded_at",
        "context_label",
        "created_at",
    }
    credit_preview = next(
        item
        for item in body["recent_credits"]["items"]
        if item["id"] == credit["id"]
    )
    assert set(credit_preview) == {
        "id",
        "amount_cents",
        "available_cents",
        "currency",
        "credit_status",
        "credit_reason",
        "source_game_id",
        "source_booking_id",
        "source_payment_id",
        "context_label",
        "created_at",
    }
    assert {item["id"] for item in body["saved_cards"]["items"]} == {
        active_method["id"]
    }
    method_row = body["saved_cards"]["items"][0]
    assert method_row["card_last4"] == "4242"
    assert "stripe_customer_id" not in method_row
    assert "stripe_payment_method_id" not in method_row
    assert "card_fingerprint" not in method_row
    assert money_issue_id in {
        item["id"] for item in body["open_money_issues"]["items"]
    }
    assert wrong_user_money_issue_id not in {
        item["id"] for item in body["open_money_issues"]["items"]
    }
    money_issue_row = next(
        item
        for item in body["open_money_issues"]["items"]
        if item["id"] == money_issue_id
    )
    assert "metadata" not in money_issue_row
    assert "idempotency_key" not in money_issue_row
    assert money_issue_row["target_payment_id"] == payment["id"]
    assert money_issue_row["target_refund_id"] == refund["id"]
    assert money_issue_row["target_game_credit_id"] is None
    assert money_issue_row["target_credit_usage_id"] is None
    assert money_issue_row["first_detected_at"]
    assert money_issue_row["last_detected_at"]

    assert all_cards_response.status_code == 200, all_cards_response.text
    all_card_ids = {
        item["id"]
        for item in all_cards_response.json()["saved_cards"]["items"]
    }
    assert active_method["id"] in all_card_ids
    assert inactive_method["id"] in all_card_ids


def test_player_cannot_read_admin_money_user_summary(client: TestClient):
    player = create_user(client)
    authenticate_as(player["id"])
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


def test_admin_money_user_saved_cards_include_inactive_with_cursor(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
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
    inactive_methods = [
        create_user_payment_method(
            client,
            player["id"],
            card_brand="mastercard",
            card_last4=str(4400 + index),
            exp_month=11,
            exp_year=2031,
            method_status="detached",
            is_default=False,
            detached_at=datetime(2026, 1, index + 1, 3, 4, 5, tzinfo=UTC),
        )
        for index in range(11)
    ]
    other_player = create_user(client)
    other_method = create_user_payment_method(
        client,
        other_player["id"],
        card_brand="discover",
        card_last4="1117",
        is_default=True,
    )

    authenticate_as(admin["id"])
    user_money_path = f"/admin/money/users/{player['id']}"
    active_response = client.get(user_money_path)
    all_response = client.get(
        f"{user_money_path}?include_inactive_payment_methods=true"
    )

    assert active_response.status_code == 200, active_response.text
    active_cards = active_response.json()["saved_cards"]
    assert {item["id"] for item in active_cards["items"]} == {active_method["id"]}
    active_row = active_cards["items"][0]
    assert active_row["card_brand"] == "visa"
    assert active_row["card_last4"] == "4242"
    assert active_row["method_status"] == "active"
    assert "user_id" not in active_row
    assert "stripe_customer_id" not in active_row
    assert "stripe_payment_method_id" not in active_row
    assert "card_fingerprint" not in active_row

    assert all_response.status_code == 200, all_response.text
    saved_cards = all_response.json()["saved_cards"]
    first_page_ids = {item["id"] for item in saved_cards["items"]}
    assert len(saved_cards["items"]) == 10
    assert active_method["id"] in first_page_ids
    assert other_method["id"] not in first_page_ids
    assert saved_cards["has_more"] is True
    assert saved_cards["next_cursor"] is not None

    next_cursor = saved_cards["next_cursor"]
    next_response = client.get(
        f"{user_money_path}?include_inactive_payment_methods=true"
        f"&saved_cards_cursor={next_cursor}"
    )
    assert next_response.status_code == 200, next_response.text
    next_cards = next_response.json()["saved_cards"]
    next_ids = {item["id"] for item in next_cards["items"]}
    assert next_ids
    assert next_ids <= {item["id"] for item in inactive_methods}
