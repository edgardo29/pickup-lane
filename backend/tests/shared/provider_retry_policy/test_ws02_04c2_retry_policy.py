from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace

import pytest

import backend.firebase_admin_client as firebase_admin_client
import backend.services.stripe_service as stripe_service
from backend.observability.timeouts import (
    DependencyMutationTimeoutUnknownError,
)
from backend.services.provider_retry_policy import (
    APPLICATION_RETRY_POLICIES,
    DEPENDENCY_RETRY_BEHAVIORS,
    DURABLE_WORK_HANDOFFS,
    FANOUT_EXECUTION_POLICIES,
    PROVIDER_OPERATION_RETRY_POLICIES,
    RetryOwnership,
    RetrySafetyClass,
    dependency_behavior_by_distribution,
    policy_by_operation,
)


pytestmark = pytest.mark.no_db_cleanup

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_required_retry_safety_classes_are_source_owned() -> None:
    assert {retry_class.value for retry_class in RetrySafetyClass} == {
        "SAFE_READ",
        "IDEMPOTENT_MUTATION",
        "RECONCILE_BEFORE_RETRY",
        "MANUAL_REPAIR",
        "PROVIDER_REDELIVERY",
        "NO_AUTOMATIC_RETRY",
    }


def test_dependency_retry_versions_match_installed_packages() -> None:
    for behavior in DEPENDENCY_RETRY_BEHAVIORS:
        assert behavior.installed_version == version(behavior.distribution_name)


def test_dependency_owned_behavior_has_no_pickup_lane_retry_numbers() -> None:
    behaviors_by_distribution = {
        behavior.distribution_name: behavior
        for behavior in DEPENDENCY_RETRY_BEHAVIORS
    }

    assert behaviors_by_distribution["stripe"].owner == RetryOwnership.DEPENDENCY_OWNED
    assert (
        behaviors_by_distribution["firebase-admin"].owner
        == RetryOwnership.DEPENDENCY_OWNED
    )
    assert (
        behaviors_by_distribution["botocore"].owner
        == RetryOwnership.DEPENDENCY_OWNED
    )
    assert (
        behaviors_by_distribution["SQLAlchemy"].owner
        == RetryOwnership.APPLICATION_POLICY
    )

    for behavior in DEPENDENCY_RETRY_BEHAVIORS:
        assert behavior.approved_retry_attempts is None
        assert behavior.approved_backoff_seconds is None
        assert "version" in behavior.reassessment_trigger


def test_provider_operations_are_uniquely_classified_without_retry_numbers() -> None:
    operations = [policy.operation for policy in PROVIDER_OPERATION_RETRY_POLICIES]

    assert len(operations) == len(set(operations))
    for policy in PROVIDER_OPERATION_RETRY_POLICIES:
        assert policy.application_automatic_retry_allowed is False
        assert policy.approved_retry_attempts is None
        assert policy.approved_backoff_seconds is None


def test_stripe_policy_distinguishes_safe_reads_from_mutations() -> None:
    safe_reads = {
        "stripe.setup_intent.retrieve",
        "stripe.payment_method.retrieve",
        "stripe.payment_intent.retrieve",
        "stripe.refund.retrieve",
    }
    mutation_classes = {
        "stripe.customer.create": RetrySafetyClass.IDEMPOTENT_MUTATION,
        "stripe.setup_intent.create": RetrySafetyClass.NO_AUTOMATIC_RETRY,
        "stripe.payment_intent.create": RetrySafetyClass.IDEMPOTENT_MUTATION,
        "stripe.payment_intent.confirm": RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        "stripe.refund.create": RetrySafetyClass.IDEMPOTENT_MUTATION,
        "stripe.payment_method.detach": RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        "stripe.customer.default_payment_method.set": (
            RetrySafetyClass.RECONCILE_BEFORE_RETRY
        ),
        "stripe.customer.default_payment_method.clear": (
            RetrySafetyClass.RECONCILE_BEFORE_RETRY
        ),
    }

    for operation in safe_reads:
        policy = policy_by_operation(operation)
        assert policy.safety_class == RetrySafetyClass.SAFE_READ
        assert policy.read_operation is True
        assert policy.provider_mutation is False
        assert policy.dependency_retry_owner == RetryOwnership.DEPENDENCY_OWNED

    for operation, safety_class in mutation_classes.items():
        policy = policy_by_operation(operation)
        assert policy.safety_class == safety_class
        assert policy.read_operation is False
        assert policy.provider_mutation is True
        assert policy.unknown_outcome_possible is True


def test_setup_intent_create_is_not_stable_client_retry_without_persistence() -> None:
    policy = policy_by_operation("stripe.setup_intent.create")

    assert policy.safety_class == RetrySafetyClass.NO_AUTOMATIC_RETRY
    assert policy.provider_idempotency_key_used is True
    assert policy.client_retry_stable_idempotency is False
    assert policy.application_automatic_retry_allowed is False
    assert policy.durable_follow_up is not None


def test_unknown_provider_mutations_never_allow_blind_app_retry() -> None:
    allowed_unknown_mutation_classes = {
        RetrySafetyClass.IDEMPOTENT_MUTATION,
        RetrySafetyClass.RECONCILE_BEFORE_RETRY,
        RetrySafetyClass.MANUAL_REPAIR,
        RetrySafetyClass.NO_AUTOMATIC_RETRY,
    }

    for policy in PROVIDER_OPERATION_RETRY_POLICIES:
        if policy.unknown_outcome_possible and policy.provider_mutation:
            assert policy.application_automatic_retry_allowed is False
            assert policy.safety_class in allowed_unknown_mutation_classes
            assert policy.current_recovery


def test_manual_refund_and_webhook_ownership() -> None:
    manual_operations = {
        policy.operation: policy
        for policy in APPLICATION_RETRY_POLICIES
    }

    assert (
        manual_operations["admin_money.refund.retry"].safety_class
        == RetrySafetyClass.MANUAL_REPAIR
    )
    assert (
        manual_operations["admin_money.refund.reconcile"].safety_class
        == RetrySafetyClass.MANUAL_REPAIR
    )
    assert (
        policy_by_operation("stripe.webhook.delivery").safety_class
        == RetrySafetyClass.PROVIDER_REDELIVERY
    )
    assert (
        policy_by_operation("stripe.webhook.delivery").dependency_retry_owner
        == RetryOwnership.PROVIDER_REDELIVERY
    )


def test_firebase_and_r2_policy() -> None:
    assert (
        policy_by_operation("firebase.token.verify").safety_class
        == RetrySafetyClass.SAFE_READ
    )
    assert (
        policy_by_operation("firebase.user.lookup").safety_class
        == RetrySafetyClass.SAFE_READ
    )
    assert (
        policy_by_operation("firebase.user.delete").safety_class
        == RetrySafetyClass.RECONCILE_BEFORE_RETRY
    )
    assert (
        policy_by_operation("r2.metadata.head").safety_class
        == RetrySafetyClass.SAFE_READ
    )


def test_source_does_not_configure_provider_retry_counts() -> None:
    stripe_source = (REPO_ROOT / "backend/services/stripe_service.py").read_text()
    r2_source = (REPO_ROOT / "backend/services/r2_storage_service.py").read_text()
    firebase_source = (REPO_ROOT / "backend/firebase_admin_client.py").read_text()

    assert "max_network_retries" not in stripe_source
    assert "retries=" not in r2_source
    assert "retries =" not in r2_source
    assert "httpTimeout" in firebase_source
    assert "retry" not in firebase_source.lower()


def test_stripe_mutation_timeout_wrappers_do_not_call_provider_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def timed_out(label: str):
        def _call(*_args, **_kwargs):
            calls.append(label)
            raise TimeoutError("private provider diagnostic")

        return _call

    monkeypatch.setattr(stripe_service, "get_stripe_module", lambda: SimpleNamespace())

    mutation_client = SimpleNamespace(
        v1=SimpleNamespace(
            payment_intents=SimpleNamespace(confirm=timed_out("confirm")),
            payment_methods=SimpleNamespace(detach=timed_out("detach")),
            customers=SimpleNamespace(update=timed_out("customer_update")),
        )
    )
    monkeypatch.setattr(
        stripe_service,
        "get_stripe_client_pair",
        lambda: stripe_service.StripeClientPair(
            read=SimpleNamespace(),
            mutation=mutation_client,
        ),
    )

    with pytest.raises(DependencyMutationTimeoutUnknownError):
        stripe_service.confirm_payment_intent(
            "synthetic-payment-intent",
            payment_method_id="synthetic-payment-method",
        )

    with pytest.raises(DependencyMutationTimeoutUnknownError):
        stripe_service.detach_payment_method("synthetic-payment-method")

    with pytest.raises(DependencyMutationTimeoutUnknownError):
        stripe_service.set_customer_default_payment_method(
            customer_id="synthetic-customer",
            payment_method_id="synthetic-payment-method",
        )

    with pytest.raises(DependencyMutationTimeoutUnknownError):
        stripe_service.clear_customer_default_payment_method(
            customer_id="synthetic-customer",
        )

    assert calls == ["confirm", "detach", "customer_update", "customer_update"]


def test_firebase_delete_timeout_does_not_call_provider_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def timed_out_delete(*_args, **_kwargs) -> None:
        calls.append("delete")
        raise TimeoutError("private provider diagnostic")

    monkeypatch.setattr(firebase_admin_client, "initialize_firebase_admin", lambda: None)
    monkeypatch.setattr(firebase_admin_client.auth, "delete_user", timed_out_delete)

    with pytest.raises(DependencyMutationTimeoutUnknownError):
        firebase_admin_client.delete_firebase_user("synthetic-auth-user")

    assert calls == ["delete"]


def test_fanout_policy_remains_synchronous_and_without_execution_numbers() -> None:
    expected_workflows = {
        "platform_notice.selected_user_publish",
        "game_chat.notification_rows",
        "need_a_sub_chat.notification_rows",
        "waitlist.promotion",
        "account_deletion.cleanup",
    }

    assert {policy.workflow for policy in FANOUT_EXECUTION_POLICIES} == expected_workflows
    for policy in FANOUT_EXECUTION_POLICIES:
        assert policy.new_concurrency_allowed is False
        assert policy.approved_concurrency_cap is None
        assert policy.approved_batch_size is None
        assert "synchronous" in policy.execution_model


def test_durable_handoff_has_no_worker_numbers() -> None:
    for handoff in DURABLE_WORK_HANDOFFS:
        assert handoff.owner_pass == "WS05"
        assert handoff.approved_worker_retry_attempts is None
        assert handoff.approved_worker_concurrency is None
        assert handoff.approved_lease_seconds is None
        assert handoff.required_durable_properties


def test_relevant_provider_services_do_not_create_unbounded_async_tasks() -> None:
    service_paths = [
        "backend/services/platform_notice_service.py",
        "backend/services/game_chat_service.py",
        "backend/services/sub_post_chat_service.py",
        "backend/services/need_a_sub_notification_service.py",
        "backend/services/game_waitlist_service.py",
        "backend/services/account_deletion_service.py",
        "backend/services/payment_method_service.py",
        "backend/services/stripe_webhook_service.py",
    ]

    for service_path in service_paths:
        source = (REPO_ROOT / service_path).read_text()
        assert "asyncio.gather(" not in source
        assert "asyncio.create_task(" not in source
        assert ".create_task(" not in source


def test_dependency_behavior_lookup_is_exact() -> None:
    assert dependency_behavior_by_distribution("stripe").installed_version == "15.1.0"

    with pytest.raises(KeyError):
        dependency_behavior_by_distribution("unknown-provider")

    with pytest.raises(KeyError):
        policy_by_operation("unknown.operation")
