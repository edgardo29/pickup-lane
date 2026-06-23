"""Admin permission and response-scope policy helpers."""

from fastapi import HTTPException, status

from backend.models import User

ADMIN_ROLE = "admin"
MODERATOR_ROLE = "moderator"

PERMISSION_DASHBOARD_VIEW = "admin.dashboard.view"
PERMISSION_ACTION_CENTER_VIEW = "admin.action_center.view"
PERMISSION_AUDIT_READ = "admin.audit.read"
PERMISSION_AUDIT_SUPPORT_READ = "admin.audit.support_read"
PERMISSION_OFFICIAL_GAMES_READ = "admin.official_games.read"
PERMISSION_OFFICIAL_GAMES_WRITE = "admin.official_games.write"
PERMISSION_OFFICIAL_GAMES_CANCEL = "admin.official_games.cancel"
PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE = "admin.official_games.roster_manage"
PERMISSION_MONEY_READ = "admin.money.read"
PERMISSION_MONEY_PAYMENT_MANAGE = "admin.money.payment_manage"
PERMISSION_MONEY_REFUND = "admin.money.refund"
PERMISSION_MONEY_CREDIT_MANAGE = "admin.money.credit_manage"
PERMISSION_USERS_READ = "admin.users.read"
PERMISSION_USERS_MANAGE = "admin.users.manage"
PERMISSION_USERS_SUSPEND = "admin.users.suspend"
PERMISSION_USERS_DELETE = "admin.users.delete"
PERMISSION_USERS_HOSTING_MANAGE = "admin.users.hosting_manage"
PERMISSION_COMMUNITY_GAMES_READ = "admin.community_games.read"
PERMISSION_COMMUNITY_GAMES_WRITE = "admin.community_games.write"
PERMISSION_COMMUNITY_GAMES_CANCEL = "admin.community_games.cancel"
PERMISSION_COMMUNITY_GAMES_FLAG = "admin.community_games.flag"
PERMISSION_COMMUNITY_GAMES_HIDE_UNSAFE_CONTENT = (
    "admin.community_games.hide_unsafe_content"
)
PERMISSION_NEED_A_SUB_MODERATE = "admin.need_a_sub.moderate"
PERMISSION_CONTENT_MODERATE = "admin.content.moderate"
PERMISSION_CHAT_ROOMS_MANAGE = "admin.chat_rooms.manage"
PERMISSION_NOTIFICATIONS_READ = "admin.notifications.read"
PERMISSION_NOTIFICATIONS_MANAGE = "admin.notifications.manage"
PERMISSION_POLICIES_MANAGE = "admin.policies.manage"
PERMISSION_STAFF_MANAGE = "admin.staff.manage"
PERMISSION_VENUES_MANAGE = "admin.venues.manage"
PERMISSION_VENUE_IMAGES_MANAGE = "admin.venue_images.manage"

DATA_SCOPE_PUBLIC_SAFE = "public-safe"
DATA_SCOPE_SUPPORT_SAFE = "support-safe"
DATA_SCOPE_ADMIN_ONLY = "admin-only"
DATA_SCOPE_MONEY_SENSITIVE = "money-sensitive"
DATA_SCOPE_STAFF_SENSITIVE = "staff-sensitive"
DATA_SCOPE_STRIPE_SENSITIVE = "stripe-sensitive"

ADMIN_PERMISSIONS = frozenset(
    {
        PERMISSION_DASHBOARD_VIEW,
        PERMISSION_ACTION_CENTER_VIEW,
        PERMISSION_AUDIT_READ,
        PERMISSION_AUDIT_SUPPORT_READ,
        PERMISSION_OFFICIAL_GAMES_READ,
        PERMISSION_OFFICIAL_GAMES_WRITE,
        PERMISSION_OFFICIAL_GAMES_CANCEL,
        PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
        PERMISSION_MONEY_READ,
        PERMISSION_MONEY_PAYMENT_MANAGE,
        PERMISSION_MONEY_REFUND,
        PERMISSION_MONEY_CREDIT_MANAGE,
        PERMISSION_USERS_READ,
        PERMISSION_USERS_MANAGE,
        PERMISSION_USERS_SUSPEND,
        PERMISSION_USERS_DELETE,
        PERMISSION_USERS_HOSTING_MANAGE,
        PERMISSION_COMMUNITY_GAMES_READ,
        PERMISSION_COMMUNITY_GAMES_WRITE,
        PERMISSION_COMMUNITY_GAMES_CANCEL,
        PERMISSION_COMMUNITY_GAMES_FLAG,
        PERMISSION_COMMUNITY_GAMES_HIDE_UNSAFE_CONTENT,
        PERMISSION_NEED_A_SUB_MODERATE,
        PERMISSION_CONTENT_MODERATE,
        PERMISSION_CHAT_ROOMS_MANAGE,
        PERMISSION_NOTIFICATIONS_READ,
        PERMISSION_NOTIFICATIONS_MANAGE,
        PERMISSION_POLICIES_MANAGE,
        PERMISSION_STAFF_MANAGE,
        PERMISSION_VENUES_MANAGE,
        PERMISSION_VENUE_IMAGES_MANAGE,
    }
)

MODERATOR_PERMISSIONS = frozenset(
    {
        PERMISSION_ACTION_CENTER_VIEW,
        PERMISSION_AUDIT_SUPPORT_READ,
        PERMISSION_COMMUNITY_GAMES_READ,
        PERMISSION_COMMUNITY_GAMES_FLAG,
        PERMISSION_COMMUNITY_GAMES_HIDE_UNSAFE_CONTENT,
        PERMISSION_NEED_A_SUB_MODERATE,
        PERMISSION_CONTENT_MODERATE,
    }
)

ROLE_PERMISSIONS = {
    ADMIN_ROLE: ADMIN_PERMISSIONS,
    MODERATOR_ROLE: MODERATOR_PERMISSIONS,
}

ROLE_DATA_SCOPES = {
    ADMIN_ROLE: frozenset(
        {
            DATA_SCOPE_PUBLIC_SAFE,
            DATA_SCOPE_SUPPORT_SAFE,
            DATA_SCOPE_ADMIN_ONLY,
            DATA_SCOPE_MONEY_SENSITIVE,
            DATA_SCOPE_STAFF_SENSITIVE,
            DATA_SCOPE_STRIPE_SENSITIVE,
        }
    ),
    MODERATOR_ROLE: frozenset(
        {
            DATA_SCOPE_PUBLIC_SAFE,
            DATA_SCOPE_SUPPORT_SAFE,
        }
    ),
}


def get_admin_permissions_for_role(role: str) -> tuple[str, ...]:
    return tuple(sorted(ROLE_PERMISSIONS.get(role, frozenset())))


def get_admin_permissions_for_user(user: User) -> tuple[str, ...]:
    return get_admin_permissions_for_role(user.role)


def user_has_admin_permission(user: User, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.role, frozenset())


def _require_active_admin_account(user: User) -> None:
    if user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active account required.",
        )


def require_user_admin_permission(user: User, permission: str) -> None:
    _require_active_admin_account(user)

    if not user_has_admin_permission(user, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )


def require_user_any_admin_permission(
    user: User,
    permissions: tuple[str, ...],
) -> None:
    _require_active_admin_account(user)

    if not any(
        user_has_admin_permission(user, permission) for permission in permissions
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )


def get_admin_data_scopes_for_user(user: User) -> tuple[str, ...]:
    return tuple(sorted(ROLE_DATA_SCOPES.get(user.role, frozenset())))
