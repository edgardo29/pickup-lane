from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.sub_post_position_schema import SubPostPositionRead


class AdminNeedASubUserRead(BaseModel):
    id: UUID
    display_name: str
    account_status: str


class AdminNeedASubRequestCountsRead(BaseModel):
    total_count: int = 0
    pending_count: int = 0
    confirmed_count: int = 0
    waitlisted_count: int = 0
    terminal_count: int = 0


class AdminNeedASubPostListItemRead(BaseModel):
    id: UUID
    post_status: str
    team_name: str | None = None
    format_label: str
    environment_type: str
    game_player_group: str
    starts_at: datetime
    ends_at: datetime
    starts_on_local: date
    timezone: str
    location_name: str
    city: str
    state: str
    subs_needed: int
    owner: AdminNeedASubUserRead
    request_counts: AdminNeedASubRequestCountsRead
    created_at: datetime
    updated_at: datetime


class AdminNeedASubPostListRead(BaseModel):
    posts: list[AdminNeedASubPostListItemRead] = Field(default_factory=list)
    total_count: int = 0
    offset: int = 0
    limit: int = 50
    next_cursor: str | None = None
    has_more: bool = False


class AdminNeedASubPostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID
    post_status: str
    sport_type: str
    format_label: str
    environment_type: str
    skill_level: str
    game_player_group: str
    team_name: str | None
    starts_at: datetime
    ends_at: datetime
    timezone: str
    location_name: str
    address_line_1: str
    city: str
    state: str
    postal_code: str
    country_code: str
    neighborhood: str | None
    subs_needed: int
    price_due_at_venue_cents: int
    currency: str
    payment_note: str | None
    notes: str | None
    expires_at: datetime
    filled_at: datetime | None
    canceled_at: datetime | None
    canceled_by_user_id: UUID | None
    cancel_reason: str | None
    removed_at: datetime | None
    removed_by_user_id: UUID | None
    remove_reason: str | None
    created_at: datetime
    updated_at: datetime
    positions: list[SubPostPositionRead] = Field(default_factory=list)
    pending_count: int = 0
    confirmed_count: int = 0
    sub_waitlist_count: int = 0


class AdminNeedASubStatusHistoryRead(BaseModel):
    id: UUID
    old_status: str | None = None
    new_status: str
    change_source: str
    change_reason: str | None = None
    changed_by: AdminNeedASubUserRead | None = None
    created_at: datetime


class AdminNeedASubRequestRead(BaseModel):
    id: UUID
    sub_post_position_id: UUID
    position_label: str
    player_group: str
    requester: AdminNeedASubUserRead
    request_status: str
    confirmed_at: datetime | None = None
    declined_at: datetime | None = None
    sub_waitlisted_at: datetime | None = None
    canceled_at: datetime | None = None
    expired_at: datetime | None = None
    no_show_reported_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    status_history: list[AdminNeedASubStatusHistoryRead] = Field(default_factory=list)


class AdminNeedASubAuditActionRead(BaseModel):
    id: UUID
    admin_user_id: UUID
    action_type: str
    reason: str | None = None
    created_at: datetime


class AdminNeedASubPostDetailRead(BaseModel):
    post: AdminNeedASubPostRead
    owner: AdminNeedASubUserRead
    request_counts: AdminNeedASubRequestCountsRead
    requests: list[AdminNeedASubRequestRead] = Field(default_factory=list)
    request_total_count: int = 0
    request_offset: int = 0
    request_limit: int = 50
    post_status_history: list[AdminNeedASubStatusHistoryRead] = Field(
        default_factory=list
    )
    audit_actions: list[AdminNeedASubAuditActionRead] = Field(default_factory=list)
    audit_total_count: int = 0
    audit_offset: int = 0
    audit_limit: int = 50
