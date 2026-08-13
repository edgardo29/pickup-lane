from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import MutableHeaders

from backend.settings import build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
_ALLOWED_ORIGIN = "https://app.example.invalid"
_STATIC_ASSET_PATH = "/static/seed/venues/harrison-park/gallery-1.webp"
_IGNORED_RUNTIME_PARTS = frozenset(
    {
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "generated",
        "site-packages",
        "tests",
    }
)
_IGNORED_RUNTIME_ROOTS = frozenset({"alembic", "scripts"})
_FORWARDED_HEADER_NAMES = frozenset(
    {
        "forwarded",
        "x-forwarded-for",
        "x-forwarded-host",
        "x-forwarded-proto",
    }
)
_FORWARDED_IDENTIFIER_NAMES = frozenset(
    {
        "forwarded",
        "forwarded_for",
        "forwarded_host",
        "forwarded_proto",
        "x_forwarded_for",
        "x_forwarded_host",
        "x_forwarded_proto",
    }
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
    return main_module.create_app(settings), main_module


def _runtime_relative_source_allowed(relative_path: str) -> bool:
    parts = tuple(part for part in Path(relative_path).parts if part not in {"."})
    if parts[:1] == ("backend",):
        parts = parts[1:]
    if not parts:
        return False
    if any(part in _IGNORED_RUNTIME_PARTS for part in parts):
        return False
    return parts[0] not in _IGNORED_RUNTIME_ROOTS


def _runtime_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    for path in _BACKEND_ROOT.rglob("*.py"):
        relative = path.relative_to(_REPO_ROOT).as_posix()
        if _runtime_relative_source_allowed(relative):
            sources[relative] = path.read_text()
    return sources


def _runtime_source_trees() -> dict[str, ast.Module]:
    return {relative: ast.parse(source) for relative, source in _runtime_sources().items()}


def _route_source_files() -> tuple[Path, ...]:
    return (
        _BACKEND_ROOT / "main.py",
        *sorted((_BACKEND_ROOT / "routes").rglob("*.py")),
    )


def _route_source_trees() -> dict[str, ast.Module]:
    return {
        path.relative_to(_REPO_ROOT).as_posix(): ast.parse(path.read_text())
        for path in _route_source_files()
    }


def _headers_for(
    main_module,
    *,
    method: str = "GET",
    path: str,
    status_code: int,
    content_type: str,
) -> MutableHeaders:
    message = {"type": "http.response.start", "status": status_code, "headers": []}
    headers = MutableHeaders(scope=message)
    if content_type:
        headers["Content-Type"] = content_type

    main_module._apply_response_security_headers(
        headers,
        method=method,
        path=path,
        private_routes=(),
        status_code=status_code,
    )
    return headers


def _assert_no_api_security_headers(headers: Mapping[str, str]) -> None:
    assert "X-Content-Type-Options" not in headers
    assert "Referrer-Policy" not in headers
    assert "Cache-Control" not in headers


def _casefolded_runtime_source() -> str:
    return "\n".join(_runtime_sources().values()).casefold()


def _normalize_header_literal(value: str) -> str:
    return value.strip().casefold()


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
    if isinstance(node, ast.JoinedStr):
        values: list[str] = []
        for value in node.values:
            values.extend(_literal_strings(value))
        return tuple(values)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values: list[str] = []
        for element in node.elts:
            values.extend(_literal_strings(element))
        return tuple(values)
    return ()


def _forwarded_metadata_authority_findings() -> list[str]:
    findings: list[str] = []
    for relative, tree in _runtime_source_trees().items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if _normalize_header_literal(node.value) in _FORWARDED_HEADER_NAMES:
                    findings.append(f"{relative}:{node.lineno}:header-literal")
            elif isinstance(node, ast.Name):
                if node.id.casefold() in _FORWARDED_IDENTIFIER_NAMES:
                    findings.append(f"{relative}:{node.lineno}:identifier")
            elif isinstance(node, ast.Attribute):
                if node.attr.casefold() in _FORWARDED_IDENTIFIER_NAMES:
                    findings.append(f"{relative}:{node.lineno}:attribute")
    return sorted(findings)


def _imported_fastapi_constructors(tree: ast.Module) -> tuple[set[str], set[str]]:
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
                    module_names.add(alias.asname or "fastapi")
    return direct_names, module_names


def _is_fastapi_constructor_call(
    node: ast.AST,
    *,
    direct_names: set[str],
    module_names: set[str],
) -> bool:
    if not isinstance(node, ast.Call):
        return False
    call_name = _call_name(node.func)
    if call_name in direct_names:
        return True
    parts = call_name.split(".")
    return len(parts) >= 2 and parts[0] in module_names and parts[-1] == "FastAPI"


def _assigned_names(target: ast.AST) -> tuple[str, ...]:
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in target.elts:
            names.extend(_assigned_names(element))
        return tuple(names)
    return ()


def _function_body_nodes(function: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[ast.AST, ...]:
    nodes: list[ast.AST] = []

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            nodes.append(child)
            visit(child)

    visit(function)
    return tuple(nodes)


def _fastapi_constructor_scope(tree: ast.Module, constructor: ast.AST) -> str:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(candidate is constructor for candidate in ast.walk(node)):
                return node.name
    return "<module>"


def _module_create_app_assignments(relative: str, tree: ast.Module) -> list[str]:
    owners: list[str] = []
    for node in tree.body:
        value: ast.AST | None = None
        targets: tuple[str, ...] = ()
        if isinstance(node, ast.Assign):
            value = node.value
            targets = tuple(name for target in node.targets for name in _assigned_names(target))
        elif isinstance(node, ast.AnnAssign):
            value = node.value
            targets = _assigned_names(node.target)
        if isinstance(value, ast.Call) and _call_name(value.func) == "create_app":
            owners.extend(f"{relative}:{target}=create_app" for target in targets)
    return owners


def _fastapi_app_owner_findings() -> dict[str, list[str]]:
    findings = {
        "constructor_owners": [],
        "module_app_owners": [],
    }
    for relative, tree in _runtime_source_trees().items():
        direct_names, module_names = _imported_fastapi_constructors(tree)
        for node in ast.walk(tree):
            if _is_fastapi_constructor_call(
                node,
                direct_names=direct_names,
                module_names=module_names,
            ):
                findings["constructor_owners"].append(
                    f"{relative}:{_fastapi_constructor_scope(tree, node)}"
                )
        findings["module_app_owners"].extend(_module_create_app_assignments(relative, tree))
    return {key: sorted(values) for key, values in findings.items()}


def _manual_options_route_findings() -> list[str]:
    findings: list[str] = []
    for relative, tree in _route_source_trees().items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            method_name = _call_name(node.func).split(".")[-1]
            if method_name == "options":
                findings.append(f"{relative}:{node.lineno}:options")
            if method_name not in {"api_route", "route"}:
                continue
            for keyword in node.keywords:
                if keyword.arg == "methods" and "OPTIONS" in {
                    value.upper() for value in _literal_strings(keyword.value)
                }:
                    findings.append(f"{relative}:{node.lineno}:OPTIONS")
    return sorted(findings)


def _route_level_cors_header_findings() -> list[str]:
    findings: list[str] = []
    for relative, tree in _route_source_trees().items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            normalized = node.value.strip().casefold()
            if normalized.startswith("access-control-allow-"):
                findings.append(f"{relative}:{node.lineno}:{normalized}")
    return sorted(findings)


@pytest.mark.requirement("WS02-03-R7")
def test_source_does_not_trust_forwarded_headers_or_install_proxy_middleware() -> None:
    combined_source = _casefolded_runtime_source()

    assert _forwarded_metadata_authority_findings() == []
    assert "proxyheadersmiddleware" not in combined_source
    assert "trustedproxy" not in combined_source


@pytest.mark.requirement("WS02-03-R7")
def test_source_does_not_claim_tls_hsts_or_canonical_redirect_ownership() -> None:
    combined_source = _casefolded_runtime_source()

    assert "httpsredirectmiddleware" not in combined_source
    assert "strict-transport-security" not in combined_source
    assert "www_redirect=true" not in combined_source
    assert "http_to_https" not in combined_source
    assert "https_redirect" not in combined_source
    assert "canonical_host" not in combined_source


@pytest.mark.requirement("WS02-03-R9")
def test_backend_runtime_exposes_only_canonical_fastapi_app_construction() -> None:
    assert _fastapi_app_owner_findings() == {
        "constructor_owners": ["backend/main.py:create_app"],
        "module_app_owners": ["backend/main.py:app=create_app"],
    }


@pytest.mark.requirement("WS02-03-R9")
def test_canonical_app_has_single_http_security_middleware_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, main_module = _create_app(monkeypatch)

    middleware_counts = {
        "cors": sum(
            middleware.cls is main_module.CORSMiddleware
            for middleware in app.user_middleware
        ),
        "host": sum(
            middleware.cls is main_module.TrustedHostMiddleware
            for middleware in app.user_middleware
        ),
        "headers": sum(
            middleware.cls is main_module.ResponseSecurityHeadersMiddleware
            for middleware in app.user_middleware
        ),
    }

    assert middleware_counts == {"cors": 1, "host": 1, "headers": 1}


@pytest.mark.requirement("WS02-03-R9")
def test_no_manual_options_or_route_level_cors_owner_bypass_exists() -> None:
    assert _manual_options_route_findings() == []
    assert _route_level_cors_header_findings() == []


@pytest.mark.requirement("WS02-03-R9")
def test_static_response_stays_outside_generic_api_header_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _main_module = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        response = client.get(_STATIC_ASSET_PATH, headers={"Host": "testserver"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    _assert_no_api_security_headers(response.headers)


@pytest.mark.requirement("WS02-03-R9")
def test_framework_slash_redirect_stays_outside_generic_api_header_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _main_module = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/live/", headers={"Host": "testserver"})

    assert response.status_code == 307
    assert response.headers["location"] == "http://testserver/live"
    _assert_no_api_security_headers(response.headers)


@pytest.mark.requirement("WS02-03-R9")
@pytest.mark.parametrize(
    ("path", "status_code", "content_type"),
    [
        (_STATIC_ASSET_PATH, 200, "application/json"),
        ("/live/", 307, "application/json"),
        ("/docs/", 307, "text/html"),
    ],
)
def test_response_header_helper_excludes_static_and_redirect_classes(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    status_code: int,
    content_type: str,
) -> None:
    main_module = _import_main(monkeypatch)

    headers = _headers_for(
        main_module,
        path=path,
        status_code=status_code,
        content_type=content_type,
    )

    _assert_no_api_security_headers(headers)
