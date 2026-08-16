"""Curated pagination contract inventory for current API collection routes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaginationContract:
    method: str
    path: str
    style: str
    limit_default: int | None
    limit_max: int | None
    max_owner: str
    deterministic_order: str
    next_cursor: bool = False
    offset_param: str | None = None

    @property
    def key(self) -> tuple[str, str]:
        return self.method, self.path


@dataclass(frozen=True)
class PaginationHandoff:
    method: str
    path: str
    concern: str
    recommended_owner: str

    @property
    def key(self) -> tuple[str, str]:
        return self.method, self.path


PAGINATION_CONTRACTS = (
    PaginationContract("GET", "/admin/actions", "limit", 100, 200, "route", "created_at/id"),
    PaginationContract(
        "GET",
        "/admin/actions/log",
        "cursor",
        None,
        None,
        "service",
        "created_at/id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/admin/community-games",
        "cursor+offset",
        50,
        100,
        "route",
        "view-specific starts_at/id",
        next_cursor=True,
        offset_param="offset",
    ),
    PaginationContract(
        "GET",
        "/admin/community-games/{game_id}/chat/messages",
        "offset",
        20,
        20,
        "route",
        "created_at/id",
        offset_param="offset",
    ),
    PaginationContract(
        "GET",
        "/admin/lookups/users",
        "limit",
        10,
        10,
        "route+service",
        "display name/id",
    ),
    PaginationContract(
        "GET",
        "/admin/lookups/venues",
        "limit",
        100,
        200,
        "route",
        "name/id",
    ),
    PaginationContract(
        "GET",
        "/admin/money/credits",
        "cursor",
        50,
        100,
        "route",
        "created_at/id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/admin/money/issues",
        "cursor",
        50,
        100,
        "route",
        "created_at/id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/admin/money/payments",
        "cursor",
        50,
        100,
        "route",
        "created_at/id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/admin/money/refunds",
        "cursor",
        50,
        100,
        "route",
        "created_at/id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/admin/money/refunds/{refund_id}/events",
        "cursor",
        50,
        100,
        "route",
        "created_at/id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/admin/need-a-sub",
        "cursor+offset",
        50,
        100,
        "route",
        "view-specific starts_at/id",
        next_cursor=True,
        offset_param="offset",
    ),
    PaginationContract(
        "GET",
        "/admin/need-a-sub/{post_id}/chat/messages",
        "offset",
        20,
        20,
        "route",
        "created_at/id",
        offset_param="offset",
    ),
    PaginationContract(
        "GET",
        "/admin/notifications",
        "cursor",
        None,
        None,
        "service",
        "created_at/id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/admin/official-games",
        "cursor",
        24,
        None,
        "service",
        "starts_at/id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/admin/official-games/{game_id}/chat/messages",
        "offset",
        20,
        20,
        "route",
        "created_at/id",
        offset_param="offset",
    ),
    PaginationContract(
        "GET",
        "/admin/official-games/{game_id}/user-search",
        "limit",
        10,
        25,
        "route",
        "display name/id",
    ),
    PaginationContract(
        "GET",
        "/admin/rejected-attempts",
        "limit",
        100,
        200,
        "route",
        "created_at/id",
    ),
    PaginationContract(
        "GET",
        "/admin/review-cases",
        "cursor+offset",
        24,
        100,
        "route",
        "updated_at/id",
        next_cursor=True,
        offset_param="offset",
    ),
    PaginationContract(
        "GET",
        "/admin/support-flags",
        "limit",
        100,
        200,
        "route",
        "created_at/id",
    ),
    PaginationContract(
        "GET",
        "/admin/users",
        "cursor",
        50,
        100,
        "route",
        "created_at/id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/admin/users/{user_id}",
        "embedded-limit",
        50,
        100,
        "route",
        "activity created_at/id",
    ),
    PaginationContract(
        "GET",
        "/admin/users/{user_id}/game-activity",
        "offset",
        25,
        100,
        "route",
        "starts_at/id",
        offset_param="offset",
    ),
    PaginationContract(
        "GET",
        "/admin/users/{user_id}/need-a-sub-activity",
        "offset",
        25,
        100,
        "route",
        "starts_at/id",
        offset_param="offset",
    ),
    PaginationContract("GET", "/chat-messages", "limit", 50, None, "service", "created_at/id"),
    PaginationContract(
        "GET",
        "/games/browse",
        "cursor",
        40,
        None,
        "service",
        "starts_at/created_at/id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/inbox/app-updates",
        "cursor",
        30,
        50,
        "route",
        "occurred_at/source_rank/source_id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/inbox/game-activity",
        "cursor",
        30,
        50,
        "route",
        "occurred_at/source_rank/source_id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/my-games",
        "cursor",
        40,
        None,
        "service",
        "bucket-specific starts_at/created_at/id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/my-games/need-a-sub",
        "cursor",
        40,
        None,
        "service",
        "bucket-specific starts_at/created_at/id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/need-a-sub/posts/{sub_post_id}/chat/messages",
        "limit",
        50,
        None,
        "service",
        "created_at/id",
    ),
    PaginationContract(
        "GET",
        "/need-a-sub/posts/cards",
        "cursor",
        40,
        None,
        "service",
        "starts_at/created_at/id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/admin/platform-notices",
        "cursor",
        30,
        30,
        "route+service",
        "published_at/id",
        next_cursor=True,
    ),
    PaginationContract(
        "GET",
        "/admin/platform-notices/{notice_id}/recipients",
        "cursor",
        50,
        100,
        "route",
        "created_at/user_id",
        next_cursor=True,
    ),
)


PAGINATION_HANDOFFS = (
    PaginationHandoff("GET", "/users", "unbounded generic admin/user listing", "API owner"),
    PaginationHandoff("GET", "/user-stats", "unbounded stats listing", "API owner"),
    PaginationHandoff("GET", "/user-payment-methods", "unbounded private listing", "API owner"),
    PaginationHandoff("GET", "/venues", "unbounded venue listing", "API owner"),
    PaginationHandoff("GET", "/venue-approval-requests", "unbounded admin/support listing", "API owner"),
    PaginationHandoff("GET", "/venue-images", "unbounded image listing", "API owner"),
    PaginationHandoff("GET", "/game-chats", "unbounded chat listing", "API owner"),
    PaginationHandoff("GET", "/game-credits", "unbounded credit listing", "API owner"),
    PaginationHandoff("GET", "/admin/game-images", "unbounded admin image listing", "API owner"),
    PaginationHandoff(
        "GET",
        "/admin/official-games/{game_id}/participants",
        "bounded by one game but no explicit page contract",
        "API owner",
    ),
    PaginationHandoff(
        "GET",
        "/admin/official-games/{game_id}/bookings",
        "bounded by one game but no explicit page contract",
        "API owner",
    ),
    PaginationHandoff(
        "GET",
        "/admin/official-games/{game_id}/waitlist",
        "bounded by one game but no explicit page contract",
        "API owner",
    ),
    PaginationHandoff("GET", "/admin/venues/{venue_id}/images", "unbounded image listing", "API owner"),
    PaginationHandoff("GET", "/game-images", "unbounded image listing", "API owner"),
    PaginationHandoff("GET", "/community-game-details", "unbounded detail listing", "API owner"),
    PaginationHandoff("GET", "/games/participant-counts", "unbounded aggregate listing", "API owner"),
    PaginationHandoff("GET", "/games/{game_id}/participants", "bounded by one game but no explicit page contract", "API owner"),
    PaginationHandoff("GET", "/games", "unbounded game listing", "API owner"),
    PaginationHandoff("GET", "/bookings/me", "unbounded private booking listing", "API owner"),
    PaginationHandoff("GET", "/bookings", "unbounded booking listing", "API owner"),
    PaginationHandoff("GET", "/booking-status-history", "unbounded history listing", "API owner"),
    PaginationHandoff("GET", "/booking-policy-acceptances", "unbounded policy evidence listing", "API owner"),
    PaginationHandoff("GET", "/game-participants/me", "unbounded private participant listing", "API owner"),
    PaginationHandoff("GET", "/game-participants", "unbounded participant listing", "API owner"),
    PaginationHandoff("GET", "/game-status-history", "unbounded history listing", "API owner"),
    PaginationHandoff("GET", "/participant-status-history", "unbounded history listing", "API owner"),
    PaginationHandoff("GET", "/host-publish-fees/me", "unbounded private fee listing", "API owner"),
    PaginationHandoff("GET", "/host-publish-fees", "unbounded fee listing", "API owner"),
    PaginationHandoff("GET", "/notifications/me", "unbounded private notification listing", "API owner"),
    PaginationHandoff("GET", "/waitlist-entries/me", "unbounded private waitlist listing", "API owner"),
    PaginationHandoff("GET", "/waitlist-entries", "unbounded waitlist listing", "API owner"),
    PaginationHandoff("GET", "/payments", "unbounded payment listing", "API owner"),
    PaginationHandoff("GET", "/payment-events", "unbounded provider-event listing", "API owner"),
    PaginationHandoff("GET", "/policy-documents", "unbounded legal document listing", "API owner"),
    PaginationHandoff("GET", "/policy-acceptances", "unbounded legal evidence listing", "API owner"),
    PaginationHandoff("GET", "/refunds", "unbounded refund listing", "API owner"),
    PaginationHandoff("GET", "/need-a-sub/posts", "unbounded legacy/public listing", "API owner"),
    PaginationHandoff("GET", "/need-a-sub/posts/mine", "unbounded private listing", "API owner"),
    PaginationHandoff(
        "GET",
        "/need-a-sub/posts/{sub_post_id}/positions",
        "bounded by one post but no explicit page contract",
        "API owner",
    ),
    PaginationHandoff(
        "GET",
        "/need-a-sub/posts/{sub_post_id}/requests",
        "bounded by one post but no explicit page contract",
        "API owner",
    ),
    PaginationHandoff("GET", "/need-a-sub/my-requests", "unbounded private request listing", "API owner"),
    PaginationHandoff(
        "GET",
        "/need-a-sub/requests/{request_id}/status-history",
        "bounded by one request but no explicit page contract",
        "API owner",
    ),
    PaginationHandoff(
        "GET",
        "/need-a-sub/posts/{sub_post_id}/status-history",
        "bounded by one post but no explicit page contract",
        "API owner",
    ),
)


def pagination_contract_keys() -> frozenset[tuple[str, str]]:
    return frozenset(contract.key for contract in PAGINATION_CONTRACTS)


def pagination_handoff_keys() -> frozenset[tuple[str, str]]:
    return frozenset(handoff.key for handoff in PAGINATION_HANDOFFS)
