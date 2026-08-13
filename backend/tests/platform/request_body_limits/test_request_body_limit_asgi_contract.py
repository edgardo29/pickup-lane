from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any

import pytest

from backend.observability.request_body_limits import (
    PLATFORM_NOTICE_CREATE_PATH,
    RequestBodyLimitMiddleware,
    RequestBodyLimitRoute,
)

pytestmark = pytest.mark.no_db_cleanup


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
        if scope["type"] != "http":
            return

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
    scope_type: str = "http",
    method: str = "POST",
    path: str = PLATFORM_NOTICE_CREATE_PATH,
    headers: tuple[tuple[bytes, bytes], ...] = (),
) -> dict[str, Any]:
    return {
        "type": scope_type,
        "method": method,
        "path": path,
        "headers": list(headers),
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("client", 123),
    }


def _run(
    *,
    scope: dict[str, Any] | None = None,
    messages: tuple[dict[str, Any], ...] = (_http_message(),),
    ordinary_routes: tuple[RequestBodyLimitRoute, ...] = (),
    platform_limit: int = 4,
    stripe_limit: int = 4,
) -> MiddlewareResult:
    app = RecordingApp()
    receive = ReceiveQueue(messages)
    sent: list[dict[str, Any]] = []
    middleware = RequestBodyLimitMiddleware(
        app,
        ordinary_json_request_body_limit_bytes=4,
        ordinary_json_body_routes=ordinary_routes,
        platform_notice_request_body_limit_bytes=platform_limit,
        stripe_webhook_request_body_limit_bytes=stripe_limit,
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


@pytest.mark.requirement("WS02-04B2A1-R3")
def test_exact_limit_body_is_accepted_and_delivered_byte_for_byte() -> None:
    body = b"abcd"

    result = _run(messages=(_http_message(body),))

    assert _status(result) == 204
    assert result.app.called
    assert _delivered_body(result) == body


@pytest.mark.requirement("WS02-04B2A1-R3")
def test_limit_plus_one_body_is_rejected_before_downstream_delivery() -> None:
    result = _run(messages=(_http_message(b"abcde"),))

    assert _status(result) == 413
    assert _json_body(result)["code"] == "API.REQUEST_BODY_TOO_LARGE"
    assert result.app.called
    assert result.app.messages == []


@pytest.mark.requirement("WS02-04B2A1-R3")
def test_content_length_above_limit_rejects_before_receive_or_app_call() -> None:
    result = _run(
        scope=_scope(headers=((b"content-length", b"5"),)),
        messages=(_http_message(b"abcde"),),
    )

    assert _status(result) == 413
    assert result.receive.calls == 0
    assert not result.app.called


@pytest.mark.requirement("WS02-04B2A1-R3")
@pytest.mark.parametrize(
    "headers",
    [
        ((b"content-length", b"4"),),
        (),
        ((b"content-length", b"not-an-int"),),
        ((b"content-length", b"3"), (b"content-length", b"9")),
    ],
)
def test_actual_bytes_remain_authoritative_when_length_metadata_is_not_rejecting(
    headers: tuple[tuple[bytes, bytes], ...],
) -> None:
    result = _run(
        scope=_scope(headers=headers),
        messages=(_http_message(b"abcde"),),
    )

    assert _status(result) == 413
    assert result.receive.calls == 1
    assert result.app.messages == []


@pytest.mark.requirement("WS02-04B2A1-R3")
def test_multiple_request_messages_are_counted_cumulatively_with_more_body() -> None:
    result = _run(
        messages=(
            _http_message(b"ab", more_body=True),
            _http_message(b"cd", more_body=False),
        )
    )

    assert _status(result) == 204
    assert [message.get("more_body") for message in result.app.messages] == [True, False]
    assert _delivered_body(result) == b"abcd"


@pytest.mark.requirement("WS02-04B2A1-R3")
def test_downstream_delivery_stops_at_message_that_exceeds_limit() -> None:
    result = _run(
        messages=(
            _http_message(b"ab", more_body=True),
            _http_message(b"cde", more_body=False),
        )
    )

    assert _status(result) == 413
    assert _delivered_body(result) == b"ab"
    assert len(result.app.messages) == 1


@pytest.mark.requirement("WS02-04B2A1-R3")
def test_empty_zero_byte_messages_do_not_count_against_limit() -> None:
    result = _run(
        messages=(
            _http_message(b"", more_body=True),
            _http_message(b"", more_body=False),
        )
    )

    assert _status(result) == 204
    assert result.app.messages == [
        {"type": "http.request", "body": b"", "more_body": True},
        {"type": "http.request", "body": b"", "more_body": False},
    ]


@pytest.mark.requirement("WS02-04B2A1-R3")
def test_non_http_scope_passes_through_without_body_limit_behavior() -> None:
    result = _run(
        scope=_scope(scope_type="lifespan"),
        messages=({"type": "lifespan.startup"},),
    )

    assert result.sent == []
    assert result.receive.calls == 0
    assert result.app.called
    assert result.app.scope is not None
    assert result.app.scope["type"] == "lifespan"


@pytest.mark.requirement("WS02-04B2A1-R3")
def test_disconnect_non_request_message_reaches_downstream_receive() -> None:
    result = _run(messages=({"type": "http.disconnect"},))

    assert _status(result) == 204
    assert result.app.messages == [{"type": "http.disconnect"}]


@pytest.mark.requirement("WS02-04B2A1-R4")
@pytest.mark.parametrize(
    "headers",
    [
        (),
        ((b"content-encoding", b"identity"),),
        ((b"content-encoding", b" Identity "),),
    ],
)
def test_absent_or_identity_content_encoding_is_accepted_without_decompression(
    headers: tuple[tuple[bytes, bytes], ...],
) -> None:
    compressed_looking_bytes = b"\x1f\x8bnot-decompressed"

    result = _run(
        scope=_scope(headers=headers),
        messages=(_http_message(compressed_looking_bytes),),
        platform_limit=64,
    )

    assert _status(result) == 204
    assert _delivered_body(result) == compressed_looking_bytes


@pytest.mark.requirement("WS02-04B2A1-R4")
@pytest.mark.parametrize(
    "encoding",
    [b"gzip", b"br", b"identity, gzip", b"Identity, BR"],
)
def test_non_identity_content_encoding_is_rejected_before_body_receive(
    encoding: bytes,
) -> None:
    result = _run(
        scope=_scope(headers=((b"content-encoding", encoding),)),
        messages=(_http_message(b"body"),),
    )

    assert _status(result) == 415
    assert _json_body(result)["code"] == "API.UNSUPPORTED_CONTENT_ENCODING"
    assert result.receive.calls == 0
    assert not result.app.called


@pytest.mark.requirement("WS02-04B2A1-R7")
def test_route_outside_all_limited_classes_is_unaffected_by_size_and_encoding() -> None:
    result = _run(
        scope=_scope(
            path="/unlimited-raw",
            headers=((b"content-encoding", b"gzip"), (b"content-length", b"999")),
        ),
        messages=(_http_message(b"still delivered"),),
    )

    assert _status(result) == 204
    assert result.receive.calls == 1
    assert _delivered_body(result) == b"still delivered"


@pytest.mark.requirement("WS02-04B2A1-R7")
def test_special_classes_take_precedence_over_matching_ordinary_json_routes() -> None:
    matching_route = RequestBodyLimitRoute(
        path=PLATFORM_NOTICE_CREATE_PATH,
        methods=frozenset({"POST"}),
        path_regex=re.compile(f"^{re.escape(PLATFORM_NOTICE_CREATE_PATH)}$"),
    )

    result = _run(
        ordinary_routes=(matching_route,),
        platform_limit=8,
        messages=(_http_message(b"abcdef"),),
    )

    assert _status(result) == 204
    assert _delivered_body(result) == b"abcdef"
