from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import status
from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest

from backend.main import create_app
import backend.main as main_module
from backend.observability.correlation import CORRELATION_ID_HEADER
from backend.observability.request_body_limits import (
    DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES,
    DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES,
    DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES,
    PLATFORM_NOTICE_CREATE_PATH,
    REQUEST_BODY_TOO_LARGE_CODE,
    STRIPE_WEBHOOK_PATH,
    UNSUPPORTED_CONTENT_ENCODING_CODE,
    RequestBodyLimitMiddleware,
    RequestBodyLimitRoute,
)
from backend.routes import stripe_webhook_routes
from backend.settings import AppEnvironment, BackendSettings


pytestmark = pytest.mark.no_db_cleanup

ALLOWED_HOST = "api.example.test"
ALLOWED_ORIGIN = "https://frontend.example"
UNUSED_DATABASE_SETTING = "unused-by-request-body-limit-tests"


@dataclass(frozen=True)
class AsgiResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes
    receive_calls: int

    def json(self) -> dict[str, Any]:
        return json.loads(self.body.decode("utf-8"))


class RecordingBodyApp:
    def __init__(self) -> None:
        self.bodies: list[bytes] = []
        self.calls = 0
        self.mutations = 0

    async def __call__(self, scope, receive, send) -> None:
        del scope
        self.calls += 1
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break

        self.bodies.append(bytes(body))
        self.mutations += 1
        await send(
            {
                "type": "http.response.start",
                "status": status.HTTP_200_OK,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b'{"status":"accepted"}',
                "more_body": False,
            }
        )


def runtime_settings() -> BackendSettings:
    return BackendSettings(
        app_env=AppEnvironment.TEST,
        database_url=SecretStr(UNUSED_DATABASE_SETTING),
        allowed_hosts=(ALLOWED_HOST, "testserver"),
        cors_allowed_origins=(ALLOWED_ORIGIN,),
        enable_api_docs=True,
        enable_db_health=True,
        enable_stripe_payments=False,
    )


def ordinary_route(path: str = "/ordinary-json") -> RequestBodyLimitRoute:
    return RequestBodyLimitRoute(
        path=path,
        methods=frozenset({"POST"}),
        path_regex=re.compile(f"^{re.escape(path)}$"),
    )


def limited_app(
    inner_app: RecordingBodyApp,
    *,
    ordinary_json_body_routes: tuple[RequestBodyLimitRoute, ...] = (),
) -> RequestBodyLimitMiddleware:
    return RequestBodyLimitMiddleware(
        inner_app,
        ordinary_json_request_body_limit_bytes=(
            DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES
        ),
        ordinary_json_body_routes=ordinary_json_body_routes,
        platform_notice_request_body_limit_bytes=(
            DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES
        ),
        stripe_webhook_request_body_limit_bytes=(
            DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES
        ),
    )


def host_headers() -> list[tuple[str, str]]:
    return [("Host", ALLOWED_HOST)]


def stripe_headers() -> list[tuple[str, str]]:
    return [("Host", ALLOWED_HOST), ("Stripe-Signature", "synthetic-signature")]


def invoke_asgi(
    app,
    *,
    method: str,
    path: str,
    chunks: list[bytes] | None = None,
    headers: list[tuple[str, str]] | None = None,
) -> AsgiResponse:
    return asyncio.run(
        _invoke_asgi(
            app,
            method=method,
            path=path,
            chunks=chunks or [b""],
            headers=headers or host_headers(),
        )
    )


async def _invoke_asgi(
    app,
    *,
    method: str,
    path: str,
    chunks: list[bytes],
    headers: list[tuple[str, str]],
) -> AsgiResponse:
    sent_messages: list[dict[str, Any]] = []
    receive_calls = 0
    receive_messages = [
        {
            "type": "http.request",
            "body": chunk,
            "more_body": index < len(chunks) - 1,
        }
        for index, chunk in enumerate(chunks)
    ]
    raw_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in headers
    ]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": path,
        "raw_path": path.encode("ascii"),
        "root_path": "",
        "query_string": b"",
        "headers": raw_headers,
        "client": ("127.0.0.1", 10000),
        "server": (ALLOWED_HOST, 443),
        "state": {},
    }

    async def receive() -> dict[str, Any]:
        nonlocal receive_calls
        receive_calls += 1
        if receive_messages:
            return receive_messages.pop(0)
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    await app(scope, receive, send)

    start_message = next(
        message
        for message in sent_messages
        if message["type"] == "http.response.start"
    )
    body = b"".join(
        message.get("body", b"")
        for message in sent_messages
        if message["type"] == "http.response.body"
    )
    response_headers = {
        name.decode("latin-1").lower(): value.decode("latin-1")
        for name, value in start_message.get("headers", [])
    }
    return AsgiResponse(
        status_code=start_message["status"],
        headers=response_headers,
        body=body,
        receive_calls=receive_calls,
    )


def test_app_registers_retained_ordinary_body_routes_from_fastapi_metadata():
    app = create_app(settings=runtime_settings())
    middleware = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls is RequestBodyLimitMiddleware
    )
    ordinary_routes = middleware.kwargs["ordinary_json_body_routes"]
    route_keys = {
        (method, route.path)
        for route in ordinary_routes
        for method in route.methods
    }

    assert len(route_keys) == 81
    assert ("PATCH", "/users/me") in route_keys
    assert ("POST", "/games/{game_id}/join") in route_keys
    assert ("POST", "/admin/platform-notices") not in route_keys
    assert ("POST", STRIPE_WEBHOOK_PATH) not in route_keys
    assert all(method not in {"GET", "HEAD", "OPTIONS"} for method, _ in route_keys)


@pytest.mark.parametrize(
    "body_size",
    [
        DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES - 1,
        DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES,
    ],
)
def test_ordinary_json_route_class_accepts_body_at_or_below_limit(body_size: int):
    inner_app = RecordingBodyApp()
    body = b"x" * body_size

    response = invoke_asgi(
        limited_app(inner_app, ordinary_json_body_routes=(ordinary_route(),)),
        method="POST",
        path="/ordinary-json",
        chunks=[body],
        headers=[
            *host_headers(),
            ("Content-Length", str(body_size)),
            ("Content-Type", "application/json"),
        ],
    )

    assert response.status_code == status.HTTP_200_OK
    assert inner_app.bodies == [body]
    assert inner_app.mutations == 1


def test_ordinary_json_declared_length_above_limit_rejects_before_downstream():
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app, ordinary_json_body_routes=(ordinary_route(),)),
        method="POST",
        path="/ordinary-json",
        chunks=[b""],
        headers=[
            *host_headers(),
            ("Content-Length", str(DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES + 1)),
            ("Content-Type", "application/json"),
        ],
    )

    body = response.json()
    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert body["code"] == REQUEST_BODY_TOO_LARGE_CODE
    assert inner_app.calls == 0
    assert response.receive_calls == 0


def test_ordinary_json_actual_body_above_limit_rejects_before_mutation():
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app, ordinary_json_body_routes=(ordinary_route(),)),
        method="POST",
        path="/ordinary-json",
        chunks=[
            b"x" * DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES,
            b"y",
        ],
        headers=[*host_headers(), ("Content-Type", "application/json")],
    )

    body = response.json()
    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert body["code"] == REQUEST_BODY_TOO_LARGE_CODE
    assert inner_app.calls == 1
    assert inner_app.mutations == 0


def test_ordinary_json_declared_length_below_actual_does_not_bypass_limit():
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app, ordinary_json_body_routes=(ordinary_route(),)),
        method="POST",
        path="/ordinary-json",
        chunks=[
            b"x" * DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES,
            b"y",
        ],
        headers=[
            *host_headers(),
            ("Content-Length", "1"),
            ("Content-Type", "application/json"),
        ],
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert inner_app.mutations == 0


def test_ordinary_json_missing_content_length_uses_actual_bytes():
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app, ordinary_json_body_routes=(ordinary_route(),)),
        method="POST",
        path="/ordinary-json",
        chunks=[b"x" * (DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES + 1)],
        headers=[*host_headers(), ("Content-Type", "application/json")],
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert inner_app.mutations == 0


def test_ordinary_json_chunked_body_receives_actual_byte_enforcement():
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app, ordinary_json_body_routes=(ordinary_route(),)),
        method="POST",
        path="/ordinary-json",
        chunks=[
            b"x" * (DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES // 2),
            b"y" * ((DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES // 2) + 1),
        ],
        headers=[*host_headers(), ("Content-Type", "application/json")],
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert inner_app.mutations == 0


def test_ordinary_json_malformed_body_below_limit_reaches_existing_parser():
    app = create_app(settings=runtime_settings())

    with TestClient(app) as client:
        response = client.patch(
            "/users/me",
            content=b"{malformed",
            headers={
                "Host": ALLOWED_HOST,
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert REQUEST_BODY_TOO_LARGE_CODE not in response.text


def test_ordinary_json_oversized_malformed_body_rejects_before_parser():
    app = create_app(settings=runtime_settings())
    body = b'{"submitted_marker":"' + (
        b"x" * DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES
    )

    with TestClient(app) as client:
        response = client.patch(
            "/users/me",
            content=body,
            headers={
                "Host": ALLOWED_HOST,
                "Content-Type": "application/json",
                "Origin": ALLOWED_ORIGIN,
            },
        )

    response_body = response.json()
    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert response_body["code"] == REQUEST_BODY_TOO_LARGE_CODE
    assert "submitted_marker" not in response.text
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN


@pytest.mark.parametrize(
    "body_size",
    [
        DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES - 1,
        DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES,
    ],
)
def test_platform_notice_route_class_accepts_body_at_or_below_limit(body_size: int):
    inner_app = RecordingBodyApp()
    body = b"x" * body_size

    response = invoke_asgi(
        limited_app(inner_app),
        method="POST",
        path=PLATFORM_NOTICE_CREATE_PATH,
        chunks=[body],
        headers=[
            *host_headers(),
            ("Content-Length", str(body_size)),
        ],
    )

    assert response.status_code == status.HTTP_200_OK
    assert inner_app.bodies == [body]
    assert inner_app.mutations == 1


def test_platform_notice_special_class_precedes_ordinary_route_match():
    inner_app = RecordingBodyApp()
    body = b"x" * (DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES + 1)

    response = invoke_asgi(
        limited_app(
            inner_app,
            ordinary_json_body_routes=(ordinary_route(PLATFORM_NOTICE_CREATE_PATH),),
        ),
        method="POST",
        path=PLATFORM_NOTICE_CREATE_PATH,
        chunks=[body],
        headers=[
            *host_headers(),
            ("Content-Length", str(len(body))),
            ("Content-Type", "application/json"),
        ],
    )

    assert response.status_code == status.HTTP_200_OK
    assert inner_app.bodies == [body]


def test_platform_notice_declared_length_above_limit_rejects_before_downstream():
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app),
        method="POST",
        path=PLATFORM_NOTICE_CREATE_PATH,
        chunks=[b""],
        headers=[
            *host_headers(),
            (
                "Content-Length",
                str(DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES + 1),
            ),
        ],
    )

    body = response.json()
    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert body["code"] == REQUEST_BODY_TOO_LARGE_CODE
    assert inner_app.calls == 0
    assert response.receive_calls == 0


def test_platform_notice_actual_body_above_limit_rejects_before_mutation():
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app),
        method="POST",
        path=PLATFORM_NOTICE_CREATE_PATH,
        chunks=[
            b"x" * DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES,
            b"y",
        ],
    )

    body = response.json()
    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert body["code"] == REQUEST_BODY_TOO_LARGE_CODE
    assert inner_app.calls == 1
    assert inner_app.mutations == 0


def test_platform_notice_declared_length_below_actual_does_not_bypass_limit():
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app),
        method="POST",
        path=PLATFORM_NOTICE_CREATE_PATH,
        chunks=[
            b"x" * DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES,
            b"y",
        ],
        headers=[*host_headers(), ("Content-Length", "1")],
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert inner_app.mutations == 0


def test_platform_notice_duplicate_or_malformed_lengths_use_actual_bytes_only():
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app),
        method="POST",
        path=PLATFORM_NOTICE_CREATE_PATH,
        chunks=[b"safe"],
        headers=[
            *host_headers(),
            ("Content-Length", "malformed"),
            (
                "Content-Length",
                str(DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES + 1),
            ),
        ],
    )

    assert response.status_code == status.HTTP_200_OK
    assert inner_app.bodies == [b"safe"]


def test_platform_notice_duplicate_lengths_do_not_bypass_actual_byte_limit():
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app),
        method="POST",
        path=PLATFORM_NOTICE_CREATE_PATH,
        chunks=[
            b"x" * DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES,
            b"y",
        ],
        headers=[
            *host_headers(),
            ("Content-Length", "1"),
            ("Content-Length", "2"),
        ],
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert inner_app.mutations == 0


def test_platform_notice_chunked_body_receives_actual_byte_enforcement():
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app),
        method="POST",
        path=f"{PLATFORM_NOTICE_CREATE_PATH}/",
        chunks=[
            b"x" * (DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES // 2),
            b"y" * ((DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES // 2) + 1),
        ],
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert inner_app.mutations == 0


def test_platform_notice_limit_does_not_apply_to_recipient_pagination_path():
    inner_app = RecordingBodyApp()
    notice_id = uuid.uuid4()
    body = b"x" * (DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES + 1)

    response = invoke_asgi(
        limited_app(inner_app),
        method="POST",
        path=f"/admin/platform-notices/{notice_id}/recipients",
        chunks=[body],
        headers=[*host_headers(), ("Content-Length", str(len(body)))],
    )

    assert response.status_code == status.HTTP_200_OK
    assert inner_app.bodies == [body]


def test_signed_stripe_webhook_preserves_exact_bytes_and_reads_once(monkeypatch):
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
    body = b'{"type":"synthetic.event","spacing":" preserved "}'
    app = create_app(settings=runtime_settings())

    response = invoke_asgi(
        app,
        method="POST",
        path=STRIPE_WEBHOOK_PATH,
        chunks=[body],
        headers=[*stripe_headers(), ("Content-Length", str(len(body)))],
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "processed"}
    assert captured["payload"] == body
    assert captured["signature"] == "synthetic-signature"
    assert response.receive_calls == 1


def test_signed_stripe_declared_length_above_limit_rejects_before_verification(
    monkeypatch,
):
    verification_called = False
    mutation_called = False

    def fake_construct_webhook_event(payload: bytes, stripe_signature: str):
        del payload, stripe_signature
        nonlocal verification_called
        verification_called = True

    def fake_record_and_process_stripe_webhook_event(db, stripe_event):
        del db, stripe_event
        nonlocal mutation_called
        mutation_called = True

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
    app = create_app(settings=runtime_settings())

    response = invoke_asgi(
        app,
        method="POST",
        path=STRIPE_WEBHOOK_PATH,
        chunks=[b""],
        headers=[
            *stripe_headers(),
            ("Content-Length", str(DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES + 1)),
        ],
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert response.json()["code"] == REQUEST_BODY_TOO_LARGE_CODE
    assert verification_called is False
    assert mutation_called is False
    assert response.receive_calls == 0


def test_signed_stripe_actual_body_above_limit_rejects_before_verification(
    monkeypatch,
):
    verification_called = False
    mutation_called = False

    def fake_construct_webhook_event(payload: bytes, stripe_signature: str):
        del payload, stripe_signature
        nonlocal verification_called
        verification_called = True

    def fake_record_and_process_stripe_webhook_event(db, stripe_event):
        del db, stripe_event
        nonlocal mutation_called
        mutation_called = True

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
    app = create_app(settings=runtime_settings())

    response = invoke_asgi(
        app,
        method="POST",
        path=STRIPE_WEBHOOK_PATH,
        chunks=[
            b"x" * DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES,
            b"y",
        ],
        headers=stripe_headers(),
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert verification_called is False
    assert mutation_called is False


def test_signed_stripe_declared_length_below_actual_does_not_bypass_limit(
    monkeypatch,
):
    verification_called = False

    def fake_construct_webhook_event(payload: bytes, stripe_signature: str):
        del payload, stripe_signature
        nonlocal verification_called
        verification_called = True

    monkeypatch.setattr(
        stripe_webhook_routes,
        "construct_webhook_event",
        fake_construct_webhook_event,
    )
    app = create_app(settings=runtime_settings())

    response = invoke_asgi(
        app,
        method="POST",
        path=STRIPE_WEBHOOK_PATH,
        chunks=[
            b"x" * DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES,
            b"y",
        ],
        headers=[*stripe_headers(), ("Content-Length", "1")],
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert verification_called is False


def test_signed_stripe_chunked_body_receives_actual_byte_enforcement(monkeypatch):
    verification_called = False

    def fake_construct_webhook_event(payload: bytes, stripe_signature: str):
        del payload, stripe_signature
        nonlocal verification_called
        verification_called = True

    monkeypatch.setattr(
        stripe_webhook_routes,
        "construct_webhook_event",
        fake_construct_webhook_event,
    )
    app = create_app(settings=runtime_settings())

    response = invoke_asgi(
        app,
        method="POST",
        path=STRIPE_WEBHOOK_PATH,
        chunks=[
            b"x" * (DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES // 2),
            b"y" * ((DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES // 2) + 1),
        ],
        headers=stripe_headers(),
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert verification_called is False


def test_stripe_missing_signature_remains_route_rejected_before_body_read():
    body = b"x" * (DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES + 1)
    app = create_app(settings=runtime_settings())

    response = invoke_asgi(
        app,
        method="POST",
        path=STRIPE_WEBHOOK_PATH,
        chunks=[body],
        headers=[
            *host_headers(),
            ("Content-Length", str(DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES + 1)),
        ],
    )

    response_body = response.json()
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response_body["code"] == "API.BAD_REQUEST"
    assert response.receive_calls == 0


@pytest.mark.parametrize(
    "service_result",
    [
        {"status": "duplicate"},
        {"status": "ignored"},
    ],
)
def test_signed_stripe_below_limit_preserves_service_result_compatibility(
    monkeypatch,
    service_result,
):
    def fake_construct_webhook_event(payload: bytes, stripe_signature: str):
        del payload, stripe_signature
        return {"id": "evt_synthetic", "type": "synthetic.event", "data": {}}

    def fake_record_and_process_stripe_webhook_event(db, stripe_event):
        del db, stripe_event
        return service_result

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
    app = create_app(settings=runtime_settings())

    response = invoke_asgi(
        app,
        method="POST",
        path=STRIPE_WEBHOOK_PATH,
        chunks=[b'{"type":"synthetic.event"}'],
        headers=stripe_headers(),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == service_result


@pytest.mark.parametrize(
    ("path", "headers"),
    [
        (PLATFORM_NOTICE_CREATE_PATH, host_headers()),
        (STRIPE_WEBHOOK_PATH, stripe_headers()),
    ],
)
def test_limited_request_classes_reject_non_identity_content_encoding(path, headers):
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app),
        method="POST",
        path=path,
        chunks=[b"compressed-body"],
        headers=[*headers, ("Content-Encoding", "gzip")],
    )

    body = response.json()
    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert body["code"] == UNSUPPORTED_CONTENT_ENCODING_CODE
    assert "compressed-body" not in response.body.decode("utf-8")
    assert inner_app.calls == 0
    assert response.receive_calls == 0


@pytest.mark.parametrize(
    ("path", "headers"),
    [
        (PLATFORM_NOTICE_CREATE_PATH, host_headers()),
        (STRIPE_WEBHOOK_PATH, stripe_headers()),
    ],
)
def test_limited_request_classes_allow_identity_content_encoding(path, headers):
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app),
        method="POST",
        path=path,
        chunks=[b"identity-body"],
        headers=[*headers, ("Content-Encoding", "identity")],
    )

    assert response.status_code == status.HTTP_200_OK
    assert inner_app.bodies == [b"identity-body"]


def test_ordinary_json_route_rejects_non_identity_content_encoding():
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app, ordinary_json_body_routes=(ordinary_route(),)),
        method="POST",
        path="/ordinary-json",
        chunks=[b"compressed-body"],
        headers=[
            *host_headers(),
            ("Content-Encoding", "gzip"),
            ("Content-Type", "application/json"),
        ],
    )

    body = response.json()
    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert body["code"] == UNSUPPORTED_CONTENT_ENCODING_CODE
    assert "compressed-body" not in response.body.decode("utf-8")
    assert inner_app.calls == 0
    assert response.receive_calls == 0


def test_ordinary_json_route_allows_identity_content_encoding():
    inner_app = RecordingBodyApp()

    response = invoke_asgi(
        limited_app(inner_app, ordinary_json_body_routes=(ordinary_route(),)),
        method="POST",
        path="/ordinary-json",
        chunks=[b"identity-body"],
        headers=[
            *host_headers(),
            ("Content-Encoding", "identity"),
            ("Content-Type", "application/json"),
        ],
    )

    assert response.status_code == status.HTTP_200_OK
    assert inner_app.bodies == [b"identity-body"]


def test_unclassified_body_route_keeps_current_content_encoding_behavior():
    inner_app = RecordingBodyApp()
    body = b"x" * (DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES + 1)

    response = invoke_asgi(
        limited_app(inner_app),
        method="POST",
        path="/users",
        chunks=[body],
        headers=[
            *host_headers(),
            ("Content-Length", str(len(body))),
            ("Content-Encoding", "gzip"),
        ],
    )

    assert response.status_code == status.HTTP_200_OK
    assert inner_app.bodies == [body]


def test_oversized_rejection_uses_stable_error_cors_correlation_and_security_headers():
    app = create_app(settings=runtime_settings())
    body = b"submitted-body-marker" + (
        b"x" * DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES
    )

    with TestClient(app) as client:
        response = client.post(
            PLATFORM_NOTICE_CREATE_PATH,
            content=body,
            headers={"Host": ALLOWED_HOST, "Origin": ALLOWED_ORIGIN},
        )

    response_body = response.json()
    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert response_body["detail"]
    assert response_body["code"] == REQUEST_BODY_TOO_LARGE_CODE
    assert response_body["message"] == "Request body is too large."
    assert response_body["correlation_id"] == response.headers[CORRELATION_ID_HEADER]
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"
    assert "submitted-body-marker" not in response.text
    assert "synthetic-signature" not in response.text


def test_middleware_order_preserves_outer_host_cors_security_and_correlation():
    app = create_app(settings=runtime_settings())

    assert [middleware.cls.__name__ for middleware in app.user_middleware[:5]] == [
        "CorrelationIdMiddleware",
        "ResponseSecurityHeadersMiddleware",
        "TrustedHostMiddleware",
        "CORSMiddleware",
        "RequestBodyLimitMiddleware",
    ]


def test_host_rejection_remains_outside_body_limit_response():
    app = create_app(settings=runtime_settings())
    body = b"x" * (DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES + 1)

    with TestClient(app) as client:
        response = client.post(
            PLATFORM_NOTICE_CREATE_PATH,
            content=body,
            headers={"Host": "unexpected.example.test", "Origin": ALLOWED_ORIGIN},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert REQUEST_BODY_TOO_LARGE_CODE not in response.text
    assert ALLOWED_HOST not in response.text
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_health_readiness_docs_and_bodyless_requests_are_unaffected(monkeypatch):
    monkeypatch.setattr(main_module, "check_database_connection", lambda: True)
    app = create_app(settings=runtime_settings())

    with TestClient(app) as client:
        live_response = client.get("/live", headers={"Host": ALLOWED_HOST})
        ready_response = client.get("/ready", headers={"Host": ALLOWED_HOST})
        schema_response = client.get("/openapi.json", headers={"Host": ALLOWED_HOST})

    assert live_response.status_code == status.HTTP_200_OK
    assert ready_response.status_code == status.HTTP_200_OK
    assert schema_response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize("scope_type", ["websocket", "lifespan"])
def test_non_http_scopes_are_not_limited(scope_type):
    called = False

    async def app(scope, receive, send):
        del receive, send
        nonlocal called
        called = True
        assert scope["type"] == scope_type

    middleware = RequestBodyLimitMiddleware(
        app,
        ordinary_json_request_body_limit_bytes=1,
        ordinary_json_body_routes=(),
        platform_notice_request_body_limit_bytes=1,
        stripe_webhook_request_body_limit_bytes=1,
    )

    async def receive():
        return {"type": f"{scope_type}.disconnect"}

    async def send(message):
        del message

    asyncio.run(middleware({"type": scope_type}, receive, send))

    assert called is True
