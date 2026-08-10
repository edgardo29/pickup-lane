"""Source-owned inventory of WS03-03A recent-auth protected actions."""

from __future__ import annotations

from dataclasses import dataclass

from backend.services.auth_service import RECENT_AUTH_REQUIRED_CODE


@dataclass(frozen=True)
class RecentAuthProtectedAction:
    action_id: str
    actor: str
    method: str
    route_template: str
    enforcement_dependency: str
    frontend_caller: str
    protections: tuple[str, ...]
    provider_mfa_dependency: str
    recent_auth_required: bool = True


RECENT_AUTH_PROTECTED_ACTIONS: tuple[RecentAuthProtectedAction, ...] = (
    RecentAuthProtectedAction(
        action_id="self_account_delete",
        actor="current_user",
        method="DELETE",
        route_template="/auth/account",
        enforcement_dependency="require_recent_app_user",
        frontend_caller="useDeleteAccountSettings",
        protections=(
            "typed confirmation",
            "existing account deletion workflow guards",
            "Firebase provider remains account authority",
        ),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="admin_user_role_change",
        actor="admin",
        method="PATCH",
        route_template="/admin/users/{user_id}/role",
        enforcement_dependency="require_recent_active_admin",
        frontend_caller="AdminUserDetailPage role action",
        protections=("active admin", "final-admin guard", "idempotency key", "audit action"),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="admin_user_delete",
        actor="admin",
        method="POST",
        route_template="/admin/users/{user_id}/delete",
        enforcement_dependency="require_recent_active_admin",
        frontend_caller="AdminUserDeletePreviewModal",
        protections=("active admin", "current-state token", "idempotency key", "audit action"),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="admin_user_suspend",
        actor="admin",
        method="POST",
        route_template="/admin/users/{user_id}/suspend",
        enforcement_dependency="require_recent_active_admin",
        frontend_caller="AdminUserSuspensionModal",
        protections=("active admin", "current-state token", "idempotency key", "audit action"),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="admin_user_unsuspend",
        actor="admin",
        method="POST",
        route_template="/admin/users/{user_id}/unsuspend",
        enforcement_dependency="require_recent_active_admin",
        frontend_caller="AdminUserUnsuspensionModal",
        protections=("active admin", "idempotency key", "audit action"),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="admin_financial_outcome_create",
        actor="admin",
        method="POST",
        route_template="/admin/money/financial-outcomes",
        enforcement_dependency="require_recent_active_admin",
        frontend_caller="adminFinancialOutcomeApi",
        protections=("active admin", "idempotency key", "money issue linkage"),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="admin_money_issue_resolve",
        actor="admin",
        method="POST",
        route_template="/admin/money/issues/{money_issue_id}/resolve",
        enforcement_dependency="require_recent_active_admin",
        frontend_caller="AdminMoneyIssuePage",
        protections=("active admin", "current issue state", "idempotency key"),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="admin_money_issue_retry_credit",
        actor="admin",
        method="POST",
        route_template="/admin/money/issues/{money_issue_id}/retry-credit",
        enforcement_dependency="require_recent_active_admin",
        frontend_caller="AdminMoneyIssuePage",
        protections=("active admin", "current issue state", "idempotency key"),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="admin_refund_retry",
        actor="admin",
        method="POST",
        route_template="/admin/money/refunds/{refund_id}/retry",
        enforcement_dependency="require_recent_active_admin",
        frontend_caller="AdminMoneyIssuePage/AdminMoneyRefundPage",
        protections=("active admin", "provider reconciliation", "idempotency key"),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="admin_refund_reconcile",
        actor="admin",
        method="POST",
        route_template="/admin/money/refunds/{refund_id}/reconcile",
        enforcement_dependency="require_recent_active_admin",
        frontend_caller="AdminMoneyRefundPage",
        protections=("active admin", "provider reconciliation", "idempotency key"),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="admin_game_credit_issue",
        actor="admin",
        method="POST",
        route_template="/admin/game-credits/issue",
        enforcement_dependency="require_recent_active_admin",
        frontend_caller="admin money credit workflows",
        protections=("active admin", "source validation", "idempotency key", "ledger row"),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="admin_game_credit_reverse",
        actor="admin",
        method="POST",
        route_template="/admin/game-credits/{game_credit_id}/reverse",
        enforcement_dependency="require_recent_active_admin",
        frontend_caller="admin money credit workflows",
        protections=("active admin", "usage guard", "idempotency key", "ledger row"),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="official_game_cancel_execute",
        actor="admin",
        method="POST",
        route_template="/admin/official-games/{game_id}/cancel",
        enforcement_dependency="require_recent_active_admin",
        frontend_caller="AdminOfficialGamePage",
        protections=("active admin", "preview token", "provider refunds", "audit action"),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="platform_notice_create",
        actor="admin",
        method="POST",
        route_template="/admin/platform-notices",
        enforcement_dependency="require_recent_active_admin",
        frontend_caller="AdminPlatformNoticesPage",
        protections=("active admin", "idempotency key", "recipient selection audit"),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="platform_notice_cancel",
        actor="admin",
        method="POST",
        route_template="/admin/platform-notices/{notice_id}/cancel",
        enforcement_dependency="require_recent_active_admin",
        frontend_caller="AdminPlatformNoticesPage",
        protections=("active admin", "current notice state", "audit action"),
        provider_mfa_dependency="deferred_to_ws03_03b",
    ),
    RecentAuthProtectedAction(
        action_id="saved_payment_method_default_change",
        actor="current_user",
        method="PATCH",
        route_template="/user-payment-methods/{payment_method_id}/default",
        enforcement_dependency="require_recent_active_user",
        frontend_caller="PaymentMethodsPage",
        protections=("active user", "owned saved-card check", "persistent account-state change"),
        provider_mfa_dependency="not_required_for_current_user_saved_card_management",
    ),
    RecentAuthProtectedAction(
        action_id="saved_payment_method_detach",
        actor="current_user",
        method="DELETE",
        route_template="/user-payment-methods/{payment_method_id}",
        enforcement_dependency="require_recent_active_user",
        frontend_caller="PaymentMethodsPage",
        protections=("active user", "owned saved-card check", "persistent account-state change"),
        provider_mfa_dependency="not_required_for_current_user_saved_card_management",
    ),
)

RECENT_AUTH_PROTECTED_ROUTE_KEYS = frozenset(
    (action.method, action.route_template) for action in RECENT_AUTH_PROTECTED_ACTIONS
)

RECENT_AUTH_PUBLIC_ERROR_CODE = RECENT_AUTH_REQUIRED_CODE
