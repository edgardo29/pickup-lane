from __future__ import annotations

import pytest

from backend.settings import AppEnvironment

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]


def _unexpected_call(*args, **kwargs):
    del args, kwargs
    raise AssertionError("production refusal crossed a protected boundary")


def _set_production_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://synthetic:synthetic@db.example.invalid/pickuplane",
    )
    monkeypatch.setenv("DB_POOL_SIZE", "5")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "5")
    monkeypatch.setenv("DB_POOL_WAIT_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("DB_STATEMENT_TIMEOUT_MILLISECONDS", "12000")
    monkeypatch.setenv("DB_LOCK_TIMEOUT_MILLISECONDS", "2000")
    monkeypatch.delenv("CI", raising=False)


def test_bootstrap_admin_refuses_production_before_database_or_firebase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.scripts.bootstrap_admin as bootstrap

    _set_production_settings(monkeypatch)
    monkeypatch.setattr(bootstrap, "SessionLocal", _unexpected_call)
    monkeypatch.setattr(bootstrap, "verify_firebase_user", _unexpected_call)

    with pytest.raises(
        bootstrap.BootstrapAdminError,
        match=r"^Admin bootstrap is unavailable in production\.$",
    ):
        bootstrap.bootstrap_admin("admin@example.invalid")


def test_demo_seed_refuses_production_before_database_or_domain_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.scripts.seed_demo_browse as seed_demo

    _set_production_settings(monkeypatch)
    monkeypatch.setattr(seed_demo, "SessionLocal", _unexpected_call)
    monkeypatch.setattr(seed_demo, "seed_users", _unexpected_call)

    with pytest.raises(
        RuntimeError,
        match=r"^Demo data seeding is unavailable in production\.$",
    ):
        seed_demo.seed_demo_browse()


def test_importable_portfolio_runner_refuses_production_before_database_or_domain_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.scripts.portfolio_seed.runner as runner

    _set_production_settings(monkeypatch)
    monkeypatch.setattr(runner, "SessionLocal", _unexpected_call)
    monkeypatch.setattr(runner, "seed_users", _unexpected_call)

    with pytest.raises(
        RuntimeError,
        match=r"^Portfolio data seeding is unavailable in production\.$",
    ):
        runner.seed_portfolio_browse()


@pytest.mark.parametrize(
    ("module_name", "function_name"),
    [
        ("backend.scripts.bootstrap_admin", "bootstrap_admin"),
        ("backend.scripts.seed_demo_browse", "seed_demo_browse"),
        ("backend.scripts.portfolio_seed.runner", "seed_portfolio_browse"),
    ],
)
def test_mutation_tools_remain_available_outside_production(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    function_name: str,
) -> None:
    import importlib

    module = importlib.import_module(module_name)

    class _LocalSettings:
        app_env = AppEnvironment.LOCAL

    boundary_reached = False

    def session_boundary(*args, **kwargs):
        nonlocal boundary_reached
        del args, kwargs
        boundary_reached = True
        raise RuntimeError("test stopped at database boundary")

    monkeypatch.setattr(module, "build_settings", lambda **kwargs: _LocalSettings())
    monkeypatch.setattr(module, "SessionLocal", session_boundary)

    function = getattr(module, function_name)
    arguments = ("admin@example.invalid",) if function_name == "bootstrap_admin" else ()
    with pytest.raises(RuntimeError, match="test stopped at database boundary"):
        function(*arguments)

    assert boundary_reached is True
