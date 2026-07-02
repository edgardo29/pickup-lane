import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError


class R2StorageConfigError(RuntimeError):
    pass


class R2StorageError(RuntimeError):
    pass


class R2ObjectNotFoundError(R2StorageError):
    pass


@dataclass(frozen=True)
class R2ObjectUploadTicket:
    upload_url: str
    upload_headers: dict[str, str]
    object_url: str
    expires_at: datetime


@dataclass(frozen=True)
class R2ObjectProperties:
    content_type: str | None
    size_bytes: int
    etag: str | None


@dataclass(frozen=True)
class R2StorageConfig:
    account_id: str
    access_key_id: str
    secret_access_key: str
    endpoint_url: str
    bucket_name: str
    upload_url_minutes: int
    read_url_minutes: int
    max_image_bytes: int
    allowed_image_types: frozenset[str]


DEFAULT_ALLOWED_IMAGE_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise R2StorageConfigError(f"{name} must be an integer.") from exc


def get_allowed_image_types() -> frozenset[str]:
    configured_types = os.getenv("R2_ALLOWED_IMAGE_TYPES")
    if not configured_types:
        return DEFAULT_ALLOWED_IMAGE_TYPES

    return frozenset(
        content_type.strip().lower()
        for content_type in configured_types.split(",")
        if content_type.strip()
    )


def get_r2_storage_config() -> R2StorageConfig:
    account_id = os.getenv("R2_ACCOUNT_ID", "").strip()
    access_key_id = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
    endpoint_url = os.getenv("R2_ENDPOINT_URL", "").strip().rstrip("/")
    bucket_name = os.getenv("R2_BUCKET_NAME", "").strip()

    if not account_id:
        raise R2StorageConfigError("R2_ACCOUNT_ID is not set.")

    if not access_key_id:
        raise R2StorageConfigError("R2_ACCESS_KEY_ID is not set.")

    if not secret_access_key:
        raise R2StorageConfigError("R2_SECRET_ACCESS_KEY is not set.")

    if not endpoint_url:
        endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

    if not bucket_name:
        raise R2StorageConfigError("R2_BUCKET_NAME is not set.")

    return R2StorageConfig(
        account_id=account_id,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        endpoint_url=endpoint_url,
        bucket_name=bucket_name,
        upload_url_minutes=get_env_int("R2_UPLOAD_URL_MINUTES", 15),
        read_url_minutes=get_env_int("R2_READ_URL_MINUTES", 60),
        max_image_bytes=get_env_int("R2_MAX_IMAGE_BYTES", 8 * 1024 * 1024),
        allowed_image_types=get_allowed_image_types(),
    )


def get_r2_client(config: R2StorageConfig | None = None):
    storage_config = config or get_r2_storage_config()
    return boto3.client(
        "s3",
        endpoint_url=storage_config.endpoint_url,
        aws_access_key_id=storage_config.access_key_id,
        aws_secret_access_key=storage_config.secret_access_key,
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def build_object_url(
    object_key: str,
    config: R2StorageConfig | None = None,
) -> str:
    storage_config = config or get_r2_storage_config()
    encoded_object_key = quote(object_key, safe="/")
    return (
        f"{storage_config.endpoint_url}/"
        f"{storage_config.bucket_name}/{encoded_object_key}"
    )


def create_object_upload_url(
    *,
    object_key: str,
    content_type: str,
) -> R2ObjectUploadTicket:
    config = get_r2_storage_config()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=config.upload_url_minutes
    )

    try:
        upload_url = get_r2_client(config).generate_presigned_url(
            "put_object",
            Params={
                "Bucket": config.bucket_name,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=config.upload_url_minutes * 60,
            HttpMethod="PUT",
        )
    except (BotoCoreError, ClientError) as exc:
        raise R2StorageError("Cloudflare R2 could not create an upload URL.") from exc

    return R2ObjectUploadTicket(
        upload_url=upload_url,
        upload_headers={"Content-Type": content_type},
        object_url=build_object_url(object_key, config),
        expires_at=expires_at,
    )


def create_object_read_url(object_key: str) -> str:
    config = get_r2_storage_config()

    try:
        return get_r2_client(config).generate_presigned_url(
            "get_object",
            Params={
                "Bucket": config.bucket_name,
                "Key": object_key,
            },
            ExpiresIn=config.read_url_minutes * 60,
            HttpMethod="GET",
        )
    except (BotoCoreError, ClientError) as exc:
        raise R2StorageError("Cloudflare R2 could not create a read URL.") from exc


def get_object_properties(object_key: str) -> R2ObjectProperties:
    config = get_r2_storage_config()

    try:
        response = get_r2_client(config).head_object(
            Bucket=config.bucket_name,
            Key=object_key,
        )
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if error_code in {"404", "NoSuchKey", "NotFound"}:
            raise R2ObjectNotFoundError(
                "Uploaded object was not found for this venue image."
            ) from exc
        raise R2StorageError(
            "Cloudflare R2 could not verify the uploaded image."
        ) from exc
    except BotoCoreError as exc:
        raise R2StorageError(
            "Cloudflare R2 could not verify the uploaded image."
        ) from exc

    return R2ObjectProperties(
        content_type=response.get("ContentType"),
        size_bytes=int(response.get("ContentLength") or 0),
        etag=response.get("ETag"),
    )


def get_content_type_extension(content_type: str, file_name: str) -> str:
    normalized_content_type = content_type.strip().lower()
    if normalized_content_type == "image/jpeg":
        return "jpg"

    if normalized_content_type == "image/png":
        return "png"

    if normalized_content_type == "image/webp":
        return "webp"

    suffix = file_name.rsplit(".", maxsplit=1)[-1].lower()
    return suffix if suffix and suffix != file_name.lower() else "bin"
