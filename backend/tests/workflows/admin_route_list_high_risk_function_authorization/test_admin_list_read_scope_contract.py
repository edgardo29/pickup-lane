from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest

from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_game_roster_moderation_contract import (
    _persist_community_game_fixture,
    _persist_game_fixture,
)
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    _add_users,
    _auth_headers,
    _client,
    _install_tokens_for_users,
    _session,
    _user,
)
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_money_credit_refund_contract import (
    _persist_host_publish_fee_fixture,
    _persist_money_repair_fixture,
    _persist_paid_booking,
)

pytestmark = pytest.mark.suite_type("ordinary")


def _persist_notification_fixture(*, recipient: Any) -> uuid.UUID:
    from backend.models import Notification

    now = datetime.now(timezone.utc)
    with _session() as db:
        notification = Notification(
            id=uuid.uuid4(),
            user_id=recipient.id,
            notification_type="account_security",
            notification_category="app",
            notification_domain="account",
            source_type="account",
            title="Local account notice",
            subject_label="Account",
            summary="Local account security notice.",
            body="Local account security notice body.",
            action_key="view_profile",
            event_at=now,
            aggregation_key=f"ws03d-admin-notification-{uuid.uuid4()}",
            actor_user_id=None,
            is_read=False,
            read_at=None,
            created_at=now,
            updated_at=now,
        )
        db.add(notification)
        db.commit()
        return notification.id


def _payment_event_provider_event_id(payment_event_id: uuid.UUID) -> str:
    from backend.models import PaymentEvent

    with _session() as db:
        payment_event = db.get(PaymentEvent, payment_event_id)
        assert payment_event is not None
        return str(payment_event.provider_event_id)


@pytest.mark.requirement("WS03-04D-R4", "WS03-04D-R10")
def test_admin_user_list_and_detail_are_admin_only_and_missing_objects_return_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("list-admin", role="admin")
    ordinary = _user("list-ordinary")
    target = _user("list-target")
    _add_users(admin, ordinary, target)
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "ordinary-token": ordinary},
    )
    client = _client()

    ordinary_response = client.get(
        "/admin/users",
        headers=_auth_headers("ordinary-token"),
    )
    assert ordinary_response.status_code == 403

    list_response = client.get("/admin/users", headers=_auth_headers("admin-token"))
    assert list_response.status_code == 200
    listed_ids = {item["id"] for item in list_response.json()["users"]}
    assert str(target.id) in listed_ids

    filtered = client.get(
        f"/admin/users?query={target.email}&role=player&limit=1",
        headers=_auth_headers("admin-token"),
    )
    assert filtered.status_code == 200
    filtered_body = filtered.json()
    assert filtered_body["users"][0]["id"] == str(target.id)
    assert filtered_body["users"][0]["email"] == target.email
    assert filtered_body["limit"] == 1
    assert filtered_body["has_more"] is False

    cursor_page = client.get(
        "/admin/users?role=player&limit=1",
        headers=_auth_headers("admin-token"),
    )
    assert cursor_page.status_code == 200
    cursor_body = cursor_page.json()
    assert cursor_body["limit"] == 1
    assert cursor_body["has_more"] is True
    assert cursor_body["next_cursor"]
    second_page = client.get(
        f"/admin/users?role=player&limit=1&cursor={cursor_body['next_cursor']}",
        headers=_auth_headers("admin-token"),
    )
    assert second_page.status_code == 200
    assert second_page.json()["users"][0]["id"] != cursor_body["users"][0]["id"]

    rejected_filter = client.get(
        "/admin/users?role=not-a-role",
        headers=_auth_headers("admin-token"),
    )
    assert rejected_filter.status_code == 400

    detail_response = client.get(
        f"/admin/users/{target.id}?limit=1",
        headers=_auth_headers("admin-token"),
    )
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["user"]["id"] == str(target.id)

    game_activity = client.get(
        f"/admin/users/{target.id}/game-activity?limit=1&offset=0",
        headers=_auth_headers("admin-token"),
    )
    need_a_sub_activity = client.get(
        f"/admin/users/{target.id}/need-a-sub-activity?limit=1&offset=0",
        headers=_auth_headers("admin-token"),
    )
    assert game_activity.status_code == 200
    assert game_activity.json()["limit"] == 1
    assert need_a_sub_activity.status_code == 200
    assert need_a_sub_activity.json()["limit"] == 1

    missing_response = client.get(
        f"/admin/users/{uuid.uuid4()}",
        headers=_auth_headers("admin-token"),
    )
    assert missing_response.status_code == 404


@pytest.mark.requirement("WS03-04D-R4", "WS03-04D-R7", "WS03-04D-R10")
def test_admin_money_lists_are_admin_only_and_reject_unsupported_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("money-list-admin", role="admin")
    ordinary = _user("money-list-ordinary")
    target = _user("money-list-target")
    host = _user("money-list-host")
    _add_users(admin, ordinary, target, host)
    game_id, _venue_id = _persist_game_fixture(
        "money-list",
        admin=admin,
        creator=target,
    )
    booking_id = _persist_paid_booking(
        game_id=game_id,
        buyer_user_id=target.id,
        amount_cents=1200,
    )
    money_fixture = _persist_money_repair_fixture(
        game_id=game_id,
        booking_id=booking_id,
        target_user_id=target.id,
    )
    community_game_id, _community_venue_id = _persist_community_game_fixture(
        "money-list-fee",
        admin=admin,
        host=host,
    )
    host_publish_fee_id = _persist_host_publish_fee_fixture(
        game_id=community_game_id,
        host_user_id=host.id,
    )
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "ordinary-token": ordinary},
    )
    client = _client()

    ordinary_response = client.get(
        "/admin/money/payments",
        headers=_auth_headers("ordinary-token"),
    )
    assert ordinary_response.status_code == 403

    for route in (
        "/admin/money/payments",
        "/admin/money/refunds",
        "/admin/money/credits",
        "/admin/money/issues",
    ):
        response = client.get(route, headers=_auth_headers("admin-token"))
        assert response.status_code == 200, route
        assert "items" in response.json(), route

    payments = client.get(
        (
            "/admin/money/payments"
            f"?user_id={target.id}&payment_status=succeeded&payment_type=booking&limit=1"
        ),
        headers=_auth_headers("admin-token"),
    )
    assert payments.status_code == 200
    payment_items = payments.json()["items"]
    assert [item["id"] for item in payment_items] == [str(money_fixture["payment_id"])]
    assert payment_items[0]["payer_user_id"] == str(target.id)
    assert payment_items[0]["game_id"] == str(game_id)
    payment_detail = client.get(
        f"/admin/money/payments/{money_fixture['payment_id']}",
        headers=_auth_headers("admin-token"),
    )
    assert payment_detail.status_code == 200
    assert payment_detail.json()["payment"]["id"] == str(money_fixture["payment_id"])
    assert payment_detail.json()["payer"]["id"] == str(target.id)

    refunds = client.get(
        f"/admin/money/refunds?payment_id={money_fixture['payment_id']}&limit=10",
        headers=_auth_headers("admin-token"),
    )
    assert refunds.status_code == 200
    refund_ids = {item["id"] for item in refunds.json()["items"]}
    assert refund_ids == {
        str(money_fixture["retry_refund_id"]),
        str(money_fixture["reconcile_refund_id"]),
    }
    refund_detail = client.get(
        f"/admin/money/refunds/{money_fixture['retry_refund_id']}",
        headers=_auth_headers("admin-token"),
    )
    assert refund_detail.status_code == 200
    assert refund_detail.json()["refund"]["id"] == str(
        money_fixture["retry_refund_id"]
    )
    assert refund_detail.json()["payment_summary"]["id"] == str(
        money_fixture["payment_id"]
    )

    credits = client.get(
        (
            "/admin/money/credits"
            f"?user_id={target.id}&source_booking_id={booking_id}&limit=1"
        ),
        headers=_auth_headers("admin-token"),
    )
    assert credits.status_code == 200
    assert [item["id"] for item in credits.json()["items"]] == [
        str(money_fixture["credit_id"])
    ]
    credit_detail = client.get(
        f"/admin/money/credits/{money_fixture['credit_id']}",
        headers=_auth_headers("admin-token"),
    )
    assert credit_detail.status_code == 200
    assert credit_detail.json()["credit"]["id"] == str(money_fixture["credit_id"])
    assert credit_detail.json()["booking"]["id"] == str(booking_id)

    issues = client.get(
        f"/admin/money/issues?user_id={target.id}&status=open&limit=10",
        headers=_auth_headers("admin-token"),
    )
    assert issues.status_code == 200
    issue_ids = {item["id"] for item in issues.json()["items"]}
    assert issue_ids >= {
        str(money_fixture["resolve_issue_id"]),
        str(money_fixture["retry_issue_id"]),
    }
    issue_detail = client.get(
        f"/admin/money/issues/{money_fixture['resolve_issue_id']}",
        headers=_auth_headers("admin-token"),
    )
    assert issue_detail.status_code == 200
    assert issue_detail.json()["money_issue"]["id"] == str(
        money_fixture["resolve_issue_id"]
    )
    assert issue_detail.json()["payment"]["id"] == str(money_fixture["payment_id"])

    payment_event_provider_id = _payment_event_provider_event_id(
        money_fixture["payment_event_id"]
    )
    payment_event_list = client.get(
        f"/payment-events?provider_event_id={payment_event_provider_id}",
        headers=_auth_headers("admin-token"),
    )
    assert payment_event_list.status_code == 200
    assert [item["id"] for item in payment_event_list.json()] == [
        str(money_fixture["payment_event_id"])
    ]
    payment_event_detail = client.get(
        f"/payment-events/{money_fixture['payment_event_id']}",
        headers=_auth_headers("admin-token"),
    )
    assert payment_event_detail.status_code == 200
    assert payment_event_detail.json()["id"] == str(money_fixture["payment_event_id"])

    fee_list = client.get(
        f"/host-publish-fees?game_id={community_game_id}&host_user_id={host.id}",
        headers=_auth_headers("admin-token"),
    )
    assert fee_list.status_code == 200
    assert [item["id"] for item in fee_list.json()] == [str(host_publish_fee_id)]
    fee_detail = client.get(
        f"/host-publish-fees/{host_publish_fee_id}",
        headers=_auth_headers("admin-token"),
    )
    assert fee_detail.status_code == 200
    assert fee_detail.json()["host_user_id"] == str(host.id)

    unsupported = client.get(
        "/admin/money/payments?unsupported_filter=1",
        headers=_auth_headers("admin-token"),
    )
    assert unsupported.status_code == 400


@pytest.mark.requirement("WS03-04D-R4", "WS03-04D-R8", "WS03-04D-R10")
def test_admin_miscellaneous_read_families_are_admin_only_and_preserve_lookup_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("misc-read-admin", role="admin")
    ordinary = _user("misc-read-ordinary")
    target = _user("misc-read-target")
    _add_users(admin, ordinary, target)
    notification_id = _persist_notification_fixture(recipient=target)
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "ordinary-token": ordinary},
    )
    client = _client()

    for route in (
        "/admin/lookups/users?query=misc-read&limit=10",
        "/admin/lookups/venues?query=misc-read&limit=10",
        f"/admin/notifications?user_id={admin.id}",
        "/admin/game-images",
        "/admin/rejected-attempts",
        "/payment-events",
        "/host-publish-fees",
        "/game-status-history",
        "/participant-status-history",
        "/user-settings/11111111-1111-4111-8111-111111111111",
        "/user-stats",
        "/venue-approval-requests",
        "/waitlist-entries",
        "/users",
    ):
        ordinary_response = client.get(
            route,
            headers=_auth_headers("ordinary-token"),
        )
        assert ordinary_response.status_code == 403, route

        admin_response = client.get(route, headers=_auth_headers("admin-token"))
        assert admin_response.status_code in {200, 404}, route

    notification_list = client.get(
        f"/admin/notifications?user_id={target.id}",
        headers=_auth_headers("admin-token"),
    )
    assert notification_list.status_code == 200
    notification_body = notification_list.json()
    assert [item["id"] for item in notification_body["notifications"]] == [
        str(notification_id)
    ]
    assert notification_body["limit"] == 50

    notification_detail = client.get(
        f"/admin/notifications/{notification_id}",
        headers=_auth_headers("admin-token"),
    )
    assert notification_detail.status_code == 200
    detail_body = notification_detail.json()
    assert detail_body["id"] == str(notification_id)
    assert detail_body["user_id"] == str(target.id)
    assert detail_body["action_state"]["status"] in {
        "available",
        "disabled",
        "enabled",
    }
    assert detail_body["audit_action_count"] == 0

    unsupported_notification_query = client.get(
        f"/admin/notifications?user_id={target.id}&limit=10",
        headers=_auth_headers("admin-token"),
    )
    assert unsupported_notification_query.status_code == 400
    assert unsupported_notification_query.json()["detail"]["code"] == (
        "notification_lookup_unsupported_query_param"
    )

    missing_detail_routes = (
        "/admin/notifications/{id}",
        "/admin/game-images/{id}",
        "/admin/rejected-attempts/{id}",
        "/payment-events/{id}",
        "/host-publish-fees/{id}",
        "/game-status-history/{id}",
        "/participant-status-history/{id}",
        "/user-stats/{id}",
        "/venue-approval-requests/{id}",
        "/waitlist-entries/{id}",
        "/users/{id}",
    )
    for route_template in missing_detail_routes:
        response = client.get(
            route_template.replace("{id}", str(uuid.uuid4())),
            headers=_auth_headers("admin-token"),
        )
        assert response.status_code == 404, route_template
