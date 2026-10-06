from __future__ import annotations

import pytest
from botocore.exceptions import ConnectTimeoutError, ReadTimeoutError

from backend.observability.timeouts import (
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
)
from backend.services import r2_storage_service as r2

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.pass_provenance("WS06-02"),
]


def _config() -> r2.R2StorageConfig:
    return r2.R2StorageConfig(
        account_id="timeout-account",
        access_key_id="access",
        secret_access_key="secret",
        endpoint_url="https://timeout-account.r2.cloudflarestorage.com",
        bucket_name="timeout-bucket",
        upload_url_minutes=15,
        read_url_minutes=60,
        max_image_bytes=1024,
        allowed_image_types=frozenset({"image/png"}),
        object_connect_timeout_seconds=3,
        object_read_timeout_seconds=8,
    )


def _target() -> r2.R2StorageTarget:
    return r2.R2StorageTarget("r2", "timeout-account", "timeout-bucket")


def test_object_timeouts_reach_botocore_client(monkeypatch) -> None:
    captured = {}

    def client(*args, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(r2.boto3, "client", client)
    r2.get_r2_client(_config(), disable_retries=True)
    sdk_config = captured["config"]
    assert sdk_config.connect_timeout == 3
    assert sdk_config.read_timeout == 8
    assert sdk_config.retries["total_max_attempts"] == 1


def test_download_timeout_is_retryable_read(monkeypatch) -> None:
    class Client:
        def get_object(self, **kwargs):
            raise ReadTimeoutError(endpoint_url="https://example.invalid")

    monkeypatch.setattr(r2, "get_r2_storage_config", _config)
    monkeypatch.setattr(r2, "get_r2_client", lambda config: Client())
    with pytest.raises(DependencyReadTimeoutError) as exc_info:
        r2.download_object(
            target=_target(),
            object_key="staging/key",
            expected_size_bytes=3,
            expected_content_type="image/png",
            max_bytes=10,
        )
    assert exc_info.value.operation == "r2.object.download"


@pytest.mark.parametrize("operation", ["publish", "delete"])
@pytest.mark.parametrize("timeout_type", [ConnectTimeoutError, ReadTimeoutError])
def test_mutation_timeout_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    timeout_type: type[ConnectTimeoutError | ReadTimeoutError],
) -> None:
    class Client:
        def put_object(self, **kwargs):
            raise timeout_type(endpoint_url="https://example.invalid")

        def delete_object(self, **kwargs):
            raise timeout_type(endpoint_url="https://example.invalid")

    monkeypatch.setattr(r2, "get_r2_storage_config", _config)
    monkeypatch.setattr(
        r2,
        "get_r2_client",
        lambda config, *, disable_retries=False: Client(),
    )
    with pytest.raises(DependencyMutationTimeoutUnknownError) as exc_info:
        if operation == "publish":
            r2.publish_object(
                target=_target(),
                object_key="published/attempt",
                body=b"bytes",
                content_type="image/png",
            )
        else:
            r2.delete_object(target=_target(), object_key="staging/key")
    assert exc_info.value.operation == f"r2.object.{operation}"
