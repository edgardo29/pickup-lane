import uuid

from fastapi import APIRouter, Depends, status
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
    get_public_community_game_detail,
    list_public_community_game_details,
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
    return get_public_community_game_detail(db, community_game_detail_id)


@router.get(
    "",
    response_model=list[CommunityGameDetailPublicRead],
    status_code=status.HTTP_200_OK,
)
def list_community_game_details(
    game_id: uuid.UUID | None = None, db: Session = Depends(get_db)
) -> list[CommunityGameDetailPublicRead]:
    return list_public_community_game_details(db, game_id=game_id)


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
