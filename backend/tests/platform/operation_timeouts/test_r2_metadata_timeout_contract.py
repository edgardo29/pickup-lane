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
from backend.observability.timeouts import DependencyReadTimeoutError

pytestmark = pytest.mark.no_db_cleanup


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
