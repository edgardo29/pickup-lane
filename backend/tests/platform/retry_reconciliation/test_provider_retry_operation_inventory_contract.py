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
_ALLOWED_RUNTIME_BOUNDARIES = {
    "stripe": {"backend/services/stripe_service.py"},
    "firebase_admin": {"backend/firebase_admin_client.py"},
    "boto3": {"backend/services/r2_storage_service.py"},
    "botocore": {"backend/services/r2_storage_service.py"},
}
_ALLOWED_TOOLING = {
    "firebase_admin": {
        "backend/bootstrap_admin.py",
    },
    # The test runner resolves database hosts to reject non-loopback targets;
    # it does not make a production provider request.
    "socket": {"backend/test_runner.py"},
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


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
    return None


def _matched_network_module(module_name: str) -> str | None:
    for candidate in _NETWORK_MODULES:
        if module_name == candidate or module_name.startswith(f"{candidate}."):
            return candidate
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


@pytest.mark.pass_provenance('WS02-04C2')
def test_current_runtime_provider_network_boundaries_have_retry_classifications() -> None:
    unclassified: list[_NetworkHit] = []
    for path in _production_python_files():
        for hit in _network_hits(path):
            runtime_paths = _ALLOWED_RUNTIME_BOUNDARIES.get(hit.module, set())
            tooling_paths = _ALLOWED_TOOLING.get(hit.module, set())
            if hit.path not in runtime_paths and hit.path not in tooling_paths:
                unclassified.append(hit)

    assert unclassified == []


@pytest.mark.pass_provenance('WS02-04C2', 'WS06-02')
def test_r2_presigning_and_backend_object_operations_are_classified() -> None:
    source = (_REPO_ROOT / "backend/services/r2_storage_service.py").read_text()

    assert "def create_object_upload_url" in source
    assert "def create_object_read_url" in source
    assert "generate_presigned_url" in source
    assert "def download_object" in source
    assert "def publish_object" in source
    assert "def delete_object" in source
    assert "head_object" not in source
    assert 'IfNoneMatch="*"' in source
    assert '"total_max_attempts": 1' in source
