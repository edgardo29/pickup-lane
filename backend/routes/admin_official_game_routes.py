import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, User, WaitlistEntry
from backend.schemas import (
    AdminOfficialGameCancelExecute,
    AdminOfficialGameCancellationPreviewRead,
    AdminOfficialGameCancellationResultRead,
    AdminOfficialGameCreate,
    AdminOfficialGameHostAssign,
    AdminOfficialGameHostRemove,
    AdminOfficialGameListRead,
    AdminOfficialGameMoneyRead,
    AdminOfficialGameParticipantRead,
    AdminOfficialGamePlayerAdd,
    AdminOfficialGamePlayerRemovalExecute,
    AdminOfficialGamePlayerRemove,
    AdminOfficialGamePlayerRemovalPreviewRead,
    AdminOfficialGamePlayerRemovalResultRead,
    AdminOfficialGameRead,
    AdminOfficialGameUpdate,
    AdminOfficialGameUserSearchRead,
    AdminChatMessageListRead,
    AdminChatModerationActionCreate,
    AdminChatModerationActionResultRead,
    AdminChatSummaryRead,
    BookingRead,
    CurrentUserWaitlistEntryRead,
    GameParticipantRead,
)
from backend.services.auth_service import require_active_admin
from backend.services.game_cancellation_service import (
    build_official_game_cancellation_preview as preview_official_game_cancellation,
    execute_official_game_cancellation,
)
from backend.services.official_game_player_removal_service import (
    execute_official_game_player_removal,
    preview_official_game_player_removal,
)
from backend.services.official_game_query_service import (
    get_official_game_money,
    list_official_game_bookings,
    list_official_game_participants,
    list_official_game_waitlist_entries,
    list_official_games,
)
from backend.services.official_game_roster_service import (
    add_official_game_player,
    assign_official_game_host,
    remove_official_game_host,
    remove_official_game_player,
    search_official_game_add_player_users,
)
from backend.services.official_game_service import (
    create_official_game,
    get_official_game_or_404,
    update_official_game,
)
from backend.services.chat_moderation_admin_service import (
    get_admin_game_chat_summary,
    list_admin_game_chat_messages,
    mark_game_chat_message_reviewed,
    remove_game_chat_message,
    restore_game_chat_message,
)

router = APIRouter(prefix="/admin/official-games", tags=["admin_official_games"])


@router.get("", response_model=AdminOfficialGameListRead)
def list_admin_official_games(
    view: str = Query(default="active"),
    search: str | None = Query(default=None, max_length=120),
    starts_on: date | None = Query(default=None),
    limit: int = Query(default=24, ge=1),
    cursor: str | None = Query(default=None, max_length=2000),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminOfficialGameListRead:
    del current_admin
    return list_official_games(
        db,
        view=view,
        search=search,
        starts_on=starts_on,
        limit=limit,
        cursor=cursor,
    )


@router.post(
    "",
    response_model=AdminOfficialGameRead,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_official_game(
    create_request: AdminOfficialGameCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
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
    current_admin: User = Depends(require_active_admin),
) -> AdminOfficialGameRead:
    del current_admin
    game = get_official_game_or_404(db, game_id)
    return AdminOfficialGameRead(game=game)


@router.get("/{game_id}/chat/summary", response_model=AdminChatSummaryRead)
def get_admin_official_game_chat_summary_route(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminChatSummaryRead:
    get_official_game_or_404(db, game_id)
    return get_admin_game_chat_summary(
        db,
        game_id=game_id,
        viewer_user=current_admin,
    )


@router.get("/{game_id}/chat/messages", response_model=AdminChatMessageListRead)
def list_admin_official_game_chat_messages_route(
    game_id: uuid.UUID,
    view: str = Query(default="needs_review"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=20),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminChatMessageListRead:
    get_official_game_or_404(db, game_id)
    return list_admin_game_chat_messages(
        db,
        game_id=game_id,
        viewer_user=current_admin,
        view=view,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/{game_id}/chat/messages/{message_id}/review",
    response_model=AdminChatModerationActionResultRead,
    status_code=status.HTTP_200_OK,
)
def mark_admin_official_game_chat_message_reviewed_route(
    game_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: AdminChatModerationActionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminChatModerationActionResultRead:
    get_official_game_or_404(db, game_id)
    return mark_game_chat_message_reviewed(
        db,
        game_id=game_id,
        message_id=message_id,
        admin_user=current_admin,
        payload=payload,
    )


@router.post(
    "/{game_id}/chat/messages/{message_id}/remove",
    response_model=AdminChatModerationActionResultRead,
    status_code=status.HTTP_200_OK,
)
def remove_admin_official_game_chat_message_route(
    game_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: AdminChatModerationActionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminChatModerationActionResultRead:
    get_official_game_or_404(db, game_id)
    return remove_game_chat_message(
        db,
        game_id=game_id,
        message_id=message_id,
        admin_user=current_admin,
        payload=payload,
    )


@router.post(
    "/{game_id}/chat/messages/{message_id}/restore",
    response_model=AdminChatModerationActionResultRead,
    status_code=status.HTTP_200_OK,
)
def restore_admin_official_game_chat_message_route(
    game_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: AdminChatModerationActionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminChatModerationActionResultRead:
    get_official_game_or_404(db, game_id)
    return restore_game_chat_message(
        db,
        game_id=game_id,
        message_id=message_id,
        admin_user=current_admin,
        payload=payload,
    )


@router.get(
    "/{game_id}/participants",
    response_model=list[AdminOfficialGameParticipantRead],
)
def list_admin_official_game_participants(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> list[AdminOfficialGameParticipantRead]:
    del current_admin
    participants = list_official_game_participants(db, game_id)
    user_ids = {
        participant.user_id
        for participant in participants
        if participant.user_id is not None
    }
    emails_by_user_id = {}
    if user_ids:
        emails_by_user_id = dict(
            db.execute(select(User.id, User.email).where(User.id.in_(user_ids))).all()
        )

    return [
        AdminOfficialGameParticipantRead.model_validate(participant).model_copy(
            update={
                "user_email": participant.guest_email
                or emails_by_user_id.get(participant.user_id),
            }
        )
        for participant in participants
    ]


@router.get(
    "/{game_id}/bookings",
    response_model=list[BookingRead],
)
def list_admin_official_game_bookings(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
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
    current_admin: User = Depends(require_active_admin),
) -> list[WaitlistEntry]:
    del current_admin
    return list_official_game_waitlist_entries(db, game_id)


@router.get(
    "/{game_id}/money",
    response_model=AdminOfficialGameMoneyRead,
)
def get_admin_official_game_money(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminOfficialGameMoneyRead:
    del current_admin
    return get_official_game_money(db, game_id)


@router.get(
    "/{game_id}/user-search",
    response_model=AdminOfficialGameUserSearchRead,
)
def search_admin_official_game_add_player_users(
    game_id: uuid.UUID,
    q: str = Query(..., min_length=3, max_length=100),
    limit: int = Query(default=10, ge=1, le=25),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminOfficialGameUserSearchRead:
    del current_admin
    return search_official_game_add_player_users(
        db,
        game_id=game_id,
        query=q,
        limit=limit,
    )


@router.patch("/{game_id}", response_model=AdminOfficialGameRead)
def update_admin_official_game(
    game_id: uuid.UUID,
    update_request: AdminOfficialGameUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminOfficialGameRead:
    game = update_official_game(
        db,
        admin_user=current_admin,
        game_id=game_id,
        update_request=update_request,
    )
    return AdminOfficialGameRead(game=game)


@router.post(
    "/{game_id}/cancel-preview",
    response_model=AdminOfficialGameCancellationPreviewRead,
)
def preview_admin_official_game_cancellation(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminOfficialGameCancellationPreviewRead:
    return preview_official_game_cancellation(
        db,
        game_id=game_id,
        admin_user=current_admin,
    )


@router.post(
    "/{game_id}/cancel",
    response_model=AdminOfficialGameCancellationResultRead,
)
def execute_admin_official_game_cancellation(
    game_id: uuid.UUID,
    cancel_request: AdminOfficialGameCancelExecute,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminOfficialGameCancellationResultRead:
    return execute_official_game_cancellation(
        db,
        game_id=game_id,
        admin_user=current_admin,
        cancel_request=cancel_request,
    )


@router.post("/{game_id}/host", response_model=AdminOfficialGameRead)
def assign_admin_official_game_host(
    game_id: uuid.UUID,
    host_request: AdminOfficialGameHostAssign,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
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
    current_admin: User = Depends(require_active_admin),
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
    current_admin: User = Depends(require_active_admin),
) -> GameParticipantRead:
    participant = remove_official_game_player(
        db,
        admin_user=current_admin,
        game_id=game_id,
        participant_id=participant_id,
        remove_request=remove_request or AdminOfficialGamePlayerRemove(),
    )
    return participant


@router.post(
    "/{game_id}/participants/{participant_id}/remove-preview",
    response_model=AdminOfficialGamePlayerRemovalPreviewRead,
)
def preview_admin_official_game_player_removal(
    game_id: uuid.UUID,
    participant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminOfficialGamePlayerRemovalPreviewRead:
    del current_admin
    return preview_official_game_player_removal(
        db,
        game_id=game_id,
        participant_id=participant_id,
    )


@router.post(
    "/{game_id}/participants/{participant_id}/remove",
    response_model=AdminOfficialGamePlayerRemovalResultRead,
)
def execute_admin_official_game_player_removal(
    game_id: uuid.UUID,
    participant_id: uuid.UUID,
    execute_request: AdminOfficialGamePlayerRemovalExecute,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminOfficialGamePlayerRemovalResultRead:
    return execute_official_game_player_removal(
        db,
        admin_user=current_admin,
        game_id=game_id,
        participant_id=participant_id,
        execute_request=execute_request,
    )


@router.delete("/{game_id}/host", response_model=AdminOfficialGameRead)
def remove_admin_official_game_host(
    game_id: uuid.UUID,
    remove_request: AdminOfficialGameHostRemove | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminOfficialGameRead:
    game = remove_official_game_host(
        db,
        admin_user=current_admin,
        game_id=game_id,
        remove_request=remove_request or AdminOfficialGameHostRemove(),
    )
    return AdminOfficialGameRead(game=game)
