from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_NETWORK_MODULES = frozenset(
    {
        "requests",
        "httpx",
        "aiohttp",
        "urllib.request",
        "socket",
        "stripe",
        "firebase_admin",
        "boto3",
        "botocore",
        "smtplib",
        "sendgrid",
        "twilio",
        "google",
    }
)
_ALLOWED_REQUEST_BOUNDARY = {
    "stripe": {"backend/services/stripe_service.py"},
    "firebase_admin": {"backend/firebase_admin_client.py"},
    "boto3": {"backend/services/r2_storage_service.py"},
    "botocore": {"backend/services/r2_storage_service.py"},
}
_ALLOWED_TOOLING = {
    "firebase_admin": {
        "backend/scripts/bootstrap_admin.py",
    }
}


@dataclass(frozen=True)
class _NetworkHit:
    path: str
    module: str
    detail: str


def _production_python_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in _BACKEND_ROOT.rglob("*.py")
            if "tests" not in path.relative_to(_BACKEND_ROOT).parts
            and ".venv" not in path.relative_to(_BACKEND_ROOT).parts
            and "__pycache__" not in path.relative_to(_BACKEND_ROOT).parts
            and "alembic" not in path.relative_to(_BACKEND_ROOT).parts
        )
    )


def _matched_network_module(module_name: str) -> str | None:
    for candidate in _NETWORK_MODULES:
        if module_name == candidate or module_name.startswith(f"{candidate}."):
            return candidate
    return None


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
    return None


def _network_hits(path: Path) -> list[_NetworkHit]:
    relative_path = str(path.relative_to(_REPO_ROOT))
    tree = ast.parse(path.read_text(), filename=relative_path)
    aliases: dict[str, str] = {}
    hits: list[_NetworkHit] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                matched = _matched_network_module(alias.name)
                if matched is not None:
                    aliases[alias.asname or alias.name.split(".", maxsplit=1)[0]] = matched
                    hits.append(_NetworkHit(relative_path, matched, f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom) and node.module:
            matched = _matched_network_module(node.module)
            if matched is not None:
                for alias in node.names:
                    aliases[alias.asname or alias.name] = matched
                hits.append(_NetworkHit(relative_path, matched, f"from {node.module} import"))
        elif isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name is None:
                continue
            root_name = name.split(".", maxsplit=1)[0]
            matched = aliases.get(root_name)
            if matched is not None:
                hits.append(_NetworkHit(relative_path, matched, name))
    return hits


def _unclassified_hits() -> list[_NetworkHit]:
    unclassified: list[_NetworkHit] = []
    for path in _production_python_files():
        for hit in _network_hits(path):
            allowed_request_paths = _ALLOWED_REQUEST_BOUNDARY.get(hit.module, set())
            allowed_tooling_paths = _ALLOWED_TOOLING.get(hit.module, set())
            if hit.path not in allowed_request_paths and hit.path not in allowed_tooling_paths:
                unclassified.append(hit)
    return unclassified


@pytest.mark.requirement("WS02-04C1-R9")
def test_current_provider_network_inventory_has_no_unclassified_production_bypass() -> None:
    assert _unclassified_hits() == []


@pytest.mark.requirement("WS02-04C1-R9")
def test_current_provider_boundaries_are_explicitly_accounted_for() -> None:
    hits_by_module: dict[str, set[str]] = {}
    for path in _production_python_files():
        for hit in _network_hits(path):
            hits_by_module.setdefault(hit.module, set()).add(hit.path)

    assert hits_by_module["stripe"] == {"backend/services/stripe_service.py"}
    assert hits_by_module["firebase_admin"] == {
        "backend/firebase_admin_client.py",
        "backend/scripts/bootstrap_admin.py",
    }
    assert hits_by_module["boto3"] == {"backend/services/r2_storage_service.py"}
    assert hits_by_module["botocore"] == {"backend/services/r2_storage_service.py"}


@pytest.mark.requirement("WS02-04C1-R4", "WS02-04C1-R9")
def test_r2_presign_and_stripe_webhook_boundaries_are_not_counted_as_provider_timeout_proof() -> None:
    r2_source = (_REPO_ROOT / "backend" / "services" / "r2_storage_service.py").read_text()
    stripe_source = (_REPO_ROOT / "backend" / "services" / "stripe_service.py").read_text()

    assert "generate_presigned_url" in r2_source
    assert "head_object" in r2_source
    assert "Webhook.construct_event" in stripe_source
    assert "construct_webhook_event" in stripe_source


@pytest.mark.requirement("WS02-04C1-R5", "WS02-04C1-R9")
def test_database_timeout_owner_files_are_current_inventory_members() -> None:
    settings_source = (_REPO_ROOT / "backend" / "settings.py").read_text()
    database_source = (_REPO_ROOT / "backend" / "database.py").read_text()

    assert "DB_POOL_WAIT_TIMEOUT_SECONDS" in settings_source
    assert "DB_STATEMENT_TIMEOUT_MILLISECONDS" in settings_source
    assert "DB_LOCK_TIMEOUT_MILLISECONDS" in settings_source
    assert '"pool_timeout": DATABASE_TIMEOUT_SETTINGS.pool_wait_timeout_seconds' in database_source
    assert "set_config('statement_timeout'" in database_source
    assert "set_config('lock_timeout'" in database_source
