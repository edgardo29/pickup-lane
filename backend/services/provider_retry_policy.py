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
    safety_class: RetrySafetyClass
    read_operation: bool
    provider_mutation: bool
    dependency_retry_owner: RetryOwnership
    application_automatic_retry_allowed: bool
    provider_idempotency_key_used: bool
    client_retry_stable_idempotency: bool
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


STRIPE_OPERATION_RETRY_POLICIES: tuple[ProviderOperationRetryPolicy, ...] = (
    ProviderOperationRetryPolicy(
        operation="stripe.setup_intent.retrieve",
        provider="stripe",
        safety_class=RetrySafetyClass.SAFE_READ,
        read_operation=True,
        provider_mutation=False,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=False,
        unknown_outcome_possible=False,
        current_recovery="Safe read timeout returns dependency-read retry-later.",
    ),
    ProviderOperationRetryPolicy(
        operation="stripe.payment_method.retrieve",
        provider="stripe",
        safety_class=RetrySafetyClass.SAFE_READ,
        read_operation=True,
        provider_mutation=False,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=False,
        unknown_outcome_possible=False,
        current_recovery="Safe read timeout returns dependency-read retry-later.",
    ),
    ProviderOperationRetryPolicy(
        operation="stripe.payment_intent.retrieve",
        provider="stripe",
        safety_class=RetrySafetyClass.SAFE_READ,
        read_operation=True,
        provider_mutation=False,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=False,
        unknown_outcome_possible=False,
        current_recovery="Safe read timeout returns dependency-read retry-later.",
    ),
    ProviderOperationRetryPolicy(
        operation="stripe.refund.retrieve",
        provider="stripe",
        safety_class=RetrySafetyClass.SAFE_READ,
        read_operation=True,
        provider_mutation=False,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=False,
        unknown_outcome_possible=False,
        current_recovery="Admin reconciliation may re-read provider refund state.",
    ),
    ProviderOperationRetryPolicy(
        operation="stripe.customer.create",
        provider="stripe",
        safety_class=RetrySafetyClass.IDEMPOTENT_MUTATION,
        read_operation=False,
        provider_mutation=True,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=True,
        client_retry_stable_idempotency=True,
        unknown_outcome_possible=True,
        current_recovery="User-scoped customer idempotency key supports replay.",
    ),
    ProviderOperationRetryPolicy(
        operation="stripe.setup_intent.create",
        provider="stripe",
        safety_class=RetrySafetyClass.NO_AUTOMATIC_RETRY,
        read_operation=False,
        provider_mutation=True,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=True,
        client_retry_stable_idempotency=False,
        unknown_outcome_possible=True,
        current_recovery=(
            "Provider key is request-local only; returned SetupIntent can be synced."
        ),
        durable_follow_up=(
            "Durable setup-intent request identity is required before app retry."
        ),
    ),
    ProviderOperationRetryPolicy(
        operation="stripe.payment_intent.create",
        provider="stripe",
        safety_class=RetrySafetyClass.IDEMPOTENT_MUTATION,
        read_operation=False,
        provider_mutation=True,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=True,
        client_retry_stable_idempotency=True,
        unknown_outcome_possible=True,
        current_recovery="Payment row idempotency key is stable for checkout replay.",
    ),
    ProviderOperationRetryPolicy(
        operation="stripe.payment_intent.confirm",
        provider="stripe",
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        read_operation=False,
        provider_mutation=True,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=False,
        unknown_outcome_possible=True,
        current_recovery="Re-read PaymentIntent/webhook/local pending state before retry.",
    ),
    ProviderOperationRetryPolicy(
        operation="stripe.refund.create",
        provider="stripe",
        safety_class=RetrySafetyClass.IDEMPOTENT_MUTATION,
        read_operation=False,
        provider_mutation=True,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=True,
        client_retry_stable_idempotency=True,
        unknown_outcome_possible=True,
        current_recovery="Refund idempotency, events, money issues, and admin reconcile.",
    ),
    ProviderOperationRetryPolicy(
        operation="stripe.payment_method.detach",
        provider="stripe",
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        read_operation=False,
        provider_mutation=True,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=False,
        unknown_outcome_possible=True,
        current_recovery="Re-read/sync/support-repair; do not blindly detach twice.",
    ),
    ProviderOperationRetryPolicy(
        operation="stripe.customer.default_payment_method.set",
        provider="stripe",
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        read_operation=False,
        provider_mutation=True,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=False,
        unknown_outcome_possible=True,
        current_recovery="Re-read/sync/support-repair; do not blindly set twice.",
    ),
    ProviderOperationRetryPolicy(
        operation="stripe.customer.default_payment_method.clear",
        provider="stripe",
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        read_operation=False,
        provider_mutation=True,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=False,
        unknown_outcome_possible=True,
        current_recovery="Re-read/sync/support-repair; do not blindly clear twice.",
    ),
)


OTHER_PROVIDER_OPERATION_RETRY_POLICIES: tuple[ProviderOperationRetryPolicy, ...] = (
    ProviderOperationRetryPolicy(
        operation="firebase.token.verify",
        provider="firebase",
        safety_class=RetrySafetyClass.SAFE_READ,
        read_operation=True,
        provider_mutation=False,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=False,
        unknown_outcome_possible=False,
        current_recovery="Safe read timeout returns dependency-read retry-later.",
    ),
    ProviderOperationRetryPolicy(
        operation="firebase.user.lookup",
        provider="firebase",
        safety_class=RetrySafetyClass.SAFE_READ,
        read_operation=True,
        provider_mutation=False,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=False,
        unknown_outcome_possible=False,
        current_recovery="Safe read timeout returns dependency-read retry-later.",
    ),
    ProviderOperationRetryPolicy(
        operation="firebase.user.delete",
        provider="firebase",
        safety_class=RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        read_operation=False,
        provider_mutation=True,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=False,
        unknown_outcome_possible=True,
        current_recovery="Pending deletion and support/recovery flags remain authoritative.",
    ),
    ProviderOperationRetryPolicy(
        operation="r2.metadata.head",
        provider="r2",
        safety_class=RetrySafetyClass.SAFE_READ,
        read_operation=True,
        provider_mutation=False,
        dependency_retry_owner=RetryOwnership.DEPENDENCY_OWNED,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=False,
        unknown_outcome_possible=False,
        current_recovery="Metadata verification fails with dependency-read semantics.",
    ),
    ProviderOperationRetryPolicy(
        operation="stripe.webhook.delivery",
        provider="stripe",
        safety_class=RetrySafetyClass.PROVIDER_REDELIVERY,
        read_operation=False,
        provider_mutation=False,
        dependency_retry_owner=RetryOwnership.PROVIDER_REDELIVERY,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=False,
        unknown_outcome_possible=False,
        current_recovery="Provider event identity dedupe and idempotent processing.",
    ),
)


APPLICATION_RETRY_POLICIES: tuple[ProviderOperationRetryPolicy, ...] = (
    ProviderOperationRetryPolicy(
        operation="admin_money.refund.retry",
        provider="application",
        safety_class=RetrySafetyClass.MANUAL_REPAIR,
        read_operation=False,
        provider_mutation=True,
        dependency_retry_owner=RetryOwnership.MANUAL_REPAIR,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=True,
        client_retry_stable_idempotency=True,
        unknown_outcome_possible=True,
        current_recovery="Admin state-gated retry blocks uncertain provider outcome.",
    ),
    ProviderOperationRetryPolicy(
        operation="admin_money.refund.reconcile",
        provider="application",
        safety_class=RetrySafetyClass.MANUAL_REPAIR,
        read_operation=True,
        provider_mutation=False,
        dependency_retry_owner=RetryOwnership.MANUAL_REPAIR,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=True,
        unknown_outcome_possible=False,
        current_recovery="Admin state-gated reconciliation reads provider/local state.",
    ),
    ProviderOperationRetryPolicy(
        operation="admin_money.credit.retry",
        provider="application",
        safety_class=RetrySafetyClass.MANUAL_REPAIR,
        read_operation=False,
        provider_mutation=False,
        dependency_retry_owner=RetryOwnership.MANUAL_REPAIR,
        application_automatic_retry_allowed=False,
        provider_idempotency_key_used=False,
        client_retry_stable_idempotency=True,
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
        current_bound="Current confirmed game members.",
        provider_calls_per_item="none",
        new_concurrency_allowed=False,
        durable_follow_up="Future external chat delivery belongs to WS05.",
    ),
    FanoutExecutionPolicy(
        workflow="need_a_sub_chat.notification_rows",
        execution_model="synchronous_sequential_db_work",
        current_bound="Current confirmed Need-a-Sub chat members.",
        provider_calls_per_item="none",
        new_concurrency_allowed=False,
        durable_follow_up="Future external chat delivery belongs to WS05.",
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
        provider_calls_per_item="possible Firebase or Stripe mutation.",
        new_concurrency_allowed=False,
        durable_follow_up="Durable cleanup recovery belongs to WS05.",
    ),
)


DURABLE_WORK_HANDOFFS: tuple[DurableWorkHandoff, ...] = (
    DurableWorkHandoff(
        workflow="provider_unknown_outcome_reconciliation",
        current_safe_interim_behavior="Reconcile before retry or use manual repair.",
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
        workflow="future_platform_notice_delivery",
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


def policy_by_operation(operation: str) -> ProviderOperationRetryPolicy:
    for policy in PROVIDER_OPERATION_RETRY_POLICIES:
        if policy.operation == operation:
            return policy
    raise KeyError(operation)


def dependency_behavior_by_distribution(
    distribution_name: str,
) -> DependencyRetryBehavior:
    for behavior in DEPENDENCY_RETRY_BEHAVIORS:
        if behavior.distribution_name == distribution_name:
            return behavior
    raise KeyError(distribution_name)
