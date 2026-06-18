import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import PolicyAcceptance, User
from backend.schemas import (
    PolicyAcceptanceCreate,
    PolicyAcceptanceRead,
    PolicyAcceptanceUpdate,
)
from backend.services.admin_permission_service import PERMISSION_POLICIES_MANAGE
from backend.services.auth_service import require_admin_permission
from backend.services.policy_acceptance_service import (
    create_policy_acceptance_record,
    get_policy_acceptance_record,
    list_policy_acceptance_records,
    update_policy_acceptance_record,
)

router = APIRouter(prefix="/policy-acceptances", tags=["policy_acceptances"])


@router.post(
    "",
    response_model=PolicyAcceptanceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_policy_acceptance(
    policy_acceptance: PolicyAcceptanceCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_POLICIES_MANAGE)
    ),
) -> PolicyAcceptance:
    del current_admin
    return create_policy_acceptance_record(db, policy_acceptance)


@router.get(
    "/{policy_acceptance_id}",
    response_model=PolicyAcceptanceRead,
    status_code=status.HTTP_200_OK,
)
def get_policy_acceptance(
    policy_acceptance_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_POLICIES_MANAGE)
    ),
) -> PolicyAcceptance:
    del current_admin
    return get_policy_acceptance_record(db, policy_acceptance_id)


@router.get(
    "",
    response_model=list[PolicyAcceptanceRead],
    status_code=status.HTTP_200_OK,
)
def list_policy_acceptances(
    user_id: uuid.UUID | None = None,
    policy_document_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_POLICIES_MANAGE)
    ),
) -> list[PolicyAcceptance]:
    del current_admin
    return list_policy_acceptance_records(
        db,
        user_id=user_id,
        policy_document_id=policy_document_id,
    )


@router.patch(
    "/{policy_acceptance_id}",
    response_model=PolicyAcceptanceRead,
    status_code=status.HTTP_200_OK,
)
def update_policy_acceptance(
    policy_acceptance_id: uuid.UUID,
    policy_acceptance_update: PolicyAcceptanceUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_POLICIES_MANAGE)
    ),
) -> PolicyAcceptance:
    del current_admin
    return update_policy_acceptance_record(
        db,
        policy_acceptance_id,
        policy_acceptance_update,
    )
