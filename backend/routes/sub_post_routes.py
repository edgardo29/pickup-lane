import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import SubPostChatMessage, User
from backend.routes.auth_routes import get_current_app_user, get_optional_current_app_user
from backend.schemas import (
    SubPostCancel,
    SubPostChatEnsureCreate,
    SubPostChatMessageCreate,
    SubPostChatMessageRead,
    SubPostChatMessageUpdate,
    SubPostChatRead,
    SubPostChatReadStateRead,
    SubPostCreate,
    SubPostPublicRead,
    SubPostRead,
    SubPostRemove,
    SubPostUpdate,
)
from backend.services.need_a_sub_service import (
    cancel_sub_post,
    create_sub_post,
    expire_due_posts_and_requests,
    get_sub_post_or_404,
    is_publicly_visible_sub_post,
    query_owner_posts,
    query_visible_posts,
    remove_sub_post,
    serialize_public_sub_post,
    serialize_sub_post,
    update_sub_post,
    user_can_view_private_sub_post,
)
from backend.services.sub_post_chat_service import (
    build_sender_snapshot,
    create_or_update_sub_chat_notifications,
    get_latest_visible_sub_chat_messages,
    get_or_create_active_sub_post_chat,
    get_sub_chat_read_state,
    get_sub_post_chat_for_post,
    mark_sub_chat_read,
    normalize_message_body,
    require_sub_post_chat_can_write,
    require_sub_post_chat_member,
    serialize_sub_chat_message,
    validate_sender_rate_limit,
    validate_sub_post_chat_access,
    validate_total_message_limit,
)

router = APIRouter(prefix="/need-a-sub/posts", tags=["need_a_sub_posts"])


def serialize_sub_post_chat(
    db_chat,
    unread_count: int = 0,
    last_read_at: datetime | None = None,
) -> SubPostChatRead:
    return SubPostChatRead(
        id=db_chat.id,
        sub_post_id=db_chat.sub_post_id,
        chat_status=db_chat.chat_status,
        created_at=db_chat.created_at,
        updated_at=db_chat.updated_at,
        closed_at=db_chat.closed_at,
        unread_count=unread_count,
        last_read_at=last_read_at,
    )


def validate_optional_acting_user(
    acting_user_id: uuid.UUID | None,
    current_user: User,
) -> None:
    if acting_user_id is not None and acting_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="acting_user_id must match the authenticated user.",
        )


@router.post("", response_model=SubPostRead, status_code=status.HTTP_201_CREATED)
def create_need_a_sub_post(
    sub_post: SubPostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> dict:
    new_post = create_sub_post(db, current_user, sub_post)
    return serialize_sub_post(db, new_post)


@router.get("", response_model=list[SubPostPublicRead], status_code=status.HTTP_200_OK)
def list_need_a_sub_posts(
    city: str | None = None,
    state: str | None = Query(default=None),
    starts_after: datetime | None = None,
    starts_before: datetime | None = None,
    skill_level: str | None = None,
    game_player_group: str | None = None,
    format_label: str | None = None,
    environment_type: str | None = None,
    sport_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    expire_due_posts_and_requests(db)
    posts = query_visible_posts(
        db,
        city=city,
        state_value=state,
        starts_after=starts_after,
        starts_before=starts_before,
        skill_level=skill_level,
        game_player_group=game_player_group,
        format_label=format_label,
        environment_type=environment_type,
        sport_type=sport_type,
    )
    return [serialize_public_sub_post(db, sub_post) for sub_post in posts]


@router.get("/mine", response_model=list[SubPostRead], status_code=status.HTTP_200_OK)
def list_my_need_a_sub_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> list[dict]:
    expire_due_posts_and_requests(db)
    posts = query_owner_posts(db, current_user)
    return [serialize_sub_post(db, sub_post) for sub_post in posts]


@router.post(
    "/{sub_post_id}/chat",
    response_model=SubPostChatRead,
    status_code=status.HTTP_200_OK,
)
def ensure_need_a_sub_chat(
    sub_post_id: uuid.UUID,
    payload: SubPostChatEnsureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> SubPostChatRead:
    validate_optional_acting_user(payload.acting_user_id, current_user)
    sub_post = get_sub_post_or_404(db, sub_post_id)
    validate_sub_post_chat_access(db, sub_post, current_user)
    db_chat = get_or_create_active_sub_post_chat(db, sub_post)

    try:
        db.commit()
        db.refresh(db_chat)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc

    read_state, unread_count = get_sub_chat_read_state(db, db_chat, current_user)
    return serialize_sub_post_chat(
        db_chat,
        unread_count=unread_count,
        last_read_at=read_state.last_read_at if read_state else None,
    )


@router.get(
    "/{sub_post_id}/chat",
    response_model=SubPostChatRead,
    status_code=status.HTTP_200_OK,
)
def get_need_a_sub_chat(
    sub_post_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> SubPostChatRead:
    sub_post = get_sub_post_or_404(db, sub_post_id)
    validate_sub_post_chat_access(db, sub_post, current_user)
    db_chat = get_sub_post_chat_for_post(db, sub_post.id)
    if db_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat not found.",
        )

    read_state, unread_count = get_sub_chat_read_state(db, db_chat, current_user)
    return serialize_sub_post_chat(
        db_chat,
        unread_count=unread_count,
        last_read_at=read_state.last_read_at if read_state else None,
    )


@router.get(
    "/{sub_post_id}/chat/read-state",
    response_model=SubPostChatReadStateRead,
    status_code=status.HTTP_200_OK,
)
def get_need_a_sub_chat_read_state(
    sub_post_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> SubPostChatReadStateRead:
    sub_post = get_sub_post_or_404(db, sub_post_id)
    validate_sub_post_chat_access(db, sub_post, current_user)
    db_chat = get_sub_post_chat_for_post(db, sub_post.id)
    if db_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat not found.",
        )

    read_state, unread_count = get_sub_chat_read_state(db, db_chat, current_user)
    return SubPostChatReadStateRead(
        chat_id=db_chat.id,
        user_id=current_user.id,
        last_read_at=read_state.last_read_at if read_state else None,
        last_read_message_id=read_state.last_read_message_id if read_state else None,
        unread_count=unread_count,
    )


@router.post(
    "/{sub_post_id}/chat/read",
    response_model=SubPostChatReadStateRead,
    status_code=status.HTTP_200_OK,
)
def mark_need_a_sub_chat_read(
    sub_post_id: uuid.UUID,
    payload: SubPostChatEnsureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> SubPostChatReadStateRead:
    validate_optional_acting_user(payload.acting_user_id, current_user)
    sub_post = get_sub_post_or_404(db, sub_post_id)
    validate_sub_post_chat_access(db, sub_post, current_user)
    db_chat = get_sub_post_chat_for_post(db, sub_post.id)
    if db_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat not found.",
        )

    read_state = mark_sub_chat_read(db, db_chat, current_user)

    try:
        db.commit()
        db.refresh(read_state)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc

    return SubPostChatReadStateRead(
        chat_id=db_chat.id,
        user_id=current_user.id,
        last_read_at=read_state.last_read_at,
        last_read_message_id=read_state.last_read_message_id,
        unread_count=0,
    )


@router.get(
    "/{sub_post_id}/chat/messages",
    response_model=list[SubPostChatMessageRead],
    status_code=status.HTTP_200_OK,
)
def list_need_a_sub_chat_messages(
    sub_post_id: uuid.UUID,
    before_created_at: datetime | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> list[dict]:
    sub_post = get_sub_post_or_404(db, sub_post_id)
    validate_sub_post_chat_access(db, sub_post, current_user)
    db_chat = get_sub_post_chat_for_post(db, sub_post.id)
    if db_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat not found.",
        )

    messages = get_latest_visible_sub_chat_messages(
        db,
        db_chat.id,
        limit=limit,
        before_created_at=before_created_at,
    )
    return [serialize_sub_chat_message(db, message, sub_post) for message in messages]


@router.post(
    "/{sub_post_id}/chat/messages",
    response_model=SubPostChatMessageRead,
    status_code=status.HTTP_201_CREATED,
)
def create_need_a_sub_chat_message(
    sub_post_id: uuid.UUID,
    payload: SubPostChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> dict:
    current_time = datetime.now(timezone.utc)
    sub_post = get_sub_post_or_404(db, sub_post_id)
    validate_sub_post_chat_access(db, sub_post, current_user)
    db_chat = get_sub_post_chat_for_post(db, sub_post.id)
    if db_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat not found.",
        )
    require_sub_post_chat_can_write(db, db_chat, current_user)

    if payload.chat_id != db_chat.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chat_id must match this post's Need a Sub chat.",
        )

    if payload.sender_user_id is not None and payload.sender_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="sender_user_id must match the authenticated user.",
        )

    message_body = normalize_message_body(payload.message_body)
    validate_sender_rate_limit(db, db_chat.id, current_user.id, current_time)
    validate_total_message_limit(db, db_chat.id)
    sender_display_name, sender_initials = build_sender_snapshot(current_user)
    new_message = SubPostChatMessage(
        id=uuid.uuid4(),
        chat_id=db_chat.id,
        sender_user_id=current_user.id,
        sender_display_name_snapshot=sender_display_name,
        sender_initials_snapshot=sender_initials,
        message_type="text",
        message_body=message_body,
        moderation_status="visible",
    )

    try:
        db.add(new_message)
        db.flush()
        create_or_update_sub_chat_notifications(
            db,
            sub_post=sub_post,
            db_chat=db_chat,
            message=new_message,
            sender=current_user,
            event_at=current_time,
        )
        mark_sub_chat_read(db, db_chat, current_user, current_time)
        db.commit()
        db.refresh(new_message)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc

    return serialize_sub_chat_message(db, new_message, sub_post)


@router.patch(
    "/{sub_post_id}/chat/messages/{message_id}",
    response_model=SubPostChatMessageRead,
    status_code=status.HTTP_200_OK,
)
def update_need_a_sub_chat_message(
    sub_post_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: SubPostChatMessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> dict:
    sub_post = get_sub_post_or_404(db, sub_post_id)
    db_chat = get_sub_post_chat_for_post(db, sub_post.id)
    if db_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat not found.",
        )

    require_sub_post_chat_member(db, db_chat, current_user)
    db_message = db.get(SubPostChatMessage, message_id)
    if db_message is None or db_message.chat_id != db_chat.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat message not found.",
        )

    if db_message.sender_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the sender can update this Need a Sub chat message.",
        )

    if db_message.moderation_status in {"hidden_by_admin", "deleted_by_sender"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hidden or deleted Need a Sub chat messages cannot be updated.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "chat_id" in update_data and update_data["chat_id"] != db_chat.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chat_id cannot be changed for an existing Need a Sub chat message.",
        )

    forbidden_fields = {
        "sender_user_id",
        "sender_display_name_snapshot",
        "sender_initials_snapshot",
        "message_type",
    }
    if forbidden_fields & set(update_data):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sender and message type fields cannot be changed.",
        )

    if "message_body" in update_data:
        db_message.message_body = normalize_message_body(update_data["message_body"])
        db_message.edited_at = datetime.now(timezone.utc)

    if "moderation_status" in update_data:
        if update_data["moderation_status"] != "deleted_by_sender":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only sender deletion is supported for this message.",
            )
        db_message.moderation_status = "deleted_by_sender"
        db_message.deleted_at = datetime.now(timezone.utc)
        db_message.deleted_by_user_id = current_user.id

    db_message.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc

    return serialize_sub_chat_message(db, db_message, sub_post)


@router.get(
    "/{sub_post_id}",
    response_model=SubPostRead | SubPostPublicRead,
    status_code=status.HTTP_200_OK,
)
def get_need_a_sub_post(
    sub_post_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_app_user),
) -> dict:
    expire_due_posts_and_requests(db)
    sub_post = get_sub_post_or_404(db, sub_post_id)

    if user_can_view_private_sub_post(db, sub_post, current_user):
        return serialize_sub_post(db, sub_post)

    if not is_publicly_visible_sub_post(sub_post):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub post not found.",
        )

    return serialize_public_sub_post(db, sub_post)


@router.patch("/{sub_post_id}", response_model=SubPostRead, status_code=status.HTTP_200_OK)
def update_need_a_sub_post(
    sub_post_id: uuid.UUID,
    payload: SubPostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> dict:
    expire_due_posts_and_requests(db)
    sub_post = update_sub_post(db, current_user, sub_post_id, payload)
    return serialize_sub_post(db, sub_post)


@router.patch(
    "/{sub_post_id}/cancel",
    response_model=SubPostRead,
    status_code=status.HTTP_200_OK,
)
def cancel_need_a_sub_post(
    sub_post_id: uuid.UUID,
    payload: SubPostCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> dict:
    expire_due_posts_and_requests(db)
    sub_post = cancel_sub_post(db, current_user, sub_post_id, payload.cancel_reason)
    return serialize_sub_post(db, sub_post)


@router.patch(
    "/{sub_post_id}/remove",
    response_model=SubPostRead,
    status_code=status.HTTP_200_OK,
)
def remove_need_a_sub_post(
    sub_post_id: uuid.UUID,
    payload: SubPostRemove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> dict:
    expire_due_posts_and_requests(db)
    sub_post = remove_sub_post(db, current_user, sub_post_id, payload.remove_reason)
    return serialize_sub_post(db, sub_post)
