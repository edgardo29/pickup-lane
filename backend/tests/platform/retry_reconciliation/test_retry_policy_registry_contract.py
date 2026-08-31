from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import backend.services.provider_retry_policy as retry_policy

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_EXPECTED_CLASSES = {
    "SAFE_READ",
    "IDEMPOTENT_MUTATION",
    "RECONCILE_BEFORE_RETRY",
    "MANUAL_REPAIR",
    "PROVIDER_REDELIVERY",
    "NO_AUTOMATIC_RETRY",
}


def _by_context() -> dict[str, retry_policy.ProviderOperationRetryPolicy]:
    return {
        policy.workflow_context: policy
        for policy in retry_policy.PROVIDER_OPERATION_RETRY_POLICIES
    }


def _resolve_dotted_object(dotted_path: str) -> object:
    parts = dotted_path.split(".")
    import_errors: list[ModuleNotFoundError] = []
    for module_end in range(len(parts) - 1, 0, -1):
        module_name = ".".join(parts[:module_end])
        try:
            current = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name != module_name:
                raise
            import_errors.append(exc)
            continue

        for attr_name in parts[module_end:]:
            current = getattr(current, attr_name)
        return current

    raise import_errors[-1] if import_errors else ModuleNotFoundError(dotted_path)


@pytest.mark.requirement("WS02-04C2-R1")
def test_retry_classes_and_registry_shape_are_source_owned_and_declarative() -> None:
    source = (_REPO_ROOT / "backend/services/provider_retry_policy.py").read_text()

    assert {item.value for item in retry_policy.RetrySafetyClass} == _EXPECTED_CLASSES
    assert "def retry" not in source
    assert "sleep(" not in source
    assert "asyncio" not in source
    assert "@dataclass(frozen=True)" in source
    assert "get_stripe_client_pair" not in source

    for policy in retry_policy.PROVIDER_OPERATION_RETRY_POLICIES:
        assert policy.workflow_context
        assert policy.material_callers
        assert policy.current_recovery
        assert policy.application_automatic_retry_allowed is False


@pytest.mark.requirement("WS02-04C2-R1", "WS02-04C2-R5", "WS02-04C2-R6")
def test_retry_policy_material_callers_resolve_to_current_source_symbols() -> None:
    unresolved_callers: list[str] = []
    for policy in retry_policy.PROVIDER_OPERATION_RETRY_POLICIES:
        for caller in policy.material_callers:
            try:
                _resolve_dotted_object(caller)
            except (AttributeError, ModuleNotFoundError):
                unresolved_callers.append(
                    f"{policy.workflow_context}: {caller}"
                )

    assert unresolved_callers == []


@pytest.mark.requirement("WS02-04C2-R1", "WS02-04C2-R5", "WS02-04C2-R6")
def test_workflow_specific_stripe_mutation_entries_are_truthful() -> None:
    policies = _by_context()

    assert policies["checkout_initial_create_before_provider_result"].operation == (
        "stripe.payment_intent.create"
    )
    assert policies["checkout_initial_create_before_provider_result"].safety_class == (
        retry_policy.RetrySafetyClass.NO_AUTOMATIC_RETRY
    )
    assert policies[
        "checkout_initial_create_before_provider_result"
    ].identity_survives_replay
    assert "pending checkout checkpoint is committed" in policies[
        "checkout_initial_create_before_provider_result"
    ].current_recovery

    assert policies["checkout_initial_confirm_after_checkpoint"].operation == (
        "stripe.payment_intent.confirm"
    )
    assert policies["checkout_initial_confirm_after_checkpoint"].safety_class == (
        retry_policy.RetrySafetyClass.RECONCILE_BEFORE_RETRY
    )
    assert policies["checkout_initial_confirm_after_checkpoint"].identity_survives_replay
    assert "reacquires game serialization" in policies[
        "checkout_initial_confirm_after_checkpoint"
    ].current_recovery
    assert "re-reads the persisted PaymentIntent" in policies[
        "checkout_initial_confirm_after_checkpoint"
    ].current_recovery
    assert policies["checkout_initial_confirm_after_checkpoint"].provider_idempotency_key_used
    assert policies[
        "checkout_initial_confirm_after_checkpoint"
    ].client_retry_stable_idempotency
    assert "PaymentConfirmationAttempt" in policies[
        "checkout_initial_confirm_after_checkpoint"
    ].idempotency_identity_source
    assert policies[
        "checkout_existing_pending_confirm_after_provider_read"
    ].provider_idempotency_key_used
    assert "PaymentConfirmationAttempt" in policies[
        "checkout_existing_pending_confirm_after_provider_read"
    ].idempotency_identity_source

    assert policies["saved_card_customer_creation"].safety_class == (
        retry_policy.RetrySafetyClass.IDEMPOTENT_MUTATION
    )
    assert policies["saved_card_customer_creation"].client_retry_stable_idempotency
    assert policies["saved_card_setup_intent_creation"].safety_class == (
        retry_policy.RetrySafetyClass.IDEMPOTENT_MUTATION
    )
    assert policies["saved_card_setup_intent_creation"].client_retry_stable_idempotency
    assert policies["saved_card_setup_intent_creation"].identity_survives_replay
    assert (
        policies["saved_card_setup_intent_creation"].idempotency_identity_source
        == "persisted payment-method operation provider_idempotency_key"
    )
    assert "stripe_payment_method_operation_reconcile" in policies[
        "saved_card_setup_intent_creation"
    ].current_recovery

    assert policies["community_publish_fee_initial_create"].material_callers == (
        "backend.services.community_game_publish_service.create_paid_publish_attempt",
    )
    assert policies[
        "community_publish_fee_confirm_after_checkpoint"
    ].material_callers == (
        "backend.services.community_game_publish_service.create_paid_publish_attempt",
    )
    assert policies["waitlist_auto_promotion_confirm"].provider_idempotency_key_used
    assert "PaymentConfirmationAttempt" in policies[
        "waitlist_auto_promotion_confirm"
    ].idempotency_identity_source
    for context in (
        "user_visible_saved_card_detach",
        "saved_card_default_set",
        "saved_card_default_clear",
    ):
        assert policies[context].provider_idempotency_key_used
        assert policies[context].client_retry_stable_idempotency
        assert policies[context].idempotency_identity_source == (
            "persisted payment-method operation provider_idempotency_key"
        )


@pytest.mark.requirement("WS02-04C2-R1", "WS02-04C2-R5")
def test_operation_lookup_cannot_silently_select_the_wrong_context() -> None:
    payment_create_policies = retry_policy.policies_by_operation(
        "stripe.payment_intent.create"
    )

    assert {policy.workflow_context for policy in payment_create_policies} >= {
        "checkout_initial_create_before_provider_result",
        "community_publish_fee_initial_create",
        "waitlist_auto_promotion_create",
    }
    with pytest.raises(ValueError, match="multiple retry-policy workflow contexts"):
        retry_policy.policy_by_operation("stripe.payment_intent.create")

    checkout_policy = retry_policy.policy_by_operation(
        "stripe.payment_intent.create",
        workflow_context="checkout_initial_create_before_provider_result",
    )
    assert checkout_policy.safety_class == retry_policy.RetrySafetyClass.NO_AUTOMATIC_RETRY

    unambiguous_read = retry_policy.policy_by_operation("stripe.setup_intent.retrieve")
    assert unambiguous_read.safety_class == retry_policy.RetrySafetyClass.SAFE_READ


@pytest.mark.requirement("WS02-04C2-R1", "WS02-04C2-R5")
def test_blanket_payment_intent_create_replay_claim_is_gone() -> None:
    for policy in retry_policy.policies_by_operation("stripe.payment_intent.create"):
        rendered = " ".join(
            value
            for value in (
                policy.current_recovery,
                policy.durable_follow_up or "",
                policy.idempotency_identity_source or "",
            )
        ).lower()
        assert "stable for checkout replay" not in rendered

    checkout_policy = retry_policy.policy_by_operation_context(
        "stripe.payment_intent.create",
        "checkout_initial_create_before_provider_result",
    )
    assert checkout_policy.provider_idempotency_key_used
    assert not checkout_policy.client_retry_stable_idempotency


@pytest.mark.requirement("WS02-04C2-R8", "WS02-04C2-R9")
def test_fanout_entries_and_durable_handoffs_are_complete_and_non_numeric() -> None:
    assert {policy.workflow for policy in retry_policy.FANOUT_EXECUTION_POLICIES} == {
        "platform_notice.selected_user_publish",
        "game_chat.notification_rows",
        "need_a_sub_chat.notification_rows",
        "game_updated.notification_rows",
        "waitlist.promotion",
        "account_deletion.cleanup",
        "official_game_cancellation.refunds",
        "official_game_player_removal.refunds",
        "community_publish_fee.financial_outcome_refund",
        "late_checkout_payment.compensation",
    }
    for policy in retry_policy.FANOUT_EXECUTION_POLICIES:
        assert (
            "sequential" in policy.execution_model
            or policy.execution_model
            in {
                "single_admin_state_gated_workflow",
                "single_webhook_compensation_checkpoint",
            }
        )
        assert policy.new_concurrency_allowed is False
        assert policy.approved_concurrency_cap is None
        assert policy.approved_batch_size is None

    assert {handoff.workflow for handoff in retry_policy.DURABLE_WORK_HANDOFFS} == {
        "provider_unknown_outcome_reconciliation",
        "checkout_post_expiry_provider_reconciliation",
        "account_deletion_cleanup_recovery",
        "future_external_notification_delivery",
        "future_platform_notice_external_delivery",
        "durable_financial_reconciliation",
    }
    for handoff in retry_policy.DURABLE_WORK_HANDOFFS:
        assert handoff.owner_pass == "WS05"
        assert handoff.required_durable_properties
        assert handoff.approved_worker_retry_attempts is None
        assert handoff.approved_worker_concurrency is None
        assert handoff.approved_lease_seconds is None
