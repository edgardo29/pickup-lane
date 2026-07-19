from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.tests.helpers import (
    authenticate_as,
    create_user,
    set_user_account_status,
    set_user_role,
    soft_delete_user,
)


def campaign_payload(
    *,
    idempotency_key: str = "campaign-create-001",
    **overrides: object,
) -> dict:
    payload = {
        "internal_name": "Summer maintenance notice",
        "title": "Scheduled maintenance",
        "summary": "Pickup Lane will be briefly unavailable.",
        "body": "Pickup Lane will be unavailable on Tuesday from 2:00 AM to 2:30 AM.",
        "audience_type": "all_active_users",
        "delivery_class": "mandatory",
        "target_user_ids": [],
        "idempotency_key": idempotency_key,
    }
    payload.update(overrides)
    return payload


def create_campaign(
    client: TestClient,
    admin_user_id: str,
    **overrides: object,
) -> dict:
    authenticate_as(admin_user_id)
    response = client.post(
        "/admin/platform-notice-campaigns",
        json=campaign_payload(**overrides),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_platform_notice_campaign_routes_require_manage_permission(
    client: TestClient,
):
    player = create_user(client)
    authenticate_as(player["id"])
    player_response = client.get("/admin/platform-notice-campaigns")
    assert player_response.status_code == 403, player_response.text
    player_send_response = client.post(
        "/admin/platform-notice-campaigns/00000000-0000-0000-0000-000000000001/send",
        json={"idempotency_key": "permission-send-001"},
    )
    assert player_send_response.status_code == 403, player_send_response.text

    suspended_admin = create_user(client)
    set_user_role(suspended_admin["id"], "admin")
    set_user_account_status(suspended_admin["id"], "suspended")
    authenticate_as(suspended_admin["id"])
    suspended_response = client.get("/admin/platform-notice-campaigns")
    assert suspended_response.status_code == 403, suspended_response.text
    suspended_attempts_response = client.get(
        "/admin/platform-notice-campaigns/"
        "00000000-0000-0000-0000-000000000001/attempts"
    )
    assert suspended_attempts_response.status_code == 403


def test_admin_creates_selected_user_campaign_without_delivering_notifications(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    first_target = create_user(client)
    second_target = create_user(client)

    campaign = create_campaign(
        client,
        admin["id"],
        audience_type="selected_users",
        delivery_class="preference_controlled",
        target_user_ids=[second_target["id"], first_target["id"], first_target["id"]],
    )

    assert campaign["campaign_status"] == "draft"
    assert campaign["audience_type"] == "selected_users"
    assert campaign["delivery_class"] == "preference_controlled"
    assert set(campaign["target_user_ids"]) == {first_target["id"], second_target["id"]}
    assert campaign["target_user_count"] == 2
    assert campaign["created_by_user_id"] == admin["id"]
    assert campaign["updated_by_user_id"] == admin["id"]

    get_response = client.get(
        f"/admin/platform-notice-campaigns/{campaign['id']}"
    )
    assert get_response.status_code == 200, get_response.text
    assert get_response.json() == campaign

    from backend.database import SessionLocal
    from backend.models import AdminAction, Notification

    with SessionLocal() as db:
        audit_action = db.scalar(
            select(AdminAction).where(
                AdminAction.action_type == "create_platform_notice_campaign",
                AdminAction.target_platform_notice_campaign_id == UUID(campaign["id"]),
            )
        )
        assert audit_action is not None
        assert audit_action.admin_user_id == UUID(admin["id"])
        assert audit_action.metadata_ == {
            "campaign_status": "draft",
            "audience_type": "selected_users",
            "delivery_class": "preference_controlled",
            "selected_user_count": 2,
        }
        assert db.scalar(select(func.count()).select_from(Notification)) == 0


def test_campaign_creation_is_idempotent_and_rejects_key_reuse(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    first = create_campaign(client, admin["id"])
    replay = create_campaign(client, admin["id"])
    assert replay["id"] == first["id"]

    update_response = client.patch(
        f"/admin/platform-notice-campaigns/{first['id']}",
        json={"title": "Edited current title"},
    )
    assert update_response.status_code == 200, update_response.text

    replay_after_edit = create_campaign(client, admin["id"])
    assert replay_after_edit["id"] == first["id"]
    assert replay_after_edit["title"] == "Edited current title"

    conflict_response = client.post(
        "/admin/platform-notice-campaigns",
        json=campaign_payload(title="Different initial payload"),
    )
    assert conflict_response.status_code == 409, conflict_response.text
    assert "different campaign" in conflict_response.text

    from backend.database import SessionLocal
    from backend.models import AdminAction, PlatformNoticeCampaign

    with SessionLocal() as db:
        assert (
            db.scalar(select(func.count()).select_from(PlatformNoticeCampaign)) == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(AdminAction)
                .where(AdminAction.action_type == "create_platform_notice_campaign")
            )
            == 1
        )


def test_campaign_audience_validation_rejects_invalid_targets(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    active_target = create_user(client)
    suspended_target = create_user(client)
    set_user_account_status(suspended_target["id"], "suspended")
    authenticate_as(admin["id"])

    all_users_with_targets = client.post(
        "/admin/platform-notice-campaigns",
        json=campaign_payload(
            target_user_ids=[active_target["id"]],
        ),
    )
    assert all_users_with_targets.status_code == 400, all_users_with_targets.text

    selected_without_targets = client.post(
        "/admin/platform-notice-campaigns",
        json=campaign_payload(
            idempotency_key="campaign-create-002",
            audience_type="selected_users",
        ),
    )
    assert selected_without_targets.status_code == 400, selected_without_targets.text

    selected_suspended_user = client.post(
        "/admin/platform-notice-campaigns",
        json=campaign_payload(
            idempotency_key="campaign-create-003",
            audience_type="selected_users",
            target_user_ids=[suspended_target["id"]],
        ),
    )
    assert selected_suspended_user.status_code == 400, selected_suspended_user.text
    assert "active accounts" in selected_suspended_user.text


def test_admin_updates_draft_campaign_and_replaces_selected_targets(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    first_target = create_user(client)
    second_target = create_user(client)
    campaign = create_campaign(
        client,
        admin["id"],
        audience_type="selected_users",
        target_user_ids=[first_target["id"]],
    )

    response = client.patch(
        f"/admin/platform-notice-campaigns/{campaign['id']}",
        json={
            "title": "Updated maintenance window",
            "target_user_ids": [second_target["id"]],
        },
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["title"] == "Updated maintenance window"
    assert updated["target_user_ids"] == [second_target["id"]]
    assert updated["target_user_count"] == 1

    no_op_response = client.patch(
        f"/admin/platform-notice-campaigns/{campaign['id']}",
        json={},
    )
    assert no_op_response.status_code == 200, no_op_response.text
    assert no_op_response.json()["id"] == campaign["id"]

    from backend.database import SessionLocal
    from backend.models import AdminAction

    with SessionLocal() as db:
        update_actions = db.scalars(
            select(AdminAction).where(
                AdminAction.action_type == "update_platform_notice_campaign",
                AdminAction.target_platform_notice_campaign_id == UUID(campaign["id"]),
            )
        ).all()
        assert len(update_actions) == 1
        assert update_actions[0].metadata_["changed_fields"] == [
            "target_user_ids",
            "title",
        ]
        assert update_actions[0].metadata_["before"]["selected_user_count"] == 1
        assert update_actions[0].metadata_["after"]["selected_user_count"] == 1


def test_non_draft_campaign_cannot_be_edited(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    campaign = create_campaign(client, admin["id"])

    from backend.database import SessionLocal
    from backend.models import PlatformNoticeCampaign

    with SessionLocal() as db:
        db_campaign = db.get(PlatformNoticeCampaign, UUID(campaign["id"]))
        assert db_campaign is not None
        db_campaign.campaign_status = "sending"
        db.commit()

    response = client.patch(
        f"/admin/platform-notice-campaigns/{campaign['id']}",
        json={"title": "Too late to edit"},
    )
    assert response.status_code == 409, response.text
    assert "Only draft" in response.text


def test_campaign_list_filters_searches_and_paginates(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    create_campaign(
        client,
        admin["id"],
        idempotency_key="campaign-create-101",
        internal_name="Maintenance alpha",
        delivery_class="mandatory",
    )
    matching = create_campaign(
        client,
        admin["id"],
        idempotency_key="campaign-create-102",
        internal_name="Operations beta",
        title="Court closure update",
        delivery_class="preference_controlled",
    )

    response = client.get(
        "/admin/platform-notice-campaigns",
        params={
            "campaign_status": "draft",
            "audience_type": "all_active_users",
            "delivery_class": "preference_controlled",
            "search": "closure",
            "offset": 0,
            "limit": 1,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_count"] == 1
    assert body["offset"] == 0
    assert body["limit"] == 1
    assert [item["id"] for item in body["campaigns"]] == [matching["id"]]


def test_selected_campaign_send_delivers_and_preserves_inactive_skips(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    active_target = create_user(client)
    suspended_target = create_user(client)
    deleted_target = create_user(client)
    campaign = create_campaign(
        client,
        admin["id"],
        idempotency_key="selected-delivery-create-001",
        audience_type="selected_users",
        target_user_ids=[
            active_target["id"],
            suspended_target["id"],
            deleted_target["id"],
        ],
    )
    set_user_account_status(suspended_target["id"], "suspended")
    soft_delete_user(deleted_target["id"])

    response = client.post(
        f"/admin/platform-notice-campaigns/{campaign['id']}/send",
        json={"idempotency_key": "selected-delivery-send-001"},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["campaign"]["campaign_status"] == "completed"
    assert result["campaign"]["delivery_summary"] == {
        "targeted_count": 3,
        "delivered_count": 1,
        "skipped_count": 2,
        "failed_count": 0,
    }
    assert result["campaign"]["first_sent_at"] is not None
    assert result["campaign"]["completed_at"] is not None
    assert result["attempt"]["attempt_type"] == "initial_send"
    assert result["attempt"]["attempt_status"] == "completed"
    assert result["attempt"]["targeted_count"] == 3
    assert result["attempt"]["delivered_count"] == 1
    assert result["attempt"]["skipped_count"] == 2
    assert result["attempt"]["failed_count"] == 0

    from backend.database import SessionLocal
    from backend.models import (
        AdminAction,
        Notification,
        PlatformNoticeCampaignDelivery,
    )

    with SessionLocal() as db:
        deliveries = db.scalars(
            select(PlatformNoticeCampaignDelivery).where(
                PlatformNoticeCampaignDelivery.campaign_id
                == UUID(campaign["id"])
            )
        ).all()
        deliveries_by_recipient = {
            str(delivery.recipient_user_id_snapshot): delivery
            for delivery in deliveries
        }
        delivered = deliveries_by_recipient[active_target["id"]]
        assert delivered.delivery_status == "delivered"
        assert delivered.attempt_count == 1
        assert delivered.notification_id is not None
        assert (
            deliveries_by_recipient[suspended_target["id"]].skip_reason
            == "suspended"
        )
        assert (
            deliveries_by_recipient[deleted_target["id"]].skip_reason
            == "deleted"
        )

        notification = db.get(Notification, delivered.notification_id)
        assert notification is not None
        assert notification.user_id == UUID(active_target["id"])
        assert notification.notification_type == "admin_notice"
        assert notification.notification_category == "app"
        assert notification.notification_domain == "admin"
        assert notification.source_type == "pickup_lane"
        assert notification.subject_label == "Pickup Lane"
        assert notification.title == campaign["title"]
        assert notification.summary == campaign["summary"]
        assert notification.body == campaign["body"]
        assert notification.action_key is None
        assert notification.actor_user_id is None
        assert notification.aggregation_key == (
            f"admin_notice:campaign:{campaign['id']}:user:{active_target['id']}"
        )

        audit_action = db.scalar(
            select(AdminAction).where(
                AdminAction.action_type == "send_platform_notice_campaign",
                AdminAction.target_platform_notice_campaign_id
                == UUID(campaign["id"]),
            )
        )
        assert audit_action is not None
        assert audit_action.idempotency_key == "selected-delivery-send-001"
        assert audit_action.metadata_["attempt_type"] == "initial_send"
        assert audit_action.metadata_["campaign_status"] == "completed"
        assert audit_action.metadata_["targeted_count"] == 3
        assert audit_action.metadata_["delivered_count"] == 1
        assert audit_action.metadata_["skipped_count"] == 2
        assert audit_action.metadata_["failed_count"] == 0


def test_all_active_campaign_snapshots_only_currently_active_users(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    active_player = create_user(client)
    suspended_player = create_user(client)
    pending_deletion_player = create_user(client)
    deleted_player = create_user(client)
    set_user_account_status(suspended_player["id"], "suspended")
    set_user_account_status(pending_deletion_player["id"], "pending_deletion")
    soft_delete_user(deleted_player["id"])
    campaign = create_campaign(
        client,
        admin["id"],
        idempotency_key="all-active-delivery-create-001",
    )

    response = client.post(
        f"/admin/platform-notice-campaigns/{campaign['id']}/send",
        json={"idempotency_key": "all-active-delivery-send-001"},
    )
    assert response.status_code == 200, response.text
    summary = response.json()["campaign"]["delivery_summary"]
    assert summary == {
        "targeted_count": 2,
        "delivered_count": 2,
        "skipped_count": 0,
        "failed_count": 0,
    }

    deliveries_response = client.get(
        f"/admin/platform-notice-campaigns/{campaign['id']}/deliveries"
    )
    assert deliveries_response.status_code == 200, deliveries_response.text
    recipient_ids = {
        delivery["recipient_user_id_snapshot"]
        for delivery in deliveries_response.json()["deliveries"]
    }
    assert recipient_ids == {admin["id"], active_player["id"]}
    assert suspended_player["id"] not in recipient_ids
    assert pending_deletion_player["id"] not in recipient_ids
    assert deleted_player["id"] not in recipient_ids


def test_campaign_send_replay_is_idempotent_and_rejects_invalid_reuse(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    target = create_user(client)
    campaign = create_campaign(
        client,
        admin["id"],
        idempotency_key="send-replay-create-001",
        audience_type="selected_users",
        target_user_ids=[target["id"]],
    )
    send_path = f"/admin/platform-notice-campaigns/{campaign['id']}/send"
    payload = {"idempotency_key": "send-replay-attempt-001"}

    first_response = client.post(send_path, json=payload)
    assert first_response.status_code == 200, first_response.text
    replay_response = client.post(send_path, json=payload)
    assert replay_response.status_code == 200, replay_response.text
    assert replay_response.json() == first_response.json()

    different_key_response = client.post(
        send_path,
        json={"idempotency_key": "send-replay-attempt-002"},
    )
    assert different_key_response.status_code == 409
    retry_key_reuse_response = client.post(
        f"/admin/platform-notice-campaigns/{campaign['id']}/retry-failed",
        json=payload,
    )
    assert retry_key_reuse_response.status_code == 409
    assert "different delivery operation" in retry_key_reuse_response.text
    no_failures_response = client.post(
        f"/admin/platform-notice-campaigns/{campaign['id']}/retry-failed",
        json={"idempotency_key": "send-replay-retry-001"},
    )
    assert no_failures_response.status_code == 409
    assert "no failed deliveries" in no_failures_response.text

    from backend.database import SessionLocal
    from backend.models import (
        AdminAction,
        Notification,
        PlatformNoticeCampaignAttempt,
        PlatformNoticeCampaignDelivery,
    )

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Notification)) == 1
        assert (
            db.scalar(
                select(func.count()).select_from(PlatformNoticeCampaignDelivery)
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count()).select_from(PlatformNoticeCampaignAttempt)
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(AdminAction)
                .where(
                    AdminAction.action_type == "send_platform_notice_campaign"
                )
            )
            == 1
        )


def test_failed_delivery_retry_only_processes_failed_recipients(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    successful_target = create_user(client)
    failed_target = create_user(client)
    skipped_target = create_user(client)
    campaign = create_campaign(
        client,
        admin["id"],
        idempotency_key="retry-delivery-create-001",
        audience_type="selected_users",
        target_user_ids=[
            successful_target["id"],
            failed_target["id"],
            skipped_target["id"],
        ],
    )
    set_user_account_status(skipped_target["id"], "suspended")

    from backend.services import platform_notice_delivery_service

    original_create = (
        platform_notice_delivery_service.create_or_get_campaign_notification
    )

    def fail_one_recipient(
        db,
        *,
        campaign,
        recipient_user_id,
        event_at,
    ):
        if recipient_user_id == UUID(failed_target["id"]):
            raise RuntimeError("simulated delivery failure")
        return original_create(
            db,
            campaign=campaign,
            recipient_user_id=recipient_user_id,
            event_at=event_at,
        )

    monkeypatch.setattr(
        platform_notice_delivery_service,
        "create_or_get_campaign_notification",
        fail_one_recipient,
    )
    send_response = client.post(
        f"/admin/platform-notice-campaigns/{campaign['id']}/send",
        json={"idempotency_key": "retry-delivery-send-001"},
    )
    assert send_response.status_code == 200, send_response.text
    send_result = send_response.json()
    assert send_result["campaign"]["campaign_status"] == "completed_with_failures"
    assert send_result["campaign"]["delivery_summary"] == {
        "targeted_count": 3,
        "delivered_count": 1,
        "skipped_count": 1,
        "failed_count": 1,
    }
    assert send_result["attempt"]["attempt_status"] == "completed_with_failures"

    monkeypatch.setattr(
        platform_notice_delivery_service,
        "create_or_get_campaign_notification",
        original_create,
    )
    retry_payload = {"idempotency_key": "retry-delivery-attempt-001"}
    retry_response = client.post(
        f"/admin/platform-notice-campaigns/{campaign['id']}/retry-failed",
        json=retry_payload,
    )
    assert retry_response.status_code == 200, retry_response.text
    retry_result = retry_response.json()
    assert retry_result["campaign"]["campaign_status"] == "completed"
    assert retry_result["campaign"]["delivery_summary"] == {
        "targeted_count": 3,
        "delivered_count": 2,
        "skipped_count": 1,
        "failed_count": 0,
    }
    assert retry_result["attempt"]["attempt_type"] == "retry_failed"
    assert retry_result["attempt"]["attempt_status"] == "completed"
    assert retry_result["attempt"]["targeted_count"] == 1
    assert retry_result["attempt"]["delivered_count"] == 1

    replay_response = client.post(
        f"/admin/platform-notice-campaigns/{campaign['id']}/retry-failed",
        json=retry_payload,
    )
    assert replay_response.status_code == 200, replay_response.text
    assert replay_response.json() == retry_result

    deliveries_response = client.get(
        f"/admin/platform-notice-campaigns/{campaign['id']}/deliveries",
        params={"delivery_status": "delivered", "offset": 0, "limit": 1},
    )
    assert deliveries_response.status_code == 200, deliveries_response.text
    assert deliveries_response.json()["total_count"] == 2
    assert len(deliveries_response.json()["deliveries"]) == 1

    attempts_response = client.get(
        f"/admin/platform-notice-campaigns/{campaign['id']}/attempts",
        params={"attempt_type": "retry_failed"},
    )
    assert attempts_response.status_code == 200, attempts_response.text
    attempts_body = attempts_response.json()
    assert attempts_body["total_count"] == 1
    assert attempts_body["attempts"][0]["id"] == retry_result["attempt"]["id"]

    from backend.database import SessionLocal
    from backend.models import (
        AdminAction,
        Notification,
        PlatformNoticeCampaignDelivery,
    )

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Notification)) == 2
        deliveries = db.scalars(
            select(PlatformNoticeCampaignDelivery).where(
                PlatformNoticeCampaignDelivery.campaign_id
                == UUID(campaign["id"])
            )
        ).all()
        attempts_by_recipient = {
            str(delivery.recipient_user_id_snapshot): delivery.attempt_count
            for delivery in deliveries
        }
        assert attempts_by_recipient[successful_target["id"]] == 1
        assert attempts_by_recipient[failed_target["id"]] == 2
        assert attempts_by_recipient[skipped_target["id"]] == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(AdminAction)
                .where(
                    AdminAction.action_type
                    == "retry_platform_notice_campaign"
                )
            )
            == 1
        )


def test_retry_skips_failed_recipient_that_became_inactive(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    failed_target = create_user(client)
    campaign = create_campaign(
        client,
        admin["id"],
        idempotency_key="retry-inactive-create-001",
        audience_type="selected_users",
        target_user_ids=[failed_target["id"]],
    )

    from backend.services import platform_notice_delivery_service

    original_create = (
        platform_notice_delivery_service.create_or_get_campaign_notification
    )

    def fail_recipient(
        db,
        *,
        campaign,
        recipient_user_id,
        event_at,
    ):
        raise RuntimeError("simulated delivery failure")

    monkeypatch.setattr(
        platform_notice_delivery_service,
        "create_or_get_campaign_notification",
        fail_recipient,
    )
    send_response = client.post(
        f"/admin/platform-notice-campaigns/{campaign['id']}/send",
        json={"idempotency_key": "retry-inactive-send-001"},
    )
    assert send_response.status_code == 200, send_response.text
    send_result = send_response.json()
    assert send_result["campaign"]["campaign_status"] == "failed"
    assert send_result["campaign"]["delivery_summary"] == {
        "targeted_count": 1,
        "delivered_count": 0,
        "skipped_count": 0,
        "failed_count": 1,
    }
    assert send_result["attempt"]["attempt_status"] == "failed"

    set_user_account_status(failed_target["id"], "suspended")
    monkeypatch.setattr(
        platform_notice_delivery_service,
        "create_or_get_campaign_notification",
        original_create,
    )
    retry_response = client.post(
        f"/admin/platform-notice-campaigns/{campaign['id']}/retry-failed",
        json={"idempotency_key": "retry-inactive-attempt-001"},
    )
    assert retry_response.status_code == 200, retry_response.text
    retry_result = retry_response.json()
    assert retry_result["campaign"]["campaign_status"] == "completed"
    assert retry_result["campaign"]["delivery_summary"] == {
        "targeted_count": 1,
        "delivered_count": 0,
        "skipped_count": 1,
        "failed_count": 0,
    }
    assert retry_result["attempt"]["attempt_type"] == "retry_failed"
    assert retry_result["attempt"]["attempt_status"] == "completed"
    assert retry_result["attempt"]["targeted_count"] == 1
    assert retry_result["attempt"]["delivered_count"] == 0
    assert retry_result["attempt"]["skipped_count"] == 1
    assert retry_result["attempt"]["failed_count"] == 0

    from backend.database import SessionLocal
    from backend.models import Notification, PlatformNoticeCampaignDelivery

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Notification)) == 0
        delivery = db.scalar(
            select(PlatformNoticeCampaignDelivery).where(
                PlatformNoticeCampaignDelivery.campaign_id
                == UUID(campaign["id"])
            )
        )
        assert delivery is not None
        assert delivery.delivery_status == "skipped"
        assert delivery.skip_reason == "suspended"
        assert delivery.failure_code is None
        assert delivery.notification_id is None
        assert delivery.attempt_count == 1
