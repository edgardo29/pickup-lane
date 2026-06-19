"""Admin audit action workflows and validation helpers."""

import re
import uuid
from datetime import date, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    Booking,
    ChatMessage,
    Game,
    GameCredit,
    GameParticipant,
    Notification,
    Payment,
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
from backend.schemas.admin_action_schema import AdminActionCreate, AdminActionNoteCreate
from backend.services.admin_action_policy import (
    ADMIN_ACTION_TARGET_FIELDS,
    TARGET_ADMIN_ACTION_ID,
    TARGET_BOOKING_ID,
    TARGET_GAME_CREDIT_ID,
    TARGET_GAME_ID,
    TARGET_MESSAGE_ID,
    TARGET_NOTIFICATION_ID,
    TARGET_PARTICIPANT_ID,
    TARGET_PAYMENT_ID,
    TARGET_REFUND_ID,
    TARGET_SUB_CHAT_MESSAGE_ID,
    TARGET_SUB_POST_ID,
    TARGET_SUB_POST_POSITION_ID,
    TARGET_SUB_POST_REQUEST_ID,
    TARGET_USER_ID,
    TARGET_VENUE_ID,
    TARGET_VENUE_IMAGE_ID,
    TARGET_SUPPORT_FLAG_ID,
    AdminActionPolicy,
    TargetRule,
    get_admin_action_policy,
)
from backend.services.admin_permission_service import get_admin_data_scopes_for_user
from backend.services.auth_service import require_user_admin_permission
from backend.services.user_service import build_user_conflict_detail

MAX_REASON_LENGTH = 1000
MAX_IDEMPOTENCY_KEY_LENGTH = 160
MAX_METADATA_STRING_LENGTH = 2000
MAX_METADATA_LIST_LENGTH = 100
MAX_METADATA_DICT_KEYS = 100

FORBIDDEN_METADATA_KEY_FRAGMENTS = {
    "auth_user_id",
    "firebase_uid",
    "firebase",
    "stripe_customer_id",
    "stripe_payment_method_id",
    "card_fingerprint",
    "raw_payload",
    "raw_request",
    "request_body",
    "headers",
    "authorization",
    "token",
    "cookie",
    "client_secret",
    "stripe_payload",
    "message_body",
    "body_text",
}

SENSITIVE_NOTE_PATTERNS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "firebase_uid",
    "stripe_customer_id",
    "stripe_payment_method_id",
    "card_fingerprint",
    "sk_live_",
    "sk_test_",
)

SENSITIVE_METADATA_VALUE_PATTERNS = SENSITIVE_NOTE_PATTERNS + (
    "whsec_",
    "rk_live_",
    "rk_test_",
)

SENSITIVE_METADATA_VALUE_REGEXES = (
    re.compile(r"\b(pm|cus|seti|pi|ch|card)_[A-Za-z0-9]+"),
)

METADATA_TOP_LEVEL_KEYS_BY_BUILDER: dict[str, frozenset[str] | None] = {
    "audit_note": frozenset({"note_length"}),
    "credit": frozenset({"amount_cents", "credit_reason", "game_credit_id"}),
    "game_cancellation": frozenset(
        {
            "old_game_status",
            "new_game_status",
            "notified_user_count",
            "cancelled_at",
            "cancelled_booking_count",
            "paid_booking_count",
            "processing_payment_booking_count",
            "uncharged_pending_booking_count",
            "refund_followup_required",
            "payment_followup_required",
            "payment_refund_created",
            "refund_created_count",
            "refund_failed_count",
            "refund_processing_count",
            "refund_missing_charge_count",
            "credit_restored_count",
            "credit_restored_cents",
            "credit_released_count",
            "credit_released_cents",
        }
    ),
    "moderation": frozenset(
        {
            "source",
            "reviewed",
            "before",
            "after",
            "old_status",
            "new_status",
            "removed_by",
            "hidden_by",
        }
    ),
    "money": frozenset(
        {
            "amount_cents",
            "before",
            "currency",
            "after",
            "refund_reason",
            "refund_status",
            "old_refund_status",
            "new_refund_status",
            "payment_type",
            "payment_status",
            "old_payment_status",
            "new_payment_status",
            "source",
            "reviewed",
        }
    ),
    "official_game": frozenset(
        {
            "game",
            "replacement",
            "changed_fields",
            "checkout_sensitive_changed_fields",
            "expired_pending_booking_count",
            "before",
            "after",
            "payment_handling",
            "game_price_per_player_cents",
            "booking_total_cents",
            "discount_cents",
            "created_payment",
            "removed_participant_ids",
            "removed_count",
            "payment_refund_created",
            "removal_outcome",
            "refund_created_count",
            "refund_failed_count",
            "refund_processing_count",
            "refund_follow_up_required",
            "credit_restored_count",
            "credit_restored_cents",
            "waitlist_advanced_entry_ids",
        }
    ),
    "support": frozenset(
        {
            "source",
            "reviewed",
            "before",
            "after",
            "old_status",
            "new_status",
            "status",
        }
    ),
}

TARGET_MODEL_BY_FIELD = {
    TARGET_USER_ID: User,
    TARGET_GAME_ID: Game,
    TARGET_BOOKING_ID: Booking,
    TARGET_PARTICIPANT_ID: GameParticipant,
    TARGET_PAYMENT_ID: Payment,
    TARGET_REFUND_ID: Refund,
    TARGET_GAME_CREDIT_ID: GameCredit,
    TARGET_VENUE_ID: Venue,
    TARGET_VENUE_IMAGE_ID: VenueImage,
    TARGET_MESSAGE_ID: ChatMessage,
    TARGET_SUB_POST_ID: SubPost,
    TARGET_SUB_POST_REQUEST_ID: SubPostRequest,
    TARGET_SUB_POST_POSITION_ID: SubPostPosition,
    TARGET_SUB_CHAT_MESSAGE_ID: SubPostChatMessage,
    TARGET_NOTIFICATION_ID: Notification,
    TARGET_ADMIN_ACTION_ID: AdminAction,
    TARGET_SUPPORT_FLAG_ID: SupportFlag,
}

TARGET_NOT_FOUND_DETAIL = {
    TARGET_USER_ID: "Target user not found.",
    TARGET_GAME_ID: "Target game not found.",
    TARGET_BOOKING_ID: "Target booking not found.",
    TARGET_PARTICIPANT_ID: "Target participant not found.",
    TARGET_PAYMENT_ID: "Target payment not found.",
    TARGET_REFUND_ID: "Target refund not found.",
    TARGET_GAME_CREDIT_ID: "Target game credit not found.",
    TARGET_VENUE_ID: "Target venue not found.",
    TARGET_VENUE_IMAGE_ID: "Target venue image not found.",
    TARGET_MESSAGE_ID: "Target message not found.",
    TARGET_SUB_POST_ID: "Target Need a Sub post not found.",
    TARGET_SUB_POST_REQUEST_ID: "Target Need a Sub request not found.",
    TARGET_SUB_POST_POSITION_ID: "Target Need a Sub position not found.",
    TARGET_SUB_CHAT_MESSAGE_ID: "Target Need a Sub chat message not found.",
    TARGET_NOTIFICATION_ID: "Target notification not found.",
    TARGET_ADMIN_ACTION_ID: "Target admin action not found.",
    TARGET_SUPPORT_FLAG_ID: "Target support flag not found.",
}


def build_admin_action_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "ck_admin_actions_action_type" in error_text:
        return "action_type is not supported."

    if "ck_admin_actions_target_required" in error_text:
        return "At least one target field must be provided."

    if "uq_admin_actions_audit_note_idempotency" in error_text:
        return "Audit note with this idempotency key already exists."

    return build_user_conflict_detail(exc)


def unsupported_action_type_response() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="action_type is not supported.",
    )


def get_policy_or_400(action_type: str) -> AdminActionPolicy:
    policy = get_admin_action_policy(action_type)
    if policy is None:
        raise unsupported_action_type_response()
    return policy


def normalize_optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None

    normalized = " ".join(value.strip().split())
    if not normalized:
        return None

    if len(normalized) > MAX_REASON_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be {MAX_REASON_LENGTH} characters or fewer.",
        )

    return normalized


def normalize_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    if len(normalized) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "idempotency_key must be "
                f"{MAX_IDEMPOTENCY_KEY_LENGTH} characters or fewer."
            ),
        )

    return normalized


def provided_target_fields(action_data: dict[str, Any]) -> set[str]:
    return {
        field_name
        for field_name in ADMIN_ACTION_TARGET_FIELDS
        if action_data.get(field_name) is not None
    }


def describe_fields(fields: tuple[str, ...] | list[str] | set[str]) -> str:
    return ", ".join(sorted(fields))


def validate_required_rule(action_type: str, rule: TargetRule, data: dict[str, Any]) -> None:
    if rule.all_of:
        missing_fields = [
            field_name for field_name in rule.all_of if data.get(field_name) is None
        ]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"{action_type} requires target field(s): "
                    f"{describe_fields(missing_fields)}."
                ),
            )

    if rule.one_of and not any(data.get(field_name) is not None for field_name in rule.one_of):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{action_type} requires one of target field(s): "
                f"{describe_fields(rule.one_of)}."
            ),
        )


def validate_target_policy(
    policy: AdminActionPolicy,
    action_data: dict[str, Any],
    *,
    client_targets_only: bool,
) -> None:
    allowed_fields = (
        policy.client_allowed_target_fields
        if client_targets_only and policy.client_allowed_target_fields is not None
        else policy.allowed_target_fields
    )
    unexpected_targets = provided_target_fields(action_data) - allowed_fields
    if unexpected_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{policy.action_type} does not allow target field(s): "
                f"{describe_fields(unexpected_targets)}."
            ),
        )

    for rule in policy.required_target_rules:
        validate_required_rule(policy.action_type, rule, action_data)


def validate_required_reason(policy: AdminActionPolicy, reason: str | None) -> None:
    if policy.requires_reason and not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{policy.action_type} requires a reason.",
        )


def validate_reference_exists(
    db: Session,
    field_name: str,
    record_id: uuid.UUID,
) -> None:
    model = TARGET_MODEL_BY_FIELD.get(field_name)
    if model is None:
        return

    record = db.get(model, record_id)
    if record is None or getattr(record, "deleted_at", None) is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=TARGET_NOT_FOUND_DETAIL[field_name],
        )


def validate_target_references(db: Session, action_data: dict[str, Any]) -> None:
    for field_name in ADMIN_ACTION_TARGET_FIELDS:
        target_id = action_data.get(field_name)
        if target_id is not None:
            validate_reference_exists(db, field_name, target_id)


def validate_metadata_key(key: str) -> None:
    normalized_key = key.strip().lower()
    if not normalized_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="metadata keys cannot be empty.",
        )

    if any(fragment in normalized_key for fragment in FORBIDDEN_METADATA_KEY_FRAGMENTS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="metadata contains a forbidden sensitive field.",
        )


def validate_metadata_string_value(value: str) -> None:
    lower_value = value.lower()
    if any(pattern in lower_value for pattern in SENSITIVE_METADATA_VALUE_PATTERNS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="metadata contains a forbidden sensitive value.",
        )

    if any(regex.search(value) for regex in SENSITIVE_METADATA_VALUE_REGEXES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="metadata contains a forbidden sensitive value.",
        )


def normalize_metadata_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, uuid.UUID):
        return str(value)

    if isinstance(value, datetime | date):
        return value.isoformat()

    if isinstance(value, str):
        if len(value) > MAX_METADATA_STRING_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "metadata string values must be "
                    f"{MAX_METADATA_STRING_LENGTH} characters or fewer."
                ),
            )
        validate_metadata_string_value(value)
        return value

    if isinstance(value, list):
        if len(value) > MAX_METADATA_LIST_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "metadata lists must contain "
                    f"{MAX_METADATA_LIST_LENGTH} items or fewer."
                ),
            )
        return [normalize_metadata_value(item) for item in value]

    if isinstance(value, dict):
        if len(value) > MAX_METADATA_DICT_KEYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "metadata objects must contain "
                    f"{MAX_METADATA_DICT_KEYS} keys or fewer."
                ),
            )

        normalized_dict = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="metadata keys must be strings.",
                )
            validate_metadata_key(key)
            normalized_dict[key] = normalize_metadata_value(item)
        return normalized_dict

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="metadata values must be JSON primitives, arrays, or objects.",
    )


def build_action_metadata(
    policy: AdminActionPolicy,
    metadata: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if metadata is None:
        return None

    if not isinstance(metadata, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="metadata must be an object.",
        )

    normalized_metadata = normalize_metadata_value(metadata)
    allowed_keys = METADATA_TOP_LEVEL_KEYS_BY_BUILDER.get(policy.metadata_builder_key)
    if allowed_keys is not None:
        unexpected_keys = set(metadata) - allowed_keys
        if unexpected_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"{policy.action_type} metadata does not allow field(s): "
                    f"{describe_fields(unexpected_keys)}."
                ),
            )

    return normalized_metadata


def validate_note_text(note: str) -> str:
    normalized_note = normalize_optional_text(note, "note")
    if normalized_note is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="note is required.",
        )

    lower_note = normalized_note.lower()
    if any(pattern in lower_note for pattern in SENSITIVE_NOTE_PATTERNS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="note appears to contain sensitive data.",
        )

    return normalized_note


def action_data_from_payload(payload: AdminActionCreate) -> dict[str, Any]:
    return payload.model_dump()


def build_admin_action_instance(
    *,
    admin_user_id: uuid.UUID,
    policy: AdminActionPolicy,
    action_data: dict[str, Any],
    created_at: datetime | None = None,
) -> AdminAction:
    normalized_reason = normalize_optional_text(action_data.get("reason"), "reason")
    validate_required_reason(policy, normalized_reason)
    metadata = build_action_metadata(policy, action_data.get("metadata"))
    admin_action_data = {
        "id": uuid.uuid4(),
        "admin_user_id": admin_user_id,
        "action_type": policy.action_type,
        "reason": normalized_reason,
        "metadata_": metadata,
        "idempotency_key": normalize_idempotency_key(action_data.get("idempotency_key")),
        **{
            field_name: action_data.get(field_name)
            for field_name in ADMIN_ACTION_TARGET_FIELDS
        },
    }
    if created_at is not None:
        admin_action_data["created_at"] = created_at

    return AdminAction(**admin_action_data)


def create_admin_action(
    db: Session,
    *,
    admin_user: User,
    payload: AdminActionCreate,
) -> AdminAction:
    action_data = action_data_from_payload(payload)
    policy = get_policy_or_400(action_data["action_type"])

    if policy.action_type == "append_audit_note":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the audit note endpoint to append audit notes.",
        )

    require_user_admin_permission(admin_user, policy.mutation_permission)
    validate_target_policy(policy, action_data, client_targets_only=True)
    validate_target_references(db, action_data)
    admin_action = build_admin_action_instance(
        admin_user_id=admin_user.id,
        policy=policy,
        action_data=action_data,
    )

    try:
        db.add(admin_action)
        db.commit()
        db.refresh(admin_action)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_admin_action_conflict_detail(exc),
        ) from exc

    return admin_action


def record_admin_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    action_type: str,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    created_at: datetime | None = None,
    **targets: uuid.UUID | None,
) -> AdminAction:
    policy = get_policy_or_400(action_type)
    unknown_targets = set(targets) - set(ADMIN_ACTION_TARGET_FIELDS)
    if unknown_targets:
        raise ValueError(
            f"Unknown admin action target(s): {describe_fields(unknown_targets)}"
        )

    action_data = {
        "action_type": action_type,
        "reason": reason,
        "metadata": metadata,
        "idempotency_key": idempotency_key,
        **{
            field_name: targets.get(field_name)
            for field_name in ADMIN_ACTION_TARGET_FIELDS
        },
    }
    validate_target_policy(policy, action_data, client_targets_only=False)
    admin_action = build_admin_action_instance(
        admin_user_id=admin_user_id,
        policy=policy,
        action_data=action_data,
        created_at=created_at,
    )
    db.add(admin_action)
    return admin_action


def get_admin_action_or_404(db: Session, admin_action_id: uuid.UUID) -> AdminAction:
    admin_action = db.get(AdminAction, admin_action_id)

    if admin_action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin action not found.",
        )

    return admin_action


def user_can_read_admin_action(user: User, admin_action: AdminAction) -> bool:
    policy = get_admin_action_policy(admin_action.action_type)
    if policy is None:
        return False

    return policy.sensitivity_scope in get_admin_data_scopes_for_user(user)


def get_admin_action_for_viewer_or_404(
    db: Session,
    admin_action_id: uuid.UUID,
    viewer_user: User,
) -> AdminAction:
    admin_action = get_admin_action_or_404(db, admin_action_id)

    if not user_can_read_admin_action(viewer_user, admin_action):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin action not found.",
        )

    return admin_action


def build_copied_note_targets(
    original_action: AdminAction,
    note_policy: AdminActionPolicy,
) -> dict[str, uuid.UUID | None]:
    copied_targets = {
        field_name: getattr(original_action, field_name)
        for field_name in note_policy.server_copied_target_fields
        if field_name != TARGET_ADMIN_ACTION_ID
    }
    copied_targets[TARGET_ADMIN_ACTION_ID] = original_action.id
    return copied_targets


def get_existing_audit_note_by_idempotency_key(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    target_admin_action_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction).where(
            AdminAction.action_type == "append_audit_note",
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.target_admin_action_id == target_admin_action_id,
            AdminAction.idempotency_key == idempotency_key,
        )
    )


def append_admin_action_note(
    db: Session,
    *,
    admin_user: User,
    target_admin_action_id: uuid.UUID,
    payload: AdminActionNoteCreate,
) -> AdminAction:
    original_action = get_admin_action_or_404(db, target_admin_action_id)
    original_policy = get_policy_or_400(original_action.action_type)
    if original_action.action_type == "append_audit_note":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audit notes cannot target another audit note.",
        )
    if not original_policy.allows_audit_note:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audit notes are not allowed for this action.",
        )

    require_user_admin_permission(admin_user, original_policy.effective_note_permission)
    note_text = validate_note_text(payload.note)
    idempotency_key = normalize_idempotency_key(payload.idempotency_key)
    if idempotency_key is not None:
        existing_note = get_existing_audit_note_by_idempotency_key(
            db,
            admin_user_id=admin_user.id,
            target_admin_action_id=target_admin_action_id,
            idempotency_key=idempotency_key,
        )
        if existing_note is not None:
            return existing_note

    note_policy = get_policy_or_400("append_audit_note")
    action_data = {
        "action_type": "append_audit_note",
        "reason": note_text,
        "metadata": {"note_length": len(note_text)},
        "idempotency_key": idempotency_key,
        **build_copied_note_targets(original_action, note_policy),
    }
    validate_target_policy(note_policy, action_data, client_targets_only=False)
    admin_action = build_admin_action_instance(
        admin_user_id=admin_user.id,
        policy=note_policy,
        action_data=action_data,
    )

    try:
        db.add(admin_action)
        db.commit()
        db.refresh(admin_action)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_admin_action_conflict_detail(exc),
        ) from exc

    return admin_action


def list_admin_actions(
    db: Session,
    *,
    viewer_user: User,
    admin_user_id: uuid.UUID | None = None,
    action_type: str | None = None,
    target_filters: dict[str, uuid.UUID | None] | None = None,
    limit: int | None = None,
) -> list[AdminAction]:
    statement = select(AdminAction)

    if admin_user_id is not None:
        statement = statement.where(AdminAction.admin_user_id == admin_user_id)

    if action_type is not None:
        get_policy_or_400(action_type)
        statement = statement.where(AdminAction.action_type == action_type)

    for field_name, target_id in (target_filters or {}).items():
        if target_id is not None:
            statement = statement.where(getattr(AdminAction, field_name) == target_id)

    visible_actions: list[AdminAction] = []
    for admin_action in db.scalars(statement.order_by(AdminAction.created_at.desc())):
        if user_can_read_admin_action(viewer_user, admin_action):
            visible_actions.append(admin_action)

            if limit is not None and len(visible_actions) >= limit:
                break

    return visible_actions
