"""Admin workflows for sparse Platform Notices."""

import base64
import binascii
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, func, literal_column, or_, select, text, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    PlatformNotice,
    PlatformNoticeRecipient,
    PlatformNoticeSelectedRead,
    User,
)
from backend.schemas.platform_notice_schema import (
    PlatformNoticeCancel,
    PlatformNoticeCreate,
    PlatformNoticeCreateResultRead,
    PlatformNoticeListRead,
    PlatformNoticeRead,
    PlatformNoticeRecipientListRead,
    PlatformNoticeRecipientRead,
)
from backend.services.account_eligibility_service import (
    account_eligible_condition,
    user_is_account_eligible,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.user_service import get_user_display_name

AUDIENCE_TYPE_ALL_ELIGIBLE = "all_eligible_users"
AUDIENCE_TYPE_SELECTED = "selected_users"
PLATFORM_NOTICE_AUDIENCE_TYPES = {
    AUDIENCE_TYPE_ALL_ELIGIBLE,
    AUDIENCE_TYPE_SELECTED,
}
MAX_SELECTED_PLATFORM_NOTICE_USERS = 200
MAX_NOTICE_LIST_LIMIT = 30
MAX_RECIPIENT_LIST_LIMIT = 100
MAX_NOTICE_HISTORY_SEARCH_LENGTH = 200
MIN_NOTICE_HISTORY_SEARCH_MEANINGFUL_CHARS = 3
NOTICE_HISTORY_SORT_VERSION = "published_desc_v1"
NOTICE_HISTORY_SEARCH_EXPRESSION_SQL = (
    "(coalesce(title, '') || ' ' || coalesce(message, ''))"
)
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalize_single_line_text(
    value: str,
    *,
    field_name: str,
    max_length: int,
) -> str:
    normalized = " ".join(str(value or "").strip().split())
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required.",
        )
    if CONTROL_CHARACTER_PATTERN.search(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} contains unsupported characters.",
        )
    if len(normalized) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be {max_length} characters or fewer.",
        )
    return normalized


def normalize_message(value: str) -> str:
    normalized = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message is required.",
        )
    if CONTROL_CHARACTER_PATTERN.search(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message contains unsupported characters.",
        )
    if len(normalized) > 4000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message must be 4000 characters or fewer.",
        )
    return normalized


def normalize_cancellation_reason(value: str) -> str:
    normalized = " ".join(str(value or "").strip().split())
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cancellation_reason is required.",
        )
    if CONTROL_CHARACTER_PATTERN.search(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cancellation_reason contains unsupported characters.",
        )
    if len(normalized) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cancellation_reason must be 1000 characters or fewer.",
        )
    return normalized


def normalize_audience_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in PLATFORM_NOTICE_AUDIENCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="audience_type is not supported.",
        )
    return normalized


def normalize_idempotency_key(value: str) -> str:
    normalized = str(value or "").strip()
    if len(normalized) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be at least 8 characters.",
        )
    if len(normalized) > 160:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be 160 characters or fewer.",
        )
    return normalized


def hash_idempotency_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def escape_like_search(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def normalize_notice_search(value: str | None) -> str | None:
    normalized = " ".join((value or "").strip().lower().split())
    if not normalized:
        return None

    if len(normalized) > MAX_NOTICE_HISTORY_SEARCH_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "search must be "
                f"{MAX_NOTICE_HISTORY_SEARCH_LENGTH} characters or fewer."
            ),
        )

    meaningful_characters = sum(1 for character in normalized if character.isalnum())
    if meaningful_characters < MIN_NOTICE_HISTORY_SEARCH_MEANINGFUL_CHARS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "search must include at least "
                f"{MIN_NOTICE_HISTORY_SEARCH_MEANINGFUL_CHARS} letters or numbers."
            ),
        )

    return normalized


def platform_notice_history_search_expression():
    return literal_column(NOTICE_HISTORY_SEARCH_EXPRESSION_SQL)


def notice_search_context_hash(search: str | None) -> str | None:
    if search is None:
        return None

    return hashlib.sha256(search.encode("utf-8")).hexdigest()


def normalize_selected_user_ids(user_ids: list[uuid.UUID] | None) -> list[uuid.UUID]:
    normalized = sorted(set(user_ids or []), key=str)
    if len(normalized) > MAX_SELECTED_PLATFORM_NOTICE_USERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "selected_user_ids cannot contain more than "
                f"{MAX_SELECTED_PLATFORM_NOTICE_USERS} users."
            ),
        )
    return normalized


def validate_audience_payload(
    *,
    audience_type: str,
    selected_user_ids: list[uuid.UUID],
) -> None:
    if audience_type == AUDIENCE_TYPE_ALL_ELIGIBLE and selected_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="all_eligible_users notices cannot include selected_user_ids.",
        )
    if audience_type == AUDIENCE_TYPE_SELECTED and not selected_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="selected_users notices require at least one selected user.",
        )


def canonical_request_fingerprint(
    *,
    audience_type: str,
    message: str,
    selected_user_ids: list[uuid.UUID],
    title: str,
) -> str:
    payload = {
        "audience_type": audience_type,
        "message": message,
        "selected_user_ids": [str(user_id) for user_id in selected_user_ids],
        "title": title,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def next_global_sequence(db: Session) -> int:
    value = db.scalar(text("SELECT nextval('platform_notice_global_sequence_seq')"))
    return int(value)


def load_users_by_id(
    db: Session,
    user_ids: list[uuid.UUID],
) -> dict[uuid.UUID, User]:
    if not user_ids:
        return {}

    users = db.scalars(select(User).where(User.id.in_(user_ids))).all()
    return {user.id: user for user in users}


def require_selected_users_eligible(
    db: Session,
    selected_user_ids: list[uuid.UUID],
) -> None:
    user_by_id = load_users_by_id(db, selected_user_ids)
    missing_user_ids = [
        user_id for user_id in selected_user_ids if user_id not in user_by_id
    ]
    if missing_user_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "selected_user_not_found",
                "message": "Every selected user must exist before publishing.",
                "missing_user_ids": [str(user_id) for user_id in missing_user_ids],
            },
        )

    ineligible_user_ids = [
        user_id
        for user_id in selected_user_ids
        if not user_is_account_eligible(user_by_id[user_id])
    ]
    if ineligible_user_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "selected_user_ineligible",
                "message": (
                    "Every selected user must be active and eligible before "
                    "the platform notice can be published."
                ),
                "ineligible_user_ids": [
                    str(user_id) for user_id in ineligible_user_ids
                ],
            },
        )


def serialize_admin_summary(user: User | None) -> dict[str, Any] | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "display_name": get_user_display_name(user, fallback="Admin"),
        "email": user.email,
    }


def platform_notice_status(notice: PlatformNotice) -> str:
    return "cancelled" if notice.cancelled_at is not None else "published"


def selected_recipient_count(db: Session, notice_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(PlatformNoticeRecipient)
        .where(PlatformNoticeRecipient.notice_id == notice_id)
    ) or 0


def selected_recipient_counts(
    db: Session,
    notice_ids: list[uuid.UUID],
) -> dict[uuid.UUID, int]:
    if not notice_ids:
        return {}

    rows = db.execute(
        select(
            PlatformNoticeRecipient.notice_id,
            func.count(PlatformNoticeRecipient.user_id),
        )
        .where(PlatformNoticeRecipient.notice_id.in_(notice_ids))
        .group_by(PlatformNoticeRecipient.notice_id)
    ).all()
    return {notice_id: int(count) for notice_id, count in rows}


def serialize_platform_notice(
    db: Session,
    notice: PlatformNotice,
    *,
    selected_count: int | None = None,
) -> PlatformNoticeRead:
    count = selected_count
    if count is None and notice.audience_type == AUDIENCE_TYPE_SELECTED:
        count = selected_recipient_count(db, notice.id)

    return PlatformNoticeRead(
        id=notice.id,
        title=notice.title,
        message=notice.message,
        audience_type=notice.audience_type,
        status=platform_notice_status(notice),
        selected_recipient_count=count or 0,
        global_sequence=notice.global_sequence,
        published_at=notice.published_at,
        created_at=notice.created_at,
        updated_at=notice.updated_at,
        created_by_admin_id=notice.created_by_admin_id,
        created_by_admin=serialize_admin_summary(
            db.get(User, notice.created_by_admin_id)
            if notice.created_by_admin_id
            else None
        ),
        cancelled_at=notice.cancelled_at,
        cancelled_by_admin_id=notice.cancelled_by_admin_id,
        cancelled_by_admin=serialize_admin_summary(
            db.get(User, notice.cancelled_by_admin_id)
            if notice.cancelled_by_admin_id
            else None
        ),
        cancellation_reason=notice.cancellation_reason,
    )


def get_notice_by_admin_idempotency_key(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    idempotency_key_hash: str,
) -> PlatformNotice | None:
    return db.scalar(
        select(PlatformNotice).where(
            PlatformNotice.created_by_admin_id == admin_user_id,
            PlatformNotice.idempotency_key_hash == idempotency_key_hash,
        )
    )


def build_publish_metadata(notice: PlatformNotice, selected_count: int) -> dict[str, Any]:
    return {
        "audience_type": notice.audience_type,
        "selected_recipient_count": selected_count,
        "global_sequence": notice.global_sequence,
        "published_at": notice.published_at.isoformat(),
        "title": notice.title,
        "message_length": len(notice.message),
    }


def create_platform_notice(
    db: Session,
    *,
    creator_user: User,
    payload: PlatformNoticeCreate,
) -> PlatformNoticeCreateResultRead:
    title = normalize_single_line_text(
        payload.title,
        field_name="title",
        max_length=150,
    )
    message = normalize_message(payload.message)
    audience_type = normalize_audience_type(payload.audience_type)
    selected_user_ids = normalize_selected_user_ids(payload.selected_user_ids)
    validate_audience_payload(
        audience_type=audience_type,
        selected_user_ids=selected_user_ids,
    )

    idempotency_key = normalize_idempotency_key(payload.idempotency_key)
    idempotency_key_hash = hash_idempotency_key(idempotency_key)
    request_fingerprint = canonical_request_fingerprint(
        audience_type=audience_type,
        message=message,
        selected_user_ids=selected_user_ids,
        title=title,
    )

    existing_notice = get_notice_by_admin_idempotency_key(
        db,
        admin_user_id=creator_user.id,
        idempotency_key_hash=idempotency_key_hash,
    )
    if existing_notice is not None:
        if existing_notice.request_fingerprint != request_fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "idempotency_key_conflict",
                    "message": (
                        "This idempotency key was already used for a different "
                        "platform notice request."
                    ),
                },
            )
        return PlatformNoticeCreateResultRead(
            notice=serialize_platform_notice(db, existing_notice),
            idempotent_replay=True,
        )

    if audience_type == AUDIENCE_TYPE_SELECTED:
        require_selected_users_eligible(db, selected_user_ids)

    published_at = now_utc()
    notice = PlatformNotice(
        id=uuid.uuid4(),
        title=title,
        message=message,
        audience_type=audience_type,
        global_sequence=(
            next_global_sequence(db)
            if audience_type == AUDIENCE_TYPE_ALL_ELIGIBLE
            else None
        ),
        published_at=published_at,
        created_by_admin_id=creator_user.id,
        idempotency_key_hash=idempotency_key_hash,
        request_fingerprint=request_fingerprint,
        created_at=published_at,
        updated_at=published_at,
    )

    try:
        db.add(notice)
        db.flush()
        if audience_type == AUDIENCE_TYPE_SELECTED:
            db.add_all([
                PlatformNoticeRecipient(
                    notice_id=notice.id,
                    user_id=user_id,
                    created_at=published_at,
                )
                for user_id in selected_user_ids
            ])

        selected_count = len(selected_user_ids)
        record_admin_action(
            db,
            admin_user_id=creator_user.id,
            action_type="publish_platform_notice",
            target_platform_notice_id=notice.id,
            metadata=build_publish_metadata(notice, selected_count),
        )
        db.commit()
        db.refresh(notice)
    except IntegrityError as exc:
        db.rollback()
        replay_notice = get_notice_by_admin_idempotency_key(
            db,
            admin_user_id=creator_user.id,
            idempotency_key_hash=idempotency_key_hash,
        )
        if replay_notice is not None:
            if replay_notice.request_fingerprint != request_fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "idempotency_key_conflict",
                        "message": (
                            "This idempotency key was already used for a "
                            "different platform notice request."
                        ),
                    },
                ) from exc
            return PlatformNoticeCreateResultRead(
                notice=serialize_platform_notice(db, replay_notice),
                idempotent_replay=True,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc

    return PlatformNoticeCreateResultRead(
        notice=serialize_platform_notice(
            db,
            notice,
            selected_count=len(selected_user_ids),
        ),
        idempotent_replay=False,
    )


def encode_notice_cursor(
    notice: PlatformNotice,
    *,
    audience_type: str | None,
    search: str | None,
    status_filter: str | None,
) -> str:
    payload = {
        "audience": audience_type,
        "last_id": str(notice.id),
        "last_published_at": notice.published_at.isoformat(),
        "normalized_search_hash": notice_search_context_hash(search),
        "sort_version": NOTICE_HISTORY_SORT_VERSION,
        "status": status_filter,
    }
    return base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")


def decode_notice_cursor(cursor: str | None) -> dict[str, Any] | None:
    normalized = str(cursor or "").strip()
    if not normalized:
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(normalized.encode("ascii")))
        required_keys = {
            "audience",
            "last_id",
            "last_published_at",
            "normalized_search_hash",
            "sort_version",
            "status",
        }
        if not isinstance(payload, dict) or not required_keys.issubset(payload):
            raise ValueError
        return {
            "audience": payload.get("audience"),
            "id": uuid.UUID(payload["last_id"]),
            "published_at": datetime.fromisoformat(payload["last_published_at"]),
            "search_hash": payload.get("normalized_search_hash"),
            "sort_version": payload.get("sort_version"),
            "status": payload.get("status"),
        }
    except (
        KeyError,
        TypeError,
        ValueError,
        binascii.Error,
        json.JSONDecodeError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        ) from exc


def validate_notice_cursor_context(
    cursor_data: dict[str, Any] | None,
    *,
    audience_type: str | None,
    search: str | None,
    status_filter: str | None,
) -> None:
    if cursor_data is None:
        return

    if (
        cursor_data.get("audience") != audience_type
        or cursor_data.get("search_hash") != notice_search_context_hash(search)
        or cursor_data.get("sort_version") != NOTICE_HISTORY_SORT_VERSION
        or cursor_data.get("status") != status_filter
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor does not match the current query.",
        )


def notice_cursor_filter(cursor_data: dict[str, Any] | None):
    if cursor_data is None:
        return None
    return tuple_(PlatformNotice.published_at, PlatformNotice.id) < tuple_(
        cursor_data["published_at"],
        cursor_data["id"],
    )


def list_platform_notices(
    db: Session,
    *,
    audience_type: str | None = None,
    cursor: str | None = None,
    limit: int = MAX_NOTICE_LIST_LIMIT,
    search: str | None = None,
    status_filter: str | None = None,
) -> PlatformNoticeListRead:
    effective_limit = max(1, min(limit, MAX_NOTICE_LIST_LIMIT))
    statement = select(PlatformNotice)
    normalized_audience_type = (
        normalize_audience_type(audience_type) if audience_type else None
    )

    if normalized_audience_type:
        statement = statement.where(
            PlatformNotice.audience_type == normalized_audience_type
        )

    normalized_status = str(status_filter or "").strip().lower()
    if normalized_status:
        if normalized_status == "published":
            statement = statement.where(PlatformNotice.cancelled_at.is_(None))
        elif normalized_status == "cancelled":
            statement = statement.where(PlatformNotice.cancelled_at.is_not(None))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="status is not supported.",
            )

    normalized_search = normalize_notice_search(search)
    if normalized_search:
        like_search = f"%{escape_like_search(normalized_search)}%"
        statement = statement.where(
            platform_notice_history_search_expression().ilike(
                like_search,
                escape="\\",
            )
        )

    cursor_data = decode_notice_cursor(cursor)
    validate_notice_cursor_context(
        cursor_data,
        audience_type=normalized_audience_type,
        search=normalized_search,
        status_filter=normalized_status or None,
    )
    cursor_filter = notice_cursor_filter(cursor_data)
    if cursor_filter is not None:
        statement = statement.where(cursor_filter)

    notices = db.scalars(
        statement.order_by(
            PlatformNotice.published_at.desc(),
            PlatformNotice.id.desc(),
        ).limit(effective_limit + 1)
    ).all()

    page_notices = list(notices[:effective_limit])
    selected_counts = selected_recipient_counts(
        db,
        [
            notice.id
            for notice in page_notices
            if notice.audience_type == AUDIENCE_TYPE_SELECTED
        ],
    )
    return PlatformNoticeListRead(
        notices=[
            serialize_platform_notice(
                db,
                notice,
                selected_count=selected_counts.get(notice.id, 0),
            )
            for notice in page_notices
        ],
        limit=effective_limit,
        next_cursor=encode_notice_cursor(
            page_notices[-1],
            audience_type=normalized_audience_type,
            search=normalized_search,
            status_filter=normalized_status or None,
        )
        if len(notices) > effective_limit and page_notices
        else None,
        has_more=len(notices) > effective_limit,
    )


def get_platform_notice_or_404(
    db: Session,
    notice_id: uuid.UUID,
) -> PlatformNotice:
    notice = db.get(PlatformNotice, notice_id)
    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform notice not found.",
        )
    return notice


def get_platform_notice(
    db: Session,
    *,
    notice_id: uuid.UUID,
) -> PlatformNoticeRead:
    return serialize_platform_notice(db, get_platform_notice_or_404(db, notice_id))


def encode_recipient_cursor(recipient: PlatformNoticeRecipient) -> str:
    payload = {
        "created_at": recipient.created_at.isoformat(),
        "user_id": str(recipient.user_id),
    }
    return base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")


def decode_recipient_cursor(cursor: str | None) -> dict[str, Any] | None:
    normalized = str(cursor or "").strip()
    if not normalized:
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(normalized.encode("ascii")))
        return {
            "created_at": datetime.fromisoformat(payload["created_at"]),
            "user_id": uuid.UUID(payload["user_id"]),
        }
    except (
        KeyError,
        TypeError,
        ValueError,
        binascii.Error,
        json.JSONDecodeError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        ) from exc


def recipient_cursor_filter(cursor_data: dict[str, Any] | None):
    if cursor_data is None:
        return None
    return or_(
        PlatformNoticeRecipient.created_at > cursor_data["created_at"],
        and_(
            PlatformNoticeRecipient.created_at == cursor_data["created_at"],
            PlatformNoticeRecipient.user_id > cursor_data["user_id"],
        ),
    )


def list_platform_notice_recipients(
    db: Session,
    *,
    cursor: str | None = None,
    limit: int = 50,
    notice_id: uuid.UUID,
) -> PlatformNoticeRecipientListRead:
    notice = get_platform_notice_or_404(db, notice_id)
    if notice.audience_type != AUDIENCE_TYPE_SELECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only selected-user platform notices have recipient rows.",
        )

    effective_limit = max(1, min(limit, MAX_RECIPIENT_LIST_LIMIT))
    cursor_filter = recipient_cursor_filter(decode_recipient_cursor(cursor))
    statement = (
        select(PlatformNoticeRecipient, User, PlatformNoticeSelectedRead)
        .join(User, User.id == PlatformNoticeRecipient.user_id)
        .outerjoin(
            PlatformNoticeSelectedRead,
            and_(
                PlatformNoticeSelectedRead.notice_id
                == PlatformNoticeRecipient.notice_id,
                PlatformNoticeSelectedRead.user_id == PlatformNoticeRecipient.user_id,
            ),
        )
        .where(PlatformNoticeRecipient.notice_id == notice_id)
    )
    if cursor_filter is not None:
        statement = statement.where(cursor_filter)

    rows = db.execute(
        statement.order_by(
            PlatformNoticeRecipient.created_at.asc(),
            PlatformNoticeRecipient.user_id.asc(),
        ).limit(effective_limit + 1)
    ).all()
    page_rows = rows[:effective_limit]
    recipients = [
        PlatformNoticeRecipientRead(
            user_id=user.id,
            display_name=get_user_display_name(user),
            email=user.email,
            account_status=user.account_status,
            currently_eligible=user_is_account_eligible(user),
            read_at=read.read_at if read else None,
            created_at=recipient.created_at,
        )
        for recipient, user, read in page_rows
    ]

    return PlatformNoticeRecipientListRead(
        recipients=recipients,
        limit=effective_limit,
        next_cursor=encode_recipient_cursor(page_rows[-1][0])
        if len(rows) > effective_limit and page_rows
        else None,
        has_more=len(rows) > effective_limit,
    )


def cancel_platform_notice(
    db: Session,
    *,
    admin_user: User,
    notice_id: uuid.UUID,
    payload: PlatformNoticeCancel,
) -> PlatformNoticeRead:
    notice = db.scalar(
        select(PlatformNotice)
        .where(PlatformNotice.id == notice_id)
        .with_for_update()
    )
    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform notice not found.",
        )
    cancellation_reason = normalize_cancellation_reason(payload.cancellation_reason)

    if notice.cancelled_at is not None:
        return serialize_platform_notice(db, notice)

    cancelled_at = now_utc()
    notice.cancelled_at = cancelled_at
    notice.cancelled_by_admin_id = admin_user.id
    notice.cancellation_reason = cancellation_reason
    notice.updated_at = cancelled_at

    try:
        db.add(notice)
        record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="cancel_platform_notice",
            reason=cancellation_reason,
            target_platform_notice_id=notice.id,
            metadata={
                "audience_type": notice.audience_type,
                "selected_recipient_count": selected_recipient_count(db, notice.id)
                if notice.audience_type == AUDIENCE_TYPE_SELECTED
                else 0,
                "global_sequence": notice.global_sequence,
                "published_at": notice.published_at.isoformat(),
                "title": notice.title,
                "message_length": len(notice.message),
                "cancelled_at": cancelled_at.isoformat(),
                "cancellation_reason": cancellation_reason,
            },
        )
        db.commit()
        db.refresh(notice)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc

    return serialize_platform_notice(db, notice)


def active_global_notice_count(db: Session) -> int:
    return db.scalar(
        select(func.count())
        .select_from(PlatformNotice)
        .where(
            PlatformNotice.audience_type == AUDIENCE_TYPE_ALL_ELIGIBLE,
            PlatformNotice.cancelled_at.is_(None),
            PlatformNotice.published_at <= now_utc(),
        )
    ) or 0


def current_eligible_user_count(db: Session) -> int:
    return db.scalar(
        select(func.count()).select_from(User).where(account_eligible_condition())
    ) or 0


def admin_platform_notice_summary(db: Session) -> dict[str, int]:
    return {
        "active_global_notice_count": active_global_notice_count(db),
        "current_eligible_user_count": current_eligible_user_count(db),
    }


__all__ = [
    "AUDIENCE_TYPE_ALL_ELIGIBLE",
    "AUDIENCE_TYPE_SELECTED",
    "MAX_SELECTED_PLATFORM_NOTICE_USERS",
    "cancel_platform_notice",
    "create_platform_notice",
    "get_platform_notice",
    "list_platform_notice_recipients",
    "list_platform_notices",
]
