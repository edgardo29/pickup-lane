from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import backend.services.transaction_boundary_policy as boundary_policy

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _policies_by_workflow() -> dict[str, boundary_policy.TransactionBoundaryPolicy]:
    return {
        policy.workflow: policy
        for policy in boundary_policy.TRANSACTION_BOUNDARY_POLICIES
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


@pytest.mark.pass_provenance('WS04-02A', 'WS06-02')
def test_current_side_effecting_workflows_are_declared_with_complete_boundaries() -> None:
    policies = _policies_by_workflow()

    assert policies.keys() == {
        "checkout.payment_intent.create",
        "checkout.payment_intent.confirm",
        "checkout.credit_covered_confirm",
        "checkout.stale_pending_expire",
        "waitlist.auto_promotion.payment_intent",
        "community_publish_fee.payment_intent.create",
        "community_publish_fee.payment_intent.confirm",
        "community_publish.finalize_success",
        "stripe.webhook.payment_event_ingest",
        "late_checkout_payment.compensation",
        "durable.refund.fulfillment",
        "admin_money.refund.retry",
        "admin_money.refund.reconcile",
        "admin_money.credit.retry",
        "official_game_cancellation.refunds",
        "official_player_removal.refunds",
        "community_publish_financial_outcome.refund",
        "saved_card.customer_create",
        "saved_card.setup_intent",
        "saved_card.setup_sync",
        "saved_card.default_update",
        "saved_card.detach",
        "saved_card.unpersisted_cleanup",
        "auth.firebase_token_verify",
        "auth.firebase_app_check_verify",
        "auth.firebase_user_lookup",
        "auth.email_availability_lookup",
        "account_deletion.saved_card_cleanup",
        "account_deletion.firebase_delete",
        "unfinished_account.firebase_cleanup",
        "r2.venue_image_download",
        "r2.venue_image_publish",
        "r2.venue_image_cleanup",
        "notifications.local_rows",
        "platform_notice.publish",
        "support.local_flags",
        "admin.local_actions",
    }

    for policy in policies.values():
        assert policy.workflow
        _resolve_dotted_object(policy.service_function)
        assert policy.database_unit_of_work
        assert policy.external_effect
        assert policy.required_pre_effect_checkpoint
        assert policy.required_post_effect_recording
        assert policy.timeout_or_unknown_outcome
        assert policy.recovery_path


@pytest.mark.pass_provenance('WS04-02A', 'WS06-02')
def test_provider_backed_transaction_contexts_define_pre_effect_boundaries() -> None:
    assert boundary_policy.provider_retry_contexts() == {
        "saved_card_setup_sync",
        "checkout_active_hold_reentry",
        "checkout_initial_create_before_provider_result",
        "checkout_initial_confirm_after_checkpoint",
        "checkout_existing_pending_confirm_after_provider_read",
        "waitlist_auto_promotion_create",
        "waitlist_auto_promotion_confirm",
        "community_publish_fee_initial_create",
        "community_publish_fee_confirm_after_checkpoint",
        "stripe_webhook_provider_redelivery",
        "admin_refund_retry_state_gate",
        "admin_refund_reconcile_state_gate",
        "admin_credit_repair_state_gate",
        "durable_refund_fulfillment",
        "refund_fulfillment_reconciliation",
        "saved_card_customer_creation",
        "saved_card_setup_intent_creation",
        "saved_card_default_set",
        "saved_card_default_clear",
        "user_visible_saved_card_detach",
        "account_deletion_saved_card_cleanup",
        "unpersisted_best_effort_payment_method_cleanup",
        "account_deletion_auth_cleanup",
        "authenticated_request_identity",
        "app_check_request_verification",
        "authenticated_token_user_lookup",
        "email_availability_lookup",
        "venue_image_staging_download",
        "venue_image_publication",
        "venue_image_object_cleanup",
    }

    for policy in boundary_policy.TRANSACTION_BOUNDARY_POLICIES:
        if policy.provider_backed:
            assert "not applicable - no external provider mutation" not in (
                policy.required_pre_effect_checkpoint.lower()
            )


@pytest.mark.pass_provenance('WS04-02A')
def test_checkout_and_publish_create_policies_require_committed_checkpoints() -> None:
    checkout_boundary = boundary_policy.policy_by_workflow(
        "checkout.payment_intent.create"
    )
    publish_boundary = boundary_policy.policy_by_workflow(
        "community_publish_fee.payment_intent.create"
    )

    assert (
        "committed pending booking"
        in checkout_boundary.required_pre_effect_checkpoint.lower()
    )
    assert checkout_boundary.operation_class == (
        boundary_policy.ExternalOperationClass.NO_AUTOMATIC_RETRY_MUTATION
    )
    assert "without confirmation or automatic app replay" in (
        checkout_boundary.timeout_or_unknown_outcome
    )
    assert "recoverable" in checkout_boundary.timeout_or_unknown_outcome

    assert "Committed publish attempt" in publish_boundary.required_pre_effect_checkpoint
    assert publish_boundary.operation_class == (
        boundary_policy.ExternalOperationClass.RECONCILE_BEFORE_RETRY_MUTATION
    )
    assert "ordinary app retry is not approved" in (
        publish_boundary.timeout_or_unknown_outcome
    )
    assert "reconciliation" in publish_boundary.recovery_path


@pytest.mark.pass_provenance("WS06-02")
def test_r2_object_boundaries_have_exact_retry_safety_classes() -> None:
    policies = _policies_by_workflow()
    assert policies["r2.venue_image_download"].operation_class == (
        boundary_policy.ExternalOperationClass.STORAGE_OBJECT_DEPENDENCY
    )
    assert policies["r2.venue_image_publish"].operation_class == (
        boundary_policy.ExternalOperationClass.NO_AUTOMATIC_RETRY_MUTATION
    )
    assert policies["r2.venue_image_cleanup"].operation_class == (
        boundary_policy.ExternalOperationClass.IDEMPOTENT_PROVIDER_MUTATION
    )
    assert "never reused" in policies[
        "r2.venue_image_publish"
    ].timeout_or_unknown_outcome


@pytest.mark.pass_provenance('WS04-02A')
def test_plan_named_waitlist_late_refund_and_unfinished_cleanup_paths_are_reconciled() -> None:
    policies = _policies_by_workflow()
    unfinished_cleanup = policies["unfinished_account.firebase_cleanup"]

    assert policies["waitlist.auto_promotion.payment_intent"].provider_retry_contexts == (
        "waitlist_auto_promotion_create",
        "waitlist_auto_promotion_confirm",
    )
    assert policies["late_checkout_payment.compensation"].provider_retry_contexts == ()
    assert unfinished_cleanup.provider_retry_contexts == (
        "account_deletion_auth_cleanup",
    )
    assert unfinished_cleanup.service_function == (
        "backend.services.auth_account_service.cleanup_unfinished_account_workflow"
    )
    assert "unknown Firebase outcome" in unfinished_cleanup.timeout_or_unknown_outcome
    assert "Duplicate cleanup reuses Firebase identity" in unfinished_cleanup.recovery_path
    assert unfinished_cleanup.downstream_owner == "account_cleanup"


@pytest.mark.pass_provenance('WS04-02A')
def test_boundary_policy_is_declarative_and_contains_no_sensitive_or_runtime_claims() -> None:
    source = (_REPO_ROOT / "backend/services/transaction_boundary_policy.py").read_text()
    rendered = repr(boundary_policy.TRANSACTION_BOUNDARY_POLICIES)

    assert "def retry" not in source
    assert "create_engine" not in source
    assert "create_payment_intent(" not in source
    assert "delete_firebase_user(" not in source
    assert "provider dashboard is configured" not in rendered.lower()
    assert "final production topology" not in rendered.lower()
    assert "DATABASE" + "_URL" not in rendered
    assert "postgresql" + "://" not in rendered
