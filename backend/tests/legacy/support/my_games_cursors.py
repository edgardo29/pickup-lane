from __future__ import annotations

from base64 import urlsafe_b64encode
from datetime import datetime
from json import dumps
from typing import Any
from uuid import UUID, uuid4


def make_my_games_cursor(
    *,
    domain: str = "games",
    view: str = "upcoming",
    sort_direction: str = "asc",
    starts_at: datetime | str = "2026-08-01T18:00:00+00:00",
    created_at: datetime | str = "2026-07-01T12:00:00+00:00",
    item_id: UUID | str | None = None,
    extra_payload: dict[str, Any] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "domain": domain,
        "view": view,
        "sort_direction": sort_direction,
        "starts_at": starts_at.isoformat()
        if isinstance(starts_at, datetime)
        else starts_at,
        "created_at": created_at.isoformat()
        if isinstance(created_at, datetime)
        else created_at,
        "id": str(item_id or uuid4()),
    }
    if extra_payload is not None:
        payload.update(extra_payload)

    serialized = dumps(payload, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    return urlsafe_b64encode(serialized).decode("ascii")
