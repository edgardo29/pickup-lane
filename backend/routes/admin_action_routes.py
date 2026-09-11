import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import (
    AdminActionDetailRead,
    AdminActionLogListRead,
)
from backend.services.admin_action_display_service import (
    list_admin_action_log,
    serialize_admin_action_detail_read,
)
from backend.services.admin_action_service import (
    get_admin_action_for_viewer_or_404,
)
from backend.services.auth_service import require_active_admin

router = APIRouter(prefix="/admin/actions", tags=["admin_actions"])
ADMIN_ACTION_LOG_QUERY_PARAMS = {
    "admin_user_id",
    "action_type",
    "target_game_id",
    "cursor",
}


def reject_unsupported_log_params(request: Request) -> None:
    unsupported_params = sorted(
        set(request.query_params.keys()) - ADMIN_ACTION_LOG_QUERY_PARAMS
    )
    if unsupported_params:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "admin_action_log_unsupported_query_param",
                "message": "Admin Action Log only supports its documented filters.",
                "params": unsupported_params,
            },
        )


@router.post("", status_code=status.HTTP_410_GONE)
def create_admin_action_route(
    current_user: User = Depends(require_active_admin),
) -> None:
    del current_user
    raise_retired_mutation_route(
        code="admin_action_scaffold_removed",
        message=(
            "Direct admin action creation is no longer supported. Audit actions "
            "are recorded by product-owned admin workflows."
        ),
    )


@router.get(
    "/log",
    response_model=AdminActionLogListRead,
    status_code=status.HTTP_200_OK,
)
def list_admin_action_log_route(
    request: Request,
    admin_user_id: uuid.UUID | None = None,
    action_type: str | None = Query(default=None, max_length=60),
    target_game_id: uuid.UUID | None = None,
    cursor: str | None = None,
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminActionLogListRead:
    reject_unsupported_log_params(request)
    return list_admin_action_log(
        db,
        viewer_user=current_user,
        admin_user_id=admin_user_id,
        action_type=action_type,
        target_game_id=target_game_id,
        cursor=cursor,
    )


@router.get(
    "/{admin_action_id}",
    response_model=AdminActionDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_action_route(
    admin_action_id: uuid.UUID,
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminActionDetailRead:
    admin_action = get_admin_action_for_viewer_or_404(
        db,
        admin_action_id,
        current_user,
    )
    return serialize_admin_action_detail_read(
        db,
        admin_action,
        viewer_user=current_user,
    )


@router.post(
    "/{admin_action_id}/notes",
    status_code=status.HTTP_410_GONE,
)
def append_admin_action_note_route(
    admin_action_id: uuid.UUID,
    current_user: User = Depends(require_active_admin),
) -> None:
    del admin_action_id, current_user
    raise_retired_mutation_route(
        code="admin_action_note_scaffold_removed",
        message=(
            "Direct admin action notes are no longer supported. Admin action "
            "history is recorded by product-owned workflows."
        ),
    )
