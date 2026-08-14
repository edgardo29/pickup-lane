from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import Body, Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from backend.observability.request_body_limits import (
    DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES,
    RequestBodyLimitMiddleware,
    RequestBodyLimitRoute,
)

pytestmark = pytest.mark.no_db_cleanup

_ORDINARY_PATH = "/ordinary"
_ORDINARY_LIMIT = DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES


@dataclass
class MiddlewareResult:
    app: RecordingApp
    receive: ReceiveQueue
    sent: list[dict[str, Any]]


class ReceiveQueue:
    def __init__(self, messages: tuple[dict[str, Any], ...]) -> None:
        self._messages = list(messages)
        self.calls = 0

    async def __call__(self) -> dict[str, Any]:
        self.calls += 1
        if self._messages:
            return self._messages.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}


class RecordingApp:
    def __init__(self) -> None:
        self.called = False
        self.scope: dict[str, Any] | None = None
        self.messages: list[dict[str, Any]] = []

    async def __call__(self, scope, receive, send) -> None:
        self.called = True
        self.scope = dict(scope)
        while True:
            message = await receive()
            self.messages.append(message)
            if message["type"] != "http.request" or not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})


def _http_message(body: bytes = b"", *, more_body: bool = False) -> dict[str, Any]:
    return {"type": "http.request", "body": body, "more_body": more_body}


def _scope(
    *,
    method: str = "POST",
    path: str = _ORDINARY_PATH,
    headers: tuple[tuple[bytes, bytes], ...] = (),
) -> dict[str, Any]:
    return {
        "type": "http",
        "method": method,
        "path": path,
        "headers": list(headers),
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("client", 123),
    }


def _ordinary_route(path: str = _ORDINARY_PATH) -> RequestBodyLimitRoute:
    app = FastAPI()

    @app.post(path)
    def ordinary_route(payload: dict):
        return payload

    route = next(route for route in app.routes if isinstance(route, APIRoute))
    return RequestBodyLimitRoute(
        path=route.path,
        methods=frozenset({"POST"}),
        path_regex=route.path_regex,
    )


def _run(
    *,
    scope: dict[str, Any] | None = None,
    messages: tuple[dict[str, Any], ...] = (_http_message(),),
    limit_bytes: int = _ORDINARY_LIMIT,
    ordinary_routes: tuple[RequestBodyLimitRoute, ...] = (_ordinary_route(),),
) -> MiddlewareResult:
    app = RecordingApp()
    receive = ReceiveQueue(messages)
    sent: list[dict[str, Any]] = []
    middleware = RequestBodyLimitMiddleware(
        app,
        ordinary_json_request_body_limit_bytes=limit_bytes,
        ordinary_json_body_routes=ordinary_routes,
        platform_notice_request_body_limit_bytes=163_840,
        stripe_webhook_request_body_limit_bytes=65_536,
    )

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    asyncio.run(middleware(scope or _scope(), receive, send))
    return MiddlewareResult(app=app, receive=receive, sent=sent)


def _status(result: MiddlewareResult) -> int:
    starts = [message for message in result.sent if message["type"] == "http.response.start"]
    assert len(starts) == 1
    return int(starts[0]["status"])


def _json_body(result: MiddlewareResult) -> dict[str, Any]:
    body = b"".join(
        message.get("body", b"")
        for message in result.sent
        if message["type"] == "http.response.body"
    )
    return json.loads(body)


def _delivered_body(result: MiddlewareResult) -> bytes:
    return b"".join(
        message.get("body", b"")
        for message in result.app.messages
        if message["type"] == "http.request"
    )


@pytest.mark.requirement("WS02-04B2A2C-R3", "WS02-04B2A2C-R4")
def test_exact_ordinary_json_limit_is_accepted_and_delivered_byte_for_byte() -> None:
    body = b"x" * _ORDINARY_LIMIT

    result = _run(messages=(_http_message(body),))

    assert _status(result) == 204
    assert result.app.called
    assert _delivered_body(result) == body


@pytest.mark.requirement("WS02-04B2A2C-R3", "WS02-04B2A2C-R4")
def test_limit_plus_one_ordinary_json_body_is_rejected_before_delivery() -> None:
    result = _run(messages=(_http_message(b"x" * (_ORDINARY_LIMIT + 1)),))

    assert _status(result) == 413
    assert _json_body(result)["code"] == "API.REQUEST_BODY_TOO_LARGE"
    assert result.app.called
    assert result.app.messages == []


@pytest.mark.requirement("WS02-04B2A2C-R3")
def test_valid_oversized_content_length_rejects_before_receive_or_app_call() -> None:
    result = _run(
        scope=_scope(headers=((b"content-length", str(_ORDINARY_LIMIT + 1).encode()),)),
        messages=(_http_message(b"x" * (_ORDINARY_LIMIT + 1)),),
    )

    assert _status(result) == 413
    assert result.receive.calls == 0
    assert not result.app.called


@pytest.mark.requirement("WS02-04B2A2C-R3")
@pytest.mark.parametrize(
    "headers",
    [
        (),
        ((b"content-length", b"not-an-int"),),
        ((b"content-length", b"1"), (b"content-length", str(_ORDINARY_LIMIT + 1).encode())),
        ((b"content-length", b"1"),),
    ],
)
def test_actual_bytes_remain_authoritative_when_length_metadata_cannot_reject(
    headers: tuple[tuple[bytes, bytes], ...],
) -> None:
    result = _run(
        scope=_scope(headers=headers),
        messages=(_http_message(b"x" * (_ORDINARY_LIMIT + 1)),),
    )

    assert _status(result) == 413
    assert result.receive.calls == 1
    assert result.app.messages == []


@pytest.mark.requirement("WS02-04B2A2C-R3", "WS02-04B2A2C-R4")
def test_multi_message_ordinary_body_is_counted_cumulatively() -> None:
    result = _run(
        messages=(
            _http_message(b"a" * 32_768, more_body=True),
            _http_message(b"b" * 32_768, more_body=False),
        )
    )

    assert _status(result) == 204
    assert _delivered_body(result) == b"a" * 32_768 + b"b" * 32_768


@pytest.mark.requirement("WS02-04B2A2C-R3", "WS02-04B2A2C-R4")
def test_multi_message_ordinary_body_rejects_when_cumulative_bytes_exceed_limit() -> None:
    result = _run(
        messages=(
            _http_message(b"a" * 32_768, more_body=True),
            _http_message(b"b" * 32_769, more_body=False),
        )
    )

    assert _status(result) == 413
    assert _delivered_body(result) == b"a" * 32_768


@pytest.mark.requirement("WS02-04B2A2C-R1", "WS02-04B2A2C-R3")
def test_ordinary_route_path_regex_and_trailing_slash_normalization_are_compatible() -> None:
    result = _run(
        scope=_scope(path="/ordinary/abc/", headers=((b"content-length", b"5"),)),
        messages=(_http_message(b"abcde"),),
        limit_bytes=4,
        ordinary_routes=(_ordinary_route("/ordinary/{item_id}"),),
    )

    assert _status(result) == 413
    assert result.receive.calls == 0
    assert not result.app.called


@pytest.mark.requirement("WS02-04B2A2C-R4")
def test_oversized_ordinary_body_does_not_reach_fastapi_dependency_or_handler() -> None:
    calls: list[str] = []
    app = FastAPI()

    def require_payload(payload: dict = Body(...)):
        calls.append("dependency")
        return payload

    @app.post("/ordinary")
    def ordinary_route(payload: dict = Depends(require_payload)):
        calls.append("handler")
        return payload

    app.add_middleware(
        RequestBodyLimitMiddleware,
        ordinary_json_request_body_limit_bytes=16,
        ordinary_json_body_routes=(_ordinary_route(),),
        platform_notice_request_body_limit_bytes=163_840,
        stripe_webhook_request_body_limit_bytes=65_536,
    )

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.post(
            "/ordinary",
            headers={"Content-Type": "application/json"},
            content=b'{"value":"' + b"x" * 64 + b'"}',
        )

    assert response.status_code == 413
    assert response.json()["code"] == "API.REQUEST_BODY_TOO_LARGE"
    assert calls == []
