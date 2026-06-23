import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import GameParticipant, User
from backend.schemas import (
    GameParticipantCreate,
    GameParticipantRead,
    GameParticipantUpdate,
    PublicGameParticipantRead,
)
from backend.services.admin_permission_service import (
    PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
)
from backend.services.auth_service import (
    get_current_app_user,
    require_admin_permission,
)
from backend.services.game_participant_service import (
    create_game_participant_workflow,
    get_game_participant_for_user_or_404,
    list_game_participants as list_game_participants_workflow,
    update_game_participant_workflow,
)
from backend.services.game_service import list_current_user_game_participants

router = APIRouter(prefix="/game-participants", tags=["game_participants"])


# Admin-only endpoint for protected roster row creation.
@router.post(
    "", response_model=GameParticipantRead, status_code=status.HTTP_201_CREATED
)
def create_game_participant(
    participant: GameParticipantCreate,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE)
    ),
) -> GameParticipant:
    return create_game_participant_workflow(db, participant)


@router.get(
    "/me",
    response_model=list[PublicGameParticipantRead],
    status_code=status.HTTP_200_OK,
)
def list_my_game_participants(
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> list[GameParticipant]:
    return list_current_user_game_participants(db, current_user)


# Fetches a single participant visible to the current user or roster admins.
@router.get(
    "/{participant_id}",
    response_model=GameParticipantRead,
    status_code=status.HTTP_200_OK,
)
def get_game_participant(
    participant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> GameParticipant:
    return get_game_participant_for_user_or_404(db, participant_id, current_user)


# Admin-only endpoint for roster row queries.
@router.get("", response_model=list[GameParticipantRead], status_code=status.HTTP_200_OK)
def list_game_participants(
    game_id: uuid.UUID | None = None,
    booking_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    participant_status: str | None = None,
    attendance_status: str | None = None,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE)
    ),
) -> list[GameParticipant]:
    return list_game_participants_workflow(
        db,
        game_id=game_id,
        booking_id=booking_id,
        user_id=user_id,
        participant_status=participant_status,
        attendance_status=attendance_status,
    )


# Admin-only endpoint for protected roster row updates.
@router.patch(
    "/{participant_id}",
    response_model=GameParticipantRead,
    status_code=status.HTTP_200_OK,
)
def update_game_participant(
    participant_id: uuid.UUID,
    participant_update: GameParticipantUpdate,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE)
    ),
) -> GameParticipant:
    return update_game_participant_workflow(db, participant_id, participant_update)
