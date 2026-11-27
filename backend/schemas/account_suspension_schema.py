from datetime import datetime

from pydantic import BaseModel


class SuspendedAccountRead(BaseModel):
    account_status: str
    notice_title: str
    notice_message: str
    notice_occurred_at: datetime
