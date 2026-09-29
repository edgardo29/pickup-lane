from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import pytest
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    ReadTimeoutError,
)

import backend.services.r2_storage_service as r2_storage
from backend.observability.metrics import MetricsRecorder, metrics_context
from backend.observability.timeouts import DependencyReadTimeoutError

pytestmark = pytest.mark.no_db_cleanup


@pytest.mark.parametrize(
    "operation", ["r2.upload_url.create", "r2.read_url.create", "r2.metadata.head"]
)
@pytest.mark.parametrize(
    "outcome",
    ["succeeded", "timed_out", "rate_limited", "failed", "configuration_error"],
)
def test_complete_r2_operation_metric_matrix(monkeypatch, operation, outcome):
    calls = []
    error = {
        "timed_out": ReadTimeoutError(endpoint_url="https://private.invalid"),
        "rate_limited": ClientError({"Error": {"Code": "SlowDown"}}, "private"),
        "failed": ClientError({"Error": {"Code": "AccessDenied"}}, "private"),
    }.get(outcome)

    class Client:
        def head_object(self, **kwargs):
            calls.append("head")
            if error:
                raise error
            return {"ContentType": "image/jpeg", "ContentLength": 12, "ETag": "private"}

        def generate_presigned_url(self, *args, **kwargs):
            calls.append("presign")
            if error:
                raise error
            return "https://private.invalid/signed"

    def config():
        if outcome == "configuration_error":
            raise r2_storage.R2StorageConfigError("private-secret")
        return _config()

    monkeypatch.setattr(r2_storage, "get_r2_storage_config", config)
    monkeypatch.setattr(r2_storage.boto3, "client", lambda *a, **k: Client())
    call = {
        "r2.upload_url.create": lambda: r2_storage.create_object_upload_url(
            object_key="private-key", content_type="image/jpeg"
        ),
        "r2.read_url.create": lambda: r2_storage.create_object_read_url("private-key"),
        "r2.metadata.head": lambda: r2_storage.get_object_properties("private-key"),
    }[operation]
    recorder = MetricsRecorder("api", "test", "r2-test")
    with metrics_context(recorder):
        if outcome == "succeeded":
            call()
        else:
            try:
                call()
            except Exception as exc:  # noqa: BLE001 - matrix spans distinct preserved public types.
                assert exc is not None
            else:
                pytest.fail("The configured storage failure must propagate")
    series = recorder.snapshot().series
    assert len(series) == 1 and series[0].value == 1
    assert dict(series[0].dimensions) == {
        "provider_kind": "r2",
        "operation": operation,
        "result": outcome,
    }
    assert len(calls) == (0 if outcome == "configuration_error" else 1)
    assert "private" not in repr(recorder.snapshot())


@pytest.mark.parametrize("code", ["404", "NoSuchKey", "NotFound"])
def test_r2_absence_has_one_nonfailure_observation(monkeypatch, code):
    monkeypatch.setattr(r2_storage, "get_r2_storage_config", _config)
    client = _FakeR2Client(
        head_error=ClientError({"Error": {"Code": code}}, "HeadObject")
    )
    monkeypatch.setattr(r2_storage, "get_r2_client", lambda config: client)
    recorder = MetricsRecorder("api", "test", "r2-test")
    with metrics_context(recorder), pytest.raises(r2_storage.R2ObjectNotFoundError):
        r2_storage.get_object_properties("private-key")
    assert len(recorder.snapshot().series) == 1
    assert dict(recorder.snapshot().series[0].dimensions)["result"] == "not_found"


def test_r2_result_conversion_failure_is_not_success(monkeypatch):
    monkeypatch.setattr(r2_storage, "get_r2_storage_config", _config)
    client = _FakeR2Client()
    monkeypatch.setattr(
        client, "head_object", lambda **k: {"ContentLength": "private-invalid"}
    )
    monkeypatch.setattr(r2_storage, "get_r2_client", lambda config: client)
    recorder = MetricsRecorder("api", "test", "r2-test")
    with metrics_context(recorder), pytest.raises(r2_storage.R2StorageError):
        r2_storage.get_object_properties("private-key")
    assert dict(recorder.snapshot().series[0].dimensions)["result"] == "failed"


@pytest.mark.parametrize(
    ("operation", "call"),
    [
        (
            "r2.upload_url.create",
            lambda: r2_storage.create_object_upload_url(
                object_key="private-key", content_type="image/jpeg"
            ),
        ),
        (
            "r2.read_url.create",
            lambda: r2_storage.create_object_read_url("private-key"),
        ),
    ],
)
@pytest.mark.parametrize(
    "malformed_url",
    [
        pytest.param("", id="empty-value"),
        pytest.param("   ", id="blank-value"),
        pytest.param("not-a-url", id="missing-scheme-and-authority"),
        pytest.param(
            "ftp://r2.example.invalid/object",
            id="unsupported-scheme",
        ),
        pytest.param("https:///missing-host", id="missing-host"),
        pytest.param(
            "https://user@r2.example.invalid/object",
            id="userinfo",
        ),
        pytest.param(
            "https://r2.example.invalid/object#fragment",
            id="fragment",
        ),
        pytest.param(
            "https://r2.example.invalid:/object",
            id="empty-port",
        ),
        pytest.param(
            "https://r2.example.invalid:not-a-port/object",
            id="non-numeric-port",
        ),
        pytest.param(
            "https://r2.example.invalid:0/object",
            id="zero-port",
        ),
        pytest.param(
            "https://r2.example.invalid:65536/object",
            id="out-of-range-port",
        ),
        pytest.param(
            "https://foo|bar.example.invalid/object",
            id="forbidden-dns-codepoint",
        ),
        pytest.param(
            "https://r2..example.invalid/object",
            id="empty-dns-label",
        ),
        pytest.param(
            "https://-r2.example.invalid/object",
            id="leading-label-hyphen",
        ),
        pytest.param(
            "https://r2-.example.invalid/object",
            id="trailing-label-hyphen",
        ),
        pytest.param(
            f"https://{'a' * 64}.example.invalid/object",
            id="oversized-dns-label",
        ),
        pytest.param(
            "https://999.999.999.999/object",
            id="invalid-ipv4-address",
        ),
        pytest.param(
            "https://0x100000000/object",
            id="invalid-whatwg-ipv4-number",
        ),
        pytest.param(
            "https://[127.0.0.1]/object",
            id="bracketed-ipv4-address",
        ),
        pytest.param(
            "https://[v1.invalid]/object",
            id="non-ip-bracketed-host",
        ),
        pytest.param(
            "https://[fe80::1%eth0]/object",
            id="raw-ipv6-zone-identifier",
        ),
        pytest.param(
            "https://[fe80::1%25eth0]/object",
            id="encoded-ipv6-zone-identifier",
        ),
        pytest.param("https://%/object", id="malformed-host-escape"),
        pytest.param(
            "https://r2\\evil.example.invalid/object",
            id="backslash-in-authority",
        ),
        pytest.param(
            "https://r2.example.invalid/\x00object",
            id="raw-control-character",
        ),
    ],
)
def test_malformed_presigned_url_is_failed_without_success_observation(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    call,
    malformed_url: str,
) -> None:
    class MalformedSigningClient:
        def generate_presigned_url(self, *args, **kwargs):
            return malformed_url

    monkeypatch.setattr(r2_storage, "get_r2_storage_config", _config)
    monkeypatch.setattr(
        r2_storage,
        "get_r2_client",
        lambda config: MalformedSigningClient(),
    )
    recorder = MetricsRecorder("api", "test", "r2-test")

    with metrics_context(recorder), pytest.raises(r2_storage.R2StorageError):
        call()

    (series,) = recorder.snapshot().series
    assert dict(series.dimensions) == {
        "provider_kind": "r2",
        "operation": operation,
        "result": "failed",
    }


@pytest.mark.parametrize(
    ("operation", "call"),
    [
        (
            "r2.upload_url.create",
            lambda: r2_storage.create_object_upload_url(
                object_key="private-key", content_type="image/jpeg"
            ),
        ),
        (
            "r2.read_url.create",
            lambda: r2_storage.create_object_read_url("private-key"),
        ),
    ],
)
@pytest.mark.parametrize(
    "valid_url",
    [
        pytest.param(
            "https://bucket.account.r2.cloudflarestorage.com/"
            "folder%2Fimage%20name.jpg?X-Amz-Credential=key%2Fscope&"
            "X-Amz-Signature=a%2Bb%2Fc%3D&token=one%20two",
            id="r2-percent-encoded-path-and-query",
        ),
        pytest.param(
            "http://localhost:8080/object",
            id="http-single-label-host-with-port",
        ),
        pytest.param(
            "https://127.0.0.1:65535/object",
            id="canonical-ipv4-with-maximum-port",
        ),
        pytest.param(
            "https://[2001:db8::1]:443/object",
            id="ipv6-literal-with-port",
        ),
        pytest.param(
            "https://bücher.example/object",
            id="idna-hostname",
        ),
        pytest.param(
            "https://r2.example.invalid./object",
            id="absolute-dns-hostname",
        ),
        pytest.param(
            f"https://{'a' * 63}.example.invalid/object",
            id="maximum-dns-label",
        ),
    ],
)
def test_valid_presigned_url_is_preserved_with_success_observation(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    call,
    valid_url: str,
) -> None:
    class ValidSigningClient:
        def generate_presigned_url(self, *args, **kwargs):
            return valid_url

    monkeypatch.setattr(r2_storage, "get_r2_storage_config", _config)
    monkeypatch.setattr(
        r2_storage,
        "get_r2_client",
        lambda config: ValidSigningClient(),
    )
    recorder = MetricsRecorder("api", "test", "r2-test")

    with metrics_context(recorder):
        result = call()

    actual_url = result.upload_url if operation == "r2.upload_url.create" else result
    assert actual_url == valid_url
    (series,) = recorder.snapshot().series
    assert dict(series.dimensions) == {
        "provider_kind": "r2",
        "operation": operation,
        "result": "succeeded",
    }


@pytest.mark.parametrize(
    "call",
    [
        lambda: r2_storage.create_object_upload_url(
            object_key="private-key", content_type="image/jpeg"
        ),
        lambda: r2_storage.create_object_read_url("private-key"),
    ],
)
def test_presigned_url_cancellation_propagates_without_provider_result(
    monkeypatch: pytest.MonkeyPatch,
    call,
) -> None:
    cancellation = asyncio.CancelledError()

    class CancelledSigningClient:
        def generate_presigned_url(self, *args, **kwargs):
            raise cancellation

    monkeypatch.setattr(r2_storage, "get_r2_storage_config", _config)
    monkeypatch.setattr(
        r2_storage,
        "get_r2_client",
        lambda config: CancelledSigningClient(),
    )
    recorder = MetricsRecorder("api", "test", "r2-test")

    with metrics_context(recorder), pytest.raises(asyncio.CancelledError) as exc_info:
        call()

    assert exc_info.value is cancellation
    assert recorder.snapshot().series == ()


def _config() -> r2_storage.R2StorageConfig:
    return r2_storage.R2StorageConfig(
        account_id="synthetic-account",
        access_key_id="synthetic-access-key",
        secret_access_key="synthetic-secret",
        endpoint_url="https://r2.example.invalid",
        bucket_name="synthetic-bucket",
        upload_url_minutes=15,
        read_url_minutes=10,
        max_image_bytes=1_000_000,
        allowed_image_types=frozenset({"image/jpeg"}),
        metadata_connect_timeout_seconds=2,
        metadata_read_timeout_seconds=6,
    )


class _FakeR2Client:
    def __init__(self, *, head_error: BaseException | None = None) -> None:
        self.head_error = head_error
        self.head_calls: list[dict[str, str]] = []
        self.presign_calls: list[dict[str, Any]] = []

    def head_object(self, **kwargs: str) -> dict[str, object]:
        self.head_calls.append(kwargs)
        if self.head_error is not None:
            raise self.head_error
        return {"ContentType": "image/jpeg", "ContentLength": 1234, "ETag": "etag"}

    def generate_presigned_url(self, method: str, **kwargs: Any) -> str:
        self.presign_calls.append({"method": method, **kwargs})
        return f"https://signed.example.invalid/{method}"


@pytest.mark.requirement("WS02-04C1-R4")
def test_r2_metadata_client_receives_approved_connect_and_read_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_client(*args: Any, **kwargs: Any) -> _FakeR2Client:
        calls.append({"args": args, "kwargs": kwargs})
        return _FakeR2Client()

    monkeypatch.setattr(r2_storage.boto3, "client", fake_client)

    client = r2_storage.get_r2_client(_config())

    assert isinstance(client, _FakeR2Client)
    assert calls[0]["args"] == ("s3",)
    botocore_config = calls[0]["kwargs"]["config"]
    assert botocore_config.connect_timeout == 2
    assert botocore_config.read_timeout == 6


@pytest.mark.requirement("WS02-04C1-R4")
@pytest.mark.parametrize(
    "timeout_error",
    [
        ConnectTimeoutError(endpoint_url="https://r2.example.invalid"),
        ReadTimeoutError(endpoint_url="https://r2.example.invalid", error="synthetic"),
    ],
)
def test_r2_head_timeout_maps_to_dependency_read(
    monkeypatch: pytest.MonkeyPatch,
    timeout_error: BaseException,
) -> None:
    fake_client = _FakeR2Client(head_error=timeout_error)
    monkeypatch.setattr(r2_storage, "get_r2_storage_config", _config)
    monkeypatch.setattr(r2_storage, "get_r2_client", lambda config: fake_client)

    with pytest.raises(DependencyReadTimeoutError) as exc_info:
        r2_storage.get_object_properties("venues/synthetic.jpg")

    assert exc_info.value.provider_kind == "r2"
    assert exc_info.value.operation == "r2.metadata.head"
    assert fake_client.head_calls == [
        {"Bucket": "synthetic-bucket", "Key": "venues/synthetic.jpg"}
    ]


@pytest.mark.requirement("WS02-04C1-R4")
def test_r2_object_not_found_and_storage_failures_remain_distinct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(r2_storage, "get_r2_storage_config", _config)
    monkeypatch.setattr(
        r2_storage,
        "get_r2_client",
        lambda config: _FakeR2Client(
            head_error=ClientError({"Error": {"Code": "NoSuchKey"}}, "HeadObject")
        ),
    )

    with pytest.raises(r2_storage.R2ObjectNotFoundError):
        r2_storage.get_object_properties("missing.jpg")

    monkeypatch.setattr(
        r2_storage,
        "get_r2_client",
        lambda config: _FakeR2Client(
            head_error=ClientError({"Error": {"Code": "AccessDenied"}}, "HeadObject")
        ),
    )
    with pytest.raises(r2_storage.R2StorageError) as client_error_info:
        r2_storage.get_object_properties("forbidden.jpg")
    assert isinstance(client_error_info.value.__cause__, ClientError)

    monkeypatch.setattr(
        r2_storage,
        "get_r2_client",
        lambda config: _FakeR2Client(head_error=BotoCoreError(error_msg="synthetic")),
    )
    with pytest.raises(r2_storage.R2StorageError):
        r2_storage.get_object_properties("broken.jpg")


@pytest.mark.requirement("WS02-04C1-R4", "WS02-04C1-R7")
def test_r2_head_cancellation_propagates_without_timeout_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cancellation = asyncio.CancelledError()
    fake_client = _FakeR2Client(head_error=cancellation)
    monkeypatch.setattr(r2_storage, "get_r2_storage_config", _config)
    monkeypatch.setattr(r2_storage, "get_r2_client", lambda config: fake_client)

    with pytest.raises(asyncio.CancelledError) as exc_info:
        r2_storage.get_object_properties("venues/cancelled.jpg")

    assert exc_info.value is cancellation
    assert fake_client.head_calls == [
        {"Bucket": "synthetic-bucket", "Key": "venues/cancelled.jpg"}
    ]


@pytest.mark.requirement("WS02-04C1-R4")
def test_r2_presigned_urls_are_local_signing_not_metadata_network_timeout_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeR2Client()
    monkeypatch.setattr(r2_storage, "get_r2_storage_config", _config)
    monkeypatch.setattr(r2_storage, "get_r2_client", lambda config: fake_client)
    monkeypatch.setattr(
        r2_storage,
        "datetime",
        type(
            "FrozenDatetime",
            (),
            {
                "now": staticmethod(lambda tz=None: datetime(2026, 1, 1, tzinfo=tz)),
            },
        ),
    )

    upload_ticket = r2_storage.create_object_upload_url(
        object_key="venues/synthetic.jpg",
        content_type="image/jpeg",
    )
    read_url = r2_storage.create_object_read_url("venues/synthetic.jpg")

    assert upload_ticket.upload_url == "https://signed.example.invalid/put_object"
    assert read_url == "https://signed.example.invalid/get_object"
    assert fake_client.head_calls == []
    assert [call["method"] for call in fake_client.presign_calls] == [
        "put_object",
        "get_object",
    ]
