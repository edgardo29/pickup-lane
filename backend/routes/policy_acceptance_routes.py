import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import PolicyAcceptance, User
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import (
    PolicyAcceptanceRead,
)
from backend.services.auth_service import require_active_admin
from backend.services.policy_acceptance_service import (
    get_policy_acceptance_record,
    list_policy_acceptance_records,
)

router = APIRouter(prefix="/policy-acceptances", tags=["policy_acceptances"])


@router.post(
    "",
    status_code=status.HTTP_410_GONE,
)
def create_policy_acceptance(
    current_admin: User = Depends(require_active_admin),
) -> None:
    del current_admin
    raise_retired_mutation_route(
        code="policy_acceptance_generic_mutation_removed",
        message=(
            "Generic policy acceptance creation is retired. Acceptance evidence "
            "must be recorded by a supported server-owned workflow."
        ),
    )


@router.get(
    "/{policy_acceptance_id}",
    response_model=PolicyAcceptanceRead,
    status_code=status.HTTP_200_OK,
)
def get_policy_acceptance(
    policy_acceptance_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
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
    current_admin: User = Depends(require_active_admin),
) -> list[PolicyAcceptance]:
    del current_admin
    return list_policy_acceptance_records(
        db,
        user_id=user_id,
        policy_document_id=policy_document_id,
    )


@router.patch(
    "/{policy_acceptance_id}",
    status_code=status.HTTP_410_GONE,
)
def update_policy_acceptance(
    policy_acceptance_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
) -> None:
    del policy_acceptance_id, current_admin
    raise_retired_mutation_route(
        code="policy_acceptance_generic_mutation_removed",
        message=(
            "Generic policy acceptance updates are retired. Acceptance evidence "
            "must remain owned by supported server-owned workflows."
        ),
    )
