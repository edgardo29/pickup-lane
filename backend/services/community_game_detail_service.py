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
from backend.services.admin_action_service import (
    AUDIT_UNAVAILABLE_DETAIL,
    integrity_error_matches_table,
    record_admin_action,
    record_financial_sensitive_read,
)
from backend.services.auth_service import user_is_active_admin
from backend.services.game_rules import (
    HOST_EDITABLE_GAME_STATUSES,
    require_game_not_started,
)
from backend.services.game_service import user_can_view_hidden_game
from backend.services.moderation_surfacing_service import surface_community_game_text
from backend.services.query_pagination import (
    DEFAULT_COLLECTION_LIMIT,
    MAX_COLLECTION_LIMIT,
    bounded_collection_limit,
    bounded_collection_offset,
)


def build_community_game_detail_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_community_game_details_game_id" in error_text:
        return "This game already has community game details."

    return "Community game details could not be saved."


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
    db: Session,
    community_game_detail: CommunityGameDetailCreate,
    admin_user: User,
) -> CommunityGameDetail:
    detail_data = community_game_detail.model_dump()
    db_game = get_community_game_or_404(db, community_game_detail.game_id)
    validate_community_game_detail_business_rules(detail_data, db_game)

    new_community_game_detail = CommunityGameDetail(id=uuid.uuid4(), **detail_data)

    try:
        db.add(new_community_game_detail)
        try:
            record_admin_action(
                db,
                admin_user_id=admin_user.id,
                action_type="create_community_game_detail",
                outcome="succeeded",
                target_game_id=new_community_game_detail.game_id,
                metadata={
                    "source": "admin_community_game_detail",
                    "after": {
                        "detail_present": True,
                        "game_id": str(new_community_game_detail.game_id),
                    },
                },
            )
        except (HTTPException, ValueError):
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=AUDIT_UNAVAILABLE_DETAIL,
            ) from None
        db.flush()
        db.commit()
    except IntegrityError as exc:
        audit_failure = integrity_error_matches_table(exc, "admin_actions")
        db.rollback()
        if audit_failure:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=AUDIT_UNAVAILABLE_DETAIL,
            ) from None
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_community_game_detail_conflict_detail(exc),
        ) from exc

    db.refresh(new_community_game_detail)
    surface_community_game_text(db, game_id=new_community_game_detail.game_id)
    return new_community_game_detail


def get_public_community_game_detail(
    db: Session,
    community_game_detail_id: uuid.UUID,
    current_user: User | None = None,
) -> CommunityGameDetailPublicRead:
    detail_ref = db.execute(
        select(
            CommunityGameDetail.id,
            CommunityGameDetail.game_id,
            Game.game_type,
            Game.public_visibility_status,
            Game.deleted_at,
        )
        .join(Game, CommunityGameDetail.game_id == Game.id)
        .where(CommunityGameDetail.id == community_game_detail_id)
    ).one_or_none()
    if (
        detail_ref is not None
        and detail_ref.deleted_at is None
        and detail_ref.game_type == "community"
        and detail_ref.public_visibility_status != "visible"
        and current_user is not None
        and user_is_active_admin(current_user)
    ):
        record_financial_sensitive_read(
            authenticated_admin_id=current_user.id,
            action_type="read_staff_hidden_community_payment_detail",
            target_id=detail_ref.game_id,
        )
    elif detail_ref is not None and (
        detail_ref.deleted_at is not None or detail_ref.game_type != "community"
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community game details not found.",
        )
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
    if db_game.public_visibility_status != "visible" and (
        current_user is None
        or not user_can_view_hidden_game(
            db,
            db_game,
            current_user,
            now=datetime.now(timezone.utc),
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community game details not found.",
        )
    return serialize_public_community_game_detail(db_community_game_detail)


def user_can_view_community_game_details(
    db: Session,
    db_game: Game,
    current_user: User | None,
) -> bool:
    if db_game.public_visibility_status == "visible":
        return True

    if current_user is None:
        return False

    return user_can_view_hidden_game(
        db,
        db_game,
        current_user,
        now=datetime.now(timezone.utc),
    )


def list_public_community_game_details(
    db: Session,
    *,
    game_id: uuid.UUID | None = None,
    current_user: User | None = None,
    limit: int = DEFAULT_COLLECTION_LIMIT,
    offset: int = 0,
) -> list[CommunityGameDetailPublicRead]:
    statement = (
        select(CommunityGameDetail)
        .join(Game, CommunityGameDetail.game_id == Game.id)
        .where(Game.deleted_at.is_(None))
    )

    if game_id is not None:
        statement = statement.where(CommunityGameDetail.game_id == game_id)

    if game_id is not None:
        game_ref = db.execute(
            select(Game.id, Game.game_type, Game.public_visibility_status, Game.deleted_at)
            .where(Game.id == game_id)
        ).one_or_none()
        if game_ref is None or game_ref.deleted_at is not None or game_ref.game_type != "community":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Community game details not found.",
            )
        if (
            game_ref.public_visibility_status != "visible"
            and current_user is not None
            and user_is_active_admin(current_user)
        ):
            record_financial_sensitive_read(
                authenticated_admin_id=current_user.id,
                action_type="read_staff_hidden_community_payment_list",
                target_id=game_id,
            )
        db_game = db.get(Game, game_id)
        if not user_can_view_community_game_details(db, db_game, current_user):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Community game details not found.",
            )
    else:
        statement = statement.where(Game.public_visibility_status == "visible")

    community_game_details = db.scalars(
        statement.order_by(
            CommunityGameDetail.created_at.desc(),
            CommunityGameDetail.id.desc(),
        )
        .offset(bounded_collection_offset(offset))
        .limit(bounded_collection_limit(limit, max_limit=MAX_COLLECTION_LIMIT))
    ).all()
    return [
        serialize_public_community_game_detail(detail)
        for detail in community_game_details
    ]


def update_community_game_detail_workflow(
    db: Session,
    community_game_detail_id: uuid.UUID,
    community_game_detail_update: CommunityGameDetailUpdate,
    admin_user: User,
) -> CommunityGameDetail:
    db_community_game_detail = db.scalar(
        select(CommunityGameDetail)
        .where(CommunityGameDetail.id == community_game_detail_id)
        .execution_options(populate_existing=True)
        .with_for_update()
    )

    if db_community_game_detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community game details not found.",
        )

    update_data = community_game_detail_update.model_dump(exclude_unset=True)
    prior_game_id = db_community_game_detail.game_id
    changed_fields = sorted(
        field_name
        for field_name, field_value in update_data.items()
        if field_value != getattr(db_community_game_detail, field_name)
    )
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
        try:
            record_admin_action(
                db,
                admin_user_id=admin_user.id,
                action_type="update_community_game_detail",
                outcome="succeeded",
                target_game_id=db_community_game_detail.game_id,
                metadata={
                    "source": "admin_community_game_detail",
                    "before": {"game_id": str(prior_game_id)},
                    "after": {
                        "game_id": str(db_community_game_detail.game_id),
                        "changed_fields": changed_fields,
                    },
                },
            )
        except (HTTPException, ValueError):
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=AUDIT_UNAVAILABLE_DETAIL,
            ) from None
        db.flush()
        db.commit()
    except IntegrityError as exc:
        audit_failure = integrity_error_matches_table(exc, "admin_actions")
        db.rollback()
        if audit_failure:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=AUDIT_UNAVAILABLE_DETAIL,
            ) from None
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_community_game_detail_conflict_detail(exc),
        ) from exc

    db.refresh(db_community_game_detail)
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
            payment_methods_snapshot=[
                method.model_dump() for method in detail_update.payment_methods_snapshot
            ],
            payment_instructions_snapshot=detail_update.payment_instructions_snapshot,
        )
    else:
        db_community_game_detail.payment_methods_snapshot = (
            [method.model_dump() for method in detail_update.payment_methods_snapshot]
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
