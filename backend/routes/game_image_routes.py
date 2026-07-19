import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import GameImage, User
from backend.schemas import GameImageCreate, GameImageRead, GameImageUpdate
from backend.services.auth_service import require_active_admin
from backend.services.game_image_service import (
    create_game_image_record,
    get_admin_game_image_record,
    get_public_game_image_record,
    list_admin_game_image_records,
    list_public_game_image_records,
    update_game_image_record,
)

router = APIRouter(prefix="/game-images", tags=["game_images"])
admin_router = APIRouter(prefix="/admin/game-images", tags=["admin_game_images"])


@router.post("", response_model=GameImageRead, status_code=status.HTTP_201_CREATED)
def create_game_image(
    game_image: GameImageCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> GameImage:
    del current_admin
    return create_game_image_record(db, game_image)


@router.get(
    "/{game_image_id}",
    response_model=GameImageRead,
    status_code=status.HTTP_200_OK,
)
def get_game_image(
    game_image_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> GameImage:
    return get_public_game_image_record(db, game_image_id)


@router.get("", response_model=list[GameImageRead], status_code=status.HTTP_200_OK)
def list_game_images(
    game_id: uuid.UUID | None = None,
    uploaded_by_user_id: uuid.UUID | None = None,
    image_status: str | None = None,
    is_primary: bool | None = None,
    db: Session = Depends(get_db),
) -> list[GameImage]:
    return list_public_game_image_records(
        db,
        game_id=game_id,
        uploaded_by_user_id=uploaded_by_user_id,
        image_status=image_status,
        is_primary=is_primary,
    )


@router.patch(
    "/{game_image_id}",
    response_model=GameImageRead,
    status_code=status.HTTP_200_OK,
)
def update_game_image(
    game_image_id: uuid.UUID,
    game_image_update: GameImageUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> GameImage:
    del current_admin
    return update_game_image_record(db, game_image_id, game_image_update)


@admin_router.get(
    "/{game_image_id}",
    response_model=GameImageRead,
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
    response_model=list[GameImageRead],
    status_code=status.HTTP_200_OK,
)
def list_admin_game_images(
    game_id: uuid.UUID | None = None,
    uploaded_by_user_id: uuid.UUID | None = None,
    image_status: str | None = None,
    is_primary: bool | None = None,
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
    )
