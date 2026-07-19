import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    ChatMessage,
    Game,
    GameChat,
    GameChatMessageDetection,
    GameChatRead,
    GameParticipant,
    Notification,
    User,
)
from backend.schemas.chat_message_schema import ChatMessageCreate
from backend.schemas.game_chat_schema import (
    GameChatCreate,
    GameChatEnsureCreate,
    GameChatRead as GameChatReadSchema,
    GameChatUpdate,
)
from backend.schemas.game_chat_read_schema import GameChatReadStateRead
from backend.services.admin_action_service import record_admin_action
from backend.services.auth_service import user_is_active_admin
from backend.services.chat_moderation_service import (
    build_safe_message_preview,
    detect_chat_message,
)
from backend.services.game_participant_rules import ROSTER_USER_PARTICIPANT_TYPES
from backend.services.game_rules import OPEN_GAME_STATUSES
from backend.services.moderation_surfacing_service import surface_game_chat_message_text
from backend.services.notification_event_service import (
    build_game_notification_fields,
    reopen_aggregated_notification,
    resolve_aggregated_notification,
)

logger = logging.getLogger(__name__)

CHAT_MEMBER_STATUSES = {"confirmed"}
VALID_CHAT_STATUSES = {"active", "closed"}
TERMINAL_CHAT_STATUSES = {"closed"}
MAX_CHAT_MESSAGE_LENGTH = 300
MAX_CHAT_MESSAGES_PER_PAGE = 50
MAX_CHAT_MESSAGES_TOTAL = 200
MAX_CHAT_MESSAGES_PER_MINUTE = 5
VALID_VISIBILITY_STATUSES = {"visible", "removed"}
VALID_REVIEW_STATUSES = {"clear", "needs_review", "reviewed"}


def build_game_chat_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_game_chats_game_id" in error_text:
        return "This game already has a chat room."

    return error_text


def get_active_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


def get_effective_user(
    db: Session,
    acting_user_id: uuid.UUID | None,
    current_user: User | None,
) -> User:
    if current_user is not None:
        return current_user

    if acting_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to use game chat.",
        )

    db_user = db.get(User, acting_user_id)
    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return db_user


def serialize_game_chat(
    db_game_chat: GameChat,
    unread_count: int = 0,
    last_read_at: datetime | None = None,
) -> GameChatReadSchema:
    return GameChatReadSchema(
        id=db_game_chat.id,
        game_id=db_game_chat.game_id,
        chat_status=db_game_chat.chat_status,
        created_at=db_game_chat.created_at,
        updated_at=db_game_chat.updated_at,
        closed_at=db_game_chat.closed_at,
        message_count=db_game_chat.message_count,
        needs_review_count=db_game_chat.needs_review_count,
        removed_count=db_game_chat.removed_count,
        latest_message_id=db_game_chat.latest_message_id,
        latest_message_preview=db_game_chat.latest_message_preview,
        latest_message_at=db_game_chat.latest_message_at,
        unread_count=unread_count,
        last_read_at=last_read_at,
    )


def validate_game_chat_business_rules(chat_data: dict[str, object]) -> None:
    for field_name in ("game_id", "chat_status"):
        if chat_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if chat_data["chat_status"] not in VALID_CHAT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chat_status must be 'active' or 'closed'.",
        )


def normalize_game_chat_lifecycle_fields(
    chat_data: dict[str, object],
    existing_game_chat: GameChat | None = None,
) -> dict[str, object]:
    normalized_data = dict(chat_data)

    if normalized_data["chat_status"] == "closed":
        normalized_data["closed_at"] = (
            normalized_data.get("closed_at")
            or (existing_game_chat.closed_at if existing_game_chat is not None else None)
            or datetime.now(timezone.utc)
        )
    else:
        normalized_data["closed_at"] = None

    return normalized_data


def validate_game_chat_references(db: Session, chat_data: dict[str, object]) -> None:
    db_game = get_active_game_or_404(db, chat_data["game_id"])

    if not db_game.is_chat_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game does not have chat enabled.",
        )

    if db_game.publish_status == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Archived games cannot create chat rooms.",
        )

    if db_game.game_status not in OPEN_GAME_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active games can create chat rooms.",
        )


def validate_game_chat_is_editable(db_game_chat: GameChat) -> None:
    if db_game_chat.chat_status in TERMINAL_CHAT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Closed game chats cannot be updated.",
        )


def create_game_chat_record(
    db: Session,
    game_chat: GameChatCreate,
    current_admin: User,
) -> GameChat:
    chat_data = normalize_game_chat_lifecycle_fields(game_chat.model_dump())
    validate_game_chat_business_rules(chat_data)
    validate_game_chat_references(db, chat_data)

    new_game_chat = GameChat(
        id=uuid.uuid4(),
        **chat_data,
    )

    try:
        db.add(new_game_chat)
        db.flush()
        record_admin_action(
            db,
            admin_user_id=current_admin.id,
            action_type="create_game_chat",
            target_game_id=new_game_chat.game_id,
            metadata={
                "after": {
                    "chat_id": str(new_game_chat.id),
                    "chat_status": new_game_chat.chat_status,
                }
            },
        )
        db.commit()
        db.refresh(new_game_chat)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_chat_conflict_detail(exc),
        ) from exc

    return new_game_chat


def list_game_chat_records(
    db: Session,
    *,
    game_id: uuid.UUID | None = None,
    chat_status: str | None = None,
) -> list[GameChat]:
    statement = select(GameChat)

    if game_id is not None:
        statement = statement.where(GameChat.game_id == game_id)

    if chat_status is not None:
        if chat_status not in VALID_CHAT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="chat_status must be 'active' or 'closed'.",
            )
        statement = statement.where(GameChat.chat_status == chat_status)

    game_chats = db.scalars(statement.order_by(GameChat.created_at.desc())).all()
    return list(game_chats)


def update_game_chat_record(
    db: Session,
    game_chat_id: uuid.UUID,
    game_chat_update: GameChatUpdate,
    current_admin: User,
) -> GameChat:
    db_game_chat = get_game_chat_or_404(db, game_chat_id)
    validate_game_chat_is_editable(db_game_chat)
    update_data = game_chat_update.model_dump(exclude_unset=True)
    before_state = {
        "chat_id": str(db_game_chat.id),
        "chat_status": db_game_chat.chat_status,
        "closed_at": (
            db_game_chat.closed_at.isoformat()
            if db_game_chat.closed_at is not None
            else None
        ),
    }

    if "game_id" in update_data and update_data["game_id"] != db_game_chat.game_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="game_id cannot be changed for an existing game chat.",
        )

    effective_chat_data = {
        "game_id": db_game_chat.game_id,
        "chat_status": update_data.get("chat_status", db_game_chat.chat_status),
        "closed_at": update_data.get("closed_at", db_game_chat.closed_at),
    }
    effective_chat_data = normalize_game_chat_lifecycle_fields(
        effective_chat_data,
        db_game_chat,
    )
    validate_game_chat_business_rules(effective_chat_data)
    get_active_game_or_404(db, db_game_chat.game_id)
    update_data["closed_at"] = effective_chat_data["closed_at"]

    for field_name, field_value in update_data.items():
        setattr(db_game_chat, field_name, field_value)

    db_game_chat.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_game_chat)
        db.flush()
        record_admin_action(
            db,
            admin_user_id=current_admin.id,
            action_type="update_game_chat",
            target_game_id=db_game_chat.game_id,
            metadata={
                "before": before_state,
                "after": {
                    "chat_id": str(db_game_chat.id),
                    "chat_status": db_game_chat.chat_status,
                    "closed_at": (
                        db_game_chat.closed_at.isoformat()
                        if db_game_chat.closed_at is not None
                        else None
                    ),
                },
            },
        )
        db.commit()
        db.refresh(db_game_chat)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_chat_conflict_detail(exc),
        ) from exc

    return db_game_chat


def get_game_chat_or_404(db: Session, chat_id: uuid.UUID) -> GameChat:
    db_game_chat = db.get(GameChat, chat_id)

    if db_game_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game chat not found.",
        )

    return db_game_chat


def get_chat_game_or_404(db: Session, game_chat: GameChat) -> Game:
    db_game = db.get(Game, game_chat.game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


def get_or_create_active_game_chat(db: Session, db_game: Game) -> GameChat:
    if not db_game.is_chat_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game does not have chat enabled.",
        )

    if db_game.publish_status == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Archived games cannot create chat rooms.",
        )

    if db_game.game_status not in OPEN_GAME_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active games can create chat rooms.",
        )

    existing_chat = db.scalar(
        select(GameChat).where(
            GameChat.game_id == db_game.id,
            GameChat.chat_status == "active",
        )
    )

    if existing_chat is not None:
        return existing_chat

    new_chat = GameChat(
        id=uuid.uuid4(),
        game_id=db_game.id,
        chat_status="active",
    )
    db.add(new_chat)
    db.flush()
    return new_chat


def ensure_game_chat_for_game_workflow(
    db: Session,
    game_id: uuid.UUID,
    payload: GameChatEnsureCreate,
    current_user: User,
) -> GameChatReadSchema:
    db_game = get_active_game_or_404(db, game_id)
    effective_user = get_effective_user(db, payload.acting_user_id, current_user)

    if not db_game.is_chat_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game does not have chat enabled.",
        )

    db_game_chat = get_or_create_active_game_chat(db, db_game)
    require_chat_member(db, db_game_chat, effective_user)

    try:
        db.commit()
        db.refresh(db_game_chat)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_chat_conflict_detail(exc),
        ) from exc

    read_state, unread_count = get_chat_read_state(db, db_game_chat, effective_user)
    return serialize_game_chat(
        db_game_chat,
        unread_count=unread_count,
        last_read_at=read_state.last_read_at if read_state else None,
    )


def require_chat_member(db: Session, game_chat: GameChat, user: User) -> Game:
    db_game = get_chat_game_or_404(db, game_chat)

    if not db_game.is_chat_enabled or game_chat.chat_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This game chat is not available.",
        )

    if is_chat_member(db, db_game, user.id):
        return db_game

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only confirmed players and the host can use game chat.",
    )


def require_chat_member_for_message_change(
    db: Session,
    game_chat: GameChat,
    user: User,
) -> Game:
    db_game = get_chat_game_or_404(db, game_chat)

    if not db_game.is_chat_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This game chat is not available.",
        )

    if not is_chat_member(db, db_game, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only confirmed players and the host can use game chat.",
        )

    if game_chat.chat_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game chat cannot receive message changes.",
        )

    return db_game


def is_chat_member(db: Session, db_game: Game, user_id: uuid.UUID) -> bool:
    if db_game.host_user_id == user_id:
        return True

    participant = db.scalar(
        select(GameParticipant.id).where(
            GameParticipant.game_id == db_game.id,
            GameParticipant.user_id == user_id,
            GameParticipant.participant_type.in_(ROSTER_USER_PARTICIPANT_TYPES),
            GameParticipant.participant_status.in_(CHAT_MEMBER_STATUSES),
        )
    )

    return participant is not None


def list_chat_member_user_ids(
    db: Session,
    db_game: Game,
    exclude_user_id: uuid.UUID | None = None,
) -> list[uuid.UUID]:
    user_ids = set()

    if db_game.host_user_id is not None:
        user_ids.add(db_game.host_user_id)

    participant_user_ids = db.scalars(
        select(GameParticipant.user_id).where(
            GameParticipant.game_id == db_game.id,
            GameParticipant.user_id.is_not(None),
            GameParticipant.participant_type.in_(ROSTER_USER_PARTICIPANT_TYPES),
            GameParticipant.participant_status.in_(CHAT_MEMBER_STATUSES),
        )
    ).all()
    user_ids.update(user_id for user_id in participant_user_ids if user_id is not None)

    if exclude_user_id is not None:
        user_ids.discard(exclude_user_id)

    return list(user_ids)


def chat_message_aggregation_key(
    game_id: uuid.UUID,
    chat_id: uuid.UUID,
    recipient_user_id: uuid.UUID,
) -> str:
    return f"game:{game_id}:chat:{chat_id}:user:{recipient_user_id}:chat_message"


def normalize_message_body(message_body: str) -> str:
    normalized_body = " ".join(message_body.strip().split())

    if not normalized_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message_body must not be empty.",
        )

    if len(normalized_body) > MAX_CHAT_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"message_body must be {MAX_CHAT_MESSAGE_LENGTH} characters or fewer.",
        )

    return normalized_body


def validate_sender_rate_limit(
    db: Session,
    chat_id: uuid.UUID,
    sender_user_id: uuid.UUID,
    current_time: datetime,
) -> None:
    window_start = ensure_timezone(current_time) - timedelta(minutes=1)
    message_count = db.scalar(
        select(func.count())
        .select_from(ChatMessage)
        .where(
            ChatMessage.chat_id == chat_id,
            ChatMessage.sender_user_id == sender_user_id,
            ChatMessage.message_type == "text",
            ChatMessage.visibility_status == "visible",
            ChatMessage.created_at >= window_start,
        )
    ) or 0

    if message_count >= MAX_CHAT_MESSAGES_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Slow down before sending another game chat message.",
        )


def validate_total_message_limit(db: Session, chat_id: uuid.UUID) -> None:
    message_count = db.scalar(
        select(func.count())
        .select_from(ChatMessage)
        .where(
            ChatMessage.chat_id == chat_id,
            ChatMessage.message_type == "text",
            ChatMessage.visibility_status == "visible",
        )
    ) or 0

    if message_count >= MAX_CHAT_MESSAGES_TOTAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game chat has reached its message limit.",
        )


def sender_repeated_message(
    db: Session,
    chat_id: uuid.UUID,
    sender_user_id: uuid.UUID,
    message_body: str,
    *,
    exclude_message_id: uuid.UUID | None = None,
) -> bool:
    statement = select(ChatMessage.message_body).where(
        ChatMessage.chat_id == chat_id,
        ChatMessage.sender_user_id == sender_user_id,
        ChatMessage.message_type == "text",
        ChatMessage.visibility_status == "visible",
    )
    if exclude_message_id is not None:
        statement = statement.where(ChatMessage.id != exclude_message_id)

    latest_body = db.scalar(
        statement.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(1)
    )
    return (
        latest_body is not None
        and latest_body.strip().casefold() == message_body.strip().casefold()
    )


def get_latest_visible_messages(
    db: Session,
    chat_id: uuid.UUID,
    limit: int = MAX_CHAT_MESSAGES_PER_PAGE,
) -> list[ChatMessage]:
    page_limit = max(1, min(limit, MAX_CHAT_MESSAGES_PER_PAGE))
    messages = db.scalars(
        select(ChatMessage)
        .where(
            ChatMessage.chat_id == chat_id,
            ChatMessage.visibility_status == "visible",
        )
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(page_limit)
    ).all()

    return list(reversed(messages))


def get_chat_read_state(
    db: Session,
    game_chat: GameChat,
    user: User,
) -> tuple[GameChatRead | None, int]:
    read_state = db.scalar(
        select(GameChatRead).where(
            GameChatRead.chat_id == game_chat.id,
            GameChatRead.user_id == user.id,
        )
    )

    unread_count = count_unread_messages(db, game_chat.id, user.id, read_state)
    return read_state, unread_count


def get_game_chat_read_state_record(
    db: Session,
    game_chat_id: uuid.UUID,
    acting_user_id: uuid.UUID | None,
    current_user: User,
) -> GameChatReadStateRead:
    db_game_chat = get_game_chat_or_404(db, game_chat_id)
    effective_user = get_effective_user(db, acting_user_id, current_user)
    require_chat_member(db, db_game_chat, effective_user)
    read_state, unread_count = get_chat_read_state(db, db_game_chat, effective_user)

    return GameChatReadStateRead(
        chat_id=db_game_chat.id,
        user_id=effective_user.id,
        last_read_at=read_state.last_read_at if read_state else None,
        last_read_message_id=read_state.last_read_message_id if read_state else None,
        unread_count=unread_count,
    )


def mark_game_chat_read_workflow(
    db: Session,
    game_chat_id: uuid.UUID,
    payload: GameChatEnsureCreate,
    current_user: User,
) -> GameChatReadStateRead:
    db_game_chat = get_game_chat_or_404(db, game_chat_id)
    effective_user = get_effective_user(db, payload.acting_user_id, current_user)
    require_chat_member(db, db_game_chat, effective_user)
    read_state = mark_chat_read(db, db_game_chat, effective_user)

    try:
        db.commit()
        db.refresh(read_state)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_chat_conflict_detail(exc),
        ) from exc

    return GameChatReadStateRead(
        chat_id=db_game_chat.id,
        user_id=effective_user.id,
        last_read_at=read_state.last_read_at,
        last_read_message_id=read_state.last_read_message_id,
        unread_count=0,
    )


def count_unread_messages(
    db: Session,
    chat_id: uuid.UUID,
    user_id: uuid.UUID,
    read_state: GameChatRead | None,
) -> int:
    statement = select(func.count(ChatMessage.id)).where(
        ChatMessage.chat_id == chat_id,
        ChatMessage.visibility_status == "visible",
        ChatMessage.sender_user_id != user_id,
    )

    if read_state is not None:
        statement = statement.where(
            ChatMessage.created_at > ensure_timezone(read_state.last_read_at)
        )

    return int(db.scalar(statement) or 0)


def mark_chat_read(
    db: Session,
    game_chat: GameChat,
    user: User,
    now: datetime | None = None,
) -> GameChatRead:
    effective_now = now or datetime.now(timezone.utc)
    last_message_id = db.scalar(
        select(ChatMessage.id)
        .where(
            ChatMessage.chat_id == game_chat.id,
            ChatMessage.visibility_status == "visible",
        )
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(1)
    )
    read_state = db.scalar(
        select(GameChatRead).where(
            GameChatRead.chat_id == game_chat.id,
            GameChatRead.user_id == user.id,
        )
    )

    if read_state is None:
        read_state = GameChatRead(
            id=uuid.uuid4(),
            chat_id=game_chat.id,
            user_id=user.id,
            last_read_at=effective_now,
            last_read_message_id=last_message_id,
            created_at=effective_now,
            updated_at=effective_now,
        )
    else:
        read_state.last_read_at = effective_now
        read_state.last_read_message_id = last_message_id
        read_state.updated_at = effective_now

    db.add(read_state)
    mark_chat_notifications_read(db, game_chat, user.id, effective_now)
    return read_state


def mark_chat_notifications_read(
    db: Session,
    game_chat: GameChat,
    user_id: uuid.UUID,
    now: datetime,
) -> None:
    resolve_aggregated_notification(
        db,
        user_id=user_id,
        aggregation_key=chat_message_aggregation_key(
            game_chat.game_id,
            game_chat.id,
            user_id,
        ),
        values={"aggregate_count": None},
        read_at=now,
    )


def create_or_update_chat_notifications(
    db: Session,
    db_game: Game,
    game_chat: GameChat,
    chat_message: ChatMessage,
    sender_user: User,
    now: datetime,
) -> None:
    recipient_user_ids = list_chat_member_user_ids(
        db,
        db_game,
        exclude_user_id=sender_user.id,
    )

    for recipient_user_id in recipient_user_ids:
        aggregation_key = chat_message_aggregation_key(
            db_game.id,
            game_chat.id,
            recipient_user_id,
        )
        notification_fields = build_game_notification_fields(
            db_game,
            "chat_message",
            event_at=now,
            aggregation_key=aggregation_key,
        )
        notification_fields.update(
            {
                "actor_user_id": sender_user.id,
                "related_game_id": db_game.id,
                "related_chat_id": game_chat.id,
                "related_message_id": chat_message.id,
            }
        )
        reopen_aggregated_notification(
            db,
            user_id=recipient_user_id,
            notification_type="chat_message",
            notification_category="game_activity",
            notification_domain="game",
            aggregation_key=aggregation_key,
            values=notification_fields,
            aggregate_count_mode="increment",
        )


def reconcile_game_chat_notifications_after_moderation(
    db: Session,
    *,
    db_chat: GameChat,
    moderated_at: datetime,
) -> None:
    notifications = db.scalars(
        select(Notification).where(
            Notification.related_chat_id == db_chat.id,
            Notification.notification_type == "chat_message",
        )
    ).all()

    for notification in notifications:
        read_state = db.scalar(
            select(GameChatRead).where(
                GameChatRead.chat_id == db_chat.id,
                GameChatRead.user_id == notification.user_id,
            )
        )
        unread_filters = [
            ChatMessage.chat_id == db_chat.id,
            ChatMessage.visibility_status == "visible",
            ChatMessage.sender_user_id != notification.user_id,
        ]
        if read_state is not None:
            unread_filters.append(
                ChatMessage.created_at > ensure_timezone(read_state.last_read_at)
            )

        unread_count = (
            db.scalar(
                select(func.count())
                .select_from(ChatMessage)
                .where(*unread_filters)
            )
            or 0
        )
        latest_unread_message = db.scalar(
            select(ChatMessage)
            .where(*unread_filters)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(1)
        )

        if unread_count == 0 or latest_unread_message is None:
            notification.is_read = True
            if notification.read_at is None:
                notification.read_at = moderated_at
            notification.aggregate_count = None
        else:
            notification.is_read = False
            notification.read_at = None
            notification.aggregate_count = unread_count
            notification.actor_user_id = latest_unread_message.sender_user_id
            notification.related_message_id = latest_unread_message.id
            notification.event_at = latest_unread_message.created_at

        notification.updated_at = moderated_at
        db.add(notification)


def ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def build_chat_message_conflict_detail(exc: IntegrityError) -> str:
    return str(exc.orig)


def refresh_game_chat_summary(db: Session, db_game_chat: GameChat) -> None:
    db_game_chat.message_count = (
        db.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(
                ChatMessage.chat_id == db_game_chat.id,
                ChatMessage.visibility_status == "visible",
            )
        )
        or 0
    )
    db_game_chat.needs_review_count = (
        db.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(
                ChatMessage.chat_id == db_game_chat.id,
                ChatMessage.review_status == "needs_review",
            )
        )
        or 0
    )
    db_game_chat.removed_count = (
        db.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(
                ChatMessage.chat_id == db_game_chat.id,
                ChatMessage.visibility_status == "removed",
            )
        )
        or 0
    )
    latest_visible_message = db.scalar(
        select(ChatMessage)
        .where(
            ChatMessage.chat_id == db_game_chat.id,
            ChatMessage.visibility_status == "visible",
        )
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(1)
    )
    if latest_visible_message is None:
        db_game_chat.latest_message_id = None
        db_game_chat.latest_message_preview = None
        db_game_chat.latest_message_at = None
    else:
        db_game_chat.latest_message_id = latest_visible_message.id
        db_game_chat.latest_message_preview = build_safe_message_preview(
            latest_visible_message.message_body
        )
        db_game_chat.latest_message_at = latest_visible_message.created_at
    db_game_chat.updated_at = datetime.now(timezone.utc)
    db.add(db_game_chat)


def replace_game_chat_message_detections(
    db: Session,
    db_chat_message: ChatMessage,
    *,
    is_repeated_message: bool,
) -> None:
    db.execute(
        delete(GameChatMessageDetection).where(
            GameChatMessageDetection.message_id == db_chat_message.id
        )
    )
    try:
        detections = detect_chat_message(
            db_chat_message.message_body,
            is_repeated_message=is_repeated_message,
        )
    except Exception:
        logger.exception(
            "Game chat moderation detector failed for message %s.",
            db_chat_message.id,
        )
        detections = []
    db_chat_message.review_status = "needs_review" if detections else "clear"
    db_chat_message.reviewed_at = None
    db_chat_message.reviewed_by_user_id = None
    for detection in detections:
        db.add(
            GameChatMessageDetection(
                id=uuid.uuid4(),
                message_id=db_chat_message.id,
                category=detection.category,
                severity=detection.severity,
                rule_key=detection.rule_key,
                matched_preview=detection.matched_preview,
            )
        )


def get_chat_message_or_404(
    db: Session,
    chat_message_id: uuid.UUID,
) -> ChatMessage:
    db_chat_message = db.get(ChatMessage, chat_message_id)

    if db_chat_message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat message not found.",
        )

    return db_chat_message


def can_moderate_chat_messages(user: User) -> bool:
    return user_is_active_admin(user)


def create_chat_message_record(
    db: Session,
    chat_message: ChatMessageCreate,
    current_user: User,
) -> ChatMessage:
    now = datetime.now(timezone.utc)
    message_data = chat_message.model_dump()
    db_game_chat = get_game_chat_or_404(db, message_data["chat_id"])
    db_game = require_chat_member_for_message_change(
        db,
        db_game_chat,
        current_user,
    )

    message_data["message_body"] = normalize_message_body(message_data["message_body"])
    validate_sender_rate_limit(db, db_game_chat.id, current_user.id, now)
    validate_total_message_limit(db, db_game_chat.id)
    is_repeated_message = sender_repeated_message(
        db,
        db_game_chat.id,
        current_user.id,
        message_data["message_body"],
    )

    new_chat_message = ChatMessage(
        id=uuid.uuid4(),
        sender_user_id=current_user.id,
        message_type="text",
        is_pinned=False,
        visibility_status="visible",
        **message_data,
    )

    try:
        db.add(new_chat_message)
        db.flush()
        replace_game_chat_message_detections(
            db,
            new_chat_message,
            is_repeated_message=is_repeated_message,
        )
        db.add(new_chat_message)
        db.flush()
        refresh_game_chat_summary(db, db_game_chat)
        create_or_update_chat_notifications(
            db,
            db_game,
            db_game_chat,
            new_chat_message,
            current_user,
            now,
        )
        mark_chat_read(db, db_game_chat, current_user, now)
        db.commit()
        db.refresh(new_chat_message)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_chat_message_conflict_detail(exc),
        ) from exc

    surface_game_chat_message_text(db, message_id=new_chat_message.id)
    return new_chat_message


def get_chat_message_record(
    db: Session,
    chat_message_id: uuid.UUID,
    current_user: User,
) -> ChatMessage:
    db_chat_message = get_chat_message_or_404(db, chat_message_id)
    db_game_chat = get_game_chat_or_404(db, db_chat_message.chat_id)

    if can_moderate_chat_messages(current_user):
        return db_chat_message

    require_chat_member(db, db_game_chat, current_user)
    if db_chat_message.visibility_status != "visible":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat message not found.",
        )

    return db_chat_message


def list_chat_message_records(
    db: Session,
    current_user: User,
    *,
    chat_id: uuid.UUID | None = None,
    sender_user_id: uuid.UUID | None = None,
    visibility_status: str | None = None,
    review_status: str | None = None,
    is_pinned: bool | None = None,
    after_created_at: datetime | None = None,
    limit: int = MAX_CHAT_MESSAGES_PER_PAGE,
) -> list[ChatMessage]:
    if chat_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chat_id is required.",
        )

    db_game_chat = get_game_chat_or_404(db, chat_id)
    can_moderate = can_moderate_chat_messages(current_user)
    if not can_moderate:
        require_chat_member(db, db_game_chat, current_user)
        if visibility_status not in {None, "visible"} or review_status is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required.",
            )

    if visibility_status is not None and visibility_status not in VALID_VISIBILITY_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="visibility_status must be 'visible' or 'removed'.",
        )

    if review_status is not None and review_status not in VALID_REVIEW_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="review_status must be 'clear', 'needs_review', or 'reviewed'.",
        )

    if (
        not can_moderate
        and sender_user_id is None
        and visibility_status in {None, "visible"}
        and review_status is None
        and is_pinned is None
        and after_created_at is None
    ):
        return get_latest_visible_messages(db, chat_id, limit)

    statement = select(ChatMessage).where(ChatMessage.chat_id == chat_id)

    if not can_moderate:
        statement = statement.where(ChatMessage.visibility_status == "visible")
    elif visibility_status is not None:
        statement = statement.where(ChatMessage.visibility_status == visibility_status)

    if can_moderate and review_status is not None:
        statement = statement.where(ChatMessage.review_status == review_status)

    if after_created_at is not None:
        statement = statement.where(ChatMessage.created_at > after_created_at)

    if sender_user_id is not None:
        statement = statement.where(ChatMessage.sender_user_id == sender_user_id)

    if is_pinned is not None:
        statement = statement.where(ChatMessage.is_pinned == is_pinned)

    page_limit = max(1, min(limit, MAX_CHAT_MESSAGES_PER_PAGE))
    chat_messages = db.scalars(
        statement.order_by(
            ChatMessage.created_at.desc(),
            ChatMessage.id.desc(),
        ).limit(page_limit)
    ).all()
    return list(reversed(chat_messages))
