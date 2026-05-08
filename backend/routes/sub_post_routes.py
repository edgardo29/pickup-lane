import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.routes.auth_routes import get_current_app_user
from backend.schemas import SubPostCancel, SubPostCreate, SubPostRead, SubPostRemove
from backend.services.need_a_sub_service import (
    cancel_sub_post,
    create_sub_post,
    get_sub_post_or_404,
    query_visible_posts,
    remove_sub_post,
    serialize_sub_post,
)

router = APIRouter(prefix="/need-a-sub/posts", tags=["need_a_sub_posts"])


@router.post("", response_model=SubPostRead, status_code=status.HTTP_201_CREATED)
def create_need_a_sub_post(
    sub_post: SubPostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> dict:
    new_post = create_sub_post(db, current_user, sub_post)
    return serialize_sub_post(db, new_post)


@router.get("", response_model=list[SubPostRead], status_code=status.HTTP_200_OK)
def list_need_a_sub_posts(
    city: str | None = None,
    state: str | None = Query(default=None),
    starts_after: datetime | None = None,
    starts_before: datetime | None = None,
    skill_level: str | None = None,
    game_player_group: str | None = None,
    format_label: str | None = None,
    sport_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    posts = query_visible_posts(
        db,
        city=city,
        state_value=state,
        starts_after=starts_after,
        starts_before=starts_before,
        skill_level=skill_level,
        game_player_group=game_player_group,
        format_label=format_label,
        sport_type=sport_type,
    )
    return [serialize_sub_post(db, sub_post) for sub_post in posts]


@router.get("/{sub_post_id}", response_model=SubPostRead, status_code=status.HTTP_200_OK)
def get_need_a_sub_post(
    sub_post_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    sub_post = get_sub_post_or_404(db, sub_post_id)
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
    sub_post = remove_sub_post(db, current_user, sub_post_id, payload.remove_reason)
    return serialize_sub_post(db, sub_post)
