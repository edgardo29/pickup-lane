import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import SubPostPositionRead
from backend.services.need_a_sub_service import (
    expire_due_posts_and_requests,
    get_sub_post_or_404,
    is_publicly_visible_sub_post,
    list_positions,
    serialize_sub_post_position,
)

router = APIRouter(
    prefix="/need-a-sub/posts/{sub_post_id}/positions",
    tags=["need_a_sub_positions"],
)


@router.get("", response_model=list[SubPostPositionRead], status_code=status.HTTP_200_OK)
def list_need_a_sub_positions(
    sub_post_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list:
    expire_due_posts_and_requests(db)
    sub_post = get_sub_post_or_404(db, sub_post_id)

    if not is_publicly_visible_sub_post(sub_post):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub post not found.",
        )

    return [
        serialize_sub_post_position(db, position)
        for position in list_positions(db, sub_post_id)
    ]
