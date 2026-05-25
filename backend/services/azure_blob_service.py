import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    generate_blob_sas,
)


class AzureStorageConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class AzureBlobUploadTicket:
    upload_url: str
    upload_headers: dict[str, str]
    blob_url: str
    expires_at: datetime


@dataclass(frozen=True)
class AzureBlobProperties:
    content_type: str | None
    size_bytes: int
    etag: str | None


@dataclass(frozen=True)
class AzureBlobStorageConfig:
    account_name: str
    account_key: str
    account_url: str
    connection_string: str
    venue_images_container: str
    upload_sas_minutes: int
    read_sas_minutes: int
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
        raise AzureStorageConfigError(f"{name} must be an integer.") from exc


def parse_connection_string_value(connection_string: str, key: str) -> str | None:
    for segment in connection_string.split(";"):
        segment_key, _, segment_value = segment.partition("=")
        if segment_key == key:
            return segment_value

    return None


def get_allowed_image_types() -> frozenset[str]:
    configured_types = os.getenv("AZURE_STORAGE_ALLOWED_IMAGE_TYPES")
    if not configured_types:
        return DEFAULT_ALLOWED_IMAGE_TYPES

    return frozenset(
        content_type.strip().lower()
        for content_type in configured_types.split(",")
        if content_type.strip()
    )


def get_azure_blob_storage_config() -> AzureBlobStorageConfig:
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "").strip()
    account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL", "").strip().rstrip("/")
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_VENUE_IMAGES", "").strip()

    if not connection_string:
        raise AzureStorageConfigError("AZURE_STORAGE_CONNECTION_STRING is not set.")

    if not account_name:
        account_name = parse_connection_string_value(connection_string, "AccountName") or ""

    account_key = parse_connection_string_value(connection_string, "AccountKey") or ""

    if not account_name:
        raise AzureStorageConfigError("AZURE_STORAGE_ACCOUNT_NAME is not set.")

    if not account_key:
        raise AzureStorageConfigError(
            "AZURE_STORAGE_CONNECTION_STRING must include AccountKey."
        )

    if not account_url:
        account_url = f"https://{account_name}.blob.core.windows.net"

    if not container_name:
        raise AzureStorageConfigError(
            "AZURE_STORAGE_CONTAINER_VENUE_IMAGES is not set."
        )

    return AzureBlobStorageConfig(
        account_name=account_name,
        account_key=account_key,
        account_url=account_url,
        connection_string=connection_string,
        venue_images_container=container_name,
        upload_sas_minutes=get_env_int("AZURE_STORAGE_UPLOAD_SAS_MINUTES", 15),
        read_sas_minutes=get_env_int("AZURE_STORAGE_READ_SAS_MINUTES", 60),
        max_image_bytes=get_env_int("AZURE_STORAGE_MAX_IMAGE_BYTES", 8 * 1024 * 1024),
        allowed_image_types=get_allowed_image_types(),
    )


def get_blob_service_client() -> BlobServiceClient:
    config = get_azure_blob_storage_config()
    return BlobServiceClient.from_connection_string(config.connection_string)


def build_blob_url(blob_name: str, config: AzureBlobStorageConfig | None = None) -> str:
    storage_config = config or get_azure_blob_storage_config()
    encoded_blob_name = quote(blob_name, safe="/")
    return (
        f"{storage_config.account_url}/"
        f"{storage_config.venue_images_container}/{encoded_blob_name}"
    )


def create_blob_upload_sas_url(
    *,
    blob_name: str,
    content_type: str,
) -> AzureBlobUploadTicket:
    config = get_azure_blob_storage_config()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=config.upload_sas_minutes)
    sas_token = generate_blob_sas(
        account_name=config.account_name,
        container_name=config.venue_images_container,
        blob_name=blob_name,
        account_key=config.account_key,
        permission=BlobSasPermissions(create=True, write=True),
        start=now - timedelta(minutes=5),
        expiry=expires_at,
        content_type=content_type,
    )
    blob_url = build_blob_url(blob_name, config)

    return AzureBlobUploadTicket(
        upload_url=f"{blob_url}?{sas_token}",
        upload_headers={
            "x-ms-blob-type": "BlockBlob",
            "Content-Type": content_type,
        },
        blob_url=blob_url,
        expires_at=expires_at,
    )


def create_blob_read_sas_url(blob_name: str) -> str:
    config = get_azure_blob_storage_config()
    now = datetime.now(timezone.utc)
    sas_token = generate_blob_sas(
        account_name=config.account_name,
        container_name=config.venue_images_container,
        blob_name=blob_name,
        account_key=config.account_key,
        permission=BlobSasPermissions(read=True),
        start=now - timedelta(minutes=5),
        expiry=now + timedelta(minutes=config.read_sas_minutes),
    )

    return f"{build_blob_url(blob_name, config)}?{sas_token}"


def get_blob_properties(blob_name: str) -> AzureBlobProperties:
    config = get_azure_blob_storage_config()
    blob_client = get_blob_service_client().get_blob_client(
        container=config.venue_images_container,
        blob=blob_name,
    )
    properties = blob_client.get_blob_properties()

    return AzureBlobProperties(
        content_type=properties.content_settings.content_type,
        size_bytes=properties.size,
        etag=properties.etag,
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
