"""Restricted account experience for a suspended player."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import AdminAction, Notification, User
from backend.schemas.account_suspension_schema import SuspendedAccountRead


def get_suspended_account_notice(
    db: Session,
    *,
    user: User,
) -> SuspendedAccountRead:
    if user.account_status != "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not suspended.",
        )

    notice = db.scalar(
        select(Notification)
        .join(
            AdminAction,
            AdminAction.target_notification_id == Notification.id,
        )
        .where(
            AdminAction.action_type == "suspend_user",
            AdminAction.outcome == "succeeded",
            AdminAction.target_user_id == user.id,
            Notification.user_id == user.id,
            Notification.notification_type == "account_security",
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(1)
    )
    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suspension notice not found.",
        )

    return SuspendedAccountRead(
        account_status=user.account_status,
        notice_title=notice.title,
        notice_message=notice.body,
        notice_occurred_at=notice.event_at,
    )
