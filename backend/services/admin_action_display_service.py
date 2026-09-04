"""Display and cursor support for the global admin action log."""

import base64
import binascii
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    AdminFinancialOutcome,
    AdminReviewCase,
    Booking,
    ChatMessage,
    Game,
    GameCredit,
    GameCreditUsage,
    GameParticipant,
    HostPublishEntitlement,
    HostPublishFee,
    MoneyIssue,
    Notification,
    Payment,
    PlatformNotice,
    Refund,
    SubPost,
    SubPostChatMessage,
    SubPostPosition,
    SubPostRequest,
    SupportFlag,
    User,
    Venue,
    VenueImage,
)
from backend.schemas.admin_action_schema import (
    AdminActionDetailRead,
    AdminActionLogActionTypeOptionRead,
    AdminActionLogItemRead,
    AdminActionLogListRead,
    AdminActionLogTargetSummaryRead,
    AdminActionTargetDetailRead,
)
from backend.services.admin_action_policy import (
    ADMIN_ACTION_TYPES,
    TARGET_ADMIN_ACTION_ID,
    TARGET_BOOKING_ID,
    TARGET_CREDIT_USAGE_ID,
    TARGET_FINANCIAL_OUTCOME_ID,
    TARGET_GAME_CREDIT_ID,
    TARGET_GAME_ID,
    TARGET_HOST_PUBLISH_ENTITLEMENT_ID,
    TARGET_HOST_PUBLISH_FEE_ID,
    TARGET_MESSAGE_ID,
    TARGET_MONEY_ISSUE_ID,
    TARGET_NOTIFICATION_ID,
    TARGET_PARTICIPANT_ID,
    TARGET_PAYMENT_ID,
    TARGET_PLATFORM_NOTICE_ID,
    TARGET_REFUND_ID,
    TARGET_REVIEW_CASE_ID,
    TARGET_SUB_CHAT_MESSAGE_ID,
    TARGET_SUB_POST_ID,
    TARGET_SUB_POST_POSITION_ID,
    TARGET_SUB_POST_REQUEST_ID,
    TARGET_SUPPORT_FLAG_ID,
    TARGET_USER_ID,
    TARGET_VENUE_ID,
    TARGET_VENUE_IMAGE_ID,
)
from backend.services.admin_action_service import (
    get_policy_or_400,
    serialize_admin_action_reads,
    user_can_read_admin_action,
)
from backend.services.user_service import get_user_display_name

ADMIN_ACTION_LOG_CURSOR_VERSION = 1
ADMIN_ACTION_LOG_SORT_VERSION = "created_at_desc_id_desc"
ADMIN_ACTION_LOG_PAGE_LIMIT = 50


@dataclass(frozen=True)
class PrimaryTargetRule:
    field_name: str
    fallback_type_label: str


@dataclass(frozen=True)
class AdminActionDisplayRule:
    action_type: str
    label: str
    primary_targets: tuple[PrimaryTargetRule, ...]


@dataclass(frozen=True)
class TargetDisplayRule:
    field_name: str
    fallback_type_label: str
    model: type
    label_builder: Callable[[Any], str]
    destination_builder: Callable[[Any], str | None]
    type_label_builder: Callable[[Any], str] | None = None


def normalize_optional_exact_filter(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()
    return normalized_value or None


def label_from_token(value: str | None) -> str:
    return str(value or "").replace("_", " ").replace("-", " ").title()


def type_key_from_label(label: str) -> str:
    return label.lower().replace(" ", "_").replace("-", "_")


def full_id_label(type_label: str, target_id: uuid.UUID) -> str:
    return f"{type_label} {target_id}"


def format_money_cents(amount_cents: int | None) -> str | None:
    if amount_cents is None:
        return None

    dollars = amount_cents / 100
    return f"${dollars:,.2f}"


def user_label(user: User | None, *, fallback_user_id: uuid.UUID | None = None) -> str:
    if user is None:
        return str(fallback_user_id) if fallback_user_id is not None else "Unknown user"

    return get_user_display_name(user) or user.email or str(user.id)


def game_label(game: Game) -> str:
    return game.title or game.venue_name_snapshot or full_id_label("Game", game.id)


def game_type_label(game: Game) -> str:
    if game.game_type == "official":
        return "Official game"
    if game.game_type == "community":
        return "Community game"
    return "Game"


def game_destination(game: Game) -> str | None:
    if game.game_type == "official":
        return f"/admin/official-games/{game.id}"
    if game.game_type == "community":
        return f"/admin/community-games/{game.id}"
    return None


def payment_label(payment: Payment) -> str:
    amount = format_money_cents(payment.amount_cents)
    if amount is not None:
        return f"Payment {amount}"
    return full_id_label("Payment", payment.id)


def refund_label(refund: Refund) -> str:
    amount = format_money_cents(refund.amount_cents)
    if amount is not None:
        return f"Refund {amount}"
    return full_id_label("Refund", refund.id)


def credit_label(credit: GameCredit) -> str:
    amount = format_money_cents(credit.amount_cents)
    if amount is not None:
        return f"Credit {amount}"
    return full_id_label("Credit", credit.id)


def financial_outcome_label(outcome: AdminFinancialOutcome) -> str:
    amount = format_money_cents(outcome.amount_cents)
    if amount is not None:
        return f"Financial outcome {amount}"
    return full_id_label("Financial outcome", outcome.id)


def host_publish_fee_label(fee: HostPublishFee) -> str:
    amount = format_money_cents(fee.amount_cents)
    if amount is not None:
        return f"Publish fee {amount}"
    return full_id_label("Publish fee", fee.id)


def compact_status_label(prefix: str, record: Any, status_field: str) -> str:
    status_value = getattr(record, status_field, None)
    if status_value:
        return f"{prefix} {label_from_token(status_value)}"
    return full_id_label(prefix, record.id)


def message_label(message: ChatMessage) -> str:
    return compact_status_label("Game message", message, "visibility_status")


def sub_chat_message_label(message: SubPostChatMessage) -> str:
    sender = message.sender_display_name_snapshot
    if sender:
        return f"Need a Sub message from {sender}"
    return compact_status_label("Need a Sub message", message, "visibility_status")


def sub_post_label(post: SubPost) -> str:
    return (
        post.team_name
        or post.location_name
        or full_id_label("Need a Sub post", post.id)
    )


def venue_image_label(image: VenueImage) -> str:
    return image.caption or image.alt_text or full_id_label("Venue photo", image.id)


def notification_label(notification: Notification) -> str:
    return (
        notification.title
        or notification.subject_label
        or full_id_label(
            "Notification",
            notification.id,
        )
    )


def no_destination(record: Any) -> None:
    del record
    return None


def id_destination(prefix: str) -> Callable[[Any], str]:
    return lambda record: f"{prefix}/{record.id}"


TARGET_DISPLAY_RULES: dict[str, TargetDisplayRule] = {
    TARGET_USER_ID: TargetDisplayRule(
        field_name=TARGET_USER_ID,
        fallback_type_label="User",
        model=User,
        label_builder=lambda user: user_label(user),
        destination_builder=id_destination("/admin/users"),
    ),
    TARGET_GAME_ID: TargetDisplayRule(
        field_name=TARGET_GAME_ID,
        fallback_type_label="Game",
        model=Game,
        label_builder=game_label,
        destination_builder=game_destination,
        type_label_builder=game_type_label,
    ),
    TARGET_BOOKING_ID: TargetDisplayRule(
        field_name=TARGET_BOOKING_ID,
        fallback_type_label="Booking",
        model=Booking,
        label_builder=lambda booking: compact_status_label(
            "Booking",
            booking,
            "booking_status",
        ),
        destination_builder=no_destination,
    ),
    TARGET_PARTICIPANT_ID: TargetDisplayRule(
        field_name=TARGET_PARTICIPANT_ID,
        fallback_type_label="Participant",
        model=GameParticipant,
        label_builder=lambda participant: (
            participant.display_name_snapshot
            or full_id_label("Participant", participant.id)
        ),
        destination_builder=no_destination,
    ),
    TARGET_PAYMENT_ID: TargetDisplayRule(
        field_name=TARGET_PAYMENT_ID,
        fallback_type_label="Payment",
        model=Payment,
        label_builder=payment_label,
        destination_builder=id_destination("/admin/money/payments"),
    ),
    TARGET_REFUND_ID: TargetDisplayRule(
        field_name=TARGET_REFUND_ID,
        fallback_type_label="Refund",
        model=Refund,
        label_builder=refund_label,
        destination_builder=id_destination("/admin/money/refunds"),
    ),
    TARGET_GAME_CREDIT_ID: TargetDisplayRule(
        field_name=TARGET_GAME_CREDIT_ID,
        fallback_type_label="Credit",
        model=GameCredit,
        label_builder=credit_label,
        destination_builder=id_destination("/admin/money/credits"),
    ),
    TARGET_CREDIT_USAGE_ID: TargetDisplayRule(
        field_name=TARGET_CREDIT_USAGE_ID,
        fallback_type_label="Credit usage",
        model=GameCreditUsage,
        label_builder=lambda usage: full_id_label("Credit usage", usage.id),
        destination_builder=no_destination,
    ),
    TARGET_VENUE_ID: TargetDisplayRule(
        field_name=TARGET_VENUE_ID,
        fallback_type_label="Venue",
        model=Venue,
        label_builder=lambda venue: venue.name or full_id_label("Venue", venue.id),
        destination_builder=no_destination,
    ),
    TARGET_VENUE_IMAGE_ID: TargetDisplayRule(
        field_name=TARGET_VENUE_IMAGE_ID,
        fallback_type_label="Venue photo",
        model=VenueImage,
        label_builder=venue_image_label,
        destination_builder=no_destination,
    ),
    TARGET_MESSAGE_ID: TargetDisplayRule(
        field_name=TARGET_MESSAGE_ID,
        fallback_type_label="Game message",
        model=ChatMessage,
        label_builder=message_label,
        destination_builder=no_destination,
    ),
    TARGET_SUB_POST_ID: TargetDisplayRule(
        field_name=TARGET_SUB_POST_ID,
        fallback_type_label="Need a Sub post",
        model=SubPost,
        label_builder=sub_post_label,
        destination_builder=id_destination("/admin/need-a-sub"),
    ),
    TARGET_SUB_POST_REQUEST_ID: TargetDisplayRule(
        field_name=TARGET_SUB_POST_REQUEST_ID,
        fallback_type_label="Need a Sub request",
        model=SubPostRequest,
        label_builder=lambda request: compact_status_label(
            "Need a Sub request",
            request,
            "request_status",
        ),
        destination_builder=id_destination("/admin/need-a-sub/requests"),
    ),
    TARGET_SUB_POST_POSITION_ID: TargetDisplayRule(
        field_name=TARGET_SUB_POST_POSITION_ID,
        fallback_type_label="Need a Sub position",
        model=SubPostPosition,
        label_builder=lambda position: (
            position.position_label or full_id_label("Need a Sub position", position.id)
        ),
        destination_builder=no_destination,
    ),
    TARGET_SUB_CHAT_MESSAGE_ID: TargetDisplayRule(
        field_name=TARGET_SUB_CHAT_MESSAGE_ID,
        fallback_type_label="Need a Sub message",
        model=SubPostChatMessage,
        label_builder=sub_chat_message_label,
        destination_builder=no_destination,
    ),
    TARGET_NOTIFICATION_ID: TargetDisplayRule(
        field_name=TARGET_NOTIFICATION_ID,
        fallback_type_label="Notification",
        model=Notification,
        label_builder=notification_label,
        destination_builder=id_destination("/admin/notifications"),
    ),
    TARGET_PLATFORM_NOTICE_ID: TargetDisplayRule(
        field_name=TARGET_PLATFORM_NOTICE_ID,
        fallback_type_label="Platform notice",
        model=PlatformNotice,
        label_builder=lambda notice: (
            notice.title or full_id_label("Platform notice", notice.id)
        ),
        destination_builder=id_destination("/admin/platform-notices"),
    ),
    TARGET_ADMIN_ACTION_ID: TargetDisplayRule(
        field_name=TARGET_ADMIN_ACTION_ID,
        fallback_type_label="Admin action",
        model=AdminAction,
        label_builder=lambda action: admin_action_label(action.action_type),
        destination_builder=no_destination,
    ),
    TARGET_SUPPORT_FLAG_ID: TargetDisplayRule(
        field_name=TARGET_SUPPORT_FLAG_ID,
        fallback_type_label="Support flag",
        model=SupportFlag,
        label_builder=lambda flag: flag.title or full_id_label("Support flag", flag.id),
        destination_builder=no_destination,
    ),
    TARGET_MONEY_ISSUE_ID: TargetDisplayRule(
        field_name=TARGET_MONEY_ISSUE_ID,
        fallback_type_label="Money issue",
        model=MoneyIssue,
        label_builder=lambda issue: (
            issue.latest_summary or label_from_token(issue.issue_type)
        ),
        destination_builder=id_destination("/admin/money/issues"),
    ),
    TARGET_REVIEW_CASE_ID: TargetDisplayRule(
        field_name=TARGET_REVIEW_CASE_ID,
        fallback_type_label="Review case",
        model=AdminReviewCase,
        label_builder=lambda case: case.title or full_id_label("Review case", case.id),
        destination_builder=id_destination("/admin/review-cases"),
    ),
    TARGET_FINANCIAL_OUTCOME_ID: TargetDisplayRule(
        field_name=TARGET_FINANCIAL_OUTCOME_ID,
        fallback_type_label="Financial outcome",
        model=AdminFinancialOutcome,
        label_builder=financial_outcome_label,
        destination_builder=id_destination("/admin/money/financial-outcomes"),
    ),
    TARGET_HOST_PUBLISH_FEE_ID: TargetDisplayRule(
        field_name=TARGET_HOST_PUBLISH_FEE_ID,
        fallback_type_label="Publish fee",
        model=HostPublishFee,
        label_builder=host_publish_fee_label,
        destination_builder=no_destination,
    ),
    TARGET_HOST_PUBLISH_ENTITLEMENT_ID: TargetDisplayRule(
        field_name=TARGET_HOST_PUBLISH_ENTITLEMENT_ID,
        fallback_type_label="Publish entitlement",
        model=HostPublishEntitlement,
        label_builder=lambda entitlement: label_from_token(
            entitlement.entitlement_type
        ),
        destination_builder=no_destination,
    ),
}


ACTION_DISPLAY_RULES: dict[str, AdminActionDisplayRule] = {
    "cancel_game": AdminActionDisplayRule(
        "cancel_game",
        "Official game cancelled",
        (PrimaryTargetRule(TARGET_GAME_ID, "Official game"),),
    ),
    "refund_booking": AdminActionDisplayRule(
        "refund_booking",
        "Booking refunded",
        (
            PrimaryTargetRule(TARGET_REFUND_ID, "Refund"),
            PrimaryTargetRule(TARGET_PAYMENT_ID, "Payment"),
            PrimaryTargetRule(TARGET_BOOKING_ID, "Booking"),
        ),
    ),
    "create_refund": AdminActionDisplayRule(
        "create_refund",
        "Refund created",
        (PrimaryTargetRule(TARGET_REFUND_ID, "Refund"),),
    ),
    "update_refund": AdminActionDisplayRule(
        "update_refund",
        "Refund updated",
        (PrimaryTargetRule(TARGET_REFUND_ID, "Refund"),),
    ),
    "create_financial_outcome": AdminActionDisplayRule(
        "create_financial_outcome",
        "Financial outcome created",
        (PrimaryTargetRule(TARGET_FINANCIAL_OUTCOME_ID, "Financial outcome"),),
    ),
    "apply_financial_outcome": AdminActionDisplayRule(
        "apply_financial_outcome",
        "Financial outcome applied",
        (PrimaryTargetRule(TARGET_FINANCIAL_OUTCOME_ID, "Financial outcome"),),
    ),
    "create_payment": AdminActionDisplayRule(
        "create_payment",
        "Payment created",
        (PrimaryTargetRule(TARGET_PAYMENT_ID, "Payment"),),
    ),
    "update_payment": AdminActionDisplayRule(
        "update_payment",
        "Payment updated",
        (PrimaryTargetRule(TARGET_PAYMENT_ID, "Payment"),),
    ),
    "mark_no_show": AdminActionDisplayRule(
        "mark_no_show",
        "No-show marked",
        (PrimaryTargetRule(TARGET_PARTICIPANT_ID, "Participant"),),
    ),
    "reverse_no_show": AdminActionDisplayRule(
        "reverse_no_show",
        "No-show reversed",
        (PrimaryTargetRule(TARGET_PARTICIPANT_ID, "Participant"),),
    ),
    "suspend_user": AdminActionDisplayRule(
        "suspend_user",
        "User suspended",
        (PrimaryTargetRule(TARGET_USER_ID, "User"),),
    ),
    "unsuspend_user": AdminActionDisplayRule(
        "unsuspend_user",
        "User unsuspended",
        (PrimaryTargetRule(TARGET_USER_ID, "User"),),
    ),
    "restrict_hosting": AdminActionDisplayRule(
        "restrict_hosting",
        "Hosting restricted",
        (PrimaryTargetRule(TARGET_USER_ID, "User"),),
    ),
    "restore_hosting": AdminActionDisplayRule(
        "restore_hosting",
        "Hosting restored",
        (PrimaryTargetRule(TARGET_USER_ID, "User"),),
    ),
    "delete_user": AdminActionDisplayRule(
        "delete_user",
        "User deleted",
        (PrimaryTargetRule(TARGET_USER_ID, "User"),),
    ),
    "approve_venue": AdminActionDisplayRule(
        "approve_venue",
        "Venue approved",
        (PrimaryTargetRule(TARGET_VENUE_ID, "Venue"),),
    ),
    "reject_venue": AdminActionDisplayRule(
        "reject_venue",
        "Venue rejected",
        (PrimaryTargetRule(TARGET_VENUE_ID, "Venue"),),
    ),
    "create_venue_image": AdminActionDisplayRule(
        "create_venue_image",
        "Venue photo created",
        (PrimaryTargetRule(TARGET_VENUE_IMAGE_ID, "Venue photo"),),
    ),
    "update_venue_image": AdminActionDisplayRule(
        "update_venue_image",
        "Venue photo updated",
        (PrimaryTargetRule(TARGET_VENUE_IMAGE_ID, "Venue photo"),),
    ),
    "remove_venue_image": AdminActionDisplayRule(
        "remove_venue_image",
        "Venue photo removed",
        (PrimaryTargetRule(TARGET_VENUE_IMAGE_ID, "Venue photo"),),
    ),
    "mark_chat_message_reviewed": AdminActionDisplayRule(
        "mark_chat_message_reviewed",
        "Chat message reviewed",
        (
            PrimaryTargetRule(TARGET_MESSAGE_ID, "Game message"),
            PrimaryTargetRule(TARGET_SUB_CHAT_MESSAGE_ID, "Need a Sub message"),
        ),
    ),
    "remove_chat_message": AdminActionDisplayRule(
        "remove_chat_message",
        "Chat message removed",
        (
            PrimaryTargetRule(TARGET_MESSAGE_ID, "Game message"),
            PrimaryTargetRule(TARGET_SUB_CHAT_MESSAGE_ID, "Need a Sub message"),
        ),
    ),
    "restore_chat_message": AdminActionDisplayRule(
        "restore_chat_message",
        "Chat message restored",
        (
            PrimaryTargetRule(TARGET_MESSAGE_ID, "Game message"),
            PrimaryTargetRule(TARGET_SUB_CHAT_MESSAGE_ID, "Need a Sub message"),
        ),
    ),
    "update_game": AdminActionDisplayRule(
        "update_game",
        "Game updated",
        (PrimaryTargetRule(TARGET_GAME_ID, "Game"),),
    ),
    "create_game_chat": AdminActionDisplayRule(
        "create_game_chat",
        "Game chat created",
        (PrimaryTargetRule(TARGET_GAME_ID, "Game"),),
    ),
    "update_game_chat": AdminActionDisplayRule(
        "update_game_chat",
        "Game chat updated",
        (PrimaryTargetRule(TARGET_GAME_ID, "Game"),),
    ),
    "update_booking": AdminActionDisplayRule(
        "update_booking",
        "Booking updated",
        (PrimaryTargetRule(TARGET_BOOKING_ID, "Booking"),),
    ),
    "update_participant": AdminActionDisplayRule(
        "update_participant",
        "Participant updated",
        (PrimaryTargetRule(TARGET_PARTICIPANT_ID, "Participant"),),
    ),
    "issue_credit": AdminActionDisplayRule(
        "issue_credit",
        "Credit issued",
        (
            PrimaryTargetRule(TARGET_GAME_CREDIT_ID, "Credit"),
            PrimaryTargetRule(TARGET_USER_ID, "User"),
        ),
    ),
    "reverse_credit": AdminActionDisplayRule(
        "reverse_credit",
        "Credit reversed",
        (PrimaryTargetRule(TARGET_GAME_CREDIT_ID, "Credit"),),
    ),
    "create_official_game": AdminActionDisplayRule(
        "create_official_game",
        "Official game created",
        (PrimaryTargetRule(TARGET_GAME_ID, "Official game"),),
    ),
    "update_official_game": AdminActionDisplayRule(
        "update_official_game",
        "Official game updated",
        (PrimaryTargetRule(TARGET_GAME_ID, "Official game"),),
    ),
    "assign_official_host": AdminActionDisplayRule(
        "assign_official_host",
        "Official host assigned",
        (PrimaryTargetRule(TARGET_GAME_ID, "Official game"),),
    ),
    "remove_official_host": AdminActionDisplayRule(
        "remove_official_host",
        "Official host removed",
        (PrimaryTargetRule(TARGET_GAME_ID, "Official game"),),
    ),
    "admin_add_player": AdminActionDisplayRule(
        "admin_add_player",
        "Player added by admin",
        (
            PrimaryTargetRule(TARGET_PARTICIPANT_ID, "Participant"),
            PrimaryTargetRule(TARGET_GAME_ID, "Official game"),
        ),
    ),
    "admin_remove_player": AdminActionDisplayRule(
        "admin_remove_player",
        "Player removed by admin",
        (
            PrimaryTargetRule(TARGET_PARTICIPANT_ID, "Participant"),
            PrimaryTargetRule(TARGET_GAME_ID, "Official game"),
        ),
    ),
    "waive_payment": AdminActionDisplayRule(
        "waive_payment",
        "Payment waived",
        (
            PrimaryTargetRule(TARGET_PAYMENT_ID, "Payment"),
            PrimaryTargetRule(TARGET_BOOKING_ID, "Booking"),
        ),
    ),
    "remove_sub_post": AdminActionDisplayRule(
        "remove_sub_post",
        "Need a Sub post removed",
        (PrimaryTargetRule(TARGET_SUB_POST_ID, "Need a Sub post"),),
    ),
    "hide_need_sub_post": AdminActionDisplayRule(
        "hide_need_sub_post",
        "Need a Sub post hidden",
        (PrimaryTargetRule(TARGET_SUB_POST_ID, "Need a Sub post"),),
    ),
    "restore_need_sub_post": AdminActionDisplayRule(
        "restore_need_sub_post",
        "Need a Sub post restored",
        (PrimaryTargetRule(TARGET_SUB_POST_ID, "Need a Sub post"),),
    ),
    "hide_community_game": AdminActionDisplayRule(
        "hide_community_game",
        "Community game hidden",
        (PrimaryTargetRule(TARGET_GAME_ID, "Community game"),),
    ),
    "restore_community_game": AdminActionDisplayRule(
        "restore_community_game",
        "Community game restored",
        (PrimaryTargetRule(TARGET_GAME_ID, "Community game"),),
    ),
    "pause_community_game_joining": AdminActionDisplayRule(
        "pause_community_game_joining",
        "Community game joining paused",
        (PrimaryTargetRule(TARGET_GAME_ID, "Community game"),),
    ),
    "resume_community_game_joining": AdminActionDisplayRule(
        "resume_community_game_joining",
        "Community game joining resumed",
        (PrimaryTargetRule(TARGET_GAME_ID, "Community game"),),
    ),
    "admin_cancel_community_game": AdminActionDisplayRule(
        "admin_cancel_community_game",
        "Community game cancelled",
        (PrimaryTargetRule(TARGET_GAME_ID, "Community game"),),
    ),
    "hide_unsafe_community_payment_text": AdminActionDisplayRule(
        "hide_unsafe_community_payment_text",
        "Unsafe payment text hidden",
        (PrimaryTargetRule(TARGET_GAME_ID, "Community game"),),
    ),
    "restore_community_payment_text": AdminActionDisplayRule(
        "restore_community_payment_text",
        "Community payment text restored",
        (PrimaryTargetRule(TARGET_GAME_ID, "Community game"),),
    ),
    "create_review_case": AdminActionDisplayRule(
        "create_review_case",
        "Review case created",
        (PrimaryTargetRule(TARGET_REVIEW_CASE_ID, "Review case"),),
    ),
    "close_review_case": AdminActionDisplayRule(
        "close_review_case",
        "Review case closed",
        (PrimaryTargetRule(TARGET_REVIEW_CASE_ID, "Review case"),),
    ),
    "add_review_case_note": AdminActionDisplayRule(
        "add_review_case_note",
        "Review case note added",
        (PrimaryTargetRule(TARGET_REVIEW_CASE_ID, "Review case"),),
    ),
    "assign_review_case": AdminActionDisplayRule(
        "assign_review_case",
        "Review case assignment changed",
        (PrimaryTargetRule(TARGET_REVIEW_CASE_ID, "Review case"),),
    ),
    "reopen_review_case": AdminActionDisplayRule(
        "reopen_review_case",
        "Review case reopened",
        (PrimaryTargetRule(TARGET_REVIEW_CASE_ID, "Review case"),),
    ),
    "merge_review_case": AdminActionDisplayRule(
        "merge_review_case",
        "Review cases merged",
        (PrimaryTargetRule(TARGET_REVIEW_CASE_ID, "Review case"),),
    ),
    "update_notification": AdminActionDisplayRule(
        "update_notification",
        "Notification updated",
        (PrimaryTargetRule(TARGET_NOTIFICATION_ID, "Notification"),),
    ),
    "create_notification": AdminActionDisplayRule(
        "create_notification",
        "Notification created",
        (PrimaryTargetRule(TARGET_NOTIFICATION_ID, "Notification"),),
    ),
    "publish_platform_notice": AdminActionDisplayRule(
        "publish_platform_notice",
        "Platform notice published",
        (PrimaryTargetRule(TARGET_PLATFORM_NOTICE_ID, "Platform notice"),),
    ),
    "cancel_platform_notice": AdminActionDisplayRule(
        "cancel_platform_notice",
        "Platform notice cancelled",
        (PrimaryTargetRule(TARGET_PLATFORM_NOTICE_ID, "Platform notice"),),
    ),
    "user_role_changed": AdminActionDisplayRule(
        "user_role_changed",
        "User role changed",
        (PrimaryTargetRule(TARGET_USER_ID, "User"),),
    ),
    "append_audit_note": AdminActionDisplayRule(
        "append_audit_note",
        "Action note appended",
        (PrimaryTargetRule(TARGET_ADMIN_ACTION_ID, "Admin action"),),
    ),
    "resolve_support_flag": AdminActionDisplayRule(
        "resolve_support_flag",
        "Support flag resolved",
        (PrimaryTargetRule(TARGET_SUPPORT_FLAG_ID, "Support flag"),),
    ),
    "resolve_money_issue": AdminActionDisplayRule(
        "resolve_money_issue",
        "Money issue resolved",
        (PrimaryTargetRule(TARGET_MONEY_ISSUE_ID, "Money issue"),),
    ),
    "retry_money_issue_credit": AdminActionDisplayRule(
        "retry_money_issue_credit",
        "Money issue credit retried",
        (PrimaryTargetRule(TARGET_MONEY_ISSUE_ID, "Money issue"),),
    ),
    "reconcile_refund": AdminActionDisplayRule(
        "reconcile_refund",
        "Refund reconciled",
        (PrimaryTargetRule(TARGET_REFUND_ID, "Refund"),),
    ),
}


def admin_action_label(action_type: str) -> str:
    return ACTION_DISPLAY_RULES.get(
        action_type,
        AdminActionDisplayRule(
            action_type=action_type,
            label=label_from_token(action_type),
            primary_targets=(),
        ),
    ).label


def invalid_admin_action_log_cursor_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": "invalid_admin_action_log_cursor",
            "message": "cursor is invalid.",
        },
    )


def query_context_hash(context: dict[str, object]) -> str:
    raw_context = json.dumps(
        context,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw_context).hexdigest()


def build_admin_action_log_context(
    *,
    admin_user_id: uuid.UUID | None,
    action_type: str | None,
) -> dict[str, object]:
    return {
        "admin_user_id": str(admin_user_id) if admin_user_id is not None else None,
        "action_type": action_type,
        "sort_version": ADMIN_ACTION_LOG_SORT_VERSION,
    }


def encode_admin_action_log_cursor(
    admin_action: AdminAction,
    *,
    context_hash: str,
) -> str:
    payload = {
        "cursor_version": ADMIN_ACTION_LOG_CURSOR_VERSION,
        "sort_version": ADMIN_ACTION_LOG_SORT_VERSION,
        "created_at": admin_action.created_at.isoformat(),
        "id": str(admin_action.id),
        "query_context_hash": context_hash,
    }
    raw_payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw_payload).decode("ascii")


def decode_admin_action_log_cursor(
    cursor: str | None,
    *,
    expected_context_hash: str,
) -> dict[str, Any] | None:
    normalized_cursor = normalize_optional_exact_filter(cursor)
    if normalized_cursor is None:
        return None

    try:
        raw_payload = base64.urlsafe_b64decode(normalized_cursor.encode("ascii"))
        payload = json.loads(raw_payload.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("cursor payload must be an object")
        if payload.get("cursor_version") != ADMIN_ACTION_LOG_CURSOR_VERSION:
            raise ValueError("unsupported cursor version")
        if payload.get("sort_version") != ADMIN_ACTION_LOG_SORT_VERSION:
            raise ValueError("unsupported sort version")
        if payload.get("query_context_hash") != expected_context_hash:
            raise ValueError("cursor context mismatch")
        return {
            "created_at": datetime.fromisoformat(payload["created_at"]),
            "id": uuid.UUID(payload["id"]),
        }
    except (
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        binascii.Error,
    ) as exc:
        raise invalid_admin_action_log_cursor_error() from exc


def build_cursor_filter(cursor_data: dict[str, Any] | None):
    if cursor_data is None:
        return None

    return or_(
        AdminAction.created_at < cursor_data["created_at"],
        and_(
            AdminAction.created_at == cursor_data["created_at"],
            AdminAction.id < cursor_data["id"],
        ),
    )


def build_admin_action_log_filters(
    *,
    admin_user_id: uuid.UUID | None = None,
    action_type: str | None = None,
) -> tuple[list[object], str, str | None]:
    normalized_action_type = normalize_optional_exact_filter(action_type)
    filters: list[object] = []

    if admin_user_id is not None:
        filters.append(AdminAction.admin_user_id == admin_user_id)

    if normalized_action_type is not None:
        get_policy_or_400(normalized_action_type)
        filters.append(AdminAction.action_type == normalized_action_type)

    context = build_admin_action_log_context(
        admin_user_id=admin_user_id,
        action_type=normalized_action_type,
    )
    return filters, query_context_hash(context), normalized_action_type


def admin_action_type_options() -> list[AdminActionLogActionTypeOptionRead]:
    options = [
        AdminActionLogActionTypeOptionRead(
            action_type=action_type,
            label=admin_action_label(action_type),
        )
        for action_type in ADMIN_ACTION_TYPES
    ]
    return sorted(
        options,
        key=lambda option: (option.label.casefold(), option.action_type),
    )


def users_by_id(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, User]:
    if not user_ids:
        return {}

    return {
        user.id: user
        for user in db.scalars(select(User).where(User.id.in_(user_ids))).all()
    }


def selected_target_rules(action: AdminAction) -> tuple[PrimaryTargetRule, ...]:
    display_rule = ACTION_DISPLAY_RULES.get(action.action_type)
    if display_rule is None:
        return tuple(
            PrimaryTargetRule(
                field_name, TARGET_DISPLAY_RULES[field_name].fallback_type_label
            )
            for field_name in TARGET_DISPLAY_RULES
        )
    return display_rule.primary_targets


def collect_primary_target_ids(
    actions: list[AdminAction],
) -> dict[str, set[uuid.UUID]]:
    ids_by_field: dict[str, set[uuid.UUID]] = {
        field_name: set() for field_name in TARGET_DISPLAY_RULES
    }
    for action in actions:
        for target_rule in selected_target_rules(action):
            target_id = getattr(action, target_rule.field_name, None)
            if target_id is not None:
                ids_by_field[target_rule.field_name].add(target_id)
                break

    return {
        field_name: target_ids
        for field_name, target_ids in ids_by_field.items()
        if target_ids
    }


def collect_all_target_ids(action: AdminAction) -> dict[str, set[uuid.UUID]]:
    return {
        field_name: {target_id}
        for field_name in TARGET_DISPLAY_RULES
        if (target_id := getattr(action, field_name, None)) is not None
    }


def load_records_by_field(
    db: Session,
    ids_by_field: dict[str, set[uuid.UUID]],
) -> dict[str, dict[uuid.UUID, Any]]:
    records_by_field: dict[str, dict[uuid.UUID, Any]] = {}

    for field_name, target_ids in ids_by_field.items():
        display_rule = TARGET_DISPLAY_RULES[field_name]
        records = db.scalars(
            select(display_rule.model).where(display_rule.model.id.in_(target_ids))
        ).all()
        records_by_field[field_name] = {record.id: record for record in records}

    return records_by_field


def load_target_records(
    db: Session,
    actions: list[AdminAction],
) -> dict[str, dict[uuid.UUID, Any]]:
    return load_records_by_field(db, collect_primary_target_ids(actions))


def build_target_summary(
    action: AdminAction,
    target_rule: PrimaryTargetRule,
    records_by_field: dict[str, dict[uuid.UUID, Any]],
) -> AdminActionLogTargetSummaryRead | None:
    target_id = getattr(action, target_rule.field_name, None)
    if target_id is None:
        return None

    display_rule = TARGET_DISPLAY_RULES.get(target_rule.field_name)
    if display_rule is None:
        return None

    record = records_by_field.get(target_rule.field_name, {}).get(target_id)
    if record is None or getattr(record, "deleted_at", None) is not None:
        type_label = target_rule.fallback_type_label
        return AdminActionLogTargetSummaryRead(
            target_field=target_rule.field_name,
            target_type=type_key_from_label(type_label),
            target_type_label=type_label,
            target_id=target_id,
            label=full_id_label(type_label, target_id),
            destination_path=None,
        )

    type_label = (
        display_rule.type_label_builder(record)
        if display_rule.type_label_builder is not None
        else target_rule.fallback_type_label
    )
    return AdminActionLogTargetSummaryRead(
        target_field=target_rule.field_name,
        target_type=type_key_from_label(type_label),
        target_type_label=type_label,
        target_id=target_id,
        label=display_rule.label_builder(record),
        destination_path=display_rule.destination_builder(record),
    )


def primary_target_summary(
    action: AdminAction,
    records_by_field: dict[str, dict[uuid.UUID, Any]],
) -> AdminActionLogTargetSummaryRead | None:
    for target_rule in selected_target_rules(action):
        summary = build_target_summary(action, target_rule, records_by_field)
        if summary is not None:
            return summary

    return None


def serialize_admin_action_target_detail(
    summary: AdminActionLogTargetSummaryRead,
    *,
    primary_summary: AdminActionLogTargetSummaryRead | None,
) -> AdminActionTargetDetailRead:
    return AdminActionTargetDetailRead(
        target_field=summary.target_field,
        target_type=summary.target_type,
        target_type_label=summary.target_type_label,
        target_id=summary.target_id,
        label=summary.label,
        destination_path=summary.destination_path,
        is_primary=(
            primary_summary is not None
            and summary.target_field == primary_summary.target_field
            and summary.target_id == primary_summary.target_id
        ),
    )


def serialize_admin_action_target_details(
    db: Session,
    action: AdminAction,
) -> list[AdminActionTargetDetailRead]:
    records_by_field = load_records_by_field(db, collect_all_target_ids(action))
    primary_summary = primary_target_summary(action, records_by_field)
    target_details: list[AdminActionTargetDetailRead] = []

    for field_name, display_rule in TARGET_DISPLAY_RULES.items():
        target_id = getattr(action, field_name, None)
        if target_id is None:
            continue

        summary = build_target_summary(
            action,
            PrimaryTargetRule(field_name, display_rule.fallback_type_label),
            records_by_field,
        )
        if summary is not None:
            target_details.append(
                serialize_admin_action_target_detail(
                    summary,
                    primary_summary=primary_summary,
                )
            )

    return target_details


def serialize_admin_action_detail_read(
    db: Session,
    action: AdminAction,
) -> AdminActionDetailRead:
    action_read = serialize_admin_action_reads(db, [action])[0].model_dump()
    return AdminActionDetailRead(
        **action_read,
        target_details=serialize_admin_action_target_details(db, action),
    )


def reason_preview(reason: str | None) -> str | None:
    normalized_reason = " ".join((reason or "").split())
    if not normalized_reason:
        return None
    if len(normalized_reason) <= 140:
        return normalized_reason
    return f"{normalized_reason[:137]}..."


def serialize_admin_action_log_item(
    action: AdminAction,
    *,
    admin_users: dict[uuid.UUID, User],
    records_by_field: dict[str, dict[uuid.UUID, Any]],
) -> AdminActionLogItemRead:
    admin_user = admin_users.get(action.admin_user_id)
    target_summary = primary_target_summary(action, records_by_field)

    return AdminActionLogItemRead(
        id=action.id,
        action_type=action.action_type,
        action_label=admin_action_label(action.action_type),
        admin_user_id=action.admin_user_id,
        admin_label=user_label(admin_user, fallback_user_id=action.admin_user_id),
        admin_email=admin_user.email if admin_user is not None else None,
        primary_target=target_summary,
        target_label=target_summary.label
        if target_summary is not None
        else "No target",
        target_type_label=(
            target_summary.target_type_label if target_summary is not None else "Target"
        ),
        destination_path=(
            target_summary.destination_path if target_summary is not None else None
        ),
        reason_preview=reason_preview(action.reason),
        created_at=action.created_at,
    )


def list_admin_action_log(
    db: Session,
    *,
    viewer_user: User,
    admin_user_id: uuid.UUID | None = None,
    action_type: str | None = None,
    cursor: str | None = None,
) -> AdminActionLogListRead:
    filters, context_hash, _normalized_action_type = build_admin_action_log_filters(
        admin_user_id=admin_user_id,
        action_type=action_type,
    )

    cursor_filter = build_cursor_filter(
        decode_admin_action_log_cursor(
            cursor,
            expected_context_hash=context_hash,
        )
    )
    if cursor_filter is not None:
        filters.append(cursor_filter)

    query_limit = ADMIN_ACTION_LOG_PAGE_LIMIT
    actions = list(
        db.scalars(
            select(AdminAction)
            .where(*filters)
            .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
            .limit(query_limit + 1)
        ).all()
    )
    visible_actions = [
        action for action in actions if user_can_read_admin_action(viewer_user, action)
    ]
    has_more = len(visible_actions) > query_limit
    page_actions = visible_actions[:query_limit]

    admin_users = users_by_id(
        db,
        sorted({action.admin_user_id for action in page_actions}, key=str),
    )
    records_by_field = load_target_records(db, page_actions)
    next_cursor = (
        encode_admin_action_log_cursor(
            page_actions[-1],
            context_hash=context_hash,
        )
        if has_more and page_actions
        else None
    )

    return AdminActionLogListRead(
        actions=[
            serialize_admin_action_log_item(
                action,
                admin_users=admin_users,
                records_by_field=records_by_field,
            )
            for action in page_actions
        ],
        action_type_options=admin_action_type_options(),
        limit=query_limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )
