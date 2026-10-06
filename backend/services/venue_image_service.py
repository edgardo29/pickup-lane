"""Venue image read and admin upload workflows."""

import sys
import uuid
from datetime import datetime, timezone
from threading import BoundedSemaphore

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from backend.models import User, Venue, VenueImage
from backend.observability.metrics import record_provider_outcome
from backend.observability.structured_logging import emit_event
from backend.observability.timeouts import (
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
    database_timeout_from_exception,
    is_cancellation,
)
from backend.schemas.venue_image_schema import (
    VenueImageAdminRead,
    VenueImageCompleteUpload,
    VenueImagePublicRead,
    VenueImageRead,
    VenueImageUpdate,
    VenueImageUploadCreate,
    VenueImageUploadRead,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.image_rules import VALID_IMAGE_ROLES
from backend.services.query_pagination import (
    DEFAULT_ADMIN_COLLECTION_LIMIT,
    DEFAULT_COLLECTION_LIMIT,
    MAX_ADMIN_COLLECTION_LIMIT,
    MAX_COLLECTION_LIMIT,
    bounded_collection_limit,
    bounded_collection_offset,
)
from backend.services.r2_storage_service import (
    ImageUploadMismatchError,
    R2MutationOutcomeUnknownError,
    R2ObjectNotFoundError,
    R2PublicationCollisionError,
    R2StorageConfig,
    R2StorageConfigError,
    R2StorageError,
    R2StorageTarget,
    R2StorageTargetMismatchError,
    create_object_read_url,
    create_object_upload_url,
    delete_object,
    download_object,
    get_content_type_extension,
    get_r2_storage_config,
    publish_object,
    storage_target_from_config,
)
from backend.services.venue_image_processing import (
    ImageContentRejectedError,
    ImageProcessorNotReadyError,
    sanitize_venue_image,
    validate_image_processor_readiness,
)

VALID_IMAGE_STATUSES = {"pending_upload", "active", "hidden", "removed"}
PUBLIC_IMAGE_STATUSES = {"active"}
SELECTED_IMAGE_STATUSES = {"pending_upload", "active"}
MAX_ACTIVE_SELECTED_VENUE_IMAGES = 3
_IMAGE_PROCESSING_SLOT = BoundedSemaphore(value=1)


def _emit_venue_image_event(
    event_name: str,
    severity: str,
    *,
    result: str,
    resource_kind: str = "venue_image",
) -> bool:
    """Emit the bounded, privacy-safe venue-image diagnostic shape."""
    return emit_event(
        event_name,
        severity,
        {"resource_kind": resource_kind, "result": result},
    )


class ImageProcessingBusyError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "STORAGE.IMAGE_PROCESSOR_BUSY",
                "message": "Image processor is busy.",
                "outcome": "retry_later",
            },
        )


class VenueImagePersistenceError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "STORAGE.PERSISTENCE_FAILED",
                "message": "Image publication state could not be saved.",
                "outcome": "failed",
            },
        )


class DatabaseCommitOutcomeUnknownError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "API.DATABASE_COMMIT_OUTCOME_UNKNOWN",
                "message": (
                    "Database commit outcome is unknown. Check current state before retrying."
                ),
                "outcome": "unknown",
            },
        )


def venue_image_error(
    status_code: int,
    *,
    code: str,
    message: str,
    outcome: str,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "outcome": outcome},
    )


def storage_target_for_image(venue_image: VenueImage) -> R2StorageTarget:
    return R2StorageTarget(
        provider=venue_image.storage_provider,
        account_id=venue_image.storage_account_id,
        bucket_name=venue_image.storage_bucket,
    )


def build_venue_image_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_venue_images_one_active_primary_per_venue" in error_text:
        return "This venue already has an active primary image."

    if "uq_venue_images_storage_object_key" in error_text:
        return "This venue image object already exists."

    if "ck_venue_images_image_role" in error_text:
        return "image_role is not supported."

    if "ck_venue_images_image_status" in error_text:
        return "image_status is not supported."

    if "ck_venue_images_pending_upload_intent" in error_text:
        return "Pending venue image uploads require a live, unconsumed intent."

    if "ck_venue_images_size_bytes_positive" in error_text:
        return "size_bytes must be greater than 0."

    if "ck_venue_images_sort_order_non_negative" in error_text:
        return "sort_order must be greater than or equal to 0."

    return error_text


def storage_config_error_response(exc: R2StorageConfigError) -> HTTPException:
    if isinstance(exc, R2StorageTargetMismatchError):
        return venue_image_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            code="STORAGE.TARGET_MISMATCH",
            message="Stored image target does not match configured storage.",
            outcome="configuration_error",
        )
    return venue_image_error(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        code="STORAGE.CONFIG_UNAVAILABLE",
        message="Image storage configuration is unavailable.",
        outcome="configuration_error",
    )


def r2_upload_url_error_response(exc: R2StorageError) -> HTTPException:
    del exc
    return venue_image_error(
        status.HTTP_502_BAD_GATEWAY,
        code="STORAGE.UPLOAD_URL_FAILED",
        message="Image upload URL could not be created.",
        outcome="provider_error",
    )


def r2_read_url_error_response(exc: R2StorageError) -> HTTPException:
    del exc
    return venue_image_error(
        status.HTTP_502_BAD_GATEWAY,
        code="STORAGE.READ_URL_FAILED",
        message="Image read URL could not be created.",
        outcome="provider_error",
    )


def _emit_storage_failure(
    *,
    operation: str,
    configuration_error: bool,
    provider_code: str,
    result: str | None = None,
) -> None:
    emit_event(
        "storage.operation_failed",
        "error",
        {
            "provider_kind": "r2",
            "operation": operation,
            "result": result
            or ("configuration_error" if configuration_error else "provider_error"),
            "stable_error_code": provider_code,
        },
    )


def _storage_config_error_code(exc: R2StorageConfigError) -> str:
    return (
        "STORAGE.TARGET_MISMATCH"
        if isinstance(exc, R2StorageTargetMismatchError)
        else "STORAGE.CONFIG_UNAVAILABLE"
    )


def venue_image_storage_not_ready_response(exc: ProgrammingError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Venue image storage is not ready. Run the latest database migrations "
            "before uploading photos."
        ),
    )


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned_value = value.strip()
    return cleaned_value or None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_venue_image_audit_snapshot(venue_image: VenueImage) -> dict[str, object]:
    return {
        "image_status": venue_image.image_status,
        "image_role": venue_image.image_role,
        "is_primary": venue_image.is_primary,
        "sort_order": venue_image.sort_order,
    }


def get_active_venue_or_404(db: Session, venue_id: uuid.UUID) -> Venue:
    venue = db.get(Venue, venue_id)

    if venue is None or venue.deleted_at is not None or not venue.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found.",
        )

    return venue


def get_locked_venue_or_404(db: Session, venue_id: uuid.UUID) -> Venue:
    venue = db.scalar(
        select(Venue)
        .where(Venue.id == venue_id)
        .execution_options(populate_existing=True)
        .with_for_update()
    )

    if venue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found.",
        )

    return venue


def get_locked_active_venue_or_404(db: Session, venue_id: uuid.UUID) -> Venue:
    venue = get_locked_venue_or_404(db, venue_id)
    if venue.deleted_at is not None or not venue.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found.",
        )
    return venue


def get_venue_image_or_404(db: Session, venue_image_id: uuid.UUID) -> VenueImage:
    venue_image = db.get(VenueImage, venue_image_id)

    if venue_image is None or venue_image.deleted_at is not None:
        raise venue_image_error(
            status.HTTP_404_NOT_FOUND,
            code="API.NOT_FOUND",
            message="Venue image not found.",
            outcome="not_found",
        )

    return venue_image


def get_locked_venue_image_or_404(
    db: Session,
    venue_image_id: uuid.UUID,
) -> VenueImage:
    venue_image = db.scalar(
        select(VenueImage)
        .where(
            VenueImage.id == venue_image_id,
            VenueImage.deleted_at.is_(None),
        )
        .execution_options(populate_existing=True)
        .with_for_update()
    )

    if venue_image is None:
        raise venue_image_error(
            status.HTTP_404_NOT_FOUND,
            code="API.NOT_FOUND",
            message="Venue image not found.",
            outcome="not_found",
        )

    return venue_image


def validate_image_role(image_role: str) -> str:
    if image_role not in VALID_IMAGE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_role is not supported.",
        )

    return image_role


def validate_image_status(image_status: str) -> str:
    if image_status not in VALID_IMAGE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_status is not supported.",
        )

    return image_status


def validate_upload_request(upload_request: VenueImageUploadCreate):
    validate_image_role(upload_request.image_role)

    try:
        config = get_r2_storage_config()
    except R2StorageConfigError as exc:
        record_provider_outcome("r2.upload.validate", "configuration_error")
        _emit_storage_failure(
            operation="r2.upload.validate",
            configuration_error=True,
            provider_code=_storage_config_error_code(exc),
        )
        raise storage_config_error_response(exc) from exc

    normalized_content_type = upload_request.content_type.strip().lower()
    if normalized_content_type not in config.allowed_image_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image content type is not supported.",
        )

    if upload_request.size_bytes > config.max_image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image is larger than the configured upload limit.",
        )
    return config


def validate_selected_image_capacity(db: Session, venue_id: uuid.UUID) -> None:
    selected_image_count = db.scalar(
        select(func.count())
        .select_from(VenueImage)
        .where(
            VenueImage.venue_id == venue_id,
            VenueImage.deleted_at.is_(None),
            VenueImage.image_status.in_(SELECTED_IMAGE_STATUSES),
        )
    )
    if int(selected_image_count or 0) >= MAX_ACTIVE_SELECTED_VENUE_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A venue can have at most 3 selected images.",
        )


def validate_completable_upload_intent(
    venue_image: VenueImage,
    *,
    now: datetime,
) -> None:
    if venue_image.image_status == "removed":
        raise venue_image_error(
            status.HTTP_404_NOT_FOUND,
            code="API.NOT_FOUND",
            message="Venue image not found.",
            outcome="not_found",
        )

    if (
        venue_image.image_status != "pending_upload"
        or venue_image.upload_completed_at is not None
    ):
        raise venue_image_error(
            status.HTTP_409_CONFLICT,
            code="STORAGE.UPLOAD_NOT_PENDING",
            message="Venue image upload is no longer pending.",
            outcome="conflict",
        )

    if venue_image.upload_expires_at is None or now >= venue_image.upload_expires_at:
        raise venue_image_error(
            status.HTTP_409_CONFLICT,
            code="STORAGE.UPLOAD_NOT_PENDING",
            message="Venue image upload is no longer pending.",
            outcome="conflict",
        )


def validate_venue_image_status_transition(
    *,
    current_status: str,
    requested_status: str | None,
) -> None:
    if current_status == "removed":
        raise venue_image_error(
            status.HTTP_404_NOT_FOUND,
            code="API.NOT_FOUND",
            message="Venue image not found.",
            outcome="not_found",
        )
    if requested_status is None or requested_status == current_status:
        return

    allowed_transitions = {
        "pending_upload": {"removed"},
        "active": {"hidden", "removed"},
        "hidden": {"active", "removed"},
    }
    if requested_status not in allowed_transitions[current_status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Venue image status transition is not allowed.",
        )


def build_venue_image_object_key(
    *,
    venue_id: uuid.UUID,
    venue_image_id: uuid.UUID,
    file_name: str,
    content_type: str,
    is_primary: bool,
    sort_order: int,
) -> str:
    extension = get_content_type_extension(content_type, file_name)
    del is_primary, sort_order
    return f"venues/{venue_id}/staging/{venue_image_id}.{extension}"


def build_venue_image_publication_key(
    *,
    venue_id: uuid.UUID,
    venue_image_id: uuid.UUID,
    publication_attempt_id: uuid.UUID,
    content_type: str,
) -> str:
    extension = get_content_type_extension(content_type, "")
    return (
        f"venues/{venue_id}/published/{venue_image_id}/"
        f"{publication_attempt_id}.{extension}"
    )


def clear_other_primary_venue_images(
    db: Session,
    *,
    venue_id: uuid.UUID,
    excluding_image_id: uuid.UUID,
    now: datetime | None = None,
) -> None:
    existing_primary_images = db.scalars(
        select(VenueImage).where(
            VenueImage.venue_id == venue_id,
            VenueImage.id != excluding_image_id,
            VenueImage.is_primary.is_(True),
            VenueImage.image_status == "active",
            VenueImage.deleted_at.is_(None),
        )
    ).all()

    changed_at = now or utc_now()
    for image in existing_primary_images:
        image.is_primary = False
        image.updated_at = changed_at
        db.add(image)


def build_venue_image_read(
    venue_image: VenueImage,
    *,
    config: R2StorageConfig | None = None,
) -> VenueImageRead:
    is_published = venue_image.publication_object_key is not None
    image_url = None
    if is_published:
        try:
            image_url = create_object_read_url(
                target=storage_target_for_image(venue_image),
                object_key=venue_image.publication_object_key,
                config=config,
            )
        except R2StorageConfigError as exc:
            _emit_storage_failure(
                operation="r2.read_url.create",
                configuration_error=True,
                provider_code=_storage_config_error_code(exc),
            )
            raise storage_config_error_response(exc) from exc
        except R2StorageError as exc:
            _emit_storage_failure(
                operation="r2.read_url.create",
                configuration_error=False,
                provider_code="STORAGE.READ_URL_FAILED",
            )
            raise r2_read_url_error_response(exc) from exc

    return VenueImageRead(
        id=venue_image.id,
        venue_id=venue_image.venue_id,
        uploaded_by_user_id=venue_image.uploaded_by_user_id,
        image_url=image_url,
        storage_provider=venue_image.storage_provider,
        storage_object_key=(
            venue_image.publication_object_key
            if is_published
            else venue_image.storage_object_key
        ),
        storage_bucket=venue_image.storage_bucket,
        storage_account_id=venue_image.storage_account_id,
        content_type=(
            venue_image.publication_content_type
            if is_published
            else venue_image.content_type
        ),
        size_bytes=(
            venue_image.publication_size_bytes
            if is_published
            else venue_image.size_bytes
        ),
        etag=(venue_image.publication_etag if is_published else venue_image.etag),
        image_role=venue_image.image_role,
        image_status=venue_image.image_status,
        is_primary=venue_image.is_primary,
        sort_order=venue_image.sort_order,
        alt_text=venue_image.alt_text,
        caption=venue_image.caption,
        upload_requested_at=venue_image.upload_requested_at,
        upload_completed_at=venue_image.upload_completed_at,
        created_at=venue_image.created_at,
        updated_at=venue_image.updated_at,
        deleted_at=venue_image.deleted_at,
    )


def build_public_venue_image_read(
    venue_image: VenueImage,
    *,
    config: R2StorageConfig | None = None,
) -> VenueImagePublicRead:
    if venue_image.publication_object_key is None:
        raise VenueImagePersistenceError()
    try:
        image_url = create_object_read_url(
            target=storage_target_for_image(venue_image),
            object_key=venue_image.publication_object_key,
            config=config,
        )
    except R2StorageConfigError as exc:
        _emit_storage_failure(
            operation="r2.read_url.create",
            configuration_error=True,
            provider_code=_storage_config_error_code(exc),
        )
        raise storage_config_error_response(exc) from exc
    except R2StorageError as exc:
        _emit_storage_failure(
            operation="r2.read_url.create",
            configuration_error=False,
            provider_code="STORAGE.READ_URL_FAILED",
        )
        raise r2_read_url_error_response(exc) from exc

    return VenueImagePublicRead(
        id=venue_image.id,
        venue_id=venue_image.venue_id,
        image_url=image_url,
        image_role=venue_image.image_role,
        is_primary=venue_image.is_primary,
        sort_order=venue_image.sort_order,
        alt_text=venue_image.alt_text,
        caption=venue_image.caption,
    )


def build_admin_venue_image_read(
    venue_image: VenueImage,
    *,
    config: R2StorageConfig | None = None,
) -> VenueImageAdminRead:
    return VenueImageAdminRead(
        **build_venue_image_read(venue_image, config=config).model_dump(mode="python")
    )


def list_venue_images_statement(
    *,
    venue_id: uuid.UUID | None,
    image_status: str | None,
    public_only: bool,
    limit: int,
    offset: int,
    max_limit: int,
):
    statement = select(VenueImage).where(VenueImage.deleted_at.is_(None))

    if venue_id is not None:
        statement = statement.where(VenueImage.venue_id == venue_id)

    if public_only:
        statement = statement.where(VenueImage.image_status.in_(PUBLIC_IMAGE_STATUSES))
    elif image_status is not None:
        validate_image_status(image_status)
        statement = statement.where(VenueImage.image_status == image_status)

    return (
        statement.order_by(
            VenueImage.is_primary.desc(),
            VenueImage.sort_order.asc(),
            VenueImage.created_at.asc(),
            VenueImage.id.asc(),
        )
        .offset(bounded_collection_offset(offset))
        .limit(bounded_collection_limit(limit, max_limit=max_limit))
    )


def list_public_venue_images(
    db: Session,
    *,
    venue_id: uuid.UUID | None,
    limit: int = DEFAULT_COLLECTION_LIMIT,
    offset: int = 0,
) -> list[VenueImagePublicRead]:
    venue_images = db.scalars(
        list_venue_images_statement(
            venue_id=venue_id,
            image_status="active",
            public_only=True,
            limit=limit,
            offset=offset,
            max_limit=MAX_COLLECTION_LIMIT,
        )
    ).all()
    return [build_public_venue_image_read(venue_image) for venue_image in venue_images]


def check_venue_image_upload_readiness(db: Session) -> dict[str, bool]:
    try:
        config = get_r2_storage_config()
        validate_image_processor_readiness(config.allowed_image_types)
        db.scalars(select(VenueImage.id).limit(1)).first()
    except R2StorageConfigError as exc:
        record_provider_outcome("r2.readiness.check", "configuration_error")
        _emit_storage_failure(
            operation="r2.readiness.check",
            configuration_error=True,
            provider_code=_storage_config_error_code(exc),
        )
        raise storage_config_error_response(exc) from exc
    except ImageProcessorNotReadyError as exc:
        _emit_venue_image_event(
            "venue_image.processor_not_ready",
            "error",
            result="codec_unavailable",
        )
        raise venue_image_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            code="STORAGE.IMAGE_PROCESSOR_UNAVAILABLE",
            message="Image processing is unavailable.",
            outcome="not_ready",
        ) from exc
    except ProgrammingError as exc:
        db.rollback()
        raise venue_image_storage_not_ready_response(exc) from exc

    return {"ready": True}


def list_admin_venue_images(
    db: Session,
    *,
    venue_id: uuid.UUID,
    image_status: str | None,
    limit: int = DEFAULT_ADMIN_COLLECTION_LIMIT,
    offset: int = 0,
) -> list[VenueImageAdminRead]:
    get_active_venue_or_404(db, venue_id)
    venue_images = db.scalars(
        list_venue_images_statement(
            venue_id=venue_id,
            image_status=image_status,
            public_only=False,
            limit=limit,
            offset=offset,
            max_limit=MAX_ADMIN_COLLECTION_LIMIT,
        )
    ).all()
    return [build_admin_venue_image_read(venue_image) for venue_image in venue_images]


def create_venue_image_upload(
    db: Session,
    *,
    venue_id: uuid.UUID,
    upload_request: VenueImageUploadCreate,
    current_admin: User,
) -> VenueImageUploadRead:
    get_active_venue_or_404(db, venue_id)
    storage_config = validate_upload_request(upload_request)
    try:
        validate_image_processor_readiness(storage_config.allowed_image_types)
    except ImageProcessorNotReadyError as exc:
        _emit_venue_image_event(
            "venue_image.processor_not_ready",
            "error",
            result="codec_unavailable",
        )
        raise venue_image_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            code="STORAGE.IMAGE_PROCESSOR_UNAVAILABLE",
            message="Image processing is unavailable.",
            outcome="not_ready",
        ) from exc
    try:
        get_locked_active_venue_or_404(db, venue_id)
        validate_selected_image_capacity(db, venue_id)
        storage_target = storage_target_from_config(storage_config)

        venue_image_id = uuid.uuid4()
        content_type = upload_request.content_type.strip().lower()
        object_key = build_venue_image_object_key(
            venue_id=venue_id,
            venue_image_id=venue_image_id,
            file_name=upload_request.file_name,
            content_type=content_type,
            is_primary=upload_request.is_primary,
            sort_order=upload_request.sort_order,
        )
        try:
            upload_ticket = create_object_upload_url(
                target=storage_target,
                object_key=object_key,
                content_type=content_type,
                config=storage_config,
            )
        except R2StorageConfigError as exc:
            _emit_storage_failure(
                operation="r2.upload_url.create",
                configuration_error=True,
                provider_code=_storage_config_error_code(exc),
            )
            raise storage_config_error_response(exc) from exc
        except R2StorageError as exc:
            _emit_storage_failure(
                operation="r2.upload_url.create",
                configuration_error=False,
                provider_code="STORAGE.UPLOAD_URL_FAILED",
            )
            raise r2_upload_url_error_response(exc) from exc

        venue_image = VenueImage(
            id=venue_image_id,
            venue_id=venue_id,
            uploaded_by_user_id=current_admin.id,
            storage_provider="r2",
            storage_object_key=object_key,
            storage_bucket=storage_config.bucket_name,
            storage_account_id=storage_config.account_id,
            content_type=content_type,
            size_bytes=upload_request.size_bytes,
            image_role=upload_request.image_role,
            image_status="pending_upload",
            is_primary=upload_request.is_primary,
            sort_order=upload_request.sort_order,
            alt_text=clean_optional_text(upload_request.alt_text),
            caption=clean_optional_text(upload_request.caption),
            upload_expires_at=upload_ticket.expires_at,
        )
        db.add(venue_image)
        db.flush()
        record_admin_action(
            db,
            admin_user_id=current_admin.id,
            action_type="create_venue_image",
            outcome="succeeded",
            target_venue_id=venue_id,
            target_venue_image_id=venue_image.id,
            metadata={
                "source": "venue_image_upload_url",
                "status": venue_image.image_status,
                "after": build_venue_image_audit_snapshot(venue_image),
            },
        )
        db.flush()
        image_response = build_admin_venue_image_read(venue_image)
        response = VenueImageUploadRead(
            image=image_response,
            upload_url=upload_ticket.upload_url,
            upload_headers=upload_ticket.upload_headers,
            expires_at=upload_ticket.expires_at,
        )
        db.commit()
        return response
    except HTTPException:
        db.rollback()
        raise
    except ProgrammingError as exc:
        db.rollback()
        raise venue_image_storage_not_ready_response(exc) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_venue_image_conflict_detail(exc),
        ) from exc
    except BaseException:
        db.rollback()
        raise


def _emit_validation_rejection(category: str) -> None:
    _emit_venue_image_event(
        "venue_image.validation_rejected",
        "warning",
        result=category,
    )


def _cleanup_image_object(
    *,
    target: R2StorageTarget,
    object_key: str,
    object_kind: str,
    config: R2StorageConfig | None = None,
) -> None:
    try:
        delete_object(target=target, object_key=object_key, config=config)
    except Exception as exc:  # noqa: BLE001 - cleanup preserves the primary result.
        if isinstance(
            exc,
            (DependencyMutationTimeoutUnknownError, R2MutationOutcomeUnknownError),
        ):
            result = "unknown_outcome"
        elif isinstance(exc, R2StorageConfigError):
            result = "configuration_error"
        elif isinstance(exc, R2StorageError):
            result = exc.result
        else:
            result = "failed"
        _emit_venue_image_event(
            "venue_image.cleanup_incomplete",
            "warning",
            resource_kind=object_kind,
            result=result,
        )


def _rollback_preserving_primary_result(db: Session) -> None:
    """Attempt rollback without replacing an already established outcome."""

    primary_exception = sys.exception()
    try:
        db.rollback()
    except BaseException as rollback_exc:
        if is_cancellation(rollback_exc) and (
            primary_exception is None or not is_cancellation(primary_exception)
        ):
            raise
        # Preserve an original cancellation or other already-established
        # primary result across ordinary rollback cleanup failures.


def _cleanup_preserving_primary_result(
    *,
    target: R2StorageTarget,
    object_key: str,
    object_kind: str,
    config: R2StorageConfig | None = None,
) -> None:
    """Attempt secondary object cleanup without replacing a primary failure."""

    try:
        _cleanup_image_object(
            target=target,
            object_key=object_key,
            object_kind=object_kind,
            config=config,
        )
    except BaseException as exc:
        try:
            _emit_venue_image_event(
                "venue_image.cleanup_incomplete",
                "warning",
                resource_kind=object_kind,
                result="unknown_outcome",
            )
        except BaseException:  # noqa: BLE001,S110 - preserve the primary outcome.
            pass
        if is_cancellation(exc):
            raise


def complete_venue_image_upload(
    db: Session,
    *,
    venue_image_id: uuid.UUID,
    complete_request: VenueImageCompleteUpload | None = None,
    current_admin: User,
) -> VenueImageAdminRead:
    del complete_request  # accepted for browser compatibility; never authoritative
    initial_image = get_venue_image_or_404(db, venue_image_id)
    validate_completable_upload_intent(initial_image, now=utc_now())
    if not _IMAGE_PROCESSING_SLOT.acquire(blocking=False):
        _emit_venue_image_event(
            "venue_image.processing_rejected",
            "warning",
            result="busy",
        )
        raise ImageProcessingBusyError()

    target = storage_target_for_image(initial_image)
    candidate_key: str | None = None
    candidate_owned = False
    commit_invoked = False
    storage_operation = "r2.object.download"
    try:
        try:
            config = get_r2_storage_config()
            validate_image_processor_readiness(config.allowed_image_types)
        except ImageProcessorNotReadyError as exc:
            _emit_venue_image_event(
                "venue_image.processor_not_ready",
                "error",
                result="codec_unavailable",
            )
            raise venue_image_error(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                code="STORAGE.IMAGE_PROCESSOR_UNAVAILABLE",
                message="Image processing is unavailable.",
                outcome="not_ready",
            ) from exc

        publication_attempt_id = uuid.uuid4()
        candidate_key = build_venue_image_publication_key(
            venue_id=initial_image.venue_id,
            venue_image_id=initial_image.id,
            publication_attempt_id=publication_attempt_id,
            content_type=initial_image.content_type,
        )
        downloaded = download_object(
            target=target,
            object_key=initial_image.storage_object_key,
            expected_size_bytes=initial_image.size_bytes,
            expected_content_type=initial_image.content_type,
            max_bytes=config.max_image_bytes,
            config=config,
        )
        sanitized = sanitize_venue_image(
            downloaded.body,
            declared_content_type=initial_image.content_type,
            allowed_types=config.allowed_image_types,
            max_bytes=config.max_image_bytes,
        )
        storage_operation = "r2.object.publish"
        published = publish_object(
            target=target,
            object_key=candidate_key,
            body=sanitized.body,
            content_type=sanitized.content_type,
            config=config,
        )
        candidate_owned = True

        venue_image = get_locked_venue_image_or_404(db, venue_image_id)
        now = utc_now()
        validate_completable_upload_intent(venue_image, now=now)
        before_snapshot = build_venue_image_audit_snapshot(venue_image)
        old_status = venue_image.image_status
        should_mark_primary = bool(venue_image.is_primary)
        if should_mark_primary:
            venue_image.is_primary = False

        venue_image.image_status = "active"
        venue_image.publication_object_key = candidate_key
        venue_image.publication_content_type = sanitized.content_type
        venue_image.publication_size_bytes = len(sanitized.body)
        venue_image.publication_etag = published.etag
        venue_image.upload_completed_at = now
        venue_image.updated_at = now
        db.add(venue_image)

        if should_mark_primary:
            clear_other_primary_venue_images(
                db,
                venue_id=venue_image.venue_id,
                excluding_image_id=venue_image.id,
                now=now,
            )
            db.flush()
            venue_image.is_primary = True
            venue_image.updated_at = now
            db.add(venue_image)

        record_admin_action(
            db,
            admin_user_id=current_admin.id,
            action_type="update_venue_image",
            outcome="succeeded",
            target_venue_id=venue_image.venue_id,
            target_venue_image_id=venue_image.id,
            metadata={
                "source": "venue_image_upload_complete",
                "old_status": old_status,
                "new_status": venue_image.image_status,
                "before": before_snapshot,
                "after": build_venue_image_audit_snapshot(venue_image),
            },
        )
        db.flush()
        storage_operation = "r2.read_url.create"
        response = build_admin_venue_image_read(venue_image, config=config)

        commit_invoked = True
        try:
            db.commit()
        except BaseException as exc:
            # Commit has been invoked, so preserve staging and the confirmed
            # candidate before attempting any fallible recovery bookkeeping.
            try:
                _emit_venue_image_event(
                    "venue_image.completion_outcome_unknown",
                    "error",
                    result="database_commit_unknown",
                )
            except BaseException:  # noqa: BLE001,S110 - preserve original commit result.
                pass
            try:
                db.invalidate()
            except BaseException:  # noqa: BLE001,S110 - preserve original commit result.
                pass
            try:
                db.close()
            except BaseException:  # noqa: BLE001,S110 - preserve original commit result.
                pass
            if not isinstance(exc, Exception):
                raise
            raise DatabaseCommitOutcomeUnknownError() from exc

        _cleanup_image_object(
            target=target,
            object_key=initial_image.storage_object_key,
            object_kind="staging",
            config=config,
        )
        return response
    except ImageUploadMismatchError as exc:
        _rollback_preserving_primary_result(db)
        _emit_validation_rejection("metadata_mismatch")
        _cleanup_preserving_primary_result(
            target=target,
            object_key=initial_image.storage_object_key,
            object_kind="staging",
            config=config,
        )
        raise venue_image_error(
            status.HTTP_400_BAD_REQUEST,
            code="STORAGE.UPLOAD_MISMATCH",
            message="Uploaded image metadata does not match the upload request.",
            outcome="metadata_mismatch",
        ) from exc
    except ImageContentRejectedError as exc:
        _rollback_preserving_primary_result(db)
        _emit_validation_rejection(exc.category)
        _cleanup_preserving_primary_result(
            target=target,
            object_key=initial_image.storage_object_key,
            object_kind="staging",
            config=config,
        )
        raise venue_image_error(
            status.HTTP_400_BAD_REQUEST,
            code="STORAGE.IMAGE_INVALID",
            message="Uploaded image content is invalid.",
            outcome=exc.category,
        ) from exc
    except R2ObjectNotFoundError as exc:
        _rollback_preserving_primary_result(db)
        raise venue_image_error(
            status.HTTP_400_BAD_REQUEST,
            code="STORAGE.OBJECT_NOT_FOUND",
            message="Uploaded image object was not found.",
            outcome="not_found",
        ) from exc
    except R2StorageConfigError as exc:
        _rollback_preserving_primary_result(db)
        _emit_storage_failure(
            operation=storage_operation,
            configuration_error=True,
            provider_code=_storage_config_error_code(exc),
        )
        raise storage_config_error_response(exc) from exc
    except DependencyReadTimeoutError:
        _rollback_preserving_primary_result(db)
        raise
    except DependencyMutationTimeoutUnknownError:
        _rollback_preserving_primary_result(db)
        raise
    except R2MutationOutcomeUnknownError as exc:
        _rollback_preserving_primary_result(db)
        _emit_storage_failure(
            operation="r2.object.publish",
            configuration_error=False,
            provider_code="STORAGE.MUTATION_OUTCOME_UNKNOWN",
        )
        raise venue_image_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            code="STORAGE.MUTATION_OUTCOME_UNKNOWN",
            message="Storage mutation outcome is unknown. Check current state before retrying.",
            outcome="unknown",
        ) from exc
    except (R2PublicationCollisionError, R2StorageError) as exc:
        _rollback_preserving_primary_result(db)
        if candidate_owned and candidate_key is not None:
            _cleanup_preserving_primary_result(
                target=target,
                object_key=candidate_key,
                object_kind="publication_candidate",
                config=config,
            )
        operation = storage_operation
        if operation == "r2.object.publish":
            code = "STORAGE.PUBLICATION_FAILED"
        elif operation == "r2.read_url.create":
            code = "STORAGE.READ_URL_FAILED"
        else:
            code = "STORAGE.OBJECT_READ_FAILED"
        _emit_storage_failure(
            operation=operation,
            configuration_error=False,
            provider_code=code,
            result=(
                "rate_limited"
                if isinstance(exc, R2StorageError) and exc.result == "rate_limited"
                else "provider_error"
            ),
        )
        if operation == "r2.read_url.create":
            raise r2_read_url_error_response(exc) from exc
        raise venue_image_error(
            status.HTTP_502_BAD_GATEWAY,
            code=code,
            message="Image storage operation failed.",
            outcome=(
                "rate_limited"
                if isinstance(exc, R2StorageError) and exc.result == "rate_limited"
                else "provider_error"
            ),
        ) from exc
    except HTTPException:
        if not commit_invoked:
            _rollback_preserving_primary_result(db)
            if candidate_owned and candidate_key is not None:
                _cleanup_preserving_primary_result(
                    target=target,
                    object_key=candidate_key,
                    object_kind="publication_candidate",
                    config=config,
                )
        raise
    except IntegrityError as exc:
        _rollback_preserving_primary_result(db)
        if candidate_owned and candidate_key is not None:
            _cleanup_preserving_primary_result(
                target=target,
                object_key=candidate_key,
                object_kind="publication_candidate",
                config=config,
            )
        raise VenueImagePersistenceError() from exc
    except Exception as exc:
        _rollback_preserving_primary_result(db)
        if candidate_owned and candidate_key is not None:
            _cleanup_preserving_primary_result(
                target=target,
                object_key=candidate_key,
                object_kind="publication_candidate",
                config=config,
            )
        database_timeout = database_timeout_from_exception(exc)
        if database_timeout is not None:
            raise database_timeout from exc
        raise VenueImagePersistenceError() from exc
    except BaseException:
        if not commit_invoked:
            _rollback_preserving_primary_result(db)
            if candidate_owned and candidate_key is not None:
                _cleanup_preserving_primary_result(
                    target=target,
                    object_key=candidate_key,
                    object_kind="publication_candidate",
                    config=config,
                )
        raise
    finally:
        _IMAGE_PROCESSING_SLOT.release()


def update_venue_image(
    db: Session,
    *,
    venue_image_id: uuid.UUID,
    image_update: VenueImageUpdate,
    current_admin: User,
) -> VenueImageAdminRead:
    update_data = image_update.model_dump(exclude_unset=True)
    reason = clean_optional_text(update_data.pop("reason", None))

    if "image_role" in update_data and update_data["image_role"] is not None:
        update_data["image_role"] = validate_image_role(update_data["image_role"])

    if "image_status" in update_data and update_data["image_status"] is not None:
        update_data["image_status"] = validate_image_status(update_data["image_status"])

    for text_field in ("alt_text", "caption"):
        if text_field in update_data:
            update_data[text_field] = clean_optional_text(update_data[text_field])

    try:
        venue_image = get_locked_venue_image_or_404(db, venue_image_id)
        requested_status = update_data.get("image_status")
        validate_venue_image_status_transition(
            current_status=venue_image.image_status,
            requested_status=requested_status,
        )
        if venue_image.image_status == "hidden" and requested_status == "active":
            get_locked_venue_or_404(db, venue_image.venue_id)
            validate_selected_image_capacity(db, venue_image.venue_id)

        now = utc_now()
        if requested_status == "removed":
            update_data["deleted_at"] = now
            update_data["is_primary"] = False

        before_snapshot = build_venue_image_audit_snapshot(venue_image)
        old_status = venue_image.image_status

        for field_name, field_value in update_data.items():
            setattr(venue_image, field_name, field_value)

        # Pending intents may carry the administrator's requested primary
        # selection into completion. Hidden and removed images cannot remain
        # primary.
        if venue_image.image_status in {"hidden", "removed"} and venue_image.is_primary:
            venue_image.is_primary = False

        venue_image.updated_at = now

        if venue_image.image_status == "active" and venue_image.is_primary:
            clear_other_primary_venue_images(
                db,
                venue_id=venue_image.venue_id,
                excluding_image_id=venue_image.id,
                now=now,
            )

        action_type = (
            "remove_venue_image"
            if venue_image.image_status == "removed"
            else "update_venue_image"
        )
        record_admin_action(
            db,
            admin_user_id=current_admin.id,
            action_type=action_type,
            outcome="succeeded",
            target_venue_id=venue_image.venue_id,
            target_venue_image_id=venue_image.id,
            reason=reason,
            metadata={
                "source": "venue_image_update",
                "old_status": old_status,
                "new_status": venue_image.image_status,
                "before": before_snapshot,
                "after": build_venue_image_audit_snapshot(venue_image),
            },
        )
        db.add(venue_image)
        db.flush()
        response = build_admin_venue_image_read(venue_image)
        db.commit()
        return response
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_venue_image_conflict_detail(exc),
        ) from exc
    except BaseException:
        db.rollback()
        raise
