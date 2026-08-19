from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

REPO_ROOT = Path(__file__).resolve().parents[4]
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"
PAYMENT_METHODS_API = FRONTEND_SRC / "lib" / "paymentMethodsApi.js"
CHECKOUT_API = FRONTEND_SRC / "pages" / "browse-games" / "gameCheckoutApi.js"
INBOX_API = FRONTEND_SRC / "pages" / "inbox" / "inboxApi.js"
ADMIN_MONEY_API = FRONTEND_SRC / "pages" / "admin" / "money" / "adminMoneyApi.js"
SEED_PAYMENT_EVENT = REPO_ROOT / "backend" / "scripts" / "seed_payment_event_scenario.py"
SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx"}


def _frontend_sources() -> str:
    return "\n".join(
        path.read_text()
        for path in FRONTEND_SRC.rglob("*")
        if path.is_file() and path.suffix in SOURCE_SUFFIXES
    )


@pytest.mark.requirement("WS02-04B2A2B2-R7")
def test_current_callers_use_supported_setup_checkout_inbox_and_admin_money_flows() -> None:
    payment_methods_api = PAYMENT_METHODS_API.read_text()
    checkout_api = CHECKOUT_API.read_text()
    inbox_api = INBOX_API.read_text()
    admin_money_api = ADMIN_MONEY_API.read_text()

    assert "/user-payment-methods/setup-intent" in payment_methods_api
    assert "/user-payment-methods/sync" in payment_methods_api
    assert "/checkout/games/${gameId}/payment-intent" in checkout_api
    assert "/inbox/app-updates/global-seen" in inbox_api
    assert "/admin/money/payments" in admin_money_api
    assert "/admin/money/refunds" in admin_money_api
    assert "/admin/money/issues" in admin_money_api


@pytest.mark.requirement("WS02-04B2A2B2-R7")
def test_current_frontend_sources_do_not_construct_retired_generic_payment_mutations() -> None:
    source = _frontend_sources()

    retired_mutation_fragments = (
        "apiRequest('/payments', {",
        'apiRequest("/payments", {',
        "apiRequest(`/payments/${",
        "apiRequest('/refunds', {",
        'apiRequest("/refunds", {',
        "apiRequest(`/refunds/${",
        "apiRequest('/payment-events', {",
        'apiRequest("/payment-events", {',
    )
    for fragment in retired_mutation_fragments:
        assert fragment not in source


@pytest.mark.requirement("WS02-04B2A2B2-R7")
def test_retired_payment_event_seed_script_is_absent() -> None:
    assert not SEED_PAYMENT_EVENT.exists()
