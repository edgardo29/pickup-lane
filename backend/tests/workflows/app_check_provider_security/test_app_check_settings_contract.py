from __future__ import annotations

from pathlib import Path

import pytest

from backend.settings import (
    BACKEND_ENVIRONMENT_VARIABLES,
    FirebaseAppCheckMode,
    SettingsError,
    build_settings,
)

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

REPO_ROOT = Path(__file__).resolve().parents[4]
TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
PRODUCTION_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_prod"
FIREBASE_ADMIN_JSON = '{"type":"service_account","project_id":"pickup-lane-synthetic"}'
SYNTHETIC_APP_ID = "1:123456789:web:syntheticapp"


def _settings_env(app_env: str, **overrides: str | None) -> dict[str, str]:
    database_url = TEST_DATABASE_URL if app_env in {"test", "ci"} else PRODUCTION_DATABASE_URL
    env = {
        "APP_ENV": app_env,
        "DATABASE_URL": database_url,
        "INBOX_TOKEN_SECRET": "synthetic-independent-app-check-token",
        "ALLOWED_HOSTS": "api.example.invalid",
        "CORS_ALLOWED_ORIGINS": "https://app.example.invalid",
        "ENABLE_API_DOCS": "false",
        "ENABLE_DB_HEALTH": "false",
        "FIREBASE_ADMIN_CREDENTIALS_JSON": FIREBASE_ADMIN_JSON,
        "FIREBASE_PROJECT_ID": "pickup-lane-synthetic",
        "ENABLE_STRIPE_PAYMENTS": "false",
        "R2_ACCOUNT_ID": "synthetic-r2-account",
        "R2_ACCESS_KEY_ID": "synthetic-r2-access-key-id",
        "R2_SECRET_ACCESS_KEY": "synthetic-r2-secret-access-key",
        "R2_BUCKET_NAME": "pickup-lane-synthetic-bucket",
        "R2_ENDPOINT_URL": "https://synthetic-r2-account.r2.cloudflarestorage.com",
    }
    if app_env in {"preview", "staging", "production"}:
        env.update(DB_POOL_SIZE="5", DB_MAX_OVERFLOW="2")
        env["FIREBASE_APP_CHECK_MODE"] = "disabled"
    for name, value in overrides.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def _build(env: dict[str, str]):
    return build_settings(env, load_dotenv_file=False, validate_full=True)


def _assert_rejected(
    env: dict[str, str],
    *,
    mentions: tuple[str, ...],
    does_not_echo: tuple[str, ...] = (),
) -> None:
    with pytest.raises(SettingsError) as exc_info:
        _build(env)
    message = str(exc_info.value)
    for fragment in mentions:
        assert fragment in message
    for value in does_not_echo:
        assert value not in message


@pytest.mark.requirement("WS03-03B-R1", "WS03-03B-R7")
@pytest.mark.parametrize("app_env", ["local", "test", "ci"])
def test_local_test_and_ci_default_app_check_to_disabled_without_app_id(
    app_env: str,
) -> None:
    settings = _build(_settings_env(app_env))

    assert settings.firebase_app_check_mode is FirebaseAppCheckMode.DISABLED
    assert settings.firebase_app_check_app_id is None


@pytest.mark.requirement("WS03-03B-R1", "WS03-03B-R6")
@pytest.mark.parametrize("app_env", ["preview", "staging", "production"])
def test_production_like_environments_require_explicit_app_check_mode(
    app_env: str,
) -> None:
    _assert_rejected(
        _settings_env(app_env, FIREBASE_APP_CHECK_MODE=None),
        mentions=("FIREBASE_APP_CHECK_MODE", "explicit"),
    )


@pytest.mark.requirement("WS03-03B-R1")
def test_explicit_disabled_mode_may_omit_supported_web_app_id() -> None:
    settings = _build(
        _settings_env(
            "production",
            FIREBASE_APP_CHECK_MODE="disabled",
            FIREBASE_APP_CHECK_APP_ID=None,
        )
    )

    assert settings.firebase_app_check_mode is FirebaseAppCheckMode.DISABLED
    assert settings.firebase_app_check_app_id is None


@pytest.mark.requirement("WS03-03B-R1", "WS03-03B-R7")
@pytest.mark.parametrize("raw_mode", ["observe", "enforced"])
def test_observe_and_enforced_modes_require_non_blank_supported_web_app_id(
    raw_mode: str,
) -> None:
    _assert_rejected(
        _settings_env(
            "test",
            FIREBASE_APP_CHECK_MODE=raw_mode,
            FIREBASE_APP_CHECK_APP_ID=None,
        ),
        mentions=("FIREBASE_APP_CHECK_APP_ID", "required"),
    )


@pytest.mark.requirement("WS03-03B-R1")
@pytest.mark.parametrize(
    ("raw_mode", "expected"),
    [
        (" observe ", FirebaseAppCheckMode.OBSERVE),
        ("ENFORCED", FirebaseAppCheckMode.ENFORCED),
    ],
)
def test_observe_and_enforced_modes_accept_configured_supported_web_app_id(
    raw_mode: str,
    expected: FirebaseAppCheckMode,
) -> None:
    settings = _build(
        _settings_env(
            "test",
            FIREBASE_APP_CHECK_MODE=raw_mode,
            FIREBASE_APP_CHECK_APP_ID=SYNTHETIC_APP_ID,
        )
    )

    assert settings.firebase_app_check_mode is expected
    assert settings.firebase_app_check_app_id == SYNTHETIC_APP_ID


@pytest.mark.requirement("WS03-03B-R1", "WS03-03B-R7")
@pytest.mark.parametrize("raw_mode", ["", "audit", "required", "true"])
def test_unknown_or_blank_app_check_modes_fail_safely(raw_mode: str) -> None:
    _assert_rejected(
        _settings_env("test", FIREBASE_APP_CHECK_MODE=raw_mode),
        mentions=("FIREBASE_APP_CHECK_MODE",),
    )


@pytest.mark.requirement("WS03-03B-R1", "WS03-03B-R6", "WS03-03B-R7")
def test_supported_web_app_id_is_separate_from_firebase_project_id() -> None:
    _assert_rejected(
        _settings_env(
            "test",
            FIREBASE_APP_CHECK_MODE="observe",
            FIREBASE_APP_CHECK_APP_ID="pickup-lane-synthetic",
        ),
        mentions=("FIREBASE_APP_CHECK_APP_ID", "FIREBASE_PROJECT_ID"),
    )


@pytest.mark.requirement("WS03-03B-R1", "WS03-03B-R7")
def test_production_like_app_check_app_id_rejects_documented_placeholder_without_echo() -> None:
    placeholder = "replace-with-firebase-app-check-app-id"

    _assert_rejected(
        _settings_env(
            "production",
            FIREBASE_APP_CHECK_MODE="observe",
            FIREBASE_APP_CHECK_APP_ID=placeholder,
        ),
        mentions=("FIREBASE_APP_CHECK_APP_ID", "placeholder"),
        does_not_echo=(placeholder,),
    )


@pytest.mark.requirement("WS03-03B-R1", "WS03-03B-R2", "WS03-03B-R7")
def test_app_check_environment_names_are_finite_and_synthetic_examples_only() -> None:
    backend_example = (REPO_ROOT / "backend/.env.example").read_text()
    frontend_example = (REPO_ROOT / "frontend/.env.example").read_text()

    assert "FIREBASE_APP_CHECK_MODE" in BACKEND_ENVIRONMENT_VARIABLES
    assert "FIREBASE_APP_CHECK_APP_ID" in BACKEND_ENVIRONMENT_VARIABLES
    assert "FIREBASE_APP_CHECK_MODE=disabled" in backend_example
    assert "FIREBASE_APP_CHECK_APP_ID=replace-with-firebase-app-check-app-id" in backend_example
    assert "VITE_FIREBASE_APP_CHECK_MODE=disabled" in frontend_example
    assert "VITE_FIREBASE_APP_CHECK_RECAPTCHA_ENTERPRISE_SITE_KEY=" in frontend_example
    assert "VITE_FIREBASE_APP_CHECK_APP_ID" not in frontend_example
    assert SYNTHETIC_APP_ID not in backend_example
