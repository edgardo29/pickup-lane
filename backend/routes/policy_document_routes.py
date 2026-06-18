import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import PolicyDocument, User
from backend.schemas import (
    PolicyDocumentCreate,
    PolicyDocumentRead,
    PolicyDocumentUpdate,
)
from backend.services.admin_permission_service import PERMISSION_POLICIES_MANAGE
from backend.services.auth_service import require_admin_permission
from backend.services.policy_document_service import (
    create_policy_document_record,
    get_public_policy_document_record,
    list_public_policy_document_records,
    update_policy_document_record,
)

router = APIRouter(prefix="/policy-documents", tags=["policy_documents"])


@router.post("", response_model=PolicyDocumentRead, status_code=status.HTTP_201_CREATED)
def create_policy_document(
    policy_document: PolicyDocumentCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_POLICIES_MANAGE)
    ),
) -> PolicyDocument:
    del current_admin
    return create_policy_document_record(db, policy_document)


@router.get(
    "/{policy_document_id}",
    response_model=PolicyDocumentRead,
    status_code=status.HTTP_200_OK,
)
def get_policy_document(
    policy_document_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> PolicyDocument:
    return get_public_policy_document_record(db, policy_document_id)


@router.get("", response_model=list[PolicyDocumentRead], status_code=status.HTTP_200_OK)
def list_policy_documents(
    policy_type: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
) -> list[PolicyDocument]:
    return list_public_policy_document_records(
        db,
        policy_type=policy_type,
        is_active=is_active,
    )


@router.patch(
    "/{policy_document_id}",
    response_model=PolicyDocumentRead,
    status_code=status.HTTP_200_OK,
)
def update_policy_document(
    policy_document_id: uuid.UUID,
    policy_document_update: PolicyDocumentUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_POLICIES_MANAGE)
    ),
) -> PolicyDocument:
    del current_admin
    return update_policy_document_record(
        db,
        policy_document_id,
        policy_document_update,
    )
