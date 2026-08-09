import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import PolicyDocument, User
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import (
    PolicyDocumentRead,
)
from backend.services.auth_service import require_active_admin
from backend.services.policy_document_service import (
    get_public_policy_document_record,
    list_public_policy_document_records,
)

router = APIRouter(prefix="/policy-documents", tags=["policy_documents"])


@router.post("", status_code=status.HTTP_410_GONE)
def create_policy_document(
    current_admin: User = Depends(require_active_admin),
) -> None:
    del current_admin
    raise_retired_mutation_route(
        code="policy_document_generic_authoring_removed",
        message=(
            "Generic policy document authoring is retired. Policy and legal "
            "content is source-managed."
        ),
    )


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
    status_code=status.HTTP_410_GONE,
)
def update_policy_document(
    policy_document_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
) -> None:
    del policy_document_id, current_admin
    raise_retired_mutation_route(
        code="policy_document_generic_authoring_removed",
        message=(
            "Generic policy document updates are retired. Policy and legal "
            "content is source-managed."
        ),
    )
