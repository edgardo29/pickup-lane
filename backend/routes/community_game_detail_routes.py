import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import CommunityGameDetail, User
from backend.schemas import (
    CommunityGameDetailCreate,
    CommunityGameDetailHostRead,
    CommunityGameDetailHostUpsert,
    CommunityGameDetailPublicRead,
    CommunityGameDetailStaffRead,
    CommunityGameDetailUpdate,
)
from backend.services.admin_permission_service import PERMISSION_COMMUNITY_GAMES_WRITE
from backend.services.auth_service import require_active_user, require_admin_permission
from backend.services.community_game_detail_service import (
    create_community_game_detail_workflow,
    get_host_community_game_detail_workflow,
    serialize_public_community_game_detail,
    update_community_game_detail_workflow,
    upsert_host_community_game_detail_workflow,
)

router = APIRouter(prefix="/community-game-details", tags=["community_game_details"])


@router.post(
    "",
    response_model=CommunityGameDetailStaffRead,
    status_code=status.HTTP_201_CREATED,
)
def create_community_game_detail(
    community_game_detail: CommunityGameDetailCreate,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(
        require_admin_permission(PERMISSION_COMMUNITY_GAMES_WRITE)
    ),
) -> CommunityGameDetail:
    return create_community_game_detail_workflow(db, community_game_detail)


@router.put(
    "/games/{game_id}/host-edit",
    response_model=CommunityGameDetailHostRead,
    status_code=status.HTTP_200_OK,
)
def upsert_host_community_game_detail(
    game_id: uuid.UUID,
    detail_update: CommunityGameDetailHostUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> CommunityGameDetail:
    return upsert_host_community_game_detail_workflow(
        db, game_id, detail_update, current_user
    )


@router.get(
    "/games/{game_id}/host-edit",
    response_model=CommunityGameDetailHostRead,
    status_code=status.HTTP_200_OK,
)
def get_host_community_game_detail(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> CommunityGameDetail:
    return get_host_community_game_detail_workflow(db, game_id, current_user)


@router.get(
    "/{community_game_detail_id}",
    response_model=CommunityGameDetailPublicRead,
    status_code=status.HTTP_200_OK,
)
def get_community_game_detail(
    community_game_detail_id: uuid.UUID, db: Session = Depends(get_db)
) -> CommunityGameDetailPublicRead:
    db_community_game_detail = db.get(
        CommunityGameDetail, community_game_detail_id
    )

    if db_community_game_detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community game details not found.",
        )

    return serialize_public_community_game_detail(db_community_game_detail)


@router.get(
    "",
    response_model=list[CommunityGameDetailPublicRead],
    status_code=status.HTTP_200_OK,
)
def list_community_game_details(
    game_id: uuid.UUID | None = None, db: Session = Depends(get_db)
) -> list[CommunityGameDetailPublicRead]:
    statement = select(CommunityGameDetail)

    if game_id is not None:
        statement = statement.where(CommunityGameDetail.game_id == game_id)

    community_game_details = db.scalars(
        statement.order_by(CommunityGameDetail.created_at.desc())
    ).all()
    return [
        serialize_public_community_game_detail(detail)
        for detail in community_game_details
    ]


@router.patch(
    "/{community_game_detail_id}",
    response_model=CommunityGameDetailStaffRead,
    status_code=status.HTTP_200_OK,
)
def update_community_game_detail(
    community_game_detail_id: uuid.UUID,
    community_game_detail_update: CommunityGameDetailUpdate,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(
        require_admin_permission(PERMISSION_COMMUNITY_GAMES_WRITE)
    ),
) -> CommunityGameDetail:
    return update_community_game_detail_workflow(
        db, community_game_detail_id, community_game_detail_update
    )
