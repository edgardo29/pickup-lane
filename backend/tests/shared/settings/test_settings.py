import importlib
from pathlib import Path

import pytest

from backend.settings import (
    BACKEND_ENVIRONMENT_VARIABLES,
    AppEnvironment,
    DEFAULT_RELEASE_IDENTITY,
    DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES,
    DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES,
    SettingsError,
    build_settings,
    get_inbox_token_secret,
    reset_settings_cache,
)


pytestmark = pytest.mark.no_db_cleanup

LOCAL_DATABASE_URL = (
    "postgresql+psycopg://local_user:local_password@localhost:5432/"
    "pickup_lane_local"
)
TEST_DATABASE_URL = (
    "postgresql+psycopg://test_user:test_password@localhost:5432/"
    "pickup_lane_test_db"
)
PRODUCTION_DATABASE_URL = (
    "postgresql+psycopg://app_user:app_password@db.example.net:5432/"
    "pickup_lane"
)
PRODUCTION_ALLOWED_HOSTS = "api.example.net,admin-api.example.net"
PRODUCTION_ORIGINS = "https://app.example.net,https://admin.example.net"
FIREBASE_ADMIN_JSON = '{"type":"service_account","project_id":"pickup-lane-synthetic"}'
CI_MERGE_COMMIT_SHA = "61f14285517180d22f1d5e71af278d815040e63c"
NORMAL_GITHUB_SHA = "c1d68518c606f5b704b02bd9639fb76189c07a82"


def local_env(**overrides):
    return _clean_env(
        {
            "APP_ENV": "local",
            "DATABASE_URL": LOCAL_DATABASE_URL,
            "INBOX_TOKEN_SECRET": "synthetic-independent-inbox-token",
            **overrides,
        }
    )


def backend_test_env(**overrides):
    return _clean_env(
        {
            "APP_ENV": "test",
            "DATABASE_URL": TEST_DATABASE_URL,
            "INBOX_TOKEN_SECRET": "synthetic-independent-inbox-token",
            **overrides,
        }
    )


def production_like_env(app_env="production", **overrides):
    return _clean_env(
        {
            "APP_ENV": app_env,
            "DATABASE_URL": PRODUCTION_DATABASE_URL,
            "INBOX_TOKEN_SECRET": "synthetic-independent-inbox-token",
            "FIREBASE_ADMIN_CREDENTIALS_JSON": FIREBASE_ADMIN_JSON,
            "ALLOWED_HOSTS": PRODUCTION_ALLOWED_HOSTS,
            "CORS_ALLOWED_ORIGINS": PRODUCTION_ORIGINS,
            "ENABLE_API_DOCS": "false",
            "ENABLE_DB_HEALTH": "false",
            "R2_ACCOUNT_ID": "synthetic-r2-account",
            "R2_ACCESS_KEY_ID": "synthetic-r2-access-key",
            "R2_SECRET_ACCESS_KEY": "synthetic-r2-secret-key",
            "R2_BUCKET_NAME": "pickup-lane-synthetic-media",
            **overrides,
        }
    )


def _clean_env(values):
    return {key: value for key, value in values.items() if value is not None}


@pytest.mark.parametrize(
    "app_env",
    ["local", "test", "ci", "preview", "staging", "production"],
)
def test_canonical_app_environments_are_accepted(app_env):
    env = production_like_env(app_env) if app_env in {"preview", "staging", "production"} else backend_test_env(APP_ENV=app_env)

    settings = build_settings(env)

    assert settings.app_env == AppEnvironment(app_env)


def test_app_environment_is_case_normalized():
    settings = build_settings(production_like_env(" PrEvIeW "))

    assert settings.app_env == AppEnvironment.PREVIEW


@pytest.mark.parametrize("app_env", ["", "qa", "development", "prod"])
def test_blank_and_unknown_app_environments_are_rejected(app_env):
    with pytest.raises(SettingsError, match="APP_ENV"):
        build_settings(local_env(APP_ENV=app_env))


def test_ci_defaults_to_ci_environment_when_app_env_is_absent():
    settings = build_settings(
        backend_test_env(APP_ENV=None, CI="true"),
    )

    assert settings.app_env == AppEnvironment.CI


def test_deployed_markers_require_explicit_production_like_environment():
    with pytest.raises(SettingsError, match="APP_ENV"):
        build_settings(production_like_env(APP_ENV=None, RENDER="true"))

    with pytest.raises(SettingsError, match="APP_ENV"):
        build_settings(local_env(RENDER_SERVICE_ID="srv-synthetic"))

    settings = build_settings(production_like_env("preview", RENDER="true"))
    assert settings.app_env == AppEnvironment.PREVIEW


@pytest.mark.parametrize("commit_sha", [CI_MERGE_COMMIT_SHA, NORMAL_GITHUB_SHA])
def test_source_revision_full_git_commit_sha_is_accepted(commit_sha):
    settings = build_settings(backend_test_env(GITHUB_SHA=commit_sha.upper()))

    assert settings.release_identity == commit_sha


def test_minimal_database_settings_accept_github_merge_sha():
    settings = build_settings(
        backend_test_env(APP_ENV="ci", GITHUB_SHA=CI_MERGE_COMMIT_SHA),
        validate_full=False,
    )

    assert settings.release_identity == CI_MERGE_COMMIT_SHA
    assert settings.database_url_value == TEST_DATABASE_URL


def test_release_identity_falls_back_when_no_source_revision_is_supplied():
    settings = build_settings(backend_test_env())

    assert settings.release_identity == DEFAULT_RELEASE_IDENTITY


@pytest.mark.parametrize(
    "value",
    [
        "555-555-0123",
        "a" * 39,
        "a" * 65,
        f"{NORMAL_GITHUB_SHA} ",
        "release candidate",
        "release/path",
        "https://" + "release.example/path",
        "release" + "@example.test",
        "postgresql://" + "db.example.test/release",
        "sk_" + "test_" + "syntheticvalue",
        "user:pass",
    ],
)
def test_source_revision_non_sha_sensitive_or_unsafe_values_are_rejected(value):
    with pytest.raises(SettingsError, match="GITHUB_SHA"):
        build_settings(backend_test_env(GITHUB_SHA=value))


def test_generic_release_label_still_uses_sensitive_text_validation():
    settings = build_settings(backend_test_env(RELEASE_IDENTITY="commit.abc123"))

    assert settings.release_identity == "commit.abc123"

    with pytest.raises(SettingsError, match="RELEASE_IDENTITY"):
        build_settings(backend_test_env(RELEASE_IDENTITY="555-555-0123"))


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://test_user:test_password@localhost:5432/pickup_lane_test_db",
        (
            "postgresql+psycopg://test_user:encoded%40password@[::1]:5432/"
            "pickup_lane_test_db?sslmode=disable"
        ),
        (
            "postgresql+psycopg2://test_user:test_password@127.0.0.1:5432/"
            "pickup_lane_test_db"
        ),
    ],
)
def test_test_and_ci_database_url_forms_are_accepted(database_url):
    settings = build_settings(backend_test_env(APP_ENV="ci", DATABASE_URL=database_url))

    assert settings.database_url_value == database_url


@pytest.mark.parametrize(
    "app_env,database_url,expected",
    [
        ("test", "postgresql+psycopg://user:password@localhost:5432/pickup_lane", "pickup_lane_test_db"),
        ("ci", "postgresql+psycopg://user:password@localhost:5432/pickup_lane_test", "pickup_lane_test_db"),
        ("local", "sqlite:///tmp/pickup_lane.db", "PostgreSQL"),
        ("local", "mysql://user:password@localhost:3306/pickup_lane", "PostgreSQL"),
        ("local", "postgresql+psycopg://localhost", "database name"),
        ("local", "not-a-url", "valid SQLAlchemy"),
        ("production", "postgresql+psycopg://user:password@localhost:5432/pickup_lane", "localhost"),
        ("production", "postgresql+psycopg://user:password@db.example.net:5432/pickup_lane_test", "database name"),
    ],
)
def test_database_url_safety_rejects_unsafe_forms(app_env, database_url, expected):
    env = production_like_env(app_env, DATABASE_URL=database_url) if app_env == "production" else backend_test_env(APP_ENV=app_env, DATABASE_URL=database_url)

    with pytest.raises(SettingsError, match="DATABASE_URL") as exc_info:
        build_settings(env)

    assert expected in str(exc_info.value)
    assert database_url not in str(exc_info.value)


def test_cors_origins_default_locally_and_normalize_explicit_values():
    local_settings = build_settings(local_env(CORS_ALLOWED_ORIGINS=None))
    explicit_settings = build_settings(
        local_env(
            CORS_ALLOWED_ORIGINS=(
                " https://app.example.net/ , https://app.example.net,"
                "https://admin.example.net "
            )
        )
    )

    assert local_settings.cors_allowed_origins == (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    assert explicit_settings.cors_allowed_origins == (
        "https://app.example.net",
        "https://admin.example.net",
    )


@pytest.mark.parametrize(
    "origins,expected",
    [
        ("*", "wildcard"),
        ("https://app.example.net/path", "origins only"),
        ("https://app.example.net, ,https://admin.example.net", "blank origins"),
        ("not-an-origin", "valid http or https"),
    ],
)
def test_cors_rejects_unbounded_or_malformed_origins(origins, expected):
    with pytest.raises(SettingsError, match=expected):
        build_settings(local_env(CORS_ALLOWED_ORIGINS=origins))


def test_production_like_cors_must_be_explicit_and_nonlocal():
    with pytest.raises(SettingsError, match="CORS_ALLOWED_ORIGINS"):
        build_settings(production_like_env(CORS_ALLOWED_ORIGINS=None))

    with pytest.raises(SettingsError, match="localhost"):
        build_settings(
            production_like_env(
                CORS_ALLOWED_ORIGINS="http://localhost:5173",
            )
        )


def test_api_docs_and_db_health_are_env_aware():
    local_settings = build_settings(local_env(ENABLE_API_DOCS=None, ENABLE_DB_HEALTH=None))
    preview_settings = build_settings(
        production_like_env(
            "preview",
            ENABLE_API_DOCS=None,
            ENABLE_DB_HEALTH=None,
        )
    )

    assert local_settings.enable_api_docs is True
    assert local_settings.enable_db_health is True
    assert preview_settings.enable_api_docs is False
    assert preview_settings.enable_db_health is False


def test_production_rejects_public_api_docs():
    with pytest.raises(SettingsError, match="ENABLE_API_DOCS"):
        build_settings(production_like_env("production", ENABLE_API_DOCS="true"))


@pytest.mark.parametrize(
    "app_env",
    ["local", "test", "ci", "preview", "staging", "production"],
)
def test_request_body_limit_defaults_apply_in_every_environment(app_env):
    env = (
        production_like_env(app_env)
        if app_env in {"preview", "staging", "production"}
        else backend_test_env(APP_ENV=app_env)
    )

    settings = build_settings(env)

    assert (
        settings.platform_notice_request_body_limit_bytes
        == DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES
    )
    assert (
        settings.stripe_webhook_request_body_limit_bytes
        == DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES
    )


def test_request_body_limit_settings_accept_positive_overrides():
    settings = build_settings(
        local_env(
            PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES="1024",
            STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES="2048",
        )
    )

    assert settings.platform_notice_request_body_limit_bytes == 1024
    assert settings.stripe_webhook_request_body_limit_bytes == 2048


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES", "0"),
        ("PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES", "-1"),
        ("PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES", "large"),
        ("STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES", "0"),
        ("STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES", "-1"),
        ("STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES", "large"),
    ],
)
def test_request_body_limit_settings_reject_unsafe_values(name, value):
    with pytest.raises(SettingsError, match=name):
        build_settings(local_env(**{name: value}))


def test_stripe_disabled_does_not_require_unused_secrets():
    settings = build_settings(
        local_env(
            ENABLE_STRIPE_PAYMENTS="false",
            STRIPE_SECRET_KEY=None,
            STRIPE_PUBLISHABLE_KEY=None,
            STRIPE_WEBHOOK_SECRET=None,
        )
    )

    assert settings.enable_stripe_payments is False
    assert settings.stripe_secret_key_value is None


@pytest.mark.parametrize(
    "overrides,expected",
    [
        ({"ENABLE_STRIPE_PAYMENTS": "true", "STRIPE_SECRET_KEY": None}, "STRIPE_SECRET_KEY"),
        ({"STRIPE_CURRENCY": "cad"}, "STRIPE_CURRENCY"),
        ({"ENABLE_STRIPE_PAYMENTS": "sometimes"}, "ENABLE_STRIPE_PAYMENTS"),
    ],
)
def test_stripe_validation_is_explicit(overrides, expected):
    with pytest.raises(SettingsError, match=expected):
        build_settings(local_env(**overrides))


def test_stripe_enabled_requires_all_private_settings():
    settings = build_settings(
        local_env(
            ENABLE_STRIPE_PAYMENTS="true",
            STRIPE_SECRET_KEY="synthetic-stripe-secret-key",
            STRIPE_PUBLISHABLE_KEY="synthetic-stripe-publishable-key",
            STRIPE_WEBHOOK_SECRET="synthetic-stripe-webhook-secret",
        )
    )

    assert settings.enable_stripe_payments is True
    assert settings.stripe_currency == "USD"


def test_firebase_admin_json_is_validated_without_provider_initialization():
    settings = build_settings(
        production_like_env(FIREBASE_ADMIN_CREDENTIALS_JSON=FIREBASE_ADMIN_JSON)
    )

    assert settings.firebase_admin_credentials_json_value == FIREBASE_ADMIN_JSON


def test_firebase_admin_json_rejects_malformed_values():
    with pytest.raises(SettingsError, match="FIREBASE_ADMIN_CREDENTIALS_JSON"):
        build_settings(production_like_env(FIREBASE_ADMIN_CREDENTIALS_JSON="not-json"))


def test_production_like_firebase_admin_path_must_be_readable():
    with pytest.raises(SettingsError, match="FIREBASE_ADMIN_CREDENTIALS"):
        build_settings(
            production_like_env(
                FIREBASE_ADMIN_CREDENTIALS_JSON=None,
                FIREBASE_ADMIN_CREDENTIALS="/not/a/readable/firebase-admin.json",
            )
        )


def test_production_like_requires_firebase_admin_credentials():
    with pytest.raises(SettingsError, match="FIREBASE_ADMIN_CREDENTIALS_JSON"):
        build_settings(
            production_like_env(
                FIREBASE_ADMIN_CREDENTIALS_JSON=None,
                FIREBASE_ADMIN_CREDENTIALS=None,
            )
        )


def test_r2_complete_config_derives_endpoint_and_normalizes_image_types():
    settings = build_settings(
        local_env(
            R2_ACCOUNT_ID="synthetic-r2-account",
            R2_ACCESS_KEY_ID="synthetic-r2-access-key",
            R2_SECRET_ACCESS_KEY="synthetic-r2-secret-key",
            R2_BUCKET_NAME="pickup-lane-synthetic-media",
            R2_ALLOWED_IMAGE_TYPES=" image/PNG , image/JPEG ",
        )
    )

    assert settings.r2_endpoint_url == "https://synthetic-r2-account.r2.cloudflarestorage.com"
    assert settings.r2_allowed_image_types == frozenset({"image/png", "image/jpeg"})


@pytest.mark.parametrize(
    "overrides,expected",
    [
        ({"R2_ACCOUNT_ID": "synthetic-r2-account"}, "R2_ACCESS_KEY_ID"),
        ({"R2_UPLOAD_URL_MINUTES": "0"}, "R2_UPLOAD_URL_MINUTES"),
        ({"R2_READ_URL_MINUTES": "ten"}, "R2_READ_URL_MINUTES"),
        ({"R2_MAX_IMAGE_BYTES": "-1"}, "R2_MAX_IMAGE_BYTES"),
        ({"R2_ALLOWED_IMAGE_TYPES": "application/pdf"}, "R2_ALLOWED_IMAGE_TYPES"),
        (
            {
                "R2_ACCOUNT_ID": "synthetic-r2-account",
                "R2_ACCESS_KEY_ID": "synthetic-r2-access-key",
                "R2_SECRET_ACCESS_KEY": "synthetic-r2-secret-key",
                "R2_BUCKET_NAME": "pickup-lane-synthetic-media",
                "R2_ENDPOINT_URL": "http://r2.example.net",
            },
            "R2_ENDPOINT_URL",
        ),
    ],
)
def test_r2_rejects_partial_or_unsafe_config(overrides, expected):
    with pytest.raises(SettingsError, match=expected):
        build_settings(local_env(**overrides))


def test_inbox_token_secret_must_be_independent():
    with pytest.raises(SettingsError, match="DATABASE_URL"):
        build_settings(local_env(INBOX_TOKEN_SECRET=LOCAL_DATABASE_URL))

    with pytest.raises(SettingsError, match="STRIPE_SECRET_KEY"):
        build_settings(
            local_env(
                ENABLE_STRIPE_PAYMENTS="true",
                STRIPE_SECRET_KEY="shared-synthetic-secret",
                STRIPE_PUBLISHABLE_KEY="synthetic-stripe-publishable-key",
                STRIPE_WEBHOOK_SECRET="synthetic-stripe-webhook-secret",
                INBOX_TOKEN_SECRET="shared-synthetic-secret",
            )
        )


def test_inbox_token_secret_has_no_database_url_fallback():
    settings = build_settings(local_env(INBOX_TOKEN_SECRET=None))

    with pytest.raises(SettingsError, match="INBOX_TOKEN_SECRET"):
        get_inbox_token_secret(settings)


def test_settings_repr_masks_private_values():
    settings = build_settings(local_env())
    rendered = repr(settings)

    assert LOCAL_DATABASE_URL not in rendered
    assert "synthetic-independent-inbox-token" not in rendered
    assert "**********" in rendered


def test_backend_env_example_matches_authoritative_setting_names():
    example_names = {
        line.split("=", maxsplit=1)[0]
        for line in Path("backend/.env.example").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert example_names == BACKEND_ENVIRONMENT_VARIABLES
    assert not any(name.startswith("VITE_") for name in example_names)


def test_create_app_uses_typed_docs_health_and_cors_settings():
    from backend.main import create_app

    settings = build_settings(local_env())
    app = create_app(settings=settings)
    paths = set(app.openapi()["paths"])
    cors_middleware = [
        middleware
        for middleware in app.user_middleware
        if middleware.cls.__name__ == "CORSMiddleware"
    ][0]

    assert "/db-health" in paths
    assert cors_middleware.kwargs["allow_origins"] == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_main_import_uses_synthetic_env_without_database_or_provider_contact(monkeypatch):
    for key, value in backend_test_env().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("ENABLE_API_DOCS", "true")
    monkeypatch.setenv("ENABLE_DB_HEALTH", "false")
    reset_settings_cache()

    import backend.main as main_module

    try:
        reloaded_main = importlib.reload(main_module)

        assert reloaded_main.app.docs_url == "/docs"
        assert all(route.path != "/db-health" for route in reloaded_main.app.routes)
    finally:
        monkeypatch.setenv("ENABLE_DB_HEALTH", "true")
        reset_settings_cache()
        importlib.reload(main_module)
        reset_settings_cache()


def test_minimal_database_settings_do_not_require_provider_credentials():
    settings = build_settings(
        backend_test_env(
            FIREBASE_ADMIN_CREDENTIALS_JSON=None,
            FIREBASE_ADMIN_CREDENTIALS=None,
            R2_ACCOUNT_ID=None,
            R2_ACCESS_KEY_ID=None,
            R2_SECRET_ACCESS_KEY=None,
            R2_BUCKET_NAME=None,
        ),
        validate_full=False,
    )

    assert settings.database_url_value == TEST_DATABASE_URL
