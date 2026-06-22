"""Shared community-hosting eligibility rules."""

from datetime import datetime

from fastapi import HTTPException, status

from backend.models import User

HOSTING_STATUS_NOT_ELIGIBLE = "not_eligible"
HOSTING_STATUS_PENDING_REVIEW = "pending_review"
HOSTING_STATUS_ELIGIBLE = "eligible"
HOSTING_STATUS_RESTRICTED = "restricted"
HOSTING_STATUS_SUSPENDED = "suspended"
HOSTING_STATUS_BANNED = "banned_from_hosting"

COMMUNITY_PUBLISH_BLOCKING_DETAILS = {
    HOSTING_STATUS_NOT_ELIGIBLE: (
        "Your account is not eligible to host community games."
    ),
    HOSTING_STATUS_PENDING_REVIEW: "Your hosting access is pending review.",
    HOSTING_STATUS_RESTRICTED: "Your hosting access is restricted.",
    HOSTING_STATUS_SUSPENDED: "Your hosting access is suspended.",
    HOSTING_STATUS_BANNED: "Your account is banned from hosting.",
}


def apply_verified_hosting_eligibility(
    user: User,
    *,
    verified_at: datetime,
) -> bool:
    if user.hosting_status != HOSTING_STATUS_NOT_ELIGIBLE:
        return False

    user.hosting_status = HOSTING_STATUS_ELIGIBLE
    user.hosting_suspended_until = None
    user.updated_at = verified_at
    return True


def require_community_publish_hosting_access(user: User) -> None:
    if user.hosting_status == HOSTING_STATUS_ELIGIBLE:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=COMMUNITY_PUBLISH_BLOCKING_DETAILS.get(
            user.hosting_status,
            "Your account cannot publish community games.",
        ),
    )
