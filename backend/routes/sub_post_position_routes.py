import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import SubPostPositionRead
from backend.services.need_a_sub_post_service import (
    list_public_sub_post_positions,
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
    return list_public_sub_post_positions(db, sub_post_id)
