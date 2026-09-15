from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.testclient import TestClient

from backend.observability.correlation import CORRELATION_ID_HEADER, get_correlation_id
from backend.observability.structured_logging import emit_event
from backend.observability.timeouts import DependencyReadTimeoutError
from backend.settings import build_settings, reset_settings_cache

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.requirement("WS09-01A"),
]

_DATABASE_URL = "postgresql+psycopg://127.0.0.1:5432/pickup_lane_test_db"


def _app(
    monkeypatch: pytest.MonkeyPatch,
    *,
    release: str = "request-logging-test-release",
):
    environment = {
        "APP_ENV": "test",
        "DATABASE_URL": _DATABASE_URL,
        "INBOX_TOKEN_SECRET": "synthetic-request-logging-token",
        "ALLOWED_HOSTS": "testserver",
        "CORS_ALLOWED_ORIGINS": "https://app.example.invalid",
        "ENABLE_API_DOCS": "false",
        "ENABLE_DB_HEALTH": "false",
        "ENABLE_STRIPE_PAYMENTS": "false",
        "PICKUP_LANE_RELEASE": release,
    }
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    reset_settings_cache()
    import backend.main as main_module

    settings = build_settings(
        environment,
        load_dotenv_file=False,
        validate_full=True,
    )
    app = main_module.create_app(settings)

    @app.get("/synthetic/success")
    def success() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/synthetic/redirect")
    def redirect() -> RedirectResponse:
        return RedirectResponse("/synthetic/success", status_code=307)

    @app.get("/synthetic/client-error")
    def client_error() -> None:
        raise HTTPException(status_code=418, detail="Synthetic handled error.")

    @app.get("/synthetic/server-error")
    def server_error() -> JSONResponse:
        return JSONResponse({"ok": False}, status_code=503)

    @app.get("/synthetic/timeout")
    def timeout() -> None:
        raise DependencyReadTimeoutError(
            provider_kind="stripe",
            operation="payment.lookup",
        )

    @app.get("/synthetic/unexpected")
    def unexpected() -> None:
        raise RuntimeError("Bearer private-canary user@example.invalid")

    @app.get("/synthetic/started")
    def started() -> StreamingResponse:
        def body():
            yield b"started"
            raise RuntimeError("Bearer post-start-private-canary")

        return StreamingResponse(body(), status_code=202)

    @app.get("/synthetic/items/{item_id}")
    def matched_sensitive_path(item_id: str) -> dict[str, bool]:
        del item_id
        return {"ok": True}

    return app


def _records(capsys: pytest.CaptureFixture[str]) -> list[dict[str, object]]:
    output = capsys.readouterr()
    assert output.err == ""
    return [json.loads(line) for line in output.out.splitlines()]


@pytest.mark.parametrize(
    ("path", "status_code", "severity", "result"),
    [
        ("/synthetic/success", 200, "info", "success"),
        ("/synthetic/redirect", 307, "info", "success"),
        ("/synthetic/client-error", 418, "warning", "client_error"),
        ("/synthetic/server-error", 503, "error", "server_error"),
    ],
)
def test_handled_requests_emit_one_exact_completion(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    path: str,
    status_code: int,
    severity: str,
    result: str,
) -> None:
    app = _app(monkeypatch)
    correlation_id = str(uuid.uuid4())

    with TestClient(app, follow_redirects=False) as client:
        response = client.get(path, headers={CORRELATION_ID_HEADER: correlation_id})

    assert response.status_code == status_code
    records = _records(capsys)
    completions = [
        record for record in records if record["event_name"] == "http.request"
    ]
    assert completions == [
        {
            "correlation_id": correlation_id,
            "environment": "test",
            "event_name": "http.request",
            "http_method": "get",
            "http_status_code": status_code,
            "labels": {"route_template": path},
            "occurred_at": completions[0]["occurred_at"],
            "release": app.state.release_identity,
            "result": result,
            "schema_version": "1",
            "severity": severity,
            "source_identity": "api",
        }
    ]


def test_timeout_and_unexpected_paths_are_distinct_and_have_one_completion(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = _app(monkeypatch)

    with TestClient(app, raise_server_exceptions=False) as client:
        timeout_response = client.get("/synthetic/timeout")
        unexpected_response = client.get("/synthetic/unexpected")

    assert timeout_response.status_code == 503
    assert timeout_response.json()["code"] == "API.DEPENDENCY_READ_TIMEOUT"
    assert unexpected_response.status_code == 500
    assert unexpected_response.json()["code"] == "API.UNEXPECTED"

    records = _records(capsys)
    assert [record["event_name"] for record in records] == [
        "application.timeout",
        "http.request",
        "application.unexpected_error",
        "http.request",
    ]
    assert records[0]["correlation_id"] == records[1]["correlation_id"]
    assert records[2]["correlation_id"] == records[3]["correlation_id"]
    assert records[0]["stable_error_code"] == "API.DEPENDENCY_READ_TIMEOUT"
    assert records[2]["stable_error_code"] == "API.UNEXPECTED"
    assert "private-canary" not in json.dumps(records)


@pytest.mark.parametrize(
    "request_id",
    [None, "", "not-a-uuid", str(uuid.uuid4()).upper(), str(uuid.uuid1())],
)
def test_missing_empty_and_invalid_request_ids_are_replaced_without_leakage(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    request_id: str | None,
) -> None:
    app = _app(monkeypatch)
    headers = {} if request_id is None else {CORRELATION_ID_HEADER: request_id}

    with TestClient(app) as client:
        response = client.get("/synthetic/success", headers=headers)

    selected = response.headers[CORRELATION_ID_HEADER]
    assert str(uuid.UUID(selected, version=4)) == selected
    if request_id:
        assert selected != request_id
    records = _records(capsys)
    assert records[-1]["correlation_id"] == selected
    if request_id:
        assert request_id not in json.dumps(records)


def test_concurrent_requests_keep_correlation_and_app_metadata_isolated(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = _app(monkeypatch)
    request_ids = [str(uuid.uuid4()) for _ in range(8)]

    with TestClient(app, raise_server_exceptions=False) as client:

        def make_request(item: tuple[int, str]) -> tuple[str, int]:
            index, request_id = item
            path = "/synthetic/timeout" if index == 3 else "/synthetic/success"
            response = client.get(path, headers={CORRELATION_ID_HEADER: request_id})
            return response.headers[CORRELATION_ID_HEADER], response.status_code

        with ThreadPoolExecutor(max_workers=8) as executor:
            responses = list(executor.map(make_request, enumerate(request_ids)))

    assert {correlation for correlation, _ in responses} == set(request_ids)
    records = _records(capsys)
    completions = [
        record for record in records if record["event_name"] == "http.request"
    ]
    assert len(completions) == len(request_ids)
    assert {record["correlation_id"] for record in completions} == set(request_ids)
    assert all(record["source_identity"] == "api" for record in records)


def test_sensitive_unmatched_path_query_and_headers_never_enter_records(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = _app(monkeypatch)
    canary = "private-user@example.invalid"

    with TestClient(app) as client:
        response = client.get(
            f"/missing/{canary}?token=Bearer-private-canary",
            headers={"Cookie": "session=private-canary", "User-Agent": canary},
        )

    assert response.status_code == 404
    records = _records(capsys)
    completion = records[-1]
    assert completion["labels"] == {"route_template": "/{unmatched}"}
    assert canary not in json.dumps(records)
    assert "Bearer-private-canary" not in json.dumps(records)
    assert "session=private-canary" not in json.dumps(records)


def test_matched_sensitive_path_uses_only_route_template(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = _app(monkeypatch)
    canary = "private-user@example.invalid"

    with TestClient(app) as client:
        response = client.get(f"/synthetic/items/{canary}")

    assert response.status_code == 200
    records = _records(capsys)
    assert records[-1]["labels"] == {"route_template": "/synthetic/items/{item_id}"}
    assert canary not in json.dumps(records)


def test_completed_request_does_not_leak_context_into_background_emission(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = _app(monkeypatch)
    request_id = str(uuid.uuid4())

    with TestClient(app) as client:
        response = client.get(
            "/synthetic/success",
            headers={CORRELATION_ID_HEADER: request_id},
        )

    assert response.status_code == 200
    assert get_correlation_id() is None
    assert emit_event(
        "runtime.background",
        "info",
        {"operation": "background.test", "result": "success"},
    )

    records = _records(capsys)
    assert records[-2]["correlation_id"] == request_id
    assert records[-1]["event_name"] == "runtime.background"
    assert records[-1]["release"] == app.state.release_identity
    assert "correlation_id" not in records[-1]


def test_repeated_apps_keep_per_app_release_without_duplicate_records(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = _app(monkeypatch, release="release-first")
    second = _app(monkeypatch, release="release-second")

    with TestClient(first) as client:
        first_response = client.get("/synthetic/success")
    with TestClient(second) as client:
        second_response = client.get("/synthetic/success")

    assert first_response.status_code == second_response.status_code == 200
    records = [
        record for record in _records(capsys) if record["event_name"] == "http.request"
    ]
    assert len(records) == 2
    assert [record["release"] for record in records] == [
        "release-first",
        "release-second",
    ]


def test_failure_after_response_start_has_one_captured_status_completion(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = _app(monkeypatch)

    with TestClient(app, raise_server_exceptions=False) as client:
        client.get("/synthetic/started")

    records = _records(capsys)
    completions = [
        record for record in records if record["event_name"] == "http.request"
    ]
    diagnostics = [
        record
        for record in records
        if record["event_name"] == "application.unexpected_error"
    ]
    assert len(completions) == 1
    assert completions[0]["http_status_code"] == 202
    assert completions[0]["result"] == "success"
    assert len(diagnostics) == 1
    assert diagnostics[0]["correlation_id"] == completions[0]["correlation_id"]
    assert "post-start-private-canary" not in json.dumps(records)
