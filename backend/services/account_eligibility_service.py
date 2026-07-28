"""Shared account eligibility predicates for user-visible system features."""

from sqlalchemy import and_

from backend.models import User


def account_eligible_condition():
    return and_(User.account_status == "active", User.deleted_at.is_(None))


def user_is_account_eligible(user: User | None) -> bool:
    return (
        user is not None
        and user.account_status == "active"
        and user.deleted_at is None
    )
