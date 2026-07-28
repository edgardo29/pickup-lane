from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.tests.helpers import (
    authenticate_as,
    create_notification,
    create_user,
    set_user_account_status,
    set_user_role,
    soft_delete_user,
    unique_suffix,
)


def notice_payload(
    *,
    idempotency_key: str | None = None,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "idempotency_key": idempotency_key
        or f"platform-notice-{unique_suffix()}",
        "title": "Scheduled maintenance",
        "message": "Pickup Lane will be unavailable tonight for maintenance.",
        "audience_type": "all_eligible_users",
        "selected_user_ids": [],
    }
    payload.update(overrides)
    return payload


def publish_notice(
    client: TestClient,
    admin_user_id: str,
    **overrides: object,
) -> dict:
    authenticate_as(admin_user_id)
    response = client.post(
        "/admin/platform-notices",
        json=notice_payload(**overrides),
    )
    assert response.status_code == 201, response.text
    return response.json()


def model_count(model) -> int:
    from backend.database import SessionLocal

    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(model)) or 0


def test_platform_notice_routes_require_active_admin(client: TestClient):
    player = create_user(client)
    authenticate_as(player["id"])

    assert client.get("/admin/platform-notices").status_code == 403
    assert client.post(
        "/admin/platform-notices",
        json=notice_payload(),
    ).status_code == 403
    assert client.post(
        f"/admin/platform-notices/{uuid4()}/cancel",
        json={"cancellation_reason": "Wrong actor."},
    ).status_code == 403

    suspended_admin = create_user(client)
    set_user_role(suspended_admin["id"], "admin")
    set_user_account_status(suspended_admin["id"], "suspended")
    authenticate_as(suspended_admin["id"])

    assert client.get("/admin/platform-notices").status_code == 403


def test_publish_global_notice_uses_one_shared_row_without_notification_fanout(
    client: TestClient,
):
    from backend.database import SessionLocal
    from backend.models import (
        AdminAction,
        Notification,
        PlatformNotice,
        PlatformNoticeRecipient,
        PlatformNoticeSelectedRead,
    )

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    existing_user = create_user(client)

    idempotency_key = "global-sparse-notice"
    result = publish_notice(client, admin["id"], idempotency_key=idempotency_key)
    notice = result["notice"]

    assert result["idempotent_replay"] is False
    assert notice["audience_type"] == "all_eligible_users"
    assert notice["status"] == "published"
    assert notice["global_sequence"] is not None
    assert notice["selected_recipient_count"] == 0

    with SessionLocal() as db:
        db_notice = db.get(PlatformNotice, UUID(notice["id"]))
        assert db_notice is not None
        assert db_notice.idempotency_key_hash != idempotency_key
        assert len(db_notice.idempotency_key_hash) == 64
        assert model_count(PlatformNoticeRecipient) == 0
        assert model_count(PlatformNoticeSelectedRead) == 0
        assert model_count(Notification) == 0
        action = db.scalar(
            select(AdminAction).where(
                AdminAction.action_type == "publish_platform_notice",
                AdminAction.target_platform_notice_id == UUID(notice["id"]),
            )
        )
        assert action is not None
        assert action.reason is None
        assert action.metadata_["audience_type"] == "all_eligible_users"

    authenticate_as(existing_user["id"])
    inbox_response = client.get("/inbox/app-updates")
    assert inbox_response.status_code == 200, inbox_response.text
    items = inbox_response.json()["items"]
    assert [item["source_type"] for item in items] == ["platform_notice_global"]
    assert items[0]["source_id"] == notice["id"]
    assert items[0]["is_new"] is True
    assert items[0]["read_behavior"] == "global_seen_marker"

    future_user = create_user(client)
    authenticate_as(future_user["id"])
    future_response = client.get("/inbox/app-updates")
    assert future_response.status_code == 200, future_response.text
    assert [item["source_id"] for item in future_response.json()["items"]] == [
        notice["id"]
    ]

    notifications_response = client.get("/notifications/me")
    assert notifications_response.status_code == 200, notifications_response.text
    assert notifications_response.json() == []


def test_global_seen_marker_uses_returned_watermark_without_read_rows(
    client: TestClient,
):
    from backend.database import SessionLocal
    from backend.models import PlatformNotice, PlatformNoticeGlobalSeenState

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    user = create_user(client)

    first = publish_notice(
        client,
        admin["id"],
        idempotency_key="global-seen-first",
        title="First notice",
    )["notice"]
    authenticate_as(user["id"])
    list_response = client.get("/inbox/app-updates")
    assert list_response.status_code == 200, list_response.text
    seen_token = list_response.json()["global_seen_token"]
    assert seen_token

    second = publish_notice(
        client,
        admin["id"],
        idempotency_key="global-seen-second",
        title="Second notice",
    )["notice"]
    authenticate_as(user["id"])
    seen_response = client.put(
        "/inbox/app-updates/global-seen",
        json={"seen_token": seen_token},
    )
    assert seen_response.status_code == 200, seen_response.text
    assert seen_response.json()["app_updates_new_count"] == 1

    with SessionLocal() as db:
        state = db.get(PlatformNoticeGlobalSeenState, UUID(user["id"]))
        assert state is not None
        first_notice = db.get(PlatformNotice, UUID(first["id"]))
        second_notice = db.get(PlatformNotice, UUID(second["id"]))
        assert first_notice is not None
        assert second_notice is not None
        assert state.last_seen_global_sequence == first_notice.global_sequence
        assert state.last_seen_global_sequence < second_notice.global_sequence


def test_global_seen_marker_uses_seen_through_watermark_on_mixed_pages(
    client: TestClient,
):
    from backend.database import SessionLocal
    from backend.models import Notification, PlatformNotice

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    user = create_user(client)

    older_notice = publish_notice(
        client,
        admin["id"],
        idempotency_key="global-seen-skip-older",
        title="Older global notice",
    )["notice"]
    app_notification = create_notification(
        client,
        user["id"],
        title="Account notice between globals",
    )
    newer_notice = publish_notice(
        client,
        admin["id"],
        idempotency_key="global-seen-skip-newer",
        title="Newer global notice",
    )["notice"]
    base_time = datetime.now(UTC) - timedelta(minutes=10)
    with SessionLocal() as db:
        older_db_notice = db.get(PlatformNotice, UUID(older_notice["id"]))
        newer_db_notice = db.get(PlatformNotice, UUID(newer_notice["id"]))
        db_notification = db.get(Notification, UUID(app_notification["id"]))
        assert older_db_notice is not None
        assert newer_db_notice is not None
        assert db_notification is not None
        older_db_notice.published_at = base_time
        older_db_notice.updated_at = base_time
        db_notification.event_at = base_time + timedelta(minutes=1)
        newer_db_notice.published_at = base_time + timedelta(minutes=2)
        newer_db_notice.updated_at = base_time + timedelta(minutes=2)
        db.commit()

    authenticate_as(user["id"])
    list_response = client.get("/inbox/app-updates", params={"limit": 2})
    assert list_response.status_code == 200, list_response.text
    body = list_response.json()
    returned_ids = {item["source_id"] for item in body["items"]}
    assert newer_notice["id"] in returned_ids
    assert app_notification["id"] in returned_ids
    assert older_notice["id"] not in returned_ids
    seen_token = body["global_seen_token"]
    assert seen_token

    counts_response = client.get("/inbox/counts")
    assert counts_response.status_code == 200, counts_response.text
    assert counts_response.json()["app_updates_new_count"] == 3

    seen_response = client.put(
        "/inbox/app-updates/global-seen",
        json={"seen_token": seen_token},
    )
    assert seen_response.status_code == 200, seen_response.text
    assert seen_response.json()["app_updates_new_count"] == 1


def test_global_seen_marker_rejects_invalid_or_cross_user_tokens(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    first_user = create_user(client)
    second_user = create_user(client)
    publish_notice(
        client,
        admin["id"],
        idempotency_key="global-seen-token-owner",
    )

    authenticate_as(first_user["id"])
    invalid_response = client.put(
        "/inbox/app-updates/global-seen",
        json={"seen_token": "not-a-valid-token"},
    )
    assert invalid_response.status_code == 400, invalid_response.text

    list_response = client.get("/inbox/app-updates")
    assert list_response.status_code == 200, list_response.text
    seen_token = list_response.json()["global_seen_token"]
    assert seen_token

    authenticate_as(second_user["id"])
    cross_user_response = client.put(
        "/inbox/app-updates/global-seen",
        json={"seen_token": seen_token},
    )
    assert cross_user_response.status_code == 400, cross_user_response.text


def test_global_notice_visibility_uses_current_account_eligibility(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    suspended_user = create_user(client)
    deleted_user = create_user(client)
    set_user_account_status(suspended_user["id"], "suspended")
    soft_delete_user(deleted_user["id"])

    notice = publish_notice(client, admin["id"])["notice"]

    authenticate_as(suspended_user["id"])
    assert client.get("/inbox/app-updates").status_code == 403

    authenticate_as(deleted_user["id"])
    assert client.get("/inbox/app-updates").status_code == 403

    set_user_account_status(suspended_user["id"], "active")
    authenticate_as(suspended_user["id"])
    response = client.get("/inbox/app-updates")
    assert response.status_code == 200, response.text
    assert [item["source_id"] for item in response.json()["items"]] == [notice["id"]]


def test_selected_notice_creates_memberships_and_exact_read_state(
    client: TestClient,
):
    from backend.models import (
        Notification,
        PlatformNoticeRecipient,
        PlatformNoticeSelectedRead,
    )

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    target = create_user(client)
    outsider = create_user(client)

    notice = publish_notice(
        client,
        admin["id"],
        audience_type="selected_users",
        selected_user_ids=[target["id"], target["id"]],
    )["notice"]

    assert notice["audience_type"] == "selected_users"
    assert notice["global_sequence"] is None
    assert notice["selected_recipient_count"] == 1
    assert model_count(PlatformNoticeRecipient) == 1
    assert model_count(PlatformNoticeSelectedRead) == 0
    assert model_count(Notification) == 0

    authenticate_as(outsider["id"])
    outsider_response = client.get("/inbox/app-updates")
    assert outsider_response.status_code == 200, outsider_response.text
    assert outsider_response.json()["items"] == []

    authenticate_as(target["id"])
    target_response = client.get("/inbox/app-updates")
    assert target_response.status_code == 200, target_response.text
    item = target_response.json()["items"][0]
    assert item["source_type"] == "platform_notice_selected"
    assert item["source_id"] == notice["id"]
    assert item["is_new"] is True
    assert item["read_behavior"] == "item_read"

    read_response = client.put(
        f"/inbox/app-updates/platform-notices/{notice['id']}/read"
    )
    assert read_response.status_code == 200, read_response.text
    assert read_response.json()["is_new"] is False
    assert read_response.json()["read_at"] is not None
    assert model_count(PlatformNoticeSelectedRead) == 1

    unread_response = client.get("/inbox/app-updates", params={"filter": "new"})
    assert unread_response.status_code == 200, unread_response.text
    assert unread_response.json()["items"] == []


def test_platform_notices_do_not_resolve_through_admin_notification_lookup(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    global_user = create_user(client)
    selected_user = create_user(client)

    global_notice = publish_notice(
        client,
        admin["id"],
        idempotency_key="lookup-separation-global",
        title="Global lookup separation",
    )["notice"]
    selected_notice = publish_notice(
        client,
        admin["id"],
        idempotency_key="lookup-separation-selected",
        audience_type="selected_users",
        selected_user_ids=[selected_user["id"]],
        title="Selected lookup separation",
    )["notice"]

    authenticate_as(admin["id"])
    for notice in (global_notice, selected_notice):
        detail_response = client.get(f"/admin/notifications/{notice['id']}")
        assert detail_response.status_code == 404, detail_response.text

    for user in (global_user, selected_user):
        list_response = client.get(
            "/admin/notifications",
            params={"user_id": user["id"]},
        )
        assert list_response.status_code == 200, list_response.text
        assert list_response.json()["notifications"] == []


def test_selected_notice_read_rejects_global_and_cancelled_notices(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    target = create_user(client)

    global_notice = publish_notice(
        client,
        admin["id"],
        idempotency_key="selected-read-global-rejected",
    )["notice"]
    selected_notice = publish_notice(
        client,
        admin["id"],
        idempotency_key="selected-read-cancelled-rejected",
        audience_type="selected_users",
        selected_user_ids=[target["id"]],
    )["notice"]

    authenticate_as(admin["id"])
    cancel_response = client.post(
        f"/admin/platform-notices/{selected_notice['id']}/cancel",
        json={"cancellation_reason": "Superseded before anyone should read it."},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    authenticate_as(target["id"])
    global_read_response = client.put(
        f"/inbox/app-updates/platform-notices/{global_notice['id']}/read"
    )
    assert global_read_response.status_code == 404, global_read_response.text

    cancelled_read_response = client.put(
        f"/inbox/app-updates/platform-notices/{selected_notice['id']}/read"
    )
    assert cancelled_read_response.status_code == 404, cancelled_read_response.text


def test_selected_notice_rejects_missing_or_ineligible_users_without_persisting(
    client: TestClient,
):
    from backend.models import PlatformNotice, PlatformNoticeRecipient

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    suspended_user = create_user(client)
    set_user_account_status(suspended_user["id"], "suspended")
    authenticate_as(admin["id"])

    missing_response = client.post(
        "/admin/platform-notices",
        json=notice_payload(
            idempotency_key="missing-selected-user",
            audience_type="selected_users",
            selected_user_ids=[str(uuid4())],
        ),
    )
    assert missing_response.status_code == 422, missing_response.text
    assert missing_response.json()["detail"]["code"] == "selected_user_not_found"

    ineligible_response = client.post(
        "/admin/platform-notices",
        json=notice_payload(
            idempotency_key="ineligible-selected-user",
            audience_type="selected_users",
            selected_user_ids=[suspended_user["id"]],
        ),
    )
    assert ineligible_response.status_code == 422, ineligible_response.text
    assert ineligible_response.json()["detail"]["code"] == "selected_user_ineligible"

    assert model_count(PlatformNotice) == 0
    assert model_count(PlatformNoticeRecipient) == 0


def test_selected_notice_limit_applies_to_unique_recipients(client: TestClient):
    from backend.models import PlatformNotice, PlatformNoticeRecipient

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    target = create_user(client)
    authenticate_as(admin["id"])

    duplicate_response = client.post(
        "/admin/platform-notices",
        json=notice_payload(
            idempotency_key="duplicate-selected-users",
            audience_type="selected_users",
            selected_user_ids=[target["id"] for _ in range(201)],
        ),
    )
    assert duplicate_response.status_code == 201, duplicate_response.text
    assert duplicate_response.json()["notice"]["selected_recipient_count"] == 1

    too_many_response = client.post(
        "/admin/platform-notices",
        json=notice_payload(
            idempotency_key="too-many-selected-users",
            audience_type="selected_users",
            selected_user_ids=[str(uuid4()) for _ in range(201)],
        ),
    )
    assert too_many_response.status_code == 400, too_many_response.text
    assert "200 users" in too_many_response.text
    assert model_count(PlatformNotice) == 1
    assert model_count(PlatformNoticeRecipient) == 1


def test_publish_idempotency_is_scoped_to_admin_and_payload(
    client: TestClient,
):
    first_admin = create_user(client)
    second_admin = create_user(client)
    set_user_role(first_admin["id"], "admin")
    set_user_role(second_admin["id"], "admin")
    key = "idempotency-platform-notice-001"

    first_response = publish_notice(
        client,
        first_admin["id"],
        idempotency_key=key,
        title="Original title",
    )
    replay_response = publish_notice(
        client,
        first_admin["id"],
        idempotency_key=key,
        title="Original title",
    )
    assert replay_response["idempotent_replay"] is True
    assert replay_response["notice"]["id"] == first_response["notice"]["id"]

    authenticate_as(first_admin["id"])
    conflict_response = client.post(
        "/admin/platform-notices",
        json=notice_payload(
            idempotency_key=key,
            title="Changed title",
        ),
    )
    assert conflict_response.status_code == 409, conflict_response.text
    assert conflict_response.json()["detail"]["code"] == "idempotency_key_conflict"

    second_admin_response = publish_notice(
        client,
        second_admin["id"],
        idempotency_key=key,
        title="Original title",
    )
    assert second_admin_response["notice"]["id"] != first_response["notice"]["id"]


def test_cancel_notice_requires_reason_and_is_idempotent(client: TestClient):
    from backend.database import SessionLocal
    from backend.models import AdminAction, PlatformNotice

    creator = create_user(client)
    canceller = create_user(client)
    repeat_canceller = create_user(client)
    viewer = create_user(client)
    set_user_role(creator["id"], "admin")
    set_user_role(canceller["id"], "admin")
    set_user_role(repeat_canceller["id"], "admin")
    notice = publish_notice(client, creator["id"])["notice"]

    authenticate_as(canceller["id"])
    blank_response = client.post(
        f"/admin/platform-notices/{notice['id']}/cancel",
        json={"cancellation_reason": "   "},
    )
    assert blank_response.status_code == 400, blank_response.text

    cancel_response = client.post(
        f"/admin/platform-notices/{notice['id']}/cancel",
        json={"cancellation_reason": "Incorrect maintenance window."},
    )
    assert cancel_response.status_code == 200, cancel_response.text
    cancelled = cancel_response.json()
    assert cancelled["status"] == "cancelled"
    assert cancelled["cancelled_by_admin_id"] == canceller["id"]
    assert cancelled["cancellation_reason"] == "Incorrect maintenance window."

    authenticate_as(repeat_canceller["id"])
    repeat_response = client.post(
        f"/admin/platform-notices/{notice['id']}/cancel",
        json={"cancellation_reason": "Different retry reason."},
    )
    assert repeat_response.status_code == 200, repeat_response.text
    repeated = repeat_response.json()
    assert repeated["cancelled_by_admin_id"] == canceller["id"]
    assert repeated["cancelled_at"] == cancelled["cancelled_at"]
    assert repeated["cancellation_reason"] == "Incorrect maintenance window."

    with SessionLocal() as db:
        db_notice = db.get(PlatformNotice, UUID(notice["id"]))
        assert db_notice is not None
        assert db_notice.cancelled_at is not None
        cancel_actions = db.scalars(
            select(AdminAction).where(
                AdminAction.action_type == "cancel_platform_notice",
                AdminAction.target_platform_notice_id == UUID(notice["id"]),
            )
        ).all()
        assert len(cancel_actions) == 1
        assert cancel_actions[0].reason == "Incorrect maintenance window."

    authenticate_as(viewer["id"])
    inbox_response = client.get("/inbox/app-updates")
    assert inbox_response.status_code == 200, inbox_response.text
    assert inbox_response.json()["items"] == []


def test_concurrent_cancel_notice_records_one_audit_action(client: TestClient):
    from backend.database import SessionLocal
    from backend.models import AdminAction, User
    from backend.schemas.platform_notice_schema import PlatformNoticeCancel
    from backend.services.platform_notice_service import cancel_platform_notice

    creator = create_user(client)
    first_canceller = create_user(client)
    second_canceller = create_user(client)
    set_user_role(creator["id"], "admin")
    set_user_role(first_canceller["id"], "admin")
    set_user_role(second_canceller["id"], "admin")
    notice = publish_notice(
        client,
        creator["id"],
        idempotency_key="concurrent-cancel-notice",
    )["notice"]
    notice_id = UUID(notice["id"])
    barrier = Barrier(2)

    def cancel_as(admin_id: str, reason: str) -> str | None:
        with SessionLocal() as db:
            admin_user = db.get(User, UUID(admin_id))
            assert admin_user is not None
            barrier.wait(timeout=5)
            result = cancel_platform_notice(
                db,
                admin_user=admin_user,
                notice_id=notice_id,
                payload=PlatformNoticeCancel(cancellation_reason=reason),
            )
            return result.cancellation_reason

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda args: cancel_as(*args),
                [
                    (first_canceller["id"], "First concurrent reason."),
                    (second_canceller["id"], "Second concurrent reason."),
                ],
            )
        )

    assert len(set(results)) == 1
    with SessionLocal() as db:
        cancel_actions = db.scalars(
            select(AdminAction).where(
                AdminAction.action_type == "cancel_platform_notice",
                AdminAction.target_platform_notice_id == notice_id,
            )
        ).all()
        assert len(cancel_actions) == 1
        assert cancel_actions[0].reason == results[0]


def test_admin_history_and_selected_recipient_pagination(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    first_user = create_user(client, first_name="First", last_name="Recipient")
    second_user = create_user(client, first_name="Second", last_name="Recipient")

    global_notice = publish_notice(
        client,
        admin["id"],
        idempotency_key="history-global",
        title="Global history notice",
    )["notice"]
    selected_notice = publish_notice(
        client,
        admin["id"],
        idempotency_key="history-selected",
        title="Selected history notice",
        audience_type="selected_users",
        selected_user_ids=[first_user["id"], second_user["id"]],
    )["notice"]

    authenticate_as(admin["id"])
    list_response = client.get(
        "/admin/platform-notices",
        params={"audience_type": "selected_users", "search": "Selected"},
    )
    assert list_response.status_code == 200, list_response.text
    list_body = list_response.json()
    assert [notice["id"] for notice in list_body["notices"]] == [selected_notice["id"]]
    assert list_body["notices"][0]["selected_recipient_count"] == 2

    published_response = client.get(
        "/admin/platform-notices",
        params={"status": "published"},
    )
    assert published_response.status_code == 200, published_response.text
    assert {notice["id"] for notice in published_response.json()["notices"]} == {
        global_notice["id"],
        selected_notice["id"],
    }

    recipient_response = client.get(
        f"/admin/platform-notices/{selected_notice['id']}/recipients",
        params={"limit": 1},
    )
    assert recipient_response.status_code == 200, recipient_response.text
    recipient_body = recipient_response.json()
    assert len(recipient_body["recipients"]) == 1
    assert recipient_body["has_more"] is True
    assert recipient_body["next_cursor"]


def test_admin_history_search_rejects_short_or_nonmeaningful_queries(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])

    for search in ("ab", "___", "%%%", "--"):
        response = client.get("/admin/platform-notices", params={"search": search})
        assert response.status_code == 400, response.text
        assert "letters or numbers" in response.text


def test_admin_history_search_escapes_wildcards(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    special_notice = publish_notice(
        client,
        admin["id"],
        idempotency_key="history-search-special-wildcards",
        message=r"Backslash token ABC\DEF should match literally.",
        title="Deploy ABC_DEF 100% ready",
    )["notice"]
    publish_notice(
        client,
        admin["id"],
        idempotency_key="history-search-decoy-wildcards",
        message="Backslash token ABCDDEF should not match.",
        title="Deploy ABCXDEF 100 percent ready",
    )

    authenticate_as(admin["id"])
    for search in ("ABC_", "100%", r"ABC\D"):
        response = client.get("/admin/platform-notices", params={"search": search})
        assert response.status_code == 200, response.text
        assert [notice["id"] for notice in response.json()["notices"]] == [
            special_notice["id"]
        ]


def test_admin_history_cursor_rejects_filter_context_mismatch(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    publish_notice(
        client,
        admin["id"],
        idempotency_key="history-cursor-context-first",
        title="Cursor context first",
    )
    publish_notice(
        client,
        admin["id"],
        idempotency_key="history-cursor-context-second",
        title="Cursor context second",
    )

    authenticate_as(admin["id"])
    first_page_response = client.get(
        "/admin/platform-notices",
        params={"limit": 1, "search": "Cursor", "status": "published"},
    )
    assert first_page_response.status_code == 200, first_page_response.text
    cursor = first_page_response.json()["next_cursor"]
    assert cursor

    invalid_cursor_response = client.get(
        "/admin/platform-notices",
        params={"cursor": "not-a-valid-cursor"},
    )
    assert invalid_cursor_response.status_code == 400
    assert "cursor is invalid" in invalid_cursor_response.text

    search_mismatch_response = client.get(
        "/admin/platform-notices",
        params={
            "cursor": cursor,
            "limit": 1,
            "search": "Different",
            "status": "published",
        },
    )
    assert search_mismatch_response.status_code == 400
    assert "current query" in search_mismatch_response.text

    status_mismatch_response = client.get(
        "/admin/platform-notices",
        params={
            "cursor": cursor,
            "limit": 1,
            "search": "Cursor",
            "status": "cancelled",
        },
    )
    assert status_mismatch_response.status_code == 400
    assert "current query" in status_mismatch_response.text


def test_app_updates_merge_platform_notices_with_existing_app_notifications(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    user = create_user(client)
    app_notification = create_notification(
        client,
        user["id"],
        title="Account warning",
        body="Pickup Lane sent you an account notice.",
    )
    global_notice = publish_notice(
        client,
        admin["id"],
        idempotency_key="app-updates-merge-global",
        title="Global update",
    )["notice"]
    selected_notice = publish_notice(
        client,
        admin["id"],
        idempotency_key="app-updates-merge-selected",
        title="Selected update",
        audience_type="selected_users",
        selected_user_ids=[user["id"]],
    )["notice"]

    authenticate_as(user["id"])
    app_response = client.get("/inbox/app-updates")
    assert app_response.status_code == 200, app_response.text
    app_items = app_response.json()["items"]
    assert {item["source_id"] for item in app_items} == {
        app_notification["id"],
        global_notice["id"],
        selected_notice["id"],
    }
    assert {item["source_type"] for item in app_items} == {
        "notification",
        "platform_notice_global",
        "platform_notice_selected",
    }

    game_response = client.get("/inbox/game-activity")
    assert game_response.status_code == 200, game_response.text
    assert game_response.json()["items"] == []


def test_inbox_counts_exclude_future_normal_notifications(client: TestClient):
    user = create_user(client)
    future_event_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    create_notification(
        client,
        user["id"],
        event_at=future_event_at,
        title="Future app notice",
    )
    create_notification(
        client,
        user["id"],
        event_at=future_event_at,
        notification_type="game_updated",
        notification_category="game_activity",
        notification_domain="game",
        source_type="game",
        title="Future game update",
        subject_label="Pickup game",
        summary="Game update.",
        body="Game update.",
    )

    authenticate_as(user["id"])
    counts_response = client.get("/inbox/counts")
    assert counts_response.status_code == 200, counts_response.text
    assert counts_response.json() == {
        "app_updates_new_count": 0,
        "game_activity_unread_count": 0,
    }

    app_response = client.get("/inbox/app-updates")
    assert app_response.status_code == 200, app_response.text
    assert app_response.json()["items"] == []

    game_response = client.get("/inbox/game-activity")
    assert game_response.status_code == 200, game_response.text
    assert game_response.json()["items"] == []


def test_game_activity_cursor_is_stable_for_matching_event_times(
    client: TestClient,
):
    user = create_user(client)
    event_at = datetime.now(UTC).isoformat()
    expected_ids = {
        create_notification(
            client,
            user["id"],
            event_at=event_at,
            notification_type="game_updated",
            notification_category="game_activity",
            notification_domain="game",
            source_type="game",
            title=f"Game update {index}",
            subject_label="Pickup game",
            summary="Game update.",
            body="Game update.",
        )["id"]
        for index in range(3)
    }

    authenticate_as(user["id"])
    first_response = client.get("/inbox/game-activity", params={"limit": 2})
    assert first_response.status_code == 200, first_response.text
    first_body = first_response.json()
    assert len(first_body["items"]) == 2
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]

    second_response = client.get(
        "/inbox/game-activity",
        params={"limit": 2, "cursor": first_body["next_cursor"]},
    )
    assert second_response.status_code == 200, second_response.text
    second_body = second_response.json()
    combined_ids = [
        item["source_id"]
        for item in [*first_body["items"], *second_body["items"]]
    ]
    assert set(combined_ids) == expected_ids
    assert len(combined_ids) == len(set(combined_ids))
