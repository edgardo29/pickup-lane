from datetime import datetime
from zoneinfo import ZoneInfo

__all__ = ["local_date_string"]


def local_date_string(starts_at: datetime, timezone_name: str) -> str:
    return starts_at.astimezone(ZoneInfo(timezone_name)).date().isoformat()
