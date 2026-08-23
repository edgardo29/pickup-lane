from __future__ import annotations

from pathlib import Path
from typing import get_origin

import pytest
from fastapi.routing import APIRoute

from backend.observability.http_contracts import route_is_tombstone
from backend.observability.pagination_contracts import (
    PAGINATION_CONTRACTS,
    PAGINATION_HANDOFFS,
    pagination_contract_keys,
    pagination_handoff_keys,
)
from backend.settings import build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
_ALLOWED_ORIGIN = "https://app.example.invalid"


def _settings_env() -> dict[str, str]:
    return {
        "APP_ENV": "test",
        "DATABASE_URL": _TEST_DATABASE_URL,
        "INBOX_TOKEN_SECRET": "synthetic-independent-http-contract-token",
        "ALLOWED_HOSTS": "testserver,api.example.invalid",
        "CORS_ALLOWED_ORIGINS": _ALLOWED_ORIGIN,
        "ENABLE_API_DOCS": "true",
        "ENABLE_DB_HEALTH": "false",
        "ENABLE_STRIPE_PAYMENTS": "false",
    }


def _create_app(monkeypatch: pytest.MonkeyPatch):
    for name, value in _settings_env().items():
        monkeypatch.setenv(name, value)
    reset_settings_cache()

    import backend.main as main_module

    settings = build_settings(
        _settings_env(),
        load_dotenv_file=False,
        validate_full=True,
    )
    return main_module.create_app(settings)


def _api_routes(app) -> tuple[APIRoute, ...]:
    return tuple(route for route in app.routes if isinstance(route, APIRoute))


def _live_route_keys(app) -> set[tuple[str, str]]:
    return {
        (method.upper(), route.path)
        for route in _api_routes(app)
        for method in route.methods or ()
        if method.upper() not in {"HEAD", "OPTIONS"}
    }


def _response_model_name(route: APIRoute) -> str:
    response_model = route.response_model
    if response_model is None:
        return ""
    return getattr(response_model, "__name__", str(response_model))


def _is_inventory_relevant_collection_route(
    route: APIRoute,
    *,
    inventory_paths: set[str],
) -> bool:
    if "GET" not in {method.upper() for method in route.methods or ()}:
        return False
    if route_is_tombstone(route):
        return False

    response_model = route.response_model
    response_model_name = _response_model_name(route)
    return (
        get_origin(response_model) is list
        or response_model_name.startswith("list[")
        or "List" in response_model_name
        or "Page" in response_model_name
        or route.path in inventory_paths
    )


@pytest.mark.requirement("WS02-05A-R7")
@pytest.mark.requirement("WS04-01B-R1")
def test_pagination_contract_and_handoff_counts_are_current_live_and_disjoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)
    live_keys = _live_route_keys(app)
    contract_keys = pagination_contract_keys()
    handoff_keys = pagination_handoff_keys()

    assert len(PAGINATION_CONTRACTS) == 77
    assert len(PAGINATION_HANDOFFS) == 0
    assert len(contract_keys) == 77
    assert len(handoff_keys) == 0
    assert contract_keys.isdisjoint(handoff_keys)
    assert contract_keys <= live_keys
    assert handoff_keys <= live_keys


@pytest.mark.requirement("WS02-05A-R7")
@pytest.mark.requirement("WS04-01B-R1")
def test_every_relevant_current_collection_route_is_accounted_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)
    inventory_keys = pagination_contract_keys() | pagination_handoff_keys()
    inventory_paths = {path for _method, path in inventory_keys}
    relevant_collection_keys = {
        ("GET", route.path)
        for route in _api_routes(app)
        if _is_inventory_relevant_collection_route(route, inventory_paths=inventory_paths)
    }

    assert len(relevant_collection_keys) == 77
    assert relevant_collection_keys == inventory_keys


@pytest.mark.requirement("WS02-05A-R7")
@pytest.mark.requirement("WS04-01B-R1")
def test_approved_contract_entries_cover_current_collection_routes() -> None:
    assert all(contract.method == "GET" for contract in PAGINATION_CONTRACTS)
    assert all(contract.style for contract in PAGINATION_CONTRACTS)
    assert all(
        contract.max_owner in {"route", "route+service", "service"}
        for contract in PAGINATION_CONTRACTS
    )
    assert all(contract.deterministic_order for contract in PAGINATION_CONTRACTS)
    assert any(contract.limit_default is None for contract in PAGINATION_CONTRACTS)
    assert any(contract.limit_max is None for contract in PAGINATION_CONTRACTS)
    assert pagination_contract_keys().isdisjoint(pagination_handoff_keys())

    source = (_REPO_ROOT / "backend/observability/pagination_contracts.py").read_text()
    assert '"API owner"' not in source
    assert '"WS02-05B"' not in source
