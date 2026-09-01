from __future__ import annotations

import asyncio
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType

import pytest

from backend.settings import (
    BACKEND_ENVIRONMENT_VARIABLES,
    SettingsError,
    build_settings,
    get_migration_database_url,
    reset_settings_cache,
)

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_FRONTEND_ROOT = _REPO_ROOT / "frontend"
_TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
_PRODUCTION_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_prod"
_MIGRATION_DATABASE_URL = (
    "postgresql+psycopg://migration-db.example.invalid:5432/pickup_lane_prod"
)
_DATABASE_ENV_NAMES = frozenset(
    {
        "DATABASE_URL",
        "MIGRATION_DATABASE_URL",
        "DB_POOL_SIZE",
        "DB_MAX_OVERFLOW",
        "DB_POOL_WAIT_TIMEOUT_SECONDS",
        "DB_STATEMENT_TIMEOUT_MILLISECONDS",
        "DB_LOCK_TIMEOUT_MILLISECONDS",
    }
)
_FRONTEND_IGNORED_PARTS = frozenset(
    {"node_modules", "dist", "build", ".vite", "coverage"}
)
_FRONTEND_TEXT_SUFFIXES = frozenset(
    {".css", ".env", ".example", ".html", ".js", ".json", ".jsx", ".md", ".ts", ".tsx"}
)


def _settings_env(
    app_env: str = "test",
    **overrides: str | None,
) -> dict[str, str]:
    database_url = (
        _TEST_DATABASE_URL if app_env in {"test", "ci"} else _PRODUCTION_DATABASE_URL
    )
    env = {
        "APP_ENV": app_env,
        "DATABASE_URL": database_url,
        "DB_POOL_WAIT_TIMEOUT_SECONDS": "2",
        "DB_STATEMENT_TIMEOUT_MILLISECONDS": "12000",
        "DB_LOCK_TIMEOUT_MILLISECONDS": "2000",
    }
    for name, value in overrides.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def _build(
    app_env: str = "test",
    **overrides: str | None,
):
    return build_settings(
        _settings_env(app_env, **overrides),
        load_dotenv_file=False,
        validate_full=False,
    )


def _assert_settings_rejected(
    app_env: str,
    *,
    mentions: tuple[str, ...],
    does_not_echo: tuple[str, ...] = (),
    **overrides: str | None,
) -> str:
    with pytest.raises(SettingsError) as exc_info:
        _build(app_env, **overrides)

    message = str(exc_info.value)
    for fragment in mentions:
        assert fragment in message
    for private_value in does_not_echo:
        assert private_value not in message
    return message


def _install_environment(
    monkeypatch: pytest.MonkeyPatch,
    env: Mapping[str, str],
) -> None:
    monkeypatch.setattr("backend.settings.load_dotenv", lambda *_args, **_kwargs: False)
    for name in (
        "APP_ENV",
        "CI",
        "DATABASE_URL",
        "MIGRATION_DATABASE_URL",
        "DB_POOL_SIZE",
        "DB_MAX_OVERFLOW",
        "DB_POOL_WAIT_TIMEOUT_SECONDS",
        "DB_STATEMENT_TIMEOUT_MILLISECONDS",
        "DB_LOCK_TIMEOUT_MILLISECONDS",
        "RENDER",
        "RENDER_SERVICE_ID",
        "RENDER_SERVICE_NAME",
        "VERCEL",
        "VERCEL_ENV",
    ):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    reset_settings_cache()


def _reload_database_module(
    monkeypatch: pytest.MonkeyPatch,
    env: Mapping[str, str],
) -> ModuleType:
    _install_environment(monkeypatch, env)
    sys.modules.pop("backend.database", None)

    import backend.database as database

    return database


def _dispose_database_module(database: ModuleType) -> None:
    database.dispose_database_engine()
    sys.modules.pop("backend.database", None)
    reset_settings_cache()


def _drop_module_tree(prefix: str) -> None:
    for module_name in list(sys.modules):
        if module_name == prefix or module_name.startswith(f"{prefix}."):
            del sys.modules[module_name]


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


@pytest.mark.requirement("WS04-01A-R1")
@pytest.mark.parametrize("app_env", ["preview", "staging", "production"])
def test_production_like_runtime_requires_explicit_pool_configuration(
    app_env: str,
) -> None:
    _assert_settings_rejected(
        app_env,
        mentions=("DB_POOL_SIZE", "DB_MAX_OVERFLOW"),
        does_not_echo=(_PRODUCTION_DATABASE_URL,),
    )

    _assert_settings_rejected(
        app_env,
        DB_POOL_SIZE="5",
        mentions=("DB_MAX_OVERFLOW",),
        does_not_echo=(_PRODUCTION_DATABASE_URL,),
    )
    _assert_settings_rejected(
        app_env,
        DB_MAX_OVERFLOW="2",
        mentions=("DB_POOL_SIZE",),
        does_not_echo=(_PRODUCTION_DATABASE_URL,),
    )

    settings = _build(app_env, DB_POOL_SIZE="5", DB_MAX_OVERFLOW="0")

    assert settings.db_pool_size == 5
    assert settings.db_max_overflow == 0


@pytest.mark.requirement("WS04-01A-R1")
@pytest.mark.parametrize("app_env", ["local", "test", "ci"])
def test_local_test_and_ci_may_omit_or_supply_pool_configuration(
    app_env: str,
) -> None:
    omitted_settings = _build(app_env)

    assert omitted_settings.db_pool_size is None
    assert omitted_settings.db_max_overflow is None

    supplied_settings = _build(app_env, DB_POOL_SIZE="3", DB_MAX_OVERFLOW="1")

    assert supplied_settings.db_pool_size == 3
    assert supplied_settings.db_max_overflow == 1


@pytest.mark.requirement("WS04-01A-R1")
@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        ("DB_POOL_SIZE", "0", "greater than zero"),
        ("DB_POOL_SIZE", "-1", "greater than zero"),
        ("DB_POOL_SIZE", "not-an-int", "integer"),
        ("DB_MAX_OVERFLOW", "-1", "greater than or equal to zero"),
        ("DB_MAX_OVERFLOW", "not-an-int", "integer"),
    ],
)
def test_pool_configuration_rejects_invalid_values(
    name: str,
    value: str,
    expected: str,
) -> None:
    overrides = {"DB_POOL_SIZE": "3", "DB_MAX_OVERFLOW": "1", name: value}

    _assert_settings_rejected(
        "test",
        mentions=(name, expected),
        **overrides,
    )


@pytest.mark.requirement("WS04-01A-R1", "WS04-01A-R5")
def test_application_settings_do_not_require_migration_database_url() -> None:
    settings = _build(
        "production",
        DB_POOL_SIZE="5",
        DB_MAX_OVERFLOW="2",
        MIGRATION_DATABASE_URL=None,
    )

    assert settings.database_url_value == _PRODUCTION_DATABASE_URL
    assert settings.db_pool_size == 5
    assert settings.db_max_overflow == 2


@pytest.mark.requirement("WS04-01A-R5")
@pytest.mark.parametrize("app_env", ["preview", "staging", "production"])
def test_production_like_migrations_require_migration_database_url(
    monkeypatch: pytest.MonkeyPatch,
    app_env: str,
) -> None:
    _install_environment(monkeypatch, _settings_env(app_env))

    with pytest.raises(SettingsError) as exc_info:
        get_migration_database_url()

    assert "MIGRATION_DATABASE_URL" in str(exc_info.value)
    assert _PRODUCTION_DATABASE_URL not in str(exc_info.value)


@pytest.mark.requirement("WS04-01A-R5")
@pytest.mark.parametrize("app_env", ["local", "test", "ci"])
def test_non_production_migrations_may_fall_back_to_application_database_url(
    monkeypatch: pytest.MonkeyPatch,
    app_env: str,
) -> None:
    env = _settings_env(app_env)
    _install_environment(monkeypatch, env)

    assert get_migration_database_url() == env["DATABASE_URL"]


@pytest.mark.requirement("WS04-01A-R5")
def test_migration_database_url_is_validated_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_environment(
        monkeypatch,
        _settings_env(
            "production",
            MIGRATION_DATABASE_URL="sqlite:///pickup_lane_prod",
        ),
    )

    with pytest.raises(SettingsError) as exc_info:
        get_migration_database_url()

    message = str(exc_info.value)
    assert "MIGRATION_DATABASE_URL" in message
    assert "PostgreSQL" in message
    assert "sqlite:///pickup_lane_prod" not in message

    _install_environment(
        monkeypatch,
        _settings_env(
            "production",
            MIGRATION_DATABASE_URL=_MIGRATION_DATABASE_URL,
        ),
    )

    assert get_migration_database_url() == _MIGRATION_DATABASE_URL


@pytest.mark.requirement("WS04-01A-R2", "WS04-01A-R4")
def test_application_engine_uses_configured_pool_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = _reload_database_module(
        monkeypatch,
        _settings_env(
            "test",
            DB_POOL_SIZE="3",
            DB_MAX_OVERFLOW="1",
            DB_POOL_WAIT_TIMEOUT_SECONDS="4",
        ),
    )
    try:
        assert database.DATABASE_POOL_SETTINGS.pool_size == 3
        assert database.DATABASE_POOL_SETTINGS.max_overflow == 1
        assert database.engine.pool.size() == 3
        assert getattr(database.engine.pool, "_max_overflow") == 1
        assert getattr(database.engine.pool, "_timeout") == 4
        assert database.engine.pool.checkedout() == 0
    finally:
        _dispose_database_module(database)


@pytest.mark.requirement("WS04-01A-R1", "WS04-01A-R2")
def test_non_production_engine_keeps_optional_pool_values_optional(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = _reload_database_module(monkeypatch, _settings_env("test"))
    try:
        assert database.DATABASE_POOL_SETTINGS.pool_size is None
        assert database.DATABASE_POOL_SETTINGS.max_overflow is None
        assert database.engine.pool.checkedout() == 0
    finally:
        _dispose_database_module(database)


class _FakeSession:
    def __init__(self) -> None:
        self.rollback_calls = 0
        self.close_calls = 0

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.close_calls += 1


@pytest.mark.requirement("WS04-01A-R3")
def test_request_session_closes_after_success_without_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = _reload_database_module(monkeypatch, _settings_env("test"))
    fake_session = _FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: fake_session)
    try:
        generator = database.get_db()
        assert next(generator) is fake_session

        with pytest.raises(StopIteration):
            next(generator)

        assert fake_session.rollback_calls == 0
        assert fake_session.close_calls == 1
    finally:
        _dispose_database_module(database)


@pytest.mark.requirement("WS04-01A-R3")
def test_request_session_rolls_back_ordinary_exceptions_and_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = _reload_database_module(monkeypatch, _settings_env("test"))
    fake_session = _FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: fake_session)
    try:
        generator = database.get_db()
        assert next(generator) is fake_session

        with pytest.raises(RuntimeError, match="synthetic failure"):
            generator.throw(RuntimeError("synthetic failure"))

        assert fake_session.rollback_calls == 1
        assert fake_session.close_calls == 1
    finally:
        _dispose_database_module(database)


@pytest.mark.requirement("WS04-01A-R3", "WS04-01A-R4")
def test_request_session_closes_on_cancellation_without_reclassification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.observability.timeouts import database_timeout_from_exception

    database = _reload_database_module(monkeypatch, _settings_env("test"))
    fake_session = _FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: fake_session)
    try:
        generator = database.get_db()
        assert next(generator) is fake_session
        cancellation = asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError) as exc_info:
            generator.throw(cancellation)

        assert exc_info.value is cancellation
        assert fake_session.rollback_calls == 0
        assert fake_session.close_calls == 1
        assert database_timeout_from_exception(cancellation) is None
    finally:
        _dispose_database_module(database)


@pytest.mark.requirement("WS04-01A-R4")
def test_database_health_failure_response_remains_generic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.main as main_module
    from fastapi.testclient import TestClient

    private_error = "database failed at private-db.example.invalid"

    def failing_database_ready() -> bool:
        raise RuntimeError(private_error)

    settings = build_settings(
        {
            "APP_ENV": "test",
            "DATABASE_URL": _TEST_DATABASE_URL,
            "ALLOWED_HOSTS": "testserver",
            "CORS_ALLOWED_ORIGINS": "http://testserver",
            "ENABLE_API_DOCS": "false",
            "ENABLE_DB_HEALTH": "true",
            "ENABLE_STRIPE_PAYMENTS": "false",
        },
        load_dotenv_file=False,
        validate_full=True,
    )
    monkeypatch.setattr(main_module, "check_database_connection", failing_database_ready)

    with TestClient(main_module.create_app(settings)) as client:
        ready_response = client.get("/ready")
        db_health_response = client.get("/db-health")

    assert ready_response.status_code == 503
    assert ready_response.json()["status"] == "not_ready"
    assert db_health_response.status_code == 503
    assert db_health_response.json() == {
        "message": "Database connection is unavailable"
    }

    for response in (ready_response, db_health_response):
        assert private_error not in response.text
        assert "DATABASE_URL" not in response.text
        assert "pickup_lane_test_db" not in response.text


@pytest.mark.requirement("WS04-01A-R4")
def test_application_shutdown_disposes_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    database = _reload_database_module(monkeypatch, _settings_env("test"))
    try:
        dispose_calls: list[str] = []
        monkeypatch.setattr(database.engine, "dispose", lambda: dispose_calls.append("disposed"))

        database.dispose_database_engine()

        assert dispose_calls == ["disposed"]
    finally:
        _dispose_database_module(database)


@pytest.mark.requirement("WS04-01A-R5", "WS04-01A-R6")
def test_alembic_uses_migration_configuration_metadata_path_and_nullpool() -> None:
    source = (_BACKEND_ROOT / "alembic" / "env.py").read_text()

    assert "from backend.database import" not in source
    assert "from backend.database_metadata import Base" in source
    assert "get_migration_database_url" in source
    assert "import backend.models" in source
    assert "pool.NullPool" in source
    assert "MIGRATION_DATABASE_URL" in source


@pytest.mark.requirement("WS04-01A-R6")
def test_model_metadata_loads_complete_model_set_without_application_engine() -> None:
    _drop_module_tree("backend.models")
    sys.modules.pop("backend.database", None)
    sys.modules.pop("backend.database_metadata", None)

    import backend.database_metadata as metadata_module
    import backend.models as models

    assert "backend.database" not in sys.modules

    exported_model_tables = {
        model_class.__tablename__
        for name in models.__all__
        for model_class in (getattr(models, name),)
        if isinstance(model_class, type)
        and issubclass(model_class, metadata_module.Base)
        and model_class is not metadata_module.Base
    }

    assert len(exported_model_tables) >= 50
    assert exported_model_tables <= set(metadata_module.Base.metadata.tables)
    assert {"users", "games", "payments", "refunds"} <= set(
        metadata_module.Base.metadata.tables
    )


@pytest.mark.requirement("WS04-01A-R7")
def test_database_configuration_names_remain_backend_only_and_sanitized() -> None:
    example = (_BACKEND_ROOT / ".env.example").read_text()

    assert _DATABASE_ENV_NAMES <= BACKEND_ENVIRONMENT_VARIABLES
    for name in _DATABASE_ENV_NAMES:
        assert name in example

    assert "postgresql://" not in example
    assert "postgresql+" not in example
    assert "replace-with-migration-postgresql-url" in example

    frontend_hits: dict[str, list[str]] = {}
    for name in _DATABASE_ENV_NAMES:
        hits = [
            str(path.relative_to(_REPO_ROOT))
            for path in _frontend_text_files()
            if name in path.read_text(errors="ignore")
        ]
        if hits:
            frontend_hits[name] = hits

    assert frontend_hits == {}
