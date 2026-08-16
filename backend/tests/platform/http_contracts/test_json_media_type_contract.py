from __future__ import annotations

import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.settings import build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
_ALLOWED_ORIGIN = "https://app.example.invalid"
_CHAT_BODY = {
    "chat_id": "00000000-0000-4000-8000-000000000001",
    "message_body": "synthetic message",
}


def _settings_env(**overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": "test",
        "DATABASE_URL": _TEST_DATABASE_URL,
        "INBOX_TOKEN_SECRET": "synthetic-independent-http-contract-token",
        "ALLOWED_HOSTS": "testserver,api.example.invalid",
        "CORS_ALLOWED_ORIGINS": _ALLOWED_ORIGIN,
        "ENABLE_API_DOCS": "true",
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


def _install_chat_probe(app, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    import backend.routes.chat_message_routes as route_module

    calls: list[str] = []

    def current_user():
        calls.append("auth")
        return object()

    def db():
        calls.append("db")
        return object()

    def create_chat_message_record(db, chat_message, current_user):
        del db, chat_message, current_user
        calls.append("service")
        raise HTTPException(status_code=418, detail="chat route reached")

    app.dependency_overrides[route_module.require_verified_user] = current_user
    app.dependency_overrides[route_module.get_db] = db
    monkeypatch.setattr(
        route_module,
        "create_chat_message_record",
        create_chat_message_record,
    )
    return calls


def _post_chat(
    client: TestClient,
    *,
    content: bytes | None = None,
    content_type: str | None = "application/json",
    extra_headers: dict[str, str] | None = None,
):
    headers = {"Host": "testserver", **(extra_headers or {})}
    if content_type is not None:
        headers["Content-Type"] = content_type
    return client.post(
        "/chat-messages",
        headers=headers,
        content=content if content is not None else json.dumps(_CHAT_BODY).encode(),
    )


@pytest.mark.requirement("WS02-05A-R1")
@pytest.mark.parametrize(
    "content_type",
    [
        "application/json",
        "application/json; charset=utf-8",
        "application/vnd.pickup-lane.chat+json",
    ],
)
def test_ordinary_json_route_accepts_json_compatible_media_types(
    monkeypatch: pytest.MonkeyPatch,
    content_type: str,
) -> None:
    app = _create_app(monkeypatch)
    calls = _install_chat_probe(app, monkeypatch)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = _post_chat(client, content_type=content_type)

    assert response.status_code == 418
    assert response.json()["detail"] == "chat route reached"
    assert calls == ["auth", "db", "service"]


@pytest.mark.requirement("WS02-05A-R1")
def test_missing_content_type_remains_validation_behavior_not_media_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)
    calls = _install_chat_probe(app, monkeypatch)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = _post_chat(client, content_type=None)

    assert response.status_code == 422
    assert response.json()["code"] == "API.VALIDATION_FAILED"
    assert calls == ["auth", "db"]


@pytest.mark.requirement("WS02-05A-R1")
def test_explicit_non_json_media_rejects_before_route_business_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)
    calls = _install_chat_probe(app, monkeypatch)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = _post_chat(client, content_type="text/plain")

    assert response.status_code == 415
    assert response.json()["code"] == "API.UNSUPPORTED_MEDIA_TYPE"
    assert calls == []


@pytest.mark.requirement("WS02-05A-R1")
def test_malformed_json_keeps_validation_behavior_not_media_type_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)
    calls = _install_chat_probe(app, monkeypatch)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = _post_chat(
            client,
            content=b'{"chat_id": "00000000-0000-4000-8000-000000000001"',
            content_type="application/json",
        )

    assert response.status_code == 422
    assert response.json()["code"] == "API.MALFORMED_JSON"
    assert response.json()["message"] == "Malformed JSON request body."
    assert calls == []


@pytest.mark.requirement("WS02-05A-R1")
def test_signed_stripe_webhook_raw_body_is_outside_ordinary_json_media_enforcement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.routes.stripe_webhook_routes as route_module

    app = _create_app(monkeypatch)
    observed: dict[str, object] = {}
    app.dependency_overrides[route_module.get_db] = lambda: "synthetic-db"

    def construct_webhook_event(payload: bytes, signature: str) -> dict[str, object]:
        observed["payload"] = payload
        observed["signature"] = signature
        return {"id": "evt_synthetic", "type": "payment_intent.succeeded"}

    def record_and_process_stripe_webhook_event(db, stripe_event):
        observed["db"] = db
        observed["event"] = stripe_event
        return {"received": True, "duplicate": False}

    monkeypatch.setattr(route_module, "construct_webhook_event", construct_webhook_event)
    monkeypatch.setattr(
        route_module,
        "record_and_process_stripe_webhook_event",
        record_and_process_stripe_webhook_event,
    )

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.post(
            "/stripe/webhook",
            headers={
                "Host": "testserver",
                "Stripe-Signature": "safe-signature",
                "Content-Type": "text/plain",
            },
            content=b"raw-provider-body",
        )

    assert response.status_code == 200
    assert observed == {
        "payload": b"raw-provider-body",
        "signature": "safe-signature",
        "db": "synthetic-db",
        "event": {"id": "evt_synthetic", "type": "payment_intent.succeeded"},
    }


@pytest.mark.requirement("WS02-05A-R1", "WS02-05A-R6")
def test_bodyless_tombstone_route_is_outside_ordinary_json_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.routes.venue_routes as route_module

    app = _create_app(monkeypatch)
    calls: list[str] = []
    app.dependency_overrides[route_module.require_active_admin] = lambda: calls.append("admin") or object()

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.post(
            "/venues",
            headers={"Host": "testserver", "Content-Type": "text/plain"},
            content=b"not-json",
        )

    assert response.status_code == 410
    assert response.json()["code"] == "API.HTTP_ERROR"
    assert calls == ["admin"]


@pytest.mark.requirement("WS02-05A-R1")
@pytest.mark.parametrize(
    ("content", "extra_headers", "expected_status", "expected_code"),
    [
        (
            json.dumps(_CHAT_BODY).encode(),
            {"Content-Encoding": "gzip"},
            415,
            "API.UNSUPPORTED_CONTENT_ENCODING",
        ),
        (
            b'{"message_body":"' + b"x" * 70_000 + b'"}',
            {},
            413,
            "API.REQUEST_BODY_TOO_LARGE",
        ),
    ],
)
def test_body_limit_and_content_encoding_remain_distinct_from_media_type_contract(
    monkeypatch: pytest.MonkeyPatch,
    content: bytes,
    extra_headers: dict[str, str],
    expected_status: int,
    expected_code: str,
) -> None:
    app = _create_app(monkeypatch)
    calls = _install_chat_probe(app, monkeypatch)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = _post_chat(
            client,
            content=content,
            content_type="application/json",
            extra_headers=extra_headers,
        )

    assert response.status_code == expected_status
    assert response.json()["code"] == expected_code
    assert calls == []
