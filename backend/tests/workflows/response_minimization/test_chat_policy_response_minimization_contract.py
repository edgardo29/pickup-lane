from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.suite_type("ordinary")

CHICAGO = ZoneInfo("America/Chicago")

GAME_CHAT_PARTICIPANT_ALLOWED = {
    "id",
    "chat_id",
    "sender_user_id",
    "message_type",
    "message_body",
    "is_pinned",
    "pinned_at",
    "created_at",
    "updated_at",
}
SUB_CHAT_PARTICIPANT_ALLOWED = {
    "id",
    "chat_id",
    "sender_user_id",
    "sender_display_name_snapshot",
    "sender_initials_snapshot",
    "sender_is_current_chat_member",
    "sender_status_label",
    "message_type",
    "message_body",
    "created_at",
    "updated_at",
}
CHAT_MODERATION_FIELDS = {
    "visibility_status",
    "review_status",
    "reviewed_at",
    "reviewed_by_user_id",
    "removed_at",
    "removed_by_user_id",
    "removed_source",
    "removed_reason",
    "restored_at",
    "restored_by_user_id",
    "restored_reason",
    "detections",
}
POLICY_PUBLIC_ALLOWED = {
    "id",
    "policy_type",
    "version",
    "title",
    "content_url",
    "content_text",
    "effective_at",
}
POLICY_MANAGEMENT_FIELDS = {
    "retired_at",
    "is_active",
    "created_at",
    "updated_at",
}


def _session() -> Session:
    from backend.database import SessionLocal

    return SessionLocal()


def _create_user(
    db: Session,
    *,
    role: str = "player",
    email_prefix: str = "b2-chat",
):
    from backend.models import User

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        auth_user_id=f"{email_prefix}-{user_id}",
        role=role,
        email=f"{email_prefix}-{user_id}@example.invalid",
        email_verified_at=datetime.now(UTC),
        first_name="B2",
        last_name="Chat",
        account_status="active",
        hosting_status="eligible",
    )
    db.add(user)
    db.flush()
    return user


def _create_venue(db: Session, *, admin_user):
    from backend.models import Venue

    venue = Venue(
        id=uuid.uuid4(),
        name="B2 Chat Park",
        address_line_1="600 Message Ln",
        city="Chicago",
        state="IL",
        postal_code="60604",
        country_code="US",
        venue_status="approved",
        is_active=True,
        created_by_user_id=admin_user.id,
        approved_by_user_id=admin_user.id,
        approved_at=datetime.now(UTC),
    )
    db.add(venue)
    db.flush()
    return venue


def _create_game(db: Session, *, host_user, admin_user, venue):
    from backend.models import Game

    starts_at = datetime.now(UTC).replace(microsecond=0) + timedelta(days=8)
    game = Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="external_host",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="B2 Chat Game",
        description="Chat response proof.",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot="600 Message Ln, Chicago, IL 60604",
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        neighborhood_snapshot=None,
        host_user_id=host_user.id,
        created_by_user_id=admin_user.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        starts_on_local=starts_at.astimezone(CHICAGO).date(),
        timezone="America/Chicago",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="outdoor",
        total_spots=12,
        price_per_player_cents=1400,
        currency="USD",
        minimum_age=18,
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=4,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="custom_hosted",
        published_at=datetime.now(UTC),
    )
    db.add(game)
    db.flush()
    return game


def _create_game_chat_rows(db: Session, *, host, player, admin):
    from backend.models import ChatMessage, GameChat, GameParticipant

    venue = _create_venue(db, admin_user=admin)
    game = _create_game(db, host_user=host, admin_user=admin, venue=venue)
    participant = GameParticipant(
        id=uuid.uuid4(),
        game_id=game.id,
        participant_type="registered_user",
        user_id=player.id,
        display_name_snapshot="B2 Chat Player",
        participant_status="confirmed",
        attendance_status="unknown",
        cancellation_type="none",
        price_cents=game.price_per_player_cents,
        currency="USD",
        roster_order=1,
        confirmed_at=datetime.now(UTC),
    )
    chat = GameChat(id=uuid.uuid4(), game_id=game.id, chat_status="active")
    message = ChatMessage(
        id=uuid.uuid4(),
        chat_id=chat.id,
        sender_user_id=player.id,
        message_type="text",
        message_body="Visible logistics message",
        is_pinned=False,
        visibility_status="visible",
        review_status="needs_review",
    )
    db.add_all([participant, chat])
    db.flush()
    db.add(message)
    db.flush()
    return chat, message


def _create_sub_post_chat_rows(db: Session, *, owner, player):
    from backend.models import (
        SubPost,
        SubPostChat,
        SubPostChatMessage,
        SubPostPosition,
        SubPostRequest,
    )

    starts_at = datetime.now(UTC).replace(microsecond=0) + timedelta(days=9)
    sub_post = SubPost(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        post_status="active",
        public_visibility_status="visible",
        sport_type="soccer",
        format_label="5v5",
        environment_type="outdoor",
        skill_level="any",
        game_player_group="coed",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        starts_on_local=starts_at.astimezone(CHICAGO).date(),
        timezone="America/Chicago",
        location_name="B2 Sub Field",
        address_line_1="700 Sub Ave",
        city="Chicago",
        state="IL",
        postal_code="60605",
        country_code="US",
        subs_needed=1,
        price_due_at_venue_cents=0,
        currency="USD",
        expires_at=starts_at - timedelta(hours=12),
    )
    position = SubPostPosition(
        id=uuid.uuid4(),
        sub_post_id=sub_post.id,
        position_label="field_player",
        player_group="open",
        spots_needed=1,
        sort_order=0,
    )
    request = SubPostRequest(
        id=uuid.uuid4(),
        sub_post_id=sub_post.id,
        sub_post_position_id=position.id,
        requester_user_id=player.id,
        request_status="confirmed",
        confirmed_at=datetime.now(UTC),
    )
    chat = SubPostChat(id=uuid.uuid4(), sub_post_id=sub_post.id, chat_status="active")
    message = SubPostChatMessage(
        id=uuid.uuid4(),
        chat_id=chat.id,
        sender_user_id=player.id,
        sender_display_name_snapshot="B2 Sub Player",
        sender_initials_snapshot="BS",
        message_type="text",
        message_body="I can cover the wing.",
        visibility_status="visible",
        review_status="needs_review",
    )
    db.add(sub_post)
    db.flush()
    db.add(position)
    db.flush()
    db.add_all([request, chat])
    db.flush()
    db.add(message)
    db.flush()
    return sub_post, chat, message


def _create_policy_document(db: Session):
    from backend.models import PolicyDocument

    policy = PolicyDocument(
        id=uuid.uuid4(),
        policy_type="terms_of_service",
        version=f"b2-{uuid.uuid4().hex[:8]}",
        title="B2 Terms",
        content_url=None,
        content_text="Public policy content.",
        effective_at=datetime.now(UTC) - timedelta(days=1),
        is_active=True,
    )
    db.add(policy)
    db.flush()
    return policy


def _install_active_user_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import require_active_user

    app.dependency_overrides[require_active_user] = lambda: user


def _commit_and_detach(db: Session, *objects: object) -> None:
    db.commit()
    for item in objects:
        db.refresh(item)
        db.expunge(item)


def _route(method: str, path: str) -> APIRoute:
    from backend.main import app

    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


@pytest.mark.requirement("WS02-05B2-R6")
def test_participant_game_and_need_a_sub_chat_responses_filter_moderation_fields(
    client: TestClient,
) -> None:
    with _session() as db:
        host = _create_user(db, email_prefix="b2-chat-host")
        player = _create_user(db, email_prefix="b2-chat-player")
        admin = _create_user(db, role="admin", email_prefix="b2-chat-admin")
        game_chat, game_message = _create_game_chat_rows(
            db,
            host=host,
            player=player,
            admin=admin,
        )
        sub_post, _sub_chat, sub_message = _create_sub_post_chat_rows(
            db,
            owner=host,
            player=player,
        )
        game_chat_id = game_chat.id
        game_message_id = game_message.id
        sub_post_id = sub_post.id
        sub_message_id = sub_message.id
        _commit_and_detach(db, player)

    _install_active_user_override(player)

    game_message_response = client.get(f"/chat-messages/{game_message_id}")
    assert game_message_response.status_code == 200
    game_message_data = game_message_response.json()
    assert set(game_message_data) == GAME_CHAT_PARTICIPANT_ALLOWED
    assert CHAT_MODERATION_FIELDS.isdisjoint(game_message_data)

    game_list_response = client.get(f"/chat-messages?chat_id={game_chat_id}")
    assert game_list_response.status_code == 200
    listed_game_message = next(
        item for item in game_list_response.json() if item["id"] == str(game_message_id)
    )
    assert set(listed_game_message) == GAME_CHAT_PARTICIPANT_ALLOWED

    sub_messages_response = client.get(f"/need-a-sub/posts/{sub_post_id}/chat/messages")
    assert sub_messages_response.status_code == 200
    sub_message_data = next(
        item for item in sub_messages_response.json() if item["id"] == str(sub_message_id)
    )
    assert set(sub_message_data) == SUB_CHAT_PARTICIPANT_ALLOWED
    assert CHAT_MODERATION_FIELDS.isdisjoint(sub_message_data)
    assert sub_message_data["sender_is_current_chat_member"] is True


@pytest.mark.requirement("WS02-05B2-R7")
def test_public_policy_document_reads_expose_display_version_fields_only(
    client: TestClient,
) -> None:
    with _session() as db:
        policy = _create_policy_document(db)
        policy_id = policy.id
        policy_type = policy.policy_type
        db.commit()

    detail_response = client.get(f"/policy-documents/{policy_id}")
    assert detail_response.status_code == 200
    detail_data = detail_response.json()
    assert set(detail_data) == POLICY_PUBLIC_ALLOWED
    assert POLICY_MANAGEMENT_FIELDS.isdisjoint(detail_data)
    assert detail_data["policy_type"] == policy_type

    list_response = client.get(f"/policy-documents?policy_type={policy_type}&is_active=true")
    assert list_response.status_code == 200
    listed_policy = next(item for item in list_response.json() if item["id"] == str(policy_id))
    assert set(listed_policy) == POLICY_PUBLIC_ALLOWED


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS02-05B2-R6")
@pytest.mark.requirement("WS02-05B2-R7")
def test_chat_and_policy_routes_declare_participant_public_and_admin_models() -> None:
    from backend.schemas import (
        AdminChatMessageListRead,
        ChatMessageParticipantRead,
        PolicyDocumentPublicRead,
        SubPostChatMessageParticipantRead,
    )
    from backend.schemas.admin_chat_moderation_schema import AdminChatMessageRead

    admin_chat_fields = set(AdminChatMessageRead.model_fields)
    assert {
        "visibility_status",
        "review_status",
        "reviewed_by_user_id",
        "removed_by_user_id",
        "removed_source",
        "restored_by_user_id",
        "detections",
    }.issubset(admin_chat_fields)

    assert _route("GET", "/chat-messages").response_model == list[
        ChatMessageParticipantRead
    ]
    assert (
        _route("GET", "/chat-messages/{chat_message_id}").response_model
        is ChatMessageParticipantRead
    )
    assert _route("GET", "/need-a-sub/posts/{sub_post_id}/chat/messages").response_model == list[
        SubPostChatMessageParticipantRead
    ]
    assert _route("POST", "/need-a-sub/posts/{sub_post_id}/chat/messages").response_model is (
        SubPostChatMessageParticipantRead
    )
    assert _route("GET", "/policy-documents").response_model == list[
        PolicyDocumentPublicRead
    ]
    assert _route("GET", "/policy-documents/{policy_document_id}").response_model is (
        PolicyDocumentPublicRead
    )
    assert _route("GET", "/admin/community-games/{game_id}/chat/messages").response_model is (
        AdminChatMessageListRead
    )
    assert _route("GET", "/admin/need-a-sub/{post_id}/chat/messages").response_model is (
        AdminChatMessageListRead
    )
