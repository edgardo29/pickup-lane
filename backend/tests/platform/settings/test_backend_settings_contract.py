from __future__ import annotations

import socket
from collections.abc import Mapping

import pytest

import backend.settings as settings_module
from backend.settings import (
    AppEnvironment,
    DEDICATED_TEST_DATABASE_NAME,
    DEFAULT_ALLOWED_HOSTS,
    DEFAULT_CORS_ORIGINS,
    SettingsError,
    build_settings,
)
from backend.tests.support.environment_safety import (
    EnvironmentSafetyError,
    NETWORK_BLOCKED_MESSAGE,
)

pytestmark = pytest.mark.no_db_cleanup

_PRODUCTION_DATABASE_NAME = "pickup_lane_prod"
_PRODUCTION_DATABASE_URL = (
    f"postgresql+psycopg://db.example.invalid:5432/{_PRODUCTION_DATABASE_NAME}"
)
_TEST_DATABASE_URL = (
    f"postgresql+psycopg://db.example.invalid:5432/{DEDICATED_TEST_DATABASE_NAME}"
)
_FIREBASE_ADMIN_JSON = '{"type":"service_account","project_id":"pickup-lane-synthetic"}'
_INBOX_SECRET = "synthetic-independent-inbox-token-secret"
_STRIPE_SECRET_KEY = "synthetic-stripe-secret-key"
_STRIPE_PUBLISHABLE_KEY = "synthetic-stripe-publishable-key"
_STRIPE_WEBHOOK_SECRET = "synthetic-stripe-webhook-secret"
_R2_ACCESS_KEY_ID = "synthetic-r2-access-key-id"
_R2_SECRET_ACCESS_KEY = "synthetic-r2-secret-access-key"


def _settings_env(app_env: str | None = "production", **overrides: str | None) -> dict[str, str]:
    database_url = _TEST_DATABASE_URL if app_env in {"test", "ci"} else _PRODUCTION_DATABASE_URL
    env = {
        "DATABASE_URL": database_url,
        "ALLOWED_HOSTS": "api.example.invalid",
        "CORS_ALLOWED_ORIGINS": "https://app.example.invalid",
        "ENABLE_API_DOCS": "false",
        "ENABLE_DB_HEALTH": "false",
        "DB_POOL_SIZE": "5",
        "DB_MAX_OVERFLOW": "2",
        "FIREBASE_ADMIN_CREDENTIALS_JSON": _FIREBASE_ADMIN_JSON,
        "FIREBASE_PROJECT_ID": "pickup-lane-synthetic",
        "FIREBASE_APP_CHECK_MODE": "disabled",
        "ENABLE_STRIPE_PAYMENTS": "false",
        "R2_ACCOUNT_ID": "synthetic-r2-account",
        "R2_ACCESS_KEY_ID": _R2_ACCESS_KEY_ID,
        "R2_SECRET_ACCESS_KEY": _R2_SECRET_ACCESS_KEY,
        "R2_BUCKET_NAME": "pickup-lane-synthetic-bucket",
        "R2_ENDPOINT_URL": "https://synthetic-r2-account.r2.cloudflarestorage.com",
        "INBOX_TOKEN_SECRET": _INBOX_SECRET,
    }
    if app_env is not None:
        env["APP_ENV"] = app_env
    for name, value in overrides.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def _build(env: Mapping[str, str]):
    return build_settings(env, load_dotenv_file=False, validate_full=True)


def _assert_rejected(
    env: Mapping[str, str],
    *,
    mentions: tuple[str, ...],
    does_not_echo: tuple[str, ...] = (),
) -> str:
    with pytest.raises(SettingsError) as exc_info:
        _build(env)

    message = str(exc_info.value)
    for fragment in mentions:
        assert fragment in message
    for private_value in does_not_echo:
        assert private_value not in message
    return message


@pytest.mark.requirement("WS02-01-R1", "WS02-01-R2")
@pytest.mark.parametrize(
    ("raw_app_env", "expected_env", "production_like"),
    [
        ("local", AppEnvironment.LOCAL, False),
        ("test", AppEnvironment.TEST, False),
        ("ci", AppEnvironment.CI, False),
        ("preview", AppEnvironment.PREVIEW, True),
        ("staging", AppEnvironment.STAGING, True),
        ("production", AppEnvironment.PRODUCTION, True),
    ],
)
def test_canonical_environment_identities_parse_and_classify(
    raw_app_env: str,
    expected_env: AppEnvironment,
    production_like: bool,
) -> None:
    settings = _build(_settings_env(raw_app_env))

    assert settings.app_env is expected_env
    assert settings.is_production_like is production_like


@pytest.mark.requirement("WS02-01-R2")
def test_environment_identity_defaulting_is_bounded_to_local_or_ci() -> None:
    local_settings = _build(_settings_env(None, DATABASE_URL=_PRODUCTION_DATABASE_URL))
    ci_settings = _build(_settings_env(None, CI="true", DATABASE_URL=_TEST_DATABASE_URL))

    assert local_settings.app_env is AppEnvironment.LOCAL
    assert ci_settings.app_env is AppEnvironment.CI


@pytest.mark.requirement("WS02-01-R2", "WS02-01-R3")
def test_deployed_runtime_markers_require_explicit_production_like_identity() -> None:
    _assert_rejected(
        _settings_env(None, RENDER="true"),
        mentions=("APP_ENV",),
    )


@pytest.mark.requirement("WS02-01-R2", "WS02-01-R3")
@pytest.mark.parametrize("raw_app_env", ["", "   ", "qa"])
def test_blank_or_unknown_environment_identity_is_rejected(raw_app_env: str) -> None:
    _assert_rejected(
        _settings_env(raw_app_env),
        mentions=("APP_ENV",),
    )


@pytest.mark.requirement("WS02-01-R2")
def test_environment_identity_normalizes_accepted_case_and_padding() -> None:
    settings = _build(_settings_env(" Production "))

    assert settings.app_env is AppEnvironment.PRODUCTION


@pytest.mark.requirement("WS02-01-R3", "WS02-01-R5", "WS03-03B-R1")
@pytest.mark.parametrize("app_env", ["preview", "staging", "production"])
@pytest.mark.parametrize(
    "missing_name",
    [
        "ALLOWED_HOSTS",
        "CORS_ALLOWED_ORIGINS",
        "FIREBASE_ADMIN_CREDENTIALS_JSON",
        "FIREBASE_PROJECT_ID",
        "FIREBASE_APP_CHECK_MODE",
        "R2_ACCOUNT_ID",
    ],
)
def test_production_like_environments_reject_missing_required_config(
    app_env: str,
    missing_name: str,
) -> None:
    _assert_rejected(
        _settings_env(app_env, **{missing_name: None}),
        mentions=(missing_name,),
    )


@pytest.mark.requirement("WS02-01-R3")
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("DATABASE_URL", f"postgresql+psycopg://localhost:5432/{_PRODUCTION_DATABASE_NAME}"),
        ("DATABASE_URL", "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"),
        ("ALLOWED_HOSTS", "localhost"),
        ("CORS_ALLOWED_ORIGINS", "http://localhost:5173"),
    ],
)
def test_production_like_environments_reject_local_only_values(name: str, value: str) -> None:
    _assert_rejected(
        _settings_env("preview", **{name: value}),
        mentions=(name,),
    )


@pytest.mark.requirement("WS02-01-R3", "WS02-01-R6")
@pytest.mark.parametrize("app_env", ["preview", "staging", "production"])
@pytest.mark.parametrize(
    "name",
    [
        "ALLOWED_HOSTS",
        "CORS_ALLOWED_ORIGINS",
    ],
)
def test_production_like_environments_reject_wildcard_host_and_cors_boundaries(
    app_env: str,
    name: str,
) -> None:
    _assert_rejected(
        _settings_env(app_env, **{name: "*"}),
        mentions=(name,),
    )


@pytest.mark.requirement("WS02-01-R3")
def test_production_rejects_api_docs_exposure() -> None:
    _assert_rejected(
        _settings_env("production", ENABLE_API_DOCS="true"),
        mentions=("ENABLE_API_DOCS",),
    )


@pytest.mark.requirement("WS02-01-R3", "WS02-01-R5")
@pytest.mark.parametrize(
    ("name", "placeholder"),
    [
        ("DATABASE_URL", "replace-with-postgresql-url"),
        ("ALLOWED_HOSTS", "replace-with-api-hosts"),
        ("FIREBASE_PROJECT_ID", "replace-with-firebase-project-id"),
        ("STRIPE_SECRET_KEY", "replace-with-stripe-secret-key"),
        ("STRIPE_WEBHOOK_SECRET", "replace-with-stripe-webhook-secret"),
        ("R2_SECRET_ACCESS_KEY", "replace-with-r2-secret-access-key"),
    ],
)
def test_production_like_environments_reject_documented_placeholders_without_echoing_values(
    name: str,
    placeholder: str,
) -> None:
    _assert_rejected(
        _settings_env("production", **{name: placeholder}),
        mentions=(name,),
        does_not_echo=(placeholder,),
    )


@pytest.mark.requirement("WS02-01-R4")
@pytest.mark.parametrize("app_env", ["test", "ci"])
def test_test_and_ci_require_the_dedicated_database_identity(app_env: str) -> None:
    settings = _build(_settings_env(app_env))

    assert settings.database_url_value.endswith(f"/{DEDICATED_TEST_DATABASE_NAME}")


@pytest.mark.requirement("WS02-01-R4")
@pytest.mark.parametrize("app_env", ["test", "ci"])
def test_test_and_ci_reject_non_dedicated_database_names(app_env: str) -> None:
    _assert_rejected(
        _settings_env(app_env, DATABASE_URL="postgresql+psycopg://db.example.invalid:5432/pickup_lane_dev"),
        mentions=("DATABASE_URL", DEDICATED_TEST_DATABASE_NAME),
    )


@pytest.mark.requirement("WS02-01-R4")
@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:///pickup_lane_test_db",
        "postgresql+psycopg:///pickup_lane_test_db",
        "postgresql+psycopg://db.example.invalid",
        "not a database url",
    ],
)
def test_database_url_validation_rejects_malformed_or_unsupported_urls(
    database_url: str,
) -> None:
    _assert_rejected(
        _settings_env("local", DATABASE_URL=database_url),
        mentions=("DATABASE_URL",),
    )


@pytest.mark.requirement("WS02-01-R4")
@pytest.mark.parametrize(
    "database_name",
    [
        "pickup_lane_dev",
        "pickup_lane_local",
        "pickup_lane_test",
        "pickup_lane_staging",
        "pickup_lane_preview",
    ],
)
def test_production_database_names_reject_lower_environment_identities(
    database_name: str,
) -> None:
    _assert_rejected(
        _settings_env(
            "production",
            DATABASE_URL=f"postgresql+psycopg://db.example.invalid:5432/{database_name}",
        ),
        mentions=("DATABASE_URL",),
    )


@pytest.mark.requirement("WS02-01-R5")
@pytest.mark.parametrize(
    "missing_name",
    ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET"],
)
def test_enabled_stripe_payments_require_backend_fields_together(missing_name: str) -> None:
    env = _settings_env(
        "production",
        ENABLE_STRIPE_PAYMENTS="true",
        STRIPE_SECRET_KEY=_STRIPE_SECRET_KEY,
        STRIPE_PUBLISHABLE_KEY=_STRIPE_PUBLISHABLE_KEY,
        STRIPE_WEBHOOK_SECRET=_STRIPE_WEBHOOK_SECRET,
    )
    env.pop(missing_name)

    _assert_rejected(env, mentions=(missing_name,))


@pytest.mark.requirement("WS02-01-R5")
def test_stripe_configuration_rejects_unsupported_currency() -> None:
    _assert_rejected(
        _settings_env("production", STRIPE_CURRENCY="EUR"),
        mentions=("STRIPE_CURRENCY",),
    )


@pytest.mark.requirement("WS02-01-R5")
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("FIREBASE_ADMIN_CREDENTIALS_JSON", "{not-json-synthetic-private}"),
        ("FIREBASE_ADMIN_CREDENTIALS_JSON", "[]"),
        ("FIREBASE_PROJECT_ID", "Project_With_Underscore"),
    ],
)
def test_firebase_admin_configuration_rejects_invalid_backend_values(
    name: str,
    value: str,
) -> None:
    _assert_rejected(
        _settings_env("production", **{name: value}),
        mentions=(name,),
        does_not_echo=(value,),
    )


@pytest.mark.requirement("WS02-01-R5")
def test_firebase_admin_credentials_path_is_validated_without_provider_access() -> None:
    missing_path = "synthetic-missing-firebase-admin.json"

    _assert_rejected(
        _settings_env(
            "production",
            FIREBASE_ADMIN_CREDENTIALS_JSON=None,
            FIREBASE_ADMIN_CREDENTIALS=missing_path,
        ),
        mentions=("FIREBASE_ADMIN_CREDENTIALS",),
        does_not_echo=(missing_path,),
    )


@pytest.mark.requirement("WS02-01-R5")
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("R2_SECRET_ACCESS_KEY", None),
        ("R2_ENDPOINT_URL", "http://synthetic-r2-account.r2.cloudflarestorage.com"),
        ("R2_ENDPOINT_URL", "https://synthetic-r2-account.r2.cloudflarestorage.com/path"),
    ],
)
def test_r2_configuration_rejects_partial_or_unsafe_backend_values(
    name: str,
    value: str | None,
) -> None:
    _assert_rejected(
        _settings_env("production", **{name: value}),
        mentions=(name,),
    )


@pytest.mark.requirement("WS02-01-R5", "WS03-03B-R1")
def test_complete_backend_private_provider_config_is_accepted_without_provider_calls() -> None:
    settings = _build(
        _settings_env(
            "production",
            ENABLE_STRIPE_PAYMENTS="true",
            STRIPE_SECRET_KEY=_STRIPE_SECRET_KEY,
            STRIPE_PUBLISHABLE_KEY=_STRIPE_PUBLISHABLE_KEY,
            STRIPE_WEBHOOK_SECRET=_STRIPE_WEBHOOK_SECRET,
        )
    )

    assert settings.firebase_project_id == "pickup-lane-synthetic"
    assert settings.firebase_app_check_mode.value == "disabled"
    assert settings.enable_stripe_payments is True
    assert settings.r2_configured is True


@pytest.mark.requirement("WS02-01-R1", "WS02-01-R7")
def test_explicit_settings_construction_uses_synthetic_mapping_without_dotenv(
    monkeypatch,
) -> None:
    def unexpected_dotenv_load(*_args, **_kwargs):
        raise AssertionError("settings validation must not load dotenv here")

    monkeypatch.setattr(settings_module, "load_dotenv", unexpected_dotenv_load)

    settings = _build(_settings_env("production"))

    assert settings.allowed_hosts == ("api.example.invalid",)
    assert settings.cors_allowed_origins == ("https://app.example.invalid",)


@pytest.mark.requirement("WS02-01-R7")
def test_ordinary_settings_tests_block_uncontrolled_network_access() -> None:
    probe_socket = socket.socket()
    try:
        with pytest.raises(EnvironmentSafetyError) as exc_info:
            probe_socket.connect(("api.stripe.com", 443))
    finally:
        probe_socket.close()

    assert NETWORK_BLOCKED_MESSAGE in str(exc_info.value)


@pytest.mark.requirement("WS02-01-R1", "WS02-01-R2")
def test_non_production_defaults_are_bounded_to_non_production_environments() -> None:
    settings = _build(
        _settings_env(
            "local",
            ALLOWED_HOSTS=None,
            CORS_ALLOWED_ORIGINS=None,
            ENABLE_API_DOCS=None,
            ENABLE_DB_HEALTH=None,
        )
    )

    assert settings.allowed_hosts == DEFAULT_ALLOWED_HOSTS
    assert settings.cors_allowed_origins == DEFAULT_CORS_ORIGINS
    assert settings.enable_api_docs is True
    assert settings.enable_db_health is True
