import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import PolicyAcceptance, PolicyDocument, User
from backend.schemas import (
    PolicyAcceptanceCreate,
    PolicyAcceptanceRead,
    PolicyAcceptanceUpdate,
)

router = APIRouter(prefix="/policy-acceptances", tags=["policy_acceptances"])


def build_policy_acceptance_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_policy_acceptances_user_id_policy_document_id" in error_text:
        return "This user has already accepted this policy document."

    return error_text


def get_active_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return db_user


def get_policy_document_or_404(
    db: Session,
    policy_document_id: uuid.UUID,
) -> PolicyDocument:
    db_policy_document = db.get(PolicyDocument, policy_document_id)

    if db_policy_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy document not found.",
        )

    return db_policy_document


def validate_policy_acceptance_business_rules(
    acceptance_data: dict[str, Any],
) -> None:
    for field_name in ("user_id", "policy_document_id", "accepted_at"):
        if acceptance_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )


def normalize_policy_acceptance_fields(
    acceptance_data: dict[str, Any],
) -> dict[str, Any]:
    normalized_data = dict(acceptance_data)

    if normalized_data["accepted_at"] is None:
        normalized_data["accepted_at"] = datetime.now(timezone.utc)

    return normalized_data


def validate_policy_acceptance_references(
    db: Session,
    acceptance_data: dict[str, Any],
) -> None:
    get_active_user_or_404(db, acceptance_data["user_id"])
    db_policy_document = get_policy_document_or_404(
        db,
        acceptance_data["policy_document_id"],
    )

    now = datetime.now(timezone.utc)
    if (
        not db_policy_document.is_active
        or db_policy_document.retired_at is not None
        or db_policy_document.effective_at > now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Policy acceptances require an active, non-retired policy "
                "document that is already effective."
            ),
        )


def validate_policy_acceptance_update_rules(update_data: dict[str, Any]) -> None:
    if "accepted_at" in update_data and update_data["accepted_at"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="accepted_at cannot be null.",
        )


# This route records that one user accepted one specific policy document version.
@router.post(
    "",
    response_model=PolicyAcceptanceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_policy_acceptance(
    policy_acceptance: PolicyAcceptanceCreate,
    db: Session = Depends(get_db),
) -> PolicyAcceptance:
    acceptance_data = normalize_policy_acceptance_fields(
        policy_acceptance.model_dump()
    )
    validate_policy_acceptance_business_rules(acceptance_data)
    validate_policy_acceptance_references(db, acceptance_data)

    new_policy_acceptance = PolicyAcceptance(
        id=uuid.uuid4(),
        **acceptance_data,
    )

    try:
        db.add(new_policy_acceptance)
        db.commit()
        db.refresh(new_policy_acceptance)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_policy_acceptance_conflict_detail(exc),
        ) from exc

    return new_policy_acceptance


# This route fetches a single policy acceptance row by its internal UUID.
@router.get(
    "/{policy_acceptance_id}",
    response_model=PolicyAcceptanceRead,
    status_code=status.HTTP_200_OK,
)
def get_policy_acceptance(
    policy_acceptance_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> PolicyAcceptance:
    db_policy_acceptance = db.get(PolicyAcceptance, policy_acceptance_id)

    if db_policy_acceptance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy acceptance not found.",
        )

    return db_policy_acceptance


# This route returns policy acceptance rows currently stored in the app database.
@router.get(
    "",
    response_model=list[PolicyAcceptanceRead],
    status_code=status.HTTP_200_OK,
)
def list_policy_acceptances(
    user_id: uuid.UUID | None = None,
    policy_document_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
) -> list[PolicyAcceptance]:
    statement = select(PolicyAcceptance)

    if user_id is not None:
        statement = statement.where(PolicyAcceptance.user_id == user_id)

    if policy_document_id is not None:
        statement = statement.where(
            PolicyAcceptance.policy_document_id == policy_document_id
        )

    policy_acceptances = db.scalars(
        statement.order_by(PolicyAcceptance.accepted_at.desc())
    ).all()
    return list(policy_acceptances)


# This route allows correcting acceptance metadata without changing the accepted
# user or policy document.
@router.patch(
    "/{policy_acceptance_id}",
    response_model=PolicyAcceptanceRead,
    status_code=status.HTTP_200_OK,
)
def update_policy_acceptance(
    policy_acceptance_id: uuid.UUID,
    policy_acceptance_update: PolicyAcceptanceUpdate,
    db: Session = Depends(get_db),
) -> PolicyAcceptance:
    db_policy_acceptance = db.get(PolicyAcceptance, policy_acceptance_id)

    if db_policy_acceptance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy acceptance not found.",
        )

    update_data = policy_acceptance_update.model_dump(exclude_unset=True)
    validate_policy_acceptance_update_rules(update_data)

    for field_name, field_value in update_data.items():
        setattr(db_policy_acceptance, field_name, field_value)

    try:
        db.add(db_policy_acceptance)
        db.commit()
        db.refresh(db_policy_acceptance)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_policy_acceptance_conflict_detail(exc),
        ) from exc

    return db_policy_acceptance
