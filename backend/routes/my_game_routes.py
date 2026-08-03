from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import MyGamesListRead, MyNeedASubListRead
from backend.services.auth_service import require_active_user
from backend.services.game_service import list_my_game_cards
from backend.services.need_a_sub_post_service import list_my_need_a_sub_cards

router = APIRouter(prefix="/my-games", tags=["my_games"])


def _mark_private_no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"


@router.get("", response_model=MyGamesListRead, status_code=status.HTTP_200_OK)
def list_my_games(
    response: Response,
    view: str = Query(default="upcoming"),
    limit: int = Query(default=40, ge=1),
    cursor: str | None = Query(default=None, max_length=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> MyGamesListRead:
    _mark_private_no_store(response)
    return list_my_game_cards(
        db,
        current_user,
        view=view,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/need-a-sub",
    response_model=MyNeedASubListRead,
    status_code=status.HTTP_200_OK,
)
def list_my_need_a_sub(
    response: Response,
    view: str = Query(default="upcoming"),
    limit: int = Query(default=40, ge=1),
    cursor: str | None = Query(default=None, max_length=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> MyNeedASubListRead:
    _mark_private_no_store(response)
    return list_my_need_a_sub_cards(
        db,
        current_user,
        view=view,
        limit=limit,
        cursor=cursor,
    )
