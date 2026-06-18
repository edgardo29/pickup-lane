from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import CommunityGamePublishCreate, CommunityGamePublishRead
from backend.services.auth_service import require_active_user
from backend.services.community_game_publish_service import (
    publish_community_game_workflow,
)

router = APIRouter(prefix="/community-games", tags=["community_games"])


@router.post(
    "/publish",
    response_model=CommunityGamePublishRead,
    status_code=status.HTTP_201_CREATED,
)
def publish_community_game(
    publish_request: CommunityGamePublishCreate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> CommunityGamePublishRead:
    return publish_community_game_workflow(db, publish_request, current_user)
