from __future__ import annotations

import inspect
from pathlib import Path

import pytest

pytestmark = [pytest.mark.no_db_cleanup]

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _source(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text()


def _assert_order(source: str, *needles: str) -> None:
    positions = [source.index(needle) for needle in needles]
    assert positions == sorted(positions)


@pytest.mark.requirement("WS05-02-R2")
def test_payment_and_booking_lifecycle_values_are_explicit_and_separate() -> None:
    from backend.services import payment_lifecycle_policy

    assert payment_lifecycle_policy.PAYMENT_STATES == {
        "requires_payment_method",
        "requires_confirmation",
        "requires_action",
        "processing",
        "requires_capture",
        "succeeded",
        "failed",
        "canceled",
        "unknown",
    }
    assert payment_lifecycle_policy.PROVIDER_PAYMENT_INTENT_STATES == {
        "requires_payment_method",
        "requires_confirmation",
        "requires_action",
        "processing",
        "requires_capture",
        "succeeded",
        "canceled",
    }
    assert payment_lifecycle_policy.PENDING_PAYMENT_STATES == {
        "requires_payment_method",
        "requires_confirmation",
        "requires_action",
        "processing",
        "requires_capture",
        "unknown",
    }
    assert payment_lifecycle_policy.TERMINAL_PAYMENT_STATES == {
        "succeeded",
        "canceled",
    }
    assert payment_lifecycle_policy.provider_observation_can_advance(
        "failed", "succeeded"
    )
    assert payment_lifecycle_policy.provider_observation_can_advance(
        "failed", "canceled"
    )
    assert not payment_lifecycle_policy.provider_observation_can_advance(
        "failed", "requires_action"
    )
    assert not payment_lifecycle_policy.provider_observation_can_advance(
        "succeeded", "processing"
    )

    payment_source = _source("backend/models/payment_model.py")
    provider_constraint_start = payment_source.index(
        "provider_status IS NULL OR char_length(btrim(provider_status)) > 0"
    )
    provider_constraint_end = payment_source.index("ck_payments_provider_status")
    provider_status_constraint = payment_source[
        provider_constraint_start:provider_constraint_end
    ]
    assert "provider_status IN" not in provider_status_constraint
    assert "String(100)" in payment_source

    booking_source = _source("backend/models/booking_model.py")
    for status in (
        "pending_payment",
        "confirmed",
        "waitlisted",
        "partially_cancelled",
        "cancelled",
        "expired",
        "failed",
        "capacity_conflict",
    ):
        assert f"'{status}'" in booking_source
    for reservation_status in (
        "not_required",
        "held",
        "confirmed",
        "released",
        "capacity_conflict",
    ):
        assert f"'{reservation_status}'" in booking_source
    assert "old_reservation_status" in _source(
        "backend/models/booking_status_history_model.py"
    )
    assert "new_reservation_status" in _source(
        "backend/models/booking_status_history_model.py"
    )


@pytest.mark.requirement("WS05-02-R1", "WS05-02-R6", "WS05-02-R7")
def test_checkout_provider_calls_are_between_checkpoints_and_lock_reentry() -> None:
    from backend.services import checkout_service

    create_source = inspect.getsource(
        checkout_service.create_game_checkout_payment_intent_workflow
    )
    _assert_order(
        create_source,
        "db.rollback()",
        "require_provider_verified_checkout_payment_method(",
        "return create_game_checkout_payment_intent_workflow(",
    )
    assert "verify_provider=False" in create_source
    _assert_order(
        create_source,
        "db.commit()\n        checkpoint_committed = True",
        "payment_intent = create_payment_intent(",
    )
    _assert_order(
        create_source,
        "payment_intent = create_payment_intent(",
        "lock_booking_payment_domain_by_booking_id(db, booking_id)",
        "apply_authoritative_payment_intent_observation(",
    )

    resume_source = inspect.getsource(
        checkout_service.resume_pending_checkout_with_locked_game
    )
    _assert_order(
        resume_source,
        "db.rollback()",
        "require_provider_verified_checkout_payment_method(",
        "return resume_serialized_pending_checkout(",
    )
    assert "verify_provider=False" in resume_source
    _assert_order(
        resume_source,
        "db.commit()\n    try:\n        payment_intent = retrieve_payment_intent(",
        "stripe_status = payment_intent.status",
    )
    assert (
        "db.commit()\n        try:\n            payment_intent = confirm_payment_intent("
        in resume_source
    )
    _assert_order(
        resume_source,
        "payment_intent = retrieve_payment_intent(",
        "confirmation_now = get_database_now(db)",
        "payment_intent = confirm_payment_intent(",
        "observation_now = get_database_now(db)",
        "apply_authoritative_payment_intent_observation(",
    )


@pytest.mark.requirement("WS05-02-R2", "WS05-02-R5")
def test_unresolved_expiry_is_local_shared_and_provider_status_preserving() -> None:
    from backend.services import (
        checkout_service,
        payment_transition_service,
        stripe_webhook_service,
    )

    status_source = inspect.getsource(checkout_service.get_game_checkout_status_workflow)
    assert "expire_stale_pending_checkouts(db, db_game, now)" in status_source
    for provider_call in (
        "create_payment_intent(",
        "confirm_payment_intent(",
        "retrieve_payment_intent(",
        "retrieve_payment_method(",
    ):
        assert provider_call not in status_source

    expiry_helper_source = inspect.getsource(
        stripe_webhook_service.expire_unresolved_checkout_hold_if_stale
    )
    assert "expire_stale_pending_checkouts(db, game, now)" in expiry_helper_source
    payment_expiry_helper_source = inspect.getsource(
        stripe_webhook_service.expire_payment_checkout_hold_if_stale
    )
    assert "lock_booking_payment_domain_by_booking_id(" in payment_expiry_helper_source
    assert "expire_unresolved_checkout_hold_if_stale(" in payment_expiry_helper_source
    for provider_call in (
        "create_payment_intent(",
        "confirm_payment_intent(",
        "retrieve_payment_intent(",
        "retrieve_payment_method(",
    ):
        assert provider_call not in expiry_helper_source
        assert provider_call not in payment_expiry_helper_source

    processing_source = inspect.getsource(
        stripe_webhook_service.apply_payment_intent_processing
    )
    _assert_order(
        processing_source,
        "expire_unresolved_checkout_hold_if_stale(",
        "payment.provider_status =",
        "mark_event_processed(event, now)",
    )
    pending_source = inspect.getsource(
        stripe_webhook_service.apply_payment_intent_pending_observation
    )
    _assert_order(
        pending_source,
        "expire_unresolved_checkout_hold_if_stale(",
        'observed_status in {"requires_action", "requires_payment_method"}',
        "mark_paid_waitlist_auto_promotion_failed(",
    )
    assert "payment.provider_status =" in pending_source
    assert "mark_event_processed(event, now)" in pending_source
    event_builder_source = inspect.getsource(
        stripe_webhook_service.build_payment_intent_observation_envelope
    )
    assert '"requires_confirmation": "payment_intent.requires_confirmation"' in (
        event_builder_source
    )
    assert '"requires_capture": "payment_intent.requires_capture"' in (
        event_builder_source
    )

    reconcile_source = inspect.getsource(payment_transition_service.reconcile_payment_intent)
    assert "expire_stale_pending_checkouts(" in reconcile_source
    assert "_expire_payment_hold_if_stale(db, payment_id)" in reconcile_source
    assert "apply_authoritative_payment_intent_observation(" in reconcile_source


@pytest.mark.requirement("WS05-02-R3", "WS05-02-R5")
def test_late_success_and_capacity_conflict_create_compensation_not_refunds() -> None:
    from backend.services import stripe_webhook_service

    compensation_source = _source("backend/models/payment_compensation_model.py")
    assert "uq_payment_compensations_active" in compensation_source
    assert '"payment_id",' in compensation_source
    assert '"booking_id",' in compensation_source
    assert "'booking_cancelled'" in compensation_source
    assert "status IN ('required', 'processing')" in compensation_source

    late_success_source = inspect.getsource(
        stripe_webhook_service.expire_late_successful_payment
    )
    capacity_conflict_source = inspect.getsource(
        stripe_webhook_service.record_capacity_conflict_after_success
    )
    combined_source = late_success_source + capacity_conflict_source
    assert 'payment.payment_status = "succeeded"' in combined_source
    assert 'old_booking_status == "cancelled"' in late_success_source
    assert "booking.booking_status = next_booking_status" in late_success_source
    assert "booking.reservation_status = next_reservation_status" in late_success_source
    assert 'booking.booking_status = "capacity_conflict"' in capacity_conflict_source
    assert 'booking.reservation_status = "capacity_conflict"' in capacity_conflict_source
    assert combined_source.count("ensure_payment_compensation(") == 2
    for forbidden in (
        "create_refund(",
        "refund_payment(",
        "stripe_refund",
    ):
        assert forbidden not in combined_source


@pytest.mark.requirement("WS05-02-R2", "WS05-02-R5", "WS05-02-R7")
def test_local_invalidation_does_not_invent_provider_cancellation() -> None:
    local_invalidation_sources = {
        "game_cancellation": _source("backend/services/game_cancellation_service.py"),
        "official_game_update": _source("backend/services/official_game_service.py"),
        "official_roster_removal": _source(
            "backend/services/official_game_roster_service.py"
        ),
        "community_publish_expiry": _source(
            "backend/services/community_game_publish_service.py"
        ),
    }
    for source in local_invalidation_sources.values():
        assert 'payment.payment_status = "canceled"' not in source
        assert 'payment.payment_status = "failed"' in source

    webhook_source = _source("backend/services/stripe_webhook_service.py")
    assert 'terminal_payment_status = "canceled"' in webhook_source
    assert 'payment_status = "canceled"' in webhook_source


@pytest.mark.requirement("WS05-02-R4", "WS05-02-R5")
def test_webhook_ingest_uses_bounded_event_envelope_and_internal_job_id() -> None:
    from backend.services import payment_job_service, stripe_webhook_service

    route_source = _source("backend/routes/stripe_webhook_routes.py")
    assert "payload = await request.body()" in route_source
    assert "construct_webhook_event(payload, stripe_signature)" in route_source

    ingest_source = inspect.getsource(
        stripe_webhook_service.record_and_process_stripe_webhook_event
    )
    _assert_order(
        ingest_source,
        "event_envelope = normalize_stripe_event_envelope(event_payload)",
        "db.add(payment_event)",
        "db.flush()",
        "enqueue_webhook_event_job(db, payment_event.id)",
        "db.commit()",
    )
    assert "process_stripe_event(" not in ingest_source

    envelope_source = inspect.getsource(
        stripe_webhook_service.normalize_stripe_event_envelope
    )
    for allowed_key in (
        "payment_id",
        "booking_id",
        "game_id",
        "refund_id",
        "checkout_total_cents",
        "stripe_amount_cents",
    ):
        assert f'"{allowed_key}"' in envelope_source
    for forbidden in (
        "client_secret",
        "billing_details",
        "email",
    ):
        assert forbidden not in envelope_source

    job_source = inspect.getsource(payment_job_service.enqueue_webhook_event_job)
    assert 'payload={"payment_event_id": str(event_id)}' in job_source
    assert 'protected_identity={"payment_event_id": str(event_id)}' in job_source
    for forbidden in (
        "client_secret",
        "event_envelope",
        "provider_event_id",
        "email",
    ):
        assert forbidden not in job_source


@pytest.mark.requirement("WS05-02-R6")
def test_saved_payment_method_operations_have_durable_unknown_handoffs() -> None:
    from backend.services import payment_method_service

    operation_source = _source("backend/models/payment_method_operation_model.py")
    assert "uq_payment_method_operations_active_user" in operation_source
    assert "status IN ('pending', 'provider_unknown')" in operation_source
    for operation_kind in (
        "setup_create",
        "sync",
        "set_default",
        "detach",
        "clear_default",
    ):
        assert f"'{operation_kind}'" in operation_source
    for operation_status in (
        "pending",
        "provider_unknown",
        "succeeded",
        "failed",
    ):
        assert f"'{operation_status}'" in operation_source
    assert "client_secret" not in operation_source

    sync_source = inspect.getsource(payment_method_service.sync_saved_payment_method)
    _assert_order(
        sync_source,
        "operation = begin_payment_method_operation(",
        "setup_intent = retrieve_setup_intent(setup_intent_id)",
    )
    assert (
        'mark_payment_method_operation_unknown(db, operation, "sync_timeout_unknown")'
        in sync_source
    )
    assert "payment_method_read_timeout_unknown" in sync_source

    checkout_method_source = inspect.getsource(
        payment_method_service.get_current_user_saved_payment_method_for_checkout
    )
    assert "verify_provider: bool = True" in checkout_method_source
    assert "if verify_provider:" in checkout_method_source
    set_default_source = inspect.getsource(
        payment_method_service.set_default_saved_payment_method
    )
    _assert_order(
        set_default_source,
        "verify_saved_payment_method_with_stripe(",
        "operation = begin_payment_method_operation(",
        "set_customer_default_payment_method(",
    )
    detach_source = inspect.getsource(payment_method_service.detach_saved_payment_method)
    _assert_order(
        detach_source,
        "verify_saved_payment_method_with_stripe(",
        "operation = begin_payment_method_operation(",
        "detach_payment_method(",
    )
    assert '"clear_default"' in detach_source
    assert "allow_active_operation_ids={operation.id}" in detach_source
    retryable_source = inspect.getsource(
        payment_method_service.require_payment_method_operation_retryable
    )
    assert 'operation.status == "provider_unknown"' in retryable_source


@pytest.mark.requirement("WS05-02-R7")
def test_later_provider_and_runtime_evidence_remains_deferred() -> None:
    declaration = _source("backend/tests/support/requirements/ws05_02.json")
    assert '"id": "WS05-02-R8"' in declaration
    assert '"state": "deferred"' in declaration
    for later_owner in ("WS05-01B", "WS05-03", "WS05-04", "WS09", "WS10"):
        assert later_owner in declaration
