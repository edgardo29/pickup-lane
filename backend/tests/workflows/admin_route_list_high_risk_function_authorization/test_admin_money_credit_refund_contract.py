from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_game_roster_moderation_contract import (
    _persist_community_game_fixture,
    _persist_game_fixture,
)
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    _add_users,
    _auth_headers,
    _client,
    _count_model_rows,
    _install_tokens_for_users,
    _session,
    _user,
)

pytestmark = pytest.mark.suite_type("ordinary")


def _persist_paid_booking(
    *,
    game_id: uuid.UUID,
    buyer_user_id: uuid.UUID,
    amount_cents: int,
) -> uuid.UUID:
    from backend.models import Booking

    with _session() as db:
        booking = Booking(
            id=uuid.uuid4(),
            game_id=game_id,
            buyer_user_id=buyer_user_id,
            booking_status="confirmed",
            payment_status="paid",
            participant_count=1,
            subtotal_cents=amount_cents,
            platform_fee_cents=0,
            discount_cents=0,
            total_cents=amount_cents,
            price_per_player_snapshot_cents=amount_cents,
            platform_fee_snapshot_cents=0,
            booked_at=datetime.now(timezone.utc),
        )
        db.add(booking)
        db.commit()
        return booking.id


def _persist_money_repair_fixture(
    *,
    game_id: uuid.UUID,
    booking_id: uuid.UUID,
    target_user_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    from backend.models import (
        GameCredit,
        GameCreditUsage,
        MoneyIssue,
        Payment,
        PaymentEvent,
        Refund,
    )

    now = datetime.now(timezone.utc)
    with _session() as db:
        payment = Payment(
            id=uuid.uuid4(),
            payer_user_id=target_user_id,
            booking_id=booking_id,
            game_id=game_id,
            payment_type="booking",
            provider="stripe",
            provider_payment_intent_id=f"pi_ws03d_{uuid.uuid4().hex}",
            provider_charge_id=f"ch_ws03d_{uuid.uuid4().hex}",
            idempotency_key=f"ws03d-payment-{uuid.uuid4()}",
            amount_cents=1200,
            currency="USD",
            payment_status="succeeded",
            paid_at=now,
        )
        db.add(payment)
        db.flush()

        retry_refund = Refund(
            id=uuid.uuid4(),
            payment_id=payment.id,
            booking_id=booking_id,
            provider_refund_id=None,
            origin_workflow="direct_admin_refund",
            provider="stripe",
            provider_status="failed",
            provider_status_observed_at=now,
            provider_charge_id=payment.provider_charge_id,
            amount_cents=300,
            currency="USD",
            refund_reason="admin_refund",
            refund_status="failed",
            requested_by_user_id=target_user_id,
            approved_by_user_id=target_user_id,
            requested_at=now,
            approved_at=now,
        )
        reconcile_refund = Refund(
            id=uuid.uuid4(),
            payment_id=payment.id,
            booking_id=booking_id,
            provider_refund_id=f"re_ws03d_reconcile_{uuid.uuid4().hex}",
            origin_workflow="direct_admin_refund",
            provider="stripe",
            provider_status="failed",
            provider_status_observed_at=now,
            provider_charge_id=payment.provider_charge_id,
            amount_cents=200,
            currency="USD",
            refund_reason="admin_refund",
            refund_status="failed",
            requested_by_user_id=target_user_id,
            approved_by_user_id=target_user_id,
            requested_at=now,
            approved_at=now,
        )
        db.add_all([retry_refund, reconcile_refund])
        db.flush()

        credit = GameCredit(
            id=uuid.uuid4(),
            user_id=target_user_id,
            amount_cents=400,
            available_cents=0,
            currency="USD",
            credit_status="used",
            credit_reason="admin_credit",
            source_game_id=game_id,
            source_booking_id=booking_id,
            source_payment_id=payment.id,
            issued_by_user_id=target_user_id,
            idempotency_key=f"ws03d-credit-fixture-{uuid.uuid4()}",
        )
        db.add(credit)
        db.flush()

        credit_usage = GameCreditUsage(
            id=uuid.uuid4(),
            game_credit_id=credit.id,
            booking_id=booking_id,
            game_id=game_id,
            payment_id=payment.id,
            amount_cents=400,
            currency="USD",
            usage_type="redeem",
            usage_status="redeemed",
            idempotency_key=f"ws03d-credit-usage-{uuid.uuid4()}",
            reason_code="local_test_redeem",
            redeemed_at=now,
        )
        db.add(credit_usage)
        db.flush()

        resolve_issue = MoneyIssue(
            id=uuid.uuid4(),
            operation_key=f"ws03d-resolve-{uuid.uuid4()}",
            status="open",
            issue_type="refund_failed",
            origin_workflow="direct_admin_refund",
            value_kind="cash_refund",
            amount_cents=retry_refund.amount_cents,
            currency="USD",
            target_user_id=target_user_id,
            target_game_id=game_id,
            target_booking_id=booking_id,
            target_payment_id=payment.id,
            target_refund_id=retry_refund.id,
            latest_reason_code="local_test_refund_failed",
            latest_summary="Local test refund failed.",
            recommended_action_code="review_and_resolve_no_action",
            occurrence_count=1,
            reopen_count=0,
            first_detected_at=now,
            last_detected_at=now,
            last_activity_at=now,
        )
        retry_issue = MoneyIssue(
            id=uuid.uuid4(),
            operation_key=f"ws03d-credit-retry-{uuid.uuid4()}",
            status="open",
            issue_type="credit_restore_failed",
            origin_workflow="direct_admin_refund",
            value_kind="game_credit_restore",
            amount_cents=credit_usage.amount_cents,
            currency="USD",
            target_user_id=target_user_id,
            target_game_id=game_id,
            target_booking_id=booking_id,
            target_payment_id=payment.id,
            target_game_credit_id=credit.id,
            target_credit_usage_id=credit_usage.id,
            latest_reason_code="local_test_credit_restore_failed",
            latest_summary="Local test credit restore failed.",
            recommended_action_code="retry_credit_restore",
            occurrence_count=1,
            reopen_count=0,
            first_detected_at=now,
            last_detected_at=now,
            last_activity_at=now,
        )
        payment_event = PaymentEvent(
            id=uuid.uuid4(),
            payment_id=None,
            provider="stripe",
            provider_event_id=f"evt_ws03d_{uuid.uuid4().hex}",
            event_type="payment_intent.succeeded",
            raw_payload={"fixture": "ws03d-payment-event"},
            processing_status="pending",
        )
        db.add_all([resolve_issue, retry_issue, payment_event])
        db.commit()
        return {
            "payment_id": payment.id,
            "retry_refund_id": retry_refund.id,
            "reconcile_refund_id": reconcile_refund.id,
            "resolve_issue_id": resolve_issue.id,
            "retry_issue_id": retry_issue.id,
            "credit_id": credit.id,
            "credit_usage_id": credit_usage.id,
            "payment_event_id": payment_event.id,
        }


def _persist_host_publish_fee_fixture(
    *,
    game_id: uuid.UUID,
    host_user_id: uuid.UUID,
    amount_cents: int = 900,
) -> uuid.UUID:
    from backend.models import HostPublishFee, Payment

    now = datetime.now(timezone.utc)
    with _session() as db:
        payment = Payment(
            id=uuid.uuid4(),
            payer_user_id=host_user_id,
            booking_id=None,
            game_id=game_id,
            payment_type="community_publish_fee",
            provider="stripe",
            provider_payment_intent_id=f"pi_ws03d_fee_{uuid.uuid4().hex}",
            provider_charge_id=f"ch_ws03d_fee_{uuid.uuid4().hex}",
            idempotency_key=f"ws03d-fee-payment-{uuid.uuid4()}",
            amount_cents=amount_cents,
            currency="USD",
            payment_status="succeeded",
            paid_at=now,
        )
        db.add(payment)
        db.flush()
        fee = HostPublishFee(
            id=uuid.uuid4(),
            game_id=game_id,
            host_user_id=host_user_id,
            payment_id=payment.id,
            amount_cents=amount_cents,
            currency="USD",
            fee_status="paid",
            waiver_reason="none",
            paid_at=now,
        )
        db.add(fee)
        db.commit()
        return fee.id


def _get_credit_state(game_credit_id: uuid.UUID) -> dict[str, object]:
    from backend.models import GameCredit

    with _session() as db:
        credit = db.get(GameCredit, game_credit_id)
        assert credit is not None
        return {
            "credit_status": credit.credit_status,
            "available_cents": credit.available_cents,
            "reversed_by_user_id": credit.reversed_by_user_id,
            "reversed_at": credit.reversed_at,
        }


def _money_issue_state(money_issue_id: uuid.UUID) -> dict[str, object]:
    from backend.models import MoneyIssue

    with _session() as db:
        issue = db.get(MoneyIssue, money_issue_id)
        assert issue is not None
        return {
            "status": issue.status,
            "resolved_by_user_id": issue.resolved_by_user_id,
            "resolution_reason_code": issue.resolution_reason_code,
            "resolution_note": issue.resolution_note,
            "latest_reason_code": issue.latest_reason_code,
            "recommended_action_code": issue.recommended_action_code,
            "occurrence_count": issue.occurrence_count,
        }


def _credit_usage_status_counts(game_credit_id: uuid.UUID) -> dict[str, int]:
    from sqlalchemy import func, select

    from backend.models import GameCreditUsage

    with _session() as db:
        rows = db.execute(
            select(GameCreditUsage.usage_status, func.count())
            .where(GameCreditUsage.game_credit_id == game_credit_id)
            .group_by(GameCreditUsage.usage_status)
        ).all()
        return {str(status): int(count) for status, count in rows}


def _refund_state(refund_id: uuid.UUID) -> dict[str, object]:
    from backend.models import Refund

    with _session() as db:
        refund = db.get(Refund, refund_id)
        assert refund is not None
        return {
            "refund_status": refund.refund_status,
            "provider_refund_id": refund.provider_refund_id,
            "provider_charge_id": refund.provider_charge_id,
            "provider_status": refund.provider_status,
            "approved_by_user_id": refund.approved_by_user_id,
            "refunded_at": refund.refunded_at,
            "last_refund_event_at": refund.last_refund_event_at,
        }


def _payment_event_state(payment_event_id: uuid.UUID) -> dict[str, object]:
    from backend.models import PaymentEvent

    with _session() as db:
        event = db.get(PaymentEvent, payment_event_id)
        assert event is not None
        return {
            "payment_id": event.payment_id,
            "provider": event.provider,
            "provider_event_id": event.provider_event_id,
            "event_type": event.event_type,
            "raw_payload": event.raw_payload,
            "processing_status": event.processing_status,
            "processing_error": event.processing_error,
            "processed_at": event.processed_at,
        }


def _financial_outcome_state(financial_outcome_id: uuid.UUID) -> dict[str, object]:
    from backend.models import AdminFinancialOutcome

    with _session() as db:
        outcome = db.get(AdminFinancialOutcome, financial_outcome_id)
        assert outcome is not None
        return {
            "outcome": outcome.outcome,
            "applied_status": outcome.applied_status,
            "amount_cents": outcome.amount_cents,
            "refund_id": outcome.refund_id,
            "host_publish_entitlement_id": outcome.host_publish_entitlement_id,
            "applied_by_user_id": outcome.applied_by_user_id,
        }


@pytest.mark.requirement("WS03-04D-R3", "WS03-04D-R7", "WS03-04D-R10")
def test_stale_admin_cannot_issue_credit_or_create_financial_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, GameCredit

    admin = _user("credit-stale-admin", role="admin")
    target = _user("credit-stale-target")
    _add_users(admin, target)
    _install_tokens_for_users(
        monkeypatch,
        {"stale-admin-token": admin},
        stale_tokens={"stale-admin-token"},
    )
    before_credits = _count_model_rows(GameCredit)
    before_admin_actions = _count_model_rows(AdminAction)

    response = _client().post(
        "/admin/game-credits/issue",
        json={
            "user_id": str(target.id),
            "amount_cents": 500,
            "credit_reason": "admin_credit",
            "idempotency_key": f"ws03d-credit-stale-{uuid.uuid4()}",
            "note": "Rejected stale admin request.",
        },
        headers=_auth_headers("stale-admin-token"),
    )

    assert response.status_code == 403
    assert _count_model_rows(GameCredit) == before_credits
    assert _count_model_rows(AdminAction) == before_admin_actions


@pytest.mark.requirement("WS03-04D-R7", "WS03-04D-R10")
def test_recent_active_admin_can_issue_credit_and_ordinary_user_cannot_list_money(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, GameCredit, GameCreditUsage

    admin = _user("credit-success-admin", role="admin")
    stale_admin = _user("credit-success-stale-admin", role="admin")
    ordinary = _user("credit-success-ordinary")
    target = _user("credit-success-target")
    _add_users(admin, stale_admin, ordinary, target)
    game_id, _venue_id = _persist_game_fixture(
        "credit-success",
        admin=admin,
        creator=target,
    )
    booking_id = _persist_paid_booking(
        game_id=game_id,
        buyer_user_id=target.id,
        amount_cents=700,
    )
    _install_tokens_for_users(
        monkeypatch,
        {
            "admin-token": admin,
            "stale-admin-token": stale_admin,
            "ordinary-token": ordinary,
        },
        stale_tokens={"stale-admin-token"},
    )
    client = _client()
    before_credits = _count_model_rows(GameCredit)
    before_admin_actions = _count_model_rows(AdminAction)
    before_credit_usages = _count_model_rows(GameCreditUsage)

    response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": str(target.id),
            "amount_cents": 700,
            "credit_reason": "admin_credit",
            "source_booking_id": str(booking_id),
            "idempotency_key": f"ws03d-credit-success-{uuid.uuid4()}",
            "note": "Admin-issued local test credit.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == str(target.id)
    assert body["issued_by_user_id"] == str(admin.id)
    assert body["available_cents"] == 700
    assert _count_model_rows(GameCredit) == before_credits + 1
    assert _count_model_rows(AdminAction) == before_admin_actions + 1

    game_credit_id = uuid.UUID(body["id"])
    issued_credit_state = _get_credit_state(game_credit_id)
    stale_reverse = client.post(
        f"/admin/game-credits/{game_credit_id}/reverse",
        json={
            "idempotency_key": f"ws03d-credit-stale-reverse-{uuid.uuid4()}",
            "note": "Stale admin must not reverse local test credit.",
        },
        headers=_auth_headers("stale-admin-token"),
    )
    assert stale_reverse.status_code == 403
    assert _get_credit_state(game_credit_id) == issued_credit_state
    assert _count_model_rows(GameCreditUsage) == before_credit_usages
    assert _count_model_rows(AdminAction) == before_admin_actions + 1

    reverse_response = client.post(
        f"/admin/game-credits/{game_credit_id}/reverse",
        json={
            "idempotency_key": f"ws03d-credit-reverse-{uuid.uuid4()}",
            "note": "Reverse unused local test credit.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert reverse_response.status_code == 200
    reverse_body = reverse_response.json()
    assert reverse_body["id"] == str(game_credit_id)
    assert reverse_body["credit_status"] == "reversed"
    assert reverse_body["available_cents"] == 0
    assert reverse_body["reversed_by_user_id"] == str(admin.id)
    assert _get_credit_state(game_credit_id)["credit_status"] == "reversed"
    assert _count_model_rows(GameCreditUsage) == before_credit_usages + 1
    assert _count_model_rows(AdminAction) == before_admin_actions + 2

    ordinary_response = client.get(
        "/admin/money/credits",
        headers=_auth_headers("ordinary-token"),
    )
    assert ordinary_response.status_code == 403


@pytest.mark.requirement("WS03-04D-R7", "WS03-04D-R10")
def test_recent_admin_financial_issue_and_payment_event_repairs_persist_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import (
        AdminAction,
        AdminFinancialOutcome,
        MoneyIssueEvent,
        PaymentEvent,
    )

    admin = _user("money-repair-admin", role="admin")
    stale_admin = _user("money-repair-stale-admin", role="admin")
    host = _user("money-repair-host")
    target = _user("money-repair-target")
    _add_users(admin, stale_admin, host, target)
    official_game_id, _official_venue_id = _persist_game_fixture(
        "money-repair-official",
        admin=admin,
        creator=target,
    )
    community_game_id, _community_venue_id = _persist_community_game_fixture(
        "money-repair-community",
        admin=admin,
        host=host,
    )
    booking_id = _persist_paid_booking(
        game_id=official_game_id,
        buyer_user_id=target.id,
        amount_cents=1200,
    )
    fixture = _persist_money_repair_fixture(
        game_id=official_game_id,
        booking_id=booking_id,
        target_user_id=target.id,
    )
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "stale-admin-token": stale_admin},
        stale_tokens={"stale-admin-token"},
    )
    client = _client()
    before_outcomes = _count_model_rows(AdminFinancialOutcome)
    before_admin_actions = _count_model_rows(AdminAction)

    stale_outcome = client.post(
        "/admin/money/financial-outcomes",
        json={
            "outcome": "no_fee_charged",
            "reason": "Stale admin must not create financial outcomes.",
            "idempotency_key": f"ws03d-stale-financial-outcome-real-{uuid.uuid4()}",
            "host_user_id": str(host.id),
            "target_game_id": str(community_game_id),
            "amount_cents": 0,
        },
        headers=_auth_headers("stale-admin-token"),
    )
    assert stale_outcome.status_code == 403
    assert _count_model_rows(AdminFinancialOutcome) == before_outcomes
    assert _count_model_rows(AdminAction) == before_admin_actions

    outcome = client.post(
        "/admin/money/financial-outcomes",
        json={
            "outcome": "no_fee_charged",
            "reason": "Record no publish fee charged for local community game.",
            "internal_note": "Local test outcome note.",
            "idempotency_key": f"ws03d-financial-outcome-{uuid.uuid4()}",
            "host_user_id": str(host.id),
            "target_game_id": str(community_game_id),
            "amount_cents": 0,
        },
        headers=_auth_headers("admin-token"),
    )
    assert outcome.status_code == 201
    outcome_body = outcome.json()
    assert outcome_body["host_user_id"] == str(host.id)
    assert outcome_body["target_game_id"] == str(community_game_id)
    assert outcome_body["applied_status"] == "not_applicable"
    assert outcome_body["created_by_user_id"] == str(admin.id)
    assert _count_model_rows(AdminFinancialOutcome) == before_outcomes + 1
    assert _count_model_rows(AdminAction) == before_admin_actions + 1

    resolve_issue_id = fixture["resolve_issue_id"]
    before_resolve_issue = _money_issue_state(resolve_issue_id)
    before_issue_events = _count_model_rows(MoneyIssueEvent)
    stale_resolve = client.post(
        f"/admin/money/issues/{resolve_issue_id}/resolve",
        json={
            "resolution_reason_code": "handled_externally",
            "resolution_note": "Stale admin must not resolve money issues.",
            "resolution_external_reference": "local-test-stale-reference",
            "idempotency_key": f"ws03d-stale-resolve-real-{uuid.uuid4()}",
        },
        headers=_auth_headers("stale-admin-token"),
    )
    assert stale_resolve.status_code == 403
    assert _money_issue_state(resolve_issue_id) == before_resolve_issue
    assert _count_model_rows(MoneyIssueEvent) == before_issue_events
    assert _count_model_rows(AdminAction) == before_admin_actions + 1

    resolve = client.post(
        f"/admin/money/issues/{resolve_issue_id}/resolve",
        json={
            "resolution_reason_code": "handled_externally",
            "resolution_note": "Resolved with documented local admin review.",
            "resolution_external_reference": "local-test-resolution-reference",
            "idempotency_key": f"ws03d-resolve-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert resolve.status_code == 200
    resolved_issue = _money_issue_state(resolve_issue_id)
    assert resolved_issue["status"] == "resolved"
    assert resolved_issue["resolved_by_user_id"] == admin.id
    assert resolved_issue["resolution_reason_code"] == "handled_externally"
    assert _count_model_rows(MoneyIssueEvent) == before_issue_events + 1

    retry_issue_id = fixture["retry_issue_id"]
    credit_id = fixture["credit_id"]
    before_credit = _get_credit_state(credit_id)
    before_credit_usage_counts = _credit_usage_status_counts(credit_id)
    before_retry_issue_events = _count_model_rows(MoneyIssueEvent)
    retry_idempotency_key = f"ws03d-credit-retry-{uuid.uuid4()}"
    retry_credit = client.post(
        f"/admin/money/issues/{retry_issue_id}/retry-credit",
        json={
            "reason": "Retry failed local test credit restore.",
            "idempotency_key": retry_idempotency_key,
        },
        headers=_auth_headers("admin-token"),
    )
    assert retry_credit.status_code == 200
    after_credit = _get_credit_state(credit_id)
    assert before_credit["available_cents"] == 0
    assert after_credit["credit_status"] == "active"
    assert after_credit["available_cents"] == 400
    assert _credit_usage_status_counts(credit_id) == {
        **before_credit_usage_counts,
        "restored": 1,
    }
    assert _money_issue_state(retry_issue_id)[
        "recommended_action_code"
    ] == "review_and_resolve_no_action"
    assert _count_model_rows(MoneyIssueEvent) == before_retry_issue_events + 2

    retry_replay = client.post(
        f"/admin/money/issues/{retry_issue_id}/retry-credit",
        json={
            "reason": "Retry failed local test credit restore.",
            "idempotency_key": retry_idempotency_key,
        },
        headers=_auth_headers("admin-token"),
    )
    assert retry_replay.status_code == 200
    assert _credit_usage_status_counts(credit_id) == {
        **before_credit_usage_counts,
        "restored": 1,
    }

    payment_event_id = fixture["payment_event_id"]
    before_event = _payment_event_state(payment_event_id)
    before_payment_events = _count_model_rows(PaymentEvent)
    stale_event = client.patch(
        f"/payment-events/{payment_event_id}",
        json={
            "payment_id": str(fixture["payment_id"]),
            "processing_status": "failed",
            "processing_error": "Stale admin must not repair payment events.",
        },
        headers=_auth_headers("stale-admin-token"),
    )
    assert stale_event.status_code == 403
    assert _payment_event_state(payment_event_id) == before_event
    assert _count_model_rows(PaymentEvent) == before_payment_events

    repair_event = client.patch(
        f"/payment-events/{payment_event_id}",
        json={
            "payment_id": str(fixture["payment_id"]),
            "processing_status": "failed",
            "processing_error": "Local test event repair recorded.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert repair_event.status_code == 200
    repaired_event = _payment_event_state(payment_event_id)
    assert repaired_event["payment_id"] == fixture["payment_id"]
    assert repaired_event["processing_status"] == "failed"
    assert repaired_event["processing_error"] == "Local test event repair recorded."
    assert repaired_event["provider_event_id"] == before_event["provider_event_id"]
    assert repaired_event["event_type"] == before_event["event_type"]
    assert repaired_event["raw_payload"] == before_event["raw_payload"]


@pytest.mark.requirement("WS03-04D-R7", "WS03-04D-R10")
def test_recent_admin_financial_outcome_branches_persist_distinct_state_and_provider_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import (
        AdminAction,
        AdminFinancialOutcome,
        AdminTargetNotice,
        HostPublishEntitlement,
        Refund,
        RefundEvent,
    )
    from backend.services import admin_financial_outcome_service
    from backend.services.stripe_service import StripeRefundResult

    admin = _user("financial-branches-admin", role="admin")
    stale_admin = _user("financial-branches-stale-admin", role="admin")
    host = _user("financial-branches-host")
    branch_hosts = {
        outcome: _user(f"financial-branches-{outcome}-host")
        for outcome in ("manual_review", "forfeit", "credit", "refund")
    }
    _add_users(admin, stale_admin, host, *branch_hosts.values())
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "stale-admin-token": stale_admin},
        stale_tokens={"stale-admin-token"},
    )
    provider_calls: list[tuple[str, int]] = []

    def fake_create_refund(
        *,
        charge_id: str,
        amount_cents: int,
        currency: str,
        idempotency_key: str,
        metadata: dict[str, str],
    ) -> StripeRefundResult:
        assert metadata["source"] == "community_publish_fee_financial_outcome"
        provider_calls.append((charge_id, amount_cents))
        return StripeRefundResult(
            id=f"re_ws03d_outcome_{uuid.uuid4().hex}",
            status="succeeded",
            amount_cents=amount_cents,
            currency=currency,
            charge_id=charge_id,
            payment_intent_id=None,
        )

    monkeypatch.setattr(
        admin_financial_outcome_service,
        "create_stripe_refund",
        fake_create_refund,
    )

    client = _client()
    before_counts = {
        AdminAction: _count_model_rows(AdminAction),
        AdminFinancialOutcome: _count_model_rows(AdminFinancialOutcome),
        AdminTargetNotice: _count_model_rows(AdminTargetNotice),
        HostPublishEntitlement: _count_model_rows(HostPublishEntitlement),
        Refund: _count_model_rows(Refund),
        RefundEvent: _count_model_rows(RefundEvent),
    }

    stale_game_id, _stale_venue_id = _persist_community_game_fixture(
        "financial-stale-outcome",
        admin=admin,
        host=host,
    )
    stale_fee_id = _persist_host_publish_fee_fixture(
        game_id=stale_game_id,
        host_user_id=host.id,
    )
    stale_response = client.post(
        "/admin/money/financial-outcomes",
        json={
            "outcome": "forfeit",
            "reason": "Stale admin must not apply financial outcomes.",
            "idempotency_key": f"ws03d-outcome-stale-{uuid.uuid4()}",
            "host_publish_fee_id": str(stale_fee_id),
        },
        headers=_auth_headers("stale-admin-token"),
    )
    assert stale_response.status_code == 403
    assert provider_calls == []
    assert _count_model_rows(AdminFinancialOutcome) == before_counts[AdminFinancialOutcome]
    assert _count_model_rows(AdminAction) == before_counts[AdminAction]

    branch_expectations = {
        "manual_review": ("pending", 1, AdminFinancialOutcome),
        "forfeit": ("applied", 1, AdminFinancialOutcome),
        "credit": ("applied", 1, HostPublishEntitlement),
        "refund": ("applied", 1, Refund),
    }
    provider_call_count = 0
    created_outcome_ids: dict[str, uuid.UUID] = {}
    for outcome, (expected_status, expected_delta, counted_model) in (
        branch_expectations.items()
    ):
        branch_host = branch_hosts[outcome]
        game_id, _venue_id = _persist_community_game_fixture(
            f"financial-{outcome}",
            admin=admin,
            host=branch_host,
        )
        fee_id = _persist_host_publish_fee_fixture(
            game_id=game_id,
            host_user_id=branch_host.id,
        )
        before_model_count = _count_model_rows(counted_model)
        response = client.post(
            "/admin/money/financial-outcomes",
            json={
                "outcome": outcome,
                "reason": f"Apply local {outcome} outcome.",
                "internal_note": f"Local {outcome} branch proof.",
                "idempotency_key": f"ws03d-outcome-{outcome}-{uuid.uuid4()}",
                "host_publish_fee_id": str(fee_id),
            },
            headers=_auth_headers("admin-token"),
        )
        assert response.status_code == 201
        body = response.json()
        created_outcome_ids[outcome] = uuid.UUID(body["id"])
        state = _financial_outcome_state(created_outcome_ids[outcome])
        assert state["outcome"] == outcome
        assert state["applied_status"] == expected_status
        assert state["amount_cents"] == 900
        if outcome == "refund":
            provider_call_count += 1
            assert len(provider_calls) == provider_call_count
            assert state["refund_id"] is not None
        else:
            assert len(provider_calls) == provider_call_count
        if outcome == "credit":
            assert state["host_publish_entitlement_id"] is not None
        assert _count_model_rows(counted_model) == before_model_count + expected_delta

@pytest.mark.requirement("WS03-04D-R7", "WS03-04D-R10")
def test_recent_admin_refund_retry_and_reconcile_use_provider_fakes_after_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, RefundEvent
    from backend.services import admin_money_refund_service
    from backend.services.stripe_service import StripeRefundResult

    admin = _user("refund-repair-admin", role="admin")
    stale_admin = _user("refund-repair-stale-admin", role="admin")
    target = _user("refund-repair-target")
    _add_users(admin, stale_admin, target)
    game_id, _venue_id = _persist_game_fixture(
        "refund-repair",
        admin=admin,
        creator=target,
    )
    booking_id = _persist_paid_booking(
        game_id=game_id,
        buyer_user_id=target.id,
        amount_cents=1200,
    )
    fixture = _persist_money_repair_fixture(
        game_id=game_id,
        booking_id=booking_id,
        target_user_id=target.id,
    )
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "stale-admin-token": stale_admin},
        stale_tokens={"stale-admin-token"},
    )
    provider_calls: list[tuple[str, str, int | None]] = []

    def fake_create_refund(
        *,
        charge_id: str,
        amount_cents: int,
        currency: str,
        idempotency_key: str,
        metadata: dict[str, str],
    ) -> StripeRefundResult:
        assert metadata["source"] == "admin_money_refund_retry"
        provider_calls.append(("retry", charge_id, amount_cents))
        return StripeRefundResult(
            id=f"re_ws03d_retry_{uuid.uuid4().hex}",
            status="succeeded",
            amount_cents=amount_cents,
            currency=currency,
            charge_id=charge_id,
            payment_intent_id=None,
        )

    def fake_retrieve_refund(refund_id: str) -> StripeRefundResult:
        provider_calls.append(("reconcile", refund_id, None))
        return StripeRefundResult(
            id=refund_id,
            status="succeeded",
            amount_cents=200,
            currency="USD",
            charge_id=None,
            payment_intent_id=None,
        )

    monkeypatch.setattr(
        admin_money_refund_service,
        "create_stripe_refund",
        fake_create_refund,
    )
    monkeypatch.setattr(
        admin_money_refund_service,
        "retrieve_stripe_refund",
        fake_retrieve_refund,
    )
    client = _client()
    retry_refund_id = fixture["retry_refund_id"]
    reconcile_refund_id = fixture["reconcile_refund_id"]
    before_retry_refund = _refund_state(retry_refund_id)
    before_refund_events = _count_model_rows(RefundEvent)
    before_admin_actions = _count_model_rows(AdminAction)

    stale_retry = client.post(
        f"/admin/money/refunds/{retry_refund_id}/retry",
        json={
            "reason": "Stale admin must not retry refunds.",
            "idempotency_key": f"ws03d-stale-refund-retry-real-{uuid.uuid4()}",
        },
        headers=_auth_headers("stale-admin-token"),
    )
    assert stale_retry.status_code == 403
    assert provider_calls == []
    assert _refund_state(retry_refund_id) == before_retry_refund
    assert _count_model_rows(RefundEvent) == before_refund_events
    assert _count_model_rows(AdminAction) == before_admin_actions

    retry_idempotency_key = f"ws03d-refund-retry-{uuid.uuid4()}"
    retry = client.post(
        f"/admin/money/refunds/{retry_refund_id}/retry",
        json={
            "reason": "Retry local failed refund with provider fake.",
            "idempotency_key": retry_idempotency_key,
        },
        headers=_auth_headers("admin-token"),
    )
    assert retry.status_code == 200
    assert len(provider_calls) == 1
    assert provider_calls[0][0] == "retry"
    retry_state = _refund_state(retry_refund_id)
    assert retry_state["refund_status"] == "succeeded"
    assert retry_state["provider_status"] == "succeeded"
    assert retry_state["provider_refund_id"] is not None
    assert retry_state["approved_by_user_id"] == admin.id
    assert _count_model_rows(RefundEvent) == before_refund_events + 1
    assert _count_model_rows(AdminAction) == before_admin_actions + 1

    retry_replay = client.post(
        f"/admin/money/refunds/{retry_refund_id}/retry",
        json={
            "reason": "Retry local failed refund with provider fake.",
            "idempotency_key": retry_idempotency_key,
        },
        headers=_auth_headers("admin-token"),
    )
    assert retry_replay.status_code == 200
    assert len(provider_calls) == 1
    assert _count_model_rows(RefundEvent) == before_refund_events + 1
    assert _count_model_rows(AdminAction) == before_admin_actions + 1

    before_reconcile_refund = _refund_state(reconcile_refund_id)
    stale_reconcile = client.post(
        f"/admin/money/refunds/{reconcile_refund_id}/reconcile",
        json={
            "reason": "Stale admin must not reconcile refunds.",
            "idempotency_key": f"ws03d-stale-reconcile-real-{uuid.uuid4()}",
        },
        headers=_auth_headers("stale-admin-token"),
    )
    assert stale_reconcile.status_code == 403
    assert len(provider_calls) == 1
    assert _refund_state(reconcile_refund_id) == before_reconcile_refund

    reconcile_idempotency_key = f"ws03d-refund-reconcile-{uuid.uuid4()}"
    reconcile = client.post(
        f"/admin/money/refunds/{reconcile_refund_id}/reconcile",
        json={
            "reason": "Reconcile local failed refund with provider fake.",
            "idempotency_key": reconcile_idempotency_key,
        },
        headers=_auth_headers("admin-token"),
    )
    assert reconcile.status_code == 200
    assert len(provider_calls) == 2
    assert provider_calls[1][0] == "reconcile"
    reconcile_state = _refund_state(reconcile_refund_id)
    assert reconcile_state["refund_status"] == "succeeded"
    assert reconcile_state["provider_status"] == "succeeded"
    assert reconcile_state["provider_refund_id"] == before_reconcile_refund[
        "provider_refund_id"
    ]
    assert _count_model_rows(RefundEvent) == before_refund_events + 2
    assert _count_model_rows(AdminAction) == before_admin_actions + 2

    reconcile_replay = client.post(
        f"/admin/money/refunds/{reconcile_refund_id}/reconcile",
        json={
            "reason": "Reconcile local failed refund with provider fake.",
            "idempotency_key": reconcile_idempotency_key,
        },
        headers=_auth_headers("admin-token"),
    )
    assert reconcile_replay.status_code == 200
    assert len(provider_calls) == 2
    assert _count_model_rows(RefundEvent) == before_refund_events + 2
    assert _count_model_rows(AdminAction) == before_admin_actions + 2
