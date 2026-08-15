from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import backend.services.provider_retry_policy as retry_policy

pytestmark = pytest.mark.suite_type("ordinary")

_STARTS_AT = datetime(2035, 3, 3, 18, 0, tzinfo=timezone.utc)
_ENDS_AT = _STARTS_AT + timedelta(hours=2)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _count(db: Session, model: type[object]) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _user(index: int, *, role: str = "player"):
    from backend.models import User

    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04c2-repair-{index}-{unique}",
        role=role,
        email=f"ws02-04c2-repair-{index}-{unique}@example.invalid",
        first_name="Repair",
        last_name=f"User{index}",
        account_status="active",
        hosting_status="eligible",
    )


def _venue(admin):
    from backend.models import Venue

    return Venue(
        id=uuid.uuid4(),
        name="C2 Repair Field",
        address_line_1="3 Retry Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        created_by_user_id=admin.id,
        approved_by_user_id=admin.id,
        approved_at=datetime.now(timezone.utc),
    )


def _game(admin, venue):
    from backend.models import Game

    return Game(
        id=uuid.uuid4(),
        game_type="official",
        payment_collection_type="in_app",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="C2 Repair Game",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=None,
        created_by_user_id=admin.id,
        starts_at=_STARTS_AT,
        ends_at=_ENDS_AT,
        starts_on_local=_STARTS_AT.date(),
        timezone="UTC",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=12,
        price_per_player_cents=1200,
        currency="USD",
        allow_guests=True,
        max_guests_per_booking=0,
        host_guest_max=0,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="official_standard",
        published_at=datetime.now(timezone.utc),
    )


def _booking(user, game):
    from backend.models import Booking

    return Booking(
        id=uuid.uuid4(),
        game_id=game.id,
        buyer_user_id=user.id,
        booking_status="confirmed",
        payment_status="paid",
        participant_count=1,
        subtotal_cents=1200,
        platform_fee_cents=0,
        discount_cents=0,
        total_cents=1200,
        currency="USD",
        price_per_player_snapshot_cents=1200,
        platform_fee_snapshot_cents=0,
        booked_at=datetime.now(timezone.utc),
    )


def _payment(user, booking):
    from backend.models import Payment

    return Payment(
        id=uuid.uuid4(),
        payer_user_id=user.id,
        booking_id=booking.id,
        game_id=None,
        payment_type="booking",
        provider="stripe",
        provider_payment_intent_id=f"pi_ws02_04c2_repair_{uuid.uuid4()}",
        provider_charge_id=f"ch_ws02_04c2_repair_{uuid.uuid4()}",
        idempotency_key=f"ws02-04c2-repair-payment-{uuid.uuid4()}",
        amount_cents=1200,
        currency="USD",
        payment_status="succeeded",
        paid_at=datetime.now(timezone.utc),
        payment_metadata={"test": "ws02-04c2"},
    )


def _refund(payment, booking, *, provider_status: str | None):
    from backend.models import Refund

    return Refund(
        id=uuid.uuid4(),
        payment_id=payment.id,
        booking_id=booking.id,
        participant_id=None,
        host_publish_fee_id=None,
        provider_refund_id=None,
        origin_workflow="direct_admin_refund",
        provider="stripe",
        provider_status=provider_status,
        provider_charge_id=payment.provider_charge_id,
        amount_cents=500,
        currency="USD",
        refund_reason="admin_refund",
        refund_status="failed",
        requested_by_user_id=None,
        approved_by_user_id=None,
        requested_at=datetime.now(timezone.utc),
    )


def _target_state(db: Session, *, provider_status: str | None):
    admin = _user(0, role="admin")
    user = _user(1)
    db.add_all([admin, user])
    db.flush()
    venue = _venue(admin)
    db.add(venue)
    db.flush()
    game = _game(admin, venue)
    db.add(game)
    db.flush()
    booking = _booking(user, game)
    db.add(booking)
    db.flush()
    payment = _payment(user, booking)
    db.add(payment)
    db.flush()
    refund = _refund(payment, booking, provider_status=provider_status)
    db.add(refund)
    db.commit()
    return admin, user, payment, refund


@pytest.mark.requirement("WS02-04C2-R6")
def test_admin_refund_retry_rejects_uncertain_provider_status_without_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction
    from backend.schemas.admin_money_refund_schema import AdminMoneyRefundRetryCreate
    import backend.services.admin_money_refund_service as refund_service

    provider_calls: list[str] = []
    monkeypatch.setattr(
        refund_service,
        "call_stripe_refund_retry",
        lambda **kwargs: provider_calls.append("unexpected-provider-call"),
    )

    with _session() as db:
        admin, _user, _payment, refund = _target_state(
            db,
            provider_status="processing",
        )

        with pytest.raises(HTTPException) as exc_info:
            refund_service.retry_admin_money_refund(
                db,
                admin_user=admin,
                refund_id=refund.id,
                payload=AdminMoneyRefundRetryCreate(
                    reason="check provider first",
                    idempotency_key="ws02-04c2-repair-key",
                ),
            )
        db.rollback()

        assert exc_info.value.status_code == 400
        assert "outcome is still uncertain" in str(exc_info.value.detail)
        assert provider_calls == []
        assert _count(db, AdminAction) == 0


@pytest.mark.requirement("WS02-04C2-R6")
def test_admin_refund_reconciliation_records_state_gated_missing_provider_reference() -> None:
    from backend.models import MoneyIssue, RefundEvent
    from backend.schemas.admin_money_refund_schema import AdminMoneyRefundReconcileCreate
    import backend.services.admin_money_refund_service as refund_service

    with _session() as db:
        admin, _user, _payment, refund = _target_state(
            db,
            provider_status="unknown",
        )

        refund_service.reconcile_admin_money_refund(
            db,
            admin_user=admin,
            refund_id=refund.id,
            payload=AdminMoneyRefundReconcileCreate(
                reason="missing provider id",
                idempotency_key="ws02-04c2-reconcile-key",
            ),
        )

        events = db.scalars(select(RefundEvent)).all()
        issues = db.scalars(select(MoneyIssue)).all()

        assert len(events) == 1
        assert events[0].provider_status == "unknown"
        assert events[0].reason_code == "missing_provider_refund_id"
        assert len(issues) == 1
        assert issues[0].issue_type == "refund_missing_provider_reference"


@pytest.mark.requirement("WS02-04C2-R6")
def test_registry_keeps_manual_and_reconciliation_recovery_boundaries_explicit() -> None:
    contexts = {
        policy.workflow_context: policy
        for policy in retry_policy.PROVIDER_OPERATION_RETRY_POLICIES
    }

    assert contexts["admin_refund_retry"].safety_class == (
        retry_policy.RetrySafetyClass.MANUAL_REPAIR
    )
    assert contexts["admin_refund_retry"].dependency_retry_owner == (
        retry_policy.RetryOwnership.DEPENDENCY_OWNED
    )
    assert contexts["user_visible_saved_card_detach"].safety_class == (
        retry_policy.RetrySafetyClass.RECONCILE_BEFORE_RETRY
    )
    assert contexts["account_deletion_saved_card_cleanup"].durable_follow_up == (
        "WS05 durable account cleanup recovery."
    )
    assert contexts["account_deletion_auth_cleanup"].safety_class == (
        retry_policy.RetrySafetyClass.RECONCILE_BEFORE_RETRY
    )
    assert contexts["admin_credit_repair_state_gate"].provider == "application"
    assert not contexts["admin_credit_repair_state_gate"].provider_mutation
