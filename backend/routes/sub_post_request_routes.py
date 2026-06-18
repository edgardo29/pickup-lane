import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import SubPostRequest, User
from backend.services.auth_service import require_active_user
from backend.schemas import (
    SubPostRequestAction,
    SubPostRequestCreate,
    SubPostRequestRead,
)
from backend.services.need_a_sub_service import (
    create_request,
    expire_due_posts_and_requests,
    list_owner_sub_post_requests,
    list_requester_sub_post_requests,
    owner_accept_request,
    owner_cancel_request,
    owner_decline_request,
    owner_report_no_show,
    requester_cancel_request,
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
    current_user: User = Depends(require_active_user),
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
    current_user: User = Depends(require_active_user),
) -> list[dict]:
    return list_owner_sub_post_requests(db, sub_post_id, current_user)


@router.get(
    "/my-requests",
    response_model=list[SubPostRequestRead],
    status_code=status.HTTP_200_OK,
)
def list_my_need_a_sub_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> list[dict]:
    return list_requester_sub_post_requests(db, current_user)


@router.patch(
    "/requests/{request_id}/accept",
    response_model=SubPostRequestRead,
    status_code=status.HTTP_200_OK,
)
def accept_need_a_sub_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
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
    current_user: User = Depends(require_active_user),
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
    current_user: User = Depends(require_active_user),
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
    current_user: User = Depends(require_active_user),
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
    current_user: User = Depends(require_active_user),
) -> SubPostRequest:
    expire_due_posts_and_requests(db)
    return owner_report_no_show(db, current_user, request_id, payload.reason)
