from pydantic import BaseModel, Field

from backend.schemas.admin_money_context_schema import (
    AdminMoneyAuditActionSummaryRead,
    AdminMoneyBookingContextRead,
    AdminMoneyCommunityPublishAttemptContextRead,
    AdminMoneyGameContextRead,
    AdminMoneyHostPublishFeeContextRead,
    AdminMoneyPaymentUserContextRead,
)
from backend.schemas.admin_money_credit_schema import (
    AdminMoneyCreditGrantSummaryRead,
    AdminMoneyCreditUsageSummaryRead,
)
from backend.schemas.admin_money_issue_schema import AdminMoneyIssueSummaryRead
from backend.schemas.admin_money_payment_schema import AdminMoneyPaymentDetailItemRead
from backend.schemas.admin_money_refund_schema import AdminMoneyRefundDetailItemRead


class AdminMoneyPaymentDetailRead(BaseModel):
    payment: AdminMoneyPaymentDetailItemRead
    payer: AdminMoneyPaymentUserContextRead | None = None
    booking: AdminMoneyBookingContextRead | None = None
    game: AdminMoneyGameContextRead | None = None
    host_publish_fee: AdminMoneyHostPublishFeeContextRead | None = None
    community_publish_attempt: AdminMoneyCommunityPublishAttemptContextRead | None = None
    publish_host: AdminMoneyPaymentUserContextRead | None = None
    refunds: list[AdminMoneyRefundDetailItemRead] = Field(default_factory=list)
    credit_grants: list[AdminMoneyCreditGrantSummaryRead] = Field(default_factory=list)
    credit_usages: list[AdminMoneyCreditUsageSummaryRead] = Field(default_factory=list)
    linked_money_issues: list[AdminMoneyIssueSummaryRead] = Field(default_factory=list)
    admin_actions: list[AdminMoneyAuditActionSummaryRead] = Field(default_factory=list)
