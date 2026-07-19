"""Admin enforcement workflows for Need a Sub posts."""

import uuid
from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import AdminAction, AdminTargetNotice, SubPost, User
from backend.schemas.admin_need_a_sub_schema import (
    AdminNeedASubEnforcementActionCreate,
    AdminNeedASubEnforcementActionResultRead,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_record_rules import (
    normalize_idempotency_key,
    normalize_optional_text,
)
from backend.services.admin_review_service import link_admin_action_to_open_review_case
from backend.services.admin_target_notice_service import create_admin_target_notice
from backend.services.auth_service import require_active_admin_user
from backend.services.need_a_sub_lifecycle_service import expire_due_posts_and_requests
from backend.services.need_a_sub_post_service import (
    get_existing_remove_sub_post_action,
    get_notice_ids_for_admin_action,
    get_sub_post_for_update_or_404,
    get_sub_post_or_404,
    remove_sub_post,
    validate_remove_sub_post_replay,
)
from backend.services.need_a_sub_rules import now_utc

VISIBLE = "visible"
HIDDEN = "hidden"


def normalize_enforcement_request(
    payload: AdminNeedASubEnforcementActionCreate,
) -> tuple[str, str]:
    reason = normalize_optional_text(payload.reason, "reason")
    if reason is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason is required.",
        )

    idempotency_key = normalize_idempotency_key(payload.idempotency_key)
    if idempotency_key is None or len(idempotency_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be at least 8 characters.",
        )

    return reason, idempotency_key


def get_existing_need_sub_action(
    db: Session,
    *,
    action_type: str,
    admin_user_id: uuid.UUID,
    post_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction)
        .where(
            AdminAction.action_type == action_type,
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.target_sub_post_id == post_id,
            AdminAction.idempotency_key == idempotency_key,
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(1)
    )


def validate_existing_action(action: AdminAction, *, expected_reason: str) -> None:
    if action.reason != expected_reason:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="idempotency_key was already used for a different action.",
        )


def build_result(
    db: Session,
    *,
    post: SubPost,
    audit_action: AdminAction,
    idempotent_replay: bool,
) -> AdminNeedASubEnforcementActionResultRead:
    metadata = audit_action.metadata_ or {}
    closed_request_ids = [
        uuid.UUID(value)
        for value in metadata.get("closed_request_ids", [])
        if isinstance(value, str)
    ]
    return AdminNeedASubEnforcementActionResultRead(
        post_id=post.id,
        post_status=post.post_status,
        public_visibility_status=post.public_visibility_status,
        audit_action_id=audit_action.id,
        notice_ids=get_notice_ids_for_admin_action(db, audit_action.id),
        closed_request_ids=closed_request_ids,
        idempotent_replay=idempotent_replay,
    )


def create_owner_notice(
    db: Session,
    *,
    post: SubPost,
    audit_action: AdminAction,
    admin_user: User,
    notice_type: str,
    title: str,
    body: str,
    reason: str,
) -> AdminTargetNotice:
    return create_admin_target_notice(
        db,
        notice_type=notice_type,
        title=title,
        body=body,
        recipient_user_id=post.owner_user_id,
        target_user_id=post.owner_user_id,
        target_sub_post_id=post.id,
        admin_action=audit_action,
        created_by_user_id=admin_user.id,
        user_safe_reason=reason,
    )


def apply_need_sub_visibility_action(
    db: Session,
    *,
    post_id: uuid.UUID,
    admin_user: User,
    payload: AdminNeedASubEnforcementActionCreate,
    action_type: str,
    new_visibility: str,
    notice_type: str,
    notice_title: str,
    notice_body: str,
    state_validator: Callable[[SubPost], None],
) -> AdminNeedASubEnforcementActionResultRead:
    require_active_admin_user(admin_user)
    reason, idempotency_key = normalize_enforcement_request(payload)
    post = get_sub_post_or_404(db, post_id)

    existing_action = get_existing_need_sub_action(
        db,
        action_type=action_type,
        admin_user_id=admin_user.id,
        post_id=post.id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        validate_existing_action(existing_action, expected_reason=reason)
        return build_result(
            db,
            post=post,
            audit_action=existing_action,
            idempotent_replay=True,
        )

    post = get_sub_post_for_update_or_404(db, post.id)
    existing_action = get_existing_need_sub_action(
        db,
        action_type=action_type,
        admin_user_id=admin_user.id,
        post_id=post.id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        validate_existing_action(existing_action, expected_reason=reason)
        return build_result(
            db,
            post=post,
            audit_action=existing_action,
            idempotent_replay=True,
        )

    state_validator(post)
    current_time = now_utc()
    old_visibility = post.public_visibility_status
    post.public_visibility_status = new_visibility
    post.updated_at = current_time
    audit_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type=action_type,
        target_user_id=post.owner_user_id,
        target_sub_post_id=post.id,
        reason=reason,
        metadata={
            "source": "admin_need_a_sub_enforcement",
            "before": {"public_visibility_status": old_visibility},
            "after": {"public_visibility_status": new_visibility},
        },
        idempotency_key=idempotency_key,
        created_at=current_time,
    )
    link_admin_action_to_open_review_case(db, audit_action)
    notice = create_owner_notice(
        db,
        post=post,
        audit_action=audit_action,
        admin_user=admin_user,
        notice_type=notice_type,
        title=notice_title,
        body=notice_body,
        reason=reason,
    )
    db.flush()
    metadata = dict(audit_action.metadata_ or {})
    metadata["notice_ids"] = [str(notice.id)]
    audit_action.metadata_ = metadata

    try:
        db.add(post)
        db.add(audit_action)
        db.commit()
        db.refresh(post)
        db.refresh(audit_action)
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_need_sub_action(
            db,
            action_type=action_type,
            admin_user_id=admin_user.id,
            post_id=post_id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            validate_existing_action(existing_action, expected_reason=reason)
            post = get_sub_post_or_404(db, post_id)
            return build_result(
                db,
                post=post,
                audit_action=existing_action,
                idempotent_replay=True,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Need a Sub action could not be applied.",
        ) from exc

    return build_result(
        db,
        post=post,
        audit_action=audit_action,
        idempotent_replay=False,
    )


def hide_need_a_sub_post(
    db: Session,
    *,
    post_id: uuid.UUID,
    admin_user: User,
    payload: AdminNeedASubEnforcementActionCreate,
) -> AdminNeedASubEnforcementActionResultRead:
    def validate_state(post: SubPost) -> None:
        if post.post_status == "removed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Removed Need a Sub posts cannot be hidden.",
            )
        if post.public_visibility_status == HIDDEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Need a Sub post is already hidden.",
            )

    return apply_need_sub_visibility_action(
        db,
        post_id=post_id,
        admin_user=admin_user,
        payload=payload,
        action_type="hide_need_sub_post",
        new_visibility=HIDDEN,
        notice_type="need_sub_post_hidden",
        notice_title="Need a Sub post hidden",
        notice_body=(
            "Your Need a Sub post is hidden from public browsing while "
            "an admin review is active."
        ),
        state_validator=validate_state,
    )


def restore_need_a_sub_post(
    db: Session,
    *,
    post_id: uuid.UUID,
    admin_user: User,
    payload: AdminNeedASubEnforcementActionCreate,
) -> AdminNeedASubEnforcementActionResultRead:
    def validate_state(post: SubPost) -> None:
        if post.post_status == "removed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Removed Need a Sub posts cannot be restored.",
            )
        if post.public_visibility_status == VISIBLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Need a Sub post is already visible.",
            )

    return apply_need_sub_visibility_action(
        db,
        post_id=post_id,
        admin_user=admin_user,
        payload=payload,
        action_type="restore_need_sub_post",
        new_visibility=VISIBLE,
        notice_type="need_sub_post_restored",
        notice_title="Need a Sub post restored",
        notice_body="Your Need a Sub post is visible again.",
        state_validator=validate_state,
    )


def remove_need_a_sub_post_by_admin(
    db: Session,
    *,
    post_id: uuid.UUID,
    admin_user: User,
    payload: AdminNeedASubEnforcementActionCreate,
) -> AdminNeedASubEnforcementActionResultRead:
    expire_due_posts_and_requests(db)
    reason, idempotency_key = normalize_enforcement_request(payload)
    existing_action = get_existing_remove_sub_post_action(
        db,
        admin_user_id=admin_user.id,
        sub_post_id=post_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        validate_remove_sub_post_replay(existing_action, expected_reason=reason)
        post = get_sub_post_or_404(db, post_id)
        return build_result(
            db,
            post=post,
            audit_action=existing_action,
            idempotent_replay=True,
        )

    post = remove_sub_post(
        db,
        admin_user,
        post_id,
        reason,
        idempotency_key,
    )
    action = get_existing_remove_sub_post_action(
        db,
        admin_user_id=admin_user.id,
        sub_post_id=post.id,
        idempotency_key=idempotency_key,
    )
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Removal audit action was not recorded.",
        )
    return build_result(
        db,
        post=post,
        audit_action=action,
        idempotent_replay=False,
    )
