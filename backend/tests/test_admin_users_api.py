from datetime import UTC, datetime, timedelta
from uuid import UUID
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import (
    AdminAction,
    AdminRejectedAttempt,
    Booking,
    Game,
    GameChat,
    GameCredit,
    GameParticipant,
    GameStatusHistory,
    Notification,
    SubPost,
    SubPostChat,
    SubPostRequest,
    SupportFlag,
    User,
    UserPaymentMethod,
    WaitlistEntry,
)
from backend.services.support_flag_service import create_support_flag
from backend.tests.helpers import (
    authenticate_as,
    create_admin_action,
    create_booking,
    create_game,
    create_game_chat,
    create_game_participant,
    create_payment,
    create_refund,
    create_sub_post,
    create_user,
    create_user_payment_method,
    create_user_stats,
    create_venue,
    create_waitlist_entry,
    set_user_account_status,
    set_user_hosting_status,
    set_user_role,
    soft_delete_user,
)


def authenticate_admin(client: TestClient) -> dict:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])
    return admin


def test_admin_users_list_returns_explicit_safe_shape(client: TestClient):
    authenticate_admin(client)
    user = create_user(
        client,
        first_name="Avery",
        last_name="Support",
        email="avery.support@example.com",
        phone="+1 (312) 555-0142",
        home_city="Chicago",
        home_state="IL",
    )

    response = client.get(f"/admin/users?query={user['id']}")

    assert response.status_code == 200, response.text
    assert len(response.json()) == 1
    body = response.json()[0]
    assert body == {
        "id": user["id"],
        "display_name": "Avery Support",
        "email": "avery.support@example.com",
        "phone": "+1 (312) 555-0142",
        "role": "player",
        "account_status": "active",
        "hosting_status": "not_eligible",
        "email_verified": False,
        "home_city": "Chicago",
        "home_state": "IL",
        "member_since": user["member_since"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
        "deleted_at": None,
    }
    assert "auth_user_id" not in body
    assert "date_of_birth" not in body
    assert "profile_photo_url" not in body
    assert "stripe_customer_id" not in body


def test_admin_users_list_searches_name_email_and_normalized_phone(
    client: TestClient,
):
    authenticate_admin(client)
    target = create_user(
        client,
        first_name="Jordan",
        last_name="Keeper",
        email="jordan.keeper@example.com",
        phone="+1 (773) 555-0199",
    )
    create_user(client, first_name="Someone", last_name="Else")

    for query in ("jordan keeper", "KEEPER@EXAMPLE.COM", "7735550199"):
        response = client.get("/admin/users", params={"query": query})
        assert response.status_code == 200, response.text
        assert [item["id"] for item in response.json()] == [target["id"]]


def test_admin_users_list_filters_role_account_and_hosting_status(
    client: TestClient,
):
    authenticate_admin(client)
    target = create_user(client, first_name="Filtered", last_name="User")
    set_user_role(target["id"], "admin")
    set_user_account_status(target["id"], "suspended")
    set_user_hosting_status(target["id"], "restricted")
    create_user(client)

    response = client.get(
        "/admin/users",
        params={
            "role": "admin",
            "account_status": "suspended",
            "hosting_status": "restricted",
        },
    )

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()] == [target["id"]]


def test_admin_users_list_hides_deleted_users_unless_requested(client: TestClient):
    authenticate_admin(client)
    deleted_user = create_user(client)
    soft_delete_user(deleted_user["id"])

    default_response = client.get(
        "/admin/users",
        params={"query": deleted_user["id"]},
    )
    assert default_response.status_code == 200, default_response.text
    assert default_response.json() == []

    included_response = client.get(
        "/admin/users",
        params={
            "query": deleted_user["id"],
            "include_deleted": True,
        },
    )
    assert included_response.status_code == 200, included_response.text
    assert [item["id"] for item in included_response.json()] == [deleted_user["id"]]
    assert included_response.json()[0]["account_status"] == "deleted"
    assert included_response.json()[0]["deleted_at"] is not None


def test_admin_users_list_redacts_inconsistent_deleted_states(client: TestClient):
    authenticate_admin(client)
    status_deleted_user = create_user(
        client,
        first_name="Status",
        last_name="Deleted",
        email="status.deleted@example.com",
        phone="+13125550101",
        home_city="Chicago",
        home_state="IL",
    )
    timestamp_deleted_user = create_user(
        client,
        first_name="Timestamp",
        last_name="Deleted",
        email="timestamp.deleted@example.com",
        phone="+13125550102",
        home_city="Evanston",
        home_state="IL",
    )
    set_user_account_status(status_deleted_user["id"], "deleted")
    with SessionLocal() as db:
        db_timestamp_deleted_user = db.get(User, UUID(timestamp_deleted_user["id"]))
        assert db_timestamp_deleted_user is not None
        db_timestamp_deleted_user.deleted_at = datetime.now(UTC)
        db.commit()

    for user in (status_deleted_user, timestamp_deleted_user):
        default_response = client.get("/admin/users", params={"query": user["id"]})
        assert default_response.status_code == 200, default_response.text
        assert default_response.json() == []

        included_response = client.get(
            "/admin/users",
            params={
                "query": user["id"],
                "include_deleted": True,
            },
        )
        assert included_response.status_code == 200, included_response.text
        body = included_response.json()[0]
        assert body["id"] == user["id"]
        assert body["display_name"] == "Deleted User"
        assert body["email"] is None
        assert body["phone"] is None
        assert body["home_city"] is None
        assert body["home_state"] is None
        assert body["email_verified"] is False
        assert body["account_status"] == "deleted"

        for stale_pii_query in (
            user["email"],
            user["phone"],
            f"{user['first_name']} {user['last_name']}",
        ):
            stale_pii_response = client.get(
                "/admin/users",
                params={
                    "query": stale_pii_query,
                    "include_deleted": True,
                },
            )
            assert stale_pii_response.status_code == 200, stale_pii_response.text
            assert stale_pii_response.json() == []

        active_filter_response = client.get(
            "/admin/users",
            params={
                "account_status": "active",
                "include_deleted": True,
                "query": user["id"],
            },
        )
        assert active_filter_response.status_code == 200, active_filter_response.text
        assert active_filter_response.json() == []

        deleted_filter_response = client.get(
            "/admin/users",
            params={
                "account_status": "deleted",
                "include_deleted": True,
                "query": user["id"],
            },
        )
        assert deleted_filter_response.status_code == 200, deleted_filter_response.text
        assert [item["id"] for item in deleted_filter_response.json()] == [user["id"]]

        deleted_status_response = client.get(
            "/admin/users",
            params={
                "account_status": "deleted",
                "query": user["id"],
            },
        )
        assert deleted_status_response.status_code == 200, (
            deleted_status_response.text
        )
        assert [item["id"] for item in deleted_status_response.json()] == [user["id"]]


def test_admin_users_list_rejects_unsupported_filters(client: TestClient):
    authenticate_admin(client)

    response = client.get("/admin/users", params={"account_status": "locked"})

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "account_status is not supported."


def test_admin_users_list_rejects_player(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.get("/admin/users")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


def test_admin_users_list_rejects_suspended_admin(client: TestClient):
    admin = authenticate_admin(client)
    set_user_account_status(admin["id"], "suspended")

    response = client.get("/admin/users")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


def test_admin_staff_list_returns_staff_only_safe_shape(client: TestClient):
    admin = authenticate_admin(client)
    second_admin = create_user(
        client,
        first_name="Admin",
        last_name="Helper",
        email="admin.helper@example.com",
    )
    set_user_role(second_admin["id"], "admin")
    suspended_admin = create_user(client)
    set_user_role(suspended_admin["id"], "admin")
    set_user_account_status(suspended_admin["id"], "suspended")
    player = create_user(client)
    deleted_admin = create_user(
        client,
        first_name="Deleted",
        last_name="Admin",
        email="deleted.admin@example.com",
    )
    set_user_role(deleted_admin["id"], "admin")
    soft_delete_user(deleted_admin["id"])

    response = client.get("/admin/users/staff")

    assert response.status_code == 200, response.text
    body = response.json()
    body_by_id = {item["id"]: item for item in body}
    assert set(body_by_id) == {
        admin["id"],
        second_admin["id"],
        suspended_admin["id"],
    }
    assert player["id"] not in body_by_id
    assert deleted_admin["id"] not in body_by_id
    assert body_by_id[second_admin["id"]]["display_name"] == "Admin Helper"
    assert body_by_id[second_admin["id"]]["email"] == "admin.helper@example.com"
    assert body_by_id[second_admin["id"]]["role"] == "admin"
    assert body_by_id[second_admin["id"]]["account_status"] == "active"
    assert "permissions" not in body_by_id[second_admin["id"]]
    assert "data_scopes" not in body_by_id[second_admin["id"]]
    assert "auth_user_id" not in body_by_id[second_admin["id"]]
    assert "stripe_customer_id" not in body_by_id[second_admin["id"]]
    assert "date_of_birth" not in body_by_id[second_admin["id"]]

    included_response = client.get(
        "/admin/users/staff",
        params={"include_deleted": True},
    )
    assert included_response.status_code == 200, included_response.text
    included_by_id = {item["id"]: item for item in included_response.json()}
    assert deleted_admin["id"] in included_by_id
    assert included_by_id[deleted_admin["id"]]["display_name"] == "Deleted User"
    assert included_by_id[deleted_admin["id"]]["email"] is None
    assert included_by_id[deleted_admin["id"]]["phone"] is None
    assert included_by_id[deleted_admin["id"]]["deleted_at"] is not None


def test_admin_staff_list_redacts_inconsistent_deleted_states(client: TestClient):
    authenticate_admin(client)
    status_deleted_admin = create_user(
        client,
        first_name="Status",
        last_name="Deleted",
        email="staff.status.deleted@example.com",
        phone="+13125550201",
        home_city="Chicago",
        home_state="IL",
    )
    timestamp_deleted_admin = create_user(
        client,
        first_name="Timestamp",
        last_name="Deleted",
        email="staff.timestamp.deleted@example.com",
        phone="+13125550202",
        home_city="Evanston",
        home_state="IL",
    )
    for staff_user in (status_deleted_admin, timestamp_deleted_admin):
        set_user_role(staff_user["id"], "admin")

    set_user_account_status(status_deleted_admin["id"], "deleted")
    with SessionLocal() as db:
        db_timestamp_deleted_admin = db.get(
            User,
            UUID(timestamp_deleted_admin["id"]),
        )
        assert db_timestamp_deleted_admin is not None
        db_timestamp_deleted_admin.deleted_at = datetime.now(UTC)
        db.commit()

    default_response = client.get("/admin/users/staff")
    assert default_response.status_code == 200, default_response.text
    default_ids = {item["id"] for item in default_response.json()}
    assert status_deleted_admin["id"] not in default_ids
    assert timestamp_deleted_admin["id"] not in default_ids

    included_response = client.get(
        "/admin/users/staff",
        params={"include_deleted": True},
    )
    assert included_response.status_code == 200, included_response.text
    included_by_id = {item["id"]: item for item in included_response.json()}

    for staff_user in (status_deleted_admin, timestamp_deleted_admin):
        body = included_by_id[staff_user["id"]]
        assert body["display_name"] == "Deleted User"
        assert body["email"] is None
        assert body["phone"] is None
        assert body["home_city"] is None
        assert body["home_state"] is None
        assert body["email_verified"] is False
        assert body["account_status"] == "deleted"


def test_admin_staff_list_rejects_player_and_suspended_admin(
    client: TestClient,
):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.get("/admin/users/staff")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text

    suspended_admin = create_user(client)
    set_user_role(suspended_admin["id"], "admin")
    set_user_account_status(suspended_admin["id"], "suspended")
    authenticate_as(suspended_admin["id"])

    response = client.get("/admin/users/staff")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


@pytest.mark.parametrize(
    ("initial_role", "next_role"),
    [
        ("player", "admin"),
        ("admin", "player"),
    ],
)
def test_admin_user_staff_role_change_updates_role_and_audit_once(
    client: TestClient,
    initial_role: str,
    next_role: str,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    set_user_role(target["id"], initial_role)
    authenticate_as(admin["id"])

    payload = {
        "role": next_role,
        "reason": f"Change staff role from {initial_role} to {next_role}.",
        "idempotency_key": f"change-staff-role-{initial_role}-{next_role}",
    }
    response = client.post(
        f"/admin/users/{target['id']}/staff-role",
        json=payload,
    )
    repeat_response = client.post(
        f"/admin/users/{target['id']}/staff-role",
        json=payload,
    )
    different_request_response = client.post(
        f"/admin/users/{target['id']}/staff-role",
        json={
            **payload,
            "idempotency_key": (
                f"change-staff-role-{initial_role}-{next_role}-different"
            ),
        },
    )

    assert response.status_code == 200, response.text
    assert repeat_response.status_code == 200, repeat_response.text
    assert repeat_response.json() == response.json()
    assert different_request_response.status_code == 409
    assert "already has that role" in different_request_response.text
    body = response.json()
    assert body["user_id"] == target["id"]
    assert body["previous_role"] == initial_role
    assert body["role"] == next_role

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_actions = db.scalars(
            select(AdminAction).where(
                AdminAction.action_type == "change_staff_role",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        ).all()

        assert db_target is not None
        assert db_target.role == next_role
        assert len(audit_actions) == 1
        assert audit_actions[0].id == UUID(body["admin_action_id"])
        assert audit_actions[0].admin_user_id == UUID(admin["id"])
        assert audit_actions[0].reason == (
            f"Change staff role from {initial_role} to {next_role}."
        )
        assert audit_actions[0].metadata_ == {
            "before": {"role": initial_role},
            "after": {"role": next_role},
        }


def test_admin_user_staff_role_change_rejects_idempotency_request_mismatch(
    client: TestClient,
):
    authenticate_admin(client)
    target = create_user(client)
    payload = {
        "role": "admin",
        "reason": "Promote this player to admin.",
        "idempotency_key": "change-staff-role-request-mismatch",
    }

    response = client.post(
        f"/admin/users/{target['id']}/staff-role",
        json=payload,
    )
    role_mismatch_response = client.post(
        f"/admin/users/{target['id']}/staff-role",
        json={**payload, "role": "player"},
    )
    reason_mismatch_response = client.post(
        f"/admin/users/{target['id']}/staff-role",
        json={**payload, "reason": "Use the same key for another reason."},
    )

    assert response.status_code == 200, response.text
    for mismatch_response in (role_mismatch_response, reason_mismatch_response):
        assert mismatch_response.status_code == 409, mismatch_response.text
        assert mismatch_response.json()["detail"] == (
            "idempotency_key was already used for a different "
            "staff role change request."
        )

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "change_staff_role",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        assert db_target is not None
        assert db_target.role == "admin"
        assert audit_count == 1


def test_admin_user_staff_role_change_rejects_last_active_admin_demotion(
    client: TestClient,
):
    admin = authenticate_admin(client)

    response = client.post(
        f"/admin/users/{admin['id']}/staff-role",
        json={
            "role": "player",
            "reason": "This would remove the last active admin.",
            "idempotency_key": "change-staff-role-last-active-admin",
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "The last active admin cannot be demoted."

    with SessionLocal() as db:
        db_admin = db.get(User, UUID(admin["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "change_staff_role",
                AdminAction.target_user_id == UUID(admin["id"]),
            )
        )
        assert db_admin is not None
        assert db_admin.role == "admin"
        assert audit_count == 0


@pytest.mark.parametrize(
    ("account_status", "has_deleted_at", "expected_reason"),
    [
        ("pending_deletion", False, "pending deletion"),
        ("deleted", False, "Deleted accounts"),
        ("active", True, "Deleted accounts"),
    ],
)
def test_admin_user_staff_role_change_rejects_ineligible_target_without_mutation(
    client: TestClient,
    account_status: str,
    has_deleted_at: bool,
    expected_reason: str,
):
    authenticate_admin(client)
    target = create_user(client)
    set_user_account_status(target["id"], account_status)
    if has_deleted_at:
        with SessionLocal() as db:
            db_target = db.get(User, UUID(target["id"]))
            assert db_target is not None
            db_target.deleted_at = datetime.now(UTC)
            db.commit()

    response = client.post(
        f"/admin/users/{target['id']}/staff-role",
        json={
            "role": "admin",
            "reason": "This target cannot have staff changed.",
            "idempotency_key": (
                f"change-staff-role-invalid-{account_status}-{has_deleted_at}"
            ),
        },
    )

    assert response.status_code == 409, response.text
    assert expected_reason in response.json()["detail"]

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "change_staff_role",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        assert db_target is not None
        assert db_target.role == "player"
        assert audit_count == 0


def test_admin_user_staff_role_change_validates_target_reason_and_authorization(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    authenticate_as(admin["id"])

    missing_response = client.post(
        "/admin/users/00000000-0000-4000-8000-000000000000/staff-role",
        json={
            "role": "admin",
            "reason": "Change missing user staff role.",
            "idempotency_key": "change-staff-role-missing-user",
        },
    )
    assert missing_response.status_code == 404, missing_response.text
    assert missing_response.json()["detail"] == "User not found."

    unsupported_role_response = client.post(
        f"/admin/users/{target['id']}/staff-role",
        json={
            "role": "owner",
            "reason": "Unsupported staff role.",
            "idempotency_key": "change-staff-role-unsupported-role",
        },
    )
    assert unsupported_role_response.status_code == 400, unsupported_role_response.text
    assert unsupported_role_response.json()["detail"] == "role is not supported."

    blank_reason_response = client.post(
        f"/admin/users/{target['id']}/staff-role",
        json={
            "role": "admin",
            "reason": "   ",
            "idempotency_key": "change-staff-role-blank-reason",
        },
    )
    assert blank_reason_response.status_code == 400, blank_reason_response.text
    assert blank_reason_response.json()["detail"] == "reason is required."

    player = create_user(client)
    authenticate_as(player["id"])
    denied_response = client.post(
        f"/admin/users/{target['id']}/staff-role",
        json={
            "role": "admin",
            "reason": "Player must not change staff roles.",
            "idempotency_key": "change-staff-role-denied",
        },
    )
    assert denied_response.status_code == 403, denied_response.text
    assert "Admin access required" in denied_response.text


def test_admin_user_detail_returns_scoped_support_context(client: TestClient):
    admin = authenticate_admin(client)
    target = create_user(
        client,
        first_name="Detail",
        last_name="Player",
        email="detail.player@example.com",
    )
    other_user = create_user(client)
    stats = create_user_stats(
        client,
        target["id"],
        games_played_count=8,
        games_hosted_completed_count=2,
        no_show_count=1,
        late_cancel_count=3,
        host_cancel_count=1,
    )
    venue = create_venue(client, admin["id"])
    official_game = create_game(client, admin["id"], venue, title="Official Detail")
    booking = create_booking(client, target["id"], official_game["id"])
    participant = create_game_participant(
        client,
        target["id"],
        official_game["id"],
        booking["id"],
    )
    community_game = create_game(
        client,
        target["id"],
        venue,
        game_type="community",
        payment_collection_type="external_host",
        policy_mode="custom_hosted",
        host_user_id=target["id"],
        title="Community Detail",
    )

    with SessionLocal() as db:
        db_official_game = db.get(Game, UUID(official_game["id"]))
        assert db_official_game is not None
        db_official_game.host_user_id = UUID(target["id"])
        db.commit()

    owned_post = create_sub_post(client, target["id"], team_name="Owned Team")
    other_post = create_sub_post(client, other_user["id"], team_name="Request Team")
    authenticate_as(target["id"])
    request_response = client.post(
        f"/need-a-sub/posts/{other_post['id']}/requests",
        json={"sub_post_position_id": other_post["positions"][0]["id"]},
    )
    assert request_response.status_code == 201, request_response.text
    sub_request = request_response.json()

    direct_action = create_admin_action(
        client,
        admin["id"],
        target_user_id=target["id"],
        reason="Direct user support action.",
    )
    unrelated_action = create_admin_action(
        client,
        admin["id"],
        target_user_id=other_user["id"],
        reason="Unrelated user support action.",
    )

    with SessionLocal() as db:
        direct_flag = create_support_flag(
            db,
            flag_type="account_delete_partial_failure",
            source="account",
            title="Direct user flag",
            summary="Direct support follow-up.",
            target_user_id=UUID(target["id"]),
            idempotency_key=f"admin-user-detail-direct-{target['id']}",
        )
        direct_flag_id = direct_flag.id
        unrelated_flag = create_support_flag(
            db,
            flag_type="official_cancel_partial_failure",
            source="official_game",
            title="Unrelated shared game flag",
            summary="This flag belongs to a different user.",
            target_user_id=UUID(other_user["id"]),
            target_game_id=UUID(official_game["id"]),
            idempotency_key=f"admin-user-detail-unrelated-{other_user['id']}",
        )
        unrelated_flag_id = unrelated_flag.id

    authenticate_as(admin["id"])
    response = client.get(f"/admin/users/{target['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["id"] == target["id"]
    assert body["user"]["display_name"] == "Detail Player"
    assert body["stats"]["games_played_count"] == 8
    assert body["stats"]["last_calculated_at"] == stats["last_calculated_at"]
    assert [item["id"] for item in body["bookings"]] == [booking["id"]]
    assert [item["id"] for item in body["participations"]] == [participant["id"]]
    assert [item["id"] for item in body["community_games_hosted"]] == [
        community_game["id"]
    ]
    assert [item["id"] for item in body["official_host_assignments"]] == [
        official_game["id"]
    ]
    assert [item["id"] for item in body["sub_posts_owned"]] == [owned_post["id"]]
    assert [item["id"] for item in body["sub_requests_made"]] == [
        sub_request["id"]
    ]
    assert [item["id"] for item in body["audit_actions"]] == [direct_action["id"]]
    assert unrelated_action["id"] not in {
        item["id"] for item in body["audit_actions"]
    }
    assert [item["id"] for item in body["support_flags"]] == [str(direct_flag_id)]
    assert str(unrelated_flag_id) not in {
        item["id"] for item in body["support_flags"]
    }
    assert "capabilities" not in body
    assert "auth_user_id" not in body["user"]
    assert "date_of_birth" not in body["user"]
    assert "stripe_customer_id" not in body["user"]
    assert "payment_status" not in body["bookings"][0]


def test_admin_user_detail_excludes_soft_deleted_game_activity(client: TestClient):
    admin = authenticate_admin(client)
    target = create_user(
        client,
        first_name="Deleted",
        last_name="Game Activity",
        email="deleted.game.activity@example.com",
    )
    venue = create_venue(client, admin["id"])
    active_official_game = create_game(
        client,
        admin["id"],
        venue,
        title="Visible Official Detail",
    )
    active_booking = create_booking(client, target["id"], active_official_game["id"])
    active_participant = create_game_participant(
        client,
        target["id"],
        active_official_game["id"],
        active_booking["id"],
    )
    active_community_game = create_game(
        client,
        target["id"],
        venue,
        game_type="community",
        payment_collection_type="external_host",
        policy_mode="custom_hosted",
        host_user_id=target["id"],
        title="Visible Community Detail",
    )
    deleted_official_game = create_game(
        client,
        admin["id"],
        venue,
        title="Deleted Official Detail",
    )
    deleted_booking = create_booking(client, target["id"], deleted_official_game["id"])
    deleted_participant = create_game_participant(
        client,
        target["id"],
        deleted_official_game["id"],
        deleted_booking["id"],
    )
    deleted_community_starts_at = datetime.now(UTC) + timedelta(days=8)
    deleted_community_game = create_game(
        client,
        target["id"],
        venue,
        game_type="community",
        payment_collection_type="external_host",
        policy_mode="custom_hosted",
        host_user_id=target["id"],
        title="Deleted Community Detail",
        starts_at=deleted_community_starts_at.isoformat(),
        ends_at=(deleted_community_starts_at + timedelta(hours=1)).isoformat(),
    )

    with SessionLocal() as db:
        target_user_id = UUID(target["id"])
        deleted_at = datetime.now(UTC)
        db_active_official_game = db.get(Game, UUID(active_official_game["id"]))
        db_deleted_official_game = db.get(Game, UUID(deleted_official_game["id"]))
        db_deleted_community_game = db.get(Game, UUID(deleted_community_game["id"]))
        assert db_active_official_game is not None
        assert db_deleted_official_game is not None
        assert db_deleted_community_game is not None
        db_active_official_game.host_user_id = target_user_id
        db_deleted_official_game.host_user_id = target_user_id
        db_deleted_official_game.deleted_at = deleted_at
        db_deleted_community_game.deleted_at = deleted_at
        db.commit()

    authenticate_as(admin["id"])
    response = client.get(f"/admin/users/{target['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["id"] for item in body["bookings"]] == [active_booking["id"]]
    assert deleted_booking["id"] not in {item["id"] for item in body["bookings"]}
    assert [item["id"] for item in body["participations"]] == [
        active_participant["id"]
    ]
    assert deleted_participant["id"] not in {
        item["id"] for item in body["participations"]
    }
    assert [item["id"] for item in body["official_host_assignments"]] == [
        active_official_game["id"]
    ]
    assert deleted_official_game["id"] not in {
        item["id"] for item in body["official_host_assignments"]
    }
    assert [item["id"] for item in body["community_games_hosted"]] == [
        active_community_game["id"]
    ]
    assert deleted_community_game["id"] not in {
        item["id"] for item in body["community_games_hosted"]
    }


def test_admin_user_detail_preserves_deleted_user_redaction(client: TestClient):
    authenticate_admin(client)
    deleted_user = create_user(
        client,
        first_name="Should",
        last_name="Redact",
        email="should.redact@example.com",
        phone="+13125550123",
        home_city="Chicago",
        home_state="IL",
    )
    soft_delete_user(deleted_user["id"])

    response = client.get(f"/admin/users/{deleted_user['id']}")

    assert response.status_code == 200, response.text
    user = response.json()["user"]
    assert user["display_name"] == "Deleted User"
    assert user["email"] is None
    assert user["phone"] is None
    assert user["home_city"] is None
    assert user["home_state"] is None
    assert user["email_verified"] is False
    assert user["deleted_at"] is not None


def test_admin_user_detail_returns_404_for_missing_user(client: TestClient):
    authenticate_admin(client)

    response = client.get(
        "/admin/users/00000000-0000-4000-8000-000000000000"
    )

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "User not found."


def test_admin_user_detail_rejects_player(client: TestClient):
    player = create_user(client)
    target = create_user(client)
    authenticate_as(player["id"])

    response = client.get(f"/admin/users/{target['id']}")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


def test_admin_user_delete_preview_allows_active_player_without_impacts(
    client: TestClient,
):
    authenticate_admin(client)
    target = create_user(client)

    response = client.post(f"/admin/users/{target['id']}/delete-preview")
    repeat_response = client.post(f"/admin/users/{target['id']}/delete-preview")

    assert response.status_code == 200, response.text
    assert repeat_response.status_code == 200, repeat_response.text
    assert repeat_response.json() == response.json()
    body = response.json()
    assert body["user_id"] == target["id"]
    assert body["account_status"] == "active"
    assert body["role"] == "player"
    assert body["hosting_status"] == "not_eligible"
    assert body["can_delete"] is True
    assert len(body["preview_token"]) == 64
    assert body["blocking_reasons"] == []
    assert body["future_official_host_assignment_count"] == 0
    assert body["future_official_host_assignments"] == []
    assert body["future_community_hosted_game_count"] == 0
    assert body["future_community_hosted_games"] == []

    count_fields = [
        "active_future_booking_count",
        "active_future_official_booking_count",
        "active_future_participation_count",
        "active_future_guest_count",
        "active_waitlist_entry_count",
        "active_owned_sub_post_count",
        "active_sub_request_count",
        "payment_record_count",
        "refund_record_count",
        "game_credit_count",
        "saved_payment_method_count",
        "active_saved_payment_method_count",
        "active_support_flag_count",
    ]
    assert {field: body[field] for field in count_fields} == {
        field: 0 for field in count_fields
    }

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(AdminAction.target_user_id == UUID(target["id"]))
        )
        notification_count = db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == UUID(target["id"]))
        )
        assert db_target is not None
        assert db_target.account_status == "active"
        assert audit_count == 0
        assert notification_count == 0


def test_admin_user_delete_preview_reports_blocking_official_host_and_impacts(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    venue = create_venue(client, admin["id"])
    official_game = create_game(
        client,
        admin["id"],
        venue,
        title="Future Official Delete Blocker",
    )
    community_game = create_game(
        client,
        target["id"],
        venue,
        game_type="community",
        host_user_id=target["id"],
        policy_mode="custom_hosted",
        title="Future Community Hosted Impact",
    )
    past_official_game = create_game(
        client,
        admin["id"],
        venue,
        title="Past Official Host Assignment",
    )
    cancelled_official_game = create_game(
        client,
        admin["id"],
        venue,
        title="Cancelled Official Host Assignment",
    )
    now = datetime.now(UTC)

    with SessionLocal() as db:
        for game_id in (
            official_game["id"],
            past_official_game["id"],
            cancelled_official_game["id"],
        ):
            game = db.get(Game, UUID(game_id))
            assert game is not None
            game.host_user_id = UUID(target["id"])

        past = db.get(Game, UUID(past_official_game["id"]))
        assert past is not None
        past.starts_at = now - timedelta(days=2)
        past.ends_at = now - timedelta(days=2) + timedelta(hours=1)

        cancelled = db.get(Game, UUID(cancelled_official_game["id"]))
        assert cancelled is not None
        cancelled.game_status = "cancelled"
        cancelled.cancelled_at = now

        draft_community_game = db.get(Game, UUID(community_game["id"]))
        assert draft_community_game is not None
        draft_community_game.publish_status = "draft"
        draft_community_game.published_at = None
        db.commit()

    authenticate_as(admin["id"])
    response = client.post(f"/admin/users/{target['id']}/delete-preview")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["can_delete"] is False
    assert body["blocking_reasons"] == [
        "Remove the user from all future official host assignments before deletion."
    ]
    assert body["future_official_host_assignment_count"] == 1
    assert body["future_official_host_assignments"] == [
        {
            "id": official_game["id"],
            "title": "Future Official Delete Blocker",
            "game_type": "official",
            "game_status": "active",
            "starts_at": official_game["starts_at"],
            "city": venue["city"],
            "state": venue["state"],
        }
    ]
    assert body["future_community_hosted_game_count"] == 1
    assert body["future_community_hosted_games"] == [
        {
            "id": community_game["id"],
            "title": "Future Community Hosted Impact",
            "game_type": "community",
            "game_status": "active",
            "starts_at": community_game["starts_at"],
            "city": venue["city"],
            "state": venue["state"],
        }
    ]

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        db_official_game = db.get(Game, UUID(official_game["id"]))
        assert db_target is not None
        assert db_target.account_status == "active"
        assert db_official_game is not None
        assert db_official_game.host_user_id == UUID(target["id"])


def test_admin_user_delete_preview_token_changes_with_related_impact(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    venue = create_venue(client, admin["id"])
    official_game = create_game(client, admin["id"], venue)

    initial_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    assert initial_response.status_code == 200, initial_response.text
    assert initial_response.json()["active_future_booking_count"] == 0

    create_booking(client, target["id"], official_game["id"])
    authenticate_as(admin["id"])
    changed_response = client.post(f"/admin/users/{target['id']}/delete-preview")

    assert changed_response.status_code == 200, changed_response.text
    assert changed_response.json()["active_future_booking_count"] == 1
    assert (
        changed_response.json()["preview_token"]
        != initial_response.json()["preview_token"]
    )


def test_admin_user_delete_preview_protects_last_active_admin(
    client: TestClient,
):
    admin = authenticate_admin(client)

    blocked_response = client.post(f"/admin/users/{admin['id']}/delete-preview")

    assert blocked_response.status_code == 200, blocked_response.text
    assert blocked_response.json()["can_delete"] is False
    assert blocked_response.json()["blocking_reasons"] == [
        "The last active admin cannot be deleted."
    ]

    second_admin = create_user(client)
    set_user_role(second_admin["id"], "admin")
    authenticate_as(admin["id"])

    allowed_response = client.post(f"/admin/users/{admin['id']}/delete-preview")

    assert allowed_response.status_code == 200, allowed_response.text
    assert allowed_response.json()["can_delete"] is True
    assert allowed_response.json()["blocking_reasons"] == []


@pytest.mark.parametrize(
    ("account_status", "has_deleted_at", "expected_reason"),
    [
        (
            "pending_deletion",
            False,
            "Accounts pending deletion cannot be deleted by admin.",
        ),
        ("active", True, "Deleted accounts cannot be deleted again."),
        ("deleted", False, "Deleted accounts cannot be deleted again."),
    ],
)
def test_admin_user_delete_preview_reports_invalid_account_state(
    client: TestClient,
    account_status: str,
    has_deleted_at: bool,
    expected_reason: str,
):
    authenticate_admin(client)
    target = create_user(client)
    set_user_account_status(target["id"], account_status)
    if has_deleted_at:
        with SessionLocal() as db:
            db_target = db.get(User, UUID(target["id"]))
            assert db_target is not None
            db_target.deleted_at = datetime.now(UTC)
            db.commit()

    response = client.post(f"/admin/users/{target['id']}/delete-preview")

    assert response.status_code == 200, response.text
    assert response.json()["can_delete"] is False
    assert expected_reason in response.json()["blocking_reasons"]


def test_admin_user_delete_preview_reports_required_impact_counts(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    other_user = create_user(client)
    venue = create_venue(client, admin["id"])
    official_game = create_game(client, admin["id"], venue)
    waitlist_game = create_game(
        client,
        admin["id"],
        venue,
        title="Waitlist Delete Impact",
    )
    booking = create_booking(client, target["id"], official_game["id"])
    participant = create_game_participant(
        client,
        target["id"],
        official_game["id"],
        booking["id"],
    )
    create_game_participant(
        client,
        None,
        official_game["id"],
        booking["id"],
        participant_type="guest",
        guest_of_user_id=target["id"],
        guest_name="Guest User",
        guest_email="guest@example.com",
        guest_phone="+13125550101",
        display_name_snapshot="Guest User",
        roster_order=2,
    )
    create_waitlist_entry(client, target["id"], waitlist_game["id"])
    create_sub_post(client, target["id"], team_name="Delete Preview Owner")
    other_post = create_sub_post(client, other_user["id"], team_name="Needs Sub")
    authenticate_as(target["id"])
    sub_request_response = client.post(
        f"/need-a-sub/posts/{other_post['id']}/requests",
        json={"sub_post_position_id": other_post["positions"][0]["id"]},
    )
    assert sub_request_response.status_code == 201, sub_request_response.text

    payment = create_payment(
        client,
        target["id"],
        booking_id=booking["id"],
        payment_status="succeeded",
        provider_charge_id="ch_delete_preview",
        paid_at=datetime.now(UTC).isoformat(),
    )
    create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        participant_id=participant["id"],
    )
    create_user_payment_method(client, target["id"])
    with SessionLocal() as db:
        db.add(
            GameCredit(
                id=uuid4(),
                user_id=UUID(target["id"]),
                amount_cents=1200,
                remaining_cents=1200,
                currency="USD",
                credit_status="active",
                credit_reason="admin_credit",
                idempotency_key=f"delete-preview-credit-{target['id']}",
            )
        )
        create_support_flag(
            db,
            flag_type="account_delete_partial_failure",
            source="account",
            title="Delete preview support flag",
            summary="Open support flag for delete preview.",
            target_user_id=UUID(target["id"]),
            idempotency_key=f"delete-preview-flag-{target['id']}",
        )
        db.commit()

    authenticate_as(admin["id"])
    response = client.post(f"/admin/users/{target['id']}/delete-preview")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["can_delete"] is True
    assert body["active_future_booking_count"] == 1
    assert body["active_future_official_booking_count"] == 1
    assert body["active_future_participation_count"] == 1
    assert body["active_future_guest_count"] == 1
    assert body["active_waitlist_entry_count"] == 1
    assert body["active_owned_sub_post_count"] == 1
    assert body["active_sub_request_count"] == 1
    assert body["payment_record_count"] == 1
    assert body["refund_record_count"] == 1
    assert body["game_credit_count"] == 1
    assert body["saved_payment_method_count"] == 1
    assert body["active_saved_payment_method_count"] == 1
    assert body["active_support_flag_count"] == 1


def test_admin_user_delete_preview_validates_target_and_authorization(
    client: TestClient,
):
    authenticate_admin(client)
    target = create_user(client)

    missing_response = client.post(
        "/admin/users/00000000-0000-4000-8000-000000000000/delete-preview"
    )
    assert missing_response.status_code == 404, missing_response.text
    assert missing_response.json()["detail"] == "User not found."

    player = create_user(client)
    authenticate_as(player["id"])
    denied_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    assert denied_response.status_code == 403, denied_response.text
    assert "Admin access required" in denied_response.text

    suspended_admin = create_user(client)
    set_user_role(suspended_admin["id"], "admin")
    set_user_account_status(suspended_admin["id"], "suspended")
    authenticate_as(suspended_admin["id"])
    suspended_admin_response = client.post(
        f"/admin/users/{target['id']}/delete-preview"
    )
    assert suspended_admin_response.status_code == 403
    assert "Admin access required" in suspended_admin_response.text


def test_admin_user_delete_updates_account_activity_and_audit_once(
    client: TestClient,
    monkeypatch,
):
    admin = authenticate_admin(client)
    target = create_user(
        client,
        first_name="Delete",
        last_name="Target",
        email="delete.target@example.com",
    )
    other_user = create_user(client)
    community_player = create_user(client)
    community_waitlisted_user = create_user(client)
    venue = create_venue(client, admin["id"])
    official_game = create_game(client, admin["id"], venue)
    waitlist_game = create_game(
        client,
        admin["id"],
        venue,
        title="Delete Waitlist Game",
    )
    community_game = create_game(
        client,
        target["id"],
        venue,
        game_type="community",
        host_user_id=target["id"],
        policy_mode="custom_hosted",
        title="Delete Hosted Community Game",
    )
    community_booking = create_booking(
        client,
        community_player["id"],
        community_game["id"],
    )
    community_participant = create_game_participant(
        client,
        community_player["id"],
        community_game["id"],
        community_booking["id"],
        display_name_snapshot="Community Player",
    )
    community_waitlist_entry = create_waitlist_entry(
        client,
        community_waitlisted_user["id"],
        community_game["id"],
    )
    community_chat = create_game_chat(client, community_game["id"])
    booking = create_booking(client, target["id"], official_game["id"])
    participant = create_game_participant(
        client,
        target["id"],
        official_game["id"],
        booking["id"],
    )
    guest = create_game_participant(
        client,
        None,
        official_game["id"],
        booking["id"],
        participant_type="guest",
        guest_of_user_id=target["id"],
        guest_name="Delete Target Guest",
        guest_email="delete.target.guest@example.com",
        guest_phone="+13125550155",
        display_name_snapshot="Delete Target Guest",
        roster_order=2,
    )
    waitlist_entry = create_waitlist_entry(client, target["id"], waitlist_game["id"])
    owned_sub_post = create_sub_post(
        client,
        target["id"],
        team_name="Delete Target Owned Sub Post",
    )
    other_sub_post = create_sub_post(
        client,
        other_user["id"],
        team_name="Delete Target Request Sub Post",
    )
    authenticate_as(target["id"])
    sub_request_response = client.post(
        f"/need-a-sub/posts/{other_sub_post['id']}/requests",
        json={"sub_post_position_id": other_sub_post["positions"][0]["id"]},
    )
    assert sub_request_response.status_code == 201, sub_request_response.text
    sub_request = sub_request_response.json()
    payment_method = create_user_payment_method(client, target["id"])
    deleted_auth_user_ids: list[str] = []
    detached_payment_method_ids: list[str] = []
    monkeypatch.setattr(
        "backend.services.admin_user_delete_service.delete_firebase_user",
        deleted_auth_user_ids.append,
    )
    monkeypatch.setattr(
        "backend.services.account_deletion_service.detach_payment_method",
        detached_payment_method_ids.append,
    )

    authenticate_as(admin["id"])
    preview_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    assert preview_response.status_code == 200, preview_response.text
    assert preview_response.json()["can_delete"] is True

    payload = {
        "preview_token": preview_response.json()["preview_token"],
        "reason": "Confirmed admin account deletion request.",
        "idempotency_key": "delete-user-success-once",
    }
    response = client.post(f"/admin/users/{target['id']}/delete", json=payload)
    repeat_response = client.post(f"/admin/users/{target['id']}/delete", json=payload)
    reason_mismatch_response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            **payload,
            "reason": "Reuse the same key for another deletion reason.",
        },
    )
    preview_mismatch_response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            **payload,
            "preview_token": "1" * 64,
        },
    )
    different_request_response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            **payload,
            "idempotency_key": "delete-user-different-request",
        },
    )

    assert response.status_code == 200, response.text
    assert repeat_response.status_code == 200, repeat_response.text
    assert repeat_response.json() == response.json()
    for mismatch_response in (reason_mismatch_response, preview_mismatch_response):
        assert mismatch_response.status_code == 409, mismatch_response.text
        assert mismatch_response.json()["detail"] == (
            "idempotency_key was already used for a different "
            "account deletion request."
        )
    assert different_request_response.status_code == 409
    assert "Deleted accounts" in different_request_response.text
    body = response.json()
    assert body["user_id"] == target["id"]
    assert body["account_status"] == "deleted"
    assert body["deleted_at"] is not None
    assert deleted_auth_user_ids == [target["auth_user_id"]]
    assert detached_payment_method_ids == [payment_method["stripe_payment_method_id"]]

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        db_booking = db.get(Booking, UUID(booking["id"]))
        db_participant = db.get(GameParticipant, UUID(participant["id"]))
        db_guest = db.get(GameParticipant, UUID(guest["id"]))
        db_waitlist_entry = db.get(WaitlistEntry, UUID(waitlist_entry["id"]))
        db_community_game = db.get(Game, UUID(community_game["id"]))
        db_community_booking = db.get(Booking, UUID(community_booking["id"]))
        db_community_participant = db.get(
            GameParticipant,
            UUID(community_participant["id"]),
        )
        db_community_waitlist_entry = db.get(
            WaitlistEntry,
            UUID(community_waitlist_entry["id"]),
        )
        db_community_chat = db.get(GameChat, UUID(community_chat["id"]))
        db_owned_sub_post = db.get(SubPost, UUID(owned_sub_post["id"]))
        db_sub_request = db.get(SubPostRequest, UUID(sub_request["id"]))
        db_payment_method = db.get(UserPaymentMethod, UUID(payment_method["id"]))
        audit_actions = db.scalars(
            select(AdminAction).where(
                AdminAction.action_type == "delete_user",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        ).all()
        notification_count = db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == UUID(target["id"]))
        )
        community_player_notifications = db.scalars(
            select(Notification).where(
                Notification.user_id == UUID(community_player["id"]),
                Notification.related_game_id == UUID(community_game["id"]),
                Notification.notification_type == "game_cancelled",
            )
        ).all()
        community_game_history = db.scalar(
            select(GameStatusHistory).where(
                GameStatusHistory.game_id == UUID(community_game["id"]),
                GameStatusHistory.new_game_status == "cancelled",
            )
        )

        assert db_target is not None
        assert db_target.account_status == "deleted"
        assert db_target.deleted_at is not None
        assert db_target.auth_user_id is None
        assert db_target.email is None
        assert db_target.phone is None
        assert db_target.first_name == "Deleted"
        assert db_target.last_name == "User"
        assert db_target.hosting_status == "not_eligible"
        assert db_target.stripe_customer_id is None
        assert db_booking is not None
        assert db_booking.booking_status == "cancelled"
        assert db_booking.cancelled_at is not None
        assert db_participant is not None
        assert db_participant.participant_status == "cancelled"
        assert db_participant.display_name_snapshot == "Deleted User"
        assert db_guest is not None
        assert db_guest.participant_status == "cancelled"
        assert db_guest.guest_name == "Deleted Guest"
        assert db_guest.guest_email is None
        assert db_guest.guest_phone is None
        assert db_guest.display_name_snapshot == "Deleted Guest"
        assert db_waitlist_entry is not None
        assert db_waitlist_entry.waitlist_status == "cancelled"
        assert db_community_game is not None
        assert db_community_game.game_status == "cancelled"
        assert db_community_game.cancel_reason == "Host account deleted."
        assert db_community_game.completed_at is None
        assert db_community_game.completed_by_user_id is None
        assert db_community_booking is not None
        assert db_community_booking.booking_status == "cancelled"
        assert db_community_booking.cancel_reason == "host_cancelled"
        assert db_community_participant is not None
        assert db_community_participant.participant_status == "cancelled"
        assert db_community_participant.cancellation_type == "host_cancelled"
        assert db_community_waitlist_entry is not None
        assert db_community_waitlist_entry.waitlist_status == "cancelled"
        assert db_community_chat is not None
        assert db_community_chat.chat_status == "closed"
        assert community_game_history is not None
        assert community_game_history.change_source == "system"
        assert len(community_player_notifications) == 1
        assert db_owned_sub_post is not None
        assert db_owned_sub_post.post_status == "cancelled"
        assert db_owned_sub_post.canceled_at is not None
        assert db_sub_request is not None
        assert db_sub_request.request_status == "canceled_by_player"
        assert db_sub_request.canceled_at is not None
        assert db_payment_method is None
        assert notification_count == 0
        assert len(audit_actions) == 1
        assert audit_actions[0].id == UUID(body["admin_action_id"])
        assert audit_actions[0].admin_user_id == UUID(admin["id"])
        assert audit_actions[0].reason == "Confirmed admin account deletion request."
        assert audit_actions[0].metadata_["before"] == {
            "account_status": "active",
            "hosting_status": "not_eligible",
            "role": "player",
            "had_auth_link": True,
        }
        assert audit_actions[0].metadata_["after"]["account_status"] == "deleted"
        assert audit_actions[0].metadata_["after"]["auth_unlinked"] is True
        assert audit_actions[0].metadata_["reviewed"] == {
            "preview_snapshot_hash": payload["preview_token"],
            "future_official_host_assignment_count": 0,
            "future_community_hosted_game_count": 1,
            "active_future_booking_count": 1,
            "active_future_official_booking_count": 1,
            "active_future_participation_count": 1,
            "active_future_guest_count": 1,
            "active_waitlist_entry_count": 1,
            "active_owned_sub_post_count": 1,
            "active_sub_request_count": 1,
            "payment_record_count": 0,
            "refund_record_count": 0,
            "game_credit_count": 0,
            "saved_payment_method_count": 1,
            "active_saved_payment_method_count": 1,
            "active_support_flag_count": 0,
        }


def test_admin_user_delete_cancels_buyer_booking_without_active_participant(
    client: TestClient,
    monkeypatch,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    venue = create_venue(client, admin["id"])
    official_game = create_game(client, admin["id"], venue)
    booking = create_booking(client, target["id"], official_game["id"])
    monkeypatch.setattr(
        "backend.services.admin_user_delete_service.delete_firebase_user",
        lambda _auth_user_id: None,
    )

    preview_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    assert preview_response.status_code == 200, preview_response.text
    assert preview_response.json()["active_future_booking_count"] == 1

    response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Delete buyer booking without an active participant.",
            "idempotency_key": "delete-user-orphan-buyer-booking",
        },
    )

    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        db_booking = db.get(Booking, UUID(booking["id"]))
        assert db_booking is not None
        assert db_booking.booking_status == "cancelled"
        assert db_booking.cancelled_at is not None
        assert db_booking.cancel_reason == "Account deleted."


def test_admin_user_delete_cancels_hosted_game_before_waitlist_promotion(
    client: TestClient,
    monkeypatch,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    waitlisted_user = create_user(client)
    venue = create_venue(client, admin["id"])
    community_game = create_game(
        client,
        target["id"],
        venue,
        game_type="community",
        host_user_id=target["id"],
        policy_mode="custom_hosted",
        title="Delete Host Before Promotion",
    )
    host_booking = create_booking(
        client,
        target["id"],
        community_game["id"],
        payment_status="not_required",
    )
    create_game_participant(
        client,
        target["id"],
        community_game["id"],
        host_booking["id"],
        participant_type="host",
    )
    waitlist_booking = create_booking(
        client,
        waitlisted_user["id"],
        community_game["id"],
        booking_status="waitlisted",
        payment_status="unpaid",
    )
    waitlist_participant = create_game_participant(
        client,
        waitlisted_user["id"],
        community_game["id"],
        waitlist_booking["id"],
        participant_status="waitlisted",
        attendance_status="not_applicable",
        confirmed_at=None,
    )
    waitlist_entry = create_waitlist_entry(
        client,
        waitlisted_user["id"],
        community_game["id"],
        promoted_booking_id=None,
    )
    monkeypatch.setattr(
        "backend.services.admin_user_delete_service.delete_firebase_user",
        lambda _auth_user_id: None,
    )

    preview_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    assert preview_response.status_code == 200, preview_response.text
    response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Cancel hosted game before any waitlist promotion.",
            "idempotency_key": "delete-host-before-waitlist-promotion",
        },
    )

    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        db_game = db.get(Game, UUID(community_game["id"]))
        db_waitlist_entry = db.get(WaitlistEntry, UUID(waitlist_entry["id"]))
        db_waitlist_participant = db.get(
            GameParticipant,
            UUID(waitlist_participant["id"]),
        )
        promotion_count = db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == UUID(waitlisted_user["id"]),
                Notification.related_game_id == UUID(community_game["id"]),
                Notification.notification_type == "waitlist_promoted",
            )
        )
        assert db_game is not None
        assert db_game.game_status == "cancelled"
        assert db_waitlist_entry is not None
        assert db_waitlist_entry.waitlist_status == "cancelled"
        assert db_waitlist_participant is not None
        assert db_waitlist_participant.participant_status == "cancelled"
        assert promotion_count == 0


def test_admin_user_delete_emits_need_a_sub_owner_cancellation_notification(
    client: TestClient,
    monkeypatch,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    requester = create_user(client)
    sub_post = create_sub_post(
        client,
        target["id"],
        team_name="Deleted Owner Notification",
    )
    authenticate_as(requester["id"])
    request_response = client.post(
        f"/need-a-sub/posts/{sub_post['id']}/requests",
        json={"sub_post_position_id": sub_post["positions"][0]["id"]},
    )
    assert request_response.status_code == 201, request_response.text
    sub_request = request_response.json()
    authenticate_as(target["id"])
    accept_response = client.patch(
        f"/need-a-sub/requests/{sub_request['id']}/accept"
    )
    assert accept_response.status_code == 200, accept_response.text
    chat_response = client.post(
        f"/need-a-sub/posts/{sub_post['id']}/chat",
        json={},
    )
    assert chat_response.status_code == 200, chat_response.text
    authenticate_as(requester["id"])
    message_response = client.post(
        f"/need-a-sub/posts/{sub_post['id']}/chat/messages",
        json={
            "chat_id": chat_response.json()["id"],
            "message_body": "This notification should close with account deletion.",
        },
    )
    assert message_response.status_code == 201, message_response.text

    with SessionLocal() as db:
        chat_notification = db.scalar(
            select(Notification).where(
                Notification.user_id == UUID(target["id"]),
                Notification.related_sub_post_id == UUID(sub_post["id"]),
                Notification.notification_type == "sub_chat_message",
            )
        )
        assert chat_notification is not None
        chat_notification_id = chat_notification.id

    monkeypatch.setattr(
        "backend.services.admin_user_delete_service.delete_firebase_user",
        lambda _auth_user_id: None,
    )

    authenticate_as(admin["id"])
    preview_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Cancel owned Need a Sub activity.",
            "idempotency_key": "delete-owner-need-a-sub-notification",
        },
    )

    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        db_request = db.get(SubPostRequest, UUID(sub_request["id"]))
        db_chat = db.get(SubPostChat, UUID(chat_response.json()["id"]))
        notification = db.scalar(
            select(Notification).where(
                Notification.user_id == UUID(requester["id"]),
                Notification.related_sub_post_id == UUID(sub_post["id"]),
                Notification.related_sub_post_request_id == UUID(sub_request["id"]),
                Notification.notification_type == "sub_post_canceled",
            )
        )
        db_chat_notification = db.get(Notification, chat_notification_id)
        assert db_request is not None
        assert db_request.request_status == "canceled_by_owner"
        assert db_chat is not None
        assert db_chat.chat_status == "closed"
        assert db_chat.closed_at is not None
        assert notification is not None
        assert db_chat_notification is not None
        assert db_chat_notification.is_read is True


def test_admin_user_delete_promotes_need_a_sub_waitlist_with_notifications(
    client: TestClient,
    monkeypatch,
):
    admin = authenticate_admin(client)
    owner = create_user(client)
    target = create_user(client)
    waitlisted_user = create_user(client)
    sub_post = create_sub_post(
        client,
        owner["id"],
        team_name="Deleted Requester Promotion",
    )

    authenticate_as(target["id"])
    target_response = client.post(
        f"/need-a-sub/posts/{sub_post['id']}/requests",
        json={"sub_post_position_id": sub_post["positions"][0]["id"]},
    )
    assert target_response.status_code == 201, target_response.text
    target_request = target_response.json()

    authenticate_as(waitlisted_user["id"])
    waitlisted_response = client.post(
        f"/need-a-sub/posts/{sub_post['id']}/requests",
        json={"sub_post_position_id": sub_post["positions"][0]["id"]},
    )
    assert waitlisted_response.status_code == 201, waitlisted_response.text
    assert waitlisted_response.json()["request_status"] == "sub_waitlist"
    waitlisted_request = waitlisted_response.json()

    monkeypatch.setattr(
        "backend.services.admin_user_delete_service.delete_firebase_user",
        lambda _auth_user_id: None,
    )
    authenticate_as(admin["id"])
    preview_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Cancel requester and promote the next player.",
            "idempotency_key": "delete-requester-promote-sub-waitlist",
        },
    )

    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        db_target_request = db.get(SubPostRequest, UUID(target_request["id"]))
        db_waitlisted_request = db.get(
            SubPostRequest,
            UUID(waitlisted_request["id"]),
        )
        requester_notification = db.scalar(
            select(Notification).where(
                Notification.user_id == UUID(waitlisted_user["id"]),
                Notification.related_sub_post_request_id
                == UUID(waitlisted_request["id"]),
                Notification.notification_type
                == "sub_waitlist_promoted_to_pending",
            )
        )
        owner_notification = db.scalar(
            select(Notification).where(
                Notification.user_id == UUID(owner["id"]),
                Notification.related_sub_post_request_id
                == UUID(waitlisted_request["id"]),
                Notification.notification_type == "sub_request_received",
            )
        )
        assert db_target_request is not None
        assert db_target_request.request_status == "canceled_by_player"
        assert db_waitlisted_request is not None
        assert db_waitlisted_request.request_status == "pending"
        assert requester_notification is not None
        assert owner_notification is not None


def test_admin_user_delete_rolls_back_when_firebase_delete_fails(
    client: TestClient,
    monkeypatch,
):
    authenticate_admin(client)
    target = create_user(client)
    preview_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    assert preview_response.status_code == 200, preview_response.text

    def fail_firebase_delete(auth_user_id: str) -> None:
        assert auth_user_id == target["auth_user_id"]
        raise RuntimeError("Firebase delete failed")

    monkeypatch.setattr(
        "backend.services.admin_user_delete_service.delete_firebase_user",
        fail_firebase_delete,
    )
    response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "This deletion should roll back.",
            "idempotency_key": "delete-user-firebase-failure",
        },
    )

    assert response.status_code == 502, response.text
    assert response.json()["detail"] == (
        "Firebase could not delete this account. Please try again."
    )

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "delete_user",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        support_flag_count = db.scalar(
            select(func.count())
            .select_from(SupportFlag)
            .where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == UUID(target["id"]),
            )
        )
        assert db_target is not None
        assert db_target.account_status == "active"
        assert db_target.auth_user_id == target["auth_user_id"]
        assert db_target.deleted_at is None
        assert audit_count == 0
        assert support_flag_count == 0


def test_admin_user_delete_records_partial_failure_when_firebase_restore_fails(
    client: TestClient,
    monkeypatch,
):
    authenticate_admin(client)
    target = create_user(client)
    preview_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    assert preview_response.status_code == 200, preview_response.text

    def fail_firebase_delete(auth_user_id: str) -> None:
        assert auth_user_id == target["auth_user_id"]
        raise RuntimeError("Firebase delete failed")

    monkeypatch.setattr(
        "backend.services.admin_user_delete_service.delete_firebase_user",
        fail_firebase_delete,
    )
    original_commit = Session.commit
    commit_count = 0

    def fail_restore_commit(db_session: Session) -> None:
        nonlocal commit_count
        commit_count += 1
        if commit_count == 2:
            raise SQLAlchemyError("forced admin delete restore failure")
        original_commit(db_session)

    monkeypatch.setattr(Session, "commit", fail_restore_commit)
    response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Force restore failure after Firebase failure.",
            "idempotency_key": "delete-user-firebase-restore-failure",
        },
    )

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == (
        "Firebase deletion failed, and app account restoration requires "
        "support follow-up."
    )

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        support_flag = db.scalar(
            select(SupportFlag).where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == UUID(target["id"]),
            )
        )
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "delete_user",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        assert db_target is not None
        assert db_target.account_status == "pending_deletion"
        assert db_target.auth_user_id == target["auth_user_id"]
        assert db_target.deleted_at is None
        assert support_flag is not None
        assert support_flag.flag_status == "open"
        assert support_flag.severity == "critical"
        assert support_flag.metadata_ == {
            "auth_identity_deleted": False,
            "app_cleanup_completed": False,
            "restore_failed": True,
            "previous_account_status": "active",
        }
        assert audit_count == 0


def test_admin_user_delete_records_partial_failure_after_database_commit_error(
    client: TestClient,
    monkeypatch,
):
    authenticate_admin(client)
    target = create_user(client)
    preview_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    assert preview_response.status_code == 200, preview_response.text

    deleted_auth_user_ids: list[str] = []
    monkeypatch.setattr(
        "backend.services.admin_user_delete_service.delete_firebase_user",
        deleted_auth_user_ids.append,
    )
    original_commit = Session.commit
    commit_count = 0

    def fail_final_commit(db_session: Session) -> None:
        nonlocal commit_count
        commit_count += 1
        if commit_count == 4:
            raise IntegrityError("forced admin delete failure", {}, RuntimeError())
        original_commit(db_session)

    monkeypatch.setattr(Session, "commit", fail_final_commit)
    response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Force a database failure after Firebase deletion.",
            "idempotency_key": "delete-user-database-failure",
        },
    )

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == (
        "Firebase deletion succeeded, but app account cleanup requires "
        "support follow-up."
    )
    assert deleted_auth_user_ids == [target["auth_user_id"]]

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        support_flag = db.scalar(
            select(SupportFlag).where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == UUID(target["id"]),
            )
        )
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "delete_user",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        assert db_target is not None
        assert db_target.account_status == "pending_deletion"
        assert db_target.auth_user_id is None
        assert db_target.deleted_at is None
        assert support_flag is not None
        assert support_flag.severity == "critical"
        assert support_flag.metadata_ == {
            "auth_identity_deleted": True,
            "app_cleanup_completed": False,
        }
        assert audit_count == 0


def test_admin_user_delete_records_partial_failure_after_database_service_error(
    client: TestClient,
    monkeypatch,
):
    authenticate_admin(client)
    target = create_user(client)
    preview_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    assert preview_response.status_code == 200, preview_response.text

    deleted_auth_user_ids: list[str] = []
    monkeypatch.setattr(
        "backend.services.admin_user_delete_service.delete_firebase_user",
        deleted_auth_user_ids.append,
    )
    original_commit = Session.commit
    commit_count = 0

    def fail_final_commit(db_session: Session) -> None:
        nonlocal commit_count
        commit_count += 1
        if commit_count == 4:
            raise SQLAlchemyError("forced admin delete database outage")
        original_commit(db_session)

    monkeypatch.setattr(Session, "commit", fail_final_commit)
    response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Force database recovery after Firebase deletion.",
            "idempotency_key": "delete-user-database-service-failure",
        },
    )

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == (
        "Firebase deletion succeeded, but app account cleanup requires "
        "support follow-up."
    )
    assert deleted_auth_user_ids == [target["auth_user_id"]]

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        support_flag = db.scalar(
            select(SupportFlag).where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == UUID(target["id"]),
            )
        )
        assert db_target is not None
        assert db_target.account_status == "pending_deletion"
        assert db_target.auth_user_id is None
        assert db_target.deleted_at is None
        assert support_flag is not None
        assert support_flag.flag_status == "open"
        assert support_flag.severity == "critical"
        assert support_flag.metadata_ == {
            "auth_identity_deleted": True,
            "app_cleanup_completed": False,
        }


def test_admin_user_delete_records_partial_failure_when_cleanup_execution_raises(
    client: TestClient,
    monkeypatch,
):
    authenticate_admin(client)
    target = create_user(client)
    preview_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    assert preview_response.status_code == 200, preview_response.text
    monkeypatch.setattr(
        "backend.services.admin_user_delete_service.delete_firebase_user",
        lambda _auth_user_id: None,
    )

    def fail_cleanup(*_args, **_kwargs):
        raise RuntimeError("forced admin cleanup execution failure")

    monkeypatch.setattr(
        "backend.services.admin_user_delete_service.cancel_future_user_activity",
        fail_cleanup,
    )

    response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Force cleanup execution recovery.",
            "idempotency_key": "delete-user-cleanup-execution-failure",
        },
    )

    assert response.status_code == 503, response.text
    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        support_flag = db.scalar(
            select(SupportFlag).where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == UUID(target["id"]),
            )
        )
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "delete_user",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        assert db_target is not None
        assert db_target.account_status == "pending_deletion"
        assert db_target.auth_user_id is None
        assert support_flag is not None
        assert support_flag.metadata_["failure_type"] == (
            "app_cleanup_execution_error"
        )
        assert audit_count == 0


def test_admin_user_delete_records_partial_failure_when_saved_card_detach_fails(
    client: TestClient,
    monkeypatch,
):
    authenticate_admin(client)
    target = create_user(client)
    payment_method = create_user_payment_method(client, target["id"])
    preview_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    assert preview_response.status_code == 200, preview_response.text

    deleted_auth_user_ids: list[str] = []
    monkeypatch.setattr(
        "backend.services.admin_user_delete_service.delete_firebase_user",
        deleted_auth_user_ids.append,
    )

    def fail_detach_payment_method(stripe_payment_method_id: str) -> None:
        assert stripe_payment_method_id == payment_method["stripe_payment_method_id"]
        raise RuntimeError("Stripe detach failed")

    monkeypatch.setattr(
        "backend.services.account_deletion_service.detach_payment_method",
        fail_detach_payment_method,
    )

    response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Force saved-card cleanup failure after Firebase deletion.",
            "idempotency_key": "delete-user-saved-card-cleanup-failure",
        },
    )

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == (
        "Firebase deletion succeeded, but app account cleanup requires "
        "support follow-up."
    )
    assert deleted_auth_user_ids == [target["auth_user_id"]]

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        db_payment_method = db.get(UserPaymentMethod, UUID(payment_method["id"]))
        support_flag = db.scalar(
            select(SupportFlag).where(
                SupportFlag.flag_type == "account_delete_partial_failure",
                SupportFlag.target_user_id == UUID(target["id"]),
            )
        )
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "delete_user",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        assert db_target is not None
        assert db_target.account_status == "pending_deletion"
        assert db_target.auth_user_id is None
        assert db_target.deleted_at is None
        assert db_payment_method is not None
        assert db_payment_method.method_status == "active"
        assert support_flag is not None
        assert support_flag.flag_status == "open"
        assert support_flag.severity == "critical"
        assert support_flag.metadata_ == {
            "auth_identity_deleted": True,
            "app_cleanup_completed": False,
            "saved_payment_method_cleanup_failed": True,
            "saved_payment_method_failure_count": 1,
            "failed_saved_payment_method_ids": [payment_method["id"]],
            "detached_saved_payment_method_ids": [],
            "failure_types": ["stripe_detach_error"],
        }
        assert audit_count == 0


def test_admin_user_delete_rejects_stale_preview_without_mutation(
    client: TestClient,
):
    authenticate_admin(client)
    target = create_user(client)
    preview_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    assert preview_response.status_code == 200, preview_response.text

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        assert db_target is not None
        db_target.updated_at = datetime.now(UTC) + timedelta(seconds=1)
        db.commit()

    response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "This preview should now be stale.",
            "idempotency_key": "delete-user-stale-preview",
        },
    )

    assert response.status_code == 409, response.text
    assert "preview is stale" in response.text

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "delete_user",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        assert db_target is not None
        assert db_target.account_status == "active"
        assert db_target.deleted_at is None
        assert audit_count == 0


def test_admin_user_delete_rejects_official_host_and_logs_attempt(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    with SessionLocal() as db:
        db_game = db.get(Game, UUID(game["id"]))
        assert db_game is not None
        db_game.host_user_id = UUID(target["id"])
        db.commit()

    authenticate_as(admin["id"])
    preview_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    assert preview_response.status_code == 200, preview_response.text
    assert preview_response.json()["can_delete"] is False

    response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Attempting delete for future official host.",
            "idempotency_key": "delete-user-official-host-blocked",
        },
    )

    assert response.status_code == 409, response.text
    assert "official host assignments" in response.text

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        rejected_attempts = db.scalars(
            select(AdminRejectedAttempt).where(
                AdminRejectedAttempt.attempt_type == "delete_user_rejected",
                AdminRejectedAttempt.target_user_id == UUID(target["id"]),
            )
        ).all()
        assert db_target is not None
        assert db_target.account_status == "active"
        assert db_target.deleted_at is None
        assert len(rejected_attempts) == 1
        assert rejected_attempts[0].route_path == "/admin/users/{user_id}/delete"
        assert rejected_attempts[0].metadata_["reason_codes"] == [
            "future_official_host"
        ]
        assert rejected_attempts[0].metadata_[
            "future_official_host_assignment_count"
        ] == 1


def test_admin_user_delete_rejects_last_active_admin_and_logs_attempt(
    client: TestClient,
):
    admin = authenticate_admin(client)
    preview_response = client.post(f"/admin/users/{admin['id']}/delete-preview")
    assert preview_response.status_code == 200, preview_response.text
    assert preview_response.json()["can_delete"] is False

    response = client.post(
        f"/admin/users/{admin['id']}/delete",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Attempting last admin delete.",
            "idempotency_key": "delete-user-last-active-admin",
        },
    )

    assert response.status_code == 409, response.text
    assert "last active admin" in response.text

    with SessionLocal() as db:
        db_admin = db.get(User, UUID(admin["id"]))
        rejected_attempt = db.scalar(
            select(AdminRejectedAttempt).where(
                AdminRejectedAttempt.attempt_type == "delete_user_rejected",
                AdminRejectedAttempt.target_user_id == UUID(admin["id"]),
            )
        )
        assert db_admin is not None
        assert db_admin.account_status == "active"
        assert db_admin.deleted_at is None
        assert rejected_attempt is not None
        assert rejected_attempt.metadata_["reason_codes"] == ["last_active_admin"]


@pytest.mark.parametrize(
    ("account_status", "has_deleted_at", "expected_reason"),
    [
        (
            "pending_deletion",
            False,
            "Accounts pending deletion cannot be deleted by admin.",
        ),
        ("active", True, "Deleted accounts cannot be deleted again."),
        ("deleted", False, "Deleted accounts cannot be deleted again."),
    ],
)
def test_admin_user_delete_rejects_invalid_state_without_mutation(
    client: TestClient,
    account_status: str,
    has_deleted_at: bool,
    expected_reason: str,
):
    authenticate_admin(client)
    target = create_user(client)
    set_user_account_status(target["id"], account_status)
    if has_deleted_at:
        with SessionLocal() as db:
            db_target = db.get(User, UUID(target["id"]))
            assert db_target is not None
            db_target.deleted_at = datetime.now(UTC)
            db.commit()

    response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": "0" * 64,
            "reason": "This target cannot be deleted by admin.",
            "idempotency_key": (
                f"delete-user-invalid-{account_status}-{has_deleted_at}"
            ),
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == expected_reason

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "delete_user",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        assert db_target is not None
        assert audit_count == 0


def test_admin_user_delete_validates_target_reason_and_authorization(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    preview_response = client.post(f"/admin/users/{target['id']}/delete-preview")
    assert preview_response.status_code == 200, preview_response.text
    preview_token = preview_response.json()["preview_token"]

    missing_response = client.post(
        "/admin/users/00000000-0000-4000-8000-000000000000/delete",
        json={
            "preview_token": preview_token,
            "reason": "Delete a missing user.",
            "idempotency_key": "delete-user-missing-user",
        },
    )
    assert missing_response.status_code == 404, missing_response.text
    assert missing_response.json()["detail"] == "User not found."

    blank_reason_response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": preview_token,
            "reason": "   ",
            "idempotency_key": "delete-user-blank-reason",
        },
    )
    assert blank_reason_response.status_code == 400, blank_reason_response.text
    assert blank_reason_response.json()["detail"] == "reason is required."

    player = create_user(client)
    authenticate_as(player["id"])
    denied_response = client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": preview_token,
            "reason": "Player must not delete users.",
            "idempotency_key": "delete-user-denied",
        },
    )
    assert denied_response.status_code == 403, denied_response.text
    assert "Admin access required" in denied_response.text


def test_admin_user_suspension_preview_allows_active_player_without_blockers(
    client: TestClient,
):
    authenticate_admin(client)
    target = create_user(client)

    response = client.post(
        f"/admin/users/{target['id']}/suspension-preview"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user_id"] == target["id"]
    assert body["account_status"] == "active"
    assert body["role"] == "player"
    assert body["can_suspend"] is True
    assert len(body["preview_token"]) == 64
    assert body["blocking_reasons"] == []
    assert body["future_official_host_assignment_count"] == 0
    assert body["future_official_host_assignments"] == []


def test_admin_user_suspension_preview_reports_only_blocking_official_hosts(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    venue = create_venue(client, admin["id"])
    blocking_game = create_game(
        client,
        admin["id"],
        venue,
        title="Future Official Host Assignment",
    )
    past_game = create_game(
        client,
        admin["id"],
        venue,
        title="Past Official Host Assignment",
    )
    cancelled_game = create_game(
        client,
        admin["id"],
        venue,
        title="Cancelled Official Host Assignment",
    )
    now = datetime.now(UTC)

    with SessionLocal() as db:
        for game_id in (
            blocking_game["id"],
            past_game["id"],
            cancelled_game["id"],
        ):
            game = db.get(Game, UUID(game_id))
            assert game is not None
            game.host_user_id = UUID(target["id"])

        past = db.get(Game, UUID(past_game["id"]))
        assert past is not None
        past.starts_at = now - timedelta(days=2)
        past.ends_at = now - timedelta(days=2) + timedelta(hours=1)

        cancelled = db.get(Game, UUID(cancelled_game["id"]))
        assert cancelled is not None
        cancelled.game_status = "cancelled"
        cancelled.cancelled_at = now
        db.commit()

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/users/{target['id']}/suspension-preview"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["can_suspend"] is False
    assert body["blocking_reasons"] == [
        "Remove the user from all future official host assignments before suspension."
    ]
    assert body["future_official_host_assignment_count"] == 1
    assert body["future_official_host_assignments"] == [
        {
            "id": blocking_game["id"],
            "title": "Future Official Host Assignment",
            "game_status": "active",
            "starts_at": blocking_game["starts_at"],
            "city": venue["city"],
            "state": venue["state"],
        }
    ]

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        db_blocking_game = db.get(Game, UUID(blocking_game["id"]))
        assert db_target is not None
        assert db_blocking_game is not None
        assert db_target.account_status == "active"
        assert db_blocking_game.host_user_id == UUID(target["id"])


def test_admin_user_suspension_preview_protects_last_active_admin(
    client: TestClient,
):
    admin = authenticate_admin(client)

    blocked_response = client.post(
        f"/admin/users/{admin['id']}/suspension-preview"
    )

    assert blocked_response.status_code == 200, blocked_response.text
    assert blocked_response.json()["can_suspend"] is False
    assert blocked_response.json()["blocking_reasons"] == [
        "The last active admin cannot be suspended."
    ]

    second_admin = create_user(client)
    set_user_role(second_admin["id"], "admin")
    authenticate_as(admin["id"])

    allowed_response = client.post(
        f"/admin/users/{admin['id']}/suspension-preview"
    )

    assert allowed_response.status_code == 200, allowed_response.text
    assert allowed_response.json()["can_suspend"] is True
    assert allowed_response.json()["blocking_reasons"] == []


@pytest.mark.parametrize(
    ("account_status", "expected_reason"),
    [
        ("suspended", "This account is already suspended."),
        (
            "pending_deletion",
            "Accounts pending deletion cannot be suspended.",
        ),
        ("deleted", "Deleted accounts cannot be suspended."),
    ],
)
def test_admin_user_suspension_preview_reports_invalid_account_state(
    client: TestClient,
    account_status: str,
    expected_reason: str,
):
    authenticate_admin(client)
    target = create_user(client)
    set_user_account_status(target["id"], account_status)

    response = client.post(
        f"/admin/users/{target['id']}/suspension-preview"
    )

    assert response.status_code == 200, response.text
    assert response.json()["can_suspend"] is False
    assert response.json()["blocking_reasons"] == [expected_reason]


def test_admin_user_suspension_preview_returns_404_for_missing_user(
    client: TestClient,
):
    authenticate_admin(client)

    response = client.post(
        "/admin/users/00000000-0000-4000-8000-000000000000/suspension-preview"
    )

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "User not found."


def test_admin_user_suspension_preview_rejects_unauthorized_staff(
    client: TestClient,
):
    target = create_user(client)

    actor = create_user(client)
    authenticate_as(actor["id"])

    response = client.post(
        f"/admin/users/{target['id']}/suspension-preview"
    )

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text

    suspended_admin = create_user(client)
    set_user_role(suspended_admin["id"], "admin")
    set_user_account_status(suspended_admin["id"], "suspended")
    authenticate_as(suspended_admin["id"])

    response = client.post(
        f"/admin/users/{target['id']}/suspension-preview"
    )

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text


def test_admin_user_suspend_updates_status_audit_and_notification_once(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    preview_response = client.post(
        f"/admin/users/{target['id']}/suspension-preview"
    )
    assert preview_response.status_code == 200, preview_response.text

    payload = {
        "preview_token": preview_response.json()["preview_token"],
        "reason": "Repeated policy violations confirmed by support.",
        "idempotency_key": "suspend-user-success-once",
    }
    response = client.post(
        f"/admin/users/{target['id']}/suspend",
        json=payload,
    )
    repeat_response = client.post(
        f"/admin/users/{target['id']}/suspend",
        json=payload,
    )
    reason_mismatch_response = client.post(
        f"/admin/users/{target['id']}/suspend",
        json={**payload, "reason": "Reuse this key for another suspension reason."},
    )
    preview_mismatch_response = client.post(
        f"/admin/users/{target['id']}/suspend",
        json={**payload, "preview_token": "1" * 64},
    )
    different_request_response = client.post(
        f"/admin/users/{target['id']}/suspend",
        json={
            **payload,
            "idempotency_key": "suspend-user-different-request",
        },
    )

    assert response.status_code == 200, response.text
    assert repeat_response.status_code == 200, repeat_response.text
    assert repeat_response.json() == response.json()
    for mismatch_response in (reason_mismatch_response, preview_mismatch_response):
        assert mismatch_response.status_code == 409, mismatch_response.text
        assert mismatch_response.json()["detail"] == (
            "idempotency_key was already used for a different suspension request."
        )
    assert different_request_response.status_code == 409
    assert "already suspended" in different_request_response.text
    body = response.json()
    assert body["user_id"] == target["id"]
    assert body["account_status"] == "suspended"

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_actions = db.scalars(
            select(AdminAction).where(
                AdminAction.action_type == "suspend_user",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        ).all()
        notifications = db.scalars(
            select(Notification).where(
                Notification.user_id == UUID(target["id"]),
                Notification.notification_type == "account_security",
            )
        ).all()

        assert db_target is not None
        assert db_target.account_status == "suspended"
        assert len(audit_actions) == 1
        assert audit_actions[0].id == UUID(body["admin_action_id"])
        assert audit_actions[0].admin_user_id == UUID(admin["id"])
        assert audit_actions[0].reason == (
            "Repeated policy violations confirmed by support."
        )
        assert audit_actions[0].metadata_ == {
            "before": {"account_status": "active"},
            "after": {"account_status": "suspended"},
            "reviewed": {"preview_snapshot_hash": payload["preview_token"]},
        }
        assert len(notifications) == 1
        assert notifications[0].id == UUID(body["notification_id"])
        assert notifications[0].title == "Account suspended"
        assert notifications[0].action_key == "view_profile"
        assert audit_actions[0].target_notification_id == notifications[0].id


def test_admin_user_suspend_rejects_stale_preview_without_mutation(
    client: TestClient,
):
    authenticate_admin(client)
    target = create_user(client)
    preview_response = client.post(
        f"/admin/users/{target['id']}/suspension-preview"
    )
    assert preview_response.status_code == 200, preview_response.text

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        assert db_target is not None
        db_target.updated_at = datetime.now(UTC) + timedelta(seconds=1)
        db.commit()

    response = client.post(
        f"/admin/users/{target['id']}/suspend",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "This preview should now be stale.",
            "idempotency_key": "suspend-user-stale-preview",
        },
    )

    assert response.status_code == 409, response.text
    assert "preview is stale" in response.text

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "suspend_user",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        assert db_target is not None
        assert db_target.account_status == "active"
        assert audit_count == 0


def test_admin_user_suspend_rejects_new_official_host_and_logs_attempt(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    preview_response = client.post(
        f"/admin/users/{target['id']}/suspension-preview"
    )
    assert preview_response.status_code == 200, preview_response.text

    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    with SessionLocal() as db:
        db_game = db.get(Game, UUID(game["id"]))
        assert db_game is not None
        db_game.host_user_id = UUID(target["id"])
        db.commit()

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/users/{target['id']}/suspend",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Host assignment appeared after preview.",
            "idempotency_key": "suspend-user-host-blocked",
        },
    )

    assert response.status_code == 409, response.text
    assert "official host assignments" in response.text

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        rejected_attempts = db.scalars(
            select(AdminRejectedAttempt).where(
                AdminRejectedAttempt.attempt_type == "suspend_user_rejected",
                AdminRejectedAttempt.target_user_id == UUID(target["id"]),
            )
        ).all()
        assert db_target is not None
        assert db_target.account_status == "active"
        assert len(rejected_attempts) == 1
        assert rejected_attempts[0].rejection_mode == "domain_rejected_postload"
        assert rejected_attempts[0].route_path == (
            "/admin/users/{user_id}/suspend"
        )
        assert rejected_attempts[0].metadata_ == {
            "reason_codes": ["future_official_host"],
            "role": "player",
            "account_status": "active",
            "future_official_host_assignment_count": 1,
        }


def test_admin_user_suspend_rejects_last_active_admin_and_logs_attempt(
    client: TestClient,
):
    admin = authenticate_admin(client)
    preview_response = client.post(
        f"/admin/users/{admin['id']}/suspension-preview"
    )
    assert preview_response.status_code == 200, preview_response.text
    assert preview_response.json()["can_suspend"] is False

    response = client.post(
        f"/admin/users/{admin['id']}/suspend",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Attempting last admin suspension.",
            "idempotency_key": "suspend-last-active-admin",
        },
    )

    assert response.status_code == 409, response.text
    assert "last active admin" in response.text

    with SessionLocal() as db:
        db_admin = db.get(User, UUID(admin["id"]))
        rejected_attempt = db.scalar(
            select(AdminRejectedAttempt).where(
                AdminRejectedAttempt.attempt_type == "suspend_user_rejected",
                AdminRejectedAttempt.target_user_id == UUID(admin["id"]),
            )
        )
        assert db_admin is not None
        assert db_admin.account_status == "active"
        assert rejected_attempt is not None
        assert rejected_attempt.metadata_["reason_codes"] == [
            "last_active_admin"
        ]


def test_admin_user_suspend_validates_reason_and_rejects_unauthorized_staff(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    preview_response = client.post(
        f"/admin/users/{target['id']}/suspension-preview"
    )
    assert preview_response.status_code == 200, preview_response.text
    preview_token = preview_response.json()["preview_token"]

    blank_reason_response = client.post(
        f"/admin/users/{target['id']}/suspend",
        json={
            "preview_token": preview_token,
            "reason": "   ",
            "idempotency_key": "suspend-blank-reason",
        },
    )
    assert blank_reason_response.status_code == 400, blank_reason_response.text
    assert blank_reason_response.json()["detail"] == "reason is required."

    player = create_user(client)
    authenticate_as(player["id"])
    denied_response = client.post(
        f"/admin/users/{target['id']}/suspend",
        json={
            "preview_token": preview_token,
            "reason": "Player must not suspend users.",
            "idempotency_key": "suspend-user-denied",
        },
    )
    assert denied_response.status_code == 403, denied_response.text
    assert "Admin access required" in denied_response.text


def test_admin_user_unsuspend_updates_status_audit_and_notification_once(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    set_user_account_status(target["id"], "suspended")
    authenticate_as(admin["id"])

    payload = {
        "reason": "Support review confirmed account access can be restored.",
        "idempotency_key": "unsuspend-user-success-once",
    }
    response = client.post(
        f"/admin/users/{target['id']}/unsuspend",
        json=payload,
    )
    repeat_response = client.post(
        f"/admin/users/{target['id']}/unsuspend",
        json=payload,
    )
    reason_mismatch_response = client.post(
        f"/admin/users/{target['id']}/unsuspend",
        json={**payload, "reason": "Reuse this key for another unsuspension reason."},
    )
    different_request_response = client.post(
        f"/admin/users/{target['id']}/unsuspend",
        json={
            **payload,
            "idempotency_key": "unsuspend-user-different-request",
        },
    )

    assert response.status_code == 200, response.text
    assert repeat_response.status_code == 200, repeat_response.text
    assert repeat_response.json() == response.json()
    assert reason_mismatch_response.status_code == 409, reason_mismatch_response.text
    assert reason_mismatch_response.json()["detail"] == (
        "idempotency_key was already used for a different unsuspension request."
    )
    assert different_request_response.status_code == 409
    assert "already active" in different_request_response.text
    body = response.json()
    assert body["user_id"] == target["id"]
    assert body["account_status"] == "active"

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_actions = db.scalars(
            select(AdminAction).where(
                AdminAction.action_type == "unsuspend_user",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        ).all()
        notifications = db.scalars(
            select(Notification).where(
                Notification.user_id == UUID(target["id"]),
                Notification.notification_type == "account_security",
            )
        ).all()

        assert db_target is not None
        assert db_target.account_status == "active"
        assert len(audit_actions) == 1
        assert audit_actions[0].id == UUID(body["admin_action_id"])
        assert audit_actions[0].admin_user_id == UUID(admin["id"])
        assert audit_actions[0].reason == (
            "Support review confirmed account access can be restored."
        )
        assert audit_actions[0].metadata_ == {
            "before": {"account_status": "suspended"},
            "after": {"account_status": "active"},
        }
        assert len(notifications) == 1
        assert notifications[0].id == UUID(body["notification_id"])
        assert notifications[0].title == "Account access restored"
        assert notifications[0].action_key == "view_profile"
        assert audit_actions[0].target_notification_id == notifications[0].id


@pytest.mark.parametrize(
    ("account_status", "expected_reason"),
    [
        ("active", "This account is already active."),
        (
            "pending_deletion",
            "Accounts pending deletion cannot be unsuspended.",
        ),
        ("deleted", "Deleted accounts cannot be unsuspended."),
    ],
)
def test_admin_user_unsuspend_rejects_non_suspended_account_without_mutation(
    client: TestClient,
    account_status: str,
    expected_reason: str,
):
    authenticate_admin(client)
    target = create_user(client)
    set_user_account_status(target["id"], account_status)

    response = client.post(
        f"/admin/users/{target['id']}/unsuspend",
        json={
            "reason": "This account is not eligible for unsuspension.",
            "idempotency_key": f"unsuspend-user-{account_status}",
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == expected_reason

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "unsuspend_user",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        notification_count = db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == UUID(target["id"]),
                Notification.title == "Account access restored",
            )
        )
        assert db_target is not None
        assert db_target.account_status == account_status
        assert audit_count == 0
        assert notification_count == 0


def test_admin_user_unsuspend_rejects_deleted_timestamp_without_mutation(
    client: TestClient,
):
    authenticate_admin(client)
    target = create_user(client)
    set_user_account_status(target["id"], "suspended")
    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        assert db_target is not None
        db_target.deleted_at = datetime.now(UTC)
        db.commit()

    response = client.post(
        f"/admin/users/{target['id']}/unsuspend",
        json={
            "reason": "This deleted account cannot be unsuspended.",
            "idempotency_key": "unsuspend-user-deleted-timestamp",
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "Deleted accounts cannot be unsuspended."

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "unsuspend_user",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        notification_count = db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == UUID(target["id"]),
                Notification.title == "Account access restored",
            )
        )
        assert db_target is not None
        assert db_target.account_status == "suspended"
        assert db_target.deleted_at is not None
        assert audit_count == 0
        assert notification_count == 0


def test_admin_user_unsuspend_validates_target_reason_and_authorization(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    set_user_account_status(target["id"], "suspended")
    authenticate_as(admin["id"])

    missing_response = client.post(
        "/admin/users/00000000-0000-4000-8000-000000000000/unsuspend",
        json={
            "reason": "Restore missing account.",
            "idempotency_key": "unsuspend-missing-user",
        },
    )
    assert missing_response.status_code == 404, missing_response.text
    assert missing_response.json()["detail"] == "User not found."

    blank_reason_response = client.post(
        f"/admin/users/{target['id']}/unsuspend",
        json={
            "reason": "   ",
            "idempotency_key": "unsuspend-blank-reason",
        },
    )
    assert blank_reason_response.status_code == 400, blank_reason_response.text
    assert blank_reason_response.json()["detail"] == "reason is required."

    player = create_user(client)
    authenticate_as(player["id"])
    denied_response = client.post(
        f"/admin/users/{target['id']}/unsuspend",
        json={
            "reason": "Player must not unsuspend users.",
            "idempotency_key": "unsuspend-user-denied",
        },
    )
    assert denied_response.status_code == 403, denied_response.text
    assert "Admin access required" in denied_response.text


def test_admin_user_hosting_restriction_preview_reports_future_games_without_mutation(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    set_user_hosting_status(target["id"], "eligible")
    venue = create_venue(client, target["id"])
    future_game = create_game(
        client,
        target["id"],
        venue,
        game_type="community",
        host_user_id=target["id"],
        policy_mode="custom_hosted",
    )
    create_game(
        client,
        admin["id"],
        venue,
        host_user_id=target["id"],
    )
    set_user_account_status(target["id"], "suspended")
    authenticate_as(admin["id"])

    response = client.post(
        f"/admin/users/{target['id']}/hosting-restriction-preview"
    )
    repeat_response = client.post(
        f"/admin/users/{target['id']}/hosting-restriction-preview"
    )

    assert response.status_code == 200, response.text
    assert repeat_response.status_code == 200, repeat_response.text
    assert repeat_response.json() == response.json()
    body = response.json()
    assert body["user_id"] == target["id"]
    assert body["account_status"] == "suspended"
    assert body["hosting_status"] == "eligible"
    assert body["can_restrict"] is True
    assert body["blocking_reasons"] == []
    assert len(body["preview_token"]) == 64
    assert body["future_community_game_count"] == 1
    assert [game["id"] for game in body["future_community_games"]] == [
        future_game["id"]
    ]

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        db_future_game = db.get(Game, UUID(future_game["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "restrict_hosting",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        assert db_target is not None
        assert db_target.account_status == "suspended"
        assert db_target.hosting_status == "eligible"
        assert db_future_game is not None
        assert db_future_game.game_status == "active"
        assert audit_count == 0


@pytest.mark.parametrize(
    ("account_status", "hosting_status", "expected_reason"),
    [
        ("active", "restricted", "already restricted"),
        ("active", "not_eligible", "not currently eligible"),
        ("active", "pending_review", "pending review"),
        ("active", "suspended", "Suspended hosting access"),
        ("active", "banned_from_hosting", "Banned hosting access"),
        ("pending_deletion", "eligible", "pending deletion"),
        ("deleted", "eligible", "Deleted accounts"),
    ],
)
def test_admin_user_hosting_restriction_preview_rejects_ineligible_state(
    client: TestClient,
    account_status: str,
    hosting_status: str,
    expected_reason: str,
):
    authenticate_admin(client)
    target = create_user(client)
    set_user_account_status(target["id"], account_status)
    set_user_hosting_status(target["id"], hosting_status)

    response = client.post(
        f"/admin/users/{target['id']}/hosting-restriction-preview"
    )

    assert response.status_code == 200, response.text
    assert response.json()["can_restrict"] is False
    assert expected_reason in response.json()["blocking_reasons"][0]


def test_admin_user_hosting_restriction_preview_rejects_deleted_timestamp(
    client: TestClient,
):
    authenticate_admin(client)
    target = create_user(client)
    set_user_hosting_status(target["id"], "eligible")
    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        assert db_target is not None
        db_target.deleted_at = datetime.now(UTC)
        db.commit()

    response = client.post(
        f"/admin/users/{target['id']}/hosting-restriction-preview"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["can_restrict"] is False
    assert body["blocking_reasons"] == [
        "Deleted accounts cannot have hosting restricted."
    ]
    assert body["hosting_status"] == "eligible"

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "restrict_hosting",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        assert db_target is not None
        assert db_target.deleted_at is not None
        assert db_target.hosting_status == "eligible"
        assert audit_count == 0


def test_admin_user_hosting_restriction_preview_validates_target_and_authorization(
    client: TestClient,
):
    authenticate_admin(client)
    target = create_user(client)
    set_user_hosting_status(target["id"], "eligible")

    missing_response = client.post(
        "/admin/users/00000000-0000-4000-8000-000000000000/"
        "hosting-restriction-preview"
    )
    assert missing_response.status_code == 404, missing_response.text
    assert missing_response.json()["detail"] == "User not found."

    player = create_user(client)
    authenticate_as(player["id"])
    denied_response = client.post(
        f"/admin/users/{target['id']}/hosting-restriction-preview"
    )
    assert denied_response.status_code == 403, denied_response.text
    assert "Admin access required" in denied_response.text


def test_admin_user_restrict_hosting_updates_status_audit_and_notification_once(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    set_user_hosting_status(target["id"], "eligible")
    venue = create_venue(client, target["id"])
    future_game = create_game(
        client,
        target["id"],
        venue,
        game_type="community",
        host_user_id=target["id"],
        policy_mode="custom_hosted",
    )
    set_user_account_status(target["id"], "suspended")

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        assert db_target is not None
        db_target.hosting_suspended_until = datetime.now(UTC) + timedelta(days=14)
        db.commit()

    authenticate_as(admin["id"])
    preview_response = client.post(
        f"/admin/users/{target['id']}/hosting-restriction-preview"
    )
    assert preview_response.status_code == 200, preview_response.text
    assert preview_response.json()["can_restrict"] is True

    payload = {
        "preview_token": preview_response.json()["preview_token"],
        "reason": "Community hosting restriction confirmed by support.",
        "idempotency_key": "restrict-hosting-success-once",
    }
    response = client.post(
        f"/admin/users/{target['id']}/restrict-hosting",
        json=payload,
    )
    repeat_response = client.post(
        f"/admin/users/{target['id']}/restrict-hosting",
        json=payload,
    )
    reason_mismatch_response = client.post(
        f"/admin/users/{target['id']}/restrict-hosting",
        json={
            **payload,
            "reason": "Reuse this key for another hosting restriction reason.",
        },
    )
    preview_mismatch_response = client.post(
        f"/admin/users/{target['id']}/restrict-hosting",
        json={**payload, "preview_token": "1" * 64},
    )
    different_request_response = client.post(
        f"/admin/users/{target['id']}/restrict-hosting",
        json={
            **payload,
            "idempotency_key": "restrict-hosting-different-request",
        },
    )

    assert response.status_code == 200, response.text
    assert repeat_response.status_code == 200, repeat_response.text
    assert repeat_response.json() == response.json()
    for mismatch_response in (reason_mismatch_response, preview_mismatch_response):
        assert mismatch_response.status_code == 409, mismatch_response.text
        assert mismatch_response.json()["detail"] == (
            "idempotency_key was already used for a different "
            "hosting restriction request."
        )
    assert different_request_response.status_code == 409
    assert "already restricted" in different_request_response.text
    body = response.json()
    assert body["user_id"] == target["id"]
    assert body["hosting_status"] == "restricted"

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        db_future_game = db.get(Game, UUID(future_game["id"]))
        audit_actions = db.scalars(
            select(AdminAction).where(
                AdminAction.action_type == "restrict_hosting",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        ).all()
        notifications = db.scalars(
            select(Notification).where(
                Notification.user_id == UUID(target["id"]),
                Notification.notification_type == "account_security",
                Notification.title == "Hosting restricted",
            )
        ).all()

        assert db_target is not None
        assert db_target.account_status == "suspended"
        assert db_target.hosting_status == "restricted"
        assert db_target.hosting_suspended_until is None
        assert db_future_game is not None
        assert db_future_game.game_status == "active"
        assert db_future_game.publish_status == "published"
        assert db_future_game.host_user_id == UUID(target["id"])
        assert len(audit_actions) == 1
        assert audit_actions[0].id == UUID(body["admin_action_id"])
        assert audit_actions[0].admin_user_id == UUID(admin["id"])
        assert audit_actions[0].reason == (
            "Community hosting restriction confirmed by support."
        )
        assert audit_actions[0].metadata_["before"]["hosting_status"] == "eligible"
        assert audit_actions[0].metadata_["after"] == {
            "hosting_status": "restricted",
            "hosting_suspended_until": None,
        }
        assert audit_actions[0].metadata_["reviewed"] == {
            "future_community_game_count": 1,
            "preview_snapshot_hash": payload["preview_token"],
        }
        assert len(notifications) == 1
        assert notifications[0].id == UUID(body["notification_id"])
        assert notifications[0].action_key == "view_profile"
        assert audit_actions[0].target_notification_id == notifications[0].id


def test_admin_user_restrict_hosting_rejects_stale_preview_without_mutation(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    set_user_hosting_status(target["id"], "eligible")
    preview_response = client.post(
        f"/admin/users/{target['id']}/hosting-restriction-preview"
    )
    assert preview_response.status_code == 200, preview_response.text

    venue = create_venue(client, admin["id"])
    create_game(
        client,
        target["id"],
        venue,
        game_type="community",
        host_user_id=target["id"],
        policy_mode="custom_hosted",
    )

    authenticate_as(admin["id"])
    response = client.post(
        f"/admin/users/{target['id']}/restrict-hosting",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "This preview should now be stale.",
            "idempotency_key": "restrict-hosting-stale-preview",
        },
    )

    assert response.status_code == 409, response.text
    assert "preview is stale" in response.text

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "restrict_hosting",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        notification_count = db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == UUID(target["id"]),
                Notification.title == "Hosting restricted",
            )
        )
        assert db_target is not None
        assert db_target.hosting_status == "eligible"
        assert audit_count == 0
        assert notification_count == 0


@pytest.mark.parametrize(
    ("account_status", "hosting_status", "expected_reason"),
    [
        ("active", "restricted", "already restricted"),
        ("active", "not_eligible", "not currently eligible"),
        ("active", "pending_review", "pending review"),
        ("active", "suspended", "Suspended hosting access"),
        ("active", "banned_from_hosting", "Banned hosting access"),
        ("pending_deletion", "eligible", "pending deletion"),
        ("deleted", "eligible", "Deleted accounts"),
    ],
)
def test_admin_user_restrict_hosting_rejects_ineligible_state_without_mutation(
    client: TestClient,
    account_status: str,
    hosting_status: str,
    expected_reason: str,
):
    authenticate_admin(client)
    target = create_user(client)
    set_user_account_status(target["id"], account_status)
    set_user_hosting_status(target["id"], hosting_status)

    response = client.post(
        f"/admin/users/{target['id']}/restrict-hosting",
        json={
            "preview_token": "0" * 64,
            "reason": "This user cannot have hosting restricted.",
            "idempotency_key": f"restrict-hosting-{account_status}-{hosting_status}",
        },
    )

    assert response.status_code == 409, response.text
    assert expected_reason in response.json()["detail"]

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "restrict_hosting",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        notification_count = db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == UUID(target["id"]),
                Notification.title == "Hosting restricted",
            )
        )
        assert db_target is not None
        assert db_target.hosting_status == hosting_status
        assert audit_count == 0
        assert notification_count == 0


def test_admin_user_restrict_hosting_rejects_deleted_timestamp_without_mutation(
    client: TestClient,
):
    authenticate_admin(client)
    target = create_user(client)
    set_user_hosting_status(target["id"], "eligible")
    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        assert db_target is not None
        db_target.deleted_at = datetime.now(UTC)
        db.commit()

    response = client.post(
        f"/admin/users/{target['id']}/restrict-hosting",
        json={
            "preview_token": "0" * 64,
            "reason": "This deleted account cannot have hosting restricted.",
            "idempotency_key": "restrict-hosting-deleted-timestamp",
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == (
        "Deleted accounts cannot have hosting restricted."
    )

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "restrict_hosting",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        notification_count = db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == UUID(target["id"]),
                Notification.title == "Hosting restricted",
            )
        )
        assert db_target is not None
        assert db_target.hosting_status == "eligible"
        assert db_target.deleted_at is not None
        assert audit_count == 0
        assert notification_count == 0


def test_admin_user_restrict_hosting_validates_target_reason_and_authorization(
    client: TestClient,
):
    authenticate_admin(client)
    target = create_user(client)
    set_user_hosting_status(target["id"], "eligible")
    preview_response = client.post(
        f"/admin/users/{target['id']}/hosting-restriction-preview"
    )
    assert preview_response.status_code == 200, preview_response.text
    preview_token = preview_response.json()["preview_token"]

    missing_response = client.post(
        "/admin/users/00000000-0000-4000-8000-000000000000/restrict-hosting",
        json={
            "preview_token": preview_token,
            "reason": "Restrict a missing user.",
            "idempotency_key": "restrict-hosting-missing-user",
        },
    )
    assert missing_response.status_code == 404, missing_response.text
    assert missing_response.json()["detail"] == "User not found."

    blank_reason_response = client.post(
        f"/admin/users/{target['id']}/restrict-hosting",
        json={
            "preview_token": preview_token,
            "reason": "   ",
            "idempotency_key": "restrict-hosting-blank-reason",
        },
    )
    assert blank_reason_response.status_code == 400, blank_reason_response.text
    assert blank_reason_response.json()["detail"] == "reason is required."

    player = create_user(client)
    authenticate_as(player["id"])
    denied_response = client.post(
        f"/admin/users/{target['id']}/restrict-hosting",
        json={
            "preview_token": preview_token,
            "reason": "Player must not restrict hosting.",
            "idempotency_key": "restrict-hosting-denied",
        },
    )
    assert denied_response.status_code == 403, denied_response.text
    assert "Admin access required" in denied_response.text


def test_admin_user_restore_hosting_updates_status_audit_and_notification_once(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    set_user_account_status(target["id"], "suspended")
    set_user_hosting_status(target["id"], "restricted")

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        assert db_target is not None
        db_target.hosting_suspended_until = datetime.now(UTC) + timedelta(days=7)
        db.commit()

    authenticate_as(admin["id"])
    payload = {
        "reason": "Support review confirmed hosting can be restored.",
        "idempotency_key": "restore-hosting-success-once",
    }
    response = client.post(
        f"/admin/users/{target['id']}/restore-hosting",
        json=payload,
    )
    repeat_response = client.post(
        f"/admin/users/{target['id']}/restore-hosting",
        json=payload,
    )
    reason_mismatch_response = client.post(
        f"/admin/users/{target['id']}/restore-hosting",
        json={
            **payload,
            "reason": "Reuse this key for another hosting restoration reason.",
        },
    )
    different_request_response = client.post(
        f"/admin/users/{target['id']}/restore-hosting",
        json={
            **payload,
            "idempotency_key": "restore-hosting-different-request",
        },
    )

    assert response.status_code == 200, response.text
    assert repeat_response.status_code == 200, repeat_response.text
    assert repeat_response.json() == response.json()
    assert reason_mismatch_response.status_code == 409, reason_mismatch_response.text
    assert reason_mismatch_response.json()["detail"] == (
        "idempotency_key was already used for a different "
        "hosting restoration request."
    )
    assert different_request_response.status_code == 409
    assert "already eligible" in different_request_response.text
    body = response.json()
    assert body["user_id"] == target["id"]
    assert body["hosting_status"] == "eligible"

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_actions = db.scalars(
            select(AdminAction).where(
                AdminAction.action_type == "restore_hosting",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        ).all()
        notifications = db.scalars(
            select(Notification).where(
                Notification.user_id == UUID(target["id"]),
                Notification.notification_type == "account_security",
                Notification.title == "Hosting restored",
            )
        ).all()

        assert db_target is not None
        assert db_target.account_status == "suspended"
        assert db_target.hosting_status == "eligible"
        assert db_target.hosting_suspended_until is None
        assert len(audit_actions) == 1
        assert audit_actions[0].id == UUID(body["admin_action_id"])
        assert audit_actions[0].admin_user_id == UUID(admin["id"])
        assert audit_actions[0].reason == (
            "Support review confirmed hosting can be restored."
        )
        assert audit_actions[0].metadata_["before"]["hosting_status"] == "restricted"
        assert audit_actions[0].metadata_["after"] == {
            "hosting_status": "eligible",
            "hosting_suspended_until": None,
        }
        assert len(notifications) == 1
        assert notifications[0].id == UUID(body["notification_id"])
        assert notifications[0].action_key == "view_profile"
        assert audit_actions[0].target_notification_id == notifications[0].id


@pytest.mark.parametrize(
    ("account_status", "hosting_status", "expected_reason"),
    [
        ("active", "eligible", "already eligible"),
        ("active", "not_eligible", "Only restricted hosting access"),
        ("active", "pending_review", "pending review"),
        ("active", "suspended", "Suspended hosting access"),
        ("active", "banned_from_hosting", "Banned hosting access"),
        ("pending_deletion", "restricted", "pending deletion"),
        ("deleted", "restricted", "Deleted accounts"),
    ],
)
def test_admin_user_restore_hosting_rejects_ineligible_state_without_mutation(
    client: TestClient,
    account_status: str,
    hosting_status: str,
    expected_reason: str,
):
    authenticate_admin(client)
    target = create_user(client)
    set_user_account_status(target["id"], account_status)
    set_user_hosting_status(target["id"], hosting_status)

    response = client.post(
        f"/admin/users/{target['id']}/restore-hosting",
        json={
            "reason": "This user cannot have hosting restored.",
            "idempotency_key": f"restore-hosting-{account_status}-{hosting_status}",
        },
    )

    assert response.status_code == 409, response.text
    assert expected_reason in response.json()["detail"]

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "restore_hosting",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        notification_count = db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == UUID(target["id"]),
                Notification.title == "Hosting restored",
            )
        )
        assert db_target is not None
        assert db_target.hosting_status == hosting_status
        assert audit_count == 0
        assert notification_count == 0


def test_admin_user_restore_hosting_rejects_deleted_timestamp_without_mutation(
    client: TestClient,
):
    authenticate_admin(client)
    target = create_user(client)
    set_user_hosting_status(target["id"], "restricted")
    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        assert db_target is not None
        db_target.deleted_at = datetime.now(UTC)
        db.commit()

    response = client.post(
        f"/admin/users/{target['id']}/restore-hosting",
        json={
            "reason": "This deleted account cannot have hosting restored.",
            "idempotency_key": "restore-hosting-deleted-timestamp",
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == (
        "Deleted accounts cannot have hosting restored."
    )

    with SessionLocal() as db:
        db_target = db.get(User, UUID(target["id"]))
        audit_count = db.scalar(
            select(func.count())
            .select_from(AdminAction)
            .where(
                AdminAction.action_type == "restore_hosting",
                AdminAction.target_user_id == UUID(target["id"]),
            )
        )
        notification_count = db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == UUID(target["id"]),
                Notification.title == "Hosting restored",
            )
        )
        assert db_target is not None
        assert db_target.hosting_status == "restricted"
        assert db_target.deleted_at is not None
        assert audit_count == 0
        assert notification_count == 0


def test_admin_user_restore_hosting_validates_target_reason_and_authorization(
    client: TestClient,
):
    admin = authenticate_admin(client)
    target = create_user(client)
    set_user_hosting_status(target["id"], "restricted")
    authenticate_as(admin["id"])

    missing_response = client.post(
        "/admin/users/00000000-0000-4000-8000-000000000000/restore-hosting",
        json={
            "reason": "Restore missing hosting access.",
            "idempotency_key": "restore-hosting-missing-user",
        },
    )
    assert missing_response.status_code == 404, missing_response.text
    assert missing_response.json()["detail"] == "User not found."

    blank_reason_response = client.post(
        f"/admin/users/{target['id']}/restore-hosting",
        json={
            "reason": "   ",
            "idempotency_key": "restore-hosting-blank-reason",
        },
    )
    assert blank_reason_response.status_code == 400, blank_reason_response.text
    assert blank_reason_response.json()["detail"] == "reason is required."

    player = create_user(client)
    authenticate_as(player["id"])
    denied_response = client.post(
        f"/admin/users/{target['id']}/restore-hosting",
        json={
            "reason": "Player must not restore hosting.",
            "idempotency_key": "restore-hosting-denied",
        },
    )
    assert denied_response.status_code == 403, denied_response.text
    assert "Admin access required" in denied_response.text
