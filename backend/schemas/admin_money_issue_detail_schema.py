from pydantic import BaseModel, Field

from backend.schemas.admin_money_context_schema import (
    AdminMoneyBookingContextRead,
    AdminMoneyGameContextRead,
)
from backend.schemas.admin_money_credit_schema import (
    AdminMoneyCreditGrantSummaryRead,
    AdminMoneyCreditUsageSummaryRead,
)
from backend.schemas.admin_money_issue_schema import (
    AdminMoneyIssueEventRead,
    AdminMoneyIssueSummaryRead,
)
from backend.schemas.admin_money_payment_schema import AdminMoneyPaymentDetailItemRead
from backend.schemas.admin_money_refund_schema import (
    AdminMoneyRefundDetailItemRead,
    AdminMoneyRefundEventRead,
)


class AdminMoneyIssueDetailRead(BaseModel):
    money_issue: AdminMoneyIssueSummaryRead
    events: list[AdminMoneyIssueEventRead] = Field(default_factory=list)
    recent_refund_events: list[AdminMoneyRefundEventRead] = Field(default_factory=list)
    refund: AdminMoneyRefundDetailItemRead | None = None
    payment: AdminMoneyPaymentDetailItemRead | None = None
    booking: AdminMoneyBookingContextRead | None = None
    game: AdminMoneyGameContextRead | None = None
    credit: AdminMoneyCreditGrantSummaryRead | None = None
    credit_usages: list[AdminMoneyCreditUsageSummaryRead] = Field(default_factory=list)
