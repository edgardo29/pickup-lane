import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, GameParticipant, User, WaitlistEntry
from backend.schemas import (
    AdminOfficialGameCreate,
    AdminOfficialGameHostAssign,
    AdminOfficialGameHostRemove,
    AdminOfficialGameListRead,
    AdminOfficialGamePlayerAdd,
    AdminOfficialGamePlayerRemove,
    AdminOfficialGameRead,
    AdminOfficialGameUpdate,
    BookingRead,
    CurrentUserWaitlistEntryRead,
    GameParticipantRead,
)
from backend.services.admin_permission_service import (
    PERMISSION_OFFICIAL_GAMES_READ,
    PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
    PERMISSION_OFFICIAL_GAMES_WRITE,
)
from backend.services.auth_service import require_admin_permission
from backend.services.official_game_service import (
    add_official_game_player,
    assign_official_game_host,
    create_official_game,
    get_official_game_or_404,
    list_official_game_bookings,
    list_official_game_waitlist_entries,
    list_official_games,
    remove_official_game_host,
    remove_official_game_player,
    update_official_game,
)

router = APIRouter(prefix="/admin/official-games", tags=["admin_official_games"])
VALID_GAME_STATUS_FILTERS = {
    "scheduled",
    "full",
    "cancelled",
    "completed",
    "abandoned",
}


@router.get("", response_model=AdminOfficialGameListRead)
def list_admin_official_games(
    game_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_READ)
    ),
) -> AdminOfficialGameListRead:
    del current_admin
    if game_status is not None and game_status not in VALID_GAME_STATUS_FILTERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "game_status must be 'scheduled', 'full', 'cancelled', "
                "'completed', or 'abandoned'."
            ),
        )

    games = list_official_games(db, game_status=game_status, limit=limit)
    return AdminOfficialGameListRead(games=games)


@router.post(
    "",
    response_model=AdminOfficialGameRead,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_official_game(
    create_request: AdminOfficialGameCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_WRITE)
    ),
) -> AdminOfficialGameRead:
    game = create_official_game(
        db,
        admin_user=current_admin,
        create_request=create_request,
    )
    return AdminOfficialGameRead(game=game)


@router.get("/{game_id}", response_model=AdminOfficialGameRead)
def get_admin_official_game(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_READ)
    ),
) -> AdminOfficialGameRead:
    del current_admin
    game = get_official_game_or_404(db, game_id)
    return AdminOfficialGameRead(game=game)


@router.get(
    "/{game_id}/participants",
    response_model=list[GameParticipantRead],
)
def list_admin_official_game_participants(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_READ)
    ),
) -> list[GameParticipant]:
    del current_admin
    get_official_game_or_404(db, game_id)
    participants = db.scalars(
        select(GameParticipant)
        .where(GameParticipant.game_id == game_id)
        .order_by(
            GameParticipant.roster_order.asc().nulls_last(),
            GameParticipant.created_at.asc(),
        )
    ).all()
    return list(participants)


@router.get(
    "/{game_id}/bookings",
    response_model=list[BookingRead],
)
def list_admin_official_game_bookings(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_READ)
    ),
) -> list[Booking]:
    del current_admin
    return list_official_game_bookings(db, game_id)


@router.get(
    "/{game_id}/waitlist",
    response_model=list[CurrentUserWaitlistEntryRead],
)
def list_admin_official_game_waitlist(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_READ)
    ),
) -> list[WaitlistEntry]:
    del current_admin
    return list_official_game_waitlist_entries(db, game_id)


@router.patch("/{game_id}", response_model=AdminOfficialGameRead)
def update_admin_official_game(
    game_id: uuid.UUID,
    update_request: AdminOfficialGameUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_WRITE)
    ),
) -> AdminOfficialGameRead:
    game = update_official_game(
        db,
        admin_user=current_admin,
        game_id=game_id,
        update_request=update_request,
    )
    return AdminOfficialGameRead(game=game)


@router.post("/{game_id}/host", response_model=AdminOfficialGameRead)
def assign_admin_official_game_host(
    game_id: uuid.UUID,
    host_request: AdminOfficialGameHostAssign,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE)
    ),
) -> AdminOfficialGameRead:
    game = assign_official_game_host(
        db,
        admin_user=current_admin,
        game_id=game_id,
        host_request=host_request,
    )
    return AdminOfficialGameRead(game=game)


@router.post(
    "/{game_id}/players",
    response_model=GameParticipantRead,
    status_code=status.HTTP_201_CREATED,
)
def add_admin_official_game_player(
    game_id: uuid.UUID,
    add_request: AdminOfficialGamePlayerAdd,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE)
    ),
) -> GameParticipantRead:
    participant = add_official_game_player(
        db,
        admin_user=current_admin,
        game_id=game_id,
        add_request=add_request,
    )
    return participant


@router.delete(
    "/{game_id}/participants/{participant_id}",
    response_model=GameParticipantRead,
)
def remove_admin_official_game_player(
    game_id: uuid.UUID,
    participant_id: uuid.UUID,
    remove_request: AdminOfficialGamePlayerRemove | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE)
    ),
) -> GameParticipantRead:
    participant = remove_official_game_player(
        db,
        admin_user=current_admin,
        game_id=game_id,
        participant_id=participant_id,
        remove_request=remove_request or AdminOfficialGamePlayerRemove(),
    )
    return participant


@router.delete("/{game_id}/host", response_model=AdminOfficialGameRead)
def remove_admin_official_game_host(
    game_id: uuid.UUID,
    remove_request: AdminOfficialGameHostRemove | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE)
    ),
) -> AdminOfficialGameRead:
    game = remove_official_game_host(
        db,
        admin_user=current_admin,
        game_id=game_id,
        remove_request=remove_request or AdminOfficialGameHostRemove(),
    )
    return AdminOfficialGameRead(game=game)
