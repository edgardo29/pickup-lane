"""Typed backend settings and environment safety validation."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, SecretStr
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from backend.observability.request_body_limits import (
    DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES,
    DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES,
    DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES,
)
from backend.observability.redaction import contains_sensitive_text


class SettingsError(RuntimeError):
    """Raised when backend environment configuration is unsafe or invalid."""


class AppEnvironment(str, Enum):
    LOCAL = "local"
    TEST = "test"
    CI = "ci"
    PREVIEW = "preview"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def is_production_like(self) -> bool:
        return self in {self.PREVIEW, self.STAGING, self.PRODUCTION}


class FirebaseAppCheckMode(str, Enum):
    DISABLED = "disabled"
    OBSERVE = "observe"
    ENFORCED = "enforced"

    @property
    def requires_app_id(self) -> bool:
        return self in {self.OBSERVE, self.ENFORCED}


BACKEND_ENVIRONMENT_VARIABLES = frozenset(
    {
        "APP_ENV",
        "DATABASE_URL",
        "MIGRATION_DATABASE_URL",
        "DB_POOL_SIZE",
        "DB_MAX_OVERFLOW",
        "INBOX_TOKEN_SECRET",
        "FIREBASE_ADMIN_CREDENTIALS_JSON",
        "FIREBASE_ADMIN_CREDENTIALS",
        "FIREBASE_PROJECT_ID",
        "FIREBASE_APP_CHECK_MODE",
        "FIREBASE_APP_CHECK_APP_ID",
        "ALLOWED_HOSTS",
        "CORS_ALLOWED_ORIGINS",
        "ENABLE_API_DOCS",
        "ENABLE_DB_HEALTH",
        "ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES",
        "PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES",
        "STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES",
        "ENABLE_STRIPE_PAYMENTS",
        "STRIPE_SECRET_KEY",
        "STRIPE_PUBLISHABLE_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "STRIPE_CURRENCY",
        "STRIPE_READ_TIMEOUT_SECONDS",
        "STRIPE_MUTATION_TIMEOUT_SECONDS",
        "FIREBASE_HTTP_TIMEOUT_SECONDS",
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET_NAME",
        "R2_ENDPOINT_URL",
        "R2_UPLOAD_URL_MINUTES",
        "R2_READ_URL_MINUTES",
        "R2_MAX_IMAGE_BYTES",
        "R2_ALLOWED_IMAGE_TYPES",
        "R2_METADATA_CONNECT_TIMEOUT_SECONDS",
        "R2_METADATA_READ_TIMEOUT_SECONDS",
        "DB_POOL_WAIT_TIMEOUT_SECONDS",
        "DB_STATEMENT_TIMEOUT_MILLISECONDS",
        "DB_LOCK_TIMEOUT_MILLISECONDS",
    }
)

DEPLOYMENT_MARKER_ENV_NAMES = frozenset(
    {
        "RENDER",
        "RENDER_SERVICE_ID",
        "RENDER_SERVICE_NAME",
        "VERCEL",
        "VERCEL_ENV",
    }
)

TRUE_ENV_VALUES = frozenset({"1", "true", "yes", "on"})
FALSE_ENV_VALUES = frozenset({"0", "false", "no", "off"})

DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
DEFAULT_ALLOWED_HOSTS = ("localhost", "127.0.0.1", "testserver")
DEFAULT_R2_ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
DEDICATED_TEST_DATABASE_NAME = "pickup_lane_test_db"
SUPPORTED_STRIPE_CURRENCY = "USD"
DEFAULT_STRIPE_READ_TIMEOUT_SECONDS = 6
DEFAULT_STRIPE_MUTATION_TIMEOUT_SECONDS = 15
DEFAULT_FIREBASE_HTTP_TIMEOUT_SECONDS = 8
DEFAULT_RECENT_AUTHENTICATION_WINDOW_SECONDS = 5 * 60
DEFAULT_R2_METADATA_CONNECT_TIMEOUT_SECONDS = 2
DEFAULT_R2_METADATA_READ_TIMEOUT_SECONDS = 6
DEFAULT_DB_POOL_WAIT_TIMEOUT_SECONDS = 2
DEFAULT_DB_STATEMENT_TIMEOUT_MILLISECONDS = 12_000
DEFAULT_DB_LOCK_TIMEOUT_MILLISECONDS = 2_000

DOCUMENTED_PLACEHOLDER_VALUES = frozenset(
    {
        "replace-with-independent-secret",
        "replace-with-postgresql-url",
        "replace-with-migration-postgresql-url",
        "replace-with-api-hosts",
        "replace-with-firebase-admin-json",
        "replace-with-firebase-project-id",
        "replace-with-firebase-app-check-app-id",
        "replace-with-stripe-secret-key",
        "replace-with-stripe-publishable-key",
        "replace-with-stripe-webhook-secret",
        "replace-with-r2-account-id",
        "replace-with-r2-access-key-id",
        "replace-with-r2-secret-access-key",
        "replace-with-r2-bucket-name",
        "https://replace-with-r2-account-id.r2.cloudflarestorage.com",
    }
)

DEFAULT_RELEASE_IDENTITY = "source-unavailable"
RELEASE_IDENTITY_ENV_NAMES = (
    "PICKUP_LANE_RELEASE",
    "RELEASE_IDENTITY",
    "SOURCE_REVISION",
    "GITHUB_SHA",
    "RENDER_GIT_COMMIT",
    "VERCEL_GIT_COMMIT_SHA",
)
SOURCE_REVISION_ENV_NAMES = frozenset(
    {
        "SOURCE_REVISION",
        "GITHUB_SHA",
        "RENDER_GIT_COMMIT",
        "VERCEL_GIT_COMMIT_SHA",
    }
)
_MAX_RELEASE_IDENTITY_LENGTH = 80
_FULL_GIT_COMMIT_SHA_LENGTHS = frozenset({40, 64})

_LOCAL_HOSTNAMES = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
    }
)

_UNSAFE_PRODUCTION_LIKE_DB_NAME_PARTS = ("dev", "local", "test")
_UNSAFE_PRODUCTION_DB_NAME_PARTS = ("staging", "preview")
_DNS_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_FULL_GIT_COMMIT_SHA_RE = re.compile(r"^[0-9a-fA-F]+$")


@dataclass(frozen=True)
class DatabaseTimeoutSettings:
    pool_wait_timeout_seconds: int
    statement_timeout_milliseconds: int
    lock_timeout_milliseconds: int


@dataclass(frozen=True)
class DatabasePoolSettings:
    pool_size: int | None
    max_overflow: int | None


class BackendSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_env: AppEnvironment
    release_identity: str = DEFAULT_RELEASE_IDENTITY
    database_url: SecretStr
    inbox_token_secret: SecretStr | None = None
    firebase_admin_credentials_json: SecretStr | None = None
    firebase_admin_credentials: SecretStr | None = None
    firebase_project_id: str | None = None
    firebase_app_check_mode: FirebaseAppCheckMode = FirebaseAppCheckMode.DISABLED
    firebase_app_check_app_id: str | None = None
    allowed_hosts: tuple[str, ...] = DEFAULT_ALLOWED_HOSTS
    cors_allowed_origins: tuple[str, ...]
    cors_allow_credentials: bool = True
    enable_api_docs: bool
    enable_db_health: bool
    ordinary_json_request_body_limit_bytes: int = (
        DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES
    )
    platform_notice_request_body_limit_bytes: int = (
        DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES
    )
    stripe_webhook_request_body_limit_bytes: int = (
        DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES
    )
    enable_stripe_payments: bool
    stripe_secret_key: SecretStr | None = None
    stripe_publishable_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_currency: str = SUPPORTED_STRIPE_CURRENCY
    stripe_read_timeout_seconds: int = DEFAULT_STRIPE_READ_TIMEOUT_SECONDS
    stripe_mutation_timeout_seconds: int = DEFAULT_STRIPE_MUTATION_TIMEOUT_SECONDS
    firebase_http_timeout_seconds: int = DEFAULT_FIREBASE_HTTP_TIMEOUT_SECONDS
    recent_authentication_window_seconds: int = (
        DEFAULT_RECENT_AUTHENTICATION_WINDOW_SECONDS
    )
    r2_account_id: str | None = None
    r2_access_key_id: SecretStr | None = None
    r2_secret_access_key: SecretStr | None = None
    r2_bucket_name: str | None = None
    r2_endpoint_url: str | None = None
    r2_upload_url_minutes: int = 15
    r2_read_url_minutes: int = 60
    r2_max_image_bytes: int = 8 * 1024 * 1024
    r2_allowed_image_types: frozenset[str] = DEFAULT_R2_ALLOWED_IMAGE_TYPES
    r2_metadata_connect_timeout_seconds: int = (
        DEFAULT_R2_METADATA_CONNECT_TIMEOUT_SECONDS
    )
    r2_metadata_read_timeout_seconds: int = DEFAULT_R2_METADATA_READ_TIMEOUT_SECONDS
    db_pool_wait_timeout_seconds: int = DEFAULT_DB_POOL_WAIT_TIMEOUT_SECONDS
    db_statement_timeout_milliseconds: int = DEFAULT_DB_STATEMENT_TIMEOUT_MILLISECONDS
    db_lock_timeout_milliseconds: int = DEFAULT_DB_LOCK_TIMEOUT_MILLISECONDS
    db_pool_size: int | None = None
    db_max_overflow: int | None = None

    @property
    def is_production_like(self) -> bool:
        return self.app_env.is_production_like

    @property
    def database_url_value(self) -> str:
        return self.database_url.get_secret_value()

    @property
    def inbox_token_secret_value(self) -> str | None:
        return _secret_value(self.inbox_token_secret)

    @property
    def firebase_admin_credentials_json_value(self) -> str | None:
        return _secret_value(self.firebase_admin_credentials_json)

    @property
    def firebase_admin_credentials_value(self) -> str | None:
        return _secret_value(self.firebase_admin_credentials)

    @property
    def stripe_secret_key_value(self) -> str | None:
        return _secret_value(self.stripe_secret_key)

    @property
    def stripe_publishable_key_value(self) -> str | None:
        return _secret_value(self.stripe_publishable_key)

    @property
    def stripe_webhook_secret_value(self) -> str | None:
        return _secret_value(self.stripe_webhook_secret)

    @property
    def r2_access_key_id_value(self) -> str | None:
        return _secret_value(self.r2_access_key_id)

    @property
    def r2_secret_access_key_value(self) -> str | None:
        return _secret_value(self.r2_secret_access_key)

    @property
    def r2_configured(self) -> bool:
        return all(
            (
                self.r2_account_id,
                self.r2_access_key_id,
                self.r2_secret_access_key,
                self.r2_bucket_name,
                self.r2_endpoint_url,
            )
        )


def get_settings() -> BackendSettings:
    return _cached_settings()


@lru_cache(maxsize=1)
def _cached_settings() -> BackendSettings:
    return build_settings(load_dotenv_file=True, validate_full=True)


def get_database_url() -> str:
    return _cached_database_url()


@lru_cache(maxsize=1)
def _cached_database_url() -> str:
    return build_settings(load_dotenv_file=True, validate_full=False).database_url_value


def get_database_timeout_settings() -> DatabaseTimeoutSettings:
    return _cached_database_timeout_settings()


@lru_cache(maxsize=1)
def _cached_database_timeout_settings() -> DatabaseTimeoutSettings:
    settings = build_settings(load_dotenv_file=True, validate_full=False)
    return DatabaseTimeoutSettings(
        pool_wait_timeout_seconds=settings.db_pool_wait_timeout_seconds,
        statement_timeout_milliseconds=settings.db_statement_timeout_milliseconds,
        lock_timeout_milliseconds=settings.db_lock_timeout_milliseconds,
    )


def get_database_pool_settings() -> DatabasePoolSettings:
    return _cached_database_pool_settings()


@lru_cache(maxsize=1)
def _cached_database_pool_settings() -> DatabasePoolSettings:
    settings = build_settings(load_dotenv_file=True, validate_full=False)
    return DatabasePoolSettings(
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )


def get_migration_database_url() -> str:
    return _cached_migration_database_url()


@lru_cache(maxsize=1)
def _cached_migration_database_url() -> str:
    env, loaded_dotenv = _environment_mapping(None, load_dotenv_file=True)
    app_env = _parse_app_env(env)
    _validate_runtime_environment_source(env, loaded_dotenv, app_env)
    return _parse_migration_database_url(env, app_env)


def reset_settings_cache() -> None:
    _cached_settings.cache_clear()
    _cached_database_url.cache_clear()
    _cached_database_timeout_settings.cache_clear()
    _cached_database_pool_settings.cache_clear()
    _cached_migration_database_url.cache_clear()


def get_inbox_token_secret(settings: BackendSettings | None = None) -> str:
    backend_settings = settings or get_settings()
    secret = backend_settings.inbox_token_secret_value
    if not secret:
        _fail("INBOX_TOKEN_SECRET", "must be set before inbox tokens are used")
    return secret


def build_settings(
    environ: Mapping[str, str] | None = None,
    *,
    load_dotenv_file: bool = False,
    validate_full: bool = True,
) -> BackendSettings:
    env, loaded_dotenv = _environment_mapping(environ, load_dotenv_file=load_dotenv_file)
    app_env = _parse_app_env(env)

    _validate_runtime_environment_source(env, loaded_dotenv, app_env)

    database_url = _parse_database_url(env, app_env)
    release_identity = _parse_release_identity(env)
    allowed_hosts = _parse_allowed_hosts(env, app_env) if validate_full else DEFAULT_ALLOWED_HOSTS
    cors_origins = _parse_cors_origins(env, app_env) if validate_full else DEFAULT_CORS_ORIGINS
    enable_api_docs = (
        _parse_bool(env, "ENABLE_API_DOCS", default=not app_env.is_production_like)
        if validate_full
        else False
    )
    enable_db_health = (
        _parse_bool(env, "ENABLE_DB_HEALTH", default=not app_env.is_production_like)
        if validate_full
        else False
    )
    ordinary_json_request_body_limit_bytes = _parse_positive_int(
        env,
        "ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES",
        default=DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES,
    )
    platform_notice_request_body_limit_bytes = _parse_positive_int(
        env,
        "PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES",
        default=DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES,
    )
    stripe_webhook_request_body_limit_bytes = _parse_positive_int(
        env,
        "STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES",
        default=DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES,
    )
    timeout_values = _parse_timeout_settings(env)
    database_pool_values = _parse_database_pool_settings(env, app_env)

    if app_env is AppEnvironment.PRODUCTION and enable_api_docs:
        _fail("ENABLE_API_DOCS", "must be disabled in production")

    stripe_values = (
        _parse_stripe_settings(env, app_env) if validate_full else _empty_stripe_settings()
    )
    firebase_values = (
        _parse_firebase_admin_settings(env, app_env)
        if validate_full
        else _empty_firebase_settings()
    )
    app_check_values = (
        _parse_firebase_app_check_settings(env, app_env)
        if validate_full
        else _empty_firebase_app_check_settings()
    )
    r2_values = _parse_r2_settings(env, app_env) if validate_full else _empty_r2_settings()
    inbox_token_secret = _parse_inbox_token_secret(env, app_env, database_url, validate_full)

    return BackendSettings(
        app_env=app_env,
        release_identity=release_identity,
        database_url=SecretStr(database_url),
        inbox_token_secret=SecretStr(inbox_token_secret) if inbox_token_secret else None,
        allowed_hosts=allowed_hosts,
        cors_allowed_origins=cors_origins,
        enable_api_docs=enable_api_docs,
        enable_db_health=enable_db_health,
        ordinary_json_request_body_limit_bytes=ordinary_json_request_body_limit_bytes,
        platform_notice_request_body_limit_bytes=platform_notice_request_body_limit_bytes,
        stripe_webhook_request_body_limit_bytes=stripe_webhook_request_body_limit_bytes,
        **timeout_values,
        **database_pool_values,
        **stripe_values,
        **firebase_values,
        **app_check_values,
        **r2_values,
    )


def _environment_mapping(
    environ: Mapping[str, str] | None,
    *,
    load_dotenv_file: bool,
) -> tuple[dict[str, str], bool]:
    if environ is not None:
        return dict(environ), False

    loaded_dotenv = False
    if load_dotenv_file and _local_dotenv_may_load(os.environ):
        load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
        loaded_dotenv = True
    return dict(os.environ), loaded_dotenv


def _local_dotenv_may_load(environ: Mapping[str, str]) -> bool:
    raw_app_env = environ.get("APP_ENV")
    if raw_app_env and raw_app_env.strip().lower() in {
        AppEnvironment.PREVIEW.value,
        AppEnvironment.STAGING.value,
        AppEnvironment.PRODUCTION.value,
    }:
        return False
    return not _has_deployment_marker(environ)


def _parse_app_env(env: Mapping[str, str]) -> AppEnvironment:
    raw_value = env.get("APP_ENV")
    if raw_value is None:
        return AppEnvironment.CI if _parse_optional_ci(env) else AppEnvironment.LOCAL

    normalized = raw_value.strip().lower()
    if not normalized:
        _fail("APP_ENV", "must not be blank")

    try:
        return AppEnvironment(normalized)
    except ValueError:
        _fail("APP_ENV", "must be one of ci, local, preview, production, staging, or test")


def _validate_runtime_environment_source(
    env: Mapping[str, str],
    loaded_dotenv: bool,
    app_env: AppEnvironment,
) -> None:
    if loaded_dotenv and app_env.is_production_like:
        _fail("APP_ENV", "production-like environments must be supplied by deployed environment injection")
    if _has_deployment_marker(env) and not app_env.is_production_like:
        _fail("APP_ENV", "deployed runtimes must set preview, staging, or production explicitly")


def _parse_optional_ci(env: Mapping[str, str]) -> bool:
    raw_value = env.get("CI")
    if raw_value is None:
        return False
    return raw_value.strip().lower() not in FALSE_ENV_VALUES


def _parse_database_url(
    env: Mapping[str, str],
    app_env: AppEnvironment,
    *,
    name: str = "DATABASE_URL",
) -> str:
    database_url = _required_text(env, name)
    return _parse_database_url_value(name, database_url, app_env)


def _parse_database_url_value(
    name: str,
    database_url: str,
    app_env: AppEnvironment,
) -> str:
    if _is_documented_placeholder(database_url):
        _fail(name, "must not use a documented placeholder value")

    try:
        parsed = make_url(database_url)
    except ArgumentError:
        _fail(name, "must be a valid SQLAlchemy database URL")

    driver = parsed.drivername.lower()
    if driver not in {"postgresql", "postgresql+psycopg", "postgresql+psycopg2"}:
        _fail(name, "must use a PostgreSQL SQLAlchemy driver")
    if not parsed.database:
        _fail(name, "must include a database name")
    if not parsed.host:
        _fail(name, "must include a host")

    database_name = str(parsed.database)
    if app_env in {AppEnvironment.TEST, AppEnvironment.CI}:
        if database_name != DEDICATED_TEST_DATABASE_NAME:
            _fail(name, f"must use database {DEDICATED_TEST_DATABASE_NAME} in test and ci")
    elif app_env.is_production_like:
        if _is_local_host(parsed.host):
            _fail(name, "must not use localhost in production-like environments")
        lowered_name = database_name.lower()
        if any(
            part in lowered_name for part in _UNSAFE_PRODUCTION_LIKE_DB_NAME_PARTS
        ):
            _fail(name, "must not use a development, local, or test database name")
        if app_env is AppEnvironment.PRODUCTION and any(
            part in lowered_name for part in _UNSAFE_PRODUCTION_DB_NAME_PARTS
        ):
            _fail(name, "must not use a staging or preview database name")

    return database_url


def _parse_migration_database_url(
    env: Mapping[str, str],
    app_env: AppEnvironment,
) -> str:
    migration_database_url = _optional_text(env, "MIGRATION_DATABASE_URL")
    if migration_database_url is None:
        if app_env.is_production_like:
            _fail(
                "MIGRATION_DATABASE_URL",
                "is required for migrations in production-like environments",
            )
        return _parse_database_url(env, app_env)
    return _parse_database_url_value(
        "MIGRATION_DATABASE_URL",
        migration_database_url,
        app_env,
    )


def _parse_release_identity(env: Mapping[str, str]) -> str:
    for name in RELEASE_IDENTITY_ENV_NAMES:
        raw_value = env.get(name)
        if raw_value is None:
            continue
        value = raw_value.strip()
        if not value:
            continue
        if value != raw_value:
            _fail(name, "must not contain whitespace")
        if len(value) > _MAX_RELEASE_IDENTITY_LENGTH:
            _fail(name, "must be concise")
        if any(character.isspace() for character in value):
            _fail(name, "must not contain whitespace")
        if any(character in value for character in ("\x00", "/", "\\", "@", ":")):
            _fail(name, "must not contain sensitive or path-like characters")
        if name in SOURCE_REVISION_ENV_NAMES:
            if _is_full_git_commit_sha(value):
                return value.lower()
            _validate_release_identity_text(name, value)
            _fail(name, "must be a full Git commit SHA")
        _validate_release_identity_text(name, value)
        return value
    return DEFAULT_RELEASE_IDENTITY


def _is_full_git_commit_sha(value: str) -> bool:
    return (
        len(value) in _FULL_GIT_COMMIT_SHA_LENGTHS
        and bool(_FULL_GIT_COMMIT_SHA_RE.fullmatch(value))
    )


def _validate_release_identity_text(name: str, value: str) -> None:
    if contains_sensitive_text(value):
        _fail(name, "must not contain sensitive data")
    parsed = urlsplit(value)
    if parsed.scheme and parsed.netloc:
        _fail(name, "must not be a URL")


def _parse_allowed_hosts(env: Mapping[str, str], app_env: AppEnvironment) -> tuple[str, ...]:
    raw_value = _optional_text(env, "ALLOWED_HOSTS")
    if raw_value is None:
        if app_env.is_production_like:
            _fail("ALLOWED_HOSTS", "must be explicit in production-like environments")
        return DEFAULT_ALLOWED_HOSTS

    allowed_hosts: list[str] = []
    for raw_host in raw_value.split(","):
        host = _normalize_allowed_host(raw_host)
        if host == "*":
            _fail("ALLOWED_HOSTS", "must not use a global wildcard")
        if _is_documented_placeholder(host):
            _fail("ALLOWED_HOSTS", "must not use a documented placeholder value")
        if app_env.is_production_like and _is_local_host(host):
            _fail("ALLOWED_HOSTS", "must not include localhost in production-like environments")
        allowed_hosts.append(host)

    if not allowed_hosts:
        _fail("ALLOWED_HOSTS", "must not be empty")

    return tuple(dict.fromkeys(allowed_hosts))


def _normalize_allowed_host(raw_host: str) -> str:
    host = raw_host.strip().lower().rstrip(".")
    if not host:
        _fail("ALLOWED_HOSTS", "must not include blank hosts")
    if any(ord(character) < 32 or ord(character) == 127 for character in raw_host):
        _fail("ALLOWED_HOSTS", "must not contain control characters")
    if "://" in host or any(character in host for character in ("/", "?", "#", "@", "\\")):
        _fail("ALLOWED_HOSTS", "must contain host names only")
    if ":" in host:
        _fail("ALLOWED_HOSTS", "must not include ports")
    if host == "*":
        return host
    if len(host) > 253:
        _fail("ALLOWED_HOSTS", "must contain valid host names")

    labels = host.split(".")
    if not labels or any(not label for label in labels):
        _fail("ALLOWED_HOSTS", "must contain valid host names")
    if not all(_DNS_LABEL_RE.fullmatch(label) for label in labels):
        _fail("ALLOWED_HOSTS", "must contain valid host names")
    return host


def _parse_cors_origins(
    env: Mapping[str, str],
    app_env: AppEnvironment,
) -> tuple[str, ...]:
    raw_value = _optional_text(env, "CORS_ALLOWED_ORIGINS")
    if raw_value is None:
        if app_env.is_production_like:
            _fail("CORS_ALLOWED_ORIGINS", "must be explicit in production-like environments")
        return DEFAULT_CORS_ORIGINS

    origins: list[str] = []
    for raw_origin in raw_value.split(","):
        origin = raw_origin.strip().rstrip("/")
        if not origin:
            _fail("CORS_ALLOWED_ORIGINS", "must not include blank origins")
        if origin == "*":
            _fail("CORS_ALLOWED_ORIGINS", "must not use wildcard origins with credentials")
        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            _fail("CORS_ALLOWED_ORIGINS", "must contain valid http or https origins")
        if parsed.path or parsed.query or parsed.fragment:
            _fail("CORS_ALLOWED_ORIGINS", "must contain origins only, without paths or query strings")
        if app_env.is_production_like and _is_local_origin(parsed.hostname):
            _fail("CORS_ALLOWED_ORIGINS", "must not include localhost in production-like environments")
        origins.append(origin)

    return tuple(dict.fromkeys(origins))


def _parse_stripe_settings(
    env: Mapping[str, str],
    app_env: AppEnvironment,
) -> dict[str, object]:
    currency = (_optional_text(env, "STRIPE_CURRENCY") or SUPPORTED_STRIPE_CURRENCY).upper()
    if currency != SUPPORTED_STRIPE_CURRENCY:
        _fail("STRIPE_CURRENCY", f"must be {SUPPORTED_STRIPE_CURRENCY}")

    enabled = _parse_bool(env, "ENABLE_STRIPE_PAYMENTS", default=False)
    secret_key = _optional_text(env, "STRIPE_SECRET_KEY")
    publishable_key = _optional_text(env, "STRIPE_PUBLISHABLE_KEY")
    webhook_secret = _optional_text(env, "STRIPE_WEBHOOK_SECRET")

    if enabled:
        for name, value in (
            ("STRIPE_SECRET_KEY", secret_key),
            ("STRIPE_PUBLISHABLE_KEY", publishable_key),
            ("STRIPE_WEBHOOK_SECRET", webhook_secret),
        ):
            if not value:
                _fail(name, "is required when Stripe payments are enabled")

    if app_env.is_production_like:
        for name, value in (
            ("STRIPE_SECRET_KEY", secret_key),
            ("STRIPE_PUBLISHABLE_KEY", publishable_key),
            ("STRIPE_WEBHOOK_SECRET", webhook_secret),
        ):
            if value and _is_documented_placeholder(value):
                _fail(name, "must not use a documented placeholder value")

    return {
        "enable_stripe_payments": enabled,
        "stripe_secret_key": SecretStr(secret_key) if secret_key else None,
        "stripe_publishable_key": SecretStr(publishable_key) if publishable_key else None,
        "stripe_webhook_secret": SecretStr(webhook_secret) if webhook_secret else None,
        "stripe_currency": currency,
    }


def _empty_stripe_settings() -> dict[str, object]:
    return {
        "enable_stripe_payments": False,
        "stripe_secret_key": None,
        "stripe_publishable_key": None,
        "stripe_webhook_secret": None,
        "stripe_currency": SUPPORTED_STRIPE_CURRENCY,
    }


def _parse_firebase_admin_settings(
    env: Mapping[str, str],
    app_env: AppEnvironment,
) -> dict[str, object]:
    credentials_json = _optional_text(env, "FIREBASE_ADMIN_CREDENTIALS_JSON")
    credentials_path = _optional_text(env, "FIREBASE_ADMIN_CREDENTIALS")
    project_id = _optional_text(env, "FIREBASE_PROJECT_ID")

    if credentials_json:
        if app_env.is_production_like and _is_documented_placeholder(credentials_json):
            _fail("FIREBASE_ADMIN_CREDENTIALS_JSON", "must not use a documented placeholder value")
        try:
            parsed_credentials = json.loads(credentials_json)
        except json.JSONDecodeError:
            _fail("FIREBASE_ADMIN_CREDENTIALS_JSON", "must contain valid JSON")
        if not isinstance(parsed_credentials, dict):
            _fail("FIREBASE_ADMIN_CREDENTIALS_JSON", "must contain a JSON object")

    if credentials_path and app_env.is_production_like and _is_documented_placeholder(credentials_path):
        _fail("FIREBASE_ADMIN_CREDENTIALS", "must not use a documented placeholder value")
    if (
        credentials_path
        and app_env.is_production_like
        and not Path(credentials_path).is_file()
    ):
        _fail("FIREBASE_ADMIN_CREDENTIALS", "must point to a readable file")

    if app_env.is_production_like and not (credentials_json or credentials_path):
        _fail("FIREBASE_ADMIN_CREDENTIALS_JSON", "is required in production-like environments")

    if project_id:
        if app_env.is_production_like and _is_documented_placeholder(project_id):
            _fail("FIREBASE_PROJECT_ID", "must not use a documented placeholder value")
        if not _DNS_LABEL_RE.fullmatch(project_id):
            _fail("FIREBASE_PROJECT_ID", "must be a valid Firebase project id")
    elif app_env.is_production_like:
        _fail("FIREBASE_PROJECT_ID", "is required in production-like environments")

    return {
        "firebase_admin_credentials_json": SecretStr(credentials_json)
        if credentials_json
        else None,
        "firebase_admin_credentials": SecretStr(credentials_path) if credentials_path else None,
        "firebase_project_id": project_id,
    }


def _empty_firebase_settings() -> dict[str, object]:
    return {
        "firebase_admin_credentials_json": None,
        "firebase_admin_credentials": None,
        "firebase_project_id": None,
    }


def _parse_firebase_app_check_settings(
    env: Mapping[str, str],
    app_env: AppEnvironment,
) -> dict[str, object]:
    raw_mode = _optional_text(env, "FIREBASE_APP_CHECK_MODE")
    if raw_mode is None:
        if app_env.is_production_like:
            _fail("FIREBASE_APP_CHECK_MODE", "must be explicit in production-like environments")
        mode = FirebaseAppCheckMode.DISABLED
    else:
        try:
            mode = FirebaseAppCheckMode(raw_mode.lower())
        except ValueError:
            _fail("FIREBASE_APP_CHECK_MODE", "must be one of disabled, observe, or enforced")

    app_id = _optional_text(env, "FIREBASE_APP_CHECK_APP_ID")
    if mode.requires_app_id and not app_id:
        _fail("FIREBASE_APP_CHECK_APP_ID", "is required when Firebase App Check is observe or enforced")
    if app_id and app_env.is_production_like and _is_documented_placeholder(app_id):
        _fail("FIREBASE_APP_CHECK_APP_ID", "must not use a documented placeholder value")

    firebase_project_id = _optional_text(env, "FIREBASE_PROJECT_ID")
    if app_id and firebase_project_id and app_id == firebase_project_id:
        _fail("FIREBASE_APP_CHECK_APP_ID", "must be separate from FIREBASE_PROJECT_ID")

    return {
        "firebase_app_check_mode": mode,
        "firebase_app_check_app_id": app_id,
    }


def _empty_firebase_app_check_settings() -> dict[str, object]:
    return {
        "firebase_app_check_mode": FirebaseAppCheckMode.DISABLED,
        "firebase_app_check_app_id": None,
    }


def _parse_r2_settings(env: Mapping[str, str], app_env: AppEnvironment) -> dict[str, object]:
    account_id = _optional_text(env, "R2_ACCOUNT_ID")
    access_key_id = _optional_text(env, "R2_ACCESS_KEY_ID")
    secret_access_key = _optional_text(env, "R2_SECRET_ACCESS_KEY")
    bucket_name = _optional_text(env, "R2_BUCKET_NAME")
    endpoint_url = _optional_text(env, "R2_ENDPOINT_URL")

    supplied_values = [account_id, access_key_id, secret_access_key, bucket_name, endpoint_url]
    require_complete = app_env.is_production_like or any(value is not None for value in supplied_values)
    if require_complete:
        for name, value in (
            ("R2_ACCOUNT_ID", account_id),
            ("R2_ACCESS_KEY_ID", access_key_id),
            ("R2_SECRET_ACCESS_KEY", secret_access_key),
            ("R2_BUCKET_NAME", bucket_name),
        ):
            if not value:
                _fail(name, "is required when R2 storage is configured")
            if app_env.is_production_like and _is_documented_placeholder(value):
                _fail(name, "must not use a documented placeholder value")
        endpoint_url = endpoint_url or f"https://{account_id}.r2.cloudflarestorage.com"

    if endpoint_url:
        if app_env.is_production_like and _is_documented_placeholder(endpoint_url):
            _fail("R2_ENDPOINT_URL", "must not use a documented placeholder value")
        parsed_endpoint = urlsplit(endpoint_url)
        if parsed_endpoint.scheme != "https" or not parsed_endpoint.netloc:
            _fail("R2_ENDPOINT_URL", "must be a valid https URL")
        if parsed_endpoint.path not in {"", "/"} or parsed_endpoint.query or parsed_endpoint.fragment:
            _fail("R2_ENDPOINT_URL", "must not include paths, queries, or fragments")

    return {
        "r2_account_id": account_id,
        "r2_access_key_id": SecretStr(access_key_id) if access_key_id else None,
        "r2_secret_access_key": SecretStr(secret_access_key) if secret_access_key else None,
        "r2_bucket_name": bucket_name,
        "r2_endpoint_url": endpoint_url.rstrip("/") if endpoint_url else None,
        "r2_upload_url_minutes": _parse_positive_int(
            env, "R2_UPLOAD_URL_MINUTES", default=15
        ),
        "r2_read_url_minutes": _parse_positive_int(env, "R2_READ_URL_MINUTES", default=60),
        "r2_max_image_bytes": _parse_positive_int(
            env, "R2_MAX_IMAGE_BYTES", default=8 * 1024 * 1024
        ),
        "r2_allowed_image_types": _parse_image_types(env),
    }


def _empty_r2_settings() -> dict[str, object]:
    return {
        "r2_account_id": None,
        "r2_access_key_id": None,
        "r2_secret_access_key": None,
        "r2_bucket_name": None,
        "r2_endpoint_url": None,
        "r2_upload_url_minutes": 15,
        "r2_read_url_minutes": 60,
        "r2_max_image_bytes": 8 * 1024 * 1024,
        "r2_allowed_image_types": DEFAULT_R2_ALLOWED_IMAGE_TYPES,
    }


def _parse_timeout_settings(env: Mapping[str, str]) -> dict[str, int]:
    stripe_read_timeout_seconds = _parse_positive_int(
        env,
        "STRIPE_READ_TIMEOUT_SECONDS",
        default=DEFAULT_STRIPE_READ_TIMEOUT_SECONDS,
    )
    stripe_mutation_timeout_seconds = _parse_positive_int(
        env,
        "STRIPE_MUTATION_TIMEOUT_SECONDS",
        default=DEFAULT_STRIPE_MUTATION_TIMEOUT_SECONDS,
    )
    firebase_http_timeout_seconds = _parse_positive_int(
        env,
        "FIREBASE_HTTP_TIMEOUT_SECONDS",
        default=DEFAULT_FIREBASE_HTTP_TIMEOUT_SECONDS,
    )
    r2_metadata_connect_timeout_seconds = _parse_positive_int(
        env,
        "R2_METADATA_CONNECT_TIMEOUT_SECONDS",
        default=DEFAULT_R2_METADATA_CONNECT_TIMEOUT_SECONDS,
    )
    r2_metadata_read_timeout_seconds = _parse_positive_int(
        env,
        "R2_METADATA_READ_TIMEOUT_SECONDS",
        default=DEFAULT_R2_METADATA_READ_TIMEOUT_SECONDS,
    )
    db_pool_wait_timeout_seconds = _parse_positive_int(
        env,
        "DB_POOL_WAIT_TIMEOUT_SECONDS",
        default=DEFAULT_DB_POOL_WAIT_TIMEOUT_SECONDS,
    )
    db_statement_timeout_milliseconds = _parse_positive_int(
        env,
        "DB_STATEMENT_TIMEOUT_MILLISECONDS",
        default=DEFAULT_DB_STATEMENT_TIMEOUT_MILLISECONDS,
    )
    db_lock_timeout_milliseconds = _parse_positive_int(
        env,
        "DB_LOCK_TIMEOUT_MILLISECONDS",
        default=DEFAULT_DB_LOCK_TIMEOUT_MILLISECONDS,
    )

    if db_lock_timeout_milliseconds >= db_statement_timeout_milliseconds:
        _fail(
            "DB_LOCK_TIMEOUT_MILLISECONDS",
            "must be less than DB_STATEMENT_TIMEOUT_MILLISECONDS",
        )

    return {
        "stripe_read_timeout_seconds": stripe_read_timeout_seconds,
        "stripe_mutation_timeout_seconds": stripe_mutation_timeout_seconds,
        "firebase_http_timeout_seconds": firebase_http_timeout_seconds,
        "r2_metadata_connect_timeout_seconds": r2_metadata_connect_timeout_seconds,
        "r2_metadata_read_timeout_seconds": r2_metadata_read_timeout_seconds,
        "db_pool_wait_timeout_seconds": db_pool_wait_timeout_seconds,
        "db_statement_timeout_milliseconds": db_statement_timeout_milliseconds,
        "db_lock_timeout_milliseconds": db_lock_timeout_milliseconds,
    }


def _parse_database_pool_settings(
    env: Mapping[str, str],
    app_env: AppEnvironment,
) -> dict[str, int | None]:
    raw_pool_size = _optional_text(env, "DB_POOL_SIZE")
    raw_max_overflow = _optional_text(env, "DB_MAX_OVERFLOW")

    if raw_pool_size is None and raw_max_overflow is None:
        if app_env.is_production_like:
            _fail(
                "DB_POOL_SIZE",
                "and DB_MAX_OVERFLOW are required in production-like environments",
            )
        return {"db_pool_size": None, "db_max_overflow": None}

    if raw_pool_size is None:
        _fail("DB_POOL_SIZE", "is required when DB_MAX_OVERFLOW is set")
    if raw_max_overflow is None:
        _fail("DB_MAX_OVERFLOW", "is required when DB_POOL_SIZE is set")

    return {
        "db_pool_size": _parse_positive_int_value("DB_POOL_SIZE", raw_pool_size),
        "db_max_overflow": _parse_non_negative_int_value(
            "DB_MAX_OVERFLOW",
            raw_max_overflow,
        ),
    }


def _parse_inbox_token_secret(
    env: Mapping[str, str],
    app_env: AppEnvironment,
    database_url: str,
    validate_full: bool,
) -> str | None:
    token_secret = _optional_text(env, "INBOX_TOKEN_SECRET")
    if app_env.is_production_like and not token_secret and validate_full:
        _fail("INBOX_TOKEN_SECRET", "is required in production-like environments")
    if not token_secret:
        return None

    if token_secret == database_url:
        _fail("INBOX_TOKEN_SECRET", "must be independent from DATABASE_URL")

    for name in (
        "FIREBASE_ADMIN_CREDENTIALS_JSON",
        "FIREBASE_ADMIN_CREDENTIALS",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
    ):
        other_value = _optional_text(env, name)
        if other_value and token_secret == other_value:
            _fail("INBOX_TOKEN_SECRET", f"must be independent from {name}")

    if app_env.is_production_like and _is_documented_placeholder(token_secret):
        _fail("INBOX_TOKEN_SECRET", "must not use a documented placeholder value")

    return token_secret


def _parse_image_types(env: Mapping[str, str]) -> frozenset[str]:
    raw_value = _optional_text(env, "R2_ALLOWED_IMAGE_TYPES")
    if raw_value is None:
        return DEFAULT_R2_ALLOWED_IMAGE_TYPES

    image_types: set[str] = set()
    for raw_type in raw_value.split(","):
        image_type = raw_type.strip().lower()
        if not image_type:
            _fail("R2_ALLOWED_IMAGE_TYPES", "must not include blank image types")
        parts = image_type.split("/")
        if len(parts) != 2 or not all(parts):
            _fail("R2_ALLOWED_IMAGE_TYPES", "must contain MIME image types")
        if parts[0] != "image":
            _fail("R2_ALLOWED_IMAGE_TYPES", "must contain image MIME types only")
        image_types.add(image_type)
    return frozenset(image_types)


def _parse_bool(env: Mapping[str, str], name: str, *, default: bool) -> bool:
    raw_value = _optional_text(env, name)
    if raw_value is None:
        return default
    normalized = raw_value.lower()
    if normalized in TRUE_ENV_VALUES:
        return True
    if normalized in FALSE_ENV_VALUES:
        return False
    _fail(name, "must be a boolean value")


def _parse_positive_int(env: Mapping[str, str], name: str, *, default: int) -> int:
    raw_value = _optional_text(env, name)
    if raw_value is None:
        return default
    return _parse_positive_int_value(name, raw_value)


def _parse_positive_int_value(name: str, raw_value: str) -> int:
    try:
        parsed_value = int(raw_value)
    except ValueError:
        _fail(name, "must be an integer")
    if parsed_value <= 0:
        _fail(name, "must be greater than zero")
    return parsed_value


def _parse_non_negative_int_value(name: str, raw_value: str) -> int:
    try:
        parsed_value = int(raw_value)
    except ValueError:
        _fail(name, "must be an integer")
    if parsed_value < 0:
        _fail(name, "must be greater than or equal to zero")
    return parsed_value


def _optional_text(env: Mapping[str, str], name: str) -> str | None:
    if name not in env:
        return None
    value = env[name].strip()
    if not value:
        _fail(name, "must not be blank")
    return value


def _required_text(env: Mapping[str, str], name: str) -> str:
    value = _optional_text(env, name)
    if value is None:
        _fail(name, "is required")
    return value


def _secret_value(secret: SecretStr | None) -> str | None:
    return secret.get_secret_value() if secret else None


def _has_deployment_marker(env: Mapping[str, str]) -> bool:
    return any(_truthy_marker(env.get(name)) for name in DEPLOYMENT_MARKER_ENV_NAMES)


def _truthy_marker(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() not in {"", *FALSE_ENV_VALUES}


def _is_local_host(host: str | None) -> bool:
    if not host:
        return False
    return host.strip("[]").lower() in _LOCAL_HOSTNAMES


def _is_local_origin(host: str | None) -> bool:
    return _is_local_host(host)


def _is_documented_placeholder(value: str) -> bool:
    return value.strip() in DOCUMENTED_PLACEHOLDER_VALUES


def _fail(name: str, reason: str) -> None:
    raise SettingsError(f"{name}: {reason}")
