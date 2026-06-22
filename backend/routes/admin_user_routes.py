import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    AdminUserDeleteCreate,
    AdminUserDeleteImpactPreviewRead,
    AdminUserDeleteResultRead,
    AdminUserDetailRead,
    AdminUserHostingRestrictionPreviewRead,
    AdminUserListRead,
    AdminUserRestrictHostingCreate,
    AdminUserRestrictHostingResultRead,
    AdminUserRestoreHostingCreate,
    AdminUserRestoreHostingResultRead,
    AdminUserStaffRead,
    AdminUserStaffRoleChangeCreate,
    AdminUserStaffRoleChangeResultRead,
    AdminUserSuspendCreate,
    AdminUserSuspendResultRead,
    AdminUserSuspensionPreviewRead,
    AdminUserUnsuspendCreate,
    AdminUserUnsuspendResultRead,
)
from backend.services.admin_permission_service import (
    PERMISSION_STAFF_MANAGE,
    PERMISSION_USERS_DELETE,
    PERMISSION_USERS_HOSTING_MANAGE,
    PERMISSION_USERS_READ,
    PERMISSION_USERS_SUSPEND,
)
from backend.services.admin_user_account_service import (
    preview_admin_user_suspension,
    suspend_admin_user,
    unsuspend_admin_user,
)
from backend.services.admin_user_delete_service import (
    delete_admin_user,
    preview_admin_user_delete_impact,
)
from backend.services.admin_user_service import (
    get_admin_user_detail,
    list_admin_staff_users,
    list_admin_users,
)
from backend.services.admin_user_hosting_service import (
    preview_admin_user_hosting_restriction,
    restrict_admin_user_hosting,
    restore_admin_user_hosting,
)
from backend.services.admin_user_staff_service import change_admin_user_staff_role
from backend.services.auth_service import require_admin_permission

router = APIRouter(prefix="/admin/users", tags=["admin_users"])


@router.get("", response_model=list[AdminUserListRead], status_code=status.HTTP_200_OK)
def list_admin_users_route(
    query: str | None = Query(default=None, max_length=120),
    account_status: str | None = None,
    hosting_status: str | None = None,
    role: str | None = None,
    include_deleted: bool = False,
    limit: int = Query(default=100, ge=1, le=200),
    current_admin: User = Depends(require_admin_permission(PERMISSION_USERS_READ)),
    db: Session = Depends(get_db),
) -> list[AdminUserListRead]:
    del current_admin
    return list_admin_users(
        db,
        query=query,
        account_status=account_status,
        hosting_status=hosting_status,
        role=role,
        include_deleted=include_deleted,
        limit=limit,
    )


@router.get(
    "/staff",
    response_model=list[AdminUserStaffRead],
    status_code=status.HTTP_200_OK,
)
def list_admin_staff_route(
    include_deleted: bool = False,
    limit: int = Query(default=100, ge=1, le=200),
    current_admin: User = Depends(require_admin_permission(PERMISSION_STAFF_MANAGE)),
    db: Session = Depends(get_db),
) -> list[AdminUserStaffRead]:
    del current_admin
    return list_admin_staff_users(
        db,
        include_deleted=include_deleted,
        limit=limit,
    )


@router.get(
    "/{user_id}",
    response_model=AdminUserDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_user_detail_route(
    user_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    current_admin: User = Depends(require_admin_permission(PERMISSION_USERS_READ)),
    db: Session = Depends(get_db),
) -> AdminUserDetailRead:
    return get_admin_user_detail(
        db,
        user_id=user_id,
        viewer_user=current_admin,
        limit=limit,
    )


@router.post(
    "/{user_id}/delete-preview",
    response_model=AdminUserDeleteImpactPreviewRead,
    status_code=status.HTTP_200_OK,
)
def preview_admin_user_delete_impact_route(
    user_id: uuid.UUID,
    current_admin: User = Depends(require_admin_permission(PERMISSION_USERS_DELETE)),
    db: Session = Depends(get_db),
) -> AdminUserDeleteImpactPreviewRead:
    del current_admin
    return preview_admin_user_delete_impact(db, user_id=user_id)


@router.post(
    "/{user_id}/delete",
    response_model=AdminUserDeleteResultRead,
    status_code=status.HTTP_200_OK,
)
def delete_admin_user_route(
    user_id: uuid.UUID,
    payload: AdminUserDeleteCreate,
    request: Request,
    current_admin: User = Depends(require_admin_permission(PERMISSION_USERS_DELETE)),
    db: Session = Depends(get_db),
) -> AdminUserDeleteResultRead:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None) or request.url.path
    return delete_admin_user(
        db,
        admin_user=current_admin,
        user_id=user_id,
        payload=payload,
        route_method=request.method,
        route_path=route_path,
    )


@router.post(
    "/{user_id}/staff-role",
    response_model=AdminUserStaffRoleChangeResultRead,
    status_code=status.HTTP_200_OK,
)
def change_admin_user_staff_role_route(
    user_id: uuid.UUID,
    payload: AdminUserStaffRoleChangeCreate,
    current_admin: User = Depends(require_admin_permission(PERMISSION_STAFF_MANAGE)),
    db: Session = Depends(get_db),
) -> AdminUserStaffRoleChangeResultRead:
    return change_admin_user_staff_role(
        db,
        admin_user=current_admin,
        user_id=user_id,
        payload=payload,
    )


@router.post(
    "/{user_id}/suspension-preview",
    response_model=AdminUserSuspensionPreviewRead,
    status_code=status.HTTP_200_OK,
)
def preview_admin_user_suspension_route(
    user_id: uuid.UUID,
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_USERS_SUSPEND)
    ),
    db: Session = Depends(get_db),
) -> AdminUserSuspensionPreviewRead:
    del current_admin
    return preview_admin_user_suspension(db, user_id=user_id)


@router.post(
    "/{user_id}/hosting-restriction-preview",
    response_model=AdminUserHostingRestrictionPreviewRead,
    status_code=status.HTTP_200_OK,
)
def preview_admin_user_hosting_restriction_route(
    user_id: uuid.UUID,
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_USERS_HOSTING_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> AdminUserHostingRestrictionPreviewRead:
    del current_admin
    return preview_admin_user_hosting_restriction(db, user_id=user_id)


@router.post(
    "/{user_id}/restrict-hosting",
    response_model=AdminUserRestrictHostingResultRead,
    status_code=status.HTTP_200_OK,
)
def restrict_admin_user_hosting_route(
    user_id: uuid.UUID,
    payload: AdminUserRestrictHostingCreate,
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_USERS_HOSTING_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> AdminUserRestrictHostingResultRead:
    return restrict_admin_user_hosting(
        db,
        admin_user=current_admin,
        user_id=user_id,
        payload=payload,
    )


@router.post(
    "/{user_id}/restore-hosting",
    response_model=AdminUserRestoreHostingResultRead,
    status_code=status.HTTP_200_OK,
)
def restore_admin_user_hosting_route(
    user_id: uuid.UUID,
    payload: AdminUserRestoreHostingCreate,
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_USERS_HOSTING_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> AdminUserRestoreHostingResultRead:
    return restore_admin_user_hosting(
        db,
        admin_user=current_admin,
        user_id=user_id,
        payload=payload,
    )


@router.post(
    "/{user_id}/suspend",
    response_model=AdminUserSuspendResultRead,
    status_code=status.HTTP_200_OK,
)
def suspend_admin_user_route(
    user_id: uuid.UUID,
    payload: AdminUserSuspendCreate,
    request: Request,
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_USERS_SUSPEND)
    ),
    db: Session = Depends(get_db),
) -> AdminUserSuspendResultRead:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None) or request.url.path
    return suspend_admin_user(
        db,
        admin_user=current_admin,
        user_id=user_id,
        payload=payload,
        route_method=request.method,
        route_path=route_path,
    )


@router.post(
    "/{user_id}/unsuspend",
    response_model=AdminUserUnsuspendResultRead,
    status_code=status.HTTP_200_OK,
)
def unsuspend_admin_user_route(
    user_id: uuid.UUID,
    payload: AdminUserUnsuspendCreate,
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_USERS_SUSPEND)
    ),
    db: Session = Depends(get_db),
) -> AdminUserUnsuspendResultRead:
    return unsuspend_admin_user(
        db,
        admin_user=current_admin,
        user_id=user_id,
        payload=payload,
    )
