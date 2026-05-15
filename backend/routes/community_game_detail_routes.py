import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import CommunityGameDetail, Game
from backend.schemas import (
    CommunityGameDetailCreate,
    CommunityGameDetailRead,
    CommunityGameDetailUpdate,
)

router = APIRouter(prefix="/community-game-details", tags=["community_game_details"])

def build_community_game_detail_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_community_game_details_game_id" in error_text:
        return "This game already has community game details."

    return error_text


def get_community_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    if db_game.game_type != "community":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Community game details require a community game.",
        )

    return db_game


def validate_community_game_detail_business_rules(
    detail_data: dict[str, object]
) -> None:
    payment_methods = detail_data["payment_methods_snapshot"]
    if not isinstance(payment_methods, list) or not all(
        isinstance(method, dict) for method in payment_methods
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payment_methods_snapshot must be a list of payment method objects.",
        )


@router.post(
    "",
    response_model=CommunityGameDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def create_community_game_detail(
    community_game_detail: CommunityGameDetailCreate,
    db: Session = Depends(get_db),
) -> CommunityGameDetail:
    detail_data = community_game_detail.model_dump()
    validate_community_game_detail_business_rules(detail_data)
    get_community_game_or_404(db, community_game_detail.game_id)

    new_community_game_detail = CommunityGameDetail(id=uuid.uuid4(), **detail_data)

    try:
        db.add(new_community_game_detail)
        db.commit()
        db.refresh(new_community_game_detail)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_community_game_detail_conflict_detail(exc),
        ) from exc

    return new_community_game_detail


@router.get(
    "/{community_game_detail_id}",
    response_model=CommunityGameDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_community_game_detail(
    community_game_detail_id: uuid.UUID, db: Session = Depends(get_db)
) -> CommunityGameDetail:
    db_community_game_detail = db.get(
        CommunityGameDetail, community_game_detail_id
    )

    if db_community_game_detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community game details not found.",
        )

    return db_community_game_detail


@router.get(
    "", response_model=list[CommunityGameDetailRead], status_code=status.HTTP_200_OK
)
def list_community_game_details(
    game_id: uuid.UUID | None = None, db: Session = Depends(get_db)
) -> list[CommunityGameDetail]:
    statement = select(CommunityGameDetail)

    if game_id is not None:
        statement = statement.where(CommunityGameDetail.game_id == game_id)

    community_game_details = db.scalars(
        statement.order_by(CommunityGameDetail.created_at.desc())
    ).all()
    return list(community_game_details)


@router.patch(
    "/{community_game_detail_id}",
    response_model=CommunityGameDetailRead,
    status_code=status.HTTP_200_OK,
)
def update_community_game_detail(
    community_game_detail_id: uuid.UUID,
    community_game_detail_update: CommunityGameDetailUpdate,
    db: Session = Depends(get_db),
) -> CommunityGameDetail:
    db_community_game_detail = db.get(
        CommunityGameDetail, community_game_detail_id
    )

    if db_community_game_detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community game details not found.",
        )

    update_data = community_game_detail_update.model_dump(exclude_unset=True)
    effective_detail_data = {
        "game_id": update_data.get("game_id", db_community_game_detail.game_id),
        "payment_methods_snapshot": update_data.get(
            "payment_methods_snapshot",
            db_community_game_detail.payment_methods_snapshot,
        ),
        "payment_instructions_snapshot": update_data.get(
            "payment_instructions_snapshot",
            db_community_game_detail.payment_instructions_snapshot,
        ),
    }
    validate_community_game_detail_business_rules(effective_detail_data)
    get_community_game_or_404(db, effective_detail_data["game_id"])

    for field_name, field_value in update_data.items():
        setattr(db_community_game_detail, field_name, field_value)

    db_community_game_detail.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_community_game_detail)
        db.commit()
        db.refresh(db_community_game_detail)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_community_game_detail_conflict_detail(exc),
        ) from exc

    return db_community_game_detail
