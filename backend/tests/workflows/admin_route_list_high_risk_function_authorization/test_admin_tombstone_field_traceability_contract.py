from __future__ import annotations

import re
import uuid

import pytest

from backend.schemas.admin_action_schema import AdminActionCreate, AdminActionNoteCreate
from backend.schemas.admin_chat_moderation_schema import AdminChatModerationActionCreate
from backend.schemas.admin_community_schema import (
    AdminCommunityGameEnforcementActionCreate,
    AdminCommunityGameHidePaymentTextCreate,
    AdminCommunityGameReviewFlagCreate,
)
from backend.schemas.admin_money_financial_outcome_schema import (
    AdminMoneyFinancialOutcomeCreate,
)
from backend.schemas.admin_money_issue_schema import (
    AdminMoneyIssueCreditRetryCreate,
    AdminMoneyIssueResolveCreate,
)
from backend.schemas.admin_money_refund_schema import (
    AdminMoneyRefundReconcileCreate,
    AdminMoneyRefundRetryCreate,
)
from backend.schemas.admin_need_a_sub_schema import AdminNeedASubEnforcementActionCreate
from backend.schemas.admin_official_game_schema import (
    AdminOfficialGameCancelExecute,
    AdminOfficialGameCreate,
    AdminOfficialGameHostAssign,
    AdminOfficialGameHostRemove,
    AdminOfficialGameHostRemovalExecute,
    AdminOfficialGamePlayerAdd,
    AdminOfficialGamePlayerRemove,
    AdminOfficialGamePlayerRemovalExecute,
    AdminOfficialGameUpdate,
)
from backend.schemas.admin_review_schema import (
    AdminReviewCaseClose,
    AdminReviewCaseNoteCreate,
)
from backend.schemas.community_game_detail_schema import (
    CommunityGameDetailCreate,
    CommunityGameDetailUpdate,
)
from backend.schemas.game_schema import GameCreate, GameUpdate
from backend.schemas.admin_user_schema import (
    AdminUserDeleteCreate,
    AdminUserRestrictHostingCreate,
    AdminUserRestoreHostingCreate,
    AdminUserRoleChangeCreate,
    AdminUserSuspendCreate,
    AdminUserUnsuspendCreate,
)
from backend.schemas.game_credit_schema import (
    GameCreditIssueCreate,
    GameCreditReverseCreate,
)
from backend.schemas.payment_event_schema import PaymentEventUpdate
from backend.schemas.platform_notice_schema import (
    PlatformNoticeCancel,
    PlatformNoticeCreate,
)
from backend.schemas.support_flag_schema import SupportFlagResolve
from backend.schemas.venue_image_schema import (
    VenueImageCompleteUpload,
    VenueImageUpdate,
    VenueImageUploadCreate,
)
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    _add_users,
    _auth_headers,
    _client,
    _count_model_rows,
    _d_tombstone_route_keys,
    _install_tokens_for_users,
    _user,
)

pytestmark = pytest.mark.suite_type("ordinary")


@pytest.mark.requirement("WS03-04D-R9", "WS03-04D-R11")
def test_d_write_schemas_forbid_extra_server_controlled_fields_from_current_source() -> None:
    guarded_models = [
        AdminActionCreate,
        AdminActionNoteCreate,
        AdminChatModerationActionCreate,
        AdminCommunityGameEnforcementActionCreate,
        AdminCommunityGameHidePaymentTextCreate,
        AdminCommunityGameReviewFlagCreate,
        AdminMoneyFinancialOutcomeCreate,
        AdminMoneyIssueCreditRetryCreate,
        AdminMoneyIssueResolveCreate,
        AdminMoneyRefundReconcileCreate,
        AdminMoneyRefundRetryCreate,
        AdminNeedASubEnforcementActionCreate,
        AdminOfficialGameCancelExecute,
        AdminOfficialGameCreate,
        AdminOfficialGameHostAssign,
        AdminOfficialGameHostRemove,
        AdminOfficialGameHostRemovalExecute,
        AdminOfficialGamePlayerAdd,
        AdminOfficialGamePlayerRemove,
        AdminOfficialGamePlayerRemovalExecute,
        AdminOfficialGameUpdate,
        AdminReviewCaseClose,
        AdminReviewCaseNoteCreate,
        AdminUserDeleteCreate,
        AdminUserRestrictHostingCreate,
        AdminUserRestoreHostingCreate,
        AdminUserRoleChangeCreate,
        AdminUserSuspendCreate,
        AdminUserUnsuspendCreate,
        CommunityGameDetailCreate,
        CommunityGameDetailUpdate,
        GameCreate,
        GameUpdate,
        GameCreditIssueCreate,
        GameCreditReverseCreate,
        PaymentEventUpdate,
        PlatformNoticeCancel,
        PlatformNoticeCreate,
        SupportFlagResolve,
        VenueImageCompleteUpload,
        VenueImageUpdate,
        VenueImageUploadCreate,
    ]

    assert {model.__name__ for model in guarded_models} == {
        "AdminActionCreate",
        "AdminActionNoteCreate",
        "AdminChatModerationActionCreate",
        "AdminCommunityGameEnforcementActionCreate",
        "AdminCommunityGameHidePaymentTextCreate",
        "AdminCommunityGameReviewFlagCreate",
        "AdminMoneyFinancialOutcomeCreate",
        "AdminMoneyIssueCreditRetryCreate",
        "AdminMoneyIssueResolveCreate",
        "AdminMoneyRefundReconcileCreate",
        "AdminMoneyRefundRetryCreate",
        "AdminNeedASubEnforcementActionCreate",
        "AdminOfficialGameCancelExecute",
        "AdminOfficialGameCreate",
        "AdminOfficialGameHostAssign",
        "AdminOfficialGameHostRemove",
        "AdminOfficialGameHostRemovalExecute",
        "AdminOfficialGamePlayerAdd",
        "AdminOfficialGamePlayerRemove",
        "AdminOfficialGamePlayerRemovalExecute",
        "AdminOfficialGameUpdate",
        "AdminReviewCaseClose",
        "AdminReviewCaseNoteCreate",
        "AdminUserDeleteCreate",
        "AdminUserRestrictHostingCreate",
        "AdminUserRestoreHostingCreate",
        "AdminUserRoleChangeCreate",
        "AdminUserSuspendCreate",
        "AdminUserUnsuspendCreate",
        "CommunityGameDetailCreate",
        "CommunityGameDetailUpdate",
        "GameCreate",
        "GameUpdate",
        "GameCreditIssueCreate",
        "GameCreditReverseCreate",
        "PaymentEventUpdate",
        "PlatformNoticeCancel",
        "PlatformNoticeCreate",
        "SupportFlagResolve",
        "VenueImageCompleteUpload",
        "VenueImageUpdate",
        "VenueImageUploadCreate",
    }
    assert {model.model_config.get("extra") for model in guarded_models} == {"forbid"}


@pytest.mark.requirement(
    "WS03-04D-R6",
    "WS03-04D-R8",
    "WS03-04D-R9",
    "WS03-04D-R10",
)
def test_representative_retired_routes_return_410_without_business_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, Notification, Payment

    admin = _user("tombstone-admin", role="admin")
    _add_users(admin)
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()
    before_counts = {
        Payment: _count_model_rows(Payment),
        Notification: _count_model_rows(Notification),
        AdminAction: _count_model_rows(AdminAction),
    }

    for method, route in (
        ("post", "/admin/actions"),
        ("post", "/payments"),
        ("patch", "/payments/11111111-1111-4111-8111-111111111111"),
        ("post", "/notifications"),
        ("get", "/notifications"),
        ("patch", "/notifications/11111111-1111-4111-8111-111111111111"),
    ):
        if method in {"post", "patch"}:
            response = getattr(client, method)(
                route,
                json={},
                headers=_auth_headers("admin-token"),
            )
        else:
            response = getattr(client, method)(
                route,
                headers=_auth_headers("admin-token"),
            )
        assert response.status_code == 410, route

    assert _count_model_rows(Payment) == before_counts[Payment]
    assert _count_model_rows(Notification) == before_counts[Notification]
    assert _count_model_rows(AdminAction) == before_counts[AdminAction]


@pytest.mark.requirement("WS03-04D-R6", "WS03-04D-R8", "WS03-04D-R10")
def test_all_current_retired_d_routes_return_410_without_business_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import (
        AdminAction,
        Game,
        GameParticipant,
        GameStatusHistory,
        HostPublishFee,
        Notification,
        ParticipantStatusHistory,
        Payment,
        PaymentEvent,
        Refund,
        UserSettings,
        UserStats,
        Venue,
        VenueApprovalRequest,
        WaitlistEntry,
    )

    admin = _user("all-tombstone-admin", role="admin")
    _add_users(admin)
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()
    protected_models = (
        AdminAction,
        Game,
        GameParticipant,
        GameStatusHistory,
        HostPublishFee,
        Notification,
        ParticipantStatusHistory,
        Payment,
        PaymentEvent,
        Refund,
        UserSettings,
        UserStats,
        Venue,
        VenueApprovalRequest,
        WaitlistEntry,
    )
    before_counts = {model: _count_model_rows(model) for model in protected_models}
    tombstone_routes = sorted(_d_tombstone_route_keys())

    assert len(tombstone_routes) == 45

    for method, route_template in tombstone_routes:
        path = re.sub(r"\{[^{}]+\}", lambda _match: str(uuid.uuid4()), route_template)
        request = getattr(client, method.lower())
        kwargs = {"headers": _auth_headers("admin-token")}
        if method in {"POST", "PATCH"}:
            kwargs["json"] = {}

        response = request(path, **kwargs)

        assert response.status_code == 410, (method, route_template)

    assert {model: _count_model_rows(model) for model in protected_models} == (
        before_counts
    )
