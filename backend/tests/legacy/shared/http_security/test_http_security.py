from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Response, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest

import backend.firebase_admin_client as firebase_admin_client
from backend.main import create_app
import backend.main as main_module
import backend.services.r2_storage_service as r2_storage_service
import backend.services.stripe_service as stripe_service
from backend.settings import (
    AppEnvironment,
    BackendSettings,
    DEFAULT_ALLOWED_HOSTS,
    SettingsError,
    build_settings,
)


pytestmark = pytest.mark.no_db_cleanup

ALLOWED_HOST = "api.example.test"
ALLOWED_ORIGIN = "https://frontend.example"
DISALLOWED_ORIGIN = "https://frontend.example.evil"
DATABASE_URL_SCHEME = "postgresql://"
TEST_DATABASE_URL = DATABASE_URL_SCHEME + "localhost/pickup_lane_test_db"
PRODUCTION_DATABASE_URL = DATABASE_URL_SCHEME + "db.example.test/pickup_lane"


def backend_test_env(**overrides: str | None) -> dict[str, str]:
    return clean_env(
        {
            "APP_ENV": "test",
            "DATABASE_URL": TEST_DATABASE_URL,
            "INBOX_TOKEN_SECRET": "synthetic-independent-inbox-token",
            **overrides,
        }
    )


def production_like_env(**overrides: str | None) -> dict[str, str]:
    return clean_env(
        {
            "APP_ENV": "production",
            "DATABASE_URL": PRODUCTION_DATABASE_URL,
            "INBOX_TOKEN_SECRET": "synthetic-independent-inbox-token",
            "FIREBASE_ADMIN_CREDENTIALS_JSON": (
                '{"type":"service_account","project_id":"synthetic-project"}'
            ),
            "ALLOWED_HOSTS": ALLOWED_HOST,
            "CORS_ALLOWED_ORIGINS": ALLOWED_ORIGIN,
            "ENABLE_API_DOCS": "false",
            "ENABLE_DB_HEALTH": "false",
            "R2_ACCOUNT_ID": "synthetic-account",
            "R2_ACCESS_KEY_ID": "synthetic-access-id",
            "R2_SECRET_ACCESS_KEY": "synthetic-storage-credential",
            "R2_BUCKET_NAME": "synthetic-media",
            **overrides,
        }
    )


def clean_env(values: dict[str, str | None]) -> dict[str, str]:
    return {key: value for key, value in values.items() if value is not None}


def runtime_settings(
    *,
    app_env: AppEnvironment = AppEnvironment.TEST,
    allowed_hosts: tuple[str, ...] = (ALLOWED_HOST, "testserver"),
    cors_allowed_origins: tuple[str, ...] = (ALLOWED_ORIGIN,),
    enable_api_docs: bool = True,
    enable_db_health: bool = True,
) -> BackendSettings:
    return BackendSettings(
        app_env=app_env,
        database_url=SecretStr(TEST_DATABASE_URL),
        allowed_hosts=allowed_hosts,
        cors_allowed_origins=cors_allowed_origins,
        enable_api_docs=enable_api_docs,
        enable_db_health=enable_db_health,
        enable_stripe_payments=False,
    )


def build_test_app(
    *,
    tmp_path: Path | None = None,
    settings: BackendSettings | None = None,
):
    app = create_app(settings=settings or runtime_settings())

    @app.get("/_test/explicit-cache")
    def explicit_cache(response: Response):
        response.headers["Cache-Control"] = "private, max-age=60"
        return {"status": "explicit"}

    @app.get("/_test/redirect")
    def redirect():
        return RedirectResponse("/live", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    @app.delete("/_test/no-content", status_code=status.HTTP_204_NO_CONTENT)
    def no_content():
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/_test/unauthorized")
    def unauthorized():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    @app.get("/_test/forbidden")
    def forbidden():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    @app.post("/_test/webhook-response")
    def webhook_response():
        return JSONResponse({"accepted": True}, status_code=status.HTTP_202_ACCEPTED)

    @app.get("/_test/server-error")
    def controlled_server_error():
        return JSONResponse(
            {"detail": "temporary failure"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if tmp_path is not None:
        file_path = tmp_path / "download.txt"
        file_path.write_text("download-body\n")

        @app.get("/_test/file")
        def file_response():
            return FileResponse(file_path, media_type="text/plain")

    return app


def host_headers(host: str = ALLOWED_HOST) -> dict[str, str]:
    return {"Host": host}


def origin_headers(origin: str = ALLOWED_ORIGIN) -> dict[str, str]:
    return {"Host": ALLOWED_HOST, "Origin": origin}


def preflight_headers(origin: str = ALLOWED_ORIGIN) -> dict[str, str]:
    return {
        "Host": ALLOWED_HOST,
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Authorization, Content-Type",
    }


def assert_api_security_headers(response):
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"


def test_local_and_test_host_defaults_remain_usable():
    local_settings = build_settings(backend_test_env(APP_ENV="local", ALLOWED_HOSTS=None))
    test_settings = build_settings(backend_test_env(ALLOWED_HOSTS=None))

    assert local_settings.allowed_hosts == DEFAULT_ALLOWED_HOSTS
    assert test_settings.allowed_hosts == DEFAULT_ALLOWED_HOSTS


def test_allowed_hosts_normalize_case_and_trailing_dot():
    settings = build_settings(
        backend_test_env(ALLOWED_HOSTS=" API.EXAMPLE.TEST. , api.example.test ")
    )

    assert settings.allowed_hosts == (ALLOWED_HOST,)


def test_production_like_host_configuration_is_required():
    with pytest.raises(SettingsError, match="ALLOWED_HOSTS"):
        build_settings(production_like_env(ALLOWED_HOSTS=None))


def test_production_like_global_wildcard_host_is_rejected():
    with pytest.raises(SettingsError, match="ALLOWED_HOSTS"):
        build_settings(production_like_env(ALLOWED_HOSTS="*"))


def test_documented_allowed_host_placeholder_is_rejected():
    with pytest.raises(SettingsError, match="ALLOWED_HOSTS"):
        build_settings(backend_test_env(ALLOWED_HOSTS="replace-with-api-hosts"))


@pytest.mark.parametrize(
    "allowed_hosts",
    [
        "https://api.example.test",
        "api.example.test/path",
        "api.example.test?debug=true",
        "api.example.test#fragment",
        "user@api.example.test",
        "api.example.test:443",
        "bad host.example",
        "bad_host.example",
        "-bad.example",
        "bad-.example",
        "api..example.test",
        "api.example.test,\nother.example.test",
        "api.example.test,,other.example.test",
    ],
)
def test_malformed_allowed_host_entries_are_rejected(allowed_hosts: str):
    with pytest.raises(SettingsError, match="ALLOWED_HOSTS"):
        build_settings(backend_test_env(ALLOWED_HOSTS=allowed_hosts))


def test_valid_host_is_accepted(monkeypatch):
    monkeypatch.setattr(main_module, "check_database_connection", lambda: True)
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/live", headers=host_headers())

    assert response.status_code == 200
    assert response.json()["status"] == "live"


@pytest.mark.parametrize("host", ["unexpected.example.test", "bad_host.example"])
def test_invalid_and_malformed_hosts_are_rejected_without_allowlist_disclosure(host):
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/live", headers=host_headers(host))

    assert response.status_code == 400
    assert ALLOWED_HOST not in response.text
    assert_api_security_headers(response)


@pytest.mark.parametrize("path", ["/live", "/ready", "/db-health", "/docs", "/"])
def test_host_validation_applies_to_health_docs_and_api_routes(monkeypatch, path):
    monkeypatch.setattr(main_module, "check_database_connection", lambda: True)
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get(path, headers=host_headers("unexpected.example.test"))

    assert response.status_code == 400
    assert ALLOWED_HOST not in response.text


def test_allowed_cors_simple_request_receives_exact_origin_and_credentials(monkeypatch):
    monkeypatch.setattr(main_module, "check_database_connection", lambda: True)
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/live", headers=origin_headers())

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert "Origin" in response.headers["Vary"]


@pytest.mark.parametrize(
    "origin",
    [
        DISALLOWED_ORIGIN,
        "https://evil-frontend.example",
        "https://frontend.example/path",
        "https://FRONTEND.example",
        "https://fr0ntend.example",
    ],
)
def test_disallowed_cors_simple_request_does_not_receive_allow_origin(origin):
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/live", headers=origin_headers(origin))

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


def test_null_origin_is_not_implicitly_allowed():
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/live", headers=origin_headers("null"))

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


def test_allowed_credentialed_preflight_succeeds():
    app = build_test_app()

    with TestClient(app) as client:
        response = client.options("/games", headers=preflight_headers())

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert "Authorization" in response.headers["Access-Control-Allow-Headers"]
    assert "Origin" in response.headers["Vary"]


def test_disallowed_preflight_fails_safely():
    app = build_test_app()

    with TestClient(app) as client:
        response = client.options("/games", headers=preflight_headers(DISALLOWED_ORIGIN))

    assert response.status_code == 400
    assert "Access-Control-Allow-Origin" not in response.headers


def test_wildcard_cors_origin_remains_rejected_for_credentialed_production_like_config():
    with pytest.raises(SettingsError, match="CORS_ALLOWED_ORIGINS"):
        build_settings(production_like_env(CORS_ALLOWED_ORIGINS="*"))


def test_cors_headers_are_present_on_controlled_application_errors():
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/missing-route", headers=origin_headers())

    assert response.status_code == 404
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert_api_security_headers(response)


def test_api_json_security_headers_are_applied():
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/", headers=host_headers())

    assert response.status_code == 200
    assert response.json() == {"message": "Backend is running"}
    assert_api_security_headers(response)


def test_validation_error_security_headers_are_applied():
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/games/not-a-uuid", headers=host_headers())

    assert response.status_code == 422
    assert_api_security_headers(response)


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [
        ("/_test/unauthorized", status.HTTP_401_UNAUTHORIZED),
        ("/_test/forbidden", status.HTTP_403_FORBIDDEN),
        ("/_test/server-error", status.HTTP_500_INTERNAL_SERVER_ERROR),
    ],
)
def test_auth_and_controlled_error_security_headers_are_applied(
    path: str,
    expected_status: int,
):
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get(path, headers=host_headers())

    assert response.status_code == expected_status
    assert_api_security_headers(response)


def test_not_found_security_headers_are_applied():
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/missing-route", headers=host_headers())

    assert response.status_code == 404
    assert_api_security_headers(response)


def test_webhook_response_security_headers_are_applied():
    app = build_test_app()

    with TestClient(app) as client:
        synthetic_response = client.post("/_test/webhook-response", headers=host_headers())
        real_error_response = client.post("/stripe/webhook", headers=host_headers())

    assert synthetic_response.status_code == 202
    assert_api_security_headers(synthetic_response)
    assert real_error_response.status_code == 400
    assert_api_security_headers(real_error_response)


def test_health_security_headers_preserve_ws02_02_contracts(monkeypatch):
    probe_calls = 0

    def successful_database_probe():
        nonlocal probe_calls
        probe_calls += 1
        return True

    monkeypatch.setattr(main_module, "check_database_connection", successful_database_probe)
    app = build_test_app()

    with TestClient(app) as client:
        live_response = client.get("/live", headers=host_headers())
        ready_response = client.get("/ready", headers=host_headers())
        db_health_response = client.get("/db-health", headers=host_headers())

    assert probe_calls == 2
    assert live_response.json()["status"] == "live"
    assert ready_response.json()["status"] == "ready"
    assert db_health_response.json() == {"message": "Database connection is working"}
    for response in (live_response, ready_response, db_health_response):
        assert response.status_code == 200
        assert_api_security_headers(response)


def test_ready_remains_recoverable_and_hides_database_details(monkeypatch):
    results = iter([RuntimeError("private database diagnostic"), True])

    def flaky_database_probe():
        result = next(results)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(main_module, "check_database_connection", flaky_database_probe)
    app = build_test_app()

    with TestClient(app) as client:
        failed_response = client.get("/ready", headers=host_headers())
        recovered_response = client.get("/ready", headers=host_headers())

    assert failed_response.status_code == 503
    assert failed_response.json()["status"] == "not_ready"
    assert "private database diagnostic" not in failed_response.text
    assert_api_security_headers(failed_response)
    assert recovered_response.status_code == 200
    assert recovered_response.json()["status"] == "ready"
    assert_api_security_headers(recovered_response)


def test_documentation_html_security_headers_are_applied_when_enabled():
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/docs", headers=host_headers())

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Content-Security-Policy"] == "frame-ancestors 'none'"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "camera=()" in response.headers["Permissions-Policy"]


def test_openapi_json_security_headers_are_applied_without_html_csp():
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/openapi.json", headers=host_headers())

    assert response.status_code == 200
    assert_api_security_headers(response)
    assert "Content-Security-Policy" not in response.headers
    assert "X-Frame-Options" not in response.headers


def test_documentation_remains_unavailable_in_production_like_configuration():
    app = build_test_app(
        settings=runtime_settings(
            app_env=AppEnvironment.PRODUCTION,
            enable_api_docs=False,
            enable_db_health=False,
        )
    )

    with TestClient(app) as client:
        docs_response = client.get("/docs", headers=host_headers())
        schema_response = client.get("/openapi.json", headers=host_headers())

    assert docs_response.status_code == 404
    assert schema_response.status_code == 404
    assert_api_security_headers(docs_response)
    assert_api_security_headers(schema_response)


def test_explicit_route_cache_policy_is_not_overwritten():
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/_test/explicit-cache", headers=host_headers())

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, max-age=60"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_redirect_file_and_no_content_behaviors_are_not_corrupted(tmp_path):
    app = build_test_app(tmp_path=tmp_path)

    with TestClient(app) as client:
        redirect_response = client.get(
            "/_test/redirect",
            headers=host_headers(),
            follow_redirects=False,
        )
        no_content_response = client.delete("/_test/no-content", headers=host_headers())
        file_response = client.get("/_test/file", headers=host_headers())

    assert redirect_response.status_code == 307
    assert redirect_response.headers["location"] == "/live"
    assert "Cache-Control" not in redirect_response.headers
    assert no_content_response.status_code == 204
    assert no_content_response.content == b""
    assert no_content_response.headers["Cache-Control"] == "no-store"
    assert file_response.status_code == 200
    assert file_response.text == "download-body\n"
    assert "Cache-Control" not in file_response.headers


def test_application_import_and_lifespan_remain_provider_network_free(monkeypatch):
    provider_calls: list[str] = []

    def fail_provider_call(provider_name: str):
        def wrapped(*_args, **_kwargs):
            provider_calls.append(provider_name)
            raise AssertionError(f"{provider_name} must not initialize during app startup")

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
    monkeypatch.setattr(main_module, "check_database_connection", lambda: True)

    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/live", headers=host_headers())

    assert response.status_code == 200
    assert provider_calls == []
