import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.auth_service import (
    get_optional_current_app_user,
    require_active_admin,
    require_recent_active_admin,
    require_verified_user,
)
from backend.models import (
    Game,
    GameParticipant,
    User,
)
from backend.services.community_game_edit_service import host_edit_game_workflow
from backend.services.game_service import (
    build_game_detail_read,
    create_game_workflow,
    delete_game_workflow,
    get_game_or_404,
    get_public_game_or_404,
    list_browse_game_cards,
    list_games as list_games_workflow,
    list_public_game_participant_counts,
    list_public_game_participants,
    update_game_workflow,
)
from backend.services.game_cancellation_service import cancel_game_state_workflow
from backend.services.game_roster_service import (
    add_booking_game_guests_workflow,
    add_host_game_guests_workflow,
    join_game_roster_workflow,
    leave_game_roster_workflow,
    remove_game_guests_workflow,
)
from backend.schemas import (
    GameCancelCreate,
    GameBookingGuestAddCreate,
    GameCardListRead,
    GameCreate,
    GameGuestAddCreate,
    GameGuestAddRead,
    GameGuestRemoveCreate,
    GameGuestRemoveRead,
    GameHostEdit,
    GameDetailRead,
    GameParticipantCountRead,
    GameJoinCreate,
    GameJoinRead,
    GameLeaveCreate,
    GameLeaveRead,
    PublicGameParticipantRead,
    GameRead,
    GameUpdate,
)

router = APIRouter(prefix="/games", tags=["games"])


# This route creates the core game listing record after validating the related
# venue and user references that the row depends on.
@router.post("", response_model=GameRead, status_code=status.HTTP_201_CREATED)
def create_game(
    game: GameCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> Game:
    return create_game_workflow(db, game, current_admin)


@router.post(
    "/{game_id}/join", response_model=GameJoinRead, status_code=status.HTTP_201_CREATED
)
def join_game(
    game_id: uuid.UUID,
    join_request: GameJoinCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verified_user),
) -> GameJoinRead:
    return join_game_roster_workflow(db, game_id, join_request, current_user)


@router.post(
    "/{game_id}/leave", response_model=GameLeaveRead, status_code=status.HTTP_200_OK
)
def leave_game(
    game_id: uuid.UUID,
    leave_request: GameLeaveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verified_user),
) -> GameLeaveRead:
    return leave_game_roster_workflow(db, game_id, current_user)


@router.post(
    "/{game_id}/booking-guests/add",
    response_model=GameGuestAddRead,
    status_code=status.HTTP_201_CREATED,
)
def add_booking_game_guests(
    game_id: uuid.UUID,
    guest_request: GameBookingGuestAddCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verified_user),
) -> GameGuestAddRead:
    return add_booking_game_guests_workflow(db, game_id, guest_request, current_user)


@router.post(
    "/{game_id}/guests/add",
    response_model=GameGuestAddRead,
    status_code=status.HTTP_201_CREATED,
)
def add_host_game_guests(
    game_id: uuid.UUID,
    guest_request: GameGuestAddCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verified_user),
) -> GameGuestAddRead:
    return add_host_game_guests_workflow(db, game_id, guest_request, current_user)


@router.post(
    "/{game_id}/guests/remove",
    response_model=GameGuestRemoveRead,
    status_code=status.HTTP_200_OK,
)
def remove_game_guests(
    game_id: uuid.UUID,
    guest_request: GameGuestRemoveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verified_user),
) -> GameGuestRemoveRead:
    return remove_game_guests_workflow(db, game_id, guest_request, current_user)


@router.post(
    "/{game_id}/cancel",
    response_model=GameDetailRead,
    status_code=status.HTTP_200_OK,
)
def cancel_game(
    game_id: uuid.UUID,
    cancel_request: GameCancelCreate,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> GameDetailRead:
    game = cancel_game_state_workflow(db, game_id, cancel_request, current_user)
    return build_game_detail_read(game, current_user)


@router.get(
    "/participant-counts",
    response_model=list[GameParticipantCountRead],
    status_code=status.HTTP_200_OK,
)
def list_game_participant_counts(
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return list_public_game_participant_counts(db)


@router.get(
    "/browse",
    response_model=GameCardListRead,
    status_code=status.HTTP_200_OK,
)
def list_browse_games(
    starts_on: date | None = Query(default=None),
    limit: int = Query(default=40, ge=1),
    cursor: str | None = Query(default=None, max_length=2000),
    db: Session = Depends(get_db),
) -> GameCardListRead:
    return list_browse_game_cards(
        db,
        starts_on=starts_on,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/{game_id}/participants",
    response_model=list[PublicGameParticipantRead],
    status_code=status.HTTP_200_OK,
)
def list_game_roster_participants(
    game_id: uuid.UUID,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_app_user),
) -> list[GameParticipant]:
    participants = list_public_game_participants(db, game_id, current_user)
    game = db.get(Game, game_id)
    if game is not None and game.public_visibility_status == "hidden":
        response.headers["Cache-Control"] = "private, no-store"
    return participants


# This route fetches a single game record by its internal UUID.
@router.get("/{game_id}", response_model=GameDetailRead, status_code=status.HTTP_200_OK)
def get_game(
    game_id: uuid.UUID,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_app_user),
) -> GameDetailRead:
    game = get_public_game_or_404(db, game_id, current_user)
    if game.public_visibility_status == "hidden":
        response.headers["Cache-Control"] = "private, no-store"
    return build_game_detail_read(game, current_user)


# This route returns game records currently stored in the app database.
@router.get("", response_model=list[GameDetailRead], status_code=status.HTTP_200_OK)
def list_games(db: Session = Depends(get_db)) -> list[GameDetailRead]:
    return [build_game_detail_read(game) for game in list_games_workflow(db)]


# This route applies partial updates to an existing game record.
@router.patch("/{game_id}", response_model=GameRead, status_code=status.HTTP_200_OK)
def update_game(
    game_id: uuid.UUID,
    game_update: GameUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> Game:
    return update_game_workflow(db, game_id, game_update, current_admin)


@router.patch(
    "/{game_id}/host-edit", response_model=GameDetailRead, status_code=status.HTTP_200_OK
)
def host_edit_game(
    game_id: uuid.UUID,
    game_update: GameHostEdit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verified_user),
) -> GameDetailRead:
    game = host_edit_game_workflow(db, game_id, game_update, current_user)
    return build_game_detail_read(game, current_user)


# This route performs a soft delete so the game record remains available for
# history and operational review without appearing in normal game listings.
@router.delete("/{game_id}", response_model=GameRead, status_code=status.HTTP_200_OK)
def delete_game(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_recent_active_admin),
) -> Game:
    return delete_game_workflow(db, game_id, current_admin)
