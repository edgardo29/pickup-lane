from pydantic import BaseModel, Field

from backend.schemas.admin_money_context_schema import (
    AdminMoneyAuditActionSummaryRead,
    AdminMoneyBookingContextRead,
    AdminMoneyGameContextRead,
)
from backend.schemas.admin_money_credit_schema import (
    AdminMoneyCreditGrantSummaryRead,
    AdminMoneyCreditUsageSummaryRead,
)
from backend.schemas.admin_money_issue_schema import AdminMoneyIssueSummaryRead
from backend.schemas.admin_money_payment_schema import AdminMoneyPaymentDetailItemRead
from backend.schemas.admin_money_refund_schema import AdminMoneyRefundDetailItemRead


class AdminMoneyCreditDetailRead(BaseModel):
    credit: AdminMoneyCreditGrantSummaryRead
    credit_usages: list[AdminMoneyCreditUsageSummaryRead] = Field(default_factory=list)
    credit_usage_count: int = 0
    credit_usages_truncated: bool = False
    payments: list[AdminMoneyPaymentDetailItemRead] = Field(default_factory=list)
    refunds: list[AdminMoneyRefundDetailItemRead] = Field(default_factory=list)
    booking: AdminMoneyBookingContextRead | None = None
    game: AdminMoneyGameContextRead | None = None
    linked_money_issues: list[AdminMoneyIssueSummaryRead] = Field(default_factory=list)
    admin_actions: list[AdminMoneyAuditActionSummaryRead] = Field(default_factory=list)
