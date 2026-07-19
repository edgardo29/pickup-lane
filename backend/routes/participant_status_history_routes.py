import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ParticipantStatusHistory, User
from backend.schemas import (
    ParticipantStatusHistoryCreate,
    ParticipantStatusHistoryRead,
    ParticipantStatusHistoryUpdate,
)
from backend.services.auth_service import require_active_admin
from backend.services.status_history_service import (
    create_participant_status_history_record,
    get_participant_status_history_record,
    list_participant_status_history_records,
    update_participant_status_history_record,
)

router = APIRouter(
    prefix="/participant-status-history",
    tags=["participant_status_history"],
)


@router.post(
    "",
    response_model=ParticipantStatusHistoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_participant_status_history(
    participant_status_history: ParticipantStatusHistoryCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> ParticipantStatusHistory:
    del current_admin
    return create_participant_status_history_record(db, participant_status_history)


@router.get(
    "/{history_id}",
    response_model=ParticipantStatusHistoryRead,
    status_code=status.HTTP_200_OK,
)
def get_participant_status_history(
    history_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> ParticipantStatusHistory:
    del current_admin
    return get_participant_status_history_record(db, history_id)


@router.get(
    "",
    response_model=list[ParticipantStatusHistoryRead],
    status_code=status.HTTP_200_OK,
)
def list_participant_status_history(
    participant_id: uuid.UUID | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> list[ParticipantStatusHistory]:
    del current_admin
    return list_participant_status_history_records(
        db,
        participant_id=participant_id,
        changed_by_user_id=changed_by_user_id,
        change_source=change_source,
    )


@router.patch(
    "/{history_id}",
    response_model=ParticipantStatusHistoryRead,
    status_code=status.HTTP_200_OK,
)
def update_participant_status_history(
    history_id: uuid.UUID,
    history_update: ParticipantStatusHistoryUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> ParticipantStatusHistory:
    del current_admin
    return update_participant_status_history_record(
        db,
        history_id,
        history_update,
    )
