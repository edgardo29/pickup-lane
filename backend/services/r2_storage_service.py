import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from ipaddress import IPv4Address, IPv6Address
from urllib.parse import quote, urlsplit

import boto3
import idna
from botocore.client import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    ReadTimeoutError,
)

from backend.observability.metrics import record_provider_outcome
from backend.observability.timeouts import (
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
    is_cancellation,
)
from backend.settings import (
    DEFAULT_R2_ALLOWED_IMAGE_TYPES,
    SettingsError,
    get_settings,
)


class R2StorageConfigError(RuntimeError):
    pass


class R2StorageError(RuntimeError):
    def __init__(self, message: str, *, result: str = "failed") -> None:
        self.result = result
        super().__init__(message)


class R2ObjectNotFoundError(R2StorageError):
    pass


class R2StorageTargetMismatchError(R2StorageConfigError):
    pass


class R2MutationOutcomeUnknownError(R2StorageError):
    pass


class R2PublicationCollisionError(R2StorageError):
    pass


class ImageUploadMismatchError(ValueError):
    pass


@dataclass(frozen=True)
class R2ObjectUploadTicket:
    upload_url: str
    upload_headers: dict[str, str]
    object_url: str
    expires_at: datetime


@dataclass(frozen=True)
class R2StorageTarget:
    provider: str
    account_id: str
    bucket_name: str


@dataclass(frozen=True)
class R2ObjectReference:
    target: R2StorageTarget
    object_key: str


@dataclass(frozen=True)
class R2DownloadedObject:
    body: bytes
    content_type: str | None
    size_bytes: int
    etag: str | None


@dataclass(frozen=True)
class R2PublishedObject:
    etag: str


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
    object_connect_timeout_seconds: int
    object_read_timeout_seconds: int


DEFAULT_ALLOWED_IMAGE_TYPES = DEFAULT_R2_ALLOWED_IMAGE_TYPES


def _raise_invalid_presigned_url(error_detail: str) -> None:
    raise R2StorageError(error_detail)


def _is_ipv4_number(value: str) -> bool:
    normalized = value.casefold()
    if normalized.startswith("0x"):
        hexadecimal = normalized[2:]
        return bool(hexadecimal) and all(
            character in "0123456789abcdef" for character in hexadecimal
        )
    return value.isascii() and value.isdigit()


def _validate_explicit_port(port: str, *, error_detail: str) -> None:
    if not port or not port.isascii() or not port.isdigit():
        _raise_invalid_presigned_url(error_detail)
    if not 0 < int(port) < 65536:
        _raise_invalid_presigned_url(error_detail)


def _validate_dns_or_ipv4_hostname(hostname: str, *, error_detail: str) -> None:
    try:
        ascii_hostname = idna.encode(
            hostname,
            uts46=True,
            std3_rules=True,
        ).decode("ascii")
    except idna.IDNAError as exc:
        raise R2StorageError(error_detail) from exc

    dns_hostname = ascii_hostname.removesuffix(".").casefold()
    if not dns_hostname or len(dns_hostname) > 253:
        _raise_invalid_presigned_url(error_detail)

    try:
        IPv4Address(dns_hostname)
    except ValueError:
        # WHATWG URL consumers interpret a hostname ending in an IPv4 number as
        # an address. Reject non-canonical forms instead of allowing the browser
        # to reinterpret a DNS-looking authority after signing.
        if _is_ipv4_number(dns_hostname.rsplit(".", maxsplit=1)[-1]):
            _raise_invalid_presigned_url(error_detail)


def _validate_presigned_url_authority(
    authority: str,
    *,
    hostname: str,
    error_detail: str,
) -> None:
    if authority.startswith("["):
        closing_bracket = authority.find("]")
        remainder = authority[closing_bracket + 1 :]
        if remainder:
            if not remainder.startswith(":"):
                _raise_invalid_presigned_url(error_detail)
            _validate_explicit_port(remainder[1:], error_detail=error_detail)
        if "%" in hostname:
            _raise_invalid_presigned_url(error_detail)
        try:
            IPv6Address(hostname)
        except ValueError as exc:
            raise R2StorageError(error_detail) from exc
        return

    if ":" in authority:
        host, separator, port = authority.rpartition(":")
        if not separator or ":" in host:
            _raise_invalid_presigned_url(error_detail)
        _validate_explicit_port(port, error_detail=error_detail)

    _validate_dns_or_ipv4_hostname(hostname, error_detail=error_detail)


def _validated_presigned_url(value: object, *, error_detail: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise R2StorageError(error_detail)

    if any(
        character.isspace() or ord(character) < 32 or ord(character) == 127
        for character in value
    ):
        raise R2StorageError(error_detail)

    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError as exc:
        raise R2StorageError(error_detail) from exc

    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise R2StorageError(error_detail)
    _validate_presigned_url_authority(
        parsed.netloc,
        hostname=parsed.hostname,
        error_detail=error_detail,
    )
    return value


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
        object_connect_timeout_seconds=settings.r2_object_connect_timeout_seconds,
        object_read_timeout_seconds=settings.r2_object_read_timeout_seconds,
    )


def _storage_settings():
    try:
        return get_settings()
    except SettingsError as exc:
        raise R2StorageConfigError(str(exc)) from exc


def get_r2_client(
    config: R2StorageConfig | None = None,
    *,
    disable_retries: bool = False,
):
    storage_config = config or get_r2_storage_config()
    config_kwargs = {
        "signature_version": "s3v4",
        "s3": {"addressing_style": "path"},
        "connect_timeout": storage_config.object_connect_timeout_seconds,
        "read_timeout": storage_config.object_read_timeout_seconds,
    }
    if disable_retries:
        config_kwargs["retries"] = {"total_max_attempts": 1}
    return boto3.client(
        "s3",
        endpoint_url=storage_config.endpoint_url,
        aws_access_key_id=storage_config.access_key_id,
        aws_secret_access_key=storage_config.secret_access_key,
        region_name="auto",
        config=Config(**config_kwargs),
    )


def storage_target_from_config(config: R2StorageConfig) -> R2StorageTarget:
    return R2StorageTarget(
        provider="r2",
        account_id=config.account_id,
        bucket_name=config.bucket_name,
    )


def validate_storage_target(
    target: R2StorageTarget,
    config: R2StorageConfig | None = None,
) -> R2StorageConfig:
    storage_config = config or get_r2_storage_config()
    parsed = urlsplit(storage_config.endpoint_url)
    expected_host = f"{storage_config.account_id}.r2.cloudflarestorage.com"
    if (
        target.provider != "r2"
        or target.account_id != storage_config.account_id
        or target.bucket_name != storage_config.bucket_name
        or parsed.scheme != "https"
        or parsed.hostname != expected_host
        or parsed.port is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise R2StorageTargetMismatchError(
            "Stored image target does not match configured Cloudflare R2 storage."
        )
    return storage_config


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


def _client_error_status_and_code(exc: ClientError) -> tuple[int | None, str]:
    response = exc.response if isinstance(exc.response, Mapping) else {}
    metadata = response.get("ResponseMetadata", {})
    error = response.get("Error", {})
    status = metadata.get("HTTPStatusCode") if isinstance(metadata, Mapping) else None
    code = str(error.get("Code", "")).strip() if isinstance(error, Mapping) else ""
    return (
        status if isinstance(status, int) and not isinstance(status, bool) else None,
        code,
    )


_R2_MISSING_OBJECT_CODES = {"404", "NoSuchKey", "NotFound"}
_R2_THROTTLE_CODES = {
    "SlowDown",
    "Throttling",
    "ThrottlingException",
    "TooManyRequests",
    "TooManyRequestsException",
}


def _download_client_error_result(exc: ClientError) -> str:
    status, code = _client_error_status_and_code(exc)
    if status is None or not 400 <= status <= 599:
        return "failed"
    if status == 404:
        return "not_found" if not code or code in _R2_MISSING_OBJECT_CODES else "failed"
    if status == 429:
        return "rate_limited" if not code or code in _R2_THROTTLE_CODES else "failed"
    if status == 503 and code in _R2_THROTTLE_CODES:
        return "rate_limited"
    return "failed"


def _r2_error_result(exc: BaseException, operation: str) -> str:
    if isinstance(exc, R2StorageConfigError):
        return "configuration_error"
    original = (
        exc.__cause__
        if isinstance(exc, (R2StorageError, DependencyReadTimeoutError))
        and exc.__cause__ is not None
        else exc
    )
    if isinstance(original, ClientError):
        if operation == "r2.object.download":
            return _download_client_error_result(original)
        status, code = _client_error_status_and_code(original)
        if status == 429 and (not code or code in _R2_THROTTLE_CODES):
            return "rate_limited"
    if isinstance(original, (ConnectTimeoutError, ReadTimeoutError)):
        return "timed_out"
    return "failed"


def create_object_upload_url(
    *,
    target: R2StorageTarget,
    object_key: str,
    content_type: str,
    config: R2StorageConfig | None = None,
) -> R2ObjectUploadTicket:
    operation = "r2.upload_url.create"
    try:
        config = validate_storage_target(target, config)
    except R2StorageConfigError:
        record_provider_outcome(operation, "configuration_error")
        raise
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=config.upload_url_minutes
    )

    try:
        upload_url = _validated_presigned_url(
            get_r2_client(config).generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": config.bucket_name,
                    "Key": object_key,
                    "ContentType": content_type,
                },
                ExpiresIn=config.upload_url_minutes * 60,
                HttpMethod="PUT",
            ),
            error_detail="Cloudflare R2 could not create an upload URL.",
        )
    except (BotoCoreError, ClientError) as exc:
        record_provider_outcome(operation, _r2_error_result(exc, operation))
        raise R2StorageError("Cloudflare R2 could not create an upload URL.") from exc
    except R2StorageError:
        record_provider_outcome(operation, "failed")
        raise
    ticket = R2ObjectUploadTicket(
        upload_url=upload_url,
        upload_headers={"Content-Type": content_type},
        object_url=build_object_url(object_key, config),
        expires_at=expires_at,
    )
    record_provider_outcome(operation, "succeeded")
    return ticket


def create_object_read_url(
    *,
    target: R2StorageTarget,
    object_key: str,
    config: R2StorageConfig | None = None,
) -> str:
    operation = "r2.read_url.create"
    try:
        config = validate_storage_target(target, config)
    except R2StorageConfigError:
        record_provider_outcome(operation, "configuration_error")
        raise

    try:
        url = _validated_presigned_url(
            get_r2_client(config).generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": config.bucket_name,
                    "Key": object_key,
                },
                ExpiresIn=config.read_url_minutes * 60,
                HttpMethod="GET",
            ),
            error_detail="Cloudflare R2 could not create a read URL.",
        )
    except (BotoCoreError, ClientError) as exc:
        record_provider_outcome(operation, _r2_error_result(exc, operation))
        raise R2StorageError("Cloudflare R2 could not create a read URL.") from exc
    except R2StorageError:
        record_provider_outcome(operation, "failed")
        raise
    record_provider_outcome(operation, "succeeded")
    return url


def download_object(
    *,
    target: R2StorageTarget,
    object_key: str,
    expected_size_bytes: int,
    expected_content_type: str,
    max_bytes: int,
    config: R2StorageConfig | None = None,
) -> R2DownloadedObject:
    operation = "r2.object.download"
    body = None
    try:
        config = validate_storage_target(target, config)
        response = get_r2_client(config).get_object(
            Bucket=config.bucket_name,
            Key=object_key,
        )
        if not isinstance(response, Mapping):
            raise R2StorageError("Cloudflare R2 returned an invalid object response.")
        response_metadata = response.get("ResponseMetadata")
        response_status = (
            response_metadata.get("HTTPStatusCode")
            if isinstance(response_metadata, Mapping)
            else None
        )
        content_length = response.get("ContentLength")
        content_type = response.get("ContentType")
        etag = response.get("ETag")
        body = response.get("Body")
        if (
            isinstance(response_status, bool)
            or response_status != 200
            or "Error" in response
            or isinstance(content_length, bool)
            or not isinstance(content_length, int)
            or content_length < 0
            or (content_type is not None and not isinstance(content_type, str))
            or (etag is not None and not isinstance(etag, str))
            or body is None
            or not callable(getattr(body, "read", None))
            or not callable(getattr(body, "close", None))
        ):
            raise R2StorageError("Cloudflare R2 returned an invalid object response.")
        if content_length < 1 or content_length > max_bytes:
            raise ImageUploadMismatchError("Uploaded image size is outside policy.")
        if content_length != expected_size_bytes:
            raise ImageUploadMismatchError(
                "Uploaded image size does not match the request."
            )
        if (
            content_type is not None
            and content_type.strip().lower() != expected_content_type
        ):
            raise ImageUploadMismatchError(
                "Uploaded image type does not match the request."
            )
        content = body.read(max_bytes + 1)
        if not isinstance(content, bytes):
            raise R2StorageError("Cloudflare R2 returned an invalid object response.")
        if len(content) != content_length:
            raise ImageUploadMismatchError("Uploaded image length is inconsistent.")
        downloaded = R2DownloadedObject(
            body=content,
            content_type=content_type,
            size_bytes=content_length,
            etag=etag,
        )
    except R2StorageConfigError:
        record_provider_outcome(operation, "configuration_error")
        raise
    except ClientError as exc:
        result = _download_client_error_result(exc)
        if result == "not_found":
            record_provider_outcome(operation, "not_found")
            raise R2ObjectNotFoundError(
                "Uploaded object was not found for this venue image."
            ) from exc
        record_provider_outcome(operation, result)
        raise R2StorageError(
            "Cloudflare R2 could not read the uploaded image.",
            result=result,
        ) from exc
    except (ConnectTimeoutError, ReadTimeoutError) as exc:
        record_provider_outcome(operation, "timed_out")
        raise DependencyReadTimeoutError(
            provider_kind="r2",
            operation=operation,
        ) from exc
    except ImageUploadMismatchError:
        record_provider_outcome(operation, "failed")
        raise
    except R2StorageError:
        record_provider_outcome(operation, "failed")
        raise
    except BotoCoreError as exc:
        record_provider_outcome(operation, "failed")
        raise R2StorageError(
            "Cloudflare R2 could not read the uploaded image."
        ) from exc
    except Exception as exc:
        record_provider_outcome(operation, "failed")
        raise R2StorageError(
            "Cloudflare R2 could not read the uploaded image."
        ) from exc
    except BaseException:
        # Cancellation and other process-control interruptions remain
        # interruptions, but an invoked download still owns one final metric.
        record_provider_outcome(operation, "failed")
        raise
    finally:
        if body is not None and callable(getattr(body, "close", None)):
            primary_exception = sys.exception()
            try:
                body.close()
            except BaseException as close_exc:
                if is_cancellation(close_exc) and (
                    primary_exception is None or not is_cancellation(primary_exception)
                ):
                    if primary_exception is None:
                        record_provider_outcome(operation, "failed")
                    raise
                # Ordinary close failures, and secondary close cancellation
                # while an original cancellation is already propagating, must
                # not replace the established read outcome.
    record_provider_outcome(operation, "succeeded")
    return downloaded


def _mutation_client_error_result(exc: ClientError, *, publication: bool) -> str:
    status, code = _client_error_status_and_code(exc)
    collision_codes = {"412", "PreconditionFailed"}
    if (
        status is None
        or not 400 <= status <= 599
        or status in {408, 409}
        or status >= 500
    ):
        return "unknown_outcome"
    if publication and status == 412:
        return "collision" if code == "PreconditionFailed" else "unknown_outcome"
    if publication and code in collision_codes:
        return "unknown_outcome"
    if not publication and status == 404:
        return (
            "succeeded"
            if not code or code in _R2_MISSING_OBJECT_CODES
            else "unknown_outcome"
        )
    if publication and status in {404, 412}:
        return "unknown_outcome"
    if not publication and status == 412:
        return "unknown_outcome"
    if status == 429:
        return (
            "rate_limited"
            if not code or code in _R2_THROTTLE_CODES
            else "unknown_outcome"
        )
    if code in _R2_THROTTLE_CODES:
        return "rate_limited"
    if code in _R2_MISSING_OBJECT_CODES or not code:
        return "unknown_outcome"
    if 400 <= status < 500:
        return "failed"
    return "unknown_outcome"


def publish_object(
    *,
    target: R2StorageTarget,
    object_key: str,
    body: bytes,
    content_type: str,
    config: R2StorageConfig | None = None,
) -> R2PublishedObject:
    operation = "r2.object.publish"
    dispatched = False
    try:
        config = validate_storage_target(target, config)
        client = get_r2_client(config, disable_retries=True)
        dispatched = True
        response = client.put_object(
            Bucket=config.bucket_name,
            Key=object_key,
            Body=body,
            ContentType=content_type,
            IfNoneMatch="*",
        )
        if not isinstance(response, Mapping):
            raise R2MutationOutcomeUnknownError("Publication outcome is unknown.")
        response_metadata = response.get("ResponseMetadata")
        response_status = (
            response_metadata.get("HTTPStatusCode")
            if isinstance(response_metadata, Mapping)
            else None
        )
        etag = response.get("ETag")
        if (
            isinstance(response_status, bool)
            or not isinstance(response_status, int)
            or not 200 <= response_status < 300
            or "Error" in response
            or not isinstance(etag, str)
            or not etag.strip()
        ):
            raise R2MutationOutcomeUnknownError("Publication outcome is unknown.")
    except R2StorageConfigError:
        record_provider_outcome(operation, "configuration_error")
        raise
    except ClientError as exc:
        if not dispatched:
            record_provider_outcome(operation, "failed")
            raise R2StorageError(
                "Cloudflare R2 could not start image publication.",
                result="failed",
            ) from exc
        result = _mutation_client_error_result(exc, publication=True)
        if result == "collision":
            record_provider_outcome(operation, "failed")
            raise R2PublicationCollisionError(
                "Publication key already exists."
            ) from exc
        record_provider_outcome(operation, result)
        if result == "rate_limited" or result == "failed":
            raise R2StorageError(
                "Cloudflare R2 rejected image publication.",
                result=result,
            ) from exc
        raise R2MutationOutcomeUnknownError("Publication outcome is unknown.") from exc
    except (ConnectTimeoutError, ReadTimeoutError) as exc:
        if not dispatched:
            record_provider_outcome(operation, "failed")
            raise R2StorageError(
                "Cloudflare R2 could not start image publication.",
                result="failed",
            ) from exc
        record_provider_outcome(operation, "unknown_outcome")
        raise DependencyMutationTimeoutUnknownError(
            provider_kind="r2",
            operation=operation,
        ) from exc
    except R2MutationOutcomeUnknownError:
        record_provider_outcome(operation, "unknown_outcome")
        raise
    except Exception as exc:
        if dispatched:
            record_provider_outcome(operation, "unknown_outcome")
            raise R2MutationOutcomeUnknownError(
                "Publication outcome is unknown."
            ) from exc
        record_provider_outcome(operation, "failed")
        raise R2StorageError(
            "Cloudflare R2 could not start image publication.",
            result="failed",
        ) from exc
    except BaseException as exc:
        if dispatched:
            record_provider_outcome(operation, "unknown_outcome")
            if is_cancellation(exc) or not isinstance(exc, Exception):
                raise
            raise R2MutationOutcomeUnknownError(
                "Publication outcome is unknown."
            ) from exc
        raise
    record_provider_outcome(operation, "succeeded")
    return R2PublishedObject(etag=etag.strip())


def delete_object(
    *,
    target: R2StorageTarget,
    object_key: str,
    config: R2StorageConfig | None = None,
) -> None:
    operation = "r2.object.delete"
    dispatched = False
    try:
        config = validate_storage_target(target, config)
        client = get_r2_client(config)
        dispatched = True
        response = client.delete_object(Bucket=config.bucket_name, Key=object_key)
        if not isinstance(response, Mapping):
            raise R2MutationOutcomeUnknownError("Deletion outcome is unknown.")
        metadata = response.get("ResponseMetadata")
        status = (
            metadata.get("HTTPStatusCode") if isinstance(metadata, Mapping) else None
        )
        if (
            not isinstance(status, int)
            or not 200 <= status < 300
            or "Error" in response
        ):
            raise R2MutationOutcomeUnknownError("Deletion outcome is unknown.")
    except R2StorageConfigError:
        record_provider_outcome(operation, "configuration_error")
        raise
    except ClientError as exc:
        if not dispatched:
            record_provider_outcome(operation, "failed")
            raise R2StorageError(
                "Cloudflare R2 could not start object deletion.",
                result="failed",
            ) from exc
        result = _mutation_client_error_result(exc, publication=False)
        if result == "succeeded":
            record_provider_outcome(operation, "succeeded")
            return
        record_provider_outcome(operation, result)
        if result in {"rate_limited", "failed"}:
            raise R2StorageError(
                "Cloudflare R2 rejected object deletion.",
                result=result,
            ) from exc
        raise R2MutationOutcomeUnknownError("Deletion outcome is unknown.") from exc
    except (ConnectTimeoutError, ReadTimeoutError) as exc:
        if not dispatched:
            record_provider_outcome(operation, "failed")
            raise R2StorageError(
                "Cloudflare R2 could not start object deletion.",
                result="failed",
            ) from exc
        record_provider_outcome(operation, "unknown_outcome")
        raise DependencyMutationTimeoutUnknownError(
            provider_kind="r2",
            operation=operation,
        ) from exc
    except R2MutationOutcomeUnknownError:
        record_provider_outcome(operation, "unknown_outcome")
        raise
    except Exception as exc:
        if dispatched:
            record_provider_outcome(operation, "unknown_outcome")
            raise R2MutationOutcomeUnknownError("Deletion outcome is unknown.") from exc
        record_provider_outcome(operation, "failed")
        raise R2StorageError(
            "Cloudflare R2 could not start object deletion.",
            result="failed",
        ) from exc
    except BaseException as exc:
        if dispatched:
            record_provider_outcome(operation, "unknown_outcome")
            if is_cancellation(exc) or not isinstance(exc, Exception):
                raise
            raise R2MutationOutcomeUnknownError("Deletion outcome is unknown.") from exc
        raise
    record_provider_outcome(operation, "succeeded")


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
