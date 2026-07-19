from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class AdminUserListRead(BaseModel):
    id: UUID
    display_name: str
    email: str | None
    phone: str | None
    role: str
    account_status: str
    hosting_status: str
    email_verified: bool
    home_city: str | None
    home_state: str | None
    member_since: datetime
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class AdminUserStaffRead(AdminUserListRead):
    pass


class AdminUserStaffRoleChangeCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    role: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=160)


class AdminUserStaffRoleChangeResultRead(BaseModel):
    user_id: UUID
    previous_role: str
    role: str
    changed_at: datetime
    admin_action_id: UUID


class AdminUserProfileRead(AdminUserListRead):
    hosting_suspended_until: datetime | None


class AdminUserStatsSummaryRead(BaseModel):
    games_played_count: int
    games_hosted_completed_count: int
    no_show_count: int
    late_cancel_count: int
    host_cancel_count: int
    last_calculated_at: datetime


class AdminUserBookingSummaryRead(BaseModel):
    id: UUID
    game_id: UUID
    game_type: str
    game_title: str
    game_status: str
    starts_at: datetime
    booking_status: str
    participant_count: int
    created_at: datetime


class AdminUserParticipationSummaryRead(BaseModel):
    id: UUID
    game_id: UUID
    booking_id: UUID | None
    game_type: str
    game_title: str
    game_status: str
    starts_at: datetime
    participant_type: str
    participant_status: str
    attendance_status: str
    joined_at: datetime


class AdminUserHostedGameSummaryRead(BaseModel):
    id: UUID
    game_type: str
    title: str
    game_status: str
    starts_at: datetime
    city: str
    state: str


class AdminUserSubPostSummaryRead(BaseModel):
    id: UUID
    post_status: str
    team_name: str | None
    starts_at: datetime
    city: str
    state: str
    subs_needed: int
    created_at: datetime


class AdminUserSubRequestSummaryRead(BaseModel):
    id: UUID
    sub_post_id: UUID
    sub_post_position_id: UUID
    request_status: str
    post_status: str
    team_name: str | None
    starts_at: datetime
    city: str
    state: str
    created_at: datetime


class AdminUserAuditActionSummaryRead(BaseModel):
    id: UUID
    admin_user_id: UUID
    action_type: str
    reason: str | None
    created_at: datetime


class AdminUserSupportFlagSummaryRead(BaseModel):
    id: UUID
    flag_type: str
    flag_status: str
    severity: str
    source: str
    title: str
    summary: str
    resolution_outcome: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminUserSuspensionOfficialHostImpactRead(BaseModel):
    id: UUID
    title: str
    game_status: str
    starts_at: datetime
    city: str
    state: str


class AdminUserSuspensionPreviewRead(BaseModel):
    user_id: UUID
    account_status: str
    role: str
    can_suspend: bool
    preview_token: str = Field(min_length=64, max_length=64)
    blocking_reasons: list[str] = Field(default_factory=list)
    future_official_host_assignment_count: int = 0
    future_official_host_assignments: list[
        AdminUserSuspensionOfficialHostImpactRead
    ] = Field(default_factory=list)


class AdminUserHostingRestrictionGameImpactRead(BaseModel):
    id: UUID
    title: str
    game_status: str
    starts_at: datetime
    city: str
    state: str


class AdminUserHostingRestrictionPreviewRead(BaseModel):
    user_id: UUID
    account_status: str
    hosting_status: str
    can_restrict: bool
    preview_token: str = Field(min_length=64, max_length=64)
    blocking_reasons: list[str] = Field(default_factory=list)
    future_community_game_count: int = 0
    future_community_games: list[
        AdminUserHostingRestrictionGameImpactRead
    ] = Field(default_factory=list)


class AdminUserDeleteImpactGameRead(BaseModel):
    id: UUID
    title: str
    game_type: str
    game_status: str
    starts_at: datetime
    city: str
    state: str


class AdminUserDeleteImpactPreviewRead(BaseModel):
    user_id: UUID
    account_status: str
    role: str
    hosting_status: str
    can_delete: bool
    preview_token: str = Field(min_length=64, max_length=64)
    blocking_reasons: list[str] = Field(default_factory=list)
    future_official_host_assignment_count: int = 0
    future_official_host_assignments: list[
        AdminUserDeleteImpactGameRead
    ] = Field(default_factory=list)
    future_community_hosted_game_count: int = 0
    future_community_hosted_games: list[
        AdminUserDeleteImpactGameRead
    ] = Field(default_factory=list)
    active_future_booking_count: int = 0
    active_future_official_booking_count: int = 0
    active_future_participation_count: int = 0
    active_future_guest_count: int = 0
    active_waitlist_entry_count: int = 0
    active_owned_sub_post_count: int = 0
    active_sub_request_count: int = 0
    payment_record_count: int = 0
    refund_record_count: int = 0
    game_credit_count: int = 0
    saved_payment_method_count: int = 0
    active_saved_payment_method_count: int = 0
    active_support_flag_count: int = 0


class AdminUserDeleteCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    preview_token: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=160)


class AdminUserDeleteResultRead(BaseModel):
    user_id: UUID
    account_status: str
    deleted_at: datetime
    admin_action_id: UUID


class AdminUserRestrictHostingCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    preview_token: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=160)


class AdminUserRestrictHostingResultRead(BaseModel):
    user_id: UUID
    hosting_status: str
    restricted_at: datetime
    admin_action_id: UUID
    notification_id: UUID


class AdminUserRestoreHostingCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    reason: str = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=160)


class AdminUserRestoreHostingResultRead(BaseModel):
    user_id: UUID
    hosting_status: str
    restored_at: datetime
    admin_action_id: UUID
    notification_id: UUID


class AdminUserSuspendCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    preview_token: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=160)


class AdminUserSuspendResultRead(BaseModel):
    user_id: UUID
    account_status: str
    suspended_at: datetime
    admin_action_id: UUID
    notification_id: UUID


class AdminUserUnsuspendCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    reason: str = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=160)


class AdminUserUnsuspendResultRead(BaseModel):
    user_id: UUID
    account_status: str
    unsuspended_at: datetime
    admin_action_id: UUID
    notification_id: UUID


class AdminUserDetailRead(BaseModel):
    user: AdminUserProfileRead
    stats: AdminUserStatsSummaryRead | None = None
    bookings: list[AdminUserBookingSummaryRead] = Field(default_factory=list)
    participations: list[AdminUserParticipationSummaryRead] = Field(
        default_factory=list
    )
    community_games_hosted: list[AdminUserHostedGameSummaryRead] = Field(
        default_factory=list
    )
    official_host_assignments: list[AdminUserHostedGameSummaryRead] = Field(
        default_factory=list
    )
    sub_posts_owned: list[AdminUserSubPostSummaryRead] = Field(default_factory=list)
    sub_requests_made: list[AdminUserSubRequestSummaryRead] = Field(
        default_factory=list
    )
    audit_actions: list[AdminUserAuditActionSummaryRead] = Field(
        default_factory=list
    )
    support_flags: list[AdminUserSupportFlagSummaryRead] = Field(
        default_factory=list
    )
