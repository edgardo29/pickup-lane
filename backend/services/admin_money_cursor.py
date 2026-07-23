"""Cursor helpers for scalable admin money list endpoints."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, or_


def encode_money_cursor(sort_value: datetime | int, row_id: uuid.UUID) -> str:
    if isinstance(sort_value, datetime):
        encoded_sort_value = sort_value.isoformat()
    else:
        encoded_sort_value = str(sort_value)
    return f"{encoded_sort_value}|{row_id}"


def parse_money_cursor(
    cursor: str | None,
    *,
    field_name: str = "cursor",
    value_type: str = "datetime",
) -> tuple[datetime | int, uuid.UUID] | None:
    if cursor is None or cursor.strip() == "":
        return None

    try:
        raw_sort_value, raw_id = cursor.split("|", 1)
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
) -> Any:
    parsed = parse_money_cursor(cursor, value_type=value_type)
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
) -> Any:
    parsed = parse_money_cursor(cursor, value_type=value_type)
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
) -> str | None:
    if not page_has_more(rows, limit=limit):
        return None

    last_row = rows[limit - 1]
    return encode_money_cursor(getattr(last_row, sort_attr), last_row.id)


def next_cursor_for_rows_with_value(
    rows: list[Any],
    *,
    limit: int,
    value_getter: Any,
) -> str | None:
    if not page_has_more(rows, limit=limit):
        return None

    last_row = rows[limit - 1]
    return encode_money_cursor(value_getter(last_row), last_row.id)
