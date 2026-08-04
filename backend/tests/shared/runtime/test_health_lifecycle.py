from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest

import backend.firebase_admin_client as firebase_admin_client
from backend.main import create_app
import backend.main as main_module
import backend.services.r2_storage_service as r2_storage_service
import backend.services.stripe_service as stripe_service
from backend.settings import AppEnvironment, BackendSettings


pytestmark = pytest.mark.no_db_cleanup


def runtime_settings(
    *,
    enable_db_health: bool = True,
    release_identity: str = "ws02-02-test-release",
) -> BackendSettings:
    return BackendSettings(
        app_env=AppEnvironment.TEST,
        release_identity=release_identity,
        database_url=SecretStr("postgresql://localhost/pickup_lane_test_db"),
        cors_allowed_origins=("http://localhost:5173",),
        enable_api_docs=True,
        enable_db_health=enable_db_health,
        enable_stripe_payments=False,
    )


def test_live_returns_200_without_executing_database_query(monkeypatch):
    def fail_database_probe():
        raise AssertionError("liveness must not query the database")

    monkeypatch.setattr(main_module, "check_database_connection", fail_database_probe)
    app = create_app(settings=runtime_settings())

    with TestClient(app) as client:
        response = client.get("/live")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {
        "status": "live",
        "release": "ws02-02-test-release",
    }


def test_ready_returns_200_when_lifecycle_is_active_and_database_probe_succeeds(
    monkeypatch,
):
    probe_calls = 0

    def successful_database_probe():
        nonlocal probe_calls
        probe_calls += 1
        return True

    monkeypatch.setattr(main_module, "check_database_connection", successful_database_probe)
    app = create_app(settings=runtime_settings(release_identity="runtime-test-sha"))

    with TestClient(app) as client:
        response = client.get("/ready")

    assert probe_calls == 1
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {
        "status": "ready",
        "release": "runtime-test-sha",
    }


def test_ready_returns_503_when_lifecycle_is_inactive(monkeypatch):
    database_probe_called = False

    def successful_database_probe():
        nonlocal database_probe_called
        database_probe_called = True
        return True

    monkeypatch.setattr(main_module, "check_database_connection", successful_database_probe)
    app = create_app(settings=runtime_settings())
    client = TestClient(app)

    try:
        response = client.get("/ready")
    finally:
        client.close()

    assert database_probe_called is False
    assert response.status_code == 503
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {
        "status": "not_ready",
        "release": "ws02-02-test-release",
    }


def test_ready_returns_503_without_exposing_database_exception_details(monkeypatch):
    def failing_database_probe():
        raise RuntimeError("internal database diagnostic should stay private")

    monkeypatch.setattr(main_module, "check_database_connection", failing_database_probe)
    app = create_app(settings=runtime_settings())

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {
        "status": "not_ready",
        "release": "ws02-02-test-release",
    }
    assert "internal database diagnostic" not in response.text


def test_ready_recovers_after_previous_failed_probe(monkeypatch):
    results = iter([RuntimeError("temporary database failure"), True])

    def flaky_database_probe():
        result = next(results)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(main_module, "check_database_connection", flaky_database_probe)
    app = create_app(settings=runtime_settings())

    with TestClient(app) as client:
        failed_response = client.get("/ready")
        recovered_response = client.get("/ready")

    assert failed_response.status_code == 503
    assert failed_response.json()["status"] == "not_ready"
    assert recovered_response.status_code == 200
    assert recovered_response.json()["status"] == "ready"


def test_release_identity_is_present_and_non_sensitive(monkeypatch):
    monkeypatch.setattr(main_module, "check_database_connection", lambda: True)
    app = create_app(settings=runtime_settings(release_identity="commit.abc123"))

    with TestClient(app) as client:
        live_response = client.get("/live")
        ready_response = client.get("/ready")

    for response in (live_response, ready_response):
        body = response.json()
        assert body["release"] == "commit.abc123"
        assert set(body) == {"status", "release"}


def test_db_health_remains_disabled_when_setting_is_false(monkeypatch):
    monkeypatch.setattr(main_module, "check_database_connection", lambda: True)
    app = create_app(settings=runtime_settings(enable_db_health=False))

    with TestClient(app) as client:
        response = client.get("/db-health")

    assert response.status_code == 404


def test_enabled_db_health_uses_no_store_cache_header(monkeypatch):
    monkeypatch.setattr(main_module, "check_database_connection", lambda: True)
    app = create_app(settings=runtime_settings(enable_db_health=True))

    with TestClient(app) as client:
        response = client.get("/db-health")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {"message": "Database connection is working"}


def test_enabled_db_health_hides_database_exception_details(monkeypatch):
    def failing_database_probe():
        raise RuntimeError("private database diagnostic")

    monkeypatch.setattr(main_module, "check_database_connection", failing_database_probe)
    app = create_app(settings=runtime_settings(enable_db_health=True))

    with TestClient(app) as client:
        response = client.get("/db-health")

    assert response.status_code == 503
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {"message": "Database connection is unavailable"}
    assert "private database diagnostic" not in response.text


def test_application_shutdown_disposes_database_engine(monkeypatch):
    dispose_calls = 0

    def dispose_database_engine():
        nonlocal dispose_calls
        dispose_calls += 1

    monkeypatch.setattr(main_module, "dispose_database_engine", dispose_database_engine)
    app = create_app(settings=runtime_settings())

    with TestClient(app):
        assert dispose_calls == 0

    assert dispose_calls == 1


def test_lifespan_does_not_initialize_optional_provider_clients(monkeypatch):
    provider_calls: list[str] = []

    def fail_provider_call(provider_name: str):
        def wrapped(*_args, **_kwargs):
            provider_calls.append(provider_name)
            raise AssertionError(f"{provider_name} must not be initialized by app lifespan")

        return wrapped

    monkeypatch.setattr(
        firebase_admin_client,
        "initialize_firebase_admin",
        fail_provider_call("firebase"),
    )
    monkeypatch.setattr(
        stripe_service,
        "get_stripe_module",
        fail_provider_call("stripe"),
    )
    monkeypatch.setattr(
        r2_storage_service,
        "get_r2_client",
        fail_provider_call("r2"),
    )

    app = create_app(settings=runtime_settings())

    with TestClient(app) as client:
        response = client.get("/live")

    assert response.status_code == 200
    assert provider_calls == []
