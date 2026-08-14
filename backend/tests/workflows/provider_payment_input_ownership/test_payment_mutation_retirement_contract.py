from __future__ import annotations

import pytest
from fastapi.routing import APIRoute

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]


def _api_routes() -> list[APIRoute]:
    from backend.main import app

    return [route for route in app.routes if isinstance(route, APIRoute)]


def _route(method: str, path: str) -> APIRoute:
    matches = [
        route
        for route in _api_routes()
        if route.path == path and method.upper() in route.methods
    ]
    assert len(matches) == 1, f"{method} {path} should be registered exactly once"
    return matches[0]


def _dependency_names(route: APIRoute) -> set[str]:
    return {
        f"{dependency.call.__module__}.{dependency.call.__name__}"
        for dependency in route.dependant.dependencies
    }


@pytest.mark.requirement("WS02-04B2A2B2-R4")
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/payments"),
        ("PATCH", "/payments/{payment_id}"),
        ("POST", "/refunds"),
        ("PATCH", "/refunds/{refund_id}"),
        ("POST", "/payment-events"),
    ],
)
def test_generic_payment_refund_and_payment_event_mutations_are_bodyless_admin_tombstones(
    method: str,
    path: str,
) -> None:
    route = _route(method, path)
    dependency_names = _dependency_names(route)

    assert route.status_code == 410
    assert route.body_field is None
    assert "backend.services.auth_service.require_active_admin" in dependency_names
    assert "backend.database.get_db" not in dependency_names


@pytest.mark.requirement("WS02-04B2A2B2-R4")
def test_supported_payment_workflow_routes_remain_available() -> None:
    checkout = _route("POST", "/checkout/games/{game_id}/payment-intent")
    webhook = _route("POST", "/stripe/webhook")
    payment_event_repair = _route("PATCH", "/payment-events/{payment_event_id}")
    credit_issue = _route("POST", "/admin/game-credits/issue")
    money_refund_retry = _route("POST", "/admin/money/refunds/{refund_id}/retry")
    money_refund_reconcile = _route("POST", "/admin/money/refunds/{refund_id}/reconcile")

    assert checkout.status_code == 201
    assert webhook.status_code == 200
    assert payment_event_repair.status_code == 200
    assert credit_issue.status_code == 201
    assert money_refund_retry.status_code != 410
    assert money_refund_reconcile.status_code != 410
    assert checkout.body_field is not None
    assert payment_event_repair.body_field is not None
    assert credit_issue.body_field is not None
