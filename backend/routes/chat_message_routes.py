import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatMessage, User
from backend.schemas import ChatMessageCreate, ChatMessageRead
from backend.services.auth_service import require_active_user
from backend.services.game_chat_service import (
    create_chat_message_record,
    get_chat_message_record,
    list_chat_message_records,
)

router = APIRouter(prefix="/chat-messages", tags=["chat_messages"])


@router.post("", response_model=ChatMessageRead, status_code=status.HTTP_201_CREATED)
def create_chat_message(
    chat_message: ChatMessageCreate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> ChatMessage:
    return create_chat_message_record(db, chat_message, current_user)


@router.get(
    "/{chat_message_id}",
    response_model=ChatMessageRead,
    status_code=status.HTTP_200_OK,
)
def get_chat_message(
    chat_message_id: uuid.UUID,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> ChatMessage:
    return get_chat_message_record(db, chat_message_id, current_user)


@router.get("", response_model=list[ChatMessageRead], status_code=status.HTTP_200_OK)
def list_chat_messages(
    chat_id: uuid.UUID | None = None,
    sender_user_id: uuid.UUID | None = None,
    visibility_status: str | None = None,
    review_status: str | None = None,
    is_pinned: bool | None = None,
    after_created_at: datetime | None = None,
    limit: int = 50,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[ChatMessage]:
    return list_chat_message_records(
        db,
        current_user,
        chat_id=chat_id,
        sender_user_id=sender_user_id,
        visibility_status=visibility_status,
        review_status=review_status,
        is_pinned=is_pinned,
        after_created_at=after_created_at,
        limit=limit,
    )
