"""Real, isolated Cloudflare R2 object-semantics contract.

Run only through ``backend.test_runner test provider_contract``.
"""

from __future__ import annotations

import os
import sys
import uuid
from collections.abc import Callable

import pytest
from botocore.exceptions import BotoCoreError, ClientError

from backend.services.r2_storage_service import (
    R2PublicationCollisionError,
    R2StorageConfig,
    R2StorageError,
    delete_object,
    download_object,
    get_r2_client,
    publish_object,
    storage_target_from_config,
)

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.pass_provenance("WS06-02"),
]

_R2_CONTRACT_PREFIX_ROOT = "provider-contract/r2-object-semantics/"
_R2_CONTRACT_OBJECT_NAMES = (
    "staging.bin",
    "publication.bin",
    "collision.bin",
)


class R2ContractCleanupError(RuntimeError):
    """Raised when an otherwise successful R2 proof cannot clean up."""


def _r2_contract_object_keys(run_id: uuid.UUID) -> tuple[str, tuple[str, ...]]:
    prefix = f"{_R2_CONTRACT_PREFIX_ROOT}{run_id}/"
    return prefix, tuple(f"{prefix}{name}" for name in _R2_CONTRACT_OBJECT_NAMES)


def _is_isolated_r2_contract_prefix(prefix: str) -> bool:
    if not prefix.startswith(_R2_CONTRACT_PREFIX_ROOT) or not prefix.endswith(
        "/"
    ):
        return False
    run_id = prefix[len(_R2_CONTRACT_PREFIX_ROOT) : -1]
    try:
        return str(uuid.UUID(run_id)) == run_id
    except ValueError:
        return False


def _cleanup_r2_contract_objects(
    *,
    prefix: str,
    object_keys: tuple[str, ...],
    delete_exact_key: Callable[[str], None],
) -> None:
    primary_error = sys.exception()
    expected_keys = tuple(
        f"{prefix}{name}" for name in _R2_CONTRACT_OBJECT_NAMES
    )
    if (
        not _is_isolated_r2_contract_prefix(prefix)
        or object_keys != expected_keys
    ):
        message = (
            "R2 provider-contract cleanup refused an invalid owned-key set."
        )
        if primary_error is not None:
            primary_error.add_note(message)
            return
        raise R2ContractCleanupError(message)

    cleanup_failure_count = 0
    for key in object_keys:
        try:
            delete_exact_key(key)
        except Exception:  # noqa: BLE001 - attempt every exact owned key.
            cleanup_failure_count += 1

    if not cleanup_failure_count:
        return

    message = (
        "R2 provider-contract exact-key cleanup failed for "
        f"{cleanup_failure_count} owned object(s)."
    )
    if primary_error is not None:
        primary_error.add_note(message)
        return
    raise R2ContractCleanupError(message)


def _r2_config() -> R2StorageConfig:
    """Build only the R2 contract config; this suite has no database dependency."""

    return R2StorageConfig(
        account_id=os.environ["R2_ACCOUNT_ID"],
        access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        bucket_name=os.environ["R2_BUCKET_NAME"],
        upload_url_minutes=15,
        read_url_minutes=60,
        max_image_bytes=8 * 1024 * 1024,
        allowed_image_types=frozenset({"image/jpeg", "image/png", "image/webp"}),
        object_connect_timeout_seconds=2,
        object_read_timeout_seconds=6,
    )


def test_real_r2_get_conditional_put_collision_and_idempotent_delete() -> None:
    config = _r2_config()
    target = storage_target_from_config(config)
    client = get_r2_client(config, disable_retries=True)
    prefix, owned_keys = _r2_contract_object_keys(uuid.uuid4())
    staging_key, publication_key, collision_key = owned_keys
    staging_bytes = b"r2-contract-staging"
    publication_bytes = b"r2-contract-publication"
    original_collision_bytes = b"r2-contract-original"

    try:
        client.put_object(
            Bucket=config.bucket_name,
            Key=staging_key,
            Body=staging_bytes,
            ContentType="image/png",
        )
        downloaded = download_object(
            target=target,
            object_key=staging_key,
            expected_size_bytes=len(staging_bytes),
            expected_content_type="image/png",
            max_bytes=1024,
            config=config,
        )
        assert downloaded.body == staging_bytes
        assert downloaded.size_bytes == len(staging_bytes)
        assert downloaded.content_type == "image/png"
        assert downloaded.etag

        result = publish_object(
            target=target,
            object_key=publication_key,
            body=publication_bytes,
            content_type="image/png",
            config=config,
        )
        assert result.etag
        stored = client.get_object(Bucket=config.bucket_name, Key=publication_key)
        try:
            assert stored["Body"].read() == publication_bytes
        finally:
            stored["Body"].close()

        client.put_object(
            Bucket=config.bucket_name,
            Key=collision_key,
            Body=original_collision_bytes,
            ContentType="image/png",
        )
        with pytest.raises(R2PublicationCollisionError):
            publish_object(
                target=target,
                object_key=collision_key,
                body=b"replacement-must-not-win",
                content_type="image/png",
                config=config,
            )
        collided = client.get_object(Bucket=config.bucket_name, Key=collision_key)
        try:
            assert collided["Body"].read() == original_collision_bytes
        finally:
            collided["Body"].close()

        delete_object(target=target, object_key=staging_key, config=config)
        delete_object(target=target, object_key=staging_key, config=config)
        with pytest.raises(ClientError) as absent:
            client.get_object(Bucket=config.bucket_name, Key=staging_key)
        assert absent.value.response.get("ResponseMetadata", {}).get(
            "HTTPStatusCode"
        ) == 404
    except (BotoCoreError, ClientError, R2StorageError):
        pytest.fail(
            "The isolated R2 provider-contract operation failed.",
            pytrace=False,
        )
    finally:
        _cleanup_r2_contract_objects(
            prefix=prefix,
            object_keys=owned_keys,
            delete_exact_key=lambda key: delete_object(
                target=target,
                object_key=key,
                config=config,
            ),
        )
