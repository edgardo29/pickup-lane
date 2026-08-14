from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

import backend.settings as settings_module
from backend.settings import SettingsError, build_settings

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_FRONTEND_ROOT = _REPO_ROOT / "frontend"
_TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"

_TIMEOUT_ENV = {
    "STRIPE_READ_TIMEOUT_SECONDS": ("stripe_read_timeout_seconds", 6),
    "STRIPE_MUTATION_TIMEOUT_SECONDS": ("stripe_mutation_timeout_seconds", 15),
    "FIREBASE_HTTP_TIMEOUT_SECONDS": ("firebase_http_timeout_seconds", 8),
    "R2_METADATA_CONNECT_TIMEOUT_SECONDS": (
        "r2_metadata_connect_timeout_seconds",
        2,
    ),
    "R2_METADATA_READ_TIMEOUT_SECONDS": ("r2_metadata_read_timeout_seconds", 6),
    "DB_POOL_WAIT_TIMEOUT_SECONDS": ("db_pool_wait_timeout_seconds", 2),
    "DB_STATEMENT_TIMEOUT_MILLISECONDS": (
        "db_statement_timeout_milliseconds",
        12_000,
    ),
    "DB_LOCK_TIMEOUT_MILLISECONDS": ("db_lock_timeout_milliseconds", 2_000),
}
_FRONTEND_IGNORED_PARTS = frozenset(
    {"node_modules", "dist", "build", ".vite", "coverage"}
)
_FRONTEND_TEXT_SUFFIXES = frozenset(
    {".css", ".env", ".example", ".html", ".js", ".json", ".jsx", ".md", ".ts", ".tsx"}
)


def _settings_env(**overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": "test",
        "DATABASE_URL": _TEST_DATABASE_URL,
        "INBOX_TOKEN_SECRET": "synthetic-independent-timeout-token",
        "ALLOWED_HOSTS": "testserver,api.example.invalid",
        "CORS_ALLOWED_ORIGINS": "https://app.example.invalid",
        "ENABLE_API_DOCS": "false",
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


def _production_python_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in _BACKEND_ROOT.rglob("*.py")
            if "tests" not in path.relative_to(_BACKEND_ROOT).parts
            and ".venv" not in path.relative_to(_BACKEND_ROOT).parts
            and "__pycache__" not in path.relative_to(_BACKEND_ROOT).parts
        )
    )


def _frontend_text_files() -> tuple[Path, ...]:
    if not _FRONTEND_ROOT.exists():
        return ()
    return tuple(
        sorted(
            path
            for path in _FRONTEND_ROOT.rglob("*")
            if path.is_file()
            and not any(part in _FRONTEND_IGNORED_PARTS for part in path.parts)
            and path.suffix in _FRONTEND_TEXT_SUFFIXES
        )
    )


@pytest.mark.requirement("WS02-04C1-R1")
def test_c1_timeout_defaults_are_the_approved_values() -> None:
    settings = _build(_settings_env())

    for attribute, expected in _TIMEOUT_ENV.values():
        assert getattr(settings, attribute) == expected


@pytest.mark.requirement("WS02-04C1-R1")
@pytest.mark.parametrize(
    ("name", "attribute", "value", "extra"),
    [
        ("STRIPE_READ_TIMEOUT_SECONDS", "stripe_read_timeout_seconds", "9", {}),
        ("STRIPE_MUTATION_TIMEOUT_SECONDS", "stripe_mutation_timeout_seconds", "9", {}),
        ("FIREBASE_HTTP_TIMEOUT_SECONDS", "firebase_http_timeout_seconds", "9", {}),
        ("R2_METADATA_CONNECT_TIMEOUT_SECONDS", "r2_metadata_connect_timeout_seconds", "9", {}),
        ("R2_METADATA_READ_TIMEOUT_SECONDS", "r2_metadata_read_timeout_seconds", "9", {}),
        ("DB_POOL_WAIT_TIMEOUT_SECONDS", "db_pool_wait_timeout_seconds", "9", {}),
        (
            "DB_STATEMENT_TIMEOUT_MILLISECONDS",
            "db_statement_timeout_milliseconds",
            "3000",
            {},
        ),
        ("DB_LOCK_TIMEOUT_MILLISECONDS", "db_lock_timeout_milliseconds", "1000", {}),
    ],
)
def test_c1_timeout_positive_overrides_are_accepted(
    name: str,
    attribute: str,
    value: str,
    extra: Mapping[str, str],
) -> None:
    settings = _build(_settings_env(**{name: value}, **extra))

    assert getattr(settings, attribute) == int(value)


@pytest.mark.requirement("WS02-04C1-R1")
@pytest.mark.parametrize("name", list(_TIMEOUT_ENV))
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", "must be greater than zero"),
        ("-1", "must be greater than zero"),
        ("not-an-int", "must be an integer"),
    ],
)
def test_c1_timeout_invalid_values_are_rejected(
    name: str,
    value: str,
    expected: str,
) -> None:
    with pytest.raises(SettingsError) as exc_info:
        _build(_settings_env(**{name: value}))

    message = str(exc_info.value)
    assert name in message
    assert expected in message


@pytest.mark.requirement("WS02-04C1-R1")
def test_c1_database_lock_timeout_must_remain_lower_than_statement_timeout() -> None:
    with pytest.raises(SettingsError) as exc_info:
        _build(
            _settings_env(
                DB_STATEMENT_TIMEOUT_MILLISECONDS="2000",
                DB_LOCK_TIMEOUT_MILLISECONDS="2000",
            )
        )

    assert "DB_LOCK_TIMEOUT_MILLISECONDS" in str(exc_info.value)
    assert "must be less than DB_STATEMENT_TIMEOUT_MILLISECONDS" in str(exc_info.value)


@pytest.mark.requirement("WS02-04C1-R1")
def test_c1_timeout_environment_names_are_registered_and_documented() -> None:
    env_names = settings_module.BACKEND_ENVIRONMENT_VARIABLES
    example = (_REPO_ROOT / "backend" / ".env.example").read_text()

    for name, (_, expected) in _TIMEOUT_ENV.items():
        assert name in env_names
        assert f"{name}={expected}" in example


@pytest.mark.requirement("WS02-04C1-R1")
def test_c1_timeout_environment_names_have_single_backend_settings_owner() -> None:
    production_hits: dict[str, list[str]] = {}
    for name in _TIMEOUT_ENV:
        hits: list[str] = []
        for path in _production_python_files():
            if name in path.read_text():
                hits.append(str(path.relative_to(_REPO_ROOT)))
        production_hits[name] = hits

    assert production_hits == {
        name: ["backend/settings.py"] for name in _TIMEOUT_ENV
    }


@pytest.mark.requirement("WS02-04C1-R1")
def test_c1_timeout_environment_names_are_backend_only_configuration() -> None:
    frontend_hits: dict[str, list[str]] = {}
    for name in _TIMEOUT_ENV:
        hits = [
            str(path.relative_to(_REPO_ROOT))
            for path in _frontend_text_files()
            if name in path.read_text(errors="ignore")
        ]
        if hits:
            frontend_hits[name] = hits

    assert frontend_hits == {}
