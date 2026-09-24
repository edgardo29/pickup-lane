from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

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

    refund_id = uuid.uuid4()
    return Refund(
        id=refund_id,
        payment_id=payment.id,
        booking_id=booking.id,
        participant_id=None,
        host_publish_fee_id=None,
        provider_refund_id=None,
        origin_operation_key=f"direct_admin_refund:refund:{refund_id}",
        current_attempt_number=1,
        stripe_request_key=f"refund:{refund_id}:attempt:1",
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
    from backend.services.refund_event_service import record_refund_event

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
    if provider_status == "failed":
        refund.provider_refund_id = f"re_ws05_03a_failed_{uuid.uuid4().hex}"
        refund.provider_attempt_started_at = datetime.now(timezone.utc)
    db.add(refund)
    db.flush()
    if provider_status == "failed":
        record_refund_event(
            db,
            refund=refund,
            event_type="provider_result_recorded",
            event_source="system",
            provider_refund_id=refund.provider_refund_id,
            provider_charge_id=payment.provider_charge_id,
            provider_status="failed",
            new_refund_status="failed",
            reason_code="refund_fixture_provider_failed",
            summary="Refund fixture provider attempt failed.",
        )
    elif provider_status is None:
        record_refund_event(
            db,
            refund=refund,
            event_type="local_status_changed",
            event_source="system",
            provider_refund_id=None,
            provider_status=None,
            new_refund_status="failed",
            reason_code="provider_charge_id_missing",
            summary="Refund fixture proves no provider call started.",
            metadata={"provider_call_started": False},
        )
    db.commit()
    return admin, user, payment, refund


def _queue_refund_job(db: Session, refund) -> None:
    from backend.services.payment_job_service import build_production_job_registry
    from backend.services.refund_fulfillment_service import (
        enqueue_refund_fulfillment_job,
    )

    now = datetime.now(timezone.utc)
    refund.refund_status = "approved"
    refund.approved_at = now
    refund.provider_status = None
    refund.provider_refund_id = None
    refund.provider_attempt_started_at = None
    refund.refunded_at = None
    db.add(refund)
    enqueue_refund_fulfillment_job(
        db, refund=refund, registry=build_production_job_registry()
    )
    db.commit()


def _run_one_refund_job(*, event_emitter=None) -> str:
    from backend.database import SessionLocal
    from backend.services.durable_job_service import DurableJobRunner
    from backend.services.payment_job_service import build_production_job_registry

    return DurableJobRunner(
        session_factory=SessionLocal,
        registry=build_production_job_registry(),
        worker_identity=f"ws05-03a-test-worker-{uuid.uuid4()}",
        event_emitter=event_emitter,
    ).process_once()


@pytest.mark.requirement("WS02-04C2-R6")
def test_admin_refund_retry_rejects_uncertain_provider_status_without_job() -> None:
    import backend.services.admin_money_refund_service as refund_service
    from backend.models import AdminAction
    from backend.schemas.admin_money_refund_schema import AdminMoneyRefundRetryCreate
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
        assert _count(db, AdminAction) == 0


@pytest.mark.requirement("WS05-03A-R2")
@pytest.mark.parametrize(
    ("sibling_outcome", "sibling_status"),
    [
        ("manual_review", "pending"),
        ("credit", "applied"),
        ("forfeit", "applied"),
        ("refund", "pending"),
    ],
)
def test_publish_fee_retry_is_blocked_by_every_active_sibling_decision(
    sibling_outcome: str,
    sibling_status: str,
) -> None:
    from backend.models import (
        AdminAction,
        AdminFinancialOutcome,
        Booking,
        DurableJob,
        HostPublishFee,
    )
    from backend.schemas.admin_money_refund_schema import AdminMoneyRefundRetryCreate
    from backend.services.admin_financial_outcome_service import (
        reclassify_superseded_publish_refund_issues,
    )
    from backend.services.admin_money_issue_service import stage_refund_money_issue
    from backend.services.admin_money_refund_query_service import (
        refund_available_actions,
    )
    from backend.services.admin_money_refund_service import retry_admin_money_refund

    now = datetime.now(timezone.utc)
    with _session() as db:
        admin, user, payment, refund = _target_state(db, provider_status="failed")
        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        payment.payment_type = "community_publish_fee"
        payment.booking_id = None
        refund.booking_id = None
        fee = HostPublishFee(
            id=uuid.uuid4(),
            game_id=booking.game_id,
            host_user_id=user.id,
            payment_id=payment.id,
            amount_cents=payment.amount_cents,
            currency="USD",
            fee_status="paid",
            waiver_reason="none",
            paid_at=now,
        )
        refund.host_publish_fee_id = fee.id
        refund.origin_workflow = "community_publish_fee_refund"
        refund.refund_reason = "publish_fee_refund"
        db.add_all([payment, fee, refund])
        db.flush()
        sibling_refund = None
        if sibling_outcome == "refund":
            sibling_refund = _refund(payment, booking, provider_status=None)
            sibling_refund.host_publish_fee_id = fee.id
            sibling_refund.origin_workflow = "community_publish_fee_refund"
            sibling_refund.refund_reason = "publish_fee_refund"
            sibling_refund.refund_status = "approved"
            sibling_refund.approved_at = now
            db.add(sibling_refund)
            db.flush()
        sibling = AdminFinancialOutcome(
            id=uuid.uuid4(),
            target_game_id=booking.game_id,
            host_user_id=user.id,
            host_publish_fee_id=fee.id,
            payment_id=payment.id,
            refund_id=sibling_refund.id if sibling_refund is not None else None,
            outcome=sibling_outcome,
            applied_status=sibling_status,
            amount_cents=payment.amount_cents,
            currency="USD",
            reason="Authoritative sibling decision.",
            created_by_user_id=admin.id,
            applied_by_user_id=admin.id if sibling_status == "applied" else None,
            applied_at=now if sibling_status == "applied" else None,
        )
        db.add(sibling)
        issue = stage_refund_money_issue(
            db,
            refund=refund,
            payment=payment,
            issue_type="refund_failed",
            reason_code="provider_failed",
            summary="The cash attempt requires review.",
        )
        reclassify_superseded_publish_refund_issues(
            db, financial_outcome=sibling, admin_user=admin
        )
        db.commit()

        assert issue.status == "open"
        assert issue.recommended_action_code == "review_superseding_financial_outcome"
        retry_action = next(
            action
            for action in refund_available_actions(
                db,
                refund=refund,
                payment=payment,
                linked_money_issue=issue,
            )
            if action.action_code == "retry_refund"
        )
        assert retry_action.enabled is False
        assert any("supersedes" in blocker for blocker in retry_action.blockers)

        with pytest.raises(HTTPException) as exc_info:
            retry_admin_money_refund(
                db,
                admin_user=admin,
                refund_id=refund.id,
                payload=AdminMoneyRefundRetryCreate(
                    reason="Retry must remain blocked.",
                    idempotency_key=f"ws05-03a-active-sibling-{sibling_outcome}",
                ),
            )
        db.rollback()

        assert exc_info.value.status_code == 409
        assert _count(db, AdminAction) == 0
        assert _count(db, DurableJob) == 0


@pytest.mark.requirement("WS05-03A-R2")
@pytest.mark.parametrize(
    "blocked_state",
    ["missing_attempt", "historical_conflict", "active_reservation"],
)
def test_refund_retry_projection_and_mutation_share_fail_closed_policy(
    blocked_state: str,
) -> None:
    from backend.models import AdminAction, Booking, DurableJob
    from backend.schemas.admin_money_refund_schema import AdminMoneyRefundRetryCreate
    from backend.services.admin_money_refund_query_service import (
        refund_available_actions,
    )
    from backend.services.admin_money_refund_service import retry_admin_money_refund

    with _session() as db:
        admin, _user_row, payment, refund = _target_state(
            db, provider_status="failed"
        )
        if blocked_state == "missing_attempt":
            refund.current_attempt_number = 2
            refund.stripe_request_key = f"refund:{refund.id}:attempt:2"
        elif blocked_state == "historical_conflict":
            refund.automatic_mutation_blocked_reason = "historical_attempt_conflict"
            refund.automatic_mutation_blocked_at = datetime.now(timezone.utc)
        else:
            booking = db.get(Booking, refund.booking_id)
            assert booking is not None
            sibling = _refund(payment, booking, provider_status=None)
            sibling.booking_id = refund.booking_id
            sibling.refund_status = "approved"
            sibling.approved_at = datetime.now(timezone.utc)
            sibling.provider_status = None
            sibling.provider_attempt_started_at = None
            db.add(sibling)
        db.add(refund)
        db.commit()

        retry_action = next(
            action
            for action in refund_available_actions(db, refund=refund, payment=payment)
            if action.action_code == "retry_refund"
        )
        assert retry_action.enabled is False

        with pytest.raises(HTTPException) as exc_info:
            retry_admin_money_refund(
                db,
                admin_user=admin,
                refund_id=refund.id,
                payload=AdminMoneyRefundRetryCreate(
                    reason="The projected blocker must also block mutation.",
                    idempotency_key=f"ws05-03a-parity-{blocked_state}",
                ),
            )
        db.rollback()

        assert exc_info.value.status_code == 409
        assert _count(db, AdminAction) == 0
        assert _count(db, DurableJob) == 0


@pytest.mark.requirement("WS05-03A-R2")
def test_refund_retry_zero_remainder_projects_no_provider_work_and_resolves_no_action() -> None:
    from backend.models import AdminAction, Booking, DurableJob
    from backend.schemas.admin_money_refund_schema import AdminMoneyRefundRetryCreate
    from backend.services.admin_money_refund_query_service import (
        refund_available_actions,
    )
    from backend.services.admin_money_refund_service import retry_admin_money_refund
    from backend.services.refund_event_service import record_refund_event

    with _session() as db:
        admin, _user_row, payment, refund = _target_state(
            db, provider_status="failed"
        )
        booking = db.get(Booking, refund.booking_id)
        assert booking is not None
        sibling = _refund(payment, booking, provider_status="succeeded")
        sibling.amount_cents = payment.amount_cents
        sibling.refund_status = "succeeded"
        sibling.provider_status = "succeeded"
        sibling.provider_refund_id = f"re_ws05_03a_settled_{uuid.uuid4().hex}"
        sibling.refunded_at = datetime.now(timezone.utc)
        db.add(sibling)
        db.flush()
        record_refund_event(
            db,
            refund=sibling,
            event_type="provider_result_recorded",
            event_source="system",
            provider_refund_id=sibling.provider_refund_id,
            provider_charge_id=payment.provider_charge_id,
            provider_status="succeeded",
            new_refund_status="succeeded",
            reason_code="sibling_refund_succeeded",
            summary="Sibling refund returned the entire collected amount.",
        )
        db.commit()

        retry_action = next(
            action
            for action in refund_available_actions(db, refund=refund, payment=payment)
            if action.action_code == "retry_refund"
        )
        assert retry_action.enabled is False
        assert any("No refundable cash remains" in item for item in retry_action.blockers)

        detail = retry_admin_money_refund(
            db,
            admin_user=admin,
            refund_id=refund.id,
            payload=AdminMoneyRefundRetryCreate(
                reason="Record that no cash obligation remains.",
                idempotency_key="ws05-03a-zero-remainder",
            ),
        )

        assert detail.refund.id == refund.id
        db.refresh(refund)
        assert refund.refund_status == "failed"
        assert refund.current_attempt_number == 1
        assert _count(db, AdminAction) == 1
        assert _count(db, DurableJob) == 0


@pytest.mark.requirement("WS05-03A-R2")
def test_attempt_terminal_proof_requires_every_expected_attempt() -> None:
    from backend.models import RefundEvent
    from backend.services.refund_attempt_policy import (
        refund_has_only_terminal_attempts,
    )
    from backend.services.refund_event_service import record_refund_event

    with _session() as db:
        _admin, _user_row, _payment_row, refund = _target_state(
            db, provider_status="failed"
        )
        refund.current_attempt_number = 2
        refund.stripe_request_key = f"refund:{refund.id}:attempt:2"
        refund.provider_refund_id = None
        refund.provider_status = None
        refund.provider_attempt_started_at = None
        db.add(refund)
        record_refund_event(
            db,
            refund=refund,
            event_type="local_status_changed",
            event_source="system",
            new_refund_status="failed",
            reason_code="attempt_two_never_started",
            summary="Attempt two ended before any provider call started.",
            metadata={"provider_call_started": False},
        )
        db.flush()
        assert refund_has_only_terminal_attempts(db, refund) is True

        attempt_one = db.scalars(
            select(RefundEvent).where(
                RefundEvent.refund_id == refund.id,
                RefundEvent.attempt_number == 1,
            )
        ).one()
        db.delete(attempt_one)
        db.flush()

        assert refund_has_only_terminal_attempts(db, refund) is False


@pytest.mark.requirement("WS05-03A-R2")
def test_attempt_provider_identity_conflict_blocks_historical_selection() -> None:
    from backend.services.admin_money_refund_service import (
        canonical_historical_provider_attempts,
    )
    from backend.services.refund_attempt_policy import (
        refund_has_only_terminal_attempts,
    )
    from backend.services.refund_event_service import (
        get_refund_attempt_by_provider_refund_id,
        record_refund_event,
    )

    with _session() as db:
        _admin, _user_row, payment, refund = _target_state(
            db, provider_status="failed"
        )
        original_provider_id = refund.provider_refund_id
        assert original_provider_id is not None
        conflicting_provider_id = f"re_ws05_03a_conflict_{uuid.uuid4().hex}"
        record_refund_event(
            db,
            refund=refund,
            event_type="reconciliation_checked",
            event_source="reconciliation",
            provider_refund_id=conflicting_provider_id,
            provider_charge_id=payment.provider_charge_id,
            provider_status="failed",
            new_refund_status="failed",
            reason_code="conflicting_provider_identity",
            summary="A contradictory provider identity was observed.",
            apply_to_refund=False,
        )
        refund.current_attempt_number = 2
        refund.stripe_request_key = f"refund:{refund.id}:attempt:2"
        refund.provider_refund_id = None
        refund.provider_status = None
        refund.provider_attempt_started_at = None
        db.add(refund)
        db.flush()

        assert refund_has_only_terminal_attempts(db, refund) is False
        assert get_refund_attempt_by_provider_refund_id(
            db,
            provider="stripe",
            provider_refund_id=original_provider_id,
        ) is None
        with pytest.raises(HTTPException) as conflict:
            canonical_historical_provider_attempts(db, refund=refund)
        assert conflict.value.status_code == 409


@pytest.mark.requirement("WS05-03A-R2")
def test_historical_selection_ignores_audit_only_provider_reference() -> None:
    from backend.services.admin_money_refund_service import (
        canonical_historical_provider_attempts,
    )
    from backend.services.refund_event_service import record_refund_event

    with _session() as db:
        _admin, _user_row, payment, refund = _target_state(
            db, provider_status="failed"
        )
        authoritative_provider_id = refund.provider_refund_id
        assert authoritative_provider_id is not None
        audit_provider_id = f"re_ws05_03a_audit_{uuid.uuid4().hex}"
        record_refund_event(
            db,
            refund=refund,
            event_type="provider_outcome_unknown",
            event_source="admin",
            provider_refund_id=audit_provider_id,
            provider_charge_id=payment.provider_charge_id,
            provider_status="unknown",
            new_refund_status=None,
            reason_code="audit_only_provider_reference",
            summary="This audit event cannot define attempt identity.",
            apply_to_refund=False,
        )
        refund.current_attempt_number = 2
        refund.stripe_request_key = f"refund:{refund.id}:attempt:2"
        refund.provider_refund_id = None
        refund.provider_status = None
        refund.provider_attempt_started_at = None
        db.add(refund)
        db.flush()

        selected = canonical_historical_provider_attempts(db, refund=refund)
        assert selected[1].provider_refund_id == authoritative_provider_id
        assert selected[1].provider_refund_id != audit_provider_id


@pytest.mark.requirement("WS05-03A-R2")
def test_imported_attempt_zero_requires_authoritative_terminal_proof_before_retry() -> None:
    from backend.models import RefundEvent
    from backend.schemas.admin_money_refund_schema import AdminMoneyRefundRetryCreate
    from backend.services.admin_money_refund_service import retry_admin_money_refund
    from backend.services.refund_attempt_policy import (
        refund_has_only_terminal_attempts,
    )
    from backend.services.refund_event_service import record_refund_event

    with _session() as db:
        admin, _user_row, _payment_row, refund = _target_state(
            db, provider_status="failed"
        )
        for event in db.scalars(
            select(RefundEvent).where(RefundEvent.refund_id == refund.id)
        ).all():
            db.delete(event)
        refund.current_attempt_number = 0
        refund.stripe_request_key = None
        refund.provider_refund_id = f"re_ws05_03a_imported_{uuid.uuid4().hex}"
        refund.provider_status = "failed"
        refund.provider_attempt_started_at = None
        db.add(refund)
        db.flush()
        assert refund_has_only_terminal_attempts(db, refund) is False

        record_refund_event(
            db,
            refund=refund,
            event_type="provider_result_recorded",
            event_source="system",
            provider_refund_id=refund.provider_refund_id,
            provider_status="failed",
            new_refund_status="failed",
            reason_code="legacy_provider_attempt_failed",
            summary="Imported attempt zero has authoritative provider evidence.",
            attempt_number=0,
            attempt_request_key=None,
        )
        db.commit()
        assert refund_has_only_terminal_attempts(db, refund) is True

        retry_admin_money_refund(
            db,
            admin_user=admin,
            refund_id=refund.id,
            payload=AdminMoneyRefundRetryCreate(
                reason="Retry the proven imported failure.",
                idempotency_key="ws05-03a-imported-attempt-zero",
            ),
        )
        db.refresh(refund)
        assert refund.current_attempt_number == 1
        assert refund.stripe_request_key == f"refund:{refund.id}:attempt:1"
        assert refund.refund_status == "approved"


@pytest.mark.requirement("WS05-03A-R2")
def test_refund_event_replay_requires_complete_immutable_identity() -> None:
    from backend.services.refund_event_service import record_refund_event

    with _session() as db:
        admin, _user_one, _payment_one, refund_one = _target_state(
            db, provider_status="failed"
        )
        _other_admin, _user_two, _payment_two, refund_two = _target_state(
            db, provider_status="failed"
        )
        replay_key = "client-key-reused-across-refunds"
        event = record_refund_event(
            db,
            refund=refund_one,
            event_type="local_status_changed",
            event_source="admin",
            actor_user_id=admin.id,
            idempotency_key=replay_key,
            new_refund_status=None,
            reason_code="admin_review_recorded",
            summary="Admin review recorded without changing financial state.",
            apply_to_refund=False,
        )
        db.flush()
        exact_replay = record_refund_event(
            db,
            refund=refund_one,
            event_type="local_status_changed",
            event_source="admin",
            actor_user_id=admin.id,
            idempotency_key=replay_key,
            new_refund_status=None,
            reason_code="admin_review_recorded",
            summary="Admin review recorded without changing financial state.",
            apply_to_refund=False,
        )
        assert exact_replay.id == event.id

        other_refund_event = record_refund_event(
            db,
            refund=refund_two,
            event_type="local_status_changed",
            event_source="admin",
            actor_user_id=admin.id,
            idempotency_key=replay_key,
            new_refund_status=None,
            reason_code="admin_review_recorded",
            summary="Admin review recorded without changing financial state.",
            apply_to_refund=False,
        )
        db.flush()
        assert other_refund_event.id != event.id
        assert other_refund_event.refund_id == refund_two.id


@pytest.mark.requirement("WS05-03A-R2")
def test_same_client_retry_key_on_different_refunds_creates_distinct_event_identities() -> None:
    from backend.models import RefundEvent
    from backend.schemas.admin_money_refund_schema import AdminMoneyRefundRetryCreate
    from backend.services.admin_money_refund_service import retry_admin_money_refund

    with _session() as db:
        admin, _user_one, _payment_one, refund_one = _target_state(
            db, provider_status="failed"
        )
        _other_admin, _user_two, _payment_two, refund_two = _target_state(
            db, provider_status="failed"
        )
        payload = AdminMoneyRefundRetryCreate(
            reason="Retry each distinct refund obligation.",
            idempotency_key="same-client-key-for-distinct-refunds",
        )

        retry_admin_money_refund(
            db,
            admin_user=admin,
            refund_id=refund_one.id,
            payload=payload,
        )
        retry_admin_money_refund(
            db,
            admin_user=admin,
            refund_id=refund_two.id,
            payload=payload,
        )

        retry_events = list(
            db.scalars(
                select(RefundEvent).where(
                    RefundEvent.refund_id.in_({refund_one.id, refund_two.id}),
                    RefundEvent.reason_code == "refund_retry_queued",
                )
            ).all()
        )
        assert len(retry_events) == 2
        assert {event.refund_id for event in retry_events} == {
            refund_one.id,
            refund_two.id,
        }
        assert len({event.idempotency_key for event in retry_events}) == 2
        for event in retry_events:
            assert event.idempotency_key is not None
            assert f"refund:{event.refund_id}:admin-action:" in event.idempotency_key
            assert event.idempotency_key.endswith(":attempt:2:queued")


@pytest.mark.requirement("WS05-03A-R2")
def test_payment_ledger_ignores_audit_only_success_and_holds_missing_sibling_attempt() -> None:
    from backend.models import Booking
    from backend.services.refund_event_service import record_refund_event
    from backend.services.refund_retry_policy import evaluate_refund_retry_eligibility
    from backend.services.refund_service import (
        get_refund_payment_ledger,
        validate_refund_amount_available,
    )

    with _session() as db:
        _admin, _user, payment, refund = _target_state(
            db, provider_status="failed"
        )
        record_refund_event(
            db,
            refund=refund,
            event_type="local_status_changed",
            event_source="admin",
            new_refund_status="succeeded",
            reason_code="audit_only_success_label",
            summary="Audit history must not prove returned cash.",
            apply_to_refund=False,
        )
        db.flush()
        ledger = get_refund_payment_ledger(
            db,
            payment_id=payment.id,
            payment_amount_cents=payment.amount_cents,
        )
        assert ledger.confirmed_returned_cents == 0
        assert ledger.unresolved_attempt_cents == 0

        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        sibling = _refund(payment, booking, provider_status="failed")
        sibling.amount_cents = max(1, payment.amount_cents // 2)
        sibling.current_attempt_number = 2
        sibling.stripe_request_key = f"refund:{sibling.id}:attempt:2"
        sibling.provider_refund_id = f"re_ws05_03a_gap_{uuid.uuid4().hex}"
        db.add(sibling)
        db.flush()
        record_refund_event(
            db,
            refund=sibling,
            event_type="provider_result_recorded",
            event_source="system",
            provider_refund_id=sibling.provider_refund_id,
            provider_charge_id=payment.provider_charge_id,
            provider_status="failed",
            new_refund_status="failed",
            reason_code="second_attempt_failed",
            summary="Attempt two failed while attempt one is missing.",
            attempt_number=2,
            attempt_request_key=sibling.stripe_request_key,
        )
        db.flush()

        eligibility = evaluate_refund_retry_eligibility(
            db, refund=refund, payment=payment
        )
        assert eligibility.provider_retry_allowed is False
        assert any(
            blocker.code == "sibling_refund_reservation"
            for blocker in eligibility.blockers
        )
        ledger = get_refund_payment_ledger(
            db,
            payment_id=payment.id,
            payment_amount_cents=payment.amount_cents,
        )
        assert ledger.confirmed_returned_cents == 0
        assert ledger.unresolved_attempt_cents == payment.amount_cents
        assert ledger.attempt_history_complete is False
        assert ledger.available_cents == 0
        with pytest.raises(HTTPException) as unavailable:
            validate_refund_amount_available(
                db,
                payment_id=payment.id,
                payment_amount_cents=payment.amount_cents,
                refund_amount_cents=1,
            )
        assert unavailable.value.status_code == 400


@pytest.mark.requirement("WS05-03A-R4", "WS05-03A-R5")
def test_equivalent_success_observation_does_not_reopen_read_refund_notice() -> None:
    from backend.models import Notification
    from backend.services.refund_fulfillment_service import apply_refund_provider_result
    from backend.services.stripe_service import StripeRefundResult

    with _session() as db:
        _admin, _user, payment, refund = _target_state(
            db, provider_status="failed"
        )
        result = StripeRefundResult(
            id=refund.provider_refund_id,
            status="succeeded",
            amount_cents=refund.amount_cents,
            currency=refund.currency,
            charge_id=payment.provider_charge_id,
            payment_intent_id=payment.provider_payment_intent_id,
            metadata={
                "refund_id": str(refund.id),
                "payment_id": str(payment.id),
                "attempt_number": "1",
            },
        )
        apply_refund_provider_result(
            db,
            refund=refund,
            payment=payment,
            result=result,
            event_source="system",
            provider_event_id=f"evt_first_{uuid.uuid4().hex}",
        )
        db.flush()
        notice = db.scalars(
            select(Notification).where(
                Notification.related_booking_id == payment.booking_id,
                Notification.notification_type == "booking_refunded",
            )
        ).one()
        read_at = datetime.now(timezone.utc)
        notice.is_read = True
        notice.read_at = read_at
        db.add(notice)
        db.flush()

        apply_refund_provider_result(
            db,
            refund=refund,
            payment=payment,
            result=result,
            event_source="webhook",
            provider_event_id=f"evt_equivalent_{uuid.uuid4().hex}",
        )
        db.flush()
        db.refresh(notice)
        assert notice.is_read is True
        assert notice.read_at == read_at


@pytest.mark.requirement("WS05-03A-R2")
def test_historical_identity_mismatch_keeps_stored_payment_event_failed() -> None:
    from backend.models import PaymentEvent
    from backend.services.stripe_webhook_service import process_refund_event

    with _session() as db:
        _admin, _user, payment, refund = _target_state(
            db, provider_status="failed"
        )
        historical_provider_id = refund.provider_refund_id
        refund.current_attempt_number = 2
        refund.stripe_request_key = f"refund:{refund.id}:attempt:2"
        refund.provider_refund_id = f"re_ws05_03a_current_{uuid.uuid4().hex}"
        refund.provider_status = "failed"
        db.add(refund)
        now = datetime.now(timezone.utc)
        event = PaymentEvent(
            id=uuid.uuid4(),
            payment_id=None,
            provider="stripe",
            provider_event_id=f"evt_ws05_03a_history_{uuid.uuid4().hex}",
            event_type="refund.updated",
            event_envelope={"type": "refund.updated"},
            provider_created_at=now,
            processing_status="pending",
            created_at=now,
        )
        db.add(event)
        db.flush()

        process_refund_event(
            db,
            event,
            {
                "type": "refund.updated",
                "data": {
                    "object": {
                        "id": historical_provider_id,
                        "status": "succeeded",
                        "amount": refund.amount_cents + 1,
                        "currency": "usd",
                        "charge": payment.provider_charge_id,
                        "payment_intent": payment.provider_payment_intent_id,
                        "metadata": {
                            "refund_id": str(refund.id),
                            "payment_id": str(payment.id),
                            "attempt_number": "1",
                        },
                    }
                },
            },
            now,
        )
        db.flush()
        assert event.processing_status == "failed"
        assert "historical_attempt_identity_mismatch" in event.processing_error_code


@pytest.mark.requirement("WS02-04C2-R6")
def test_admin_refund_reconciliation_records_state_gated_missing_provider_reference() -> None:
    import backend.services.admin_money_refund_service as refund_service
    from backend.models import MoneyIssue, RefundEvent
    from backend.schemas.admin_money_refund_schema import (
        AdminMoneyRefundReconcileCreate,
    )

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
        assert refund.refund_status == "failed"
        assert len(issues) == 1
        assert issues[0].issue_type == "refund_missing_provider_reference"


@pytest.mark.requirement("WS05-03A-R2")
@pytest.mark.parametrize(
    ("classification", "expected_status"),
    [("rate_limited", 503), ("unknown_outcome", 502)],
)
def test_admin_reconciliation_maps_provider_read_failures_without_financial_mutation(
    monkeypatch: pytest.MonkeyPatch,
    classification: str,
    expected_status: int,
) -> None:
    import backend.services.admin_money_refund_service as refund_service
    from backend.models import AdminAction, RefundEvent
    from backend.schemas.admin_money_refund_schema import (
        AdminMoneyRefundReconcileCreate,
    )
    from backend.services.stripe_service import StripeRefundOperationError

    with _session() as db:
        admin, _user, _payment, refund = _target_state(
            db, provider_status="failed"
        )
        refund.provider_attempt_started_at = datetime.now(timezone.utc)
        db.add(refund)
        db.commit()
        before_events = _count(db, RefundEvent)

        def fail_read(_provider_refund_id: str):
            raise StripeRefundOperationError(
                operation="retrieve",
                classification=classification,
                http_status=429 if classification == "rate_limited" else 503,
            )

        monkeypatch.setattr(refund_service, "retrieve_stripe_refund", fail_read)
        with pytest.raises(HTTPException) as exc_info:
            refund_service.reconcile_admin_money_refund(
                db,
                admin_user=admin,
                refund_id=refund.id,
                payload=AdminMoneyRefundReconcileCreate(
                    reason="Check provider state safely.",
                    idempotency_key=f"ws05-03a-provider-read-{classification}",
                ),
            )
        db.rollback()

        assert exc_info.value.status_code == expected_status
        assert exc_info.value.detail == "Stripe refund status could not be checked."
        assert _count(db, AdminAction) == 0
        assert _count(db, RefundEvent) == before_events


@pytest.mark.requirement("WS05-03A-R2")
def test_admin_reconciliation_can_verify_and_attach_missing_provider_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.admin_money_refund_service as refund_service
    from backend.models import BookingStatusHistory
    from backend.schemas.admin_money_refund_schema import (
        AdminMoneyRefundReconcileCreate,
    )
    from backend.services.stripe_service import StripeRefundResult

    provider_refund_id = f"re_ws05_03a_{uuid.uuid4().hex}"
    with _session() as db:
        admin, _user, payment, refund = _target_state(
            db,
            provider_status="unknown",
        )
        monkeypatch.setattr(
            refund_service,
            "retrieve_stripe_refund",
            lambda refund_id: StripeRefundResult(
                id=refund_id,
                status="succeeded",
                amount_cents=refund.amount_cents,
                currency=refund.currency,
                charge_id=payment.provider_charge_id,
                payment_intent_id=payment.provider_payment_intent_id,
                metadata={
                    "refund_id": str(refund.id),
                    "payment_id": str(payment.id),
                    "attempt_number": str(refund.current_attempt_number),
                },
            ),
        )

        refund_service.reconcile_admin_money_refund(
            db,
            admin_user=admin,
            refund_id=refund.id,
            payload=AdminMoneyRefundReconcileCreate(
                reason="verified missing provider refund",
                idempotency_key="ws05-03a-attach-provider-refund",
                provider_refund_id=provider_refund_id,
            ),
        )

        db.refresh(refund)
        assert refund.provider_refund_id == provider_refund_id
        assert refund.refund_status == "succeeded"
        history = list(
            db.scalars(
                select(BookingStatusHistory).where(
                    BookingStatusHistory.booking_id == refund.booking_id,
                    BookingStatusHistory.change_reason == "refund_summary_recalculated",
                )
            ).all()
        )
        assert len(history) == 1
        assert history[0].change_source == "admin"
        assert history[0].changed_by_user_id == admin.id

        exact_replay = refund_service.reconcile_admin_money_refund(
            db,
            admin_user=admin,
            refund_id=refund.id,
            payload=AdminMoneyRefundReconcileCreate(
                reason="verified missing provider refund",
                idempotency_key="ws05-03a-attach-provider-refund",
                provider_refund_id=provider_refund_id,
            ),
        )
        assert exact_replay.refund.id == refund.id

        with pytest.raises(HTTPException) as reason_conflict:
            refund_service.reconcile_admin_money_refund(
                db,
                admin_user=admin,
                refund_id=refund.id,
                payload=AdminMoneyRefundReconcileCreate(
                    reason="different replay reason",
                    idempotency_key="ws05-03a-attach-provider-refund",
                    provider_refund_id=provider_refund_id,
                ),
            )
        assert reason_conflict.value.status_code == 409

        with pytest.raises(HTTPException) as provider_conflict:
            refund_service.reconcile_admin_money_refund(
                db,
                admin_user=admin,
                refund_id=refund.id,
                payload=AdminMoneyRefundReconcileCreate(
                    reason="verified missing provider refund",
                    idempotency_key="ws05-03a-attach-provider-refund",
                    provider_refund_id=f"re_different_{uuid.uuid4().hex}",
                ),
            )
        assert provider_conflict.value.status_code == 409


@pytest.mark.requirement("WS05-03A-R2")
def test_admin_reconciliation_stages_processing_overdue_from_current_attempt_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.admin_money_refund_service as refund_service
    from backend.models import MoneyIssue
    from backend.schemas.admin_money_refund_schema import (
        AdminMoneyRefundReconcileCreate,
    )
    from backend.services.stripe_service import StripeRefundResult

    now = datetime.now(timezone.utc)
    provider_refund_id = f"re_ws05_03a_overdue_{uuid.uuid4().hex}"
    with _session() as db:
        admin, _user, payment, refund = _target_state(
            db,
            provider_status="unknown",
        )
        refund.refund_status = "processing"
        refund.provider_status = "processing"
        refund.provider_refund_id = provider_refund_id
        refund.provider_attempt_started_at = now - timedelta(hours=25)
        db.add(refund)
        db.commit()

        monkeypatch.setattr(
            refund_service,
            "retrieve_stripe_refund",
            lambda _provider_refund_id: StripeRefundResult(
                id=provider_refund_id,
                status="processing",
                amount_cents=refund.amount_cents,
                currency=refund.currency,
                charge_id=payment.provider_charge_id,
                payment_intent_id=payment.provider_payment_intent_id,
                metadata={
                    "refund_id": str(refund.id),
                    "payment_id": str(payment.id),
                    "attempt_number": str(refund.current_attempt_number),
                },
            ),
        )

        refund_service.reconcile_admin_money_refund(
            db,
            admin_user=admin,
            refund_id=refund.id,
            payload=AdminMoneyRefundReconcileCreate(
                reason="Verify the overdue processing refund.",
                idempotency_key="ws05-03a-processing-overdue",
            ),
        )

        issue = db.scalars(
            select(MoneyIssue).where(MoneyIssue.target_refund_id == refund.id)
        ).one()
        assert issue.issue_type == "refund_processing_overdue"
        assert issue.latest_reason_code == "processing_threshold_reached"
        assert issue.recommended_action_code == "verify_provider_refund"


@pytest.mark.requirement("WS05-03A-R2")
def test_processing_age_is_scoped_to_current_attempt_and_imported_attempt_zero() -> None:
    from backend.models import Booking
    from backend.services.admin_money_refund_service import (
        refund_processing_threshold_reached,
    )
    from backend.services.refund_event_service import record_refund_event

    now = datetime.now(timezone.utc)
    with _session() as db:
        _admin, _user, payment, refund = _target_state(
            db, provider_status="failed"
        )
        old_provider_id = refund.provider_refund_id
        assert old_provider_id is not None
        record_refund_event(
            db,
            refund=refund,
            event_type="provider_result_recorded",
            event_source="system",
            provider_refund_id=old_provider_id,
            provider_charge_id=payment.provider_charge_id,
            provider_status="processing",
            new_refund_status="processing",
            reason_code="prior_attempt_processing",
            summary="The prior attempt was processing.",
            occurred_at=now - timedelta(hours=25),
            apply_to_refund=False,
        )
        refund.current_attempt_number = 2
        refund.stripe_request_key = f"refund:{refund.id}:attempt:2"
        refund.provider_refund_id = f"re_ws05_03a_current_{uuid.uuid4().hex}"
        refund.provider_status = "processing"
        refund.refund_status = "processing"
        refund.provider_attempt_started_at = now - timedelta(hours=1)
        db.add(refund)
        db.flush()

        assert not refund_processing_threshold_reached(db, refund=refund, now=now)

        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        imported = _refund(payment, booking, provider_status="processing")
        imported.current_attempt_number = 0
        imported.stripe_request_key = None
        imported.provider_refund_id = f"re_ws05_03a_imported_age_{uuid.uuid4().hex}"
        imported.provider_status = "processing"
        imported.refund_status = "processing"
        imported.provider_attempt_started_at = None
        db.add(imported)
        db.flush()
        record_refund_event(
            db,
            refund=imported,
            event_type="provider_result_recorded",
            event_source="system",
            provider_refund_id=imported.provider_refund_id,
            provider_charge_id=payment.provider_charge_id,
            provider_status="processing",
            new_refund_status="processing",
            reason_code="imported_attempt_processing",
            summary="The imported attempt remained processing.",
            occurred_at=now - timedelta(hours=25),
            attempt_number=0,
            attempt_request_key=None,
        )
        db.flush()

        assert refund_processing_threshold_reached(db, refund=imported, now=now)


@pytest.mark.requirement("WS02-04C2-R6")
def test_registry_keeps_manual_and_reconciliation_recovery_boundaries_explicit() -> None:
    contexts = {
        policy.workflow_context: policy
        for policy in retry_policy.PROVIDER_OPERATION_RETRY_POLICIES
    }

    assert contexts["admin_refund_retry_state_gate"].safety_class == (
        retry_policy.RetrySafetyClass.MANUAL_REPAIR
    )
    assert contexts["admin_refund_retry_state_gate"].dependency_retry_owner == (
        retry_policy.RetryOwnership.MANUAL_REPAIR
    )
    assert not contexts["admin_refund_retry_state_gate"].provider_mutation
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


@pytest.mark.requirement("WS05-03A-R2")
@pytest.mark.parametrize(
    ("provider_status", "runner_result", "refund_status", "job_status"),
    [
        ("succeeded", "succeeded", "succeeded", "succeeded"),
        ("failed", "succeeded", "failed", "succeeded"),
        ("pending", "retry_waiting", "processing", "retry_waiting"),
    ],
)
def test_refund_durable_runner_maps_financial_outcomes_to_job_states(
    monkeypatch: pytest.MonkeyPatch,
    provider_status: str,
    runner_result: str,
    refund_status: str,
    job_status: str,
) -> None:
    from backend.models import BookingStatusHistory, DurableJob, MoneyIssue, Refund
    from backend.services import refund_fulfillment_service as fulfillment
    from backend.services.stripe_service import StripeRefundResult

    with _session() as db:
        _admin, _user_row, payment, refund = _target_state(db, provider_status=None)
        _queue_refund_job(db, refund)
        refund_id = refund.id
        payment_id = payment.id
        charge_id = payment.provider_charge_id
        payment_intent_id = payment.provider_payment_intent_id
        amount_cents = refund.amount_cents

    monkeypatch.setattr(fulfillment, "validate_refund_preflight", lambda _currency: None)
    def create_refund_after_checkpoint(**_kwargs) -> StripeRefundResult:
        with _session() as checkpoint_db:
            checkpoint = checkpoint_db.get(Refund, refund_id)
            assert checkpoint is not None
            assert checkpoint.refund_status == "processing"
            assert checkpoint.provider_attempt_started_at is not None
        return StripeRefundResult(
            id=f"re_ws05_03a_{uuid.uuid4().hex}",
            status=provider_status,
            amount_cents=amount_cents,
            currency="USD",
            charge_id=charge_id,
            payment_intent_id=payment_intent_id,
            metadata={
                "refund_id": str(refund_id),
                "payment_id": str(payment_id),
                "attempt_number": "1",
            },
        )

    monkeypatch.setattr(fulfillment, "create_refund", create_refund_after_checkpoint)

    assert _run_one_refund_job() == runner_result

    with _session() as db:
        persisted_refund = db.get(Refund, refund_id)
        job = db.scalars(
            select(DurableJob).where(
                DurableJob.origin_reference_type == "refund",
                DurableJob.origin_reference_id == str(refund_id),
            )
        ).one()
        assert persisted_refund is not None
        assert persisted_refund.refund_status == refund_status
        assert job.status == job_status
        issue_count = _count(db, MoneyIssue)
        assert issue_count == (1 if provider_status == "failed" else 0)
        history = list(
            db.scalars(
                select(BookingStatusHistory).where(
                    BookingStatusHistory.booking_id == persisted_refund.booking_id,
                    BookingStatusHistory.change_reason == "refund_summary_recalculated",
                )
            ).all()
        )
        if provider_status == "succeeded":
            assert len(history) == 1
            assert history[0].change_source == "scheduled_job"
            assert history[0].changed_by_user_id is None
        else:
            assert history == []


@pytest.mark.requirement("WS05-03A-R2")
def test_refund_durable_runner_exhausts_final_unknown_attempt_and_stages_issue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import DurableJob, MoneyIssue, Refund
    from backend.services import refund_fulfillment_service as fulfillment
    from backend.services.stripe_service import StripeRefundResult

    with _session() as db:
        _admin, _user_row, payment, refund = _target_state(db, provider_status=None)
        _queue_refund_job(db, refund)
        refund_id = refund.id
        payment_id = payment.id
        job = db.scalars(
            select(DurableJob).where(
                DurableJob.origin_reference_id == str(refund_id)
            )
        ).one()
        job.attempt_count = job.maximum_attempts - 1
        db.add(job)
        db.commit()
        charge_id = payment.provider_charge_id
        payment_intent_id = payment.provider_payment_intent_id
        amount_cents = refund.amount_cents

    monkeypatch.setattr(fulfillment, "validate_refund_preflight", lambda _currency: None)
    monkeypatch.setattr(
        fulfillment,
        "create_refund",
        lambda **_kwargs: StripeRefundResult(
            id=f"re_ws05_03a_{uuid.uuid4().hex}",
            status="pending",
            amount_cents=amount_cents,
            currency="USD",
            charge_id=charge_id,
            payment_intent_id=payment_intent_id,
            metadata={
                "refund_id": str(refund_id),
                "payment_id": str(payment_id),
                "attempt_number": "1",
            },
        ),
    )

    assert _run_one_refund_job() == "exhausted"

    with _session() as db:
        persisted_refund = db.get(Refund, refund_id)
        job = db.scalars(
            select(DurableJob).where(
                DurableJob.origin_reference_id == str(refund_id)
            )
        ).one()
        assert persisted_refund is not None
        assert persisted_refund.provider_status == "unknown"
        assert job.status == "exhausted"
        assert _count(db, MoneyIssue) == 1


@pytest.mark.requirement("WS05-03A-R2")
def test_expired_refund_claim_returns_terminal_boundary_before_next_eligible_job() -> None:
    from backend.models import DurableJob
    from backend.services.durable_job_service import (
        DurableJobQueuePolicy,
        TerminalClaimResult,
        claim_job,
    )
    from backend.services.payment_job_service import build_production_job_registry

    registry = build_production_job_registry()
    policy = DurableJobQueuePolicy()
    with _session() as db:
        _admin, _user, _payment, first_refund = _target_state(db, provider_status=None)
        _queue_refund_job(db, first_refund)
        _admin2, _user2, _payment2, second_refund = _target_state(
            db, provider_status=None
        )
        _queue_refund_job(db, second_refund)
        first_job = db.scalars(
            select(DurableJob).where(
                DurableJob.origin_reference_id == str(first_refund.id)
            )
        ).one()
        first_job.status = "leased"
        first_job.attempt_count = first_job.maximum_attempts
        first_job.lease_token = uuid.uuid4()
        first_job.lease_owner = "expired-worker"
        first_job.heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        first_job.lease_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        first_job_id = first_job.id
        second_refund_id = second_refund.id
        db.add(first_job)
        db.commit()

    with _session() as db:
        result = claim_job(
            db,
            registry=registry,
            worker_identity="recovery-worker",
            policy=policy,
        )
        assert isinstance(result, TerminalClaimResult)
        assert result.exhausted_job.job_id == first_job_id
        db.commit()

    with _session() as db:
        next_result = claim_job(
            db,
            registry=registry,
            worker_identity="next-worker",
            policy=policy,
        )
        assert next_result is not None
        assert not isinstance(next_result, TerminalClaimResult)
        assert next_result.job.origin_reference_id == str(second_refund_id)
        db.rollback()


@pytest.mark.requirement("WS05-03A-R2")
def test_worker_checkpoint_stops_unstarted_refund_when_payment_remainder_shrinks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import DurableJob, MoneyIssue, Refund
    from backend.services import refund_fulfillment_service as fulfillment
    from backend.services.refund_event_service import record_refund_event

    with _session() as db:
        _admin, _user_row, payment, refund = _target_state(db, provider_status=None)
        _queue_refund_job(db, refund)
        sibling = Refund(
            id=uuid.uuid4(),
            payment_id=payment.id,
            booking_id=payment.booking_id,
            participant_id=None,
            host_publish_fee_id=None,
            provider_refund_id=f"re_ws05_03a_sibling_{uuid.uuid4().hex}",
            origin_operation_key=f"direct_admin_refund:refund:{uuid.uuid4()}",
            current_attempt_number=1,
            stripe_request_key=None,
            origin_workflow="direct_admin_refund",
            provider="stripe",
            provider_status="succeeded",
            provider_charge_id=payment.provider_charge_id,
            amount_cents=800,
            currency="USD",
            refund_reason="admin_refund",
            refund_status="succeeded",
            requested_at=datetime.now(timezone.utc),
            approved_at=datetime.now(timezone.utc),
            refunded_at=datetime.now(timezone.utc),
        )
        sibling.origin_operation_key = f"direct_admin_refund:refund:{sibling.id}"
        sibling.stripe_request_key = f"refund:{sibling.id}:attempt:1"
        sibling.provider_attempt_started_at = datetime.now(timezone.utc)
        db.add(sibling)
        db.flush()
        record_refund_event(
            db,
            refund=sibling,
            event_type="provider_result_recorded",
            event_source="system",
            provider_refund_id=sibling.provider_refund_id,
            provider_charge_id=payment.provider_charge_id,
            provider_status="succeeded",
            new_refund_status="succeeded",
            reason_code="provider_succeeded",
            summary="Sibling origin returned part of the payment.",
        )
        db.commit()
        refund_id = refund.id

    provider_called = False

    def fail_if_called(**_kwargs):
        nonlocal provider_called
        provider_called = True
        raise AssertionError("provider mutation must not run")

    monkeypatch.setattr(fulfillment, "validate_refund_preflight", lambda _currency: None)
    monkeypatch.setattr(fulfillment, "create_refund", fail_if_called)

    assert _run_one_refund_job() == "succeeded"
    assert provider_called is False
    with _session() as db:
        persisted = db.get(Refund, refund_id)
        job = db.scalars(
            select(DurableJob).where(DurableJob.origin_reference_id == str(refund_id))
        ).one()
        assert persisted is not None
        assert persisted.refund_status == "failed"
        assert persisted.provider_attempt_started_at is None
        assert persisted.automatic_mutation_blocked_reason == "historical_attempt_conflict"
        assert job.status == "succeeded"
        assert _count(db, MoneyIssue) == 1


@pytest.mark.requirement("WS05-03A-R2")
@pytest.mark.parametrize("origin", ["cancellation", "player_removal"])
@pytest.mark.parametrize("confirmed_cents", [500, 1200])
def test_origin_refund_producers_reserve_only_payment_ledger_remainder(
    origin: str,
    confirmed_cents: int,
) -> None:
    from backend.models import Booking, DurableJob, Game, Refund
    from backend.services.game_cancellation_service import (
        create_official_cancellation_refunds,
    )
    from backend.services.official_game_player_removal_service import (
        execute_admin_removal_refunds,
    )
    from backend.services.refund_event_service import record_refund_event

    now = datetime.now(timezone.utc)
    with _session() as db:
        admin, _user_row, payment, prior = _target_state(db, provider_status="succeeded")
        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        game = db.get(Game, booking.game_id)
        assert game is not None
        prior.amount_cents = confirmed_cents
        prior.refund_status = "succeeded"
        prior.provider_refund_id = f"re_ws05_03a_prior_{uuid.uuid4().hex}"
        prior.provider_attempt_started_at = now
        prior.provider_status = "succeeded"
        prior.approved_at = now
        prior.refunded_at = now
        db.add(prior)
        record_refund_event(
            db,
            refund=prior,
            event_type="provider_result_recorded",
            event_source="system",
            provider_refund_id=prior.provider_refund_id,
            provider_charge_id=payment.provider_charge_id,
            provider_status="succeeded",
            new_refund_status="succeeded",
            reason_code="provider_succeeded",
            summary="Prior origin returned confirmed cash.",
        )
        db.flush()

        if origin == "cancellation":
            create_official_cancellation_refunds(
                db,
                game,
                booking,
                [payment],
                admin,
                now,
            )
        else:
            execute_admin_removal_refunds(
                db,
                admin_user=admin,
                game=game,
                booking=booking,
                payments=[payment],
                now=now,
            )
        db.flush()

        created = list(
            db.scalars(
                select(Refund).where(
                    Refund.payment_id == payment.id,
                    Refund.id != prior.id,
                )
            ).all()
        )
        if confirmed_cents == payment.amount_cents:
            assert created == []
            assert _count(db, DurableJob) == 0
        else:
            assert len(created) == 1
            assert created[0].amount_cents == payment.amount_cents - confirmed_cents
            assert created[0].refund_status == "approved"
            assert _count(db, DurableJob) == 1


@pytest.mark.requirement("WS05-03A-R2")
def test_player_removal_credit_failure_commits_issue_without_success_notice() -> None:
    from backend.models import (
        Booking,
        GameCredit,
        GameCreditUsage,
        MoneyIssue,
        Notification,
    )
    from backend.services.official_game_player_removal_service import (
        record_credit_return_failure,
    )

    now = datetime.now(timezone.utc)
    with _session() as db:
        admin, user, payment, _refund_row = _target_state(
            db, provider_status="failed"
        )
        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        credit = GameCredit(
            id=uuid.uuid4(),
            user_id=user.id,
            amount_cents=payment.amount_cents,
            available_cents=0,
            currency="USD",
            credit_status="used",
            credit_reason="admin_credit",
            source_game_id=booking.game_id,
            source_booking_id=booking.id,
            source_payment_id=payment.id,
            issued_by_user_id=admin.id,
            idempotency_key=f"ws05-03a-removal-credit-{uuid.uuid4()}",
            created_at=now,
            updated_at=now,
        )
        usage = GameCreditUsage(
            id=uuid.uuid4(),
            game_credit_id=credit.id,
            booking_id=booking.id,
            game_id=booking.game_id,
            payment_id=payment.id,
            amount_cents=payment.amount_cents,
            currency="USD",
            usage_type="redeem",
            usage_status="redeemed",
            idempotency_key=f"ws05-03a-removal-usage-{uuid.uuid4()}",
            reason_code="booking_payment",
            redeemed_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add_all([credit, usage])
        db.commit()
        usage_id = usage.id
        issue_booking_id = booking.id
        issue_game_id = booking.game_id

        record_credit_return_failure(
            db,
            admin_user=admin,
            game_id=issue_game_id,
            booking_id=issue_booking_id,
            detail="Synthetic credit restore failure.",
        )

    with _session() as verification_db:
        issue = verification_db.scalars(
            select(MoneyIssue).where(
                MoneyIssue.target_credit_usage_id == usage_id,
                MoneyIssue.status == "open",
            )
        ).one()
        assert issue.recommended_action_code == "reexecute_origin_workflow"
        assert issue.origin_workflow == "player_removal"
        assert verification_db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.related_booking_id == issue_booking_id)
        ) == 0


@pytest.mark.requirement("WS05-03A-R2")
def test_refund_runner_lease_loss_does_not_persist_provider_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import DurableJob, Refund
    from backend.services import refund_fulfillment_service as fulfillment
    from backend.services.stripe_service import StripeRefundResult

    with _session() as db:
        _admin, _user_row, payment, refund = _target_state(db, provider_status=None)
        _queue_refund_job(db, refund)
        refund_id = refund.id
        payment_id = payment.id
        charge_id = payment.provider_charge_id
        payment_intent_id = payment.provider_payment_intent_id
        amount_cents = refund.amount_cents

    monkeypatch.setattr(fulfillment, "validate_refund_preflight", lambda _currency: None)

    def lose_lease_after_provider_call(**_kwargs) -> StripeRefundResult:
        with _session() as competing_db:
            job = competing_db.scalars(
                select(DurableJob).where(
                    DurableJob.origin_reference_id == str(refund_id)
                )
            ).one()
            job.status = "retry_waiting"
            job.lease_token = None
            job.lease_owner = None
            job.lease_expires_at = None
            job.heartbeat_at = None
            job.available_at = datetime.now(timezone.utc) + timedelta(hours=1)
            competing_db.add(job)
            competing_db.commit()
        return StripeRefundResult(
            id=f"re_ws05_03a_lease_loss_{uuid.uuid4().hex}",
            status="succeeded",
            amount_cents=amount_cents,
            currency="USD",
            charge_id=charge_id,
            payment_intent_id=payment_intent_id,
            metadata={
                "refund_id": str(refund_id),
                "payment_id": str(payment_id),
                "attempt_number": "1",
            },
        )

    monkeypatch.setattr(fulfillment, "create_refund", lose_lease_after_provider_call)
    assert _run_one_refund_job() == "lease_lost"

    with _session() as db:
        persisted = db.get(Refund, refund_id)
        assert persisted is not None
        assert persisted.refund_status == "processing"
        assert persisted.provider_refund_id is None
        assert persisted.refunded_at is None


@pytest.mark.requirement("WS05-03A-R2")
def test_refund_exhaustion_survives_support_staging_failure_and_diagnostic_clears_after_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    from backend.models import DurableJob, Payment, Refund
    from backend.observability.structured_logging import RuntimeEventEmitter
    from backend.services import refund_fulfillment_service as fulfillment
    from backend.services.admin_money_refund_query_service import (
        build_refund_summaries,
        get_admin_money_refund_detail,
    )
    from backend.services.stripe_service import StripeRefundResult

    with _session() as db:
        admin, _user_row, payment, refund = _target_state(db, provider_status=None)
        _queue_refund_job(db, refund)
        refund_id = refund.id
        admin_id = admin.id
        payment_id = payment.id
        charge_id = payment.provider_charge_id
        payment_intent_id = payment.provider_payment_intent_id
        amount_cents = refund.amount_cents
        job = db.scalars(
            select(DurableJob).where(
                DurableJob.origin_reference_id == str(refund_id)
            )
        ).one()
        job.attempt_count = job.maximum_attempts - 1
        db.add(job)
        db.commit()

    provider_refund_id = f"re_ws05_03a_support_failure_{uuid.uuid4().hex}"
    metadata = {
        "refund_id": str(refund_id),
        "payment_id": str(payment_id),
        "attempt_number": "1",
    }
    monkeypatch.setattr(fulfillment, "validate_refund_preflight", lambda _currency: None)
    monkeypatch.setattr(
        fulfillment,
        "create_refund",
        lambda **_kwargs: StripeRefundResult(
            id=provider_refund_id,
            status="pending",
            amount_cents=amount_cents,
            currency="USD",
            charge_id=charge_id,
            payment_intent_id=payment_intent_id,
            metadata=metadata,
        ),
    )
    monkeypatch.setattr(
        fulfillment,
        "_stage_failure_issue",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("staging failed")),
    )

    emitter = RuntimeEventEmitter("worker", "test", "test-release")
    assert _run_one_refund_job(event_emitter=emitter) == "exhausted"
    import json

    emitted = [
        json.loads(line)
        for line in capsys.readouterr().out.splitlines()
        if line.strip()
    ]
    job_events = [
        row for row in emitted if row.get("event_name") == "durable_job.processed"
    ]
    assert job_events[-1]["stable_error_code"] == "JOB.REFUND_SUPPORT_STAGING_FAILED"

    with _session() as db:
        from backend.models import User

        persisted = db.get(Refund, refund_id)
        admin = db.get(User, admin_id)
        assert persisted is not None and admin is not None
        job = db.scalars(
            select(DurableJob).where(
                DurableJob.origin_reference_id == str(refund_id)
            )
        ).one()
        assert job.last_error_code == "refund_support_staging_failed"
        list_summary = build_refund_summaries(db, [persisted])[0]
        detail = get_admin_money_refund_detail(
            db, refund_id=refund_id, viewer_user=admin
        )
        assert list_summary.durable_job_diagnostic is not None
        assert detail.refund.durable_job_diagnostic is not None

        locked_payment = db.scalars(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        ).one()
        locked_refund = db.scalars(
            select(Refund).where(Refund.id == refund_id).with_for_update()
        ).one()
        fulfillment.apply_refund_provider_result(
            db,
            refund=locked_refund,
            payment=locked_payment,
            result=StripeRefundResult(
                id=provider_refund_id,
                status="succeeded",
                amount_cents=amount_cents,
                currency="USD",
                charge_id=charge_id,
                payment_intent_id=payment_intent_id,
                metadata=metadata,
            ),
            event_source="reconciliation",
        )
        db.commit()

        refreshed = db.get(Refund, refund_id)
        assert refreshed is not None
        assert build_refund_summaries(db, [refreshed])[0].durable_job_diagnostic is None
        assert (
            get_admin_money_refund_detail(
                db, refund_id=refund_id, viewer_user=admin
            ).refund.durable_job_diagnostic
            is None
        )


@pytest.mark.requirement("WS05-03A-R2")
def test_concurrent_refund_retry_exact_replay_creates_one_attempt_and_job() -> None:
    from backend.models import AdminAction, DurableJob, Refund, User
    from backend.schemas.admin_money_refund_schema import AdminMoneyRefundRetryCreate
    from backend.services.admin_money_refund_service import retry_admin_money_refund

    with _session() as db:
        admin, _user_row, _payment_row, refund = _target_state(
            db, provider_status="failed"
        )
        admin_id = admin.id
        refund_id = refund.id

    barrier = Barrier(2)
    payload = AdminMoneyRefundRetryCreate(
        reason="Concurrent exact replay.",
        idempotency_key="ws05-03a-concurrent-refund-retry",
    )

    def retry_once() -> uuid.UUID:
        with _session() as db:
            admin = db.get(User, admin_id)
            assert admin is not None
            barrier.wait()
            result = retry_admin_money_refund(
                db,
                admin_user=admin,
                refund_id=refund_id,
                payload=payload,
            )
            return result.refund.id

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: retry_once(), range(2)))

    assert results == [refund_id, refund_id]
    with _session() as db:
        persisted_refund = db.get(Refund, refund_id)
        assert persisted_refund is not None
        assert persisted_refund.current_attempt_number == 2
        assert persisted_refund.refund_status == "approved"
        assert (
            db.scalar(
                select(func.count()).select_from(DurableJob).where(
                    DurableJob.origin_reference_id == str(refund_id)
                )
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count()).select_from(AdminAction).where(
                    AdminAction.target_refund_id == refund_id,
                    AdminAction.idempotency_key
                    == "ws05-03a-concurrent-refund-retry",
                )
            )
            == 1
        )


@pytest.mark.requirement("WS05-03A-R2")
def test_concurrent_terminal_provider_observations_cannot_downgrade_success() -> None:
    from backend.models import MoneyIssue, Payment, Refund
    from backend.services.refund_fulfillment_service import apply_refund_provider_result
    from backend.services.stripe_service import StripeRefundResult

    with _session() as db:
        _admin, _user_row, payment, refund = _target_state(db, provider_status=None)
        refund.refund_status = "processing"
        refund.provider_attempt_started_at = datetime.now(timezone.utc)
        db.add(refund)
        db.commit()
        refund_id = refund.id
        payment_id = payment.id
        provider_refund_id = f"re_ws05_03a_race_{uuid.uuid4().hex}"
        metadata = {
            "refund_id": str(refund_id),
            "payment_id": str(payment_id),
            "attempt_number": "1",
        }
        charge_id = payment.provider_charge_id
        payment_intent_id = payment.provider_payment_intent_id
        amount_cents = refund.amount_cents

    barrier = Barrier(2)

    def observe(provider_status: str) -> str:
        with _session() as db:
            barrier.wait()
            payment = db.scalars(
                select(Payment).where(Payment.id == payment_id).with_for_update()
            ).one()
            refund = db.scalars(
                select(Refund).where(Refund.id == refund_id).with_for_update()
            ).one()
            apply_refund_provider_result(
                db,
                refund=refund,
                payment=payment,
                result=StripeRefundResult(
                    id=provider_refund_id,
                    status=provider_status,
                    amount_cents=amount_cents,
                    currency="USD",
                    charge_id=charge_id,
                    payment_intent_id=payment_intent_id,
                    metadata=metadata,
                ),
                event_source="reconciliation",
            )
            db.commit()
            return provider_status

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert set(executor.map(observe, ("failed", "succeeded"))) == {
            "failed",
            "succeeded",
        }

    with _session() as db:
        persisted_refund = db.get(Refund, refund_id)
        assert persisted_refund is not None
        assert persisted_refund.refund_status == "succeeded"
        issue = db.scalars(
            select(MoneyIssue).where(MoneyIssue.target_refund_id == refund_id)
        ).first()
        if issue is not None:
            assert issue.recommended_action_code == "review_and_resolve_no_action"


@pytest.mark.requirement("WS05-03A-R2")
def test_mismatched_provider_observation_preserves_actual_identity_without_false_success() -> None:
    from backend.models import RefundEvent
    from backend.services.refund_fulfillment_service import apply_refund_provider_result
    from backend.services.stripe_service import StripeRefundResult

    with _session() as db:
        _admin, _user_row, payment, refund = _target_state(
            db, provider_status="processing"
        )
        refund.refund_status = "processing"
        refund.provider_attempt_started_at = datetime.now(timezone.utc)
        db.add(refund)
        db.flush()
        observed_id = f"re_ws05_03a_mismatch_{uuid.uuid4().hex}"
        outcome, code = apply_refund_provider_result(
            db,
            refund=refund,
            payment=payment,
            result=StripeRefundResult(
                id=observed_id,
                status="succeeded",
                amount_cents=refund.amount_cents + 1,
                currency="USD",
                charge_id="ch_wrong",
                payment_intent_id=payment.provider_payment_intent_id,
                metadata={
                    "refund_id": str(refund.id),
                    "payment_id": str(payment.id),
                    "attempt_number": "1",
                },
            ),
            event_source="reconciliation",
        )
        db.flush()

        assert (outcome, code) == ("unsafe", "refund_invalid_provider_result")
        assert refund.refund_status == "processing"
        assert refund.provider_refund_id is None
        event = db.scalars(
            select(RefundEvent)
            .where(RefundEvent.refund_id == refund.id)
            .order_by(RefundEvent.occurred_at.desc(), RefundEvent.id.desc())
        ).first()
        assert event is not None
        assert event.provider_refund_id == observed_id
        assert event.provider_charge_id == "ch_wrong"
        assert event.provider_status == "succeeded"
        assert event.new_refund_status is None


@pytest.mark.requirement("WS05-03A-R2")
def test_reconciliation_reads_every_known_attempt_before_clearing_history_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import RefundEvent
    from backend.schemas.admin_money_refund_schema import (
        AdminMoneyRefundReconcileCreate,
    )
    from backend.services import admin_money_refund_service as refund_service
    from backend.services.stripe_service import StripeRefundResult

    current_provider_id = f"re_ws05_03a_current_{uuid.uuid4().hex}"
    with _session() as db:
        admin, _user_row, payment, refund = _target_state(
            db, provider_status="failed"
        )
        old_provider_id = refund.provider_refund_id
        assert old_provider_id is not None
        old_amount_cents = refund.amount_cents
        current_amount_cents = max(1, old_amount_cents // 2)
        refund.current_attempt_number = 2
        refund.amount_cents = current_amount_cents
        refund.stripe_request_key = f"refund:{refund.id}:attempt:2"
        refund.provider_refund_id = current_provider_id
        refund.provider_status = "failed"
        refund.refund_status = "failed"
        db.add(refund)
        db.commit()
        refund_id = refund.id
        payment_id = payment.id
        admin_id = admin.id
        charge_id = payment.provider_charge_id
        payment_intent_id = payment.provider_payment_intent_id

    calls: list[str] = []

    def retrieve(provider_id: str) -> StripeRefundResult:
        calls.append(provider_id)
        attempt_number = 1 if provider_id == old_provider_id else 2
        return StripeRefundResult(
            id=provider_id,
            status="succeeded" if attempt_number == 1 else "failed",
            amount_cents=(
                old_amount_cents if attempt_number == 1 else current_amount_cents
            ),
            currency="USD",
            charge_id=charge_id,
            payment_intent_id=payment_intent_id,
            metadata={
                "refund_id": str(refund_id),
                "payment_id": str(payment_id),
                "attempt_number": str(attempt_number),
            },
        )

    monkeypatch.setattr(refund_service, "retrieve_stripe_refund", retrieve)
    with _session() as db:
        from backend.models import User

        admin = db.get(User, admin_id)
        assert admin is not None
        refund_service.reconcile_admin_money_refund(
            db,
            admin_user=admin,
            refund_id=refund_id,
            payload=AdminMoneyRefundReconcileCreate(
                reason="Reconcile complete attempt history.",
                idempotency_key="ws05-03a-full-attempt-reconciliation",
            ),
        )

    assert set(calls) == {old_provider_id, current_provider_id}
    with _session() as db:
        from backend.models import Refund

        persisted = db.get(Refund, refund_id)
        assert persisted is not None
        assert persisted.automatic_mutation_blocked_reason is None
        assert db.scalar(
            select(func.count()).select_from(RefundEvent).where(
                RefundEvent.refund_id == refund_id,
                RefundEvent.attempt_number == 1,
                RefundEvent.new_refund_status == "succeeded",
            )
        ) == 1
        historical = db.scalars(
            select(RefundEvent).where(
                RefundEvent.refund_id == refund_id,
                RefundEvent.attempt_number == 1,
                RefundEvent.new_refund_status == "succeeded",
            )
        ).one()
        assert historical.attempt_amount_cents == old_amount_cents
        assert persisted.amount_cents == current_amount_cents


@pytest.mark.requirement("WS05-03A-R2")
def test_exhausted_refund_diagnostic_is_only_the_issue_free_fallback() -> None:
    from types import SimpleNamespace

    from backend.services.admin_money_refund_query_service import (
        refund_has_current_exhausted_diagnostic,
    )

    refund_id = uuid.uuid4()
    refund = SimpleNamespace(
        id=refund_id,
        stripe_request_key=f"refund:{refund_id}:attempt:2",
        current_attempt_number=2,
        automatic_mutation_blocked_reason=None,
        refund_status="failed",
        provider_status="failed",
    )
    payment = SimpleNamespace(amount_cents=1000)
    job = SimpleNamespace(
        status="exhausted",
        idempotency_key=refund.stripe_request_key,
        protected_identity={
            "refund_id": str(refund_id),
            "attempt_number": 2,
        },
    )
    open_issue = SimpleNamespace(status="open")

    def visible(**overrides) -> bool:
        values = {
            "payment": payment,
            "durable_job": job,
            "linked_issue": None,
            "confirmed_returned_cents": 0,
            "has_final_replacement": False,
            "has_final_no_action_resolution": False,
        }
        values.update(overrides)
        return refund_has_current_exhausted_diagnostic(refund, **values)

    assert visible() is True
    assert visible(linked_issue=open_issue) is False
    assert visible(linked_issue=open_issue, has_final_replacement=True) is False
    assert visible(has_final_replacement=True) is False
    assert visible(has_final_no_action_resolution=True) is False


@pytest.mark.requirement("WS05-03A-R2")
def test_compensation_recounts_remaining_cash_and_retry_resets_lifecycle() -> None:
    from backend.models import Booking, PaymentCompensation
    from backend.schemas.admin_money_refund_schema import AdminMoneyRefundRetryCreate
    from backend.services.admin_money_refund_service import retry_admin_money_refund
    from backend.services.refund_event_service import record_refund_event
    from backend.services.stripe_webhook_service import ensure_payment_compensation

    with _session() as db:
        admin, _user_row, payment, refund = _target_state(db, provider_status="succeeded")
        record_refund_event(
            db,
            refund=refund,
            event_type="provider_result_recorded",
            event_source="system",
            provider_refund_id=f"re_ws05_03a_prior_{uuid.uuid4().hex}",
            provider_charge_id=payment.provider_charge_id,
            provider_status="succeeded",
            new_refund_status="succeeded",
            reason_code="prior_refund_succeeded",
            summary="Prior partial refund succeeded.",
        )
        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        compensation = ensure_payment_compensation(
            db,
            payment=payment,
            booking=booking,
            reason="capacity_conflict",
            now=datetime.now(timezone.utc),
        )
        assert compensation.amount_cents == 1200
        compensation_refund_id = compensation.refund_id
        assert compensation_refund_id is not None
        compensation.status = "failed"
        compensation.error_code = "provider_failed"
        compensation.resolved_at = datetime.now(timezone.utc)
        compensation_refund = db.get(type(refund), compensation_refund_id)
        assert compensation_refund is not None
        assert compensation_refund.amount_cents == 700
        compensation_refund.refund_status = "failed"
        compensation_refund.provider_status = None
        compensation_refund.provider_attempt_started_at = None
        record_refund_event(
            db,
            refund=compensation_refund,
            event_type="local_status_changed",
            event_source="system",
            new_refund_status="failed",
            reason_code="provider_charge_id_missing",
            summary="Compensation retry fixture proves no provider call started.",
            metadata={"provider_call_started": False},
        )
        db.add_all([compensation, compensation_refund])
        db.commit()

        retry_admin_money_refund(
            db,
            admin_user=admin,
            refund_id=compensation_refund_id,
            payload=AdminMoneyRefundRetryCreate(
                reason="Retry remaining compensation.",
                idempotency_key="ws05-03a-compensation-retry-reset",
            ),
        )
        persisted = db.scalars(
            select(PaymentCompensation).where(
                PaymentCompensation.id == compensation.id
            )
        ).one()
        assert persisted.status == "required"
        assert persisted.amount_cents == payment.amount_cents
        assert persisted.error_code is None
        assert persisted.processing_started_at is None
        assert persisted.resolved_at is None


@pytest.mark.requirement("WS05-03A-R2")
def test_compensation_retry_with_no_remaining_cash_resolves_without_new_attempt() -> None:
    from backend.models import AdminAction, Booking, DurableJob, PaymentCompensation
    from backend.schemas.admin_money_refund_schema import AdminMoneyRefundRetryCreate
    from backend.services.admin_money_refund_service import retry_admin_money_refund
    from backend.services.refund_fulfillment_service import apply_refund_provider_result
    from backend.services.stripe_service import StripeRefundResult

    now = datetime.now(timezone.utc)
    with _session() as db:
        admin, _user_row, payment, failed_refund = _target_state(
            db, provider_status="failed"
        )
        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        compensation = PaymentCompensation(
            id=uuid.uuid4(),
            payment_id=payment.id,
            booking_id=booking.id,
            refund_id=failed_refund.id,
            action="refund",
            reason="capacity_conflict",
            amount_cents=payment.amount_cents,
            currency="USD",
            status="failed",
            error_code="provider_failed",
            resolved_at=now,
            created_at=now,
            updated_at=now,
        )
        sibling = _refund(payment, booking, provider_status=None)
        sibling.amount_cents = payment.amount_cents
        sibling.refund_status = "approved"
        sibling.approved_at = now
        db.add_all([compensation, sibling])
        db.flush()
        provider_refund_id = f"re_ws05_03a_zero_{uuid.uuid4().hex}"
        apply_refund_provider_result(
            db,
            refund=sibling,
            payment=payment,
            result=StripeRefundResult(
                id=provider_refund_id,
                status="succeeded",
                amount_cents=sibling.amount_cents,
                currency=sibling.currency,
                charge_id=payment.provider_charge_id,
                payment_intent_id=payment.provider_payment_intent_id,
                metadata={
                    "refund_id": str(sibling.id),
                    "payment_id": str(payment.id),
                    "attempt_number": "1",
                },
            ),
            event_source="system",
        )
        db.flush()
        assert compensation.status == "succeeded"
        db.commit()
        prior_attempt = failed_refund.current_attempt_number

        retry_admin_money_refund(
            db,
            admin_user=admin,
            refund_id=failed_refund.id,
            payload=AdminMoneyRefundRetryCreate(
                reason="Verify already satisfied compensation.",
                idempotency_key="ws05-03a-compensation-zero-no-action",
            ),
        )

        db.refresh(compensation)
        db.refresh(failed_refund)
        assert compensation.status == "succeeded"
        assert compensation.amount_cents == payment.amount_cents
        assert compensation.error_code is None
        assert compensation.resolved_at is not None
        assert failed_refund.current_attempt_number == prior_attempt
        action = db.scalars(
            select(AdminAction).where(
                AdminAction.target_refund_id == failed_refund.id,
                AdminAction.idempotency_key
                == "ws05-03a-compensation-zero-no-action",
            )
        ).one()
        assert action.outcome == "succeeded"
        assert "new_attempt_number" not in (action.metadata_ or {})
        assert db.scalar(
            select(func.count())
            .select_from(DurableJob)
            .where(DurableJob.origin_reference_id == str(failed_refund.id))
        ) == 0


@pytest.mark.requirement("WS05-03A-R2")
def test_compensation_waits_for_active_sibling_before_reserving_remainder() -> None:
    from backend.models import Booking
    from backend.services.refund_event_service import record_refund_event
    from backend.services.stripe_webhook_service import ensure_payment_compensation

    with _session() as db:
        _admin, _user_row, payment, sibling = _target_state(
            db, provider_status=None
        )
        sibling.refund_status = "approved"
        sibling.approved_at = datetime.now(timezone.utc)
        db.add(sibling)
        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        compensation = ensure_payment_compensation(
            db,
            payment=payment,
            booking=booking,
            reason="capacity_conflict",
            now=datetime.now(timezone.utc),
        )
        assert compensation.amount_cents == payment.amount_cents
        assert compensation.status == "required"
        assert compensation.refund_id is None

        record_refund_event(
            db,
            refund=sibling,
            event_type="provider_result_recorded",
            event_source="system",
            provider_status="failed",
            new_refund_status="failed",
            reason_code="sibling_failed",
            summary="The sibling reservation ended without returning cash.",
        )
        compensation = ensure_payment_compensation(
            db,
            payment=payment,
            booking=booking,
            reason="capacity_conflict",
            now=datetime.now(timezone.utc),
        )
        assert compensation.refund_id is not None
        compensation_refund = db.get(type(sibling), compensation.refund_id)
        assert compensation_refund is not None
        assert compensation_refund.amount_cents == payment.amount_cents


@pytest.mark.requirement("WS05-03A-R2")
def test_publish_credit_entitlement_identity_is_unique_across_sessions() -> None:
    from sqlalchemy.exc import IntegrityError

    from backend.models import HostPublishEntitlement

    with _session() as db:
        host = _user(90)
        db.add(host)
        db.commit()
        host_id = host.id

    source_outcome_id = uuid.uuid4()
    barrier = Barrier(2)

    def create_entitlement(_index: int) -> str:
        with _session() as db:
            barrier.wait()
            db.add(
                HostPublishEntitlement(
                    id=uuid.uuid4(),
                    host_user_id=host_id,
                    entitlement_type="refund_replacement",
                    status="available",
                    source="financial_outcome",
                    source_financial_outcome_id=source_outcome_id,
                )
            )
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                return "conflict"
            return "created"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(create_entitlement, range(2))) == [
            "conflict",
            "created",
        ]

    with _session() as db:
        assert (
            db.scalar(
                select(func.count()).select_from(HostPublishEntitlement).where(
                    HostPublishEntitlement.source_financial_outcome_id
                    == source_outcome_id
                )
            )
            == 1
        )


@pytest.mark.requirement("WS05-03A-R2")
def test_financial_outcome_and_manual_resolution_replays_require_exact_identity() -> None:
    from backend.models import Booking, Game, HostPublishFee
    from backend.schemas.admin_money_financial_outcome_schema import (
        AdminMoneyFinancialOutcomeCreate,
        AdminMoneyManualReviewResolveCreate,
    )
    from backend.services.admin_financial_outcome_service import (
        create_admin_financial_outcome,
        resolve_admin_manual_review,
    )
    from backend.services.refund_event_service import record_refund_event

    now = datetime.now(timezone.utc)
    with _session() as db:
        admin, user, payment, refund_row = _target_state(
            db, provider_status="failed"
        )
        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        game = db.get(Game, booking.game_id)
        assert game is not None
        game.game_type = "community"
        game.host_user_id = user.id
        game.payment_collection_type = "external_host"
        game.policy_mode = "custom_hosted"
        payment.payment_type = "community_publish_fee"
        payment.booking_id = None
        refund_row.booking_id = None
        fee = HostPublishFee(
            id=uuid.uuid4(),
            game_id=booking.game_id,
            host_user_id=user.id,
            payment_id=payment.id,
            amount_cents=payment.amount_cents,
            currency="USD",
            fee_status="paid",
            waiver_reason="none",
            paid_at=now,
        )
        refund_row.host_publish_fee_id = fee.id
        refund_row.origin_workflow = "community_publish_fee_refund"
        refund_row.refund_reason = "publish_fee_refund"
        db.add_all([payment, fee])
        record_refund_event(
            db,
            refund=refund_row,
            event_type="provider_result_recorded",
            event_source="reconciliation",
            provider_status="failed",
            new_refund_status="failed",
            reason_code="stripe_refund_failed",
            summary="The prior cash attempt is terminal.",
        )
        db.commit()

        create_payload = AdminMoneyFinancialOutcomeCreate(
            outcome="manual_review",
            reason="Review the collected publish fee.",
            internal_note="Stable request identity.",
            idempotency_key="ws05-03a-manual-review-shared-key",
            host_publish_fee_id=fee.id,
            amount_cents=payment.amount_cents,
        )
        manual = create_admin_financial_outcome(
            db, admin_user=admin, payload=create_payload
        )
        replay = create_admin_financial_outcome(
            db, admin_user=admin, payload=create_payload
        )
        assert replay.id == manual.id
        with pytest.raises(HTTPException) as create_conflict:
            create_admin_financial_outcome(
                db,
                admin_user=admin,
                payload=create_payload.model_copy(
                    update={"reason": "Different financial decision."}
                ),
            )
        assert create_conflict.value.status_code == 409
        db.rollback()

        resolution = AdminMoneyManualReviewResolveCreate(
            outcome="credit",
            reason="Issue the verified publish replacement.",
            internal_note="Resolved after staff review.",
            amount_cents=payment.amount_cents,
            idempotency_key="ws05-03a-manual-review-shared-key",
        )
        replacement = resolve_admin_manual_review(
            db,
            admin_user=admin,
            financial_outcome_id=manual.id,
            payload=resolution,
        )
        assert replacement.id != manual.id
        assert replacement.outcome == "credit"
        assert replacement.host_publish_entitlement_id is not None
        exact_replay = resolve_admin_manual_review(
            db,
            admin_user=admin,
            financial_outcome_id=manual.id,
            payload=resolution,
        )
        assert exact_replay.id == replacement.id
        with pytest.raises(HTTPException) as resolve_conflict:
            resolve_admin_manual_review(
                db,
                admin_user=admin,
                financial_outcome_id=manual.id,
                payload=resolution.model_copy(
                    update={"reason": "Conflicting replay reason."}
                ),
            )
        assert resolve_conflict.value.status_code == 409

@pytest.mark.requirement("WS05-03A-R2")
def test_provider_no_action_resolution_requires_payment_level_satisfaction() -> None:
    from backend.models import Booking, DurableJob, MoneyIssue
    from backend.schemas.admin_money_issue_schema import AdminMoneyIssueResolveCreate
    from backend.services.admin_money_issue_service import (
        resolve_admin_money_issue,
        stage_refund_money_issue,
        validate_money_issue_resolution,
    )
    from backend.services.admin_money_refund_query_service import build_refund_summaries
    from backend.services.payment_job_service import build_production_job_registry
    from backend.services.refund_event_service import record_refund_event
    from backend.services.refund_fulfillment_service import (
        enqueue_refund_fulfillment_job,
    )

    with _session() as db:
        admin, _user_row, payment, failed_refund = _target_state(
            db, provider_status="failed"
        )
        record_refund_event(
            db,
            refund=failed_refund,
            event_type="provider_result_recorded",
            event_source="system",
            provider_status="failed",
            new_refund_status="failed",
            reason_code="provider_failed",
            summary="The original attempt failed.",
        )
        issue = stage_refund_money_issue(
            db,
            refund=failed_refund,
            payment=payment,
            issue_type="refund_failed",
            reason_code="provider_failed",
            summary="The original attempt failed.",
        )
        db.flush()
        with pytest.raises(HTTPException):
            validate_money_issue_resolution(
                db,
                money_issue=issue,
                resolution_reason_code="provider_completed_no_action_required",
                resolution_note=None,
                resolution_external_reference=None,
            )

        booking = db.get(Booking, failed_refund.booking_id)
        assert booking is not None
        sibling = _refund(payment, booking, provider_status="succeeded")
        sibling.amount_cents = payment.amount_cents
        sibling.refund_status = "succeeded"
        sibling.provider_refund_id = f"re_ws05_03a_full_{uuid.uuid4().hex}"
        sibling.approved_at = datetime.now(timezone.utc)
        sibling.refunded_at = datetime.now(timezone.utc)
        db.add(sibling)
        db.flush()
        record_refund_event(
            db,
            refund=sibling,
            event_type="provider_result_recorded",
            event_source="system",
            provider_refund_id=sibling.provider_refund_id,
            provider_charge_id=payment.provider_charge_id,
            provider_status="succeeded",
            new_refund_status="succeeded",
            reason_code="provider_succeeded",
            summary="Another origin returned the full payment.",
        )
        db.flush()
        persisted_issue = db.get(MoneyIssue, issue.id)
        assert persisted_issue is not None
        validate_money_issue_resolution(
            db,
            money_issue=persisted_issue,
            resolution_reason_code="provider_completed_no_action_required",
            resolution_note=None,
            resolution_external_reference=None,
        )
        resolve_admin_money_issue(
            db,
            admin_user=admin,
            money_issue_id=persisted_issue.id,
            payload=AdminMoneyIssueResolveCreate(
                resolution_reason_code="provider_completed_no_action_required",
                resolution_note=None,
                resolution_external_reference=None,
                idempotency_key="ws05-03a-provider-no-action-resolution",
            ),
        )
        persisted_issue = db.get(MoneyIssue, issue.id)
        assert persisted_issue is not None
        occurrence_count = persisted_issue.occurrence_count

        enqueue_refund_fulfillment_job(
            db,
            refund=failed_refund,
            registry=build_production_job_registry(),
        )
        exhausted_job = db.scalars(
            select(DurableJob).where(
                DurableJob.origin_reference_id == str(failed_refund.id)
            )
        ).one()
        exhausted_job.status = "exhausted"
        exhausted_job.attempt_count = exhausted_job.maximum_attempts
        exhausted_job.exhausted_at = datetime.now(timezone.utc)
        exhausted_job.last_error_code = "refund_outcome_unknown"
        db.add(exhausted_job)
        db.flush()
        assert (
            build_refund_summaries(db, [failed_refund])[0].durable_job_diagnostic
            is None
        )

        staged_again = stage_refund_money_issue(
            db,
            refund=failed_refund,
            payment=payment,
            issue_type="refund_failed",
            reason_code="provider_failed_reobserved",
            summary="The failed target was observed after payment satisfaction.",
        )
        assert staged_again.status == "resolved"
        assert (
            staged_again.resolution_reason_code
            == "provider_completed_no_action_required"
        )
        assert staged_again.occurrence_count == occurrence_count


@pytest.mark.requirement("WS05-03A-R2")
def test_superseded_resolution_requires_exact_applied_replacement_and_terminal_history() -> None:
    from backend.models import (
        AdminAction,
        AdminFinancialOutcome,
        Booking,
        HostPublishFee,
        MoneyIssueEvent,
    )
    from backend.schemas.admin_money_issue_schema import AdminMoneyIssueResolveCreate
    from backend.services.admin_financial_outcome_service import (
        apply_credit_outcome,
        reclassify_superseded_publish_refund_issues,
    )
    from backend.services.admin_money_issue_service import (
        financial_outcome_safely_supersedes_refund,
        resolve_admin_money_issue,
        stage_refund_money_issue,
        validate_money_issue_resolution,
    )
    from backend.services.refund_event_service import record_refund_event

    now = datetime.now(timezone.utc)
    with _session() as db:
        admin, user, payment, failed_refund = _target_state(
            db, provider_status="failed"
        )
        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        game_id = booking.game_id
        fee = HostPublishFee(
            id=uuid.uuid4(),
            game_id=game_id,
            host_user_id=user.id,
            payment_id=payment.id,
            amount_cents=500,
            currency="USD",
            fee_status="paid",
            waiver_reason="none",
            paid_at=now,
        )
        db.add(fee)
        db.flush()
        failed_refund.host_publish_fee_id = fee.id
        failed_refund.origin_workflow = "community_publish_fee_refund"
        failed_refund.refund_reason = "publish_fee_refund"
        db.add(failed_refund)
        record_refund_event(
            db,
            refund=failed_refund,
            event_type="provider_result_recorded",
            event_source="system",
            provider_status="failed",
            new_refund_status="failed",
            reason_code="provider_failed",
            summary="The cash replacement failed terminally.",
        )
        issue = stage_refund_money_issue(
            db,
            refund=failed_refund,
            payment=payment,
            issue_type="refund_failed",
            reason_code="provider_failed",
            summary="The cash replacement failed terminally.",
        )
        replacement = AdminFinancialOutcome(
            id=uuid.uuid4(),
            target_game_id=game_id,
            host_user_id=user.id,
            host_publish_fee_id=fee.id,
            payment_id=payment.id,
            outcome="credit",
            applied_status="pending",
            amount_cents=500,
            currency="USD",
            reason="Replace failed cash refund with publish credit.",
            created_by_user_id=admin.id,
            applied_by_user_id=None,
            applied_at=None,
        )
        db.add(replacement)
        db.flush()
        apply_credit_outcome(
            db,
            financial_outcome=replacement,
            admin_user=admin,
            now=now,
        )

        assert financial_outcome_safely_supersedes_refund(
            db, refund=failed_refund, replacement=replacement
        )
        reclassify_superseded_publish_refund_issues(
            db, financial_outcome=replacement, admin_user=admin
        )
        assert issue.recommended_action_code == "review_superseding_financial_outcome"
        validate_money_issue_resolution(
            db,
            money_issue=issue,
            resolution_reason_code="superseded_by_financial_outcome",
            resolution_note=None,
            resolution_external_reference=None,
        )
        resolve_admin_money_issue(
            db,
            admin_user=admin,
            money_issue_id=issue.id,
            payload=AdminMoneyIssueResolveCreate(
                resolution_reason_code="superseded_by_financial_outcome",
                resolution_note=None,
                resolution_external_reference=None,
                idempotency_key="ws05-03a-replacement-resolution-audit",
            ),
        )
        staged_again = stage_refund_money_issue(
            db,
            refund=failed_refund,
            payment=payment,
            issue_type="refund_failed",
            reason_code="provider_failed_reobserved",
            summary="The terminal cash attempt was observed again.",
        )
        assert staged_again.status == "resolved"
        assert staged_again.resolution_reason_code == "superseded_by_financial_outcome"
        action = db.scalars(
            select(AdminAction).where(
                AdminAction.target_money_issue_id == issue.id,
                AdminAction.idempotency_key
                == "ws05-03a-replacement-resolution-audit",
            )
        ).one()
        event = db.scalars(
            select(MoneyIssueEvent)
            .where(MoneyIssueEvent.admin_action_id == action.id)
            .order_by(MoneyIssueEvent.occurred_at.desc())
        ).first()
        assert (action.metadata_ or {})["replacement_financial_outcome_id"] == str(
            replacement.id
        )
        assert event is not None
        assert (event.event_metadata or {})[
            "replacement_financial_outcome_id"
        ] == str(replacement.id)

        entitlement_id = replacement.host_publish_entitlement_id
        replacement.host_publish_entitlement_id = None
        assert not financial_outcome_safely_supersedes_refund(
            db, refund=failed_refund, replacement=replacement
        )
        replacement.host_publish_entitlement_id = entitlement_id
        replacement.amount_cents = 499
        assert not financial_outcome_safely_supersedes_refund(
            db, refund=failed_refund, replacement=replacement
        )
        with pytest.raises(HTTPException):
            validate_money_issue_resolution(
                db,
                money_issue=issue,
                resolution_reason_code="superseded_by_financial_outcome",
                resolution_note=None,
                resolution_external_reference=None,
            )


@pytest.mark.requirement("WS05-03A-R2")
@pytest.mark.parametrize(
    ("outcome", "invalid_field"),
    [
        ("credit", "payer"),
        ("forfeit", "payment_type"),
        ("manual_review", "payment_amount"),
        ("credit", "payment_status"),
        ("forfeit", "fee_status"),
    ],
)
def test_publish_fee_decisions_reject_invalid_collected_payment_identity_atomically(
    outcome: str,
    invalid_field: str,
) -> None:
    from backend.models import (
        AdminAction,
        AdminFinancialOutcome,
        Booking,
        Game,
        HostPublishEntitlement,
        HostPublishFee,
        Notification,
    )
    from backend.schemas.admin_money_financial_outcome_schema import (
        AdminMoneyFinancialOutcomeCreate,
    )
    from backend.services.admin_financial_outcome_service import (
        create_admin_financial_outcome,
    )

    now = datetime.now(timezone.utc)
    with _session() as db:
        admin, user, payment, _refund_row = _target_state(
            db, provider_status="failed"
        )
        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        game = db.get(Game, booking.game_id)
        assert game is not None
        game.game_type = "community"
        game.host_user_id = user.id
        game.payment_collection_type = "external_host"
        game.policy_mode = "custom_hosted"
        payment.payment_type = "community_publish_fee"
        payment.booking_id = None
        fee = HostPublishFee(
            id=uuid.uuid4(),
            game_id=game.id,
            host_user_id=user.id,
            payment_id=payment.id,
            amount_cents=payment.amount_cents,
            currency="USD",
            fee_status="paid",
            waiver_reason="none",
            paid_at=now,
        )
        db.add_all([game, payment, fee])
        db.commit()

        if invalid_field == "payer":
            other_user = _user(88)
            db.add(other_user)
            db.flush()
            payment.payer_user_id = other_user.id
        elif invalid_field == "payment_type":
            payment.payment_type = "admin_charge"
        elif invalid_field == "payment_amount":
            payment.amount_cents += 1
        elif invalid_field == "payment_status":
            payment.payment_status = "failed"
        elif invalid_field == "fee_status":
            fee.fee_status = "failed"
        db.add_all([payment, fee])
        db.commit()

        before = {
            "actions": _count(db, AdminAction),
            "entitlements": _count(db, HostPublishEntitlement),
            "notices": _count(db, Notification),
            "outcomes": _count(db, AdminFinancialOutcome),
        }
        with pytest.raises(HTTPException):
            create_admin_financial_outcome(
                db,
                admin_user=admin,
                payload=AdminMoneyFinancialOutcomeCreate(
                    outcome=outcome,
                    reason="Invalid collected payment must fail atomically.",
                    idempotency_key=(
                        f"ws05-03a-invalid-publish-{outcome}-{invalid_field}"
                    ),
                    host_publish_fee_id=fee.id,
                    amount_cents=fee.amount_cents,
                ),
            )
        db.rollback()
        assert {
            "actions": _count(db, AdminAction),
            "entitlements": _count(db, HostPublishEntitlement),
            "notices": _count(db, Notification),
            "outcomes": _count(db, AdminFinancialOutcome),
        } == before


@pytest.mark.requirement("WS05-03A-R2")
def test_money_issue_success_and_replacement_require_complete_attempt_history() -> None:
    from backend.models import (
        AdminFinancialOutcome,
        Booking,
        Game,
        HostPublishFee,
        MoneyIssue,
    )
    from backend.services.admin_money_issue_service import (
        financial_outcome_safely_supersedes_refund,
        validate_money_issue_resolution,
    )
    from backend.services.admin_money_refund_query_service import (
        final_replacement_host_publish_fee_ids,
    )
    from backend.services.refund_event_service import record_refund_event

    now = datetime.now(timezone.utc)
    with _session() as db:
        admin, user, payment, _fixture_refund = _target_state(
            db, provider_status="failed"
        )
        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        game = db.get(Game, booking.game_id)
        assert game is not None
        payment.payment_type = "community_publish_fee"
        payment.booking_id = None
        fee = HostPublishFee(
            id=uuid.uuid4(),
            game_id=game.id,
            host_user_id=user.id,
            payment_id=payment.id,
            amount_cents=payment.amount_cents,
            currency="USD",
            fee_status="paid",
            waiver_reason="none",
            paid_at=now,
        )
        replacement_refund = _refund(payment, booking, provider_status=None)
        replacement_refund.booking_id = None
        replacement_refund.host_publish_fee_id = fee.id
        replacement_refund.origin_workflow = "community_publish_fee_refund"
        replacement_refund.refund_reason = "publish_fee_refund"
        replacement_refund.current_attempt_number = 2
        replacement_refund.stripe_request_key = (
            f"refund:{replacement_refund.id}:attempt:2"
        )
        replacement_refund.provider_refund_id = f"re_ws05_03a_{uuid.uuid4().hex}"
        replacement_refund.provider_attempt_started_at = now
        replacement_refund.refund_status = "succeeded"
        replacement_refund.refunded_at = now
        replacement_refund.amount_cents = payment.amount_cents
        replacement = AdminFinancialOutcome(
            id=uuid.uuid4(),
            target_game_id=game.id,
            host_user_id=user.id,
            host_publish_fee_id=fee.id,
            payment_id=payment.id,
            refund_id=replacement_refund.id,
            outcome="refund",
            applied_status="applied",
            amount_cents=payment.amount_cents,
            currency="USD",
            reason="Replacement cash refund.",
            created_by_user_id=admin.id,
            applied_by_user_id=admin.id,
            applied_at=now,
        )
        issue = MoneyIssue(
            id=uuid.uuid4(),
            operation_key=f"refund:{replacement_refund.id}",
            status="open",
            issue_type="refund_failed",
            origin_workflow="community_publish_fee_refund",
            value_kind="cash_refund",
            target_user_id=user.id,
            target_payment_id=payment.id,
            target_refund_id=replacement_refund.id,
            amount_cents=payment.amount_cents,
            currency="USD",
            recommended_action_code="retry_refund",
            occurrence_count=1,
            reopen_count=0,
            first_detected_at=now,
            last_detected_at=now,
            last_activity_at=now,
            latest_reason_code="provider_failed",
            latest_summary="The refund attempt failed.",
        )
        db.add_all([payment, fee])
        db.flush()
        db.add(replacement_refund)
        db.flush()
        db.add_all([replacement, issue])
        db.flush()
        record_refund_event(
            db,
            refund=replacement_refund,
            event_type="provider_result_recorded",
            event_source="system",
            provider_refund_id=replacement_refund.provider_refund_id,
            provider_charge_id=payment.provider_charge_id,
            provider_status="succeeded",
            new_refund_status="succeeded",
            reason_code="provider_succeeded",
            summary="Only attempt two has authoritative evidence.",
            attempt_number=2,
            attempt_amount_cents=payment.amount_cents,
            attempt_currency="USD",
            attempt_request_key=replacement_refund.stripe_request_key,
        )
        db.flush()

        with pytest.raises(HTTPException):
            validate_money_issue_resolution(
                db,
                money_issue=issue,
                resolution_reason_code="retried_successfully",
                resolution_note=None,
                resolution_external_reference=None,
            )
        assert not financial_outcome_safely_supersedes_refund(
            db, refund=replacement_refund, replacement=replacement
        )
        assert fee.id not in final_replacement_host_publish_fee_ids(db, {fee.id})


@pytest.mark.requirement("WS05-03A-R2")
def test_current_success_with_missing_history_remains_blocked_and_reviewable() -> None:
    from types import SimpleNamespace

    from backend.models import Booking, MoneyIssue
    from backend.services.admin_money_refund_query_service import (
        refund_available_actions,
        refund_has_current_exhausted_diagnostic,
    )
    from backend.services.refund_fulfillment_service import apply_refund_provider_result
    from backend.services.stripe_service import StripeRefundResult

    now = datetime.now(timezone.utc)
    with _session() as db:
        _admin, _user_row, payment, _fixture_refund = _target_state(
            db, provider_status="failed"
        )
        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        refund = _refund(payment, booking, provider_status=None)
        refund.current_attempt_number = 2
        refund.stripe_request_key = f"refund:{refund.id}:attempt:2"
        refund.refund_status = "processing"
        refund.provider_attempt_started_at = now
        db.add(refund)
        db.flush()

        provider_refund_id = f"re_ws05_03a_incomplete_{uuid.uuid4().hex}"
        apply_refund_provider_result(
            db,
            refund=refund,
            payment=payment,
            result=StripeRefundResult(
                id=provider_refund_id,
                status="succeeded",
                amount_cents=refund.amount_cents,
                currency="USD",
                charge_id=payment.provider_charge_id,
                payment_intent_id=payment.provider_payment_intent_id,
                metadata={
                    "refund_id": str(refund.id),
                    "payment_id": str(payment.id),
                    "attempt_number": "2",
                },
            ),
            event_source="reconciliation",
        )
        db.flush()

        issue = db.scalars(
            select(MoneyIssue).where(MoneyIssue.target_refund_id == refund.id)
        ).one()
        assert refund.refund_status == "succeeded"
        assert refund.automatic_mutation_blocked_reason == "historical_attempt_conflict"
        assert issue.issue_type == "refund_outcome_unknown"
        assert issue.recommended_action_code == "review_unknown_outcome"
        check_action = next(
            action
            for action in refund_available_actions(
                db, refund=refund, payment=payment, linked_money_issue=issue
            )
            if action.action_code == "check_provider_status"
        )
        assert check_action.enabled is True
        exhausted_job = SimpleNamespace(
            status="exhausted",
            idempotency_key=refund.stripe_request_key,
            protected_identity={
                "refund_id": str(refund.id),
                "attempt_number": refund.current_attempt_number,
            },
        )
        assert refund_has_current_exhausted_diagnostic(
            refund,
            payment=payment,
            durable_job=exhausted_job,
            linked_issue=None,
            confirmed_returned_cents=refund.amount_cents,
            has_final_replacement=False,
            has_final_no_action_resolution=False,
        )


@pytest.mark.requirement("WS05-03A-R2")
def test_worker_blocks_provider_mutation_when_earlier_attempt_evidence_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import Booking, MoneyIssue, Refund
    from backend.services import refund_fulfillment_service as fulfillment

    with _session() as db:
        _admin, _user_row, payment, _fixture_refund = _target_state(
            db, provider_status="failed"
        )
        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        refund = _refund(payment, booking, provider_status=None)
        refund.amount_cents = payment.amount_cents
        refund.current_attempt_number = 2
        refund.stripe_request_key = f"refund:{refund.id}:attempt:2"
        db.add(refund)
        db.flush()
        _queue_refund_job(db, refund)
        refund_id = refund.id

    provider_called = False

    def unexpected_provider_call(**_kwargs):
        nonlocal provider_called
        provider_called = True
        raise AssertionError("provider mutation must remain blocked")

    monkeypatch.setattr(fulfillment, "validate_refund_preflight", lambda _currency: None)
    monkeypatch.setattr(fulfillment, "create_refund", unexpected_provider_call)
    assert _run_one_refund_job() == "succeeded"
    assert provider_called is False

    with _session() as db:
        persisted = db.get(Refund, refund_id)
        assert persisted is not None
        assert persisted.refund_status == "failed"
        assert persisted.automatic_mutation_blocked_reason == "historical_attempt_conflict"
        issue = db.scalars(
            select(MoneyIssue).where(MoneyIssue.target_refund_id == refund_id)
        ).one()
        assert issue.recommended_action_code == "review_unknown_outcome"


@pytest.mark.requirement("WS05-03A-R2")
@pytest.mark.parametrize("provider_status", ["succeeded", "failed", "cancelled"])
def test_terminal_publish_fee_refund_uses_approving_admin_attribution(
    provider_status: str,
) -> None:
    from backend.models import AdminFinancialOutcome, Booking, Game, HostPublishFee
    from backend.services.refund_fulfillment_service import apply_refund_provider_result
    from backend.services.stripe_service import StripeRefundResult

    now = datetime.now(timezone.utc)
    with _session() as db:
        admin, user, payment, _fixture_refund = _target_state(
            db, provider_status="failed"
        )
        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        game = db.get(Game, booking.game_id)
        assert game is not None
        payment.payment_type = "community_publish_fee"
        payment.booking_id = None
        fee = HostPublishFee(
            id=uuid.uuid4(),
            game_id=game.id,
            host_user_id=user.id,
            payment_id=payment.id,
            amount_cents=payment.amount_cents,
            currency="USD",
            fee_status="paid",
            waiver_reason="none",
            paid_at=now,
        )
        refund = _refund(payment, booking, provider_status=None)
        refund.booking_id = None
        refund.host_publish_fee_id = fee.id
        refund.origin_workflow = "community_publish_fee_refund"
        refund.refund_reason = "publish_fee_refund"
        refund.amount_cents = payment.amount_cents
        refund.refund_status = "processing"
        refund.approved_by_user_id = admin.id
        refund.approved_at = now
        refund.provider_attempt_started_at = now
        outcome = AdminFinancialOutcome(
            id=uuid.uuid4(),
            target_game_id=game.id,
            host_user_id=user.id,
            host_publish_fee_id=fee.id,
            payment_id=payment.id,
            refund_id=refund.id,
            outcome="refund",
            applied_status="pending",
            amount_cents=payment.amount_cents,
            currency="USD",
            reason="Durable cash refund.",
            created_by_user_id=admin.id,
            applied_by_user_id=None,
            applied_at=None,
        )
        db.add_all([payment, fee])
        db.flush()
        db.add(refund)
        db.flush()
        db.add(outcome)
        db.flush()
        provider_refund_id = f"re_ws05_03a_actor_{uuid.uuid4().hex}"
        apply_refund_provider_result(
            db,
            refund=refund,
            payment=payment,
            result=StripeRefundResult(
                id=provider_refund_id,
                status=provider_status,
                amount_cents=payment.amount_cents,
                currency="USD",
                charge_id=payment.provider_charge_id,
                payment_intent_id=payment.provider_payment_intent_id,
                metadata={
                    "refund_id": str(refund.id),
                    "payment_id": str(payment.id),
                    "attempt_number": "1",
                },
            ),
            event_source="system",
        )
        db.flush()
        assert outcome.applied_status == (
            "applied" if provider_status == "succeeded" else "failed"
        )
        assert outcome.applied_at is not None
        assert outcome.applied_by_user_id == admin.id


@pytest.mark.requirement("WS05-03A-R2")
def test_ambiguous_exhaustion_persists_compensation_error_until_late_success() -> None:
    from backend.models import Booking, DurableJob, PaymentCompensation
    from backend.services import refund_fulfillment_service as fulfillment
    from backend.services.stripe_service import StripeRefundResult

    now = datetime.now(timezone.utc)
    with _session() as db:
        _admin, _user_row, payment, _fixture_refund = _target_state(
            db, provider_status="failed"
        )
        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        refund = _refund(payment, booking, provider_status=None)
        refund.amount_cents = payment.amount_cents
        refund.refund_status = "processing"
        refund.approved_at = now
        refund.provider_attempt_started_at = now
        compensation = PaymentCompensation(
            id=uuid.uuid4(),
            payment_id=payment.id,
            booking_id=booking.id,
            refund_id=refund.id,
            action="refund",
            reason="capacity_conflict",
            amount_cents=payment.amount_cents,
            currency="USD",
            status="processing",
            processing_started_at=now,
            error_code=None,
            resolved_at=None,
        )
        db.add(refund)
        db.flush()
        db.add(compensation)
        db.flush()
        from backend.services.payment_job_service import build_production_job_registry

        fulfillment.enqueue_refund_fulfillment_job(
            db, refund=refund, registry=build_production_job_registry()
        )
        db.commit()
        job = db.scalars(
            select(DurableJob).where(DurableJob.origin_reference_id == str(refund.id))
        ).one()
        assert (
            fulfillment.handle_refund_job_exhausted(
                db, job, "refund_outcome_unknown"
            )
            is None
        )
        db.flush()
        assert compensation.status == "processing"
        assert compensation.error_code == "refund_outcome_unknown"
        assert compensation.resolved_at is None

        provider_refund_id = f"re_ws05_03a_late_{uuid.uuid4().hex}"
        fulfillment.apply_refund_provider_result(
            db,
            refund=refund,
            payment=payment,
            result=StripeRefundResult(
                id=provider_refund_id,
                status="succeeded",
                amount_cents=refund.amount_cents,
                currency="USD",
                charge_id=payment.provider_charge_id,
                payment_intent_id=payment.provider_payment_intent_id,
                metadata={
                    "refund_id": str(refund.id),
                    "payment_id": str(payment.id),
                    "attempt_number": "1",
                },
            ),
            event_source="reconciliation",
        )
        db.flush()
        assert compensation.status == "succeeded"
        assert compensation.error_code is None
        assert compensation.resolved_at is not None


@pytest.mark.requirement("WS05-03A-R2")
@pytest.mark.parametrize(
    "job_status",
    ["pending", "retry_waiting", "leased", "succeeded", "exhausted", "cancelled"],
)
def test_generic_repair_preserves_refund_job_policy_and_terminal_cancel_noop(
    job_status: str,
) -> None:
    from backend.models import DurableJob, DurableJobEvent
    from backend.services.durable_job_service import (
        DurableJobError,
        operator_cancel_job,
        requeue_exhausted_job,
    )

    now = datetime.now(timezone.utc)
    with _session() as db:
        _admin, _user_row, _payment, refund = _target_state(
            db, provider_status="failed"
        )
        refund.current_attempt_number = 2
        refund.stripe_request_key = f"refund:{refund.id}:attempt:2"
        _queue_refund_job(db, refund)
        job = db.scalars(
            select(DurableJob).where(DurableJob.origin_reference_id == str(refund.id))
        ).one()
        job.status = job_status
        if job_status == "leased":
            job.lease_token = uuid.uuid4()
            job.lease_owner = "ws05-03a-repair-policy-test"
            job.lease_expires_at = now + timedelta(minutes=1)
            job.heartbeat_at = now
        if job_status == "succeeded":
            job.completed_at = now
        elif job_status == "exhausted":
            job.exhausted_at = now
            job.last_error_code = "refund_outcome_unknown"
            refund.refund_status = "processing"
            refund.provider_status = "unknown"
            refund.provider_attempt_started_at = now - timedelta(hours=13)
        elif job_status == "cancelled":
            job.cancelled_at = now
        db.add_all([job, refund])
        db.commit()

        before = (
            job.status,
            job.attempt_count,
            job.maximum_attempts,
            job.last_error_code,
            db.scalar(
                select(func.count())
                .select_from(DurableJobEvent)
                .where(DurableJobEvent.job_id == job.id)
            ),
        )
        if job_status in {"succeeded", "exhausted", "cancelled"}:
            assert (
                operator_cancel_job(
                    db, job_id=job.id, reason_code="operator_cancel"
                )
                is False
            )
        else:
            with pytest.raises(DurableJobError):
                operator_cancel_job(
                    db, job_id=job.id, reason_code="operator_cancel"
                )
        with pytest.raises(DurableJobError):
            requeue_exhausted_job(
                db,
                job_id=job.id,
                maximum_attempts=9,
                reason_code="operator_requeue",
            )
        db.flush()
        after = (
            job.status,
            job.attempt_count,
            job.maximum_attempts,
            job.last_error_code,
            db.scalar(
                select(func.count())
                .select_from(DurableJobEvent)
                .where(DurableJobEvent.job_id == job.id)
            ),
        )
        assert after == before
