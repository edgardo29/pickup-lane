from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.settings import build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
_ALLOWED_ORIGIN = "https://app.example.invalid"
_CONFIGURED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]
_APPLICATION_CONFIGURED_HEADERS = [
    "Accept",
    "Authorization",
    "Content-Type",
    "X-Firebase-AppCheck",
    "X-Request-ID",
]
_STARLETTE_EFFECTIVE_HEADERS = (
    "Accept, Accept-Language, Authorization, Content-Language, Content-Type, "
    "X-Firebase-AppCheck, X-Request-ID"
)


def _settings_env(**overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": "test",
        "DATABASE_URL": _TEST_DATABASE_URL,
        "INBOX_TOKEN_SECRET": "synthetic-independent-http-security-token",
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


def _build(env: Mapping[str, str]):
    return build_settings(env, load_dotenv_file=False, validate_full=True)


def _import_main(monkeypatch: pytest.MonkeyPatch):
    for name, value in _settings_env().items():
        monkeypatch.setenv(name, value)
    reset_settings_cache()

    import backend.main as main_module

    return main_module


def _create_app(monkeypatch: pytest.MonkeyPatch, **overrides: str | None):
    main_module = _import_main(monkeypatch)
    settings = _build(_settings_env(**overrides))
    return main_module.create_app(settings)


def _cors_middleware(app, main_module):
    matches = [
        middleware
        for middleware in app.user_middleware
        if middleware.cls is main_module.CORSMiddleware
    ]
    assert len(matches) == 1
    return matches[0]


def _preflight(
    client: TestClient,
    *,
    origin: str = _ALLOWED_ORIGIN,
    method: str = "POST",
    headers: str = "Authorization",
):
    return client.options(
        "/live",
        headers={
            "Host": "testserver",
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )


def _route_source_files() -> tuple[Path, ...]:
    return (
        _BACKEND_ROOT / "main.py",
        *sorted((_BACKEND_ROOT / "routes").rglob("*.py")),
    )


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


def _literal_strings(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return (node.value,)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values: list[str] = []
        for element in node.elts:
            values.extend(_literal_strings(element))
        return tuple(values)
    return ()


def _manual_options_route_findings() -> list[str]:
    findings: list[str] = []
    for path in _route_source_files():
        tree = ast.parse(path.read_text())
        relative = path.relative_to(_REPO_ROOT)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            call_name = _call_name(node.func)
            method_name = call_name.split(".")[-1]
            if method_name == "options":
                findings.append(f"{relative}:{node.lineno}:options")
            if method_name not in {"api_route", "route"}:
                continue
            for keyword in node.keywords:
                if keyword.arg == "methods" and "OPTIONS" in {
                    value.upper() for value in _literal_strings(keyword.value)
                }:
                    findings.append(f"{relative}:{node.lineno}:OPTIONS")
    return findings


@pytest.mark.requirement("WS02-03-R4", "WS03-03B-R4", "WS03-03B-R6")
def test_cors_middleware_uses_exact_configured_methods_and_application_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_module = _import_main(monkeypatch)
    app = _create_app(monkeypatch)
    middleware = _cors_middleware(app, main_module)

    assert main_module.APPLICATION_CORS_ALLOWED_METHODS == tuple(_CONFIGURED_METHODS)
    assert main_module.APPLICATION_CORS_ALLOWED_HEADERS == tuple(_APPLICATION_CONFIGURED_HEADERS)
    assert middleware.kwargs["allow_methods"] == _CONFIGURED_METHODS
    assert middleware.kwargs["allow_headers"] == _APPLICATION_CONFIGURED_HEADERS
    assert "*" not in middleware.kwargs["allow_methods"]
    assert "*" not in middleware.kwargs["allow_headers"]


@pytest.mark.requirement("WS02-03-R4", "WS03-03B-R4")
def test_allowed_preflight_uses_exact_methods_and_effective_starlette_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        response = _preflight(client, headers="Authorization, X-Request-ID")

    assert response.status_code == 200
    assert response.text == "OK"
    assert response.headers["Access-Control-Allow-Origin"] == _ALLOWED_ORIGIN
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert response.headers["Access-Control-Allow-Methods"] == ", ".join(_CONFIGURED_METHODS)
    assert response.headers["Access-Control-Allow-Headers"] == _STARLETTE_EFFECTIVE_HEADERS
    assert "HEAD" not in response.headers["Access-Control-Allow-Methods"]
    assert "OPTIONS" not in response.headers["Access-Control-Allow-Methods"]


@pytest.mark.requirement("WS02-03-R4")
def test_starlette_safelisted_headers_are_accepted_without_expanding_application_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        response = _preflight(
            client,
            headers="Accept, Accept-Language, Content-Language, Content-Type",
        )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Headers"] == _STARLETTE_EFFECTIVE_HEADERS


@pytest.mark.requirement("WS02-03-R4")
def test_cors_header_matching_is_case_insensitive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        response = _preflight(client, headers="authorization, x-request-id")

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Headers"] == _STARLETTE_EFFECTIVE_HEADERS


@pytest.mark.requirement("WS02-03-R4", "WS03-03B-R4")
@pytest.mark.parametrize("header_name", ["X-Custom-Header", "X-Admin", "X-Forwarded-Host"])
def test_arbitrary_non_approved_preflight_headers_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    header_name: str,
) -> None:
    app = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        response = _preflight(client, headers=header_name)

    assert response.status_code == 400
    assert response.text == "Disallowed CORS headers"
    assert response.headers["Access-Control-Allow-Headers"] == _STARLETTE_EFFECTIVE_HEADERS


@pytest.mark.requirement("WS02-03-R4")
@pytest.mark.parametrize("method", ["HEAD", "OPTIONS"])
def test_unreviewed_preflight_methods_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
) -> None:
    app = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        response = _preflight(client, method=method, headers="Authorization")

    assert response.status_code == 400
    assert response.text == "Disallowed CORS method"


@pytest.mark.requirement("WS02-03-R4")
@pytest.mark.parametrize(
    "origin",
    [
        "null",
        "https://app.example.invalid.evil",
        "https://evil-app.example.invalid",
        "http://app.example.invalid",
        "https://app.example.invalid:444",
        "https://app.example.invalid/path",
        "https://app.example.invalid?debug=true",
    ],
)
def test_disallowed_simple_origins_do_not_receive_allow_origin(
    monkeypatch: pytest.MonkeyPatch,
    origin: str,
) -> None:
    app = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/live", headers={"Host": "testserver", "Origin": origin})

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.requirement("WS02-03-R4")
def test_disallowed_origin_preflight_does_not_receive_cors_grant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        response = _preflight(
            client,
            origin="https://unauthorized.example.invalid",
            method="POST",
            headers="Authorization, X-Request-ID",
        )

    assert response.status_code == 400
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.requirement("WS02-03-R4")
def test_disallowed_origin_framework_error_does_not_receive_cors_grant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        response = client.get(
            "/missing-route",
            headers={
                "Host": "testserver",
                "Origin": "https://unauthorized.example.invalid",
            },
        )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["code"] == "API.NOT_FOUND"
    assert payload["detail"] == "Not Found"
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.requirement("WS02-03-R4")
def test_allowed_origin_simple_and_error_responses_preserve_cors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        live_response = client.get(
            "/live",
            headers={"Host": "testserver", "Origin": _ALLOWED_ORIGIN},
        )
        missing_response = client.get(
            "/missing-route",
            headers={"Host": "testserver", "Origin": _ALLOWED_ORIGIN},
        )
        no_origin_response = client.get("/live", headers={"Host": "testserver"})

    assert live_response.headers["Access-Control-Allow-Origin"] == _ALLOWED_ORIGIN
    assert live_response.headers["Access-Control-Allow-Credentials"] == "true"
    assert "Origin" in live_response.headers["Vary"]
    assert missing_response.status_code == 404
    assert missing_response.headers["Access-Control-Allow-Origin"] == _ALLOWED_ORIGIN
    assert "Access-Control-Allow-Origin" not in no_origin_response.headers


@pytest.mark.requirement("WS02-03-R4")
def test_no_manual_options_or_cors_header_bypass_exists_in_route_source() -> None:
    combined_source = "\n".join(path.read_text() for path in _route_source_files())

    assert _manual_options_route_findings() == []
    assert "Access-Control-Allow-Origin" not in combined_source
    assert "Access-Control-Allow-Headers" not in combined_source
