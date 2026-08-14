from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pytest
from fastapi import Body, Depends, FastAPI
from fastapi.routing import APIRoute

from backend.observability.http_contracts import route_is_tombstone

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_BODYLESS_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_PLATFORM_NOTICE_CREATE = ("POST", "/admin/platform-notices")
_STRIPE_WEBHOOK = ("POST", "/stripe/webhook")
_RAW_BODY_CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.(body|json|form|stream)\s*\(")
_OWNERLESS_BODY_RE = re.compile(r"\bUploadFile\b|\bFile\s*\(|\bForm\s*\(|multipart")
_FORBIDDEN_LIMIT_CLASS_TOKENS = (
    "POLICY_REQUEST_BODY_LIMIT",
    "LEGAL_REQUEST_BODY_LIMIT",
    "PAYMENT_REQUEST_BODY_LIMIT",
    "REFUND_REQUEST_BODY_LIMIT",
    "PROVIDER_REQUEST_BODY_LIMIT",
    "R2_REQUEST_BODY_LIMIT",
)


def _settings_env() -> dict[str, str]:
    return {
        "APP_ENV": "test",
        "DATABASE_URL": "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db",
        "INBOX_TOKEN_SECRET": "synthetic-independent-request-limit-token",
        "ALLOWED_HOSTS": "testserver,api.example.invalid",
        "CORS_ALLOWED_ORIGINS": "https://app.example.invalid",
        "ENABLE_API_DOCS": "false",
        "ENABLE_DB_HEALTH": "false",
        "ENABLE_STRIPE_PAYMENTS": "false",
    }


def _create_app_and_main_module():
    from backend.settings import build_settings

    import backend.main as main_module

    settings = build_settings(
        _settings_env(),
        load_dotenv_file=False,
        validate_full=True,
    )
    return main_module.create_app(settings), main_module


def _route_methods(route: APIRoute) -> tuple[str, ...]:
    return tuple(sorted(method.upper() for method in (route.methods or ()) if method))


def _non_bodyless_methods(route: APIRoute) -> tuple[str, ...]:
    return tuple(method for method in _route_methods(route) if method not in _BODYLESS_METHODS)


def _route_key(route: APIRoute) -> tuple[tuple[str, ...], str]:
    return (_route_methods(route), route.path)


def _limit_route_key(route) -> tuple[tuple[str, ...], str]:
    return (tuple(sorted(route.methods)), route.path)


def _app_routes(app: FastAPI) -> tuple[APIRoute, ...]:
    return tuple(route for route in app.routes if isinstance(route, APIRoute))


def _final_body_routes(app: FastAPI) -> tuple[APIRoute, ...]:
    return tuple(
        route
        for route in _app_routes(app)
        if _non_bodyless_methods(route) and route.body_field is not None
    )


def _direct_body_routes(app: FastAPI) -> tuple[APIRoute, ...]:
    return tuple(
        route
        for route in _app_routes(app)
        if _non_bodyless_methods(route) and route.dependant.body_params
    )


def _is_platform_notice_special(route: APIRoute) -> bool:
    return any((method, route.path) == _PLATFORM_NOTICE_CREATE for method in _non_bodyless_methods(route))


def _ordinary_from_final_metadata(app: FastAPI) -> tuple[APIRoute, ...]:
    return tuple(route for route in _final_body_routes(app) if not _is_platform_notice_special(route))


def _production_python_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in _BACKEND_ROOT.rglob("*.py")
            if "tests" not in path.relative_to(_BACKEND_ROOT).parts
            and ".venv" not in path.relative_to(_BACKEND_ROOT).parts
            and "__pycache__" not in path.relative_to(_BACKEND_ROOT).parts
        )
    )


def _manual_body_consumers() -> tuple[tuple[str, str, str, str], ...]:
    consumers: list[tuple[str, str, str, str]] = []
    for path in _production_python_files():
        relative = path.relative_to(_REPO_ROOT).as_posix()
        for line in path.read_text().splitlines():
            for match in _RAW_BODY_CALL_RE.finditer(line):
                consumers.append((relative, match.group(1), match.group(2), line.strip()))
    return tuple(sorted(consumers))


def _ownerless_body_consumer_hits() -> tuple[tuple[str, str], ...]:
    hits: list[tuple[str, str]] = []
    for path in _production_python_files():
        relative = path.relative_to(_REPO_ROOT).as_posix()
        for line in path.read_text().splitlines():
            if _OWNERLESS_BODY_RE.search(line):
                hits.append((relative, line.strip()))
    return tuple(sorted(hits))


def _source_text(paths: Iterable[str]) -> str:
    return "\n".join((_REPO_ROOT / path).read_text() for path in paths)


@pytest.mark.requirement("WS02-04B2A2C-R1", "WS02-04B2A2C-R5")
def test_current_ordinary_route_inventory_is_derived_from_final_fastapi_body_metadata() -> None:
    app, main_module = _create_app_and_main_module()
    final_body_keys = {_route_key(route) for route in _final_body_routes(app)}
    direct_body_keys = {_route_key(route) for route in _direct_body_routes(app)}
    ordinary_keys = {_route_key(route) for route in _ordinary_from_final_metadata(app)}
    production_keys = {
        _limit_route_key(route)
        for route in main_module._ordinary_json_body_routes(app)
    }

    assert len(final_body_keys) == 82
    assert len(direct_body_keys) == 82
    assert final_body_keys == direct_body_keys
    assert len(ordinary_keys) == 81
    assert production_keys == ordinary_keys
    assert ((_PLATFORM_NOTICE_CREATE[0],), _PLATFORM_NOTICE_CREATE[1]) not in production_keys
    assert ((_STRIPE_WEBHOOK[0],), _STRIPE_WEBHOOK[1]) not in production_keys


@pytest.mark.requirement("WS02-04B2A2C-R1", "WS02-04B2A2C-R5")
def test_special_bodyless_and_tombstone_route_counts_remain_accounted_for() -> None:
    app, _main_module = _create_app_and_main_module()
    routes = _app_routes(app)
    final_body_routes = _final_body_routes(app)
    no_final_body_routes = [
        route
        for route in routes
        if _non_bodyless_methods(route) and route.body_field is None
    ]
    no_final_body_tombstones = [
        route for route in no_final_body_routes if route_is_tombstone(route)
    ]
    total_tombstones = [route for route in routes if route_is_tombstone(route)]
    bodyless_method_tombstones = [
        route
        for route in total_tombstones
        if any(method in _BODYLESS_METHODS for method in _route_methods(route))
    ]
    bodyless_method_body_routes = [
        route
        for route in routes
        if any(method in _BODYLESS_METHODS for method in _route_methods(route))
        and route.body_field is not None
    ]

    assert len(_ordinary_from_final_metadata(app)) == 81
    assert len(final_body_routes) == 82
    assert len(no_final_body_routes) == 63
    assert len(no_final_body_tombstones) == 44
    assert len(total_tombstones) == 45
    assert [_route_key(route) for route in bodyless_method_tombstones] == [
        (("GET",), "/notifications")
    ]
    assert bodyless_method_body_routes == []


@pytest.mark.requirement("WS02-04B2A2C-R1")
def test_dependency_declared_request_body_inherits_ordinary_selection() -> None:
    _app, main_module = _create_app_and_main_module()
    synthetic_app = FastAPI()

    def require_payload(payload: dict = Body(...)):
        return payload

    @synthetic_app.post("/dependency-body")
    def dependency_body_route(payload=Depends(require_payload)):
        return payload

    route = next(route for route in _app_routes(synthetic_app) if route.path == "/dependency-body")
    selected = main_module._ordinary_json_body_routes(synthetic_app)

    assert route.dependant.body_params == []
    assert route.body_field is not None
    assert [_limit_route_key(route) for route in selected] == [
        (("POST",), "/dependency-body")
    ]


@pytest.mark.requirement("WS02-04B2A2C-R1", "WS02-04B2A2C-R5")
def test_manual_raw_body_consumers_are_limited_to_signed_stripe_special_class() -> None:
    assert _manual_body_consumers() == (
        (
            "backend/routes/stripe_webhook_routes.py",
            "request",
            "body",
            "payload = await request.body()",
        ),
    )


@pytest.mark.requirement("WS02-04B2A2C-R1", "WS02-04B2A2C-R5")
def test_no_ownerless_file_form_multipart_or_pass_specific_limit_class_exists() -> None:
    source = _source_text(
        (
            "backend/main.py",
            "backend/settings.py",
            "backend/observability/request_body_limits.py",
        )
    )

    assert _ownerless_body_consumer_hits() == ()
    for token in _FORBIDDEN_LIMIT_CLASS_TOKENS:
        assert token not in source
    assert "PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES" in source
    assert "STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES" in source
    assert "ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES" in source


@pytest.mark.requirement("WS02-04B2A2C-R5")
def test_direct_r2_object_bytes_are_not_a_fastapi_request_body_class() -> None:
    app, _main_module = _create_app_and_main_module()
    upload_related_routes = [
        route
        for route in _app_routes(app)
        if "upload" in route.path or "image" in route.path
    ]

    assert upload_related_routes
    assert all("r2" not in route.path.lower() for route in upload_related_routes)
    assert _ownerless_body_consumer_hits() == ()
