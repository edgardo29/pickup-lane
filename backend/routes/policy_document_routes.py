import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import PolicyDocument
from backend.schemas import (
    PolicyDocumentCreate,
    PolicyDocumentRead,
    PolicyDocumentUpdate,
)

router = APIRouter(prefix="/policy-documents", tags=["policy_documents"])

VALID_POLICY_TYPES = {
    "terms_of_service",
    "privacy_policy",
    "refund_policy",
    "player_cancellation_policy",
    "community_host_agreement",
    "official_game_rules",
}


def build_policy_document_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_policy_documents_policy_type_version" in error_text:
        return "This policy type and version already exists."

    if "ck_policy_documents_policy_type" in error_text:
        return "policy_type is not supported."

    if "ck_policy_documents_version_not_empty" in error_text:
        return "version must not be empty."

    if "ck_policy_documents_title_not_empty" in error_text:
        return "title must not be empty."

    if "ck_policy_documents_content_required" in error_text:
        return "At least one of content_url or content_text must be provided."

    if "ck_policy_documents_retired_after_effective" in error_text:
        return "retired_at must be greater than effective_at."

    return error_text


def validate_policy_document_business_rules(policy_data: dict[str, Any]) -> None:
    for field_name in ("policy_type", "version", "title", "effective_at", "is_active"):
        if policy_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if policy_data["policy_type"] not in VALID_POLICY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="policy_type is not supported.",
        )

    if not policy_data["version"].strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="version must not be empty.",
        )

    if not policy_data["title"].strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title must not be empty.",
        )

    has_content_url = (
        policy_data["content_url"] is not None
        and bool(policy_data["content_url"].strip())
    )
    has_content_text = (
        policy_data["content_text"] is not None
        and bool(policy_data["content_text"].strip())
    )

    if not has_content_url and not has_content_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of content_url or content_text must be provided.",
        )

    if (
        policy_data["retired_at"] is not None
        and policy_data["retired_at"] <= policy_data["effective_at"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="retired_at must be greater than effective_at.",
        )


def validate_policy_document_update_rules(update_data: dict[str, Any]) -> None:
    for field_name in ("policy_type", "version", "title", "effective_at", "is_active"):
        if field_name in update_data and update_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )


# This route creates one versioned legal/policy document for the app.
@router.post("", response_model=PolicyDocumentRead, status_code=status.HTTP_201_CREATED)
def create_policy_document(
    policy_document: PolicyDocumentCreate,
    db: Session = Depends(get_db),
) -> PolicyDocument:
    policy_data = policy_document.model_dump()
    validate_policy_document_business_rules(policy_data)

    new_policy_document = PolicyDocument(
        id=uuid.uuid4(),
        **policy_data,
    )

    try:
        db.add(new_policy_document)
        db.commit()
        db.refresh(new_policy_document)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_policy_document_conflict_detail(exc),
        ) from exc

    return new_policy_document


# This route fetches a single policy document by its internal UUID.
@router.get(
    "/{policy_document_id}",
    response_model=PolicyDocumentRead,
    status_code=status.HTTP_200_OK,
)
def get_policy_document(
    policy_document_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> PolicyDocument:
    db_policy_document = db.get(PolicyDocument, policy_document_id)

    if db_policy_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy document not found.",
        )

    return db_policy_document


# This route returns policy documents currently stored in the app database.
@router.get("", response_model=list[PolicyDocumentRead], status_code=status.HTTP_200_OK)
def list_policy_documents(
    policy_type: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
) -> list[PolicyDocument]:
    statement = select(PolicyDocument)

    if policy_type is not None:
        if policy_type not in VALID_POLICY_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="policy_type is not supported.",
            )
        statement = statement.where(PolicyDocument.policy_type == policy_type)

    if is_active is not None:
        statement = statement.where(PolicyDocument.is_active == is_active)

    policy_documents = db.scalars(
        statement.order_by(PolicyDocument.effective_at.desc())
    ).all()
    return list(policy_documents)


# This route applies partial corrections or lifecycle updates to a policy document.
@router.patch(
    "/{policy_document_id}",
    response_model=PolicyDocumentRead,
    status_code=status.HTTP_200_OK,
)
def update_policy_document(
    policy_document_id: uuid.UUID,
    policy_document_update: PolicyDocumentUpdate,
    db: Session = Depends(get_db),
) -> PolicyDocument:
    db_policy_document = db.get(PolicyDocument, policy_document_id)

    if db_policy_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy document not found.",
        )

    update_data = policy_document_update.model_dump(exclude_unset=True)
    validate_policy_document_update_rules(update_data)

    effective_policy_data = {
        "policy_type": update_data.get("policy_type", db_policy_document.policy_type),
        "version": update_data.get("version", db_policy_document.version),
        "title": update_data.get("title", db_policy_document.title),
        "content_url": update_data.get("content_url", db_policy_document.content_url),
        "content_text": update_data.get("content_text", db_policy_document.content_text),
        "effective_at": update_data.get("effective_at", db_policy_document.effective_at),
        "retired_at": update_data.get("retired_at", db_policy_document.retired_at),
        "is_active": update_data.get("is_active", db_policy_document.is_active),
    }
    validate_policy_document_business_rules(effective_policy_data)

    for field_name, field_value in update_data.items():
        setattr(db_policy_document, field_name, field_value)

    db_policy_document.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_policy_document)
        db.commit()
        db.refresh(db_policy_document)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_policy_document_conflict_detail(exc),
        ) from exc

    return db_policy_document
