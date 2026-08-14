from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.tests.workflows.route_lifecycle_cleanup.test_retired_route_registration_contract import (
    RETIRED_MUTATION_ROUTES,
    RetiredMutationRoute,
)

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

_SENTINEL = "B2A2B1_SENTINEL_BODY_SHOULD_NOT_BECOME_ACCEPTED"


@pytest.fixture()
def app_with_clean_overrides():
    from backend.main import app

    app.dependency_overrides.clear()
    yield app
    app.dependency_overrides.clear()


def _install_active_admin_override(app) -> None:
    from backend.services.auth_service import require_active_admin

    app.dependency_overrides[require_active_admin] = lambda: object()


def _install_rejecting_admin_override(app) -> None:
    from backend.services.auth_service import require_active_admin

    def reject_admin():
        raise HTTPException(status_code=401, detail="synthetic auth failure")

    app.dependency_overrides[require_active_admin] = reject_admin


def _request(client: TestClient, retired_route: RetiredMutationRoute, **kwargs):
    return client.request(retired_route.method, retired_route.concrete_path, **kwargs)


@pytest.mark.requirement("WS02-04B2A2B1-R1", "WS02-04B2A2B1-R2")
def test_all_retired_mutation_routes_return_410_for_authenticated_no_body_requests(
    app_with_clean_overrides,
) -> None:
    _install_active_admin_override(app_with_clean_overrides)

    with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
        for retired_route in RETIRED_MUTATION_ROUTES:
            response = _request(client, retired_route)

            assert response.status_code == 410, retired_route.id


@pytest.mark.requirement("WS02-04B2A2B1-R1", "WS02-04B2A2B1-R2")
def test_json_payloads_do_not_activate_validation_or_reflect_submitted_contract(
    app_with_clean_overrides,
) -> None:
    _install_active_admin_override(app_with_clean_overrides)

    with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
        for retired_route in RETIRED_MUTATION_ROUTES:
            response = _request(client, retired_route, json={"sentinel": _SENTINEL})

            assert response.status_code == 410, retired_route.id
            assert response.status_code != 422, retired_route.id
            assert _SENTINEL not in response.text, retired_route.id


@pytest.mark.requirement("WS02-04B2A2B1-R1", "WS02-04B2A2B1-R2")
def test_malformed_json_representatives_do_not_revive_route_owned_body_parsing(
    app_with_clean_overrides,
) -> None:
    _install_active_admin_override(app_with_clean_overrides)
    representatives = (
        RETIRED_MUTATION_ROUTES[0],
        RETIRED_MUTATION_ROUTES[1],
        RETIRED_MUTATION_ROUTES[-1],
    )

    with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
        for retired_route in representatives:
            response = _request(
                client,
                retired_route,
                content=b'{"unterminated": ',
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 410, retired_route.id
            assert response.status_code != 422, retired_route.id


@pytest.mark.requirement("WS02-04B2A2B1-R1")
def test_authentication_dependency_runs_before_representative_tombstone_handlers(
    app_with_clean_overrides,
) -> None:
    _install_rejecting_admin_override(app_with_clean_overrides)
    representatives = (
        RETIRED_MUTATION_ROUTES[0],
        RETIRED_MUTATION_ROUTES[1],
        RETIRED_MUTATION_ROUTES[-1],
    )

    with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
        for retired_route in representatives:
            response = _request(client, retired_route, json={"sentinel": _SENTINEL})

            assert response.status_code == 401, retired_route.id
            assert response.status_code != 410, retired_route.id
