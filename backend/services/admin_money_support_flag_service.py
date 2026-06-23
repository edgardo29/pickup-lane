"""Admin money support flag mutation workflows."""

import uuid

from sqlalchemy.orm import Session

from backend.models import User
from backend.schemas.admin_money_schema import AdminMoneySupportFlagDetailRead
from backend.schemas.support_flag_schema import SupportFlagResolve
from backend.services.admin_money_support_flag_read_service import (
    get_admin_money_support_flag_detail,
    get_admin_money_support_flag_or_404,
)
from backend.services.support_flag_service import resolve_support_flag


def resolve_admin_money_support_flag(
    db: Session,
    *,
    support_flag_id: uuid.UUID,
    admin_user: User,
    payload: SupportFlagResolve,
) -> AdminMoneySupportFlagDetailRead:
    get_admin_money_support_flag_or_404(
        db,
        support_flag_id=support_flag_id,
        viewer_user=admin_user,
    )
    resolve_support_flag(
        db,
        support_flag_id=support_flag_id,
        resolver_user=admin_user,
        payload=payload,
    )
    return get_admin_money_support_flag_detail(
        db,
        support_flag_id=support_flag_id,
        viewer_user=admin_user,
    )
