from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

import pytest

import backend.settings as settings_module
from backend.settings import SettingsError, build_settings

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
_PLATFORM_ENV = "PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES"
_STRIPE_ENV = "STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES"


def _settings_env(**overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": "test",
        "DATABASE_URL": _TEST_DATABASE_URL,
        "INBOX_TOKEN_SECRET": "synthetic-independent-request-limit-token",
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


def _assert_rejected(name: str, value: str) -> str:
    with pytest.raises(SettingsError) as exc_info:
        _build(_settings_env(**{name: value}))
    message = str(exc_info.value)
    assert name in message
    return message


@pytest.mark.requirement("WS02-04B2A1-R6")
def test_b2a1_request_body_limit_defaults_are_approved_values() -> None:
    settings = _build(_settings_env())

    assert settings.platform_notice_request_body_limit_bytes == 163_840
    assert settings.stripe_webhook_request_body_limit_bytes == 65_536


@pytest.mark.requirement("WS02-04B2A1-R6")
@pytest.mark.parametrize(
    ("name", "attribute", "value"),
    [
        (_PLATFORM_ENV, "platform_notice_request_body_limit_bytes", "8192"),
        (_STRIPE_ENV, "stripe_webhook_request_body_limit_bytes", "4096"),
    ],
)
def test_b2a1_request_body_limit_custom_positive_integer_is_accepted(
    name: str,
    attribute: str,
    value: str,
) -> None:
    settings = _build(_settings_env(**{name: value}))

    assert getattr(settings, attribute) == int(value)


@pytest.mark.requirement("WS02-04B2A1-R6")
@pytest.mark.parametrize("name", [_PLATFORM_ENV, _STRIPE_ENV])
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", "must be greater than zero"),
        ("-1", "must be greater than zero"),
        ("not-an-int", "must be an integer"),
    ],
)
def test_b2a1_request_body_limit_invalid_values_are_rejected(
    name: str,
    value: str,
    expected: str,
) -> None:
    message = _assert_rejected(name, value)

    assert expected in message


@pytest.mark.requirement("WS02-04B2A1-R6")
def test_b2a1_environment_variable_names_are_registered_and_documented() -> None:
    env_names = settings_module.BACKEND_ENVIRONMENT_VARIABLES
    example = (_REPO_ROOT / "backend" / ".env.example").read_text()

    assert _PLATFORM_ENV in env_names
    assert _STRIPE_ENV in env_names
    assert "PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES=163840" in example
    assert "STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES=65536" in example


@pytest.mark.requirement("WS02-04B2A1-R6", "WS02-04B2A1-R7")
def test_b2a1_settings_are_distinct_from_ordinary_json_configuration() -> None:
    settings = _build(
        _settings_env(
            PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES="1000",
            STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES="2000",
            ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES="3000",
        )
    )

    assert settings.platform_notice_request_body_limit_bytes == 1000
    assert settings.stripe_webhook_request_body_limit_bytes == 2000
    assert settings.ordinary_json_request_body_limit_bytes == 3000


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


def _string_literals(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


@pytest.mark.requirement("WS02-04B2A1-R6", "WS02-04B2A1-R7")
def test_no_duplicate_b2a1_environment_owner_exists_outside_settings_module() -> None:
    owners: dict[str, list[str]] = {_PLATFORM_ENV: [], _STRIPE_ENV: []}
    for path in _production_python_files():
        literals = _string_literals(path)
        for env_name in owners:
            if env_name in literals:
                owners[env_name].append(str(path.relative_to(_REPO_ROOT)))

    assert owners == {
        _PLATFORM_ENV: ["backend/settings.py"],
        _STRIPE_ENV: ["backend/settings.py"],
    }
