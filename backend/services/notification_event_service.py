from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.models import Game, Notification, SubPost
from backend.services.notification_policy import (
    get_notification_template,
    source_type_for_app_notification,
    subject_label_for_app_notification,
)

AGGREGATE_COUNT_MODES = {"replace", "increment", "clear", "preserve"}
AGGREGATED_NOTIFICATION_ASSIGNABLE_FIELDS = {
    "source_type",
    "title",
    "subject_label",
    "summary",
    "body",
    "action_key",
    "subject_starts_at",
    "subject_ends_at",
    "subject_timezone",
    "event_at",
    "aggregation_key",
    "aggregate_count",
    "related_game_id",
    "related_booking_id",
    "related_participant_id",
    "related_chat_id",
    "related_message_id",
    "related_sub_post_id",
    "related_sub_post_chat_id",
    "related_sub_post_chat_message_id",
    "related_sub_post_request_id",
    "related_sub_post_position_id",
    "related_payment_id",
    "related_refund_id",
    "actor_user_id",
}
RESOLVED_NOTIFICATION_ASSIGNABLE_FIELDS = (
    AGGREGATED_NOTIFICATION_ASSIGNABLE_FIELDS - {"event_at", "aggregation_key"}
)


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def source_type_for_game(game: Game | None) -> str:
    if game is None:
        return "game"

    if game.game_type == "official":
        return "official_game"

    if game.game_type == "community":
        return "community_game"

    return "game"


def subject_label_for_game(game: Game) -> str:
    return game.title or f"{game.venue_name_snapshot} {game.format_label}".strip()


def subject_label_for_sub_post(sub_post: SubPost) -> str:
    base_label = (
        sub_post.team_name
        or sub_post.location_name
        or "Need a Sub post"
    )

    if sub_post.format_label:
        return f"{base_label} {sub_post.format_label}"

    return base_label


def resolve_template_action_key(
    template_action_key: str | None,
    action_key: str | None,
    force_action_null: bool,
) -> str | None:
    if force_action_null:
        return None

    return action_key if action_key is not None else template_action_key


def build_game_notification_fields(
    game: Game,
    notification_type: str,
    *,
    event_at: datetime,
    title: str | None = None,
    summary: str | None = None,
    body: str | None = None,
    action_key: str | None = None,
    force_action_null: bool = False,
    aggregation_key: str | None = None,
    aggregate_count: int | None = None,
) -> dict[str, object]:
    template = get_notification_template(notification_type)

    return {
        "source_type": source_type_for_game(game),
        "title": title or template["title"],
        "subject_label": subject_label_for_game(game),
        "summary": summary or template["summary"],
        "body": body or template["body"],
        "action_key": resolve_template_action_key(
            template["action_key"],
            action_key,
            force_action_null,
        ),
        "subject_starts_at": game.starts_at,
        "subject_ends_at": game.ends_at,
        "subject_timezone": game.timezone or "America/Chicago",
        "event_at": ensure_aware_utc(event_at),
        "aggregation_key": aggregation_key,
        "aggregate_count": aggregate_count,
    }


def build_need_a_sub_notification_fields(
    sub_post: SubPost,
    notification_type: str,
    *,
    event_at: datetime,
    title: str | None = None,
    summary: str | None = None,
    body: str | None = None,
    action_key: str | None = None,
    force_action_null: bool = False,
    aggregation_key: str | None = None,
    aggregate_count: int | None = None,
) -> dict[str, object]:
    template = get_notification_template(notification_type)

    return {
        "source_type": "need_a_sub",
        "title": title or template["title"],
        "subject_label": subject_label_for_sub_post(sub_post),
        "summary": summary or template["summary"],
        "body": body or template["body"],
        "action_key": resolve_template_action_key(
            template["action_key"],
            action_key,
            force_action_null,
        ),
        "subject_starts_at": sub_post.starts_at,
        "subject_ends_at": sub_post.ends_at,
        "subject_timezone": sub_post.timezone or "America/Chicago",
        "event_at": ensure_aware_utc(event_at),
        "aggregation_key": aggregation_key,
        "aggregate_count": aggregate_count,
    }


def build_app_notification_fields(
    notification_type: str,
    *,
    event_at: datetime,
    source_type: str | None = None,
    subject_label: str | None = None,
    title: str | None = None,
    summary: str | None = None,
    body: str | None = None,
    action_key: str | None = None,
    force_action_null: bool = False,
) -> dict[str, object]:
    template = get_notification_template(notification_type)
    effective_source_type = source_type or source_type_for_app_notification(
        notification_type
    )

    return {
        "source_type": effective_source_type,
        "title": title or template["title"],
        "subject_label": subject_label
        or subject_label_for_app_notification(notification_type, effective_source_type),
        "summary": summary or template["summary"],
        "body": body or template["body"],
        "action_key": resolve_template_action_key(
            template["action_key"],
            action_key,
            force_action_null,
        ),
        "subject_starts_at": None,
        "subject_ends_at": None,
        "subject_timezone": None,
        "event_at": ensure_aware_utc(event_at),
        "aggregation_key": None,
        "aggregate_count": None,
    }


def validate_notification_assignment_fields(
    values: dict[str, object],
    *,
    allowed_fields: set[str],
) -> None:
    unknown_fields = set(values) - allowed_fields
    if unknown_fields:
        unknown_list = ", ".join(sorted(unknown_fields))
        raise ValueError(f"Unsupported notification assignment fields: {unknown_list}")


def assign_notification_values(
    notification: Notification,
    values: dict[str, object],
    *,
    allowed_fields: set[str],
) -> None:
    validate_notification_assignment_fields(values, allowed_fields=allowed_fields)

    for field_name, field_value in values.items():
        if field_name == "event_at" and isinstance(field_value, datetime):
            field_value = ensure_aware_utc(field_value)
        setattr(notification, field_name, field_value)


def apply_aggregate_count_mode(
    notification: Notification,
    *,
    aggregate_count_mode: str,
    was_read: bool,
    is_new: bool,
) -> None:
    if aggregate_count_mode not in AGGREGATE_COUNT_MODES:
        raise ValueError(f"Unsupported aggregate_count_mode: {aggregate_count_mode}")

    if aggregate_count_mode == "clear":
        notification.aggregate_count = None
        return

    if aggregate_count_mode == "preserve":
        return

    if aggregate_count_mode == "increment":
        if is_new or was_read:
            notification.aggregate_count = 1
            return

        current_count = notification.aggregate_count
        notification.aggregate_count = (
            current_count if current_count is not None else 1
        ) + 1


def reopen_aggregated_notification(
    db: Session,
    *,
    user_id: UUID,
    notification_type: str,
    notification_category: str,
    notification_domain: str,
    aggregation_key: str,
    values: dict[str, object],
    aggregate_count_mode: str = "replace",
) -> Notification:
    if not aggregation_key.strip():
        raise ValueError("aggregation_key is required")

    notification = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.aggregation_key == aggregation_key,
        )
        .one_or_none()
    )
    is_new = notification is None
    was_read = False if is_new else bool(notification.is_read)

    if notification is None:
        notification = Notification(
            id=uuid4(),
            user_id=user_id,
            notification_type=notification_type,
            notification_category=notification_category,
            notification_domain=notification_domain,
            aggregation_key=aggregation_key,
            is_read=False,
            read_at=None,
        )
        db.add(notification)
    else:
        notification.notification_type = notification_type
        notification.notification_category = notification_category
        notification.notification_domain = notification_domain

    assign_notification_values(
        notification,
        values,
        allowed_fields=AGGREGATED_NOTIFICATION_ASSIGNABLE_FIELDS,
    )
    now_value = values.get("event_at")
    effective_now = (
        ensure_aware_utc(now_value)
        if isinstance(now_value, datetime)
        else datetime.now(timezone.utc)
    )
    if is_new:
        notification.created_at = effective_now
    notification.updated_at = effective_now
    notification.aggregation_key = aggregation_key
    notification.is_read = False
    notification.read_at = None
    apply_aggregate_count_mode(
        notification,
        aggregate_count_mode=aggregate_count_mode,
        was_read=was_read,
        is_new=is_new,
    )

    return notification


def resolve_aggregated_notification(
    db: Session,
    *,
    user_id: UUID,
    aggregation_key: str,
    values: dict[str, object] | None = None,
    read_at: datetime | None = None,
) -> Notification | None:
    notification = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.aggregation_key == aggregation_key,
        )
        .one_or_none()
    )
    if notification is None:
        return None

    if values:
        assign_notification_values(
            notification,
            values,
            allowed_fields=RESOLVED_NOTIFICATION_ASSIGNABLE_FIELDS,
        )

    effective_read_at = ensure_aware_utc(read_at or datetime.now(timezone.utc))
    notification.is_read = True
    if notification.read_at is None:
        notification.read_at = effective_read_at
    notification.updated_at = effective_read_at

    return notification
