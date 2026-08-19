from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Iterable

import pytest
from fastapi.routing import APIRoute

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

REPO_ROOT = Path(__file__).resolve().parents[4]
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"
POLICY_DOCUMENT_SEED = REPO_ROOT / "backend" / "scripts" / "seed_policy_document_scenario.py"
POLICY_ACCEPTANCE_SEED = REPO_ROOT / "backend" / "scripts" / "seed_policy_acceptance_scenario.py"
BOOKING_POLICY_ACCEPTANCE_SEED = (
    REPO_ROOT / "backend" / "scripts" / "seed_booking_policy_acceptance_scenario.py"
)
RETIRED_POLICY_LEGAL_SEEDS = (
    POLICY_DOCUMENT_SEED,
    POLICY_ACCEPTANCE_SEED,
    BOOKING_POLICY_ACCEPTANCE_SEED,
)
SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx"}
B3_TOMBSTONE_KEYS = frozenset(
    {
        ("POST", "/policy-documents"),
        ("PATCH", "/policy-documents/{policy_document_id}"),
        ("POST", "/policy-acceptances"),
        ("PATCH", "/policy-acceptances/{policy_acceptance_id}"),
    }
)
DISALLOWED_BODY_TYPES = {
    "PolicyDocumentCreate",
    "PolicyDocumentUpdate",
    "PolicyAcceptanceCreate",
    "PolicyAcceptanceUpdate",
}
DISALLOWED_BODY_PARAM_NAMES = {
    "policy_document",
    "policy_document_update",
    "policy_acceptance",
    "policy_acceptance_update",
}
DISALLOWED_MUTATION_SERVICE_CALLS = {
    "create_policy_document_record",
    "update_policy_document_record",
    "create_policy_acceptance_record",
    "update_policy_acceptance_record",
}
FORBIDDEN_POLICY_LIMIT_NAMES = (
    "POLICY_DOCUMENT_REQUEST_BODY_LIMIT",
    "POLICY_ACCEPTANCE_REQUEST_BODY_LIMIT",
    "POLICY_LEGAL_REQUEST_BODY_LIMIT",
    "LEGAL_TEXT_REQUEST_BODY_LIMIT",
    "POLICY_TEXT_REQUEST_BODY_LIMIT",
    "ACCEPTANCE_EVIDENCE_REQUEST_BODY_LIMIT",
)


def _frontend_sources() -> dict[Path, str]:
    return {
        path: path.read_text()
        for path in FRONTEND_SRC.rglob("*")
        if path.is_file() and path.suffix in SOURCE_SUFFIXES
    }


def _iter_api_routes() -> Iterable[APIRoute]:
    from backend.main import app

    for route in app.routes:
        if isinstance(route, APIRoute):
            yield route


def _body_type_names(route: APIRoute) -> set[str]:
    names: set[str] = set()
    if route.body_field is not None:
        body_type = getattr(route.body_field, "type_", None)
        if body_type is not None:
            names.add(getattr(body_type, "__name__", repr(body_type)))
    for body_param in route.dependant.body_params:
        field_info = getattr(body_param, "field_info", None)
        annotation = getattr(body_param, "type_", None)
        if annotation is not None:
            names.add(getattr(annotation, "__name__", repr(annotation)))
        if field_info is not None:
            names.add(getattr(field_info, "annotation", "") or "")
    return {str(name) for name in names if name}


def _route_id(route: APIRoute) -> str:
    methods = ",".join(sorted(route.methods))
    return f"{methods} {route.path}"


@pytest.mark.requirement("WS02-04B2A2B3-R4")
def test_current_frontend_sources_do_not_construct_retired_policy_legal_writes() -> None:
    retired_write_fragments = (
        ("/policy-documents", "POST"),
        ("/policy-documents/", "PATCH"),
        ("/policy-acceptances", "POST"),
        ("/policy-acceptances/", "PATCH"),
    )

    for path, source in _frontend_sources().items():
        for endpoint_fragment, method in retired_write_fragments:
            for match in re.finditer(re.escape(endpoint_fragment), source):
                nearby_call_text = source[match.start() : match.start() + 700]
                assert not re.search(
                    rf"method\s*:\s*[`'\"]{method}[`'\"]",
                    nearby_call_text,
                    flags=re.IGNORECASE,
                ), f"{path.relative_to(REPO_ROOT)} constructs {method} {endpoint_fragment}"


@pytest.mark.requirement("WS02-04B2A2B3-R4")
def test_retired_policy_legal_seed_scripts_are_absent() -> None:
    assert [path for path in RETIRED_POLICY_LEGAL_SEEDS if path.exists()] == []


@pytest.mark.requirement("WS02-04B2A2B3-R4", "WS02-04B2A2B3-R5")
def test_no_alternate_active_route_accepts_policy_legal_write_bodies_or_calls_mutation_services() -> None:
    for route in _iter_api_routes():
        if any((method, route.path) in B3_TOMBSTONE_KEYS for method in route.methods):
            continue

        body_type_names = _body_type_names(route)
        body_param_names = {body_param.name for body_param in route.dependant.body_params}
        source = inspect.getsource(route.endpoint)

        assert DISALLOWED_BODY_TYPES.isdisjoint(body_type_names), _route_id(route)
        assert DISALLOWED_BODY_PARAM_NAMES.isdisjoint(body_param_names), _route_id(route)
        for function_name in DISALLOWED_MUTATION_SERVICE_CALLS:
            assert f"{function_name}(" not in source, _route_id(route)


@pytest.mark.requirement("WS02-04B2A2B3-R5")
def test_policy_legal_tombstones_have_no_same_method_alias_or_ordinary_body_route_selection() -> None:
    from backend.main import app

    request_body_middleware = [
        middleware
        for middleware in app.user_middleware
        if middleware.cls.__name__ == "RequestBodyLimitMiddleware"
    ]
    assert len(request_body_middleware) == 1
    ordinary_routes = request_body_middleware[0].kwargs["ordinary_json_body_routes"]
    ordinary_keys = {
        (method, route.path)
        for route in ordinary_routes
        for method in route.methods
    }

    for method, path in B3_TOMBSTONE_KEYS:
        aliases = [
            route.path
            for route in _iter_api_routes()
            if method in route.methods and route.path.rstrip("/") == path.rstrip("/")
        ]
        assert aliases == [path], f"{method} {path}"
        assert (method, path) not in ordinary_keys


@pytest.mark.requirement("WS02-04B2A2B3-R5")
def test_no_b3_specific_policy_legal_request_body_limit_class_or_numeric_threshold_exists() -> None:
    from backend.main import SPECIAL_BODY_ROUTE_KEYS
    from backend.observability import request_body_limits

    source = "\n".join(
        [
            (REPO_ROOT / "backend" / "main.py").read_text(),
            (REPO_ROOT / "backend" / "settings.py").read_text(),
            (REPO_ROOT / "backend" / "observability" / "request_body_limits.py").read_text(),
        ]
    ).upper()

    assert ("POST", "/policy-documents") not in SPECIAL_BODY_ROUTE_KEYS
    assert ("POST", "/policy-acceptances") not in SPECIAL_BODY_ROUTE_KEYS
    assert request_body_limits.PLATFORM_NOTICE_CREATE_PATH == "/admin/platform-notices"
    assert request_body_limits.STRIPE_WEBHOOK_PATH == "/stripe/webhook"
    for forbidden_name in FORBIDDEN_POLICY_LIMIT_NAMES:
        assert forbidden_name not in source
