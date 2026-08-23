import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, WaitlistEntry
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import (
    CurrentUserWaitlistEntryRead,
    WaitlistEntryRead,
)
from backend.services.auth_service import get_current_app_user, require_active_admin
from backend.services.waitlist_entry_service import (
    get_waitlist_entry_for_user_or_404,
    list_current_user_waitlist_entries,
    list_waitlist_entries as list_waitlist_entries_workflow,
)
from backend.services.query_pagination import (
    DEFAULT_ADMIN_COLLECTION_LIMIT,
    DEFAULT_COLLECTION_LIMIT,
    MAX_ADMIN_COLLECTION_LIMIT,
    MAX_COLLECTION_LIMIT,
)

router = APIRouter(prefix="/waitlist-entries", tags=["waitlist_entries"])


# Retired public/admin scaffold. Supported waitlist mutations are service-owned.
@router.post("", status_code=status.HTTP_410_GONE)
def create_waitlist_entry(
    _current_admin: User = Depends(require_active_admin),
) -> None:
    del _current_admin
    raise_retired_mutation_route(
        code="waitlist_entry_scaffold_removed",
        message=(
            "Direct waitlist-entry creation is no longer supported. Use "
            "product-owned waitlist workflows."
        ),
    )


@router.get(
    "/me",
    response_model=list[CurrentUserWaitlistEntryRead],
    status_code=status.HTTP_200_OK,
)
def list_my_waitlist_entries(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_COLLECTION_LIMIT, ge=1, le=MAX_COLLECTION_LIMIT),
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> list[WaitlistEntry]:
    return list_current_user_waitlist_entries(
        db,
        current_user,
        limit=limit,
        offset=offset,
    )


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
    offset: int = Query(default=0, ge=0),
    limit: int = Query(
        default=DEFAULT_ADMIN_COLLECTION_LIMIT,
        ge=1,
        le=MAX_ADMIN_COLLECTION_LIMIT,
    ),
    db: Session = Depends(get_db),
    _current_admin: User = Depends(require_active_admin),
) -> list[WaitlistEntry]:
    return list_waitlist_entries_workflow(
        db,
        game_id=game_id,
        user_id=user_id,
        waitlist_status=waitlist_status,
        limit=limit,
        offset=offset,
    )


# Retired public/admin scaffold. Supported waitlist mutations are service-owned.
@router.patch(
    "/{waitlist_entry_id}",
    status_code=status.HTTP_410_GONE,
)
def update_waitlist_entry(
    waitlist_entry_id: uuid.UUID,
    _current_admin: User = Depends(require_active_admin),
) -> None:
    del waitlist_entry_id, _current_admin
    raise_retired_mutation_route(
        code="waitlist_entry_scaffold_removed",
        message=(
            "Direct waitlist-entry updates are no longer supported. Use "
            "product-owned waitlist workflows."
        ),
    )
