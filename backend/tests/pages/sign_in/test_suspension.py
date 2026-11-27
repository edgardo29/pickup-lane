"""F07 suspension reads and access after Firebase authentication."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from backend.models import AdminAction, Notification
from backend.tests.factories import make_user

from .conftest import commitments, suspend


@pytest.mark.page("F07", 12)
def test_suspended_account_load_preserves_existing_commitments(
    db, client, firebase, suspended_commitments
):
    user, *_ = suspended_commitments
    before = commitments(db)
    response = client.get("/auth/me", headers=firebase.sign_in(user))
    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert response.json()["account_status"] == "suspended"
    assert commitments(db) == before
    db.refresh(user)
    assert user.account_status == "suspended"


@pytest.mark.page("F07", 12)
@pytest.mark.parametrize(
    "notice_state", ["linked", "missing", "wrong_owner", "active", "older_only"]
)
def test_suspension_notice_is_own_linked_notice_not_inbox_or_staff_reason(
    clock, db, client, firebase, suspended_commitments, notice_state
):
    user, _, _, result, *_ = suspended_commitments
    other = make_user(db)
    other_result = suspend(db, other)
    if notice_state == "older_only":
        first_action = db.get(AdminAction, result.admin_action_id)
        from backend.schemas.admin_user_schema import AdminUserUnsuspendCreate
        from backend.services.admin_user_account_service import unsuspend_admin_user

        clock.advance(timedelta(minutes=1))
        unsuspend_admin_user(
            db,
            admin_user=make_user(db, role="admin"),
            user_id=user.id,
            payload=AdminUserUnsuspendCreate(
                reason="Synthetic review completed",
                idempotency_key=f"restore-{user.id}",
            ),
        )
        clock.advance(timedelta(minutes=1))
        result = suspend(db, user)
        # PostgreSQL now() is fixed for this test's outer transaction. Give the
        # later real action its chronological timestamp instead of an ID tie.
        db.get(AdminAction, result.admin_action_id).created_at = (
            first_action.created_at + timedelta(minutes=2)
        )
    notification = db.get(Notification, result.notification_id)
    # A later unrelated account-security notice must not replace the suspension.
    db.add(
        Notification(
            id=uuid.uuid4(),
            user_id=user.id,
            notification_type="account_security",
            notification_category="app",
            notification_domain="account",
            source_type=notification.source_type,
            title="Unrelated account update",
            subject_label=notification.subject_label,
            summary="Unrelated",
            body="Unrelated private notice",
            action_key=None,
            event_at=clock.now + timedelta(minutes=1),
        )
    )
    if notice_state in {"missing", "older_only"}:
        db.delete(notification)
    if notice_state == "wrong_owner":
        notification.user_id = other.id
    if notice_state == "active":
        user.account_status = "active"
    db.commit()
    before = commitments(db)
    response = client.get("/account-suspended", headers=firebase.sign_in(user))
    assert response.headers["Cache-Control"] == "private, no-store"
    if notice_state == "linked":
        assert response.status_code == 200, response.text
        assert response.json() == {
            "account_status": "suspended",
            "notice_title": notification.title,
            "notice_message": notification.body,
            "notice_occurred_at": notification.event_at.isoformat().replace(
                "+00:00", "Z"
            ),
        }
        assert (
            "manage or withdraw from existing commitments"
            in response.json()["notice_message"]
        )
        assert "Product and staff actions are unavailable" not in response.text
    else:
        assert response.status_code == (403 if notice_state == "active" else 404)
        assert response.json()["detail"] == (
            "This account is not suspended."
            if notice_state == "active"
            else "Suspension notice not found."
        )
    assert "Private synthetic staff reason" not in response.text
    assert str(other_result.notification_id) not in response.text
    assert "Unrelated private notice" not in response.text
    assert commitments(db) == before
    if notice_state not in {"missing", "older_only"}:
        db.refresh(notification)
        assert notification.is_read is False


@pytest.mark.page("F07", 12)
def test_signed_out_request_cannot_read_suspension_notice(
    db, client, suspended_commitments
):
    before = list(db.execute(select(Notification.__table__)))
    response = client.get("/account-suspended")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization header."
    assert list(db.execute(select(Notification.__table__))) == before


@pytest.mark.page("F07", 12)
def test_existing_game_and_sub_commitments_remain_accessible(
    db, client, firebase, suspended_commitments
):
    user, game, post, _, *_ = suspended_commitments
    before = commitments(db)
    headers = firebase.sign_in(user)
    games = client.get("/my-games", headers=headers)
    posts = client.get("/my-games/need-a-sub", headers=headers)
    assert games.status_code == 200
    assert posts.status_code == 200
    assert [item["game"]["id"] for item in games.json()["items"]] == [str(game.id)]
    assert [item["post"]["id"] for item in posts.json()["items"]] == [str(post.id)]
    assert commitments(db) == before
