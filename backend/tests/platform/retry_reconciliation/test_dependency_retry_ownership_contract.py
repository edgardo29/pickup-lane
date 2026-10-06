from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"


def _production_sources() -> tuple[Path, ...]:
    return tuple(
        path
        for path in _BACKEND_ROOT.rglob("*.py")
        if "tests" not in path.relative_to(_BACKEND_ROOT).parts
        and ".venv" not in path.relative_to(_BACKEND_ROOT).parts
        and "__pycache__" not in path.relative_to(_BACKEND_ROOT).parts
        and "alembic" not in path.relative_to(_BACKEND_ROOT).parts
    )


@pytest.mark.pass_provenance('WS02-04C2')
def test_pickup_lane_does_not_source_configure_retry_counts_or_backoff() -> None:
    forbidden_fragments = {
        "max_network_retries",
        "retries={",
        "retry_mode",
        "backoff",
        "jitter",
    }
    hits: list[str] = []

    for path in _production_sources():
        relative = path.relative_to(_REPO_ROOT).as_posix()
        source = path.read_text()
        for fragment in forbidden_fragments:
            if fragment in source:
                hits.append(f"{relative}: {fragment}")

    assert hits == []


@pytest.mark.pass_provenance('WS02-04C2')
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
