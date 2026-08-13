from __future__ import annotations

import ast
from pathlib import Path
from typing import Mapping

import pytest
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from starlette.routing import Mount

from backend.settings import build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_TEST_DATABASE_URL = "postgresql+psycopg://127.0.0.1:5432/pickup_lane_test_db"
_ALLOWED_ORIGIN = "https://app.example.invalid"
_IGNORED_SOURCE_PARTS = frozenset(
    {
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "alembic",
        "generated",
        "legacy",
        "scripts",
        "site-packages",
        "tests",
    }
)


def _settings_env(**overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": "test",
        "DATABASE_URL": _TEST_DATABASE_URL,
        "INBOX_TOKEN_SECRET": "synthetic-independent-api-error-token",
        "ALLOWED_HOSTS": "testserver,api.example.invalid",
        "CORS_ALLOWED_ORIGINS": _ALLOWED_ORIGIN,
        "ENABLE_API_DOCS": "true",
        "ENABLE_DB_HEALTH": "false",
        "ENABLE_STRIPE_PAYMENTS": "false",
    }
    for name, value in overrides.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def _create_app(monkeypatch: pytest.MonkeyPatch, **overrides: str | None):
    for name, value in _settings_env(**overrides).items():
        monkeypatch.setenv(name, value)
    reset_settings_cache()

    import backend.main as main_module

    settings = build_settings(
        _settings_env(**overrides),
        load_dotenv_file=False,
        validate_full=True,
    )
    return main_module.create_app(settings), main_module


def _source_files() -> tuple[Path, ...]:
    files: list[Path] = [_BACKEND_ROOT / "main.py"]
    for directory_name in ("observability", "routes", "services"):
        files.extend(sorted((_BACKEND_ROOT / directory_name).rglob("*.py")))
    return tuple(
        path
        for path in files
        if not any(part in _IGNORED_SOURCE_PARTS for part in path.relative_to(_REPO_ROOT).parts)
    )


def _source_map() -> dict[str, str]:
    return {
        path.relative_to(_REPO_ROOT).as_posix(): path.read_text()
        for path in _source_files()
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def _fastapi_constructor_locations() -> list[str]:
    locations: list[str] = []
    for relative, source in _source_map().items():
        tree = ast.parse(source)
        direct_names: set[str] = set()
        module_names: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module in {"fastapi", "fastapi.applications"}:
                for alias in node.names:
                    if alias.name == "FastAPI":
                        direct_names.add(alias.asname or alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "fastapi":
                        module_names.add(alias.asname or alias.name)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            call_name = _call_name(node.func)
            parts = call_name.split(".")
            if call_name in direct_names or (
                len(parts) >= 2 and parts[0] in module_names and parts[-1] == "FastAPI"
            ):
                locations.append(f"{relative}:{node.lineno}")
    return sorted(locations)


def _api_routes(app) -> tuple[APIRoute, ...]:
    return tuple(route for route in app.routes if isinstance(route, APIRoute))


def _assert_not_public_error_envelope(payload: Mapping[str, object]) -> None:
    assert not {"detail", "code", "message", "correlation_id"} <= set(payload)


@pytest.mark.requirement("WS02-04A-R6")
def test_invalid_host_remains_trusted_host_middleware_owned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _main_module = _create_app(monkeypatch, ALLOWED_HOSTS="testserver")

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.get("/live", headers={"Host": "evil.example.invalid"})

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "Invalid host header"
    assert response.headers["X-Request-ID"]


@pytest.mark.requirement("WS02-04A-R6")
def test_health_503_responses_remain_health_contracts_not_error_envelopes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, main_module = _create_app(monkeypatch, ENABLE_DB_HEALTH="true")
    monkeypatch.setattr(main_module, "_database_ready", lambda: False)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        ready_response = client.get("/ready", headers={"Host": "testserver"})
        db_health_response = client.get("/db-health", headers={"Host": "testserver"})

    assert ready_response.status_code == 503
    assert ready_response.json() == {
        "status": "not_ready",
        "release": "source-unavailable",
    }
    assert db_health_response.status_code == 503
    assert db_health_response.json() == {
        "message": "Database connection is unavailable",
    }
    _assert_not_public_error_envelope(ready_response.json())
    _assert_not_public_error_envelope(db_health_response.json())


@pytest.mark.requirement("WS02-04A-R6")
def test_docs_openapi_and_disabled_docs_boundaries_are_distinct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_enabled_app, _main_module = _create_app(monkeypatch, ENABLE_API_DOCS="true")

    with TestClient(docs_enabled_app, follow_redirects=False, raise_server_exceptions=False) as client:
        docs_response = client.get("/docs", headers={"Host": "testserver"})
        openapi_response = client.get("/openapi.json", headers={"Host": "testserver"})

    assert docs_response.status_code == 200
    assert docs_response.headers["content-type"].startswith("text/html")
    assert "SwaggerUIBundle" in docs_response.text
    assert openapi_response.status_code == 200
    assert openapi_response.headers["content-type"].startswith("application/json")
    _assert_not_public_error_envelope(openapi_response.json())

    docs_disabled_app, _main_module = _create_app(monkeypatch, ENABLE_API_DOCS="false")
    with TestClient(docs_disabled_app, follow_redirects=False, raise_server_exceptions=False) as client:
        missing_docs_response = client.get("/docs", headers={"Host": "testserver"})

    assert missing_docs_response.status_code == 404
    payload = missing_docs_response.json()
    assert payload["code"] == "API.NOT_FOUND"
    assert payload["correlation_id"] == missing_docs_response.headers["X-Request-ID"]


@pytest.mark.requirement("WS02-04A-R6")
def test_static_redirect_and_no_content_surfaces_keep_their_owners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _main_module = _create_app(monkeypatch)

    static_mounts = [
        route for route in app.routes if isinstance(route, Mount) and route.path == "/static"
    ]
    assert len(static_mounts) == 1
    assert isinstance(static_mounts[0].app, StaticFiles)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        missing_static_response = client.get(
            "/static/missing.txt",
            headers={"Host": "testserver"},
        )
        redirect_response = client.get("/live/", headers={"Host": "testserver"})

    assert missing_static_response.status_code == 404
    assert missing_static_response.json()["code"] == "API.NOT_FOUND"
    assert "Cache-Control" not in missing_static_response.headers
    assert redirect_response.status_code == 307
    assert redirect_response.headers["location"] == "http://testserver/live"
    assert redirect_response.text == ""

    no_content_routes = [
        route.path
        for route in _api_routes(app)
        if route.status_code == 204
    ]
    assert no_content_routes == ["/auth/unfinished-account"]


@pytest.mark.requirement("WS02-04A-R6", "WS02-04A-R7")
def test_static_source_has_no_invented_file_streaming_or_websocket_error_owner() -> None:
    combined_source = "\n".join(_source_map().values())

    assert "FileResponse" not in combined_source
    assert "StreamingResponse" not in combined_source
    assert "WebSocket" not in combined_source
    assert ".websocket(" not in combined_source
    assert "app.mount(\"/static\", StaticFiles(directory=STATIC_DIR), name=\"static\")" in combined_source


@pytest.mark.requirement("WS02-04A-R7")
def test_single_exception_handler_and_app_construction_owners_remain_canonical() -> None:
    sources = _source_map()
    handler_sources = [
        relative
        for relative, source in sources.items()
        if ".add_exception_handler(" in source or ".exception_handler(" in source
    ]

    assert handler_sources == ["backend/observability/http_errors.py"]
    assert sources["backend/observability/http_errors.py"].count("app.add_exception_handler(") == 3
    assert sources["backend/main.py"].count("register_exception_handlers(app)") == 1
    assert sources["backend/main.py"].count("app.add_middleware(CorrelationIdMiddleware)") == 1
    constructor_locations = _fastapi_constructor_locations()
    assert len(constructor_locations) == 1
    assert constructor_locations[0].startswith("backend/main.py:")


@pytest.mark.requirement("WS02-04A-R7")
def test_no_route_local_error_envelope_or_duplicate_correlation_injector_exists() -> None:
    sources = _source_map()
    route_sources = {
        relative: source
        for relative, source in sources.items()
        if relative.startswith("backend/routes/")
    }
    route_combined_source = "\n".join(route_sources.values())

    assert "add_exception_handler" not in route_combined_source
    assert ".exception_handler(" not in route_combined_source
    assert "PublicErrorDescriptor" not in route_combined_source
    assert "public_error_response" not in route_combined_source
    assert "CORRELATION_ID_HEADER" not in route_combined_source
    assert "X-Request-ID" not in route_combined_source
