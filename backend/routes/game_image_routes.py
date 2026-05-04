import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Game, GameImage, User
from backend.schemas import GameImageCreate, GameImageRead, GameImageUpdate

router = APIRouter(prefix="/game-images", tags=["game_images"])

VALID_IMAGE_ROLES = {
    "card",
    "gallery",
}
VALID_IMAGE_STATUSES = {
    "active",
    "hidden",
    "removed",
}


def build_game_image_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_game_images_one_active_primary_per_game" in error_text:
        return "This game already has an active primary image."

    if "ck_game_images_image_role" in error_text:
        return "image_role is not supported."

    if "ck_game_images_image_status" in error_text:
        return "image_status is not supported."

    if "ck_game_images_image_url_not_empty" in error_text:
        return "image_url must not be empty."

    if "ck_game_images_sort_order_non_negative" in error_text:
        return "sort_order must be greater than or equal to 0."

    return error_text


def get_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


def get_active_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uploaded by user not found.",
        )

    return db_user


def validate_game_image_business_rules(image_data: dict[str, Any]) -> None:
    for field_name in (
        "game_id",
        "image_url",
        "image_role",
        "image_status",
        "is_primary",
        "sort_order",
    ):
        if image_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if image_data["image_role"] not in VALID_IMAGE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_role is not supported.",
        )

    if image_data["image_status"] not in VALID_IMAGE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_status is not supported.",
        )

    if not image_data["image_url"].strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_url must not be empty.",
        )

    if image_data["sort_order"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sort_order must be greater than or equal to 0.",
        )


def validate_game_image_references(
    db: Session,
    image_data: dict[str, Any],
) -> None:
    get_game_or_404(db, image_data["game_id"])

    if image_data["uploaded_by_user_id"] is not None:
        get_active_user_or_404(db, image_data["uploaded_by_user_id"])


def validate_game_image_update_rules(update_data: dict[str, Any]) -> None:
    for field_name in (
        "image_url",
        "image_role",
        "image_status",
        "is_primary",
        "sort_order",
    ):
        if field_name in update_data and update_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )


def normalize_game_image_lifecycle_fields(
    image_data: dict[str, Any],
) -> dict[str, Any]:
    normalized_data = dict(image_data)

    if (
        normalized_data.get("deleted_at") is not None
        or normalized_data.get("image_status") == "removed"
    ):
        normalized_data["image_status"] = "removed"
        normalized_data["is_primary"] = False

        if normalized_data.get("deleted_at") is None:
            normalized_data["deleted_at"] = datetime.now(timezone.utc)

    return normalized_data


# This route attaches one image to a game for Browse cards or Game Details
# galleries.
@router.post("", response_model=GameImageRead, status_code=status.HTTP_201_CREATED)
def create_game_image(
    game_image: GameImageCreate,
    db: Session = Depends(get_db),
) -> GameImage:
    image_data = normalize_game_image_lifecycle_fields(game_image.model_dump())
    validate_game_image_business_rules(image_data)
    validate_game_image_references(db, image_data)

    new_game_image = GameImage(
        id=uuid.uuid4(),
        **image_data,
    )

    try:
        db.add(new_game_image)
        db.commit()
        db.refresh(new_game_image)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_image_conflict_detail(exc),
        ) from exc

    return new_game_image


# This route fetches a single game image by its internal UUID.
@router.get(
    "/{game_image_id}",
    response_model=GameImageRead,
    status_code=status.HTTP_200_OK,
)
def get_game_image(
    game_image_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> GameImage:
    db_game_image = db.get(GameImage, game_image_id)

    if db_game_image is None or db_game_image.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game image not found.",
        )

    return db_game_image


# This route returns game images currently stored in the app database.
@router.get("", response_model=list[GameImageRead], status_code=status.HTTP_200_OK)
def list_game_images(
    game_id: uuid.UUID | None = None,
    uploaded_by_user_id: uuid.UUID | None = None,
    image_status: str | None = None,
    is_primary: bool | None = None,
    db: Session = Depends(get_db),
) -> list[GameImage]:
    statement = select(GameImage).where(GameImage.deleted_at.is_(None))

    if game_id is not None:
        statement = statement.where(GameImage.game_id == game_id)

    if uploaded_by_user_id is not None:
        statement = statement.where(
            GameImage.uploaded_by_user_id == uploaded_by_user_id
        )

    if image_status is not None:
        if image_status not in VALID_IMAGE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="image_status is not supported.",
            )
        statement = statement.where(GameImage.image_status == image_status)

    if is_primary is not None:
        statement = statement.where(GameImage.is_primary == is_primary)

    game_images = db.scalars(
        statement.order_by(GameImage.sort_order.asc(), GameImage.created_at.asc())
    ).all()
    return list(game_images)


# This route applies partial image metadata updates, including soft removal.
@router.patch(
    "/{game_image_id}",
    response_model=GameImageRead,
    status_code=status.HTTP_200_OK,
)
def update_game_image(
    game_image_id: uuid.UUID,
    game_image_update: GameImageUpdate,
    db: Session = Depends(get_db),
) -> GameImage:
    db_game_image = db.get(GameImage, game_image_id)

    if db_game_image is None or db_game_image.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game image not found.",
        )

    update_data = game_image_update.model_dump(exclude_unset=True)
    validate_game_image_update_rules(update_data)

    effective_image_data = normalize_game_image_lifecycle_fields(
        {
            "game_id": db_game_image.game_id,
            "uploaded_by_user_id": update_data.get(
                "uploaded_by_user_id",
                db_game_image.uploaded_by_user_id,
            ),
            "image_url": update_data.get("image_url", db_game_image.image_url),
            "image_role": update_data.get("image_role", db_game_image.image_role),
            "image_status": update_data.get("image_status", db_game_image.image_status),
            "is_primary": update_data.get("is_primary", db_game_image.is_primary),
            "sort_order": update_data.get("sort_order", db_game_image.sort_order),
            "deleted_at": update_data.get("deleted_at", db_game_image.deleted_at),
        }
    )
    validate_game_image_business_rules(effective_image_data)
    validate_game_image_references(db, effective_image_data)

    for field_name, field_value in effective_image_data.items():
        setattr(db_game_image, field_name, field_value)

    db_game_image.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_game_image)
        db.commit()
        db.refresh(db_game_image)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_image_conflict_detail(exc),
        ) from exc

    return db_game_image
