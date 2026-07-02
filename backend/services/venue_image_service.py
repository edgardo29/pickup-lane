"""Venue image read and admin upload workflows."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from backend.models import User, Venue, VenueImage
from backend.schemas.venue_image_schema import (
    VenueImageCompleteUpload,
    VenueImageRead,
    VenueImageUpdate,
    VenueImageUploadCreate,
    VenueImageUploadRead,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.r2_storage_service import (
    R2ObjectNotFoundError,
    R2StorageConfigError,
    R2StorageError,
    create_object_read_url,
    create_object_upload_url,
    get_content_type_extension,
    get_object_properties,
    get_r2_storage_config,
)
from backend.services.image_rules import VALID_IMAGE_ROLES

VALID_IMAGE_STATUSES = {"pending_upload", "active", "hidden", "removed"}
PUBLIC_IMAGE_STATUSES = {"active"}


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

    if "ck_venue_images_size_bytes_positive" in error_text:
        return "size_bytes must be greater than 0."

    if "ck_venue_images_sort_order_non_negative" in error_text:
        return "sort_order must be greater than or equal to 0."

    return error_text


def storage_config_error_response(exc: R2StorageConfigError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(exc),
    )


def storage_provider_error_response(exc: R2StorageError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=str(exc),
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


def get_venue_image_or_404(db: Session, venue_image_id: uuid.UUID) -> VenueImage:
    venue_image = db.get(VenueImage, venue_image_id)

    if venue_image is None or venue_image.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue image not found.",
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


def validate_upload_request(upload_request: VenueImageUploadCreate) -> None:
    validate_image_role(upload_request.image_role)

    try:
        config = get_r2_storage_config()
    except R2StorageConfigError as exc:
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
    slot_name = "primary" if is_primary else f"gallery-{max(sort_order, 1)}"
    return f"venues/{venue_id}/{slot_name}-{venue_image_id}.{extension}"


def clear_other_primary_venue_images(
    db: Session,
    *,
    venue_id: uuid.UUID,
    excluding_image_id: uuid.UUID,
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

    now = datetime.now(timezone.utc)
    for image in existing_primary_images:
        image.is_primary = False
        image.updated_at = now
        db.add(image)


def build_venue_image_read(venue_image: VenueImage) -> VenueImageRead:
    try:
        image_url = create_object_read_url(venue_image.storage_object_key)
    except R2StorageConfigError as exc:
        raise storage_config_error_response(exc) from exc
    except R2StorageError as exc:
        raise storage_provider_error_response(exc) from exc

    return VenueImageRead(
        id=venue_image.id,
        venue_id=venue_image.venue_id,
        uploaded_by_user_id=venue_image.uploaded_by_user_id,
        image_url=image_url,
        storage_provider=venue_image.storage_provider,
        storage_object_key=venue_image.storage_object_key,
        storage_bucket=venue_image.storage_bucket,
        storage_account_id=venue_image.storage_account_id,
        content_type=venue_image.content_type,
        size_bytes=venue_image.size_bytes,
        etag=venue_image.etag,
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


def list_venue_images_statement(
    *,
    venue_id: uuid.UUID | None,
    image_status: str | None,
    public_only: bool,
):
    statement = select(VenueImage).where(VenueImage.deleted_at.is_(None))

    if venue_id is not None:
        statement = statement.where(VenueImage.venue_id == venue_id)

    if public_only:
        statement = statement.where(VenueImage.image_status.in_(PUBLIC_IMAGE_STATUSES))
    elif image_status is not None:
        validate_image_status(image_status)
        statement = statement.where(VenueImage.image_status == image_status)

    return statement.order_by(
        VenueImage.is_primary.desc(),
        VenueImage.sort_order.asc(),
        VenueImage.created_at.asc(),
    )


def list_public_venue_images(
    db: Session,
    *,
    venue_id: uuid.UUID | None,
) -> list[VenueImageRead]:
    venue_images = db.scalars(
        list_venue_images_statement(
            venue_id=venue_id,
            image_status="active",
            public_only=True,
        )
    ).all()
    return [build_venue_image_read(venue_image) for venue_image in venue_images]


def check_venue_image_upload_readiness(db: Session) -> dict[str, bool]:
    try:
        get_r2_storage_config()
        db.scalars(select(VenueImage.id).limit(1)).first()
    except R2StorageConfigError as exc:
        raise storage_config_error_response(exc) from exc
    except ProgrammingError as exc:
        db.rollback()
        raise venue_image_storage_not_ready_response(exc) from exc

    return {"ready": True}


def list_admin_venue_images(
    db: Session,
    *,
    venue_id: uuid.UUID,
    image_status: str | None,
) -> list[VenueImageRead]:
    get_active_venue_or_404(db, venue_id)
    venue_images = db.scalars(
        list_venue_images_statement(
            venue_id=venue_id,
            image_status=image_status,
            public_only=False,
        )
    ).all()
    return [build_venue_image_read(venue_image) for venue_image in venue_images]


def create_venue_image_upload(
    db: Session,
    *,
    venue_id: uuid.UUID,
    upload_request: VenueImageUploadCreate,
    current_admin: User,
) -> VenueImageUploadRead:
    get_active_venue_or_404(db, venue_id)
    validate_upload_request(upload_request)

    try:
        storage_config = get_r2_storage_config()
    except R2StorageConfigError as exc:
        raise storage_config_error_response(exc) from exc

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
    )

    try:
        upload_ticket = create_object_upload_url(
            object_key=object_key,
            content_type=content_type,
        )
    except R2StorageConfigError as exc:
        raise storage_config_error_response(exc) from exc
    except R2StorageError as exc:
        raise storage_provider_error_response(exc) from exc

    try:
        db.add(venue_image)
        db.flush()
        record_admin_action(
            db,
            admin_user_id=current_admin.id,
            action_type="create_venue_image",
            target_venue_id=venue_id,
            target_venue_image_id=venue_image.id,
            metadata={
                "source": "venue_image_upload_url",
                "status": venue_image.image_status,
                "after": build_venue_image_audit_snapshot(venue_image),
            },
        )
        db.commit()
        db.refresh(venue_image)
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

    return VenueImageUploadRead(
        image=build_venue_image_read(venue_image),
        upload_url=upload_ticket.upload_url,
        upload_headers=upload_ticket.upload_headers,
        expires_at=upload_ticket.expires_at,
    )


def complete_venue_image_upload(
    db: Session,
    *,
    venue_image_id: uuid.UUID,
    complete_request: VenueImageCompleteUpload | None = None,
    current_admin: User,
) -> VenueImageRead:
    venue_image = get_venue_image_or_404(db, venue_image_id)
    if venue_image.image_status == "removed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Removed venue images cannot be completed.",
        )

    try:
        object_properties = get_object_properties(venue_image.storage_object_key)
    except R2StorageConfigError as exc:
        raise storage_config_error_response(exc) from exc
    except R2ObjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded object was not found for this venue image.",
        ) from exc
    except R2StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cloudflare R2 could not verify the uploaded image.",
        ) from exc

    if object_properties.size_bytes != venue_image.size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image size does not match the requested size.",
        )

    object_content_type = (object_properties.content_type or "").lower()
    if object_content_type and object_content_type != venue_image.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image content type does not match the requested type.",
        )

    try:
        now = datetime.now(timezone.utc)
        before_snapshot = build_venue_image_audit_snapshot(venue_image)
        old_status = venue_image.image_status
        should_mark_primary = bool(venue_image.is_primary)
        if should_mark_primary:
            venue_image.is_primary = False

        venue_image.image_status = "active"
        venue_image.upload_completed_at = venue_image.upload_completed_at or now
        venue_image.etag = (
            (complete_request.etag if complete_request else None)
            or object_properties.etag
            or venue_image.etag
        )
        venue_image.updated_at = now
        db.add(venue_image)

        if should_mark_primary:
            clear_other_primary_venue_images(
                db,
                venue_id=venue_image.venue_id,
                excluding_image_id=venue_image.id,
            )
            db.flush()
            venue_image.is_primary = True
            venue_image.updated_at = now
            db.add(venue_image)

        record_admin_action(
            db,
            admin_user_id=current_admin.id,
            action_type="update_venue_image",
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
        db.commit()
        db.refresh(venue_image)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_venue_image_conflict_detail(exc),
        ) from exc

    return build_venue_image_read(venue_image)


def update_venue_image(
    db: Session,
    *,
    venue_image_id: uuid.UUID,
    image_update: VenueImageUpdate,
    current_admin: User,
) -> VenueImageRead:
    venue_image = get_venue_image_or_404(db, venue_image_id)
    update_data = image_update.model_dump(exclude_unset=True)
    reason = clean_optional_text(update_data.pop("reason", None))

    if "image_role" in update_data and update_data["image_role"] is not None:
        update_data["image_role"] = validate_image_role(update_data["image_role"])

    if "image_status" in update_data and update_data["image_status"] is not None:
        update_data["image_status"] = validate_image_status(update_data["image_status"])

    if update_data.get("image_status") == "removed":
        update_data["deleted_at"] = datetime.now(timezone.utc)
        update_data["is_primary"] = False

    before_snapshot = build_venue_image_audit_snapshot(venue_image)
    old_status = venue_image.image_status

    for text_field in ("alt_text", "caption"):
        if text_field in update_data:
            update_data[text_field] = clean_optional_text(update_data[text_field])

    for field_name, field_value in update_data.items():
        setattr(venue_image, field_name, field_value)

    if venue_image.image_status != "active" and venue_image.is_primary:
        venue_image.is_primary = False

    venue_image.updated_at = datetime.now(timezone.utc)

    if venue_image.image_status == "active" and venue_image.is_primary:
        clear_other_primary_venue_images(
            db,
            venue_id=venue_image.venue_id,
            excluding_image_id=venue_image.id,
        )

    try:
        action_type = (
            "remove_venue_image"
            if venue_image.image_status == "removed"
            else "update_venue_image"
        )
        record_admin_action(
            db,
            admin_user_id=current_admin.id,
            action_type=action_type,
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
        db.commit()
        db.refresh(venue_image)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_venue_image_conflict_detail(exc),
        ) from exc

    return build_venue_image_read(venue_image)
