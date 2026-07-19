import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import CommunityGameDetail, Game, User
from backend.schemas.community_game_detail_schema import (
    CommunityGameDetailCreate,
    CommunityGameDetailHostUpsert,
    CommunityGameDetailPublicRead,
    CommunityGameDetailUpdate,
)
from backend.services.game_rules import (
    HOST_EDITABLE_GAME_STATUSES,
    require_game_not_started,
    require_publicly_visible_game,
)
from backend.services.moderation_surfacing_service import surface_community_game_text


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
    detail_data: dict[str, object], db_game: Game
) -> None:
    payment_methods = detail_data["payment_methods_snapshot"]
    if not isinstance(payment_methods, list) or not all(
        isinstance(method, dict) for method in payment_methods
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payment_methods_snapshot must be a list of payment method objects.",
        )

    if (
        db_game.payment_collection_type == "external_host"
        and db_game.price_per_player_cents > 0
        and len(payment_methods) == 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paid community games require at least one host payment method.",
        )


def serialize_public_community_game_detail(
    detail: CommunityGameDetail,
) -> CommunityGameDetailPublicRead:
    serialized = CommunityGameDetailPublicRead.model_validate(detail)
    if serialized.payment_text_moderation_status == "hidden":
        return serialized.model_copy(
            update={
                "payment_methods_snapshot": [],
                "payment_instructions_snapshot": None,
            }
        )
    return serialized


def create_community_game_detail_workflow(
    db: Session, community_game_detail: CommunityGameDetailCreate
) -> CommunityGameDetail:
    detail_data = community_game_detail.model_dump()
    db_game = get_community_game_or_404(db, community_game_detail.game_id)
    validate_community_game_detail_business_rules(detail_data, db_game)

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

    surface_community_game_text(db, game_id=new_community_game_detail.game_id)
    return new_community_game_detail


def get_public_community_game_detail(
    db: Session,
    community_game_detail_id: uuid.UUID,
) -> CommunityGameDetailPublicRead:
    db_community_game_detail = db.get(
        CommunityGameDetail, community_game_detail_id
    )

    if db_community_game_detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community game details not found.",
        )

    db_game = db.get(Game, db_community_game_detail.game_id)
    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community game details not found.",
        )
    require_publicly_visible_game(db_game)

    return serialize_public_community_game_detail(db_community_game_detail)


def list_public_community_game_details(
    db: Session,
    *,
    game_id: uuid.UUID | None = None,
) -> list[CommunityGameDetailPublicRead]:
    statement = (
        select(CommunityGameDetail)
        .join(Game, CommunityGameDetail.game_id == Game.id)
        .where(Game.deleted_at.is_(None))
    )

    if game_id is not None:
        statement = statement.where(CommunityGameDetail.game_id == game_id)

    statement = statement.where(
        (Game.game_type != "community") | (Game.public_visibility_status == "visible")
    )

    community_game_details = db.scalars(
        statement.order_by(CommunityGameDetail.created_at.desc())
    ).all()
    return [
        serialize_public_community_game_detail(detail)
        for detail in community_game_details
    ]


def update_community_game_detail_workflow(
    db: Session,
    community_game_detail_id: uuid.UUID,
    community_game_detail_update: CommunityGameDetailUpdate,
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
    db_game = get_community_game_or_404(db, effective_detail_data["game_id"])
    validate_community_game_detail_business_rules(effective_detail_data, db_game)

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

    surface_community_game_text(db, game_id=db_community_game_detail.game_id)
    return db_community_game_detail


def get_host_community_game_detail_workflow(
    db: Session,
    game_id: uuid.UUID,
    current_user: User,
) -> CommunityGameDetail:
    db_game = get_community_game_or_404(db, game_id)
    if db_game.host_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the game host can edit this game.",
        )

    db_community_game_detail = db.scalar(
        select(CommunityGameDetail).where(CommunityGameDetail.game_id == game_id)
    )
    if db_community_game_detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community game details not found.",
        )
    return db_community_game_detail


def upsert_host_community_game_detail_workflow(
    db: Session,
    game_id: uuid.UUID,
    detail_update: CommunityGameDetailHostUpsert,
    current_user: User,
) -> CommunityGameDetail:
    db_game = get_community_game_or_404(db, game_id)

    if db_game.host_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the game host can edit this game.",
        )

    if (
        db_game.publish_status != "published"
        or db_game.game_status not in HOST_EDITABLE_GAME_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published active games can be edited.",
        )

    now = datetime.now(timezone.utc)
    require_game_not_started(
        db_game, now, "Games cannot be edited after start time."
    )

    detail_data = {
        "game_id": game_id,
        **detail_update.model_dump(),
    }
    validate_community_game_detail_business_rules(detail_data, db_game)

    db_community_game_detail = db.scalar(
        select(CommunityGameDetail).where(CommunityGameDetail.game_id == game_id)
    )
    if db_community_game_detail is None:
        db_community_game_detail = CommunityGameDetail(
            id=uuid.uuid4(),
            game_id=game_id,
            payment_methods_snapshot=detail_update.payment_methods_snapshot,
            payment_instructions_snapshot=detail_update.payment_instructions_snapshot,
        )
    else:
        db_community_game_detail.payment_methods_snapshot = (
            detail_update.payment_methods_snapshot
        )
        db_community_game_detail.payment_instructions_snapshot = (
            detail_update.payment_instructions_snapshot
        )
        db_community_game_detail.updated_at = now

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

    surface_community_game_text(db, game_id=db_community_game_detail.game_id)
    return db_community_game_detail
