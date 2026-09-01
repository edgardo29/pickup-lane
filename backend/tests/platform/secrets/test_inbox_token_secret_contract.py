from __future__ import annotations

import pytest

from backend.settings import AppEnvironment, SettingsError, build_settings, get_inbox_token_secret

pytestmark = pytest.mark.no_db_cleanup

_DATABASE_USER = "synthetic_app"
_DATABASE_PASSWORD = "not-a-real-password"
_DATABASE_HOST = "db.example.invalid"
_DATABASE_NAME = "pickup_lane_prod"
_PRODUCTION_DATABASE_URL = (
    "postgresql+psycopg://"
    f"{_DATABASE_USER}:{_DATABASE_PASSWORD}@{_DATABASE_HOST}:5432/{_DATABASE_NAME}"
)
_FIREBASE_ADMIN_JSON = '{"type":"service_account","project_id":"pickup-lane-synthetic"}'
_INDEPENDENT_INBOX_SECRET = "synthetic-independent-inbox-token-secret"
_STRIPE_SECRET_KEY = "synthetic-stripe-secret-key"
_STRIPE_WEBHOOK_SECRET = "synthetic-stripe-webhook-secret"
_R2_ACCESS_KEY_ID = "synthetic-r2-access-key-id"
_R2_SECRET_ACCESS_KEY = "synthetic-r2-secret-access-key"


def _production_like_env(**overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": AppEnvironment.PRODUCTION.value,
        "DATABASE_URL": _PRODUCTION_DATABASE_URL,
        "ALLOWED_HOSTS": "api.example.invalid",
        "CORS_ALLOWED_ORIGINS": "https://app.example.invalid",
        "ENABLE_API_DOCS": "false",
        "DB_POOL_SIZE": "5",
        "DB_MAX_OVERFLOW": "2",
        "FIREBASE_ADMIN_CREDENTIALS_JSON": _FIREBASE_ADMIN_JSON,
        "FIREBASE_PROJECT_ID": "pickup-lane-synthetic",
        "FIREBASE_APP_CHECK_MODE": "disabled",
        "STRIPE_SECRET_KEY": _STRIPE_SECRET_KEY,
        "STRIPE_WEBHOOK_SECRET": _STRIPE_WEBHOOK_SECRET,
        "R2_ACCOUNT_ID": "synthetic-r2-account",
        "R2_ACCESS_KEY_ID": _R2_ACCESS_KEY_ID,
        "R2_SECRET_ACCESS_KEY": _R2_SECRET_ACCESS_KEY,
        "R2_BUCKET_NAME": "pickup-lane-synthetic-bucket",
        "R2_ENDPOINT_URL": "https://synthetic-r2-account.r2.cloudflarestorage.com",
        "INBOX_TOKEN_SECRET": _INDEPENDENT_INBOX_SECRET,
    }
    for name, value in overrides.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


@pytest.mark.requirement("EN03-INDEPENDENCE-001")
def test_production_like_settings_accept_independent_inbox_token_secret() -> None:
    settings = build_settings(
        _production_like_env(),
        load_dotenv_file=False,
        validate_full=True,
    )

    assert settings.app_env is AppEnvironment.PRODUCTION
    assert settings.inbox_token_secret_value == _INDEPENDENT_INBOX_SECRET
    assert get_inbox_token_secret(settings) == _INDEPENDENT_INBOX_SECRET


@pytest.mark.requirement("EN03-INDEPENDENCE-001")
def test_missing_production_like_inbox_token_secret_is_rejected_without_fallback() -> None:
    with pytest.raises(SettingsError) as exc_info:
        build_settings(
            _production_like_env(INBOX_TOKEN_SECRET=None),
            load_dotenv_file=False,
            validate_full=True,
        )

    message = str(exc_info.value)
    assert "INBOX_TOKEN_SECRET" in message
    assert "required" in message
    assert _PRODUCTION_DATABASE_URL not in message


@pytest.mark.requirement("EN03-INDEPENDENCE-001")
def test_documented_inbox_token_placeholder_is_rejected_without_echoing_value() -> None:
    placeholder = "replace-with-independent-secret"

    with pytest.raises(SettingsError) as exc_info:
        build_settings(
            _production_like_env(INBOX_TOKEN_SECRET=placeholder),
            load_dotenv_file=False,
            validate_full=True,
        )

    message = str(exc_info.value)
    assert "INBOX_TOKEN_SECRET" in message
    assert "placeholder" in message
    assert placeholder not in message


_CREDENTIAL_REUSE_CASES = (
    ("DATABASE_URL", _PRODUCTION_DATABASE_URL),
    ("FIREBASE_ADMIN_CREDENTIALS_JSON", _FIREBASE_ADMIN_JSON),
    ("STRIPE_SECRET_KEY", _STRIPE_SECRET_KEY),
    ("STRIPE_WEBHOOK_SECRET", _STRIPE_WEBHOOK_SECRET),
    ("R2_ACCESS_KEY_ID", _R2_ACCESS_KEY_ID),
    ("R2_SECRET_ACCESS_KEY", _R2_SECRET_ACCESS_KEY),
)


@pytest.mark.requirement("EN03-INDEPENDENCE-001")
@pytest.mark.parametrize(
    ("credential_name", "credential_value"),
    _CREDENTIAL_REUSE_CASES,
    ids=[name.lower() for name, _value in _CREDENTIAL_REUSE_CASES],
)
def test_inbox_token_secret_rejects_reuse_of_other_credentials_without_echoing_values(
    credential_name: str,
    credential_value: str,
) -> None:
    with pytest.raises(SettingsError) as exc_info:
        build_settings(
            _production_like_env(INBOX_TOKEN_SECRET=credential_value),
            load_dotenv_file=False,
            validate_full=True,
        )

    message = str(exc_info.value)
    assert "INBOX_TOKEN_SECRET" in message
    assert credential_name in message
    assert credential_value not in message


@pytest.mark.requirement("EN03-INDEPENDENCE-001")
def test_inbox_token_secret_rejects_reuse_of_firebase_admin_credentials_path_without_echoing_value(
    tmp_path,
) -> None:
    credential_file = tmp_path / "synthetic-firebase-admin.json"
    credential_file.write_text("{}", encoding="utf-8")
    credential_value = str(credential_file)

    with pytest.raises(SettingsError) as exc_info:
        build_settings(
            _production_like_env(
                FIREBASE_ADMIN_CREDENTIALS=credential_value,
                INBOX_TOKEN_SECRET=credential_value,
            ),
            load_dotenv_file=False,
            validate_full=True,
        )

    message = str(exc_info.value)
    assert "INBOX_TOKEN_SECRET" in message
    assert "FIREBASE_ADMIN_CREDENTIALS" in message
    assert credential_value not in message
