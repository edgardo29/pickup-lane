"""Source-owned retry and reconciliation policy for provider boundaries.

This module records WS02-04C2 decisions. It does not execute retries, configure
SDK retry counts, or provide a generic retry decorator.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RetrySafetyClass(str, Enum):
    SAFE_READ = "SAFE_READ"
    IDEMPOTENT_MUTATION = "IDEMPOTENT_MUTATION"
    RECONCILE_BEFORE_RETRY = "RECONCILE_BEFORE_RETRY"
    MANUAL_REPAIR = "MANUAL_REPAIR"
    PROVIDER_REDELIVERY = "PROVIDER_REDELIVERY"
    NO_AUTOMATIC_RETRY = "NO_AUTOMATIC_RETRY"


class RetryOwnership(str, Enum):
    DEPENDENCY_OWNED = "DEPENDENCY_OWNED"
    APPLICATION_POLICY = "APPLICATION_POLICY"
    PROVIDER_REDELIVERY = "PROVIDER_REDELIVERY"
    MANUAL_REPAIR = "MANUAL_REPAIR"


@dataclass(frozen=True)
class DependencyRetryBehavior:
    distribution_name: str
    installed_version: str
    owner: RetryOwnership
    current_behavior: tuple[str, ...]
    pickup_lane_override: str
    reassessment_trigger: str
    approved_retry_attempts: int | None = None
    approved_backoff_seconds: int | None = None


@dataclass(frozen=True)
class ProviderOperationRetryPolicy:
    operation: str
    provider: str
    workflow_context: str
    material_callers: tuple[str, ...]
    safety_class: RetrySafetyClass
    read_operation: bool
    provider_mutation: bool
    dependency_retry_owner: RetryOwnership
    application_automatic_retry_allowed: bool
    provider_idempotency_key_used: bool
    idempotency_identity_source: str | None
    client_retry_stable_idempotency: bool
    identity_survives_replay: bool
    unknown_outcome_possible: bool
    current_recovery: str
    durable_follow_up: str | None = None
    approved_retry_attempts: int | None = None
    approved_backoff_seconds: int | None = None


@dataclass(frozen=True)
class FanoutExecutionPolicy:
    workflow: str
    execution_model: str
    current_bound: str
    provider_calls_per_item: str
    new_concurrency_allowed: bool
    durable_follow_up: str | None = None
    approved_concurrency_cap: int | None = None
    approved_batch_size: int | None = None


@dataclass(frozen=True)
class DurableWorkHandoff:
    workflow: str
    current_safe_interim_behavior: str
    why_durable_work_may_be_needed: str
    required_durable_properties: tuple[str, ...]
    owner_pass: str = "WS05"
    approved_worker_retry_attempts: int | None = None
    approved_worker_concurrency: int | None = None
    approved_lease_seconds: int | None = None
    approved_scheduler_cadence_seconds: int | None = None
    approved_poison_threshold: int | None = None


DEPENDENCY_RETRY_BEHAVIORS: tuple[DependencyRetryBehavior, ...] = (
    DependencyRetryBehavior(
        distribution_name="stripe",
        installed_version="15.1.0",
        owner=RetryOwnership.DEPENDENCY_OWNED,
        current_behavior=(
            "Stripe SDK retry behavior is dependency-owned when not overridden.",
            "Pickup Lane uses separate read and mutation clients for timeouts.",
            "Pickup Lane does not source-configure Stripe retry attempts.",
        ),
        pickup_lane_override="none",
        reassessment_trigger="Review WS02-04C2 whenever stripe changes version.",
    ),
    DependencyRetryBehavior(
        distribution_name="firebase-admin",
        installed_version="7.4.0",
        owner=RetryOwnership.DEPENDENCY_OWNED,
        current_behavior=(
            "Firebase Admin retry behavior is dependency-owned.",
            "Pickup Lane configures only the Firebase Admin HTTP timeout.",
            "Firebase deletion timeouts remain unknown outcome.",
        ),
        pickup_lane_override="httpTimeout only",
        reassessment_trigger=(
            "Review WS02-04C2 whenever firebase-admin changes version."
        ),
    ),
    DependencyRetryBehavior(
        distribution_name="botocore",
        installed_version="1.35.99",
        owner=RetryOwnership.DEPENDENCY_OWNED,
        current_behavior=(
            "Botocore retry behavior is dependency-owned.",
            "Pickup Lane configures R2 metadata connect and read timeouts only.",
            "Pickup Lane does not source-configure Botocore retry mode or attempts.",
        ),
        pickup_lane_override="metadata timeouts only",
        reassessment_trigger="Review WS02-04C2 whenever botocore changes version.",
    ),
    DependencyRetryBehavior(
        distribution_name="SQLAlchemy",
        installed_version="2.0.49",
        owner=RetryOwnership.APPLICATION_POLICY,
        current_behavior=(
            "SQLAlchemy does not provide transparent mid-transaction retry.",
            "Pickup Lane uses rollback-on-error request sessions.",
            "No application transaction retry count or backoff is approved.",
        ),
        pickup_lane_override="database timeout classification only",
        reassessment_trigger="Review WS02-04C2 whenever SQLAlchemy changes version.",
    ),
)


def _read_policy(
    *,
    operation: str,
    provider: str,
    workflow_context: str,
    material_callers: tuple[str, ...],
    current_recovery: str,
) -> ProviderOperationRetryPolicy:
    return ProviderOperationRetryPolicy(
        operation=operation,
        provider=provider,
        workflow_context=workflow_context,
        material_callers=material_callers,
        safety_class=RetrySafetyClass.SAFE_READ,
        read_operation=True,
        provider_mutation=False,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        idempotency_identity_source=None,
        client_retry_stable_idempotency=False,
        identity_survives_replay=False,
        unknown_outcome_possible=False,
        current_recovery=current_recovery,
    )


def _stripe_mutation_policy(
    *,
    operation: str,
    workflow_context: str,
    material_callers: tuple[str, ...],
    safety_class: RetrySafetyClass,
    provider_idempotency_key_used: bool,
    idempotency_identity_source: str | None,
    client_retry_stable_idempotency: bool,
    identity_survives_replay: bool,
    current_recovery: str,
    durable_follow_up: str | None = None,
) -> ProviderOperationRetryPolicy:
    return ProviderOperationRetryPolicy(
        operation=operation,
        provider="stripe",
        workflow_context=workflow_context,
        material_callers=material_callers,
        safety_class=safety_class,
        read_operation=False,
        provider_mutation=True,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=provider_idempotency_key_used,
        idempotency_identity_source=idempotency_identity_source,
        client_retry_stable_idempotency=client_retry_stable_idempotency,
        identity_survives_replay=identity_survives_replay,
        unknown_outcome_possible=True,
        current_recovery=current_recovery,
        durable_follow_up=durable_follow_up,
    )


STRIPE_OPERATION_RETRY_POLICIES: tuple[ProviderOperationRetryPolicy, ...] = (
    _read_policy(
        operation="stripe.setup_intent.retrieve",
        provider="stripe",
        workflow_context="saved_card_setup_sync",
        material_callers=("backend.services.payment_method_service.sync_saved_payment_method",),
        current_recovery="Safe read timeout returns dependency-read retry-later.",
    ),
    _read_policy(
        operation="stripe.payment_method.retrieve",
        provider="stripe",
        workflow_context="saved_card_setup_sync",
        material_callers=("backend.services.payment_method_service.sync_saved_payment_method",),
        current_recovery="Safe read timeout returns dependency-read retry-later.",
    ),
    _read_policy(
        operation="stripe.payment_intent.retrieve",
        provider="stripe",
        workflow_context="checkout_active_hold_reentry",
        material_callers=(
            "backend.services.checkout_service.create_game_checkout_payment_intent_workflow",
        ),
        current_recovery="Safe read observes provider PaymentIntent state before another decision.",
    ),
    _read_policy(
        operation="stripe.refund.retrieve",
        provider="stripe",
        workflow_context="admin_refund_reconciliation",
        material_callers=(
            "backend.services.admin_money_refund_service.reconcile_admin_money_refund",
        ),
        current_recovery="Admin reconciliation may re-read provider refund state.",
    ),
    _stripe_mutation_policy(
        operation="stripe.customer.create",
        workflow_context="saved_card_customer_creation",
        material_callers=("backend.services.payment_method_service.ensure_stripe_customer_id",),
        safety_class=RetrySafetyClass.IDEMPOTENT_MUTATION,
        provider_idempotency_key_used=True,
        idempotency_identity_source="deterministic user-scoped key user:{user.id}:stripe_customer",
        client_retry_stable_idempotency=True,
        identity_survives_replay=True,
        current_recovery="User-scoped customer idempotency key supports deliberate replay.",
    ),
    _stripe_mutation_policy(
        operation="stripe.setup_intent.create",
        workflow_context="saved_card_setup_intent_creation",
        material_callers=(
            "backend.services.payment_method_service.create_saved_payment_method_setup_intent",
        ),
        safety_class=RetrySafetyClass.NO_AUTOMATIC_RETRY,
        provider_idempotency_key_used=True,
        idempotency_identity_source="request-local generated setup-intent key",
        client_retry_stable_idempotency=False,
        identity_survives_replay=False,
        current_recovery="Returned SetupIntent can be synced; create-timeout has no durable setup identity.",
        durable_follow_up="Durable setup-intent request identity is required before app retry.",
    ),
    _stripe_mutation_policy(
        operation="stripe.payment_intent.create",
        workflow_context="checkout_initial_create_before_provider_result",
        material_callers=(
            "backend.services.checkout_service.create_game_checkout_payment_intent_workflow",
        ),
        safety_class=RetrySafetyClass.NO_AUTOMATIC_RETRY,
        provider_idempotency_key_used=True,
        idempotency_identity_source=(
            "committed pending Booking and Payment rows with payment idempotency key"
        ),
        client_retry_stable_idempotency=False,
        identity_survives_replay=True,
        current_recovery=(
            "Create-timeout propagates unknown outcome after the pending checkout "
            "checkpoint is committed; ordinary app replay is not approved."
        ),
        durable_follow_up="WS05 owns post-expiry provider reconciliation if a provider object later appears.",
    ),
    _stripe_mutation_policy(
        operation="stripe.payment_intent.confirm",
        workflow_context="checkout_initial_confirm_after_checkpoint",
        material_callers=(
            "backend.services.checkout_service.create_game_checkout_payment_intent_workflow",
        ),
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        provider_idempotency_key_used=False,
        idempotency_identity_source="persisted checkout Payment row with provider PaymentIntent ID",
        client_retry_stable_idempotency=False,
        identity_survives_replay=True,
        current_recovery=(
            "After checkpoint commit, checkout reacquires game serialization and "
            "re-reads the persisted PaymentIntent before any confirmation decision."
        ),
        durable_follow_up="WS05 owns durable post-expiry checkout provider reconciliation.",
    ),
    _stripe_mutation_policy(
        operation="stripe.payment_intent.confirm",
        workflow_context="checkout_existing_pending_confirm_after_provider_read",
        material_callers=(
            "backend.services.checkout_service.create_game_checkout_payment_intent_workflow",
        ),
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        provider_idempotency_key_used=False,
        idempotency_identity_source="existing pending Payment row with persisted provider PaymentIntent ID",
        client_retry_stable_idempotency=False,
        identity_survives_replay=True,
        current_recovery=(
            "Active-hold re-entry acquires game serialization and retrieves provider "
            "PaymentIntent state before another confirmation decision."
        ),
        durable_follow_up="WS05 owns durable post-expiry checkout provider reconciliation.",
    ),
    _stripe_mutation_policy(
        operation="stripe.payment_intent.create",
        workflow_context="community_publish_fee_initial_create",
        material_callers=(
            "backend.services.community_game_publish_service.create_paid_publish_attempt",
        ),
        safety_class=RetrySafetyClass.NO_AUTOMATIC_RETRY,
        provider_idempotency_key_used=True,
        idempotency_identity_source="committed CommunityPublishAttempt and Payment rows",
        client_retry_stable_idempotency=False,
        identity_survives_replay=True,
        current_recovery=(
            "Create-timeout remains unknown after the local publish-fee attempt "
            "checkpoint is committed; ordinary app retry is not approved."
        ),
        durable_follow_up="Later repair/reconciliation is required before app-owned retry.",
    ),
    _stripe_mutation_policy(
        operation="stripe.payment_intent.confirm",
        workflow_context="community_publish_fee_confirm_after_checkpoint",
        material_callers=(
            "backend.services.community_game_publish_service.create_paid_publish_attempt",
        ),
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        provider_idempotency_key_used=False,
        idempotency_identity_source="committed community publish payment with provider PaymentIntent ID",
        client_retry_stable_idempotency=False,
        identity_survives_replay=True,
        current_recovery="Persisted publish payment state must be reconciled before another confirmation decision.",
        durable_follow_up="WS05 durable financial reconciliation.",
    ),
    _stripe_mutation_policy(
        operation="stripe.payment_intent.create",
        workflow_context="waitlist_auto_promotion_create",
        material_callers=(
            "backend.services.game_waitlist_service.promote_waitlist_entries",
            "backend.services.game_waitlist_service.attempt_paid_waitlist_auto_promotion",
        ),
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        provider_idempotency_key_used=True,
        idempotency_identity_source="promotion payment-row idempotency key inside locked waitlist workflow",
        client_retry_stable_idempotency=False,
        identity_survives_replay=True,
        current_recovery="Promotion processing/local state gates recovery; no blind client replay loop.",
        durable_follow_up="WS05 durable payment reconciliation.",
    ),
    _stripe_mutation_policy(
        operation="stripe.payment_intent.confirm",
        workflow_context="waitlist_auto_promotion_confirm",
        material_callers=(
            "backend.services.game_waitlist_service.promote_waitlist_entries",
            "backend.services.game_waitlist_service.attempt_paid_waitlist_auto_promotion",
        ),
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        provider_idempotency_key_used=False,
        idempotency_identity_source="promotion payment with provider PaymentIntent ID",
        client_retry_stable_idempotency=False,
        identity_survives_replay=True,
        current_recovery="Promotion processing/local state gates recovery before another mutation.",
        durable_follow_up="WS05 durable payment reconciliation.",
    ),
    _stripe_mutation_policy(
        operation="stripe.refund.create",
        workflow_context="admin_refund_retry",
        material_callers=("backend.services.admin_money_refund_service.retry_admin_money_refund",),
        safety_class=RetrySafetyClass.MANUAL_REPAIR,
        provider_idempotency_key_used=True,
        idempotency_identity_source="admin-supplied refund retry key scoped by refund/admin action",
        client_retry_stable_idempotency=True,
        identity_survives_replay=True,
        current_recovery="Admin state-gated retry blocks uncertain provider outcome until reconciliation.",
    ),
    _stripe_mutation_policy(
        operation="stripe.refund.create",
        workflow_context="official_game_cancellation_refund",
        material_callers=(
            "backend.services.game_cancellation_service.create_official_cancellation_refunds",
        ),
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        provider_idempotency_key_used=True,
        idempotency_identity_source="deterministic game/payment refund key plus refund record",
        client_retry_stable_idempotency=True,
        identity_survives_replay=True,
        current_recovery="Refund and money-issue state gate later recovery.",
        durable_follow_up="WS05 durable financial reconciliation.",
    ),
    _stripe_mutation_policy(
        operation="stripe.refund.create",
        workflow_context="official_player_removal_refund",
        material_callers=(
            "backend.services.official_game_player_removal_service.execute_admin_removal_refunds",
        ),
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        provider_idempotency_key_used=True,
        idempotency_identity_source="deterministic game/booking/payment refund key plus refund record",
        client_retry_stable_idempotency=True,
        identity_survives_replay=True,
        current_recovery="Refund and money-issue state gate later recovery.",
        durable_follow_up="WS05 durable financial reconciliation.",
    ),
    _stripe_mutation_policy(
        operation="stripe.refund.create",
        workflow_context="late_checkout_payment_refund",
        material_callers=(
            "backend.services.stripe_webhook_service.create_late_payment_refund_if_needed",
        ),
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        provider_idempotency_key_used=True,
        idempotency_identity_source="deterministic booking/payment late-refund key plus refund record",
        client_retry_stable_idempotency=True,
        identity_survives_replay=True,
        current_recovery="Late payment refund record gates later recovery.",
        durable_follow_up="WS05 durable financial reconciliation.",
    ),
    _stripe_mutation_policy(
        operation="stripe.refund.create",
        workflow_context="community_publish_financial_outcome_refund",
        material_callers=(
            "backend.services.admin_financial_outcome_service.apply_refund_outcome",
        ),
        safety_class=RetrySafetyClass.MANUAL_REPAIR,
        provider_idempotency_key_used=True,
        idempotency_identity_source="admin financial-outcome action key plus refund suffix",
        client_retry_stable_idempotency=True,
        identity_survives_replay=True,
        current_recovery="Admin financial outcome and money issue state gate recovery.",
        durable_follow_up="WS05 durable financial reconciliation.",
    ),
    _stripe_mutation_policy(
        operation="stripe.payment_method.detach",
        workflow_context="user_visible_saved_card_detach",
        material_callers=("backend.services.payment_method_service.detach_saved_payment_method",),
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        provider_idempotency_key_used=False,
        idempotency_identity_source="persisted saved-card row and provider PaymentMethod ID",
        client_retry_stable_idempotency=False,
        identity_survives_replay=True,
        current_recovery="Saved-card state must be re-read or support-repaired before another detach.",
    ),
    _stripe_mutation_policy(
        operation="stripe.payment_method.detach",
        workflow_context="account_deletion_saved_card_cleanup",
        material_callers=(
            "backend.services.account_deletion_service.detach_account_saved_payment_methods",
        ),
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        provider_idempotency_key_used=False,
        idempotency_identity_source="pending account-deletion cleanup state and provider PaymentMethod ID",
        client_retry_stable_idempotency=False,
        identity_survives_replay=True,
        current_recovery="Account deletion records cleanup failure for support/recovery.",
        durable_follow_up="WS05 durable account cleanup recovery.",
    ),
    _stripe_mutation_policy(
        operation="stripe.payment_method.detach",
        workflow_context="unpersisted_best_effort_payment_method_cleanup",
        material_callers=(
            "backend.services.payment_method_service.detach_unpersisted_payment_method",
        ),
        safety_class=RetrySafetyClass.NO_AUTOMATIC_RETRY,
        provider_idempotency_key_used=False,
        idempotency_identity_source="provider PaymentMethod intentionally not persisted locally",
        client_retry_stable_idempotency=False,
        identity_survives_replay=False,
        current_recovery="Best-effort cleanup failure does not create local saved-card state.",
    ),
    _stripe_mutation_policy(
        operation="stripe.customer.default_payment_method.set",
        workflow_context="saved_card_default_set",
        material_callers=(
            "backend.services.payment_method_service.sync_saved_payment_method",
            "backend.services.payment_method_service.set_default_saved_payment_method",
            "backend.services.payment_method_service.detach_saved_payment_method",
        ),
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        provider_idempotency_key_used=False,
        idempotency_identity_source="persisted saved-card/default-card state",
        client_retry_stable_idempotency=False,
        identity_survives_replay=True,
        current_recovery="Re-read/sync/support-repair; do not blindly set twice.",
    ),
    _stripe_mutation_policy(
        operation="stripe.customer.default_payment_method.clear",
        workflow_context="saved_card_default_clear",
        material_callers=("backend.services.payment_method_service.detach_saved_payment_method",),
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        provider_idempotency_key_used=False,
        idempotency_identity_source="persisted saved-card/default-card state",
        client_retry_stable_idempotency=False,
        identity_survives_replay=True,
        current_recovery="Re-read/sync/support-repair; do not blindly clear twice.",
    ),
)


OTHER_PROVIDER_OPERATION_RETRY_POLICIES: tuple[ProviderOperationRetryPolicy, ...] = (
    _read_policy(
        operation="firebase.token.verify",
        provider="firebase",
        workflow_context="authenticated_request_identity",
        material_callers=("backend.firebase_admin_client.verify_firebase_token",),
        current_recovery="Safe read timeout returns dependency-read retry-later.",
    ),
    _read_policy(
        operation="firebase.app_check.verify",
        provider="firebase",
        workflow_context="app_check_request_verification",
        material_callers=(
            "backend.firebase_admin_client.verify_firebase_app_check_token",
        ),
        current_recovery=(
            "WS03-03B maps unavailable verification to a safe request-level "
            "provider_unavailable response; no generic request replay or mutation "
            "replay is approved."
        ),
    ),
    _read_policy(
        operation="firebase.user.lookup",
        provider="firebase",
        workflow_context="authenticated_token_user_lookup",
        material_callers=("backend.firebase_admin_client.verify_firebase_token",),
        current_recovery="Safe read timeout returns dependency-read retry-later.",
    ),
    _read_policy(
        operation="firebase.user.lookup",
        provider="firebase",
        workflow_context="email_availability_lookup",
        material_callers=("backend.firebase_admin_client.firebase_email_exists",),
        current_recovery="Safe read timeout returns dependency-read retry-later.",
    ),
    ProviderOperationRetryPolicy(
        operation="firebase.user.delete",
        provider="firebase",
        workflow_context="account_deletion_auth_cleanup",
        material_callers=(
            "backend.services.account_deletion_service.delete_account_workflow",
            "backend.services.admin_user_delete_service.delete_admin_user",
            "backend.services.auth_account_service.cleanup_unfinished_account_workflow",
        ),
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        read_operation=False,
        provider_mutation=True,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        idempotency_identity_source="pending deletion and support/recovery state",
        client_retry_stable_idempotency=False,
        identity_survives_replay=True,
        unknown_outcome_possible=True,
        current_recovery="Pending deletion and support/recovery flags remain authoritative.",
        durable_follow_up="WS05 durable account cleanup recovery.",
    ),
    _read_policy(
        operation="r2.metadata.head",
        provider="r2",
        workflow_context="venue_image_metadata_verification",
        material_callers=("backend.services.r2_storage_service.get_object_properties",),
        current_recovery="Metadata verification fails with dependency-read semantics.",
    ),
    ProviderOperationRetryPolicy(
        operation="stripe.webhook.delivery",
        provider="stripe",
        workflow_context="stripe_webhook_provider_redelivery",
        material_callers=(
            "backend.routes.stripe_webhook_routes.handle_stripe_webhook",
            "backend.services.stripe_webhook_service.record_and_process_stripe_webhook_event",
        ),
        safety_class=RetrySafetyClass.PROVIDER_REDELIVERY,
        read_operation=False,
        provider_mutation=False,
        dependency_retry_owner=RetryOwnership.PROVIDER_REDELIVERY,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        idempotency_identity_source="provider event ID plus local uniqueness",
        client_retry_stable_idempotency=True,
        identity_survives_replay=True,
        unknown_outcome_possible=False,
        current_recovery="Provider event identity dedupe and idempotent processing.",
    ),
)


APPLICATION_RETRY_POLICIES: tuple[ProviderOperationRetryPolicy, ...] = (
    ProviderOperationRetryPolicy(
        operation="admin_money.refund.retry",
        provider="application",
        workflow_context="admin_refund_retry_state_gate",
        material_callers=("backend.services.admin_money_refund_service.retry_admin_money_refund",),
        safety_class=RetrySafetyClass.MANUAL_REPAIR,
        read_operation=False,
        provider_mutation=True,
        dependency_retry_owner=RetryOwnership.MANUAL_REPAIR,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=True,
        idempotency_identity_source="admin action idempotency key scoped to refund retry",
        client_retry_stable_idempotency=True,
        identity_survives_replay=True,
        unknown_outcome_possible=True,
        current_recovery="Admin state-gated retry blocks uncertain provider outcome.",
    ),
    ProviderOperationRetryPolicy(
        operation="admin_money.refund.reconcile",
        provider="application",
        workflow_context="admin_refund_reconcile_state_gate",
        material_callers=(
            "backend.services.admin_money_refund_service.reconcile_admin_money_refund",
        ),
        safety_class=RetrySafetyClass.MANUAL_REPAIR,
        read_operation=True,
        provider_mutation=False,
        dependency_retry_owner=RetryOwnership.MANUAL_REPAIR,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        idempotency_identity_source="admin action idempotency key scoped to refund reconcile",
        client_retry_stable_idempotency=True,
        identity_survives_replay=True,
        unknown_outcome_possible=False,
        current_recovery="Admin state-gated reconciliation reads provider/local state.",
    ),
    ProviderOperationRetryPolicy(
        operation="admin_money.credit.retry",
        provider="application",
        workflow_context="admin_credit_repair_state_gate",
        material_callers=("backend.services.admin_money_issue_service.retry_admin_money_issue_credit",),
        safety_class=RetrySafetyClass.MANUAL_REPAIR,
        read_operation=False,
        provider_mutation=False,
        dependency_retry_owner=RetryOwnership.MANUAL_REPAIR,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        idempotency_identity_source="money issue and game-credit ledger idempotency",
        client_retry_stable_idempotency=True,
        identity_survives_replay=True,
        unknown_outcome_possible=False,
        current_recovery="Money issue and credit ledger idempotency remain authoritative.",
    ),
)


PROVIDER_OPERATION_RETRY_POLICIES: tuple[ProviderOperationRetryPolicy, ...] = (
    *STRIPE_OPERATION_RETRY_POLICIES,
    *OTHER_PROVIDER_OPERATION_RETRY_POLICIES,
    *APPLICATION_RETRY_POLICIES,
)


FANOUT_EXECUTION_POLICIES: tuple[FanoutExecutionPolicy, ...] = (
    FanoutExecutionPolicy(
        workflow="platform_notice.selected_user_publish",
        execution_model="synchronous_sequential_db_insert",
        current_bound="Selected-user product maximum is 500 recipients.",
        provider_calls_per_item="none",
        new_concurrency_allowed=False,
        durable_follow_up="Future external notice delivery belongs to WS05.",
    ),
    FanoutExecutionPolicy(
        workflow="game_chat.notification_rows",
        execution_model="synchronous_sequential_db_work",
        current_bound="Current confirmed game chat members excluding sender.",
        provider_calls_per_item="none",
        new_concurrency_allowed=False,
        durable_follow_up="Future external chat delivery belongs to WS05.",
    ),
    FanoutExecutionPolicy(
        workflow="need_a_sub_chat.notification_rows",
        execution_model="synchronous_sequential_db_work",
        current_bound="Current confirmed Need-a-Sub chat members excluding sender.",
        provider_calls_per_item="none",
        new_concurrency_allowed=False,
        durable_follow_up="Future external chat delivery belongs to WS05.",
    ),
    FanoutExecutionPolicy(
        workflow="game_updated.notification_rows",
        execution_model="synchronous_sequential_db_work",
        current_bound="Current game update recipients.",
        provider_calls_per_item="none",
        new_concurrency_allowed=False,
        durable_follow_up="Future external update delivery belongs to WS05.",
    ),
    FanoutExecutionPolicy(
        workflow="waitlist.promotion",
        execution_model="synchronous_sequential_locked_workflow",
        current_bound="Available roster spots and ordered waitlist candidates.",
        provider_calls_per_item="possible Stripe payment per promoted paid entry",
        new_concurrency_allowed=False,
        durable_follow_up="Durable payment reconciliation belongs to WS05.",
    ),
    FanoutExecutionPolicy(
        workflow="account_deletion.cleanup",
        execution_model="synchronous_sequential_cleanup",
        current_bound="Current user-owned records and saved cards.",
        provider_calls_per_item="possible Firebase delete or Stripe detach per item.",
        new_concurrency_allowed=False,
        durable_follow_up="Durable cleanup recovery belongs to WS05.",
    ),
    FanoutExecutionPolicy(
        workflow="official_game_cancellation.refunds",
        execution_model="synchronous_sequential_refund_loop",
        current_bound="Current refundable successful payments for the canceled game.",
        provider_calls_per_item="possible Stripe refund per refundable payment.",
        new_concurrency_allowed=False,
        durable_follow_up="Durable financial reconciliation belongs to WS05.",
    ),
    FanoutExecutionPolicy(
        workflow="official_game_player_removal.refunds",
        execution_model="synchronous_sequential_refund_loop",
        current_bound="Current succeeded payments for the removed booking/player context.",
        provider_calls_per_item="possible Stripe refund per refundable payment.",
        new_concurrency_allowed=False,
        durable_follow_up="Durable financial reconciliation belongs to WS05.",
    ),
    FanoutExecutionPolicy(
        workflow="community_publish_fee.financial_outcome_refund",
        execution_model="single_admin_state_gated_workflow",
        current_bound="One publish-fee payment/refund context.",
        provider_calls_per_item="one possible Stripe refund.",
        new_concurrency_allowed=False,
        durable_follow_up="Durable financial reconciliation belongs to WS05.",
    ),
    FanoutExecutionPolicy(
        workflow="late_checkout_payment.refund",
        execution_model="single_webhook_repair_helper",
        current_bound="One late payment context.",
        provider_calls_per_item="one possible Stripe refund.",
        new_concurrency_allowed=False,
        durable_follow_up="Durable financial reconciliation belongs to WS05.",
    ),
)


DURABLE_WORK_HANDOFFS: tuple[DurableWorkHandoff, ...] = (
    DurableWorkHandoff(
        workflow="provider_unknown_outcome_reconciliation",
        current_safe_interim_behavior="Reconcile before retry, manual repair, or local pending/processing/support state.",
        why_durable_work_may_be_needed=(
            "Request-local recovery cannot guarantee later provider/local repair."
        ),
        required_durable_properties=(
            "claimable work identity",
            "stable replay payload reference",
            "idempotent handler",
            "bounded retry policy",
            "operator-visible exhausted state",
        ),
    ),
    DurableWorkHandoff(
        workflow="checkout_post_expiry_provider_reconciliation",
        current_safe_interim_behavior=(
            "Active-hold checkout resume reacquires game serialization, reuses pending "
            "checkout state, and re-reads the provider PaymentIntent; local expiration "
            "releases local capacity and credit holds while preserving provider identity."
        ),
        why_durable_work_may_be_needed=(
            "Delayed or missing provider/webhook outcomes after the request-local checkout hold need durable follow-up."
        ),
        required_durable_properties=(
            "persisted provider identity",
            "provider/local comparison",
            "idempotent repair decision",
            "credit/capacity compensation rules",
            "operator-visible exhausted state",
        ),
    ),
    DurableWorkHandoff(
        workflow="account_deletion_cleanup_recovery",
        current_safe_interim_behavior="Pending deletion and support flags.",
        why_durable_work_may_be_needed="Provider cleanup may outlive one request.",
        required_durable_properties=(
            "checkpointed cleanup stage",
            "safe re-entry",
            "provider outcome reconciliation",
            "support-visible failure state",
        ),
    ),
    DurableWorkHandoff(
        workflow="future_external_notification_delivery",
        current_safe_interim_behavior="In-app notification rows only.",
        why_durable_work_may_be_needed="External delivery will need durable handoff.",
        required_durable_properties=(
            "delivery job identity",
            "idempotent recipient handling",
            "retry and poison state",
            "redacted delivery telemetry",
        ),
    ),
    DurableWorkHandoff(
        workflow="future_platform_notice_external_delivery",
        current_safe_interim_behavior="Synchronous DB recipient record creation.",
        why_durable_work_may_be_needed="External bulk delivery cannot run unbounded.",
        required_durable_properties=(
            "audience snapshot",
            "claimable delivery work",
            "bounded worker concurrency",
            "partial-delivery state",
        ),
    ),
    DurableWorkHandoff(
        workflow="durable_financial_reconciliation",
        current_safe_interim_behavior="Admin refund retry/reconcile and money issues.",
        why_durable_work_may_be_needed="Manual repair may be insufficient at scale.",
        required_durable_properties=(
            "financial workflow identity",
            "provider/local comparison",
            "idempotent repair action",
            "auditable operator outcome",
        ),
    ),
)


def policies_by_operation(operation: str) -> tuple[ProviderOperationRetryPolicy, ...]:
    return tuple(
        policy
        for policy in PROVIDER_OPERATION_RETRY_POLICIES
        if policy.operation == operation
    )


def policy_by_operation(
    operation: str,
    *,
    workflow_context: str | None = None,
) -> ProviderOperationRetryPolicy:
    matches = policies_by_operation(operation)
    if not matches:
        raise KeyError(operation)

    if workflow_context is not None:
        for policy in matches:
            if policy.workflow_context == workflow_context:
                return policy
        raise KeyError(f"{operation}:{workflow_context}")

    if len(matches) > 1:
        contexts = ", ".join(sorted(policy.workflow_context for policy in matches))
        raise ValueError(
            f"operation {operation!r} has multiple retry-policy workflow contexts: {contexts}"
        )

    return matches[0]


def policy_by_operation_context(
    operation: str,
    workflow_context: str,
) -> ProviderOperationRetryPolicy:
    return policy_by_operation(operation, workflow_context=workflow_context)


def dependency_behavior_by_distribution(
    distribution_name: str,
) -> DependencyRetryBehavior:
    for behavior in DEPENDENCY_RETRY_BEHAVIORS:
        if behavior.distribution_name == distribution_name:
            return behavior
    raise KeyError(distribution_name)
