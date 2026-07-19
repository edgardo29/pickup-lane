import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    VenueImageCompleteUpload,
    VenueImageRead,
    VenueImageUpdate,
    VenueImageUploadCreate,
    VenueImageUploadRead,
)
from backend.services.auth_service import require_active_admin
from backend.services.venue_image_service import (
    check_venue_image_upload_readiness,
    complete_venue_image_upload,
    create_venue_image_upload,
    list_admin_venue_images as list_admin_venue_images_workflow,
    list_public_venue_images,
    update_venue_image,
)

public_router = APIRouter(prefix="/venue-images", tags=["venue_images"])
admin_router = APIRouter(tags=["admin_venue_images"])


@public_router.get("", response_model=list[VenueImageRead])
def list_venue_images(
    venue_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[VenueImageRead]:
    return list_public_venue_images(db, venue_id=venue_id)


@admin_router.get("/admin/venue-images/upload-readiness")
def check_admin_venue_image_upload_readiness(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> dict[str, bool]:
    del current_admin
    return check_venue_image_upload_readiness(db)


@admin_router.get(
    "/admin/venues/{venue_id}/images",
    response_model=list[VenueImageRead],
)
def list_admin_venue_images(
    venue_id: uuid.UUID,
    image_status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> list[VenueImageRead]:
    del current_admin
    return list_admin_venue_images_workflow(
        db,
        venue_id=venue_id,
        image_status=image_status,
    )


@admin_router.post(
    "/admin/venues/{venue_id}/images/upload-url",
    response_model=VenueImageUploadRead,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_venue_image_upload_url(
    venue_id: uuid.UUID,
    upload_request: VenueImageUploadCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> VenueImageUploadRead:
    return create_venue_image_upload(
        db,
        venue_id=venue_id,
        upload_request=upload_request,
        current_admin=current_admin,
    )


@admin_router.post(
    "/admin/venue-images/{venue_image_id}/complete",
    response_model=VenueImageRead,
)
def complete_admin_venue_image_upload(
    venue_image_id: uuid.UUID,
    complete_request: VenueImageCompleteUpload | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> VenueImageRead:
    return complete_venue_image_upload(
        db,
        venue_image_id=venue_image_id,
        complete_request=complete_request,
        current_admin=current_admin,
    )


@admin_router.patch(
    "/admin/venue-images/{venue_image_id}",
    response_model=VenueImageRead,
)
def update_admin_venue_image(
    venue_image_id: uuid.UUID,
    image_update: VenueImageUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> VenueImageRead:
    return update_venue_image(
        db,
        venue_image_id=venue_image_id,
        image_update=image_update,
        current_admin=current_admin,
    )
