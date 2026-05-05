from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models import ChatMessage, Game, GameChat, User
from backend.scripts.demo_data.helpers import demo_uuid, now_utc, upsert_by_id
from backend.scripts.demo_data.users import ADMIN_KEY, PLAYER_KEYS

MESSAGES_PER_CHAT = 5


def seed_game_chats(db: Session, users: dict[str, User], games: dict[str, Game]) -> dict[str, GameChat]:
    seeded_chats: dict[str, GameChat] = {}
    timestamp = now_utc()

    for game_index, (game_key, game) in enumerate(games.items()):
        if not game.is_chat_enabled:
            continue

        chat = upsert_by_id(
            db,
            GameChat,
            demo_uuid(f"game-chat:{game_key}"),
            {
                "game_id": game.id,
                "chat_status": "active",
                "locked_at": None,
                "updated_at": timestamp,
            },
        )
        db.flush()
        seeded_chats[game_key] = chat

        message_data = build_demo_messages(game, game_index, users)

        for message_index, message in enumerate(message_data, start=1):
            message_timestamp = timestamp - message["age"]
            upsert_by_id(
                db,
                ChatMessage,
                demo_uuid(f"chat-message:{game_key}:{message_index}"),
                {
                    "chat_id": chat.id,
                    "sender_user_id": message["sender_user_id"],
                    "message_type": message["message_type"],
                    "message_body": message["message_body"],
                    "is_pinned": message["is_pinned"],
                    "pinned_at": message_timestamp if message["is_pinned"] else None,
                    "pinned_by_user_id": message["sender_user_id"] if message["is_pinned"] else None,
                    "moderation_status": "visible",
                    "created_at": message_timestamp,
                    "updated_at": message_timestamp,
                    "edited_at": None,
                    "deleted_at": None,
                    "deleted_by_user_id": None,
                },
            )

    return seeded_chats


def build_demo_messages(game: Game, game_index: int, users: dict[str, User]) -> list[dict]:
    from datetime import timedelta

    player_one = users[PLAYER_KEYS[game_index % len(PLAYER_KEYS)]]
    player_two = users[PLAYER_KEYS[(game_index + 5) % len(PLAYER_KEYS)]]
    player_three = users[PLAYER_KEYS[(game_index + 11) % len(PLAYER_KEYS)]]
    admin = users[ADMIN_KEY]

    return [
        {
            "age": timedelta(minutes=46),
            "sender_user_id": None,
            "message_type": "system",
            "message_body": game.game_notes or "Bring a white and a dark shirt.",
            "is_pinned": False,
        },
        {
            "age": timedelta(minutes=31),
            "sender_user_id": player_one.id,
            "message_type": "text",
            "message_body": "Is parking pretty easy around there?",
            "is_pinned": False,
        },
        {
            "age": timedelta(minutes=23),
            "sender_user_id": admin.id,
            "message_type": "pinned_update",
            "message_body": game.parking_notes or "Give yourself a few extra minutes for parking.",
            "is_pinned": True,
        },
        {
            "age": timedelta(minutes=12),
            "sender_user_id": player_two.id,
            "message_type": "text",
            "message_body": "Anyone bringing an extra ball?",
            "is_pinned": False,
        },
        {
            "age": timedelta(minutes=4),
            "sender_user_id": player_three.id,
            "message_type": "text",
            "message_body": "I can bring one. See everyone soon.",
            "is_pinned": False,
        },
    ]
