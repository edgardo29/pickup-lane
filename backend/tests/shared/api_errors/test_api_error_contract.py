from __future__ import annotations

import logging
from pathlib import Path
import uuid

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, SecretStr
import pytest

from backend.main import create_app
from backend.observability.correlation import CORRELATION_ID_HEADER
from backend.routes import stripe_webhook_routes
from backend.settings import AppEnvironment, BackendSettings


pytestmark = pytest.mark.no_db_cleanup

ALLOWED_HOST = "api.example.test"
ALLOWED_ORIGIN = "https://frontend.example"
UNUSED_DATABASE_SETTING = "unused-by-no-db-api-error-tests"
PRIVATE_DIAGNOSTIC = "synthetic private diagnostic"


class ValidationProbePayload(BaseModel):
    count: int = Field(ge=1)
    label: str = Field(min_length=2)


def runtime_settings(
    *,
    allowed_hosts: tuple[str, ...] = (ALLOWED_HOST, "testserver"),
    cors_allowed_origins: tuple[str, ...] = (ALLOWED_ORIGIN,),
    enable_api_docs: bool = True,
    enable_db_health: bool = True,
) -> BackendSettings:
    return BackendSettings(
        app_env=AppEnvironment.TEST,
        database_url=SecretStr(UNUSED_DATABASE_SETTING),
        allowed_hosts=allowed_hosts,
        cors_allowed_origins=cors_allowed_origins,
        enable_api_docs=enable_api_docs,
        enable_db_health=enable_db_health,
        enable_stripe_payments=False,
    )


def build_error_test_app(*, static_dir: Path | None = None):
    app = create_app(settings=runtime_settings())
    if static_dir is not None:
        app.mount(
            "/_test-static",
            StaticFiles(directory=static_dir),
            name="test-static",
        )

    @app.get("/_test/items/{item_id}")
    def read_item(item_id: int):
        return {"item_id": item_id}

    @app.post("/_test/validation")
    def validation_probe(payload: ValidationProbePayload):
        return payload.model_dump()

    @app.get("/_test/unauthorized")
    def unauthorized():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.get("/_test/forbidden")
    def forbidden():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )

    @app.get("/_test/conflict")
    def conflict():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict detected.",
        )

    @app.get("/_test/unsafe-http-detail")
    def unsafe_http_detail():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PRIVATE_DIAGNOSTIC,
        )

    @app.get("/_test/unexpected")
    def unexpected():
        raise RuntimeError(PRIVATE_DIAGNOSTIC)

    @app.delete("/_test/no-content", status_code=status.HTTP_204_NO_CONTENT)
    def no_content():
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/_test/redirect")
    def redirect():
        return RedirectResponse("/live", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    return app


def host_headers(host: str = ALLOWED_HOST) -> dict[str, str]:
    return {"Host": host}


def origin_headers(origin: str = ALLOWED_ORIGIN) -> dict[str, str]:
    return {"Host": ALLOWED_HOST, "Origin": origin}


def assert_valid_correlation(correlation_id: str) -> None:
    parsed = uuid.UUID(correlation_id)
    assert parsed.version == 4
    assert str(parsed) == correlation_id


def assert_stable_error_response(response, *, code: str, status_code: int):
    assert response.status_code == status_code
    body = response.json()
    assert "detail" in body
    assert body["code"] == code
    assert isinstance(body["message"], str)
    assert body["message"]
    assert body["correlation_id"] == response.headers[CORRELATION_ID_HEADER]
    assert_valid_correlation(body["correlation_id"])
    return body


def test_request_validation_error_shape_preserves_safe_field_locations():
    app = build_error_test_app()

    with TestClient(app) as client:
        response = client.post(
            "/_test/validation",
            json={"count": "submitted-private-value", "label": "x"},
            headers=host_headers(),
        )

    body = assert_stable_error_response(
        response,
        code="API.VALIDATION_FAILED",
        status_code=422,
    )
    assert isinstance(body["detail"], list)
    assert any(error["loc"] == ["body", "count"] for error in body["detail"])
    assert any(error["loc"] == ["body", "label"] for error in body["detail"])
    assert all("input" not in error for error in body["detail"])
    assert all("ctx" not in error for error in body["detail"])
    assert "submitted-private-value" not in response.text
    assert body["details"]["field_errors"][0]["location"].startswith("body.")


def test_malformed_json_uses_distinct_stable_code_without_request_body():
    app = build_error_test_app()

    with TestClient(app) as client:
        response = client.post(
            "/_test/validation",
            content='{"count": ',
            headers={**host_headers(), "Content-Type": "application/json"},
        )

    body = assert_stable_error_response(
        response,
        code="API.MALFORMED_JSON",
        status_code=422,
    )
    assert body["message"] == "Malformed JSON request body."
    assert '{"count":' not in response.text
    assert all("ctx" not in error for error in body["detail"])


@pytest.mark.parametrize(
    ("path", "expected_status", "expected_code", "expected_detail"),
    [
        (
            "/_test/unauthorized",
            status.HTTP_401_UNAUTHORIZED,
            "AUTH.UNAUTHENTICATED",
            "Unauthorized",
        ),
        (
            "/_test/forbidden",
            status.HTTP_403_FORBIDDEN,
            "AUTH.FORBIDDEN",
            "Forbidden",
        ),
        (
            "/missing-route",
            status.HTTP_404_NOT_FOUND,
            "API.NOT_FOUND",
            "Not Found",
        ),
        (
            "/_test/conflict",
            status.HTTP_409_CONFLICT,
            "API.CONFLICT",
            "Conflict detected.",
        ),
    ],
)
def test_http_exception_shape_preserves_frontend_compatible_detail(
    path: str,
    expected_status: int,
    expected_code: str,
    expected_detail: str,
):
    app = build_error_test_app()

    with TestClient(app) as client:
        response = client.get(path, headers=host_headers())

    body = assert_stable_error_response(
        response,
        code=expected_code,
        status_code=expected_status,
    )
    assert body["detail"] == expected_detail
    assert body["message"] == expected_detail


def test_method_not_allowed_preserves_allow_header():
    app = build_error_test_app()

    with TestClient(app) as client:
        response = client.post("/_test/items/1", headers=host_headers())

    body = assert_stable_error_response(
        response,
        code="API.METHOD_NOT_ALLOWED",
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
    )
    assert body["detail"] == "Method Not Allowed"
    assert "GET" in response.headers["Allow"]


def test_authentication_error_preserves_safe_authenticate_header():
    app = build_error_test_app()

    with TestClient(app) as client:
        response = client.get("/_test/unauthorized", headers=host_headers())

    assert_stable_error_response(
        response,
        code="AUTH.UNAUTHENTICATED",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_unsafe_http_detail_is_redacted_without_internal_leakage(monkeypatch):
    monkeypatch.setattr(
        "backend.observability.http_errors.contains_sensitive_text",
        lambda value: value == PRIVATE_DIAGNOSTIC,
    )
    app = build_error_test_app()

    with TestClient(app) as client:
        response = client.get("/_test/unsafe-http-detail", headers=host_headers())

    body = assert_stable_error_response(
        response,
        code="API.SERVICE_UNAVAILABLE",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
    assert body["detail"] == "[REDACTED]"
    assert body["message"] == "Service unavailable."
    assert PRIVATE_DIAGNOSTIC not in response.text


def test_unexpected_exception_uses_generic_public_error_and_safe_log(caplog):
    app = build_error_test_app()

    with caplog.at_level(logging.ERROR, logger="backend.observability.http_errors"):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/_test/unexpected", headers=host_headers())

    body = assert_stable_error_response(
        response,
        code="API.UNEXPECTED",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    assert body["detail"] == "An unexpected error occurred."
    assert body["message"] == "Something went wrong. Please try again."
    assert PRIVATE_DIAGNOSTIC not in response.text
    assert PRIVATE_DIAGNOSTIC not in caplog.text
    assert "Unhandled application exception." in caplog.text


def test_valid_incoming_correlation_id_is_reused_in_error_response():
    app = build_error_test_app()
    incoming_correlation_id = str(uuid.uuid4())

    with TestClient(app) as client:
        response = client.get(
            "/missing-route",
            headers={**host_headers(), CORRELATION_ID_HEADER: incoming_correlation_id},
        )

    body = assert_stable_error_response(
        response,
        code="API.NOT_FOUND",
        status_code=status.HTTP_404_NOT_FOUND,
    )
    assert body["correlation_id"] == incoming_correlation_id


def test_invalid_incoming_correlation_id_is_not_reflected():
    app = build_error_test_app()

    with TestClient(app) as client:
        response = client.get(
            "/missing-route",
            headers={**host_headers(), CORRELATION_ID_HEADER: "user@example.com"},
        )

    body = assert_stable_error_response(
        response,
        code="API.NOT_FOUND",
        status_code=status.HTTP_404_NOT_FOUND,
    )
    assert body["correlation_id"] != "user@example.com"
    assert "user@example.com" not in response.text


def test_cors_and_security_headers_are_preserved_on_application_errors():
    app = build_error_test_app()

    with TestClient(app) as client:
        response = client.get("/missing-route", headers=origin_headers())

    assert_stable_error_response(
        response,
        code="API.NOT_FOUND",
        status_code=status.HTTP_404_NOT_FOUND,
    )
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"


def test_host_validation_remains_middleware_owned_and_enforced():
    app = build_error_test_app()

    with TestClient(app) as client:
        response = client.get(
            "/missing-route",
            headers=host_headers("unexpected.example.test"),
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "code" not in response.text
    assert ALLOWED_HOST not in response.text
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"


def test_health_docs_static_redirect_and_no_content_responses_keep_existing_shapes(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr("backend.main.check_database_connection", lambda: True)
    (tmp_path / "asset.txt").write_text("static-body\n")
    app = build_error_test_app(static_dir=tmp_path)

    with TestClient(app) as client:
        live_response = client.get("/live", headers=host_headers())
        ready_response = client.get("/ready", headers=host_headers())
        schema_response = client.get("/openapi.json", headers=host_headers())
        docs_response = client.get("/docs", headers=host_headers())
        static_response = client.get("/_test-static/asset.txt", headers=host_headers())
        no_content_response = client.delete("/_test/no-content", headers=host_headers())
        redirect_response = client.get(
            "/_test/redirect",
            headers=host_headers(),
            follow_redirects=False,
        )

    assert live_response.json()["status"] == "live"
    assert ready_response.json()["status"] == "ready"
    assert "detail" not in live_response.json()
    assert "openapi" in schema_response.json()
    assert "detail" not in schema_response.json()
    assert docs_response.status_code == status.HTTP_200_OK
    assert static_response.status_code == status.HTTP_200_OK
    assert static_response.text == "static-body\n"
    assert no_content_response.status_code == status.HTTP_204_NO_CONTENT
    assert no_content_response.content == b""
    assert redirect_response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert redirect_response.headers["location"] == "/live"


def test_stripe_webhook_raw_body_handling_remains_unchanged(monkeypatch):
    app = build_error_test_app()
    captured: dict[str, object] = {}

    def fake_construct_webhook_event(payload: bytes, stripe_signature: str):
        captured["payload"] = payload
        captured["signature"] = stripe_signature
        return {"id": "evt_synthetic", "type": "synthetic.event", "data": {}}

    def fake_record_and_process_stripe_webhook_event(db, stripe_event):
        del db
        captured["event"] = stripe_event
        return {"status": "processed"}

    monkeypatch.setattr(
        stripe_webhook_routes,
        "construct_webhook_event",
        fake_construct_webhook_event,
    )
    monkeypatch.setattr(
        stripe_webhook_routes,
        "record_and_process_stripe_webhook_event",
        fake_record_and_process_stripe_webhook_event,
    )

    with TestClient(app) as client:
        response = client.post(
            "/stripe/webhook",
            content=b'{"type":"synthetic.event"}',
            headers={**host_headers(), "Stripe-Signature": "synthetic-signature"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "processed"}
    assert captured["payload"] == b'{"type":"synthetic.event"}'
    assert captured["signature"] == "synthetic-signature"
    assert captured["event"] == {
        "id": "evt_synthetic",
        "type": "synthetic.event",
        "data": {},
    }
