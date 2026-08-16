from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_PRODUCTION_ROOTS = (
    _BACKEND_ROOT / "routes",
    _BACKEND_ROOT / "services",
    _BACKEND_ROOT / "main.py",
    _BACKEND_ROOT / "settings.py",
    _BACKEND_ROOT / "scripts",
)
_CHAT_RATE_OWNER_PATHS = {
    "backend/services/chat_rate_limit_service.py",
    "backend/services/game_chat_service.py",
    "backend/services/sub_post_chat_service.py",
}
_CHAT_RATE_ERROR_OWNER = {"backend/services/chat_rate_limit_service.py"}


def _production_python_files() -> tuple[Path, ...]:
    files: list[Path] = []
    for root in _PRODUCTION_ROOTS:
        if root.is_file():
            candidates = [root]
        else:
            candidates = list(root.rglob("*.py"))
        for path in candidates:
            relative_parts = path.relative_to(_BACKEND_ROOT).parts
            if "legacy" in relative_parts or "__pycache__" in relative_parts:
                continue
            files.append(path)
    return tuple(sorted(set(files)))


def _relative(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _literal_hits(literal: str) -> dict[str, list[int]]:
    hits: dict[str, list[int]] = {}
    for path in _production_python_files():
        lines = [
            index
            for index, line in enumerate(path.read_text().splitlines(), start=1)
            if literal in line
        ]
        if lines:
            hits[_relative(path)] = lines
    return hits


def _regex_hits(pattern: str) -> dict[str, list[str]]:
    regex = re.compile(pattern, flags=re.IGNORECASE)
    hits: dict[str, list[str]] = {}
    for path in _production_python_files():
        text = path.read_text()
        matches = sorted({match.group(0) for match in regex.finditer(text)})
        if matches:
            hits[_relative(path)] = matches
    return hits


@pytest.mark.requirement("WS02-04C3B-R6")
def test_c3a_chat_is_the_only_current_source_owned_rate_limit_owner() -> None:
    assert set(_literal_hits("CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES")) == {
        "backend/services/chat_rate_limit_service.py",
        "backend/services/game_chat_service.py",
        "backend/services/sub_post_chat_service.py",
    }
    assert set(_literal_hits("enforce_visible_text_chat_rate_limit")) == (
        _CHAT_RATE_OWNER_PATHS
    )
    assert set(_literal_hits("CHAT_RATE_LIMIT_WINDOW_SECONDS")) == {
        "backend/services/chat_rate_limit_service.py"
    }


@pytest.mark.requirement("WS02-04C3B-R6")
def test_no_alternate_non_chat_api_rate_limited_or_rate_limit_retry_after_producer() -> None:
    assert set(_literal_hits("API.RATE_LIMITED")) == _CHAT_RATE_ERROR_OWNER
    assert set(_literal_hits("HTTP_429_TOO_MANY_REQUESTS")) == _CHAT_RATE_ERROR_OWNER

    retry_after_hits = _literal_hits("Retry-After")
    assert _CHAT_RATE_ERROR_OWNER <= set(retry_after_hits)

    # Future unrelated HTTP Retry-After semantics are not forbidden by C3B, but
    # a non-chat RATE-LIMIT Retry-After producer would be a C3B drift.
    rate_limit_signals = (
        "api.rate_limited",
        "rate-limit",
        "rate_limit",
        "rate limited",
        "too_many_requests",
        "too many requests",
        "http_429",
        "429",
    )
    for path in _production_python_files():
        relative = _relative(path)
        if relative in _CHAT_RATE_ERROR_OWNER:
            continue
        text = path.read_text()
        for match in re.finditer("Retry-After", text):
            context = text[max(match.start() - 300, 0) : match.end() + 300].lower()
            for signal in rate_limit_signals:
                assert signal not in context


@pytest.mark.requirement("WS02-04C3B-R5", "WS02-04C3B-R6")
def test_no_generic_non_chat_rate_limiter_middleware_or_provider_cost_counter() -> None:
    main_source = (_BACKEND_ROOT / "main.py").read_text()
    settings_source = (_BACKEND_ROOT / "settings.py").read_text()
    backend_source = "\n".join(path.read_text() for path in _production_python_files())

    assert "RateLimitMiddleware" not in main_source
    assert "SlowAPIMiddleware" not in main_source
    assert "PROVIDER_COST_RATE" not in settings_source
    assert "NON_CHAT_RATE" not in settings_source
    assert "GENERIC_RATE_LIMIT" not in settings_source
    assert not _regex_hits(r"\bimport redis\b|\bfrom redis\b|slowapi|limits\.storage")
    assert not _regex_hits(r"provider[_-]?cost.{0,80}(counter|limiter|rate[_-]?limit)")
    assert not _regex_hits(r"(counter|limiter|rate[_-]?limit).{0,80}provider[_-]?cost")
    assert "provider_cost_rate_limits" not in backend_source


@pytest.mark.requirement("WS02-04C3B-R4", "WS02-04C3B-R6")
def test_existing_product_limits_are_not_reclassified_as_c3b_rate_controls() -> None:
    c3b_plan = (
        _REPO_ROOT
        / "docs/production-readiness/planning/ws02-04c3b-provider-cost-rate-limit-deferral.md"
    ).read_text()
    source_owned_closeout = (
        _REPO_ROOT
        / "docs/production-readiness/planning/ws02-04-source-owned-closeout.md"
    ).read_text()

    assert "product collection caps" in c3b_plan
    assert "These are not adequate numeric authority by themselves" in c3b_plan
    assert "Provider-cost action rates" in source_owned_closeout
    assert "authenticated non-chat throttles" in source_owned_closeout
    assert "remain open or evidence-deferred" in source_owned_closeout
