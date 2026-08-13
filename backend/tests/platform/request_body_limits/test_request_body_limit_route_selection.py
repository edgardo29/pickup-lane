from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.settings import build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
_ALLOWED_ORIGIN = "https://app.example.invalid"
_VALID_PLATFORM_NOTICE_BODY = {
    "idempotency_key": "synthetic-key-123",
    "title": "Synthetic title",
    "message": "Synthetic message",
    "audience_type": "selected_users",
    "selected_user_ids": ["00000000-0000-4000-8000-000000000001"],
}


def _settings_env(**overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": "test",
        "DATABASE_URL": _TEST_DATABASE_URL,
        "INBOX_TOKEN_SECRET": "synthetic-independent-request-limit-token",
        "ALLOWED_HOSTS": "testserver,api.example.invalid",
        "CORS_ALLOWED_ORIGINS": _ALLOWED_ORIGIN,
        "ENABLE_API_DOCS": "false",
        "ENABLE_DB_HEALTH": "false",
        "ENABLE_STRIPE_PAYMENTS": "false",
    }
    for name, value in overrides.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def _create_app(monkeypatch: pytest.MonkeyPatch, **overrides: str | None):
    for name, value in _settings_env(**overrides).items():
        monkeypatch.setenv(name, value)
    reset_settings_cache()

    import backend.main as main_module

    settings = build_settings(
        _settings_env(**overrides),
        load_dotenv_file=False,
        validate_full=True,
    )
    return main_module.create_app(settings)


def _post_json(client: TestClient, path: str, body: dict[str, Any], **headers: str):
    return client.post(
        path,
        headers={"Host": "testserver", "Content-Type": "application/json", **headers},
        content=json.dumps(body, separators=(",", ":")),
    )


@pytest.mark.requirement("WS02-04B2A1-R1", "WS02-04B2A1-R7")
@pytest.mark.parametrize("path", ["/admin/platform-notices", "/admin/platform-notices/"])
def test_platform_notice_create_uses_special_limit_before_downstream_work(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    app = _create_app(monkeypatch, PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES="16")

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = _post_json(client, path, {"message": "x" * 64})

    assert response.status_code == 413
    assert response.json()["code"] == "API.REQUEST_BODY_TOO_LARGE"


@pytest.mark.requirement("WS02-04B2A1-R1", "WS02-04B2A1-R7")
def test_platform_notice_under_limit_reaches_normal_downstream_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.routes.platform_notice_routes as route_module

    calls: list[object] = []
    app = _create_app(monkeypatch, PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES="512")
    app.dependency_overrides[route_module.require_recent_active_admin] = lambda: object()
    app.dependency_overrides[route_module.get_db] = lambda: object()

    def fake_create_platform_notice(db, *, creator_user, payload):
        del db, creator_user
        calls.append(payload)
        raise HTTPException(status_code=418, detail="platform notice service reached")

    monkeypatch.setattr(route_module, "create_platform_notice", fake_create_platform_notice)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = _post_json(client, "/admin/platform-notices", _VALID_PLATFORM_NOTICE_BODY)

    assert response.status_code == 418
    assert response.json()["detail"] == "platform notice service reached"
    assert len(calls) == 1


@pytest.mark.requirement("WS02-04B2A1-R1", "WS02-04B2A1-R7")
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/admin/platform-notices"),
        ("GET", "/admin/platform-notices/00000000-0000-4000-8000-000000000001"),
        ("GET", "/admin/platform-notices/00000000-0000-4000-8000-000000000001/recipients"),
        ("POST", "/admin/platform-notices/00000000-0000-4000-8000-000000000001/cancel"),
    ],
)
def test_nearby_platform_notice_routes_are_not_platform_notice_create_class(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
) -> None:
    app = _create_app(monkeypatch, PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES="16")

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.request(
            method,
            path,
            headers={"Host": "testserver", "Content-Type": "application/json"},
            content=b'{"cancellation_reason":"body longer than sixteen bytes"}',
        )

    assert response.status_code != 413


@pytest.mark.requirement("WS02-04B2A1-R2", "WS02-04B2A1-R7")
def test_signed_stripe_webhook_preserves_raw_bytes_to_construction_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.routes.stripe_webhook_routes as route_module

    raw_body = b'{"id":"evt_synthetic","type":"payment_intent.succeeded"}'
    observed: dict[str, object] = {}
    app = _create_app(monkeypatch)
    app.dependency_overrides[route_module.get_db] = lambda: "synthetic-db"

    def fake_construct_webhook_event(payload: bytes, signature: str) -> dict[str, object]:
        observed["payload"] = payload
        observed["signature"] = signature
        return {"id": "evt_synthetic", "type": "payment_intent.succeeded"}

    def fake_record_and_process_stripe_webhook_event(db, stripe_event):
        observed["db"] = db
        observed["event"] = stripe_event
        return {"received": True, "duplicate": False}

    monkeypatch.setattr(route_module, "construct_webhook_event", fake_construct_webhook_event)
    monkeypatch.setattr(
        route_module,
        "record_and_process_stripe_webhook_event",
        fake_record_and_process_stripe_webhook_event,
    )

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.post(
            "/stripe/webhook",
            headers={"Host": "testserver", "Stripe-Signature": "safe-signature"},
            content=raw_body,
        )

    assert response.status_code == 200
    assert observed["payload"] == raw_body
    assert observed["signature"] == "safe-signature"
    assert observed["db"] == "synthetic-db"


@pytest.mark.requirement("WS02-04B2A1-R2", "WS02-04B2A1-R7")
def test_signed_stripe_over_limit_rejects_before_provider_or_business_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.routes.stripe_webhook_routes as route_module

    calls: list[str] = []
    app = _create_app(monkeypatch, STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES="16")
    app.dependency_overrides[route_module.get_db] = lambda: calls.append("db")

    monkeypatch.setattr(
        route_module,
        "construct_webhook_event",
        lambda payload, signature: calls.append("construct"),
    )
    monkeypatch.setattr(
        route_module,
        "record_and_process_stripe_webhook_event",
        lambda db, stripe_event: calls.append("process"),
    )

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.post(
            "/stripe/webhook",
            headers={"Host": "testserver", "Stripe-Signature": "safe-signature"},
            content=b"x" * 64,
        )

    assert response.status_code == 413
    assert response.json()["code"] == "API.REQUEST_BODY_TOO_LARGE"
    assert calls == []


@pytest.mark.requirement("WS02-04B2A1-R7")
def test_missing_stripe_signature_remains_route_owned_not_signed_limit_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.routes.stripe_webhook_routes as route_module

    calls: list[str] = []
    app = _create_app(monkeypatch, STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES="16")
    app.dependency_overrides[route_module.get_db] = lambda: object()
    monkeypatch.setattr(
        route_module,
        "construct_webhook_event",
        lambda payload, signature: calls.append("construct"),
    )

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.post(
            "/stripe/webhook",
            headers={"Host": "testserver"},
            content=b"x" * 64,
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing Stripe-Signature header."
    assert calls == []


@pytest.mark.requirement("WS02-04B2A1-R7")
def test_special_class_selection_precedence_is_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _create_app(monkeypatch)

    request_body_middleware = [
        middleware
        for middleware in app.user_middleware
        if middleware.cls.__name__ == "RequestBodyLimitMiddleware"
    ]
    assert len(request_body_middleware) == 1
    ordinary_routes = request_body_middleware[0].kwargs["ordinary_json_body_routes"]

    ordinary_paths = {route.path for route in ordinary_routes}
    assert "/admin/platform-notices" not in ordinary_paths
    assert "/stripe/webhook" not in ordinary_paths
