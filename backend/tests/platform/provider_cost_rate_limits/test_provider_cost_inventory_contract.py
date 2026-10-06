from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]

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


@pytest.mark.pass_provenance('WS02-04C3B')
def test_current_source_entrypoints_cover_material_provider_cost_workflow_families() -> None:
    for relative_path, required_snippets in _SOURCE_ENTRYPOINTS.items():
        source = _read(relative_path)
        for snippet in required_snippets:
            assert snippet in source, f"{snippet!r} missing from {relative_path}"


@pytest.mark.pass_provenance('WS02-04C3B', 'WS06-02')
def test_venue_image_source_accounts_for_current_r2_object_operations() -> None:
    r2_source = _read("backend/services/r2_storage_service.py")
    venue_image_source = _read("backend/services/venue_image_service.py")

    assert "def create_object_upload_url" in r2_source
    assert "def create_object_read_url" in r2_source
    assert "generate_presigned_url" in r2_source
    assert "def download_object" in r2_source
    assert "def publish_object" in r2_source
    assert "def delete_object" in r2_source
    assert "head_object" not in r2_source
    assert "create_object_upload_url" in venue_image_source
    assert "create_object_read_url" in venue_image_source
    assert "download_object" in venue_image_source
    assert "publish_object" in venue_image_source
    assert "delete_object" in venue_image_source


@pytest.mark.pass_provenance('WS02-04C3B')
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
