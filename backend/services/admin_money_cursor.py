"""Cursor helpers for scalable admin money list endpoints."""

import base64
import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Mapping

from fastapi import HTTPException, status
from sqlalchemy import and_, or_


_CONTEXT_MISMATCH_DETAIL = "cursor does not match the current query."


def _cursor_context_digest(context: Mapping[str, object]) -> str:
    normalized_context = json.dumps(
        context,
        default=str,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(normalized_context.encode("utf-8")).hexdigest()


def _encode_cursor_payload(payload: dict[str, object]) -> str:
    raw_payload = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw_payload).decode("ascii").rstrip("=")


def _decode_cursor_payload(cursor: str, *, field_name: str) -> dict[str, object]:
    try:
        padding = "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode((cursor + padding).encode("ascii"))
        payload = json.loads(decoded)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is not valid.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is not valid.",
        )
    return payload


def encode_money_cursor(
    sort_value: datetime | int,
    row_id: uuid.UUID,
    *,
    context: Mapping[str, object] | None = None,
) -> str:
    if isinstance(sort_value, datetime):
        encoded_sort_value = sort_value.isoformat()
    else:
        encoded_sort_value = str(sort_value)
    if context is not None:
        return _encode_cursor_payload(
            {
                "context": _cursor_context_digest(context),
                "id": str(row_id),
                "sort": encoded_sort_value,
                "v": 1,
            }
        )
    return f"{encoded_sort_value}|{row_id}"


def parse_money_cursor(
    cursor: str | None,
    *,
    field_name: str = "cursor",
    value_type: str = "datetime",
    context: Mapping[str, object] | None = None,
) -> tuple[datetime | int, uuid.UUID] | None:
    if cursor is None or cursor.strip() == "":
        return None

    if "|" not in cursor:
        payload = _decode_cursor_payload(cursor, field_name=field_name)
        if payload.get("v") != 1 or not isinstance(payload.get("sort"), str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} is not valid.",
            )
        if not isinstance(payload.get("id"), str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} is not valid.",
            )
        if context is not None and payload.get("context") != _cursor_context_digest(
            context
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_CONTEXT_MISMATCH_DETAIL,
            )
        raw_sort_value = payload["sort"]
        raw_id = payload["id"]
    else:
        if context is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_CONTEXT_MISMATCH_DETAIL,
            )
        raw_sort_value, raw_id = cursor.split("|", 1)

    try:
        sort_value: datetime | int
        if value_type == "int":
            sort_value = int(raw_sort_value)
        else:
            sort_value = datetime.fromisoformat(raw_sort_value)
        return sort_value, uuid.UUID(raw_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is not valid.",
        ) from exc


def apply_desc_cursor(
    statement: Any,
    model: Any,
    sort_column: Any,
    cursor: str | None,
    *,
    value_type: str = "datetime",
    context: Mapping[str, object] | None = None,
) -> Any:
    parsed = parse_money_cursor(cursor, value_type=value_type, context=context)
    if parsed is None:
        return statement

    sort_value, row_id = parsed
    return statement.where(
        or_(
            sort_column < sort_value,
            and_(sort_column == sort_value, model.id < row_id),
        )
    )


def apply_asc_cursor(
    statement: Any,
    model: Any,
    sort_column: Any,
    cursor: str | None,
    *,
    value_type: str = "datetime",
    context: Mapping[str, object] | None = None,
) -> Any:
    parsed = parse_money_cursor(cursor, value_type=value_type, context=context)
    if parsed is None:
        return statement

    sort_value, row_id = parsed
    return statement.where(
        or_(
            sort_column > sort_value,
            and_(sort_column == sort_value, model.id > row_id),
        )
    )


def page_has_more(rows: list[Any], *, limit: int) -> bool:
    return len(rows) > limit


def next_cursor_for_rows(
    rows: list[Any],
    *,
    limit: int,
    sort_attr: str,
    context: Mapping[str, object] | None = None,
) -> str | None:
    if not page_has_more(rows, limit=limit):
        return None

    last_row = rows[limit - 1]
    return encode_money_cursor(getattr(last_row, sort_attr), last_row.id, context=context)


def next_cursor_for_rows_with_value(
    rows: list[Any],
    *,
    limit: int,
    value_getter: Any,
    context: Mapping[str, object] | None = None,
) -> str | None:
    if not page_has_more(rows, limit=limit):
        return None

    last_row = rows[limit - 1]
    return encode_money_cursor(value_getter(last_row), last_row.id, context=context)
