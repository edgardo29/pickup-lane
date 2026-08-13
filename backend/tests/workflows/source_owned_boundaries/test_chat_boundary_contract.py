from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.suite_type("ordinary")

_BASE_TIME = datetime(2035, 2, 1, 18, 0, tzinfo=timezone.utc)


def _user(index: int) -> User:
    from backend.models import User

    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04b1-chat-user-{index}-{uuid.uuid4()}",
        role="player",
        email=f"ws02-04b1-chat-{index}-{uuid.uuid4()}@example.invalid",
        first_name="Chat",
        last_name=f"User-{index}",
        account_status="active",
        hosting_status="eligible",
    )


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _venue() -> Venue:
    from backend.models import Venue

    return Venue(
        id=uuid.uuid4(),
        name="Chat Gym",
        address_line_1="1 Chat Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        is_active=True,
    )


def _game(host: User, venue: Venue) -> Game:
    from backend.models import Game

    return Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="none",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="Chat Boundary Game",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=host.id,
        created_by_user_id=host.id,
        starts_at=_BASE_TIME,
        ends_at=_BASE_TIME + timedelta(hours=2),
        starts_on_local=_BASE_TIME.date(),
        timezone="UTC",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=10,
        price_per_player_cents=0,
        currency="USD",
        policy_mode="custom_hosted",
        published_at=_BASE_TIME - timedelta(days=1),
    )


def _sub_post(owner: User) -> SubPost:
    from backend.models import SubPost

    return SubPost(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        post_status="active",
        public_visibility_status="visible",
        sport_type="soccer",
        format_label="5v5",
        environment_type="indoor",
        skill_level="any",
        game_player_group="coed",
        starts_at=_BASE_TIME,
        ends_at=_BASE_TIME + timedelta(hours=2),
        starts_on_local=_BASE_TIME.date(),
        timezone="UTC",
        location_name="Chat Field",
        address_line_1="1 Chat Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        subs_needed=1,
        price_due_at_venue_cents=0,
        currency="USD",
        expires_at=_BASE_TIME,
    )


def _game_message(
    chat: GameChat,
    sender: User | None,
    index: int,
    *,
    message_type: str = "text",
    visibility_status: str = "visible",
) -> ChatMessage:
    from backend.models import ChatMessage

    removed_at = _BASE_TIME if visibility_status == "removed" else None
    removed_source = "system" if visibility_status == "removed" else None
    return ChatMessage(
        id=uuid.uuid4(),
        chat_id=chat.id,
        sender_user_id=sender.id if sender is not None else None,
        message_type=message_type,
        message_body=f"game message {index}",
        visibility_status=visibility_status,
        review_status="clear",
        removed_at=removed_at,
        removed_source=removed_source,
        created_at=_BASE_TIME + timedelta(seconds=index),
        updated_at=_BASE_TIME + timedelta(seconds=index),
    )


def _sub_message(
    chat: SubPostChat,
    sender: User,
    index: int,
    *,
    visibility_status: str = "visible",
) -> SubPostChatMessage:
    from backend.models import SubPostChatMessage

    removed_at = _BASE_TIME if visibility_status == "removed" else None
    removed_source = "system" if visibility_status == "removed" else None
    return SubPostChatMessage(
        id=uuid.uuid4(),
        chat_id=chat.id,
        sender_user_id=sender.id,
        sender_display_name_snapshot="Chat User",
        sender_initials_snapshot="CU",
        message_type="text",
        message_body=f"sub message {index}",
        visibility_status=visibility_status,
        review_status="clear",
        removed_at=removed_at,
        removed_source=removed_source,
        created_at=_BASE_TIME + timedelta(seconds=index),
        updated_at=_BASE_TIME + timedelta(seconds=index),
    )


@pytest.mark.requirement("WS02-04B1-R7")
def test_game_and_need_a_sub_chat_message_body_boundaries() -> None:
    from backend.services import game_chat_service, sub_post_chat_service

    assert game_chat_service.normalize_message_body("x" * 300) == "x" * 300
    assert sub_post_chat_service.normalize_message_body("x" * 300) == "x" * 300

    for normalize in (game_chat_service.normalize_message_body, sub_post_chat_service.normalize_message_body):
        with pytest.raises(HTTPException) as blank_exc:
            normalize(" \n\t ")
        with pytest.raises(HTTPException) as over_exc:
            normalize("x" * 301)
        assert blank_exc.value.status_code == 400
        assert over_exc.value.status_code == 400


@pytest.mark.requirement("WS02-04B1-R7")
def test_game_chat_page_and_visible_text_history_boundaries() -> None:
    from backend.models import GameChat
    from backend.services import game_chat_service

    with _session() as db:
        sender = _user(1)
        venue = _venue()
        game = _game(sender, venue)
        chat = GameChat(id=uuid.uuid4(), game_id=game.id, chat_status="active")
        db.add(sender)
        db.add(venue)
        db.commit()

        db.add(game)
        db.commit()

        db.add(chat)
        db.commit()

        db.add_all([_game_message(chat, sender, index) for index in range(60)])
        db.commit()

        page = game_chat_service.get_latest_visible_messages(db, chat.id, limit=999)

        assert len(page) == 50

        db.add_all([_game_message(chat, sender, index) for index in range(60, 199)])
        db.add(_game_message(chat, sender, 199, visibility_status="removed"))
        db.add(_game_message(chat, None, 200, message_type="system"))
        db.commit()

        game_chat_service.validate_total_message_limit(db, chat.id)
        db.add(_game_message(chat, sender, 201))
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            game_chat_service.validate_total_message_limit(db, chat.id)
        assert exc_info.value.status_code == 400


@pytest.mark.requirement("WS02-04B1-R7")
def test_need_a_sub_chat_page_and_visible_text_history_boundaries() -> None:
    from backend.models import SubPostChat
    from backend.services import sub_post_chat_service

    with _session() as db:
        sender = _user(1)
        sub_post = _sub_post(sender)
        chat = SubPostChat(id=uuid.uuid4(), sub_post_id=sub_post.id, chat_status="active")
        db.add(sender)
        db.commit()

        db.add(sub_post)
        db.commit()

        db.add(chat)
        db.commit()

        db.add_all([_sub_message(chat, sender, index) for index in range(60)])
        db.commit()

        page = sub_post_chat_service.get_latest_visible_sub_chat_messages(db, chat.id, limit=999)

        assert len(page) == 50

        db.add_all([_sub_message(chat, sender, index) for index in range(60, 199)])
        db.add(_sub_message(chat, sender, 199, visibility_status="removed"))
        db.commit()

        sub_post_chat_service.validate_total_message_limit(db, chat.id)
        db.add(_sub_message(chat, sender, 201))
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            sub_post_chat_service.validate_total_message_limit(db, chat.id)
        assert exc_info.value.status_code == 400


@pytest.mark.requirement("WS02-04B1-R7")
def test_chat_send_workflows_preserve_c3a_rate_limiter_before_total_cap() -> None:
    from backend.services import game_chat_service, sub_post_chat_service

    game_source = inspect.getsource(game_chat_service.create_chat_message_record)
    sub_source = inspect.getsource(sub_post_chat_service.create_sub_post_chat_message_workflow)

    assert game_source.index("validate_sender_rate_limit") < game_source.index("validate_total_message_limit")
    assert sub_source.index("validate_sender_rate_limit") < sub_source.index("validate_total_message_limit")
