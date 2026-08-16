from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

REPO_ROOT = Path(__file__).resolve().parents[4]

ORDINARY_FRONTEND_ROOTS = [
    REPO_ROOT / "frontend/src/context",
    REPO_ROOT / "frontend/src/features",
    REPO_ROOT / "frontend/src/lib",
    REPO_ROOT / "frontend/src/pages/auth",
    REPO_ROOT / "frontend/src/pages/browse-games",
    REPO_ROOT / "frontend/src/pages/create-game",
    REPO_ROOT / "frontend/src/pages/inbox",
    REPO_ROOT / "frontend/src/pages/my-games",
    REPO_ROOT / "frontend/src/pages/need-a-sub",
    REPO_ROOT / "frontend/src/pages/profile",
]

ORDINARY_DISALLOWED_RESPONSE_FIELDS = {
    "provider_payment_intent_id",
    "provider_charge_id",
    "provider_refund_id",
    "raw_payload",
    "storage_object_key",
    "storage_bucket",
    "storage_account_id",
    "card_fingerprint",
    "stripe_payment_method_id",
    "stripe_customer_id",
    "reviewed_by_user_id",
    "removed_by_user_id",
    "restored_by_user_id",
}


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text()


def _ordinary_frontend_files() -> list[Path]:
    files: list[Path] = []
    for root in ORDINARY_FRONTEND_ROOTS:
        if not root.exists():
            continue
        for suffix in ("*.js", "*.jsx"):
            files.extend(path for path in root.rglob(suffix) if "admin" not in path.parts)
    return sorted(set(files))


@pytest.mark.requirement("WS02-05B2-R9")
def test_current_frontend_still_requires_retained_game_and_self_fields() -> None:
    from backend.schemas.game_schema import GameDetailRead
    from backend.schemas.user_schema import SelfUserRead

    assert "host_user_id" in GameDetailRead.model_fields
    assert "host_guest_max" in GameDetailRead.model_fields
    assert "email_verified_at" in SelfUserRead.model_fields
    assert "profile_photo_url" in SelfUserRead.model_fields

    selectors_source = _read("frontend/src/pages/browse-games/gameDetailsSelectors.js")
    view_model_source = _read("frontend/src/pages/browse-games/gameDetailsViewModel.jsx")
    verification_source = _read("frontend/src/context/authProviderVerificationActions.js")
    create_game_source = _read("frontend/src/pages/create-game/CreateGamePage.jsx")

    assert "host_user_id" in selectors_source
    assert "host_user_id" in view_model_source
    assert "host_guest_max" in view_model_source
    assert "email_verified_at" in verification_source
    assert "email_verified_at" in create_game_source


@pytest.mark.requirement("WS02-05B2-R9")
def test_public_image_ordering_uses_public_display_fields_only() -> None:
    selector_source = _read("frontend/src/pages/browse-games/gameImageSelectors.js")
    unit_test_source = _read("frontend/tests/unit/gameImageSelectors.test.js")

    assert "is_primary" in selector_source
    assert "sort_order" in selector_source
    assert "id" in selector_source
    assert "created_at" not in selector_source
    assert "storage_" not in selector_source
    assert "uploaded_by_user_id" not in selector_source

    assert "sortDisplayImages uses public image response fields only" in unit_test_source
    assert "is_primary" in unit_test_source
    assert "sort_order" in unit_test_source
    assert "created_at" not in unit_test_source
    assert "storage_" not in unit_test_source


@pytest.mark.requirement("WS02-05B2-R9")
def test_ordinary_frontend_callers_do_not_consume_removed_internal_response_fields() -> None:
    hits: dict[str, list[str]] = {}
    for path in _ordinary_frontend_files():
        source = path.read_text()
        for field_name in ORDINARY_DISALLOWED_RESPONSE_FIELDS:
            if field_name in source:
                hits.setdefault(field_name, []).append(str(path.relative_to(REPO_ROOT)))

    assert hits == {}
