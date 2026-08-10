import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import CommunityGameDetail, Game, User
from backend.schemas import (
    CommunityGameDetailCreate,
    CommunityGameDetailHostRead,
    CommunityGameDetailHostUpsert,
    CommunityGameDetailPublicRead,
    CommunityGameDetailStaffRead,
    CommunityGameDetailUpdate,
)
from backend.services.auth_service import (
    get_optional_current_app_user,
    require_active_user,
    require_active_admin,
    require_verified_user,
)
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
    _current_admin: User = Depends(require_active_admin),
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
    current_user: User = Depends(require_verified_user),
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
    community_game_detail_id: uuid.UUID,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_app_user),
) -> CommunityGameDetailPublicRead:
    detail = get_public_community_game_detail(db, community_game_detail_id, current_user)
    db_detail = db.get(CommunityGameDetail, community_game_detail_id)
    game = db.get(Game, db_detail.game_id) if db_detail is not None else None
    if game is not None and game.public_visibility_status == "hidden":
        response.headers["Cache-Control"] = "private, no-store"
    return detail


@router.get(
    "",
    response_model=list[CommunityGameDetailPublicRead],
    status_code=status.HTTP_200_OK,
)
def list_community_game_details(
    response: Response,
    game_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_app_user),
) -> list[CommunityGameDetailPublicRead]:
    details = list_public_community_game_details(
        db,
        game_id=game_id,
        current_user=current_user,
    )
    game = db.get(Game, game_id) if game_id is not None else None
    if game is not None and game.public_visibility_status == "hidden":
        response.headers["Cache-Control"] = "private, no-store"
    return details


@router.patch(
    "/{community_game_detail_id}",
    response_model=CommunityGameDetailStaffRead,
    status_code=status.HTTP_200_OK,
)
def update_community_game_detail(
    community_game_detail_id: uuid.UUID,
    community_game_detail_update: CommunityGameDetailUpdate,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(require_active_admin),
) -> CommunityGameDetail:
    return update_community_game_detail_workflow(
        db, community_game_detail_id, community_game_detail_update
    )
