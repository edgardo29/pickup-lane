from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.suite_type("ordinary"),
]

REPO_ROOT = Path(__file__).resolve().parents[4]
UTC = timezone.utc
NOW = datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC)
WINDOW = timedelta(minutes=5)

ALLOWED_FRESHNESS_SOURCE_PATHS = {
    "backend/services/auth_service.py",
    "backend/settings.py",
    "backend/services/recent_auth_policy.py",
}


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _identity(authenticated_at: datetime | None):
    from backend.services.auth_service import VerifiedFirebaseIdentity

    return VerifiedFirebaseIdentity(
        auth_user_id="synthetic-auth-user",
        email="recent-auth@example.invalid",
        email_verified=True,
        authenticated_at=authenticated_at,
    )


def _application_source_files() -> list[Path]:
    roots = [
        REPO_ROOT / "backend/alembic/versions",
        REPO_ROOT / "backend/models",
        REPO_ROOT / "backend/routes",
        REPO_ROOT / "backend/schemas",
        REPO_ROOT / "backend/services",
        REPO_ROOT / "backend/settings.py",
        REPO_ROOT / "frontend/src",
    ]
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
            continue
        for path in root.rglob("*"):
            if (
                path.is_file()
                and path.suffix in {".py", ".js", ".jsx", ".ts", ".tsx"}
                and "__pycache__" not in path.parts
            ):
                files.append(path)
    return sorted(files)


def _function_source(module_path: str, function_name: str) -> str:
    module = ast.parse(_read(module_path), filename=module_path)
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            lines = _read(module_path).splitlines()
            return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    raise AssertionError(f"{function_name} not found in {module_path}")


@pytest.mark.requirement("WS03-03A-R1")
@pytest.mark.parametrize("claim_value", [int(NOW.timestamp()), float(NOW.timestamp())])
def test_provider_auth_time_numeric_claim_parses_as_provider_utc_time(
    claim_value: int | float,
) -> None:
    from backend.services.auth_service import parse_provider_authenticated_at

    parsed = parse_provider_authenticated_at({"auth_time": claim_value})

    assert parsed == datetime.fromtimestamp(claim_value, tz=UTC)
    assert parsed.tzinfo is UTC


@pytest.mark.requirement("WS03-03A-R1", "WS03-03A-R2")
@pytest.mark.parametrize(
    "claims",
    [
        {},
        {"auth_time": True},
        {"auth_time": False},
        {"auth_time": "recent"},
        {"auth_time": None},
        {"auth_time": float("nan")},
        {"auth_time": float("inf")},
        {"auth_time": -1},
        {"auth_time": 10**100},
        {"auth_time": []},
    ],
)
def test_missing_or_malformed_provider_auth_time_is_unusable(claims: dict) -> None:
    from backend.services.auth_service import (
        is_recent_authentication,
        parse_provider_authenticated_at,
    )

    parsed = parse_provider_authenticated_at(claims)

    assert parsed is None
    assert not is_recent_authentication(
        _identity(parsed),
        now=NOW,
        window=WINDOW,
    )


@pytest.mark.requirement("WS03-03A-R1", "WS03-03A-R2")
@pytest.mark.parametrize(
    ("authenticated_at", "expected"),
    [
        (NOW, True),
        (NOW - WINDOW + timedelta(seconds=1), True),
        (NOW - WINDOW, True),
        (NOW - WINDOW - timedelta(seconds=1), False),
        (NOW + timedelta(seconds=1), False),
        ((NOW - timedelta(seconds=30)).replace(tzinfo=None), False),
        (
            (NOW - timedelta(seconds=30)).astimezone(timezone(timedelta(hours=-5))),
            True,
        ),
    ],
)
def test_recent_authentication_uses_inclusive_five_minute_utc_boundary(
    authenticated_at: datetime,
    expected: bool,
) -> None:
    from backend.services.auth_service import is_recent_authentication

    assert (
        is_recent_authentication(
            _identity(authenticated_at),
            now=NOW,
            window=WINDOW,
        )
        is expected
    )


@pytest.mark.requirement("WS03-03A-R1", "WS03-03A-R2")
def test_token_issue_time_is_not_recent_authentication_fallback() -> None:
    from backend.services.auth_service import (
        is_recent_authentication,
        parse_provider_authenticated_at,
    )

    fresh_issue_time = int(NOW.timestamp())
    stale_auth_time = int((NOW - WINDOW - timedelta(seconds=1)).timestamp())

    missing_auth_time = parse_provider_authenticated_at({"iat": fresh_issue_time})
    stale_provider_time = parse_provider_authenticated_at(
        {"iat": fresh_issue_time, "auth_time": stale_auth_time}
    )

    assert missing_auth_time is None
    assert stale_provider_time == datetime.fromtimestamp(stale_auth_time, tz=UTC)
    assert not is_recent_authentication(
        _identity(missing_auth_time),
        now=NOW,
        window=WINDOW,
    )
    assert not is_recent_authentication(
        _identity(stale_provider_time),
        now=NOW,
        window=WINDOW,
    )

    parser_source = _function_source(
        "backend/services/auth_service.py",
        "parse_provider_authenticated_at",
    )
    assert 'decoded_token.get("auth_time")' in parser_source
    assert "iat" not in parser_source


@pytest.mark.requirement("WS03-03A-R2")
def test_recent_authentication_window_is_owned_by_typed_backend_settings() -> None:
    import backend.services.auth_service as auth_service
    from backend.settings import (
        BackendSettings,
        DEFAULT_RECENT_AUTHENTICATION_WINDOW_SECONDS,
    )

    assert DEFAULT_RECENT_AUTHENTICATION_WINDOW_SECONDS == 5 * 60
    assert (
        BackendSettings.model_fields["recent_authentication_window_seconds"].default
        == DEFAULT_RECENT_AUTHENTICATION_WINDOW_SECONDS
    )
    assert auth_service.recent_authentication_window() == WINDOW

    auth_service_source = _read("backend/services/auth_service.py")
    settings_source = _read("backend/settings.py")

    assert (
        "timedelta(seconds=get_settings().recent_authentication_window_seconds)"
        in auth_service_source
    )
    assert settings_source.count("DEFAULT_RECENT_AUTHENTICATION_WINDOW_SECONDS") == 2

    duplicate_assignment_owners: list[str] = []
    for path in _application_source_files():
        if path.suffix != ".py":
            continue
        relative_path = _relative(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative_path)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = list(node.targets) if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and "RECENT_AUTH" in target.id and "WINDOW" in target.id:
                    duplicate_assignment_owners.append(f"{relative_path}:{target.id}")

    assert duplicate_assignment_owners == [
        "backend/settings.py:DEFAULT_RECENT_AUTHENTICATION_WINDOW_SECONDS"
    ]


@pytest.mark.requirement("WS03-03A-R1", "WS03-03A-R10")
def test_verified_identity_carries_provider_freshness_only_as_request_scoped_data() -> None:
    from backend.services.auth_service import VerifiedFirebaseIdentity

    fields = set(VerifiedFirebaseIdentity.__dataclass_fields__)

    assert fields == {
        "auth_user_id",
        "email",
        "email_verified",
        "authenticated_at",
        "provider_account_active",
    }
    assert VerifiedFirebaseIdentity.__dataclass_params__.frozen is True

    auth_source = _read("backend/services/auth_service.py")
    assert "authenticated_at=parse_provider_authenticated_at(decoded_token)" in auth_source
    assert "authenticated_at:" in auth_source


@pytest.mark.requirement("WS03-03A-R1", "WS03-03A-R10")
def test_application_source_has_no_app_owned_recent_auth_freshness_authority() -> None:
    disallowed_occurrences: list[str] = []
    disallowed_storage_freshness: list[str] = []
    forbidden_source_terms = (
        "recent_auth_at",
        "recently_authenticated",
        "reauthenticated_at",
        "step_up_at",
        "step_up_token",
        "fresh_auth",
        "auth_fresh",
    )
    storage_terms = ("localStorage", "sessionStorage", "indexedDB", "document.cookie")
    freshness_terms = ("auth_time", "authenticated_at", "recentAuth", "recent_auth", "stepUp")

    for path in _application_source_files():
        relative_path = _relative(path)
        source = path.read_text(encoding="utf-8")
        lower_source = source.lower()
        if relative_path not in ALLOWED_FRESHNESS_SOURCE_PATHS:
            for term in ("auth_time", "authenticated_at"):
                if term in source:
                    disallowed_occurrences.append(f"{relative_path}:{term}")
        for term in forbidden_source_terms:
            if term in lower_source and relative_path not in ALLOWED_FRESHNESS_SOURCE_PATHS:
                disallowed_occurrences.append(f"{relative_path}:{term}")
        for line_number, line in enumerate(source.splitlines(), start=1):
            if any(storage in line for storage in storage_terms) and any(
                term in line for term in freshness_terms
            ):
                disallowed_storage_freshness.append(f"{relative_path}:{line_number}")

    assert disallowed_occurrences == []
    assert disallowed_storage_freshness == []
