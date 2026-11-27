"""The suspension notice outside Inbox, in the restricted account experience."""

from datetime import datetime

import pytest

from backend.models import Notification
from backend.schemas.admin_user_schema import AdminUserSuspendCreate
from backend.services.admin_user_account_service import (
    preview_admin_user_suspension,
    suspend_admin_user,
)
from backend.tests.factories import make_user


def suspend(db, user):
    """Suspend ``user`` through the staff suspension workflow."""
    admin = make_user(db, role="admin")
    preview = preview_admin_user_suspension(db, user_id=user.id)
    return suspend_admin_user(
        db,
        admin_user=admin,
        user_id=user.id,
        payload=AdminUserSuspendCreate(
            preview_token=preview.preview_token,
            reason="Policy review",
            idempotency_key=f"suspend-{user.id}",
        ),
    )


@pytest.mark.page("F25", 13)
def test_a_suspended_user_reads_the_suspension_notice_outside_inbox(
    db, client, inbox_user, inbox_headers
):
    result = suspend(db, inbox_user)
    notice = db.get(Notification, result.notification_id)

    response = client.get("/account-suspended", headers=inbox_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["account_status"] == "suspended"
    assert body["notice_title"] == notice.title
    assert body["notice_message"] == notice.body
    assert datetime.fromisoformat(body["notice_occurred_at"]) == notice.event_at


@pytest.mark.page("F25", 13)
@pytest.mark.parametrize(
    "path", ["/inbox/app-updates", "/inbox/game-activity", "/inbox/counts"]
)
def test_a_suspended_users_inbox_requests_are_refused(
    db, client, inbox_user, inbox_headers, path
):
    suspend(db, inbox_user)

    response = client.get(path, headers=inbox_headers)

    assert response.status_code == 403
