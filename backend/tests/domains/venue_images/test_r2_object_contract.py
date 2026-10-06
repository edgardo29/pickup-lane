from __future__ import annotations

import asyncio
from io import BytesIO

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError, ReadTimeoutError

from backend.observability.metrics import MetricsRecorder, metrics_context
from backend.observability.timeouts import DependencyMutationTimeoutUnknownError
from backend.services import r2_storage_service as r2

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.pass_provenance("WS06-02"),
]


def _config() -> r2.R2StorageConfig:
    return r2.R2StorageConfig(
        account_id="test-account",
        access_key_id="test-access",
        secret_access_key="test-secret",
        endpoint_url="https://test-account.r2.cloudflarestorage.com",
        bucket_name="test-bucket",
        upload_url_minutes=15,
        read_url_minutes=60,
        max_image_bytes=1024,
        allowed_image_types=frozenset({"image/png"}),
        object_connect_timeout_seconds=2,
        object_read_timeout_seconds=6,
    )


def _target() -> r2.R2StorageTarget:
    return r2.R2StorageTarget("r2", "test-account", "test-bucket")


def _create_signed_url(operation: str, *, config: r2.R2StorageConfig):
    if operation == "upload":
        return r2.create_object_upload_url(
            target=_target(),
            object_key="staging/key.png",
            content_type="image/png",
            config=config,
        )
    return r2.create_object_read_url(
        target=_target(),
        object_key="published/key.png",
        config=config,
    )


class _Body(BytesIO):
    def __init__(self, value: bytes) -> None:
        super().__init__(value)
        self.closed_by_adapter = False
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return super().read(size)

    def close(self) -> None:
        self.closed_by_adapter = True
        super().close()


class _CloseFailingBody:
    def __init__(
        self, value: bytes, *, read_failure: BaseException | None = None
    ) -> None:
        self.value = value
        self.read_failure = read_failure
        self.closed_by_adapter = False
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        if self.read_failure is not None:
            raise self.read_failure
        return self.value

    def close(self) -> None:
        self.closed_by_adapter = True
        raise RuntimeError("synthetic streaming-body close failure")


class _ReadOnlyBody:
    def __init__(self, value: bytes) -> None:
        self.value = value
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return self.value


class _CloseCancellingBody(_CloseFailingBody):
    def __init__(self, value: bytes, cancellation: asyncio.CancelledError) -> None:
        super().__init__(value)
        self.cancellation = cancellation

    def close(self) -> None:
        self.closed_by_adapter = True
        raise self.cancellation


def _client_error(status: object, code: str) -> ClientError:
    metadata = {} if status is None else {"HTTPStatusCode": status}
    return ClientError(
        {
            "Error": {"Code": code, "Message": "synthetic"},
            "ResponseMetadata": metadata,
        },
        "PutObject",
    )


@pytest.mark.parametrize("operation", ["upload", "read"])
@pytest.mark.parametrize(
    "signed_url",
    [
        "https://test-account.r2.cloudflarestorage.com/key?X-Amz-Signature=a%2Fb",
        "http://localhost:8787/key?X-Amz-Signature=abc",
        "https://127.0.0.1:443/key?X-Amz-Signature=abc",
        "https://[2001:db8::1]:443/key?X-Amz-Signature=abc",
        "https://b\N{LATIN SMALL LETTER U WITH DIAERESIS}cher.example/key?X-Amz-Signature=abc",
        "https://example.com./key?X-Amz-Signature=abc",
    ],
)
def test_direct_upload_and_read_signing_preserve_valid_provider_urls_and_contract(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    signed_url: str,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class Client:
        def generate_presigned_url(self, client_method: str, **kwargs):
            calls.append((client_method, kwargs))
            return signed_url

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    recorder = MetricsRecorder("api", "test", "r2-signing-contract")

    with metrics_context(recorder):
        result = _create_signed_url(operation, config=_config())

    if operation == "upload":
        assert result.upload_url == signed_url
        assert result.upload_headers == {"Content-Type": "image/png"}
        assert calls == [
            (
                "put_object",
                {
                    "Params": {
                        "Bucket": "test-bucket",
                        "Key": "staging/key.png",
                        "ContentType": "image/png",
                    },
                    "ExpiresIn": 900,
                    "HttpMethod": "PUT",
                },
            )
        ]
        expected_metric_operation = "r2.upload_url.create"
    else:
        assert result == signed_url
        assert calls == [
            (
                "get_object",
                {
                    "Params": {
                        "Bucket": "test-bucket",
                        "Key": "published/key.png",
                    },
                    "ExpiresIn": 3600,
                    "HttpMethod": "GET",
                },
            )
        ]
        expected_metric_operation = "r2.read_url.create"
    (series,) = recorder.snapshot().series
    assert dict(series.dimensions) == {
        "operation": expected_metric_operation,
        "provider_kind": "r2",
        "result": "succeeded",
    }


@pytest.mark.parametrize("operation", ["upload", "read"])
@pytest.mark.parametrize(
    "signed_url",
    [
        None,
        "",
        " https://example.com/key ",
        "https://user@example.com/key",
        "https://example.com/key#fragment",
        "https://example.com:0/key",
        "https://example.com:65536/key",
        "https://example.com:not-a-port/key",
        "https://127.1/key",
        "https://0x7f000001/key",
        "ftp://example.com/key",
        "/relative/key",
        "https://example.com/key\nheader",
    ],
)
def test_direct_upload_and_read_signing_reject_invalid_provider_urls(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    signed_url: object,
) -> None:
    class Client:
        def generate_presigned_url(self, *args, **kwargs):
            return signed_url

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    recorder = MetricsRecorder("api", "test", "r2-signing-contract")

    with metrics_context(recorder), pytest.raises(r2.R2StorageError):
        _create_signed_url(operation, config=_config())

    (series,) = recorder.snapshot().series
    assert dict(series.dimensions)["result"] == "failed"


@pytest.mark.parametrize("operation", ["upload", "read"])
def test_direct_upload_and_read_signing_preserve_cancellation(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    cancellation = asyncio.CancelledError()

    class Client:
        def generate_presigned_url(self, *args, **kwargs):
            raise cancellation

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    recorder = MetricsRecorder("api", "test", "r2-signing-contract")

    with metrics_context(recorder), pytest.raises(asyncio.CancelledError) as exc_info:
        _create_signed_url(operation, config=_config())

    assert exc_info.value is cancellation
    assert recorder.snapshot().series == ()


@pytest.mark.parametrize("operation", ["upload", "read"])
def test_direct_signing_target_mismatch_prevents_client_construction(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    monkeypatch.setattr(
        r2,
        "get_r2_client",
        lambda config: pytest.fail("target mismatch reached client construction"),
    )
    target = r2.R2StorageTarget("r2", "other-account", "test-bucket")

    with pytest.raises(r2.R2StorageTargetMismatchError):
        if operation == "upload":
            r2.create_object_upload_url(
                target=target,
                object_key="staging/key.png",
                content_type="image/png",
                config=_config(),
            )
        else:
            r2.create_object_read_url(
                target=target,
                object_key="published/key.png",
                config=_config(),
            )


def test_target_mismatch_prevents_client_construction(monkeypatch) -> None:
    monkeypatch.setattr(r2, "get_r2_storage_config", _config)
    constructed = False

    def fail_client(*args, **kwargs):
        nonlocal constructed
        constructed = True

    monkeypatch.setattr(r2, "get_r2_client", fail_client)
    with pytest.raises(r2.R2StorageTargetMismatchError):
        r2.download_object(
            target=r2.R2StorageTarget("r2", "other", "test-bucket"),
            object_key="staging/key.png",
            expected_size_bytes=3,
            expected_content_type="image/png",
            max_bytes=10,
        )
    assert constructed is False


@pytest.mark.parametrize(
    ("target", "config"),
    [
        (r2.R2StorageTarget("s3", "test-account", "test-bucket"), _config()),
        (r2.R2StorageTarget("r2", "other", "test-bucket"), _config()),
        (r2.R2StorageTarget("r2", "test-account", "other"), _config()),
        (
            _target(),
            r2.R2StorageConfig(
                **{
                    **_config().__dict__,
                    "endpoint_url": "https://other.r2.cloudflarestorage.com",
                }
            ),
        ),
        (
            _target(),
            r2.R2StorageConfig(
                **{
                    **_config().__dict__,
                    "endpoint_url": (
                        "https://test-account.r2.cloudflarestorage.com/path"
                    ),
                }
            ),
        ),
    ],
)
def test_every_target_identity_mismatch_prevents_client_construction(
    monkeypatch: pytest.MonkeyPatch,
    target: r2.R2StorageTarget,
    config: r2.R2StorageConfig,
) -> None:
    client = pytest.fail
    monkeypatch.setattr(r2, "get_r2_client", client)

    with pytest.raises(r2.R2StorageTargetMismatchError):
        r2.download_object(
            target=target,
            object_key="staging/key.png",
            expected_size_bytes=3,
            expected_content_type="image/png",
            max_bytes=10,
            config=config,
        )


def test_bounded_download_validates_and_closes_body(monkeypatch) -> None:
    body = _Body(b"abc")

    class Client:
        def get_object(self, **kwargs):
            assert kwargs == {"Bucket": "test-bucket", "Key": "staging/key.png"}
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": body,
                "ContentLength": 3,
                "ContentType": "image/png",
                "ETag": '"etag"',
            }

    monkeypatch.setattr(r2, "get_r2_storage_config", _config)
    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    result = r2.download_object(
        target=_target(),
        object_key="staging/key.png",
        expected_size_bytes=3,
        expected_content_type="image/png",
        max_bytes=10,
    )
    assert result.body == b"abc"
    assert body.closed_by_adapter is True
    assert body.read_sizes == [11]


def test_download_rejects_a_readable_body_without_a_close_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = _ReadOnlyBody(b"abc")

    class Client:
        def get_object(self, **kwargs):
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": body,
                "ContentLength": 3,
                "ContentType": "image/png",
                "ETag": '"etag"',
            }

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    recorder = MetricsRecorder("api", "test", "r2-download-close-contract")

    with metrics_context(recorder), pytest.raises(r2.R2StorageError):
        r2.download_object(
            target=_target(),
            object_key="staging/key.png",
            expected_size_bytes=3,
            expected_content_type="image/png",
            max_bytes=10,
            config=_config(),
        )

    assert body.read_sizes == []
    (series,) = recorder.snapshot().series
    assert dict(series.dimensions)["result"] == "failed"


def test_download_close_failure_does_not_replace_a_successful_read_or_metric(
    monkeypatch,
) -> None:
    body = _CloseFailingBody(b"abc")

    class Client:
        def get_object(self, **kwargs):
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": body,
                "ContentLength": 3,
                "ContentType": "image/png",
                "ETag": '"etag"',
            }

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    recorder = MetricsRecorder("api", "test", "r2-download-close-test")

    with metrics_context(recorder):
        downloaded = r2.download_object(
            target=_target(),
            object_key="staging/key.png",
            expected_size_bytes=3,
            expected_content_type="image/png",
            max_bytes=10,
            config=_config(),
        )

    assert downloaded.body == b"abc"
    assert body.closed_by_adapter is True
    (series,) = recorder.snapshot().series
    assert dict(series.dimensions)["result"] == "succeeded"


def test_download_close_cancellation_propagates_and_records_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cancellation = asyncio.CancelledError()
    body = _CloseCancellingBody(b"abc", cancellation)

    class Client:
        def get_object(self, **kwargs):
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": body,
                "ContentLength": 3,
                "ContentType": "image/png",
                "ETag": '"etag"',
            }

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    recorder = MetricsRecorder("api", "test", "r2-download-close-cancellation")

    with metrics_context(recorder), pytest.raises(asyncio.CancelledError) as raised:
        r2.download_object(
            target=_target(),
            object_key="staging/key.png",
            expected_size_bytes=3,
            expected_content_type="image/png",
            max_bytes=10,
            config=_config(),
        )

    assert raised.value is cancellation
    assert body.closed_by_adapter is True
    (series,) = recorder.snapshot().series
    assert dict(series.dimensions)["result"] == "failed"


@pytest.mark.parametrize(
    ("read_failure", "expected_error"),
    [
        (OSError("synthetic stream failure"), r2.R2StorageError),
        (asyncio.CancelledError(), asyncio.CancelledError),
    ],
)
def test_download_close_failure_does_not_replace_the_original_failure_or_metric(
    monkeypatch,
    read_failure: BaseException,
    expected_error: type[BaseException],
) -> None:
    body = _CloseFailingBody(b"abc", read_failure=read_failure)

    class Client:
        def get_object(self, **kwargs):
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": body,
                "ContentLength": 3,
                "ContentType": "image/png",
            }

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    recorder = MetricsRecorder("api", "test", "r2-download-close-test")

    with metrics_context(recorder), pytest.raises(expected_error) as exc_info:
        r2.download_object(
            target=_target(),
            object_key="staging/key.png",
            expected_size_bytes=3,
            expected_content_type="image/png",
            max_bytes=10,
            config=_config(),
        )

    assert body.closed_by_adapter is True
    if isinstance(read_failure, asyncio.CancelledError):
        assert exc_info.value is read_failure
    else:
        assert exc_info.value.__cause__ is read_failure
    (series,) = recorder.snapshot().series
    assert dict(series.dimensions)["result"] == "failed"


def test_download_rejects_malformed_and_mismatched_length(monkeypatch) -> None:
    responses = iter(
        [
            {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": _Body(b"abc"),
                "ContentLength": True,
            },
            {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": _Body(b"abc"),
                "ContentLength": 4,
                "ContentType": "image/png",
            },
        ]
    )

    class Client:
        def get_object(self, **kwargs):
            return next(responses)

    monkeypatch.setattr(r2, "get_r2_storage_config", _config)
    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    call = lambda: r2.download_object(
        target=_target(),
        object_key="staging/key.png",
        expected_size_bytes=3,
        expected_content_type="image/png",
        max_bytes=10,
    )
    with pytest.raises(r2.R2StorageError):
        call()
    with pytest.raises(r2.ImageUploadMismatchError):
        call()


@pytest.mark.parametrize("content_length", [None, "3", True, -1])
def test_download_rejects_each_malformed_content_length_and_closes_body(
    monkeypatch: pytest.MonkeyPatch,
    content_length: object,
) -> None:
    body = _Body(b"abc")

    class Client:
        def get_object(self, **kwargs):
            response = {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": body,
                "ContentType": "image/png",
                "ETag": '"etag"',
            }
            if content_length is not None:
                response["ContentLength"] = content_length
            return response

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    recorder = MetricsRecorder("api", "test", "r2-download-test")

    with metrics_context(recorder), pytest.raises(r2.R2StorageError):
        r2.download_object(
            target=_target(),
            object_key="staging/key.png",
            expected_size_bytes=3,
            expected_content_type="image/png",
            max_bytes=10,
            config=_config(),
        )

    assert body.closed_by_adapter is True
    assert body.read_sizes == []
    (series,) = recorder.snapshot().series
    assert dict(series.dimensions)["result"] == "failed"


@pytest.mark.parametrize(
    ("content_length", "content", "expected_size", "content_type"),
    [
        (0, b"", 0, "image/png"),
        (11, b"x" * 11, 11, "image/png"),
        (3, b"ab", 3, "image/png"),
        (3, b"abcd", 3, "image/png"),
        (3, b"abc", 4, "image/png"),
        (3, b"abc", 3, "image/jpeg"),
        (3, b"abc", 3, ""),
        (3, b"abc", 3, "   "),
    ],
)
def test_download_rejects_each_bounded_upload_mismatch_and_closes_body(
    monkeypatch: pytest.MonkeyPatch,
    content_length: int,
    content: bytes,
    expected_size: int,
    content_type: str,
) -> None:
    body = _Body(content)

    class Client:
        def get_object(self, **kwargs):
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": body,
                "ContentLength": content_length,
                "ContentType": content_type,
            }

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    recorder = MetricsRecorder("api", "test", "r2-download-test")

    with metrics_context(recorder), pytest.raises(r2.ImageUploadMismatchError):
        r2.download_object(
            target=_target(),
            object_key="staging/key.png",
            expected_size_bytes=expected_size,
            expected_content_type="image/png",
            max_bytes=10,
            config=_config(),
        )

    assert body.closed_by_adapter is True
    if (
        1 <= content_length <= 10
        and content_length == expected_size
        and content_type == "image/png"
    ):
        assert body.read_sizes == [11]
    else:
        assert body.read_sizes == []
    (series,) = recorder.snapshot().series
    assert dict(series.dimensions)["result"] == "failed"


@pytest.mark.parametrize(
    ("failure", "expected_error"),
    [
        (OSError("synthetic stream failure"), r2.R2StorageError),
        (asyncio.CancelledError(), asyncio.CancelledError),
    ],
)
def test_download_closes_stream_on_transport_error_and_cancellation(
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
    expected_error: type[BaseException],
) -> None:
    class FailingBody(_Body):
        def read(self, size: int = -1) -> bytes:
            self.read_sizes.append(size)
            raise failure

    body = FailingBody(b"abc")

    class Client:
        def get_object(self, **kwargs):
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": body,
                "ContentLength": 3,
                "ContentType": "image/png",
            }

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())

    with pytest.raises(expected_error):
        r2.download_object(
            target=_target(),
            object_key="staging/key.png",
            expected_size_bytes=3,
            expected_content_type="image/png",
            max_bytes=10,
            config=_config(),
        )

    assert body.closed_by_adapter is True
    assert body.read_sizes == [11]


@pytest.mark.parametrize("response_status", [None, True, 204])
def test_download_requires_an_exact_normal_http_200_response(
    monkeypatch: pytest.MonkeyPatch,
    response_status: object,
) -> None:
    body = _Body(b"abc")

    class Client:
        def get_object(self, **kwargs):
            metadata = (
                {} if response_status is None else {"HTTPStatusCode": response_status}
            )
            return {
                "ResponseMetadata": metadata,
                "Body": body,
                "ContentLength": 3,
                "ContentType": "image/png",
            }

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    with pytest.raises(r2.R2StorageError):
        r2.download_object(
            target=_target(),
            object_key="staging/key.png",
            expected_size_bytes=3,
            expected_content_type="image/png",
            max_bytes=10,
            config=_config(),
        )
    assert body.closed_by_adapter is True
    assert body.read_sizes == []


def test_download_non_byte_body_is_a_provider_failure_not_upload_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class TextBody(_Body):
        def read(self, size: int = -1) -> str:
            self.read_sizes.append(size)
            return "abc"

    body = TextBody(b"abc")

    class Client:
        def get_object(self, **kwargs):
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": body,
                "ContentLength": 3,
                "ContentType": "image/png",
            }

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    with pytest.raises(r2.R2StorageError):
        r2.download_object(
            target=_target(),
            object_key="staging/key.png",
            expected_size_bytes=3,
            expected_content_type="image/png",
            max_bytes=10,
            config=_config(),
        )
    assert body.closed_by_adapter is True


@pytest.mark.parametrize(
    ("status_code", "error_code", "expected_error", "expected_result"),
    [
        (404, "", r2.R2ObjectNotFoundError, "not_found"),
        (404, "NoSuchKey", r2.R2ObjectNotFoundError, "not_found"),
        (404, "AccessDenied", r2.R2StorageError, "failed"),
        (503, "NoSuchKey", r2.R2StorageError, "failed"),
        (None, "NoSuchKey", r2.R2StorageError, "failed"),
        (429, "SlowDown", r2.R2StorageError, "rate_limited"),
        (429, "NoSuchKey", r2.R2StorageError, "failed"),
        (503, "SlowDown", r2.R2StorageError, "rate_limited"),
    ],
)
def test_download_uses_coherent_status_and_error_code_classification(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int | None,
    error_code: str,
    expected_error: type[Exception],
    expected_result: str,
) -> None:
    class Client:
        def get_object(self, **kwargs):
            raise _client_error(status_code, error_code)

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    recorder = MetricsRecorder("api", "test", "r2-download-test")
    with metrics_context(recorder), pytest.raises(expected_error):
        r2.download_object(
            target=_target(),
            object_key="staging/key.png",
            expected_size_bytes=3,
            expected_content_type="image/png",
            max_bytes=10,
            config=_config(),
        )
    assert dict(recorder.snapshot().series[0].dimensions)["result"] == expected_result


def test_conditional_publication_collision_never_retries(monkeypatch) -> None:
    calls = 0

    class Client:
        def put_object(self, **kwargs):
            nonlocal calls
            calls += 1
            assert kwargs["IfNoneMatch"] == "*"
            raise _client_error(412, "PreconditionFailed")

    monkeypatch.setattr(r2, "get_r2_storage_config", _config)
    monkeypatch.setattr(
        r2,
        "get_r2_client",
        lambda config, *, disable_retries=False: Client(),
    )
    with pytest.raises(r2.R2PublicationCollisionError):
        r2.publish_object(
            target=_target(),
            object_key="published/attempt.png",
            body=b"sanitized",
            content_type="image/png",
        )
    assert calls == 1


@pytest.mark.parametrize(
    ("status_code", "error_code"),
    [
        (408, "RequestTimeout"),
        (408, "PreconditionFailed"),
        (409, "Conflict"),
        (409, "PreconditionFailed"),
        (500, "InternalError"),
        (503, "SlowDown"),
        (None, "PreconditionFailed"),
        (None, "SlowDown"),
        (400, "PreconditionFailed"),
        (429, "PreconditionFailed"),
        (412, "SlowDown"),
        (412, "AccessDenied"),
    ],
)
def test_ambiguous_or_contradictory_publication_response_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int | None,
    error_code: str,
) -> None:
    class Client:
        def put_object(self, **kwargs):
            assert kwargs["IfNoneMatch"] == "*"
            raise _client_error(status_code, error_code)

    monkeypatch.setattr(r2, "get_r2_storage_config", _config)
    monkeypatch.setattr(
        r2,
        "get_r2_client",
        lambda config, *, disable_retries=False: Client(),
    )
    recorder = MetricsRecorder("api", "test", "r2-publication-test")

    with metrics_context(recorder), pytest.raises(r2.R2MutationOutcomeUnknownError):
        r2.publish_object(
            target=_target(),
            object_key="published/attempt.png",
            body=b"sanitized",
            content_type="image/png",
        )

    (series,) = recorder.snapshot().series
    assert dict(series.dimensions) == {
        "operation": "r2.object.publish",
        "provider_kind": "r2",
        "result": "unknown_outcome",
    }


def test_only_confirmed_http_412_is_a_publication_collision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Client:
        def put_object(self, **kwargs):
            raise _client_error(412, "PreconditionFailed")

    monkeypatch.setattr(r2, "get_r2_storage_config", _config)
    monkeypatch.setattr(
        r2,
        "get_r2_client",
        lambda config, *, disable_retries=False: Client(),
    )
    recorder = MetricsRecorder("api", "test", "r2-publication-test")

    with metrics_context(recorder), pytest.raises(r2.R2PublicationCollisionError):
        r2.publish_object(
            target=_target(),
            object_key="published/attempt.png",
            body=b"sanitized",
            content_type="image/png",
        )

    (series,) = recorder.snapshot().series
    assert dict(series.dimensions) == {
        "operation": "r2.object.publish",
        "provider_kind": "r2",
        "result": "failed",
    }


@pytest.mark.parametrize(
    ("status_code", "error_code", "expected_result"),
    [
        (400, "InvalidRequest", "failed"),
        (403, "AccessDenied", "failed"),
        (400, "SlowDown", "rate_limited"),
        (429, "TooManyRequests", "rate_limited"),
    ],
)
def test_definite_publication_rejections_keep_exact_result(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    error_code: str,
    expected_result: str,
) -> None:
    class Client:
        def put_object(self, **kwargs):
            raise _client_error(status_code, error_code)

    monkeypatch.setattr(
        r2,
        "get_r2_client",
        lambda config, *, disable_retries=False: Client(),
    )
    recorder = MetricsRecorder("api", "test", "r2-publication-test")

    with metrics_context(recorder), pytest.raises(r2.R2StorageError) as exc_info:
        r2.publish_object(
            target=_target(),
            object_key="published/attempt.png",
            body=b"sanitized",
            content_type="image/png",
            config=_config(),
        )

    assert exc_info.value.result == expected_result
    (series,) = recorder.snapshot().series
    assert dict(series.dimensions)["result"] == expected_result


@pytest.mark.parametrize(
    "response",
    [
        None,
        {},
        {"ResponseMetadata": {"HTTPStatusCode": 200}, "ETag": None},
        {"ResponseMetadata": {"HTTPStatusCode": 200}, "ETag": " "},
        {"ETag": '"etag"'},
        {"ResponseMetadata": {}, "ETag": '"etag"'},
        {"ResponseMetadata": {"HTTPStatusCode": "200"}, "ETag": '"etag"'},
        {"ResponseMetadata": {"HTTPStatusCode": True}, "ETag": '"etag"'},
        {"ResponseMetadata": {"HTTPStatusCode": 500}, "ETag": '"etag"'},
    ],
)
def test_malformed_publication_success_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
    response: object,
) -> None:
    class Client:
        def put_object(self, **kwargs):
            return response

    monkeypatch.setattr(
        r2,
        "get_r2_client",
        lambda config, *, disable_retries=False: Client(),
    )
    recorder = MetricsRecorder("api", "test", "r2-publication-test")

    with metrics_context(recorder), pytest.raises(r2.R2MutationOutcomeUnknownError):
        r2.publish_object(
            target=_target(),
            object_key="published/attempt.png",
            body=b"sanitized",
            content_type="image/png",
            config=_config(),
        )

    (series,) = recorder.snapshot().series
    assert dict(series.dimensions)["result"] == "unknown_outcome"


def test_publication_requires_coherent_http_success_and_etag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Client:
        def put_object(self, **kwargs):
            assert kwargs["IfNoneMatch"] == "*"
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "ETag": ' "etag" ',
            }

    monkeypatch.setattr(
        r2,
        "get_r2_client",
        lambda config, *, disable_retries=False: Client(),
    )
    recorder = MetricsRecorder("api", "test", "r2-publication-test")

    with metrics_context(recorder):
        published = r2.publish_object(
            target=_target(),
            object_key="published/attempt.png",
            body=b"sanitized",
            content_type="image/png",
            config=_config(),
        )

    assert published.etag == '"etag"'
    (series,) = recorder.snapshot().series
    assert dict(series.dimensions)["result"] == "succeeded"


@pytest.mark.parametrize("operation", ["download", "publish", "delete"])
def test_normal_responses_with_error_metadata_are_not_accepted_as_success(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    body = _Body(b"abc")

    class Client:
        def get_object(self, **kwargs):
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Error": {"Code": "NoSuchKey", "Message": "contradictory"},
                "Body": body,
                "ContentLength": 3,
                "ContentType": "image/png",
                "ETag": '"etag"',
            }

        def put_object(self, **kwargs):
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Error": {"Code": "PreconditionFailed", "Message": "contradictory"},
                "ETag": '"etag"',
            }

        def delete_object(self, **kwargs):
            return {
                "ResponseMetadata": {"HTTPStatusCode": 204},
                "Error": {"Code": "AccessDenied", "Message": "contradictory"},
            }

    monkeypatch.setattr(
        r2,
        "get_r2_client",
        lambda config, *, disable_retries=False: Client(),
    )

    if operation == "download":
        with pytest.raises(r2.R2StorageError):
            r2.download_object(
                target=_target(),
                object_key="staging/key.png",
                expected_size_bytes=3,
                expected_content_type="image/png",
                max_bytes=10,
                config=_config(),
            )
        assert body.closed_by_adapter is True
    elif operation == "publish":
        with pytest.raises(r2.R2MutationOutcomeUnknownError):
            r2.publish_object(
                target=_target(),
                object_key="published/key.png",
                body=b"sanitized",
                content_type="image/png",
                config=_config(),
            )
    else:
        with pytest.raises(r2.R2MutationOutcomeUnknownError):
            r2.delete_object(
                target=_target(),
                object_key="staging/key.png",
                config=_config(),
            )


def test_publication_transport_failure_and_cancellation_after_dispatch_are_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = iter(
        [
            EndpointConnectionError(endpoint_url="https://example.invalid"),
            asyncio.CancelledError(),
        ]
    )

    class Client:
        def put_object(self, **kwargs):
            raise next(failures)

    monkeypatch.setattr(
        r2,
        "get_r2_client",
        lambda config, *, disable_retries=False: Client(),
    )
    first = MetricsRecorder("api", "test", "r2-publication-test")
    with metrics_context(first), pytest.raises(r2.R2MutationOutcomeUnknownError):
        r2.publish_object(
            target=_target(),
            object_key="published/first.png",
            body=b"sanitized",
            content_type="image/png",
            config=_config(),
        )
    assert dict(first.snapshot().series[0].dimensions)["result"] == "unknown_outcome"

    second = MetricsRecorder("api", "test", "r2-publication-test")
    with metrics_context(second), pytest.raises(asyncio.CancelledError):
        r2.publish_object(
            target=_target(),
            object_key="published/second.png",
            body=b"sanitized",
            content_type="image/png",
            config=_config(),
        )
    assert dict(second.snapshot().series[0].dimensions)["result"] == "unknown_outcome"


def test_publication_cancellation_before_dispatch_has_no_provider_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        r2,
        "get_r2_client",
        lambda *args, **kwargs: (_ for _ in ()).throw(asyncio.CancelledError()),
    )
    recorder = MetricsRecorder("api", "test", "r2-publication-test")

    with metrics_context(recorder), pytest.raises(asyncio.CancelledError):
        r2.publish_object(
            target=_target(),
            object_key="published/attempt.png",
            body=b"sanitized",
            content_type="image/png",
            config=_config(),
        )

    assert recorder.snapshot().series == ()


def test_publish_timeout_is_unknown_and_delete_is_idempotent(monkeypatch) -> None:
    deletes = 0

    class Client:
        def put_object(self, **kwargs):
            raise ReadTimeoutError(endpoint_url="https://example.invalid")

        def delete_object(self, **kwargs):
            nonlocal deletes
            deletes += 1
            return {"ResponseMetadata": {"HTTPStatusCode": 204}}

    client = Client()
    monkeypatch.setattr(r2, "get_r2_storage_config", _config)
    monkeypatch.setattr(
        r2,
        "get_r2_client",
        lambda config, *, disable_retries=False: client,
    )
    with pytest.raises(DependencyMutationTimeoutUnknownError):
        r2.publish_object(
            target=_target(),
            object_key="published/attempt.png",
            body=b"sanitized",
            content_type="image/png",
        )
    r2.delete_object(target=_target(), object_key="staging/key.png")
    r2.delete_object(target=_target(), object_key="staging/key.png")
    assert deletes == 2


@pytest.mark.parametrize(
    ("failure", "expected_error", "expected_result"),
    [
        (_client_error(404, ""), None, "succeeded"),
        (_client_error(404, "NoSuchKey"), None, "succeeded"),
        (_client_error(400, "InvalidRequest"), r2.R2StorageError, "failed"),
        (_client_error(400, "SlowDown"), r2.R2StorageError, "rate_limited"),
        (_client_error(429, "SlowDown"), r2.R2StorageError, "rate_limited"),
        (
            _client_error(404, "AccessDenied"),
            r2.R2MutationOutcomeUnknownError,
            "unknown_outcome",
        ),
        (
            _client_error(429, "NoSuchKey"),
            r2.R2MutationOutcomeUnknownError,
            "unknown_outcome",
        ),
        (
            _client_error(None, "NoSuchKey"),
            r2.R2MutationOutcomeUnknownError,
            "unknown_outcome",
        ),
        (
            _client_error(408, "RequestTimeout"),
            r2.R2MutationOutcomeUnknownError,
            "unknown_outcome",
        ),
        (
            _client_error(503, "SlowDown"),
            r2.R2MutationOutcomeUnknownError,
            "unknown_outcome",
        ),
        (
            _client_error(503, "NoSuchKey"),
            r2.R2MutationOutcomeUnknownError,
            "unknown_outcome",
        ),
        (
            EndpointConnectionError(endpoint_url="https://example.invalid"),
            r2.R2MutationOutcomeUnknownError,
            "unknown_outcome",
        ),
    ],
)
def test_deletion_outcomes_are_classified_once(
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
    expected_error: type[BaseException] | None,
    expected_result: str,
) -> None:
    class Client:
        def delete_object(self, **kwargs):
            raise failure

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    recorder = MetricsRecorder("api", "test", "r2-deletion-test")

    with metrics_context(recorder):
        if expected_error is None:
            r2.delete_object(
                target=_target(), object_key="staging/key.png", config=_config()
            )
        else:
            with pytest.raises(expected_error):
                r2.delete_object(
                    target=_target(), object_key="staging/key.png", config=_config()
                )

    (series,) = recorder.snapshot().series
    assert dict(series.dimensions)["result"] == expected_result


@pytest.mark.parametrize("response", [None, {}, {"ResponseMetadata": {}}])
def test_malformed_deletion_success_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
    response: object,
) -> None:
    class Client:
        def delete_object(self, **kwargs):
            return response

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())

    with pytest.raises(r2.R2MutationOutcomeUnknownError):
        r2.delete_object(
            target=_target(), object_key="staging/key.png", config=_config()
        )


def test_deletion_cancellation_is_classified_only_after_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Client:
        def delete_object(self, **kwargs):
            raise asyncio.CancelledError()

    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    dispatched = MetricsRecorder("api", "test", "r2-deletion-test")
    with metrics_context(dispatched), pytest.raises(asyncio.CancelledError):
        r2.delete_object(
            target=_target(), object_key="staging/key.png", config=_config()
        )
    assert dict(dispatched.snapshot().series[0].dimensions)["result"] == (
        "unknown_outcome"
    )

    monkeypatch.setattr(
        r2,
        "get_r2_client",
        lambda *args, **kwargs: (_ for _ in ()).throw(asyncio.CancelledError()),
    )
    prevented = MetricsRecorder("api", "test", "r2-deletion-test")
    with metrics_context(prevented), pytest.raises(asyncio.CancelledError):
        r2.delete_object(
            target=_target(), object_key="staging/key.png", config=_config()
        )
    assert prevented.snapshot().series == ()


@pytest.mark.parametrize(
    ("publication", "failure_message"),
    [(True, "publication setup failed"), (False, "deletion setup failed")],
)
def test_mutation_failure_before_sdk_invocation_is_definite_failed(
    monkeypatch: pytest.MonkeyPatch,
    publication: bool,
    failure_message: str,
) -> None:
    monkeypatch.setattr(
        r2,
        "get_r2_client",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError(failure_message)),
    )
    recorder = MetricsRecorder("api", "test", "r2-mutation-test")
    with metrics_context(recorder), pytest.raises(r2.R2StorageError) as exc_info:
        if publication:
            r2.publish_object(
                target=_target(),
                object_key="published/attempt.png",
                body=b"sanitized",
                content_type="image/png",
                config=_config(),
            )
        else:
            r2.delete_object(
                target=_target(), object_key="staging/key.png", config=_config()
            )
    assert exc_info.value.result == "failed"
    assert dict(recorder.snapshot().series[0].dimensions)["result"] == "failed"
