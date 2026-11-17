"""Live check against a real Cloudflare R2 test bucket.

Runs only with ``pytest --live``. Reads the R2_TEST_* keys from the environment
or backend/.env, and deletes every object it creates.
"""

import os
import uuid
from pathlib import Path

import pytest
from botocore.exceptions import ClientError
from dotenv import dotenv_values

from backend.services.r2_storage_service import (
    R2PublicationCollisionError,
    R2StorageConfig,
    delete_object,
    download_object,
    get_r2_client,
    publish_object,
    storage_target_from_config,
)

pytestmark = [pytest.mark.live, pytest.mark.enable_socket]

REPO_ROOT = Path(__file__).resolve().parents[3]
R2_TEST_SETTINGS = (
    "R2_TEST_ACCOUNT_ID",
    "R2_TEST_ACCESS_KEY_ID",
    "R2_TEST_SECRET_ACCESS_KEY",
    "R2_TEST_BUCKET_NAME",
    "R2_TEST_ENDPOINT_URL",
)


@pytest.fixture
def r2_config() -> R2StorageConfig:
    stored = dotenv_values(REPO_ROOT / "backend" / ".env")
    values = {
        name: os.environ.get(name) or stored.get(name) for name in R2_TEST_SETTINGS
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        pytest.fail(
            f"Set {', '.join(missing)} in backend/.env or the environment.",
            pytrace=False,
        )
    return R2StorageConfig(
        account_id=values["R2_TEST_ACCOUNT_ID"],
        access_key_id=values["R2_TEST_ACCESS_KEY_ID"],
        secret_access_key=values["R2_TEST_SECRET_ACCESS_KEY"],
        endpoint_url=values["R2_TEST_ENDPOINT_URL"].rstrip("/"),
        bucket_name=values["R2_TEST_BUCKET_NAME"],
        upload_url_minutes=15,
        read_url_minutes=60,
        max_image_bytes=8 * 1024 * 1024,
        allowed_image_types=frozenset({"image/jpeg", "image/png", "image/webp"}),
        object_connect_timeout_seconds=2,
        object_read_timeout_seconds=6,
    )


def test_real_r2_get_conditional_put_collision_and_idempotent_delete(
    r2_config: R2StorageConfig,
) -> None:
    config = r2_config
    target = storage_target_from_config(config)
    client = get_r2_client(config, disable_retries=True)
    prefix = f"cloudflare-r2/object-semantics/{uuid.uuid4()}/"
    owned_keys = tuple(
        f"{prefix}{name}"
        for name in ("staging.bin", "publication.bin", "collision.bin")
    )
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
        assert (
            absent.value.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            == 404
        )
    finally:
        for key in owned_keys:
            delete_object(target=target, object_key=key, config=config)
