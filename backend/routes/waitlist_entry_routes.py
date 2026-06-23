import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, WaitlistEntry
from backend.schemas import (
    CurrentUserWaitlistEntryRead,
    WaitlistEntryCreate,
    WaitlistEntryRead,
    WaitlistEntryUpdate,
)
from backend.services.admin_permission_service import (
    PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
)
from backend.services.auth_service import (
    get_current_app_user,
    require_admin_permission,
)
from backend.services.waitlist_entry_service import (
    create_waitlist_entry_workflow,
    get_waitlist_entry_for_user_or_404,
    list_current_user_waitlist_entries,
    list_waitlist_entries as list_waitlist_entries_workflow,
    update_waitlist_entry_workflow,
)

router = APIRouter(prefix="/waitlist-entries", tags=["waitlist_entries"])


# Admin-only endpoint for protected waitlist entry creation.
@router.post("", response_model=WaitlistEntryRead, status_code=status.HTTP_201_CREATED)
def create_waitlist_entry(
    waitlist_entry: WaitlistEntryCreate,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE)
    ),
) -> WaitlistEntry:
    return create_waitlist_entry_workflow(db, waitlist_entry)


@router.get(
    "/me",
    response_model=list[CurrentUserWaitlistEntryRead],
    status_code=status.HTTP_200_OK,
)
def list_my_waitlist_entries(
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> list[WaitlistEntry]:
    return list_current_user_waitlist_entries(db, current_user)


# Fetches a single waitlist entry visible to the current user or roster admins.
@router.get(
    "/{waitlist_entry_id}",
    response_model=WaitlistEntryRead,
    status_code=status.HTTP_200_OK,
)
def get_waitlist_entry(
    waitlist_entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> WaitlistEntry:
    return get_waitlist_entry_for_user_or_404(db, waitlist_entry_id, current_user)


# Admin-only endpoint for waitlist entry queries.
@router.get("", response_model=list[WaitlistEntryRead], status_code=status.HTTP_200_OK)
def list_waitlist_entries(
    game_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    waitlist_status: str | None = None,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE)
    ),
) -> list[WaitlistEntry]:
    return list_waitlist_entries_workflow(
        db,
        game_id=game_id,
        user_id=user_id,
        waitlist_status=waitlist_status,
    )


# Admin-only endpoint for protected waitlist entry updates.
@router.patch(
    "/{waitlist_entry_id}",
    response_model=WaitlistEntryRead,
    status_code=status.HTTP_200_OK,
)
def update_waitlist_entry(
    waitlist_entry_id: uuid.UUID,
    waitlist_entry_update: WaitlistEntryUpdate,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE)
    ),
) -> WaitlistEntry:
    return update_waitlist_entry_workflow(db, waitlist_entry_id, waitlist_entry_update)
