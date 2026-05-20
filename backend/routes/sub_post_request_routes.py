import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import SubPostRequest, User
from backend.routes.auth_routes import get_current_app_user
from backend.schemas import (
    SubPostRequestAction,
    SubPostRequestCreate,
    SubPostRequestRead,
)
from backend.services.need_a_sub_service import (
    create_request,
    expire_due_posts_and_requests,
    get_sub_post_or_404,
    owner_accept_request,
    owner_cancel_request,
    owner_decline_request,
    owner_report_no_show,
    requester_cancel_request,
    require_live_sub_post,
    require_owner,
    serialize_sub_post_request,
)

router = APIRouter(prefix="/need-a-sub", tags=["need_a_sub_requests"])


@router.post(
    "/posts/{sub_post_id}/requests",
    response_model=SubPostRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def request_need_a_sub_spot(
    sub_post_id: uuid.UUID,
    payload: SubPostRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> SubPostRequest:
    expire_due_posts_and_requests(db)
    return create_request(db, current_user, sub_post_id, payload.sub_post_position_id)


@router.get(
    "/posts/{sub_post_id}/requests",
    response_model=list[SubPostRequestRead],
    status_code=status.HTTP_200_OK,
)
def list_need_a_sub_post_requests(
    sub_post_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> list[dict]:
    expire_due_posts_and_requests(db)
    sub_post = get_sub_post_or_404(db, sub_post_id)
    require_owner(sub_post, current_user)
    require_live_sub_post(sub_post, "Only active or filled posts can be reviewed.")
    requests = list(
        db.scalars(
            select(SubPostRequest)
            .where(SubPostRequest.sub_post_id == sub_post_id)
            .order_by(SubPostRequest.created_at.asc())
        ).all()
    )
    return [
        serialize_sub_post_request(db, sub_request, include_waitlist_ahead=True)
        for sub_request in requests
    ]


@router.get(
    "/my-requests",
    response_model=list[SubPostRequestRead],
    status_code=status.HTTP_200_OK,
)
def list_my_need_a_sub_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> list[dict]:
    expire_due_posts_and_requests(db)
    requests = list(
        db.scalars(
            select(SubPostRequest)
            .where(SubPostRequest.requester_user_id == current_user.id)
            .order_by(SubPostRequest.created_at.desc())
        ).all()
    )
    return [
        serialize_sub_post_request(db, sub_request, include_waitlist_ahead=True)
        for sub_request in requests
    ]


@router.patch(
    "/requests/{request_id}/accept",
    response_model=SubPostRequestRead,
    status_code=status.HTTP_200_OK,
)
def accept_need_a_sub_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> SubPostRequest:
    expire_due_posts_and_requests(db)
    return owner_accept_request(db, current_user, request_id)


@router.patch(
    "/requests/{request_id}/decline",
    response_model=SubPostRequestRead,
    status_code=status.HTTP_200_OK,
)
def decline_need_a_sub_request(
    request_id: uuid.UUID,
    payload: SubPostRequestAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> SubPostRequest:
    expire_due_posts_and_requests(db)
    return owner_decline_request(db, current_user, request_id, payload.reason)


@router.patch(
    "/requests/{request_id}/cancel",
    response_model=SubPostRequestRead,
    status_code=status.HTTP_200_OK,
)
def cancel_my_need_a_sub_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> SubPostRequest:
    expire_due_posts_and_requests(db)
    return requester_cancel_request(db, current_user, request_id)


@router.patch(
    "/requests/{request_id}/cancel-by-owner",
    response_model=SubPostRequestRead,
    status_code=status.HTTP_200_OK,
)
def cancel_need_a_sub_request_by_owner(
    request_id: uuid.UUID,
    payload: SubPostRequestAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> SubPostRequest:
    expire_due_posts_and_requests(db)
    return owner_cancel_request(db, current_user, request_id, payload.reason)


@router.patch(
    "/requests/{request_id}/no-show",
    response_model=SubPostRequestRead,
    status_code=status.HTTP_200_OK,
)
def report_need_a_sub_no_show(
    request_id: uuid.UUID,
    payload: SubPostRequestAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> SubPostRequest:
    expire_due_posts_and_requests(db)
    return owner_report_no_show(db, current_user, request_id, payload.reason)
