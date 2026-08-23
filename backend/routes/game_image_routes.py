import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import GameImage, User
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import GameImageAdminRead, GameImagePublicRead
from backend.services.auth_service import require_active_admin
from backend.services.game_image_service import (
    get_admin_game_image_record,
    get_public_game_image_record,
    list_admin_game_image_records,
    list_public_game_image_records,
)
from backend.services.query_pagination import (
    DEFAULT_ADMIN_COLLECTION_LIMIT,
    DEFAULT_COLLECTION_LIMIT,
    MAX_ADMIN_COLLECTION_LIMIT,
    MAX_COLLECTION_LIMIT,
)

router = APIRouter(prefix="/game-images", tags=["game_images"])
admin_router = APIRouter(prefix="/admin/game-images", tags=["admin_game_images"])


@router.post("", status_code=status.HTTP_410_GONE)
def create_game_image(
    current_admin: User = Depends(require_active_admin),
) -> None:
    del current_admin
    raise_retired_mutation_route(
        code="game_image_scaffold_removed",
        message=(
            "Direct game-image creation is no longer supported. Use the "
            "authorized venue-image upload workflow."
        ),
    )


@router.get(
    "/{game_image_id}",
    response_model=GameImagePublicRead,
    status_code=status.HTTP_200_OK,
)
def get_game_image(
    game_image_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> GameImage:
    return get_public_game_image_record(db, game_image_id)


@router.get(
    "",
    response_model=list[GameImagePublicRead],
    status_code=status.HTTP_200_OK,
)
def list_game_images(
    game_id: uuid.UUID | None = None,
    uploaded_by_user_id: uuid.UUID | None = None,
    image_status: str | None = None,
    is_primary: bool | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_COLLECTION_LIMIT, ge=1, le=MAX_COLLECTION_LIMIT),
    db: Session = Depends(get_db),
) -> list[GameImage]:
    return list_public_game_image_records(
        db,
        game_id=game_id,
        uploaded_by_user_id=uploaded_by_user_id,
        image_status=image_status,
        is_primary=is_primary,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/{game_image_id}",
    status_code=status.HTTP_410_GONE,
)
def update_game_image(
    game_image_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
) -> None:
    del game_image_id, current_admin
    raise_retired_mutation_route(
        code="game_image_scaffold_removed",
        message=(
            "Direct game-image updates are no longer supported. Use the "
            "authorized venue-image upload workflow."
        ),
    )


@admin_router.get(
    "/{game_image_id}",
    response_model=GameImageAdminRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_game_image(
    game_image_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> GameImage:
    del current_admin
    return get_admin_game_image_record(db, game_image_id)


@admin_router.get(
    "",
    response_model=list[GameImageAdminRead],
    status_code=status.HTTP_200_OK,
)
def list_admin_game_images(
    game_id: uuid.UUID | None = None,
    uploaded_by_user_id: uuid.UUID | None = None,
    image_status: str | None = None,
    is_primary: bool | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(
        default=DEFAULT_ADMIN_COLLECTION_LIMIT,
        ge=1,
        le=MAX_ADMIN_COLLECTION_LIMIT,
    ),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> list[GameImage]:
    del current_admin
    return list_admin_game_image_records(
        db,
        game_id=game_id,
        uploaded_by_user_id=uploaded_by_user_id,
        image_status=image_status,
        is_primary=is_primary,
        limit=limit,
        offset=offset,
    )
