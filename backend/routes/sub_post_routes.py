import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.services.admin_permission_service import PERMISSION_NEED_A_SUB_MODERATE
from backend.services.auth_service import (
    get_optional_current_app_user,
    require_admin_permission,
    require_active_user,
)
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
    create_sub_post_chat_message_workflow,
    ensure_sub_post_chat_workflow,
    get_sub_post_chat_read_state_workflow,
    get_sub_post_chat_workflow,
    list_sub_post_chat_messages_workflow,
    mark_sub_post_chat_read_workflow,
    update_sub_post_chat_message_workflow,
)

router = APIRouter(prefix="/need-a-sub/posts", tags=["need_a_sub_posts"])


@router.post("", response_model=SubPostRead, status_code=status.HTTP_201_CREATED)
def create_need_a_sub_post(
    sub_post: SubPostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
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
    current_user: User = Depends(require_active_user),
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
    current_user: User = Depends(require_active_user),
) -> SubPostChatRead:
    return ensure_sub_post_chat_workflow(db, sub_post_id, payload, current_user)


@router.get(
    "/{sub_post_id}/chat",
    response_model=SubPostChatRead,
    status_code=status.HTTP_200_OK,
)
def get_need_a_sub_chat(
    sub_post_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> SubPostChatRead:
    return get_sub_post_chat_workflow(db, sub_post_id, current_user)


@router.get(
    "/{sub_post_id}/chat/read-state",
    response_model=SubPostChatReadStateRead,
    status_code=status.HTTP_200_OK,
)
def get_need_a_sub_chat_read_state(
    sub_post_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> SubPostChatReadStateRead:
    return get_sub_post_chat_read_state_workflow(db, sub_post_id, current_user)


@router.post(
    "/{sub_post_id}/chat/read",
    response_model=SubPostChatReadStateRead,
    status_code=status.HTTP_200_OK,
)
def mark_need_a_sub_chat_read(
    sub_post_id: uuid.UUID,
    payload: SubPostChatEnsureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> SubPostChatReadStateRead:
    return mark_sub_post_chat_read_workflow(db, sub_post_id, payload, current_user)


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
    current_user: User = Depends(require_active_user),
) -> list[dict]:
    return list_sub_post_chat_messages_workflow(
        db,
        sub_post_id,
        current_user,
        limit=limit,
        before_created_at=before_created_at,
    )


@router.post(
    "/{sub_post_id}/chat/messages",
    response_model=SubPostChatMessageRead,
    status_code=status.HTTP_201_CREATED,
)
def create_need_a_sub_chat_message(
    sub_post_id: uuid.UUID,
    payload: SubPostChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> dict:
    return create_sub_post_chat_message_workflow(
        db,
        sub_post_id,
        payload,
        current_user,
    )


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
    current_user: User = Depends(require_active_user),
) -> dict:
    return update_sub_post_chat_message_workflow(
        db,
        sub_post_id,
        message_id,
        payload,
        current_user,
    )


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
    current_user: User = Depends(require_active_user),
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
    current_user: User = Depends(require_active_user),
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
    current_user: User = Depends(
        require_admin_permission(PERMISSION_NEED_A_SUB_MODERATE)
    ),
) -> dict:
    expire_due_posts_and_requests(db)
    sub_post = remove_sub_post(
        db,
        current_user,
        sub_post_id,
        payload.remove_reason,
        payload.idempotency_key,
    )
    return serialize_sub_post(db, sub_post)
