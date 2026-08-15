from __future__ import annotations

from pathlib import Path

import pytest

import backend.services.provider_retry_policy as retry_policy

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"


def _requirements_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for line in (_BACKEND_ROOT / "requirements.txt").read_text().splitlines():
        if "==" not in line:
            continue
        name, version = line.strip().split("==", maxsplit=1)
        versions[name] = version
    return versions


def _production_sources() -> tuple[Path, ...]:
    return tuple(
        path
        for path in _BACKEND_ROOT.rglob("*.py")
        if "tests" not in path.relative_to(_BACKEND_ROOT).parts
        and ".venv" not in path.relative_to(_BACKEND_ROOT).parts
        and "__pycache__" not in path.relative_to(_BACKEND_ROOT).parts
        and "alembic" not in path.relative_to(_BACKEND_ROOT).parts
    )


@pytest.mark.requirement("WS02-04C2-R2")
def test_dependency_versions_match_repository_authority() -> None:
    requirements = _requirements_versions()
    registry = {
        behavior.distribution_name: behavior
        for behavior in retry_policy.DEPENDENCY_RETRY_BEHAVIORS
    }

    assert registry["stripe"].installed_version == requirements["stripe"] == "15.1.0"
    assert registry["firebase-admin"].installed_version == (
        requirements["firebase-admin"]
    ) == "7.4.0"
    assert registry["botocore"].installed_version == requirements["botocore"] == "1.35.99"
    assert registry["SQLAlchemy"].installed_version == requirements["SQLAlchemy"] == "2.0.49"

    for behavior in registry.values():
        assert "WS02-04C2" in behavior.reassessment_trigger
        assert behavior.approved_retry_attempts is None
        assert behavior.approved_backoff_seconds is None


@pytest.mark.requirement("WS02-04C2-R2")
def test_pickup_lane_does_not_source_configure_retry_counts_or_backoff() -> None:
    forbidden_fragments = {
        "max_network_retries",
        "retries={",
        "retry_mode",
        "total_max_attempts",
        "backoff",
        "jitter",
    }
    hits: list[str] = []

    for path in _production_sources():
        relative = path.relative_to(_REPO_ROOT).as_posix()
        source = path.read_text()
        if relative == "backend/services/provider_retry_policy.py":
            continue
        for fragment in forbidden_fragments:
            if fragment in source:
                hits.append(f"{relative}: {fragment}")

    assert hits == []


@pytest.mark.requirement("WS02-04C2-R1", "WS02-04C2-R2")
def test_no_generic_retry_decorator_or_framework_is_introduced() -> None:
    generic_retry_hits: list[str] = []

    for path in _production_sources():
        source = path.read_text()
        relative = path.relative_to(_REPO_ROOT).as_posix()
        for fragment in (
            "import tenacity",
            "from tenacity",
            "import backoff",
            "from backoff",
            "import retrying",
            "from retrying",
            "@retry",
            "retry_with_backoff",
            "generic_retry",
        ):
            if fragment in source:
                generic_retry_hits.append(f"{relative}: {fragment}")

    assert generic_retry_hits == []
