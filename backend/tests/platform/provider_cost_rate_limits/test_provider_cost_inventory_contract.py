from __future__ import annotations

from pathlib import Path

import pytest

import backend.services.provider_retry_policy as retry_policy

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]

_EXPECTED_POLICY_KEYS = {
    ("stripe.setup_intent.retrieve", "saved_card_setup_sync"),
    ("stripe.payment_method.retrieve", "saved_card_setup_sync"),
    ("stripe.payment_intent.retrieve", "checkout_active_hold_reentry"),
    ("stripe.refund.retrieve", "admin_refund_reconciliation"),
    ("stripe.customer.create", "saved_card_customer_creation"),
    ("stripe.setup_intent.create", "saved_card_setup_intent_creation"),
    ("stripe.payment_intent.create", "checkout_initial_create_before_provider_result"),
    ("stripe.payment_intent.confirm", "checkout_initial_confirm_after_checkpoint"),
    ("stripe.payment_intent.confirm", "checkout_existing_pending_confirm_after_provider_read"),
    ("stripe.payment_intent.create", "community_publish_fee_initial_create"),
    ("stripe.payment_intent.confirm", "community_publish_fee_confirm_after_checkpoint"),
    ("stripe.payment_intent.create", "waitlist_auto_promotion_create"),
    ("stripe.payment_intent.confirm", "waitlist_auto_promotion_confirm"),
    ("stripe.refund.create", "admin_refund_retry"),
    ("stripe.refund.create", "official_game_cancellation_refund"),
    ("stripe.refund.create", "official_player_removal_refund"),
    ("stripe.refund.create", "late_checkout_payment_refund"),
    ("stripe.refund.create", "community_publish_financial_outcome_refund"),
    ("stripe.payment_method.detach", "user_visible_saved_card_detach"),
    ("stripe.payment_method.detach", "account_deletion_saved_card_cleanup"),
    ("stripe.payment_method.detach", "unpersisted_best_effort_payment_method_cleanup"),
    ("stripe.customer.default_payment_method.set", "saved_card_default_set"),
    ("stripe.customer.default_payment_method.clear", "saved_card_default_clear"),
    ("firebase.token.verify", "authenticated_request_identity"),
    ("firebase.user.lookup", "authenticated_token_user_lookup"),
    ("firebase.user.lookup", "email_availability_lookup"),
    ("firebase.user.delete", "account_deletion_auth_cleanup"),
    ("r2.metadata.head", "venue_image_metadata_verification"),
    ("stripe.webhook.delivery", "stripe_webhook_provider_redelivery"),
    ("admin_money.refund.retry", "admin_refund_retry_state_gate"),
    ("admin_money.refund.reconcile", "admin_refund_reconcile_state_gate"),
    ("admin_money.credit.retry", "admin_credit_repair_state_gate"),
}

_SOURCE_ENTRYPOINTS = {
    "backend/routes/checkout_routes.py": (
        'APIRouter(prefix="/checkout"',
        '"/games/{game_id}/payment-intent"',
        "create_game_checkout_payment_intent_workflow",
    ),
    "backend/routes/user_payment_method_routes.py": (
        'APIRouter(prefix="/user-payment-methods"',
        '"/setup-intent"',
        '"/sync"',
        "set_default_saved_payment_method",
        "detach_saved_payment_method",
    ),
    "backend/routes/community_game_publish_routes.py": (
        'APIRouter(prefix="/community-games"',
        '"/publish"',
        "publish_community_game_workflow",
    ),
    "backend/services/game_waitlist_service.py": (
        "def attempt_paid_waitlist_auto_promotion",
        "create_payment_intent",
        "confirm_payment_intent",
    ),
    "backend/routes/admin_money_routes.py": (
        'APIRouter(prefix="/admin/money"',
        "retry_admin_money_refund",
        "reconcile_admin_money_refund",
    ),
    "backend/routes/admin_official_game_routes.py": (
        'APIRouter(prefix="/admin/official-games"',
        '"/{game_id}/cancel"',
        '"/{game_id}/participants/{participant_id}/remove"',
    ),
    "backend/routes/auth_routes.py": (
        'APIRouter(prefix="/auth"',
        '"/email-availability"',
        '"/account"',
        "delete_account_workflow",
    ),
    "backend/routes/venue_image_routes.py": (
        'APIRouter(prefix="/venue-images"',
        "create_venue_image_upload",
        "complete_venue_image_upload",
    ),
    "backend/routes/stripe_webhook_routes.py": (
        'APIRouter(prefix="/stripe"',
        '"/webhook"',
        "record_and_process_stripe_webhook_event",
    ),
    "backend/routes/game_credit_routes.py": (
        'APIRouter(prefix="/game-credits"',
        'APIRouter(prefix="/admin/game-credits"',
        "issue_admin_game_credit",
        "reverse_admin_game_credit",
    ),
}

_RETIRED_GENERIC_MUTATIONS = {
    "backend/routes/payment_routes.py": "payment_generic_mutation_removed",
    "backend/routes/refund_routes.py": "refund_generic_mutation_removed",
    "backend/routes/payment_event_routes.py": "payment_event_generic_creation_removed",
    "backend/routes/host_publish_fee_routes.py": "host_publish_fee_scaffold_removed",
    "backend/routes/game_image_routes.py": "game_image_scaffold_removed",
}


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text()


def _policy_keys() -> set[tuple[str, str]]:
    return {
        (policy.operation, policy.workflow_context)
        for policy in retry_policy.PROVIDER_OPERATION_RETRY_POLICIES
    }


@pytest.mark.requirement("WS02-04C3B-R1", "WS02-04C3B-R3", "WS02-04C3B-R7")
def test_c2_provider_operation_registry_matches_current_c3b_inventory() -> None:
    assert _policy_keys() == _EXPECTED_POLICY_KEYS

    for policy in retry_policy.PROVIDER_OPERATION_RETRY_POLICIES:
        assert policy.material_callers
        assert policy.current_recovery
        assert policy.application_automatic_retry_allowed is False
        assert policy.approved_retry_attempts is None
        assert policy.approved_backoff_seconds is None

    mutation_contexts = {
        policy.workflow_context
        for policy in retry_policy.PROVIDER_OPERATION_RETRY_POLICIES
        if policy.provider_mutation
    }
    assert mutation_contexts == {
        "saved_card_customer_creation",
        "saved_card_setup_intent_creation",
        "checkout_initial_create_before_provider_result",
        "checkout_initial_confirm_after_checkpoint",
        "checkout_existing_pending_confirm_after_provider_read",
        "community_publish_fee_initial_create",
        "community_publish_fee_confirm_after_checkpoint",
        "waitlist_auto_promotion_create",
        "waitlist_auto_promotion_confirm",
        "admin_refund_retry",
        "official_game_cancellation_refund",
        "official_player_removal_refund",
        "late_checkout_payment_refund",
        "community_publish_financial_outcome_refund",
        "user_visible_saved_card_detach",
        "account_deletion_saved_card_cleanup",
        "unpersisted_best_effort_payment_method_cleanup",
        "saved_card_default_set",
        "saved_card_default_clear",
        "account_deletion_auth_cleanup",
        "admin_refund_retry_state_gate",
    }

    local_manual_contexts = {
        policy.workflow_context
        for policy in retry_policy.PROVIDER_OPERATION_RETRY_POLICIES
        if policy.provider == "application" and not policy.provider_mutation
    }
    assert local_manual_contexts == {
        "admin_refund_reconcile_state_gate",
        "admin_credit_repair_state_gate",
    }


@pytest.mark.requirement("WS02-04C3B-R1", "WS02-04C3B-R3")
def test_current_source_entrypoints_cover_material_c3b_workflow_families() -> None:
    for relative_path, required_snippets in _SOURCE_ENTRYPOINTS.items():
        source = _read(relative_path)
        for snippet in required_snippets:
            assert snippet in source, f"{snippet!r} missing from {relative_path}"


@pytest.mark.requirement("WS02-04C3B-R1", "WS02-04C3B-R3", "WS02-04C3B-R4")
def test_venue_image_inventory_distinguishes_local_signing_from_r2_metadata_head() -> None:
    r2_source = _read("backend/services/r2_storage_service.py")
    venue_image_source = _read("backend/services/venue_image_service.py")

    assert "def create_object_upload_url" in r2_source
    assert "def create_object_read_url" in r2_source
    assert "generate_presigned_url" in r2_source
    assert "def get_object_properties" in r2_source
    assert "head_object" in r2_source
    assert "create_object_upload_url" in venue_image_source
    assert "create_object_read_url" in venue_image_source
    assert "get_object_properties" in venue_image_source

    r2_policy = retry_policy.policy_by_operation("r2.metadata.head")
    assert r2_policy.workflow_context == "venue_image_metadata_verification"
    assert r2_policy.read_operation
    assert not r2_policy.provider_mutation
    assert ("r2.presigned_url.generate", "venue_image_metadata_verification") not in _policy_keys()


@pytest.mark.requirement("WS02-04C3B-R1", "WS02-04C3B-R3", "WS02-04C3B-R4")
def test_retired_generic_and_local_only_credit_paths_are_classified_truthfully() -> None:
    for relative_path, retired_code in _RETIRED_GENERIC_MUTATIONS.items():
        source = _read(relative_path)
        assert "raise_retired_mutation_route" in source
        assert retired_code in source

    credit_source = _read("backend/services/game_credit_admin_service.py")
    assert "def issue_admin_game_credit" in credit_source
    assert "def reverse_admin_game_credit" in credit_source
    assert "GameCredit(" in credit_source
    assert "GameCreditUsage(" in credit_source
    assert "stripe" not in credit_source.lower()
    assert "firebase" not in credit_source.lower()
    assert "r2" not in credit_source.lower()
