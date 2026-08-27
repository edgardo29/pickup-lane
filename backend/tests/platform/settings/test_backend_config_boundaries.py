from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from backend.settings import (
    BACKEND_ENVIRONMENT_VARIABLES,
    DEDICATED_TEST_DATABASE_NAME,
    AppEnvironment,
)

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_FRONTEND_ROOT = _REPO_ROOT / "frontend"
_CANONICAL_SETTINGS_OWNER = _BACKEND_ROOT / "settings.py"
_NON_REPOSITORY_SOURCE_PARTS = frozenset(
    {".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__", "venv"}
)
_SETTINGS_SIDE_EFFECTFUL_IMPORT_MODULES = frozenset(
    {
        "alembic",
        "backend.database",
        "backend.firebase_admin_client",
        "backend.main",
        "backend.services.r2_storage_service",
        "backend.services.stripe_service",
        "boto3",
        "botocore",
        "firebase_admin",
        "httpx",
        "requests",
        "socket",
        "stripe",
        "urllib.request",
        "urllib3",
    }
)
_SETTINGS_SIDE_EFFECTFUL_SQLALCHEMY_IMPORT_NAMES = frozenset(
    {
        "create_engine",
        "engine_from_config",
        "sessionmaker",
    }
)

_BACKEND_PRIVATE_ENV_NAMES = frozenset(
    {
        "DATABASE_URL",
        "MIGRATION_DATABASE_URL",
        "INBOX_TOKEN_SECRET",
        "FIREBASE_ADMIN_CREDENTIALS_JSON",
        "FIREBASE_ADMIN_CREDENTIALS",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
    }
)
_EXPECTED_FRONTEND_PUBLIC_NAMES = frozenset(
    {
        "VITE_API_BASE_URL",
        "VITE_FIREBASE_API_KEY",
        "VITE_FIREBASE_AUTH_DOMAIN",
        "VITE_FIREBASE_PROJECT_ID",
        "VITE_FIREBASE_STORAGE_BUCKET",
        "VITE_FIREBASE_MESSAGING_SENDER_ID",
        "VITE_FIREBASE_APP_ID",
        "VITE_FIREBASE_MEASUREMENT_ID",
        "VITE_FIREBASE_APP_CHECK_MODE",
        "VITE_FIREBASE_APP_CHECK_RECAPTCHA_ENTERPRISE_SITE_KEY",
        "VITE_ENABLE_STRIPE_PAYMENTS",
        "VITE_STRIPE_PUBLISHABLE_KEY",
    }
)


def _parse_env_example_names(path: Path) -> frozenset[str]:
    names: set[str] = set()
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, _value = line.partition("=")
        if separator:
            names.add(name.strip())
    return frozenset(names)


def _frontend_source_env_names() -> frozenset[str]:
    names: set[str] = set()
    pattern = re.compile(r"\bimport\.meta\.env\.([A-Z][A-Z0-9_]*)\b")
    for path in (_FRONTEND_ROOT / "src").rglob("*"):
        if path.suffix not in {".js", ".jsx", ".ts", ".tsx"}:
            continue
        names.update(pattern.findall(path.read_text()))
    return frozenset(names)


def _is_runtime_python_file(path: Path) -> bool:
    if path.suffix != ".py":
        return False
    relative_parts = path.relative_to(_BACKEND_ROOT).parts
    if any(part in _NON_REPOSITORY_SOURCE_PARTS for part in relative_parts):
        return False
    if relative_parts[0] == "tests":
        return False
    return path != _CANONICAL_SETTINGS_OWNER


def _runtime_python_files() -> tuple[Path, ...]:
    return tuple(sorted(path for path in _BACKEND_ROOT.rglob("*.py") if _is_runtime_python_file(path)))


def _module_is_side_effectful_for_settings(module_name: str) -> bool:
    return any(
        module_name == blocked_module or module_name.startswith(f"{blocked_module}.")
        for blocked_module in _SETTINGS_SIDE_EFFECTFUL_IMPORT_MODULES
    )


def _settings_side_effectful_imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text())
    findings: list[str] = []
    relative = path.relative_to(_REPO_ROOT)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _module_is_side_effectful_for_settings(alias.name):
                    findings.append(f"{relative}:{node.lineno}:{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            imported_modules = {module_name}
            imported_modules.update(
                f"{module_name}.{alias.name}" for alias in node.names if module_name
            )
            if any(_module_is_side_effectful_for_settings(name) for name in imported_modules):
                findings.append(f"{relative}:{node.lineno}:{module_name}")
            if module_name in {"sqlalchemy", "sqlalchemy.engine", "sqlalchemy.orm"}:
                for alias in node.names:
                    if alias.name in _SETTINGS_SIDE_EFFECTFUL_SQLALCHEMY_IMPORT_NAMES:
                        findings.append(f"{relative}:{node.lineno}:{module_name}.{alias.name}")
    return tuple(findings)


def _environment_accesses(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text())
    os_aliases: set[str] = set()
    imported_getenv_names: set[str] = set()
    imported_environ_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "os":
                    os_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            for alias in node.names:
                if alias.name == "getenv":
                    imported_getenv_names.add(alias.asname or alias.name)
                elif alias.name == "environ":
                    imported_environ_names.add(alias.asname or alias.name)

    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in os_aliases and node.attr in {"environ", "getenv"}:
                findings.append(f"{path.relative_to(_REPO_ROOT)}:{node.lineno}:{node.attr}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in imported_getenv_names:
                findings.append(f"{path.relative_to(_REPO_ROOT)}:{node.lineno}:getenv")
        elif isinstance(node, ast.Name) and node.id in imported_environ_names:
            findings.append(f"{path.relative_to(_REPO_ROOT)}:{node.lineno}:environ")
    return tuple(findings)


@pytest.mark.requirement("WS02-01-R1")
def test_only_canonical_settings_owner_is_excluded_from_runtime_env_scan() -> None:
    assert _is_runtime_python_file(_CANONICAL_SETTINGS_OWNER) is False
    assert _is_runtime_python_file(_BACKEND_ROOT / "some_feature" / "settings.py") is True


@pytest.mark.requirement("WS02-01-R1")
def test_runtime_backend_code_does_not_bypass_authoritative_settings_boundary() -> None:
    direct_environment_access = [
        finding
        for path in _runtime_python_files()
        for finding in _environment_accesses(path)
    ]

    assert direct_environment_access == []


@pytest.mark.requirement("WS02-01-R7")
def test_authoritative_settings_owner_has_no_direct_runtime_or_provider_dependencies() -> None:
    assert _settings_side_effectful_imports(_CANONICAL_SETTINGS_OWNER) == ()


@pytest.mark.requirement("WS02-01-R6", "WS03-03B-R1", "WS03-03B-R2", "WS03-03B-R6")
def test_frontend_public_config_uses_vite_names_and_excludes_backend_private_names() -> None:
    frontend_example_names = _parse_env_example_names(_FRONTEND_ROOT / ".env.example")
    frontend_source_names = _frontend_source_env_names()
    frontend_names = frontend_example_names | frontend_source_names

    assert frontend_example_names == _EXPECTED_FRONTEND_PUBLIC_NAMES
    assert frontend_source_names <= _EXPECTED_FRONTEND_PUBLIC_NAMES
    assert all(name.startswith("VITE_") for name in frontend_names)
    assert {
        name
        for name in frontend_names
        if name.removeprefix("VITE_") in _BACKEND_PRIVATE_ENV_NAMES
    } == set()


@pytest.mark.requirement("WS02-01-R6", "WS02-01-R9", "WS03-03B-R1")
def test_backend_safe_example_names_are_declared_settings_names() -> None:
    backend_example_names = _parse_env_example_names(_BACKEND_ROOT / ".env.example")

    assert backend_example_names <= BACKEND_ENVIRONMENT_VARIABLES
    assert _BACKEND_PRIVATE_ENV_NAMES <= backend_example_names
    assert all(not name.startswith("VITE_") for name in backend_example_names)


@pytest.mark.requirement("WS02-01-R2", "WS02-01-R9")
def test_environment_vocabulary_matches_settings_plan_matrix_and_ci_artifacts() -> None:
    canonical_values = {environment.value for environment in AppEnvironment}
    backend_example = (_BACKEND_ROOT / ".env.example").read_text()
    plan_text = (
        _REPO_ROOT
        / "docs"
        / "production-readiness"
        / "planning"
        / "passes"
        / "ws02"
        / "ws02-01-typed-settings-environment-isolation.md"
    ).read_text()
    matrix_text = (
        _REPO_ROOT / "docs" / "production-readiness" / "governance" / "environment-matrix.md"
    ).read_text()
    workflow_text = (_REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()

    assert canonical_values == {"local", "test", "ci", "preview", "staging", "production"}
    for value in canonical_values:
        assert value in backend_example
        assert value in plan_text
        assert value in matrix_text
    assert "APP_ENV: ci" in workflow_text
    assert DEDICATED_TEST_DATABASE_NAME in workflow_text
