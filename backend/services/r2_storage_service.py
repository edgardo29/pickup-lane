from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import boto3
from botocore.client import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    ReadTimeoutError,
)

from backend.observability.timeouts import DependencyReadTimeoutError
from backend.settings import (
    DEFAULT_R2_ALLOWED_IMAGE_TYPES,
    SettingsError,
    get_settings,
)


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
    metadata_connect_timeout_seconds: int
    metadata_read_timeout_seconds: int


DEFAULT_ALLOWED_IMAGE_TYPES = DEFAULT_R2_ALLOWED_IMAGE_TYPES


def get_allowed_image_types() -> frozenset[str]:
    return _storage_settings().r2_allowed_image_types


def get_r2_storage_config() -> R2StorageConfig:
    settings = _storage_settings()
    account_id = settings.r2_account_id
    access_key_id = settings.r2_access_key_id_value
    secret_access_key = settings.r2_secret_access_key_value
    endpoint_url = settings.r2_endpoint_url
    bucket_name = settings.r2_bucket_name

    if not account_id:
        raise R2StorageConfigError("R2_ACCOUNT_ID is not set.")

    if not access_key_id:
        raise R2StorageConfigError("R2_ACCESS_KEY_ID is not set.")

    if not secret_access_key:
        raise R2StorageConfigError("R2_SECRET_ACCESS_KEY is not set.")

    if not bucket_name:
        raise R2StorageConfigError("R2_BUCKET_NAME is not set.")

    return R2StorageConfig(
        account_id=account_id,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        endpoint_url=endpoint_url,
        bucket_name=bucket_name,
        upload_url_minutes=settings.r2_upload_url_minutes,
        read_url_minutes=settings.r2_read_url_minutes,
        max_image_bytes=settings.r2_max_image_bytes,
        allowed_image_types=settings.r2_allowed_image_types,
        metadata_connect_timeout_seconds=(
            settings.r2_metadata_connect_timeout_seconds
        ),
        metadata_read_timeout_seconds=settings.r2_metadata_read_timeout_seconds,
    )


def _storage_settings():
    try:
        return get_settings()
    except SettingsError as exc:
        raise R2StorageConfigError(str(exc)) from exc


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
            connect_timeout=storage_config.metadata_connect_timeout_seconds,
            read_timeout=storage_config.metadata_read_timeout_seconds,
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
    except (ConnectTimeoutError, ReadTimeoutError) as exc:
        raise DependencyReadTimeoutError(
            provider_kind="r2",
            operation="r2.metadata.head",
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
