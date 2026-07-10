from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from backend.services.notification_policy import (
    NOTIFICATION_IMPLEMENTATION_STATUS_BY_TYPE,
    NOTIFICATION_PREFERENCE_CLASS_BY_TYPE,
    NOTIFICATION_TYPE_CONFIG,
    VALID_NOTIFICATION_PREFERENCE_CLASSES,
)
from backend.services.notification_event_service import (
    build_game_notification_fields,
    reopen_aggregated_notification,
    resolve_aggregated_notification,
)
from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_chat_message,
    create_game,
    create_game_chat,
    create_game_participant,
    create_notification,
    create_sub_post,
    create_user,
    create_venue,
    run_as_temporary_admin,
    set_user_account_status,
    set_user_role,
)


def post_notification_as_admin(
    client: TestClient,
    payload: dict[str, object],
):
    return run_as_temporary_admin(
        client,
        lambda: client.post("/notifications", json=payload),
    )


def patch_notification_as_admin(
    client: TestClient,
    notification_id: str,
    payload: dict[str, object],
):
    return run_as_temporary_admin(
        client,
        lambda: client.patch(f"/notifications/{notification_id}", json=payload),
    )


def notification_contract_fields(
    *,
    source_type: str = "pickup_lane",
    subject_label: str = "Pickup Lane",
    summary: str = "Pickup Lane posted an update.",
    action_key: str | None = None,
    subject_starts_at: str | None = None,
    subject_ends_at: str | None = None,
    subject_timezone: str | None = None,
) -> dict[str, object]:
    fields: dict[str, object] = {
        "source_type": source_type,
        "subject_label": subject_label,
        "summary": summary,
        "event_at": datetime.now(UTC).isoformat(),
    }

    if action_key is not None:
        fields["action_key"] = action_key
    if subject_starts_at is not None:
        fields["subject_starts_at"] = subject_starts_at
    if subject_ends_at is not None:
        fields["subject_ends_at"] = subject_ends_at
    if subject_timezone is not None:
        fields["subject_timezone"] = subject_timezone

    return fields


def admin_notice_payload(user_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "user_id": user_id,
        "notification_type": "admin_notice",
        "notification_category": "app",
        "notification_domain": "admin",
        "title": "CI notification",
        **notification_contract_fields(),
        "body": "CI notification body",
        "is_read": False,
    }
    payload.update(overrides)
    return payload


def game_notification_contract_fields(
    game: dict,
    *,
    summary: str = "New messages were posted.",
    action_key: str | None = "view_game",
) -> dict[str, object]:
    return notification_contract_fields(
        source_type=(
            "official_game" if game["game_type"] == "official" else "community_game"
        ),
        subject_label=game["title"],
        summary=summary,
        action_key=action_key,
        subject_starts_at=game["starts_at"],
        subject_ends_at=game["ends_at"],
        subject_timezone=game["timezone"],
    )


def need_a_sub_notification_contract_fields(
    sub_post: dict,
    *,
    action_key: str | None = "view_sub_post",
    summary: str = "A player requested a sub spot.",
) -> dict[str, object]:
    return notification_contract_fields(
        source_type="need_a_sub",
        subject_label=f"{sub_post['team_name']} {sub_post['format_label']}",
        summary=summary,
        action_key=action_key,
        subject_starts_at=sub_post["starts_at"],
        subject_ends_at=sub_post["ends_at"],
        subject_timezone=sub_post["timezone"],
    )


def create_notification_setup(
    client: TestClient,
) -> tuple[dict, dict, dict, dict, dict, dict]:
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    participant = create_game_participant(client, user["id"], game["id"], booking["id"])
    game_chat = create_game_chat(client, game["id"])
    chat_message = create_chat_message(client, game_chat["id"], user["id"])
    return user, game, booking, participant, game_chat, chat_message


def create_sub_request(
    client: TestClient,
    requester_user_id: str,
    sub_post: dict,
    position_index: int = 0,
) -> dict:
    authenticate_as(requester_user_id)
    response = client.post(
        f"/need-a-sub/posts/{sub_post['id']}/requests",
        json={"sub_post_position_id": sub_post["positions"][position_index]["id"]},
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_payment_record(
    *,
    user_id: str,
    game_id: str,
    booking_id: str,
    payment_status: str = "succeeded",
) -> str:
    from backend.database import SessionLocal
    from backend.models import Payment

    payment_id = uuid4()
    paid_at = datetime.now(UTC) if payment_status == "succeeded" else None

    with SessionLocal() as db:
        db.add(
            Payment(
                id=payment_id,
                payer_user_id=UUID(user_id),
                booking_id=UUID(booking_id),
                game_id=UUID(game_id),
                payment_type="booking",
                provider="stripe",
                provider_payment_intent_id=f"pi_{uuid4().hex}",
                idempotency_key=f"idem_{uuid4().hex}",
                amount_cents=1300,
                currency="USD",
                payment_status=payment_status,
                paid_at=paid_at,
            )
        )
        db.commit()

    return str(payment_id)


def create_refund_record(
    *,
    payment_id: str,
    booking_id: str,
    refund_status: str = "succeeded",
) -> str:
    from backend.database import SessionLocal
    from backend.models import Refund

    refund_id = uuid4()
    refunded_at = datetime.now(UTC) if refund_status == "succeeded" else None

    with SessionLocal() as db:
        db.add(
            Refund(
                id=refund_id,
                payment_id=UUID(payment_id),
                booking_id=UUID(booking_id),
                amount_cents=1300,
                currency="USD",
                refund_reason="game_cancelled",
                refund_status=refund_status,
                provider_refund_id=f"re_{uuid4().hex}",
                refunded_at=refunded_at,
            )
        )
        db.commit()

    return str(refund_id)


def create_sub_post_chat_record(*, sub_post_id: str) -> str:
    from backend.database import SessionLocal
    from backend.models import SubPostChat

    chat_id = uuid4()

    with SessionLocal() as db:
        db.add(
            SubPostChat(
                id=chat_id,
                sub_post_id=UUID(sub_post_id),
                chat_status="active",
            )
        )
        db.commit()

    return str(chat_id)


def create_sub_post_chat_message_record(
    *,
    chat_id: str,
    sender_user_id: str,
    message_body: str = "CI Need a Sub chat message",
) -> str:
    from backend.database import SessionLocal
    from backend.models import SubPostChatMessage

    message_id = uuid4()

    with SessionLocal() as db:
        db.add(
            SubPostChatMessage(
                id=message_id,
                chat_id=UUID(chat_id),
                sender_user_id=UUID(sender_user_id),
                sender_display_name_snapshot="Test User",
                sender_initials_snapshot="TU",
                message_type="text",
                message_body=message_body,
                visibility_status="visible",
                review_status="clear",
            )
        )
        db.commit()

    return str(message_id)


def test_notifications_create_get_list_and_mark_read(client: TestClient):
    user, game, _booking, _participant, game_chat, chat_message = (
        create_notification_setup(client)
    )
    notification = create_notification(
        client,
        user["id"],
        notification_type="chat_message",
        notification_category="game_activity",
        notification_domain="game",
        title="New message",
        body="A new chat message was posted.",
        **game_notification_contract_fields(game),
        related_game_id=game["id"],
        related_chat_id=game_chat["id"],
        related_message_id=chat_message["id"],
    )

    get_response = client.get(f"/notifications/{notification['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == notification["id"]
    assert get_response.json()["related_chat_id"] == game_chat["id"]
    assert get_response.json()["notification_category"] == "game_activity"
    assert get_response.json()["notification_domain"] == "game"
    assert get_response.json()["source_type"] == "official_game"
    assert get_response.json()["source_label"] == "Official Game"
    assert get_response.json()["row_subject"].startswith(f"{game['title']} · ")
    assert get_response.json()["action"]["key"] == "view_game"
    assert get_response.json()["icon"] == "MessageSquareText"
    assert get_response.json()["severity"] == "default"

    list_response = client.get("/notifications/me?notification_category=game_activity")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == notification["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/notifications/{notification['id']}/read",
        json={},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["is_read"] is True
    assert patch_response.json()["read_at"] is not None


def test_notification_type_config_has_preference_classes():
    assert "sub_post_updated" in NOTIFICATION_TYPE_CONFIG
    assert NOTIFICATION_PREFERENCE_CLASS_BY_TYPE["sub_post_updated"] == "mandatory"
    assert "sub_chat_message" in NOTIFICATION_TYPE_CONFIG
    assert (
        NOTIFICATION_PREFERENCE_CLASS_BY_TYPE["sub_chat_message"]
        == "preference_controlled"
    )
    assert NOTIFICATION_IMPLEMENTATION_STATUS_BY_TYPE["booking_cancelled"] == "valid_only"

    for notification_type, config in NOTIFICATION_TYPE_CONFIG.items():
        assert config.preference_class in VALID_NOTIFICATION_PREFERENCE_CLASSES, (
            f"{notification_type} has invalid preference_class "
            f"{config.preference_class}"
        )


def test_notification_builders_can_force_null_action(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)

    from backend.database import SessionLocal
    from backend.models import Game

    with SessionLocal() as db:
        db_game = db.get(Game, UUID(game["id"]))
        assert db_game is not None
        fields = build_game_notification_fields(
            db_game,
            "game_cancelled",
            event_at=datetime.now(UTC),
            force_action_null=True,
        )

    assert fields["action_key"] is None


def test_notifications_hide_game_action_when_game_not_available(
    client: TestClient,
):
    user, game, _booking, _participant, _game_chat, _chat_message = (
        create_notification_setup(client)
    )
    notification = create_notification(
        client,
        user["id"],
        notification_type="game_cancelled",
        notification_category="game_activity",
        notification_domain="game",
        title="Game canceled",
        body="This game was canceled.",
        **game_notification_contract_fields(
            game,
            summary="This game was canceled.",
        ),
        related_game_id=game["id"],
        is_read=False,
    )

    from backend.database import SessionLocal
    from backend.models import Game

    with SessionLocal() as db:
        db_game = db.get(Game, UUID(game["id"]))
        assert db_game is not None
        db_game.publish_status = "draft"
        db.commit()

    response = client.get(f"/notifications/{notification['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["action_key"] == "view_game"
    assert body["action"] is None


def test_notifications_hide_sub_post_action_when_post_not_available(
    client: TestClient,
):
    owner = create_user(client)
    requester = create_user(client)
    sub_post = create_sub_post(client, owner["id"])
    notification = create_notification(
        client,
        requester["id"],
        notification_type="sub_post_updated",
        notification_category="game_activity",
        notification_domain="need_a_sub",
        title="Post updated",
        body="Review the latest details before the game.",
        **need_a_sub_notification_contract_fields(
            sub_post,
            summary="Important details were updated.",
        ),
        related_sub_post_id=sub_post["id"],
        is_read=False,
    )

    authenticate_as(owner["id"])
    cancel_response = client.patch(
        f"/need-a-sub/posts/{sub_post['id']}/cancel",
        json={"cancel_reason": "Test cancellation."},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    authenticate_as(requester["id"])
    response = client.get(f"/notifications/{notification['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["action_key"] == "view_sub_post"
    assert body["action"] is None


def test_reopen_aggregated_notification_reuses_read_row(
    client: TestClient,
):
    user, game, _booking, _participant, _game_chat, _chat_message = (
        create_notification_setup(client)
    )
    aggregation_key = f"game:{game['id']}:user:{user['id']}:game_updated"
    notification = create_notification(
        client,
        user["id"],
        notification_type="game_updated",
        notification_category="game_activity",
        notification_domain="game",
        title="Game updated",
        body="Review the latest game details before you go.",
        **game_notification_contract_fields(
            game,
            summary="Important game details were updated.",
        ),
        related_game_id=game["id"],
        aggregation_key=aggregation_key,
        is_read=False,
    )
    read_response = client.patch(
        f"/notifications/{notification['id']}/read",
        json={},
    )
    assert read_response.status_code == 200, read_response.text
    assert read_response.json()["is_read"] is True

    from backend.database import SessionLocal
    from backend.models import Game

    with SessionLocal() as db:
        db_game = db.get(Game, UUID(game["id"]))
        assert db_game is not None
        values = build_game_notification_fields(
            db_game,
            "game_updated",
            event_at=datetime.now(UTC),
            summary="Important venue details were updated.",
            aggregate_count=4,
        )
        values["related_game_id"] = db_game.id
        reopened = reopen_aggregated_notification(
            db,
            user_id=UUID(user["id"]),
            notification_type="game_updated",
            notification_category="game_activity",
            notification_domain="game",
            aggregation_key=aggregation_key,
            values=values,
            aggregate_count_mode="clear",
        )
        reopened_id = str(reopened.id)
        db.commit()

    response = client.get(f"/notifications/{notification['id']}")

    assert reopened_id == notification["id"]
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == notification["id"]
    assert body["is_read"] is False
    assert body["read_at"] is None
    assert body["summary"] == "Important venue details were updated."
    assert body["aggregate_count"] is None


def test_resolve_aggregated_notification_marks_read_without_event_bump(
    client: TestClient,
):
    user, game, _booking, _participant, _game_chat, _chat_message = (
        create_notification_setup(client)
    )
    aggregation_key = f"game:{game['id']}:user:{user['id']}:request_activity"
    notification = create_notification(
        client,
        user["id"],
        notification_type="game_updated",
        notification_category="game_activity",
        notification_domain="game",
        title="Game updated",
        body="Review the latest game details before you go.",
        **game_notification_contract_fields(
            game,
            summary="Important game details were updated.",
        ),
        related_game_id=game["id"],
        aggregation_key=aggregation_key,
        is_read=False,
    )
    before_response = client.get(f"/notifications/{notification['id']}")
    assert before_response.status_code == 200, before_response.text
    before_event_at = before_response.json()["event_at"]

    from backend.database import SessionLocal

    with SessionLocal() as db:
        resolved = resolve_aggregated_notification(
            db,
            user_id=UUID(user["id"]),
            aggregation_key=aggregation_key,
            values={
                "title": "Request handled",
                "summary": "This request was handled.",
                "body": "This pending request no longer needs review.",
                "action_key": None,
            },
        )
        assert resolved is not None
        db.commit()

    response = client.get(f"/notifications/{notification['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_read"] is True
    assert body["read_at"] is not None
    assert body["event_at"] == before_event_at
    assert body["title"] == "Request handled"
    assert body["summary"] == "This request was handled."
    assert body["action_key"] is None
    assert body["action"] is None


def test_notifications_enforce_unique_aggregation_key_per_user(
    client: TestClient,
):
    user, game, _booking, _participant, _game_chat, _chat_message = (
        create_notification_setup(client)
    )
    aggregation_key = f"game:{game['id']}:user:{user['id']}:game_updated"
    create_notification(
        client,
        user["id"],
        notification_type="game_updated",
        notification_category="game_activity",
        notification_domain="game",
        title="Game updated",
        body="Review the latest game details before you go.",
        **game_notification_contract_fields(
            game,
            summary="Important game details were updated.",
        ),
        related_game_id=game["id"],
        aggregation_key=aggregation_key,
        is_read=False,
    )

    from backend.database import SessionLocal
    from backend.models import Notification

    with SessionLocal() as db:
        db.add(
            Notification(
                id=uuid4(),
                user_id=UUID(user["id"]),
                notification_type="game_updated",
                notification_category="game_activity",
                notification_domain="game",
                source_type=(
                    "official_game"
                    if game["game_type"] == "official"
                    else "community_game"
                ),
                title="Duplicate game updated",
                subject_label=game["title"],
                summary="Important game details were updated.",
                body="Review the latest game details before you go.",
                action_key="view_game",
                subject_starts_at=datetime.fromisoformat(game["starts_at"]),
                subject_ends_at=datetime.fromisoformat(game["ends_at"]),
                subject_timezone=game["timezone"],
                event_at=datetime.now(UTC),
                aggregation_key=aggregation_key,
                related_game_id=UUID(game["id"]),
                is_read=False,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_notifications_reject_empty_title(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = post_notification_as_admin(
        client,
        {
            "user_id": user["id"],
            "notification_type": "admin_notice",
            "notification_category": "app",
            "notification_domain": "admin",
            "title": "   ",
            **notification_contract_fields(),
            "body": "Body is present",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "title must not be empty" in response.text


def test_notifications_reject_missing_event_at(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])
    contract_fields = notification_contract_fields()
    contract_fields.pop("event_at")

    response = post_notification_as_admin(
        client,
        {
            "user_id": user["id"],
            "notification_type": "admin_notice",
            "notification_category": "app",
            "notification_domain": "admin",
            "title": "Missing event time",
            **contract_fields,
            "body": "This should not be accepted.",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "event_at cannot be null" in response.text


def test_notifications_reject_invalid_source_type(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = post_notification_as_admin(
        client,
        {
            "user_id": user["id"],
            "notification_type": "admin_notice",
            "notification_category": "app",
            "notification_domain": "admin",
            "title": "Invalid source",
            **notification_contract_fields(source_type="random"),
            "body": "This should not be accepted.",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "source_type is not supported" in response.text


def test_notifications_reject_subject_start_without_timezone(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = post_notification_as_admin(
        client,
        {
            "user_id": user["id"],
            "notification_type": "admin_notice",
            "notification_category": "app",
            "notification_domain": "admin",
            "title": "Missing subject timezone",
            **notification_contract_fields(
                subject_starts_at=datetime.now(UTC).isoformat(),
            ),
            "body": "This should not be accepted.",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "subject_timezone is required" in response.text


def test_notifications_reject_action_without_target(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = post_notification_as_admin(
        client,
        {
            "user_id": user["id"],
            "notification_type": "admin_notice",
            "notification_category": "app",
            "notification_domain": "admin",
            "title": "Broken action",
            **notification_contract_fields(action_key="view_game"),
            "body": "This should not be accepted.",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "view_game notifications require related_game_id" in response.text


def test_notifications_reject_immutable_update_fields(client: TestClient):
    user = create_user(client)
    notification = create_notification(client, user["id"])

    response = patch_notification_as_admin(
        client,
        notification["id"],
        {"title": "New title"},
    )

    assert response.status_code == 400, response.text
    assert "cannot be changed" in response.text


def test_notifications_reject_booking_mismatched_game(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    first_game = create_game(client, user["id"], venue)
    second_game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], first_game["id"])
    authenticate_as(user["id"])

    response = post_notification_as_admin(
        client,
        {
            "user_id": user["id"],
            "notification_type": "booking_confirmed",
            "notification_category": "game_activity",
            "notification_domain": "game",
            "title": "Booking confirmed",
            **game_notification_contract_fields(second_game),
            "body": "Your booking is confirmed.",
            "related_game_id": second_game["id"],
            "related_booking_id": booking["id"],
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "related_booking_id must belong to related_game_id" in response.text


def test_notifications_support_payment_and_refund_relations(client: TestClient):
    user, game, booking, _participant, _game_chat, _chat_message = (
        create_notification_setup(client)
    )
    payment_id = create_payment_record(
        user_id=user["id"],
        game_id=game["id"],
        booking_id=booking["id"],
    )
    refund_id = create_refund_record(
        payment_id=payment_id,
        booking_id=booking["id"],
    )

    authenticate_as(user["id"])
    response = post_notification_as_admin(
        client,
        {
            "user_id": user["id"],
            "notification_type": "booking_refunded",
            "notification_category": "game_activity",
            "notification_domain": "game",
            "title": "Refund processed",
            **game_notification_contract_fields(
                game,
                summary="Your refund was processed.",
            ),
            "body": "Your refund for this official game was processed.",
            "related_game_id": game["id"],
            "related_booking_id": booking["id"],
            "related_payment_id": payment_id,
            "related_refund_id": refund_id,
            "is_read": False,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["related_payment_id"] == payment_id
    assert body["related_refund_id"] == refund_id

    list_response = client.get(f"/notifications/me?related_payment_id={payment_id}")
    assert list_response.status_code == 200, list_response.text
    assert [item["id"] for item in list_response.json()] == [body["id"]]

    refund_list_response = client.get(f"/notifications/me?related_refund_id={refund_id}")
    assert refund_list_response.status_code == 200, refund_list_response.text
    assert [item["id"] for item in refund_list_response.json()] == [body["id"]]


def test_notifications_reject_payment_mismatched_booking(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    first_game = create_game(client, user["id"], venue)
    second_game = create_game(client, user["id"], venue)
    first_booking = create_booking(client, user["id"], first_game["id"])
    second_booking = create_booking(client, user["id"], second_game["id"])
    payment_id = create_payment_record(
        user_id=user["id"],
        game_id=first_game["id"],
        booking_id=first_booking["id"],
    )

    authenticate_as(user["id"])
    response = post_notification_as_admin(
        client,
        {
            "user_id": user["id"],
            "notification_type": "payment_failed",
            "notification_category": "game_activity",
            "notification_domain": "game",
            "title": "Payment failed",
            **game_notification_contract_fields(
                second_game,
                summary="Your payment could not be completed.",
            ),
            "body": "Your payment for this game could not be completed.",
            "related_game_id": second_game["id"],
            "related_booking_id": second_booking["id"],
            "related_payment_id": payment_id,
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "related_payment_id must belong to related_booking_id" in response.text


def test_notifications_reject_refund_mismatched_payment(client: TestClient):
    user, game, booking, _participant, _game_chat, _chat_message = (
        create_notification_setup(client)
    )
    first_payment_id = create_payment_record(
        user_id=user["id"],
        game_id=game["id"],
        booking_id=booking["id"],
    )
    second_payment_id = create_payment_record(
        user_id=user["id"],
        game_id=game["id"],
        booking_id=booking["id"],
    )
    refund_id = create_refund_record(
        payment_id=first_payment_id,
        booking_id=booking["id"],
    )

    authenticate_as(user["id"])
    response = post_notification_as_admin(
        client,
        {
            "user_id": user["id"],
            "notification_type": "booking_refunded",
            "notification_category": "game_activity",
            "notification_domain": "game",
            "title": "Refund processed",
            **game_notification_contract_fields(
                game,
                summary="Your refund was processed.",
            ),
            "body": "Your refund for this official game was processed.",
            "related_game_id": game["id"],
            "related_booking_id": booking["id"],
            "related_payment_id": second_payment_id,
            "related_refund_id": refund_id,
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "related_refund_id must belong to related_payment_id" in response.text


def test_notifications_unread_clears_read_at(client: TestClient):
    user = create_user(client)
    notification = create_notification(client, user["id"], is_read=True)
    assert notification["read_at"] is not None

    response = patch_notification_as_admin(
        client,
        notification["id"],
        {"is_read": False},
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_read"] is False
    assert response.json()["read_at"] is None


def test_notifications_reject_category_domain_mismatch(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = post_notification_as_admin(
        client,
        {
            "user_id": user["id"],
            "notification_type": "admin_notice",
            "notification_category": "app",
            "notification_domain": "game",
            "title": "Mismatch",
            **notification_contract_fields(
                source_type="game",
                subject_label="CI Test Match",
                summary="This should not be categorized as app.",
            ),
            "body": "This should not be categorized as app.",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "App notifications must use an app notification domain" in response.text


def test_notifications_reject_type_domain_mismatch(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = post_notification_as_admin(
        client,
        {
            "user_id": user["id"],
            "notification_type": "sub_request_received",
            "notification_category": "game_activity",
            "notification_domain": "game",
            "title": "Wrong lane",
            **notification_contract_fields(
                source_type="game",
                subject_label="CI Test Match",
                summary="This should be a Need a Sub notification.",
            ),
            "body": "This should be a Need a Sub notification.",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "Need a Sub notification types" in response.text


def test_notifications_are_scoped_to_owner_unless_admin(client: TestClient):
    owner = create_user(client)
    other_user = create_user(client)
    notification = create_notification(client, owner["id"])

    authenticate_as(other_user["id"])
    get_response = client.get(f"/notifications/{notification['id']}")
    assert get_response.status_code == 404, get_response.text

    patch_response = client.patch(f"/notifications/{notification['id']}/read", json={})
    assert patch_response.status_code == 404, patch_response.text

    list_response = client.get(f"/notifications?user_id={owner['id']}")
    assert list_response.status_code == 403, list_response.text

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])

    admin_get_response = client.get(f"/notifications/{notification['id']}")
    assert admin_get_response.status_code == 200, admin_get_response.text

    admin_list_response = client.get(f"/notifications?user_id={owner['id']}")
    assert admin_list_response.status_code == 200, admin_list_response.text
    assert [item["id"] for item in admin_list_response.json()] == [notification["id"]]


def test_notification_admin_scaffolds_require_named_admin_permissions(
    client: TestClient,
):
    owner = create_user(client)
    notification = create_notification(client, owner["id"])

    authenticate_as(owner["id"])
    player_create_response = client.post(
        "/notifications",
        json=admin_notice_payload(owner["id"]),
    )
    assert player_create_response.status_code == 403, player_create_response.text

    player_list_response = client.get(f"/notifications?user_id={owner['id']}")
    assert player_list_response.status_code == 403, player_list_response.text

    player_update_response = client.patch(
        f"/notifications/{notification['id']}",
        json={"is_read": True},
    )
    assert player_update_response.status_code == 403, player_update_response.text

    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    authenticate_as(moderator["id"])

    moderator_create_response = client.post(
        "/notifications",
        json=admin_notice_payload(owner["id"]),
    )
    assert moderator_create_response.status_code == 403, moderator_create_response.text

    moderator_list_response = client.get(f"/notifications?user_id={owner['id']}")
    assert moderator_list_response.status_code == 403, moderator_list_response.text

    moderator_get_response = client.get(f"/notifications/{notification['id']}")
    assert moderator_get_response.status_code == 404, moderator_get_response.text


def test_admin_notification_debug_routes_require_admin_read_permission(
    client: TestClient,
):
    owner = create_user(client)
    notification = create_notification(client, owner["id"])

    authenticate_as(owner["id"])
    player_list_response = client.get("/admin/notifications")
    assert player_list_response.status_code == 403, player_list_response.text

    player_detail_response = client.get(f"/admin/notifications/{notification['id']}")
    assert player_detail_response.status_code == 403, player_detail_response.text

    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    authenticate_as(moderator["id"])

    moderator_list_response = client.get("/admin/notifications")
    assert moderator_list_response.status_code == 403, moderator_list_response.text

    moderator_detail_response = client.get(
        f"/admin/notifications/{notification['id']}"
    )
    assert moderator_detail_response.status_code == 403, moderator_detail_response.text

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])

    admin_list_response = client.get("/admin/notifications")
    assert admin_list_response.status_code == 200, admin_list_response.text

    admin_detail_response = client.get(f"/admin/notifications/{notification['id']}")
    assert admin_detail_response.status_code == 200, admin_detail_response.text


def test_admin_notification_debug_list_filters_and_paginates(
    client: TestClient,
):
    owner, game, booking, participant, game_chat, chat_message = (
        create_notification_setup(client)
    )
    other_user = create_user(client)
    older_event_at = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    newer_event_at = datetime.now(UTC).isoformat()
    create_notification(
        client,
        other_user["id"],
        event_at=newer_event_at,
        title="Different user notification",
    )
    matching_notification = create_notification(
        client,
        owner["id"],
        notification_type="chat_message",
        notification_category="game_activity",
        notification_domain="game",
        source_type="official_game",
        title="New chat activity",
        subject_label=game["title"],
        summary="New messages were posted.",
        body="New messages were posted for this game.",
        action_key="view_game",
        subject_starts_at=game["starts_at"],
        subject_ends_at=game["ends_at"],
        subject_timezone=game["timezone"],
        event_at=older_event_at,
        aggregation_key=(
            f"game:{game['id']}:chat:{game_chat['id']}:"
            f"user:{owner['id']}:chat_message"
        ),
        related_game_id=game["id"],
        related_chat_id=game_chat["id"],
        related_booking_id=booking["id"],
        related_participant_id=participant["id"],
        related_message_id=chat_message["id"],
    )

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])

    response = client.get(
        "/admin/notifications",
        params={
            "user_id": owner["id"],
            "notification_type": "chat_message",
            "notification_category": "game_activity",
            "notification_domain": "game",
            "source_type": "official_game",
            "is_read": False,
            "action_key": "view_game",
            "related_game_id": game["id"],
            "related_chat_id": game_chat["id"],
            "related_booking_id": booking["id"],
            "related_participant_id": participant["id"],
            "related_message_id": chat_message["id"],
            "offset": 0,
            "limit": 1,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_count"] == 1
    assert body["offset"] == 0
    assert body["limit"] == 1
    assert [item["id"] for item in body["notifications"]] == [
        matching_notification["id"]
    ]
    item = body["notifications"][0]
    assert item["action_state"] == {
        "action_key": "view_game",
        "status": "available",
        "path": f"/games/{game['id']}",
        "disabled_reason": None,
    }
    assert item["audit_action_count"] == 1
    assert item["audit_actions"][0]["action_type"] == "create_notification"


def test_admin_notification_debug_detail_reports_unavailable_actions(
    client: TestClient,
):
    owner, game, *_ = create_notification_setup(client)
    notification = create_notification(
        client,
        owner["id"],
        notification_type="game_updated",
        notification_category="game_activity",
        notification_domain="game",
        source_type="official_game",
        title="Game updated",
        subject_label=game["title"],
        summary="Important game details were updated.",
        body="Review the latest game details before heading out.",
        action_key="view_game",
        subject_starts_at=game["starts_at"],
        subject_ends_at=game["ends_at"],
        subject_timezone=game["timezone"],
        related_game_id=game["id"],
    )

    from backend.database import SessionLocal
    from backend.models import Game

    with SessionLocal() as db:
        db_game = db.get(Game, UUID(game["id"]))
        assert db_game is not None
        db_game.game_status = "cancelled"
        db_game.cancelled_at = datetime.now(UTC)
        db.commit()

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])

    response = client.get(f"/admin/notifications/{notification['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == notification["id"]
    assert body["action"] is None
    assert body["action_state"] == {
        "action_key": "view_game",
        "status": "unavailable",
        "path": None,
        "disabled_reason": None,
    }
    assert body["audit_action_count"] == 1
    assert body["audit_actions"][0]["action_type"] == "create_notification"


def test_admin_notification_debug_rejects_invalid_filters(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])

    response = client.get(
        "/admin/notifications",
        params={"notification_type": "made_up_type"},
    )

    assert response.status_code == 400, response.text
    assert "notification_type is not supported" in response.text


def test_notification_admin_create_and_update_are_audited(client: TestClient):
    from backend.database import SessionLocal
    from backend.models import AdminAction

    owner = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])

    create_response = client.post(
        "/notifications",
        json=admin_notice_payload(owner["id"]),
    )
    assert create_response.status_code == 201, create_response.text
    notification = create_response.json()

    update_response = client.patch(
        f"/notifications/{notification['id']}",
        json={"is_read": True},
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["is_read"] is True

    with SessionLocal() as db:
        actions = (
            db.query(AdminAction)
            .filter(AdminAction.target_notification_id == UUID(notification["id"]))
            .order_by(AdminAction.created_at.asc())
            .all()
        )

    assert [action.action_type for action in actions] == [
        "create_notification",
        "update_notification",
    ]
    assert all(str(action.admin_user_id) == admin["id"] for action in actions)
    assert all(str(action.target_user_id) == owner["id"] for action in actions)
    assert "body" not in actions[0].metadata_
    assert actions[1].metadata_["before"]["is_read"] is False
    assert actions[1].metadata_["after"]["is_read"] is True


def test_suspended_user_keeps_own_notification_inbox_access(client: TestClient):
    user = create_user(client)
    notification = create_notification(client, user["id"])
    set_user_account_status(user["id"], "suspended")
    authenticate_as(user["id"])

    list_response = client.get("/notifications/me")
    assert list_response.status_code == 200, list_response.text

    get_response = client.get(f"/notifications/{notification['id']}")
    assert get_response.status_code == 200, get_response.text

    read_response = client.patch(f"/notifications/{notification['id']}/read", json={})
    assert read_response.status_code == 200, read_response.text
    assert read_response.json()["is_read"] is True


def test_notifications_support_need_a_sub_relations(client: TestClient):
    owner = create_user(client)
    requester = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    sub_post = create_sub_post(client, owner["id"])
    sub_request = create_sub_request(client, requester["id"], sub_post)

    authenticate_as(admin["id"])
    response = post_notification_as_admin(
        client,
        {
            "user_id": owner["id"],
            "notification_type": "sub_request_received",
            "notification_category": "game_activity",
            "notification_domain": "need_a_sub",
            "title": "New sub request",
            **need_a_sub_notification_contract_fields(sub_post),
            "body": "A player requested your Need a Sub spot.",
            "actor_user_id": requester["id"],
            "related_sub_post_id": sub_post["id"],
            "related_sub_post_request_id": sub_request["id"],
            "related_sub_post_position_id": sub_post["positions"][0]["id"],
            "is_read": False,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["notification_category"] == "game_activity"
    assert body["notification_domain"] == "need_a_sub"
    assert body["related_sub_post_id"] == sub_post["id"]
    assert body["related_sub_post_request_id"] == sub_request["id"]
    assert body["related_sub_post_position_id"] == sub_post["positions"][0]["id"]


def test_notifications_support_sub_post_updated_type(client: TestClient):
    owner = create_user(client)
    requester = create_user(client)
    sub_post = create_sub_post(client, owner["id"])

    authenticate_as(requester["id"])
    response = post_notification_as_admin(
        client,
        {
            "user_id": requester["id"],
            "notification_type": "sub_post_updated",
            "notification_category": "game_activity",
            "notification_domain": "need_a_sub",
            "title": "Post updated",
            **need_a_sub_notification_contract_fields(
                sub_post,
                summary="Important details were updated.",
            ),
            "body": "Review the latest details before the game.",
            "related_sub_post_id": sub_post["id"],
            "is_read": False,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["notification_type"] == "sub_post_updated"
    assert body["notification_domain"] == "need_a_sub"
    assert body["related_sub_post_id"] == sub_post["id"]
    assert body["icon"] == "CalendarDays"
    assert body["severity"] == "default"
    assert body["action"]["key"] == "view_sub_post"


def test_notifications_support_sub_chat_message_relations(client: TestClient):
    owner = create_user(client)
    requester = create_user(client)
    sub_post = create_sub_post(client, owner["id"])
    sub_request = create_sub_request(client, requester["id"], sub_post)
    authenticate_as(owner["id"])
    accept_response = client.patch(f"/need-a-sub/requests/{sub_request['id']}/accept")
    assert accept_response.status_code == 200, accept_response.text
    chat_id = create_sub_post_chat_record(sub_post_id=sub_post["id"])
    message_id = create_sub_post_chat_message_record(
        chat_id=chat_id,
        sender_user_id=owner["id"],
    )

    authenticate_as(requester["id"])
    response = post_notification_as_admin(
        client,
        {
            "user_id": requester["id"],
            "notification_type": "sub_chat_message",
            "notification_category": "game_activity",
            "notification_domain": "need_a_sub",
            "title": "New chat message",
            **need_a_sub_notification_contract_fields(
                sub_post,
                summary="New messages were posted.",
            ),
            "body": "New messages were posted in the Need a Sub chat.",
            "related_sub_post_id": sub_post["id"],
            "related_sub_post_chat_id": chat_id,
            "related_sub_post_chat_message_id": message_id,
            "aggregation_key": (
                f"need_a_sub:post:{sub_post['id']}:chat:{chat_id}:"
                f"user:{requester['id']}:sub_chat_message"
            ),
            "aggregate_count": 1,
            "is_read": False,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["notification_type"] == "sub_chat_message"
    assert body["notification_domain"] == "need_a_sub"
    assert body["source_type"] == "need_a_sub"
    assert body["source_label"] == "Need a Sub"
    assert body["related_sub_post_id"] == sub_post["id"]
    assert body["related_sub_post_chat_id"] == chat_id
    assert body["related_sub_post_chat_message_id"] == message_id
    assert body["icon"] == "MessageSquareText"
    assert body["action"]["key"] == "view_sub_post"
    assert body["action"]["disabled"] is False

    chat_list_response = client.get(
        f"/notifications/me?related_sub_post_chat_id={chat_id}"
    )
    assert chat_list_response.status_code == 200, chat_list_response.text
    assert [item["id"] for item in chat_list_response.json()] == [body["id"]]

    message_list_response = client.get(
        f"/notifications/me?related_sub_post_chat_message_id={message_id}"
    )
    assert message_list_response.status_code == 200, message_list_response.text
    assert [item["id"] for item in message_list_response.json()] == [body["id"]]


def test_notifications_reject_sub_chat_message_mismatched_post(
    client: TestClient,
):
    owner = create_user(client)
    requester = create_user(client)
    first_sub_post = create_sub_post(client, owner["id"])
    first_start = datetime.fromisoformat(first_sub_post["starts_at"])
    first_end = datetime.fromisoformat(first_sub_post["ends_at"])
    second_sub_post = create_sub_post(
        client,
        owner["id"],
        starts_at=(first_start + timedelta(days=1)).isoformat(),
        ends_at=(first_end + timedelta(days=1)).isoformat(),
    )
    first_chat_id = create_sub_post_chat_record(sub_post_id=first_sub_post["id"])
    first_message_id = create_sub_post_chat_message_record(
        chat_id=first_chat_id,
        sender_user_id=owner["id"],
    )

    authenticate_as(requester["id"])
    response = post_notification_as_admin(
        client,
        {
            "user_id": requester["id"],
            "notification_type": "sub_chat_message",
            "notification_category": "game_activity",
            "notification_domain": "need_a_sub",
            "title": "New chat message",
            **need_a_sub_notification_contract_fields(
                second_sub_post,
                summary="New messages were posted.",
            ),
            "body": "New messages were posted in the Need a Sub chat.",
            "related_sub_post_id": second_sub_post["id"],
            "related_sub_post_chat_id": first_chat_id,
            "related_sub_post_chat_message_id": first_message_id,
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "related_sub_post_chat_id must belong" in response.text


def test_notifications_reject_mismatched_need_a_sub_relations(client: TestClient):
    owner = create_user(client)
    other_owner = create_user(client)
    requester = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    sub_post = create_sub_post(client, owner["id"])
    other_sub_post = create_sub_post(client, other_owner["id"])
    sub_request = create_sub_request(client, requester["id"], sub_post)

    authenticate_as(admin["id"])
    response = post_notification_as_admin(
        client,
        {
            "user_id": other_owner["id"],
            "notification_type": "sub_request_received",
            "notification_category": "game_activity",
            "notification_domain": "need_a_sub",
            "title": "New sub request",
            **need_a_sub_notification_contract_fields(other_sub_post),
            "body": "A player requested your Need a Sub spot.",
            "actor_user_id": requester["id"],
            "related_sub_post_id": other_sub_post["id"],
            "related_sub_post_request_id": sub_request["id"],
            "related_sub_post_position_id": other_sub_post["positions"][0]["id"],
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert (
        "related_sub_post_request_id must belong to related_sub_post_id"
        in response.text
    )
