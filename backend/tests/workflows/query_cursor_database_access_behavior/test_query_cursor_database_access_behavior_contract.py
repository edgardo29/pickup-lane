from __future__ import annotations

import inspect
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import event

from backend.observability.pagination_contracts import (
    PAGINATION_CONTRACTS,
    PAGINATION_HANDOFFS,
    pagination_contract_keys,
)
from backend.services.admin_money_cursor import (
    encode_money_cursor,
    parse_money_cursor,
)
from backend.services.query_pagination import (
    MAX_COLLECTION_LIMIT,
    bounded_collection_limit,
    bounded_collection_offset,
)
from backend.settings import build_settings, reset_settings_cache

_REPO_ROOT = Path(__file__).resolve().parents[4]
_TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
_ALLOWED_ORIGIN = "https://app.example.invalid"
_NEWLY_BOUNDED_OFFSET_PATHS = frozenset(
    {
        "/admin/game-images",
        "/admin/official-games/{game_id}/bookings",
        "/admin/official-games/{game_id}/participants",
        "/admin/official-games/{game_id}/waitlist",
        "/admin/venues/{venue_id}/images",
        "/booking-policy-acceptances",
        "/booking-status-history",
        "/bookings",
        "/bookings/me",
        "/community-game-details",
        "/game-chats",
        "/game-credits",
        "/game-images",
        "/game-participants",
        "/game-participants/me",
        "/game-status-history",
        "/games",
        "/games/participant-counts",
        "/games/{game_id}/participants",
        "/host-publish-fees",
        "/host-publish-fees/me",
        "/need-a-sub/my-requests",
        "/need-a-sub/posts",
        "/need-a-sub/posts/mine",
        "/need-a-sub/posts/{sub_post_id}/positions",
        "/need-a-sub/posts/{sub_post_id}/requests",
        "/need-a-sub/posts/{sub_post_id}/status-history",
        "/need-a-sub/requests/{request_id}/status-history",
        "/notifications/me",
        "/participant-status-history",
        "/payment-events",
        "/payments",
        "/policy-acceptances",
        "/policy-documents",
        "/refunds",
        "/user-payment-methods",
        "/user-stats",
        "/users",
        "/venue-approval-requests",
        "/venue-images",
        "/venues",
        "/waitlist-entries",
        "/waitlist-entries/me",
    }
)


def _settings_env() -> dict[str, str]:
    return {
        "APP_ENV": "test",
        "DATABASE_URL": os.environ.get("DATABASE_URL", _TEST_DATABASE_URL),
        "INBOX_TOKEN_SECRET": "synthetic-independent-query-cursor-token",
        "ALLOWED_HOSTS": "testserver,api.example.invalid",
        "CORS_ALLOWED_ORIGINS": _ALLOWED_ORIGIN,
        "ENABLE_API_DOCS": "true",
        "ENABLE_DB_HEALTH": "false",
        "ENABLE_STRIPE_PAYMENTS": "false",
    }


def _create_app(monkeypatch: pytest.MonkeyPatch):
    for name, value in _settings_env().items():
        monkeypatch.setenv(name, value)
    reset_settings_cache()

    try:
        import backend.main as main_module

        settings = build_settings(
            _settings_env(),
            load_dotenv_file=False,
            validate_full=True,
        )
        return main_module.create_app(settings)
    finally:
        database_module = sys.modules.get("backend.database")
        if database_module is not None:
            dispose = getattr(database_module, "dispose_database_engine", None)
            if dispose is not None:
                dispose()
        sys.modules.pop("backend.main", None)
        sys.modules.pop("backend.database", None)
        reset_settings_cache()


def _api_route_by_key(app) -> dict[tuple[str, str], APIRoute]:
    routes: dict[tuple[str, str], APIRoute] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or ():
            if method.upper() not in {"HEAD", "OPTIONS"}:
                routes[(method.upper(), route.path)] = route
    return routes


def _field_bound(query_param, bound_name: str) -> int | None:
    for metadata in query_param.field_info.metadata:
        if hasattr(metadata, bound_name):
            return getattr(metadata, bound_name)
    return None


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _install_auth_identities(
    monkeypatch: pytest.MonkeyPatch,
    identities: dict[str, tuple[str, str]],
) -> None:
    from backend.services import auth_service

    def verify_token(id_token: str) -> dict[str, object]:
        if id_token not in identities:
            raise ValueError("synthetic invalid token")
        auth_user_id, email = identities[id_token]
        return {
            "uid": auth_user_id,
            "email": email,
            "email_verified": True,
            "auth_time": int(datetime.now(timezone.utc).timestamp()),
        }

    monkeypatch.setattr(auth_service, "verify_firebase_token", verify_token)


def _user(index: int):
    from backend.models import User

    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"firebase-ws04-01b-{index}-{unique}",
        role="player",
        email=f"ws04-01b-{index}-{unique}@example.invalid",
        email_verified_at=datetime.now(timezone.utc),
        first_name=f"WS04B{index}",
        last_name="User",
        account_status="active",
        hosting_status="eligible",
        stripe_customer_id=f"cus_ws04_01b_{index}_{unique.hex[:8]}",
    )


def _payment_method(user_id: uuid.UUID, index: int):
    from backend.models import UserPaymentMethod

    unique = uuid.uuid4()
    return UserPaymentMethod(
        id=uuid.uuid4(),
        user_id=user_id,
        stripe_customer_id=f"cus_ws04_01b_{index}_{unique.hex[:8]}",
        stripe_payment_method_id=f"pm_ws04_01b_{index}_{unique.hex[:8]}",
        card_fingerprint=f"fp_ws04_01b_{index}_{unique.hex[:8]}",
        card_brand="visa",
        card_last4=f"{index:04d}"[-4:],
        exp_month=12,
        exp_year=2036,
        method_status="active",
        is_default=False,
        created_at=datetime(2026, 8, 22, 12, index, tzinfo=timezone.utc),
    )


def _venue(*, creator_id: uuid.UUID):
    from backend.models import Venue

    return Venue(
        id=uuid.uuid4(),
        name=f"WS04B Venue {uuid.uuid4()}",
        address_line_1="100 Test Street",
        city="Chicago",
        state="IL",
        postal_code="60601",
        country_code="US",
        venue_status="approved",
        created_by_user_id=creator_id,
        approved_by_user_id=creator_id,
        approved_at=datetime(2026, 8, 22, 12, tzinfo=timezone.utc),
        is_active=True,
    )


def _game(*, creator_id: uuid.UUID, venue_id: uuid.UUID):
    from backend.models import Game

    starts_at = datetime(2026, 9, 1, 18, tzinfo=timezone.utc)
    return Game(
        id=uuid.uuid4(),
        game_type="official",
        payment_collection_type="in_app",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title=f"WS04B Game {uuid.uuid4()}",
        venue_id=venue_id,
        venue_name_snapshot="WS04B Venue",
        address_snapshot="100 Test Street",
        city_snapshot="Chicago",
        state_snapshot="IL",
        created_by_user_id=creator_id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        starts_on_local=starts_at.date(),
        timezone="America/Chicago",
        sport_type="soccer",
        format_label="7v7",
        game_player_group="coed",
        skill_level="any",
        environment_type="outdoor",
        total_spots=14,
        price_per_player_cents=1200,
        currency="USD",
        minimum_age=None,
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=0,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="official_standard",
        published_at=datetime(2026, 8, 22, 12, tzinfo=timezone.utc),
    )


def _booking(*, game_id: uuid.UUID, buyer_user_id: uuid.UUID):
    from backend.models import Booking

    now = datetime(2026, 8, 22, 12, tzinfo=timezone.utc)
    return Booking(
        id=uuid.uuid4(),
        game_id=game_id,
        buyer_user_id=buyer_user_id,
        booking_status="confirmed",
        payment_status="paid",
        participant_count=1,
        subtotal_cents=1200,
        platform_fee_cents=0,
        discount_cents=0,
        total_cents=1200,
        currency="USD",
        price_per_player_snapshot_cents=1200,
        platform_fee_snapshot_cents=0,
        booked_at=now,
        created_at=now,
        updated_at=now,
    )


def _sub_post(*, owner_id: uuid.UUID):
    from backend.models import SubPost

    city = f"WS04B City {uuid.uuid4().hex[:8]}"
    starts_at = datetime(2026, 9, 2, 18, tzinfo=timezone.utc)
    return SubPost(
        id=uuid.uuid4(),
        owner_user_id=owner_id,
        post_status="active",
        public_visibility_status="visible",
        sport_type="soccer",
        format_label="7v7",
        environment_type="outdoor",
        skill_level="any",
        game_player_group="coed",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        starts_on_local=starts_at.date(),
        timezone="America/Chicago",
        location_name="WS04B Field",
        address_line_1="200 Test Street",
        city=city,
        state="IL",
        postal_code="60601",
        country_code="US",
        subs_needed=3,
        price_due_at_venue_cents=0,
        currency="USD",
        expires_at=starts_at - timedelta(hours=1),
        created_at=datetime(2026, 8, 22, 12, tzinfo=timezone.utc),
        updated_at=datetime(2026, 8, 22, 12, tzinfo=timezone.utc),
    )


def _sub_post_position(*, sub_post_id: uuid.UUID):
    from backend.models import SubPostPosition

    return SubPostPosition(
        id=uuid.uuid4(),
        sub_post_id=sub_post_id,
        position_label="field_player",
        player_group="open",
        spots_needed=3,
        sort_order=1,
        created_at=datetime(2026, 8, 22, 12, tzinfo=timezone.utc),
        updated_at=datetime(2026, 8, 22, 12, tzinfo=timezone.utc),
    )


def _sub_post_request(
    *,
    sub_post_id: uuid.UUID,
    position_id: uuid.UUID,
    requester_id: uuid.UUID,
    index: int,
    request_status: str = "sub_waitlist",
):
    from backend.models import SubPostRequest

    created_at = datetime(2026, 8, 22, 12, index, tzinfo=timezone.utc)
    return SubPostRequest(
        id=uuid.uuid4(),
        sub_post_id=sub_post_id,
        sub_post_position_id=position_id,
        requester_user_id=requester_id,
        request_status=request_status,
        confirmed_at=created_at if request_status == "confirmed" else None,
        sub_waitlisted_at=created_at if request_status == "sub_waitlist" else None,
        created_at=created_at,
        updated_at=created_at,
    )


def _notification(
    *,
    user_id: uuid.UUID,
    index: int,
    notification_type: str,
    notification_domain: str,
    source_type: str,
    action_key: str,
    related_game_id: uuid.UUID | None = None,
    related_sub_post_id: uuid.UUID | None = None,
    related_sub_post_chat_id: uuid.UUID | None = None,
):
    from backend.models import Notification

    event_at = datetime(2026, 8, 22, 12, index, tzinfo=timezone.utc)
    return Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        notification_type=notification_type,
        notification_category="game_activity",
        notification_domain=notification_domain,
        source_type=source_type,
        title=f"WS04B notification {index}",
        subject_label=f"WS04B subject {index}",
        summary=f"WS04B summary {index}",
        body=f"WS04B body {index}",
        action_key=action_key,
        event_at=event_at,
        related_game_id=related_game_id,
        related_sub_post_id=related_sub_post_id,
        related_sub_post_chat_id=related_sub_post_chat_id,
        is_read=False,
        read_at=None,
        created_at=event_at,
        updated_at=event_at,
    )


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS04-01B-R1")
def test_all_current_collection_routes_have_explicit_contracts() -> None:
    assert len(PAGINATION_CONTRACTS) == 77
    assert len(PAGINATION_HANDOFFS) == 0
    assert len(pagination_contract_keys()) == 77
    assert {contract.key for contract in PAGINATION_HANDOFFS} == set()


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS04-01B-R1")
@pytest.mark.requirement("WS04-01B-R2")
def test_newly_bounded_offset_routes_expose_limit_and_offset_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)
    route_by_key = _api_route_by_key(app)
    contract_by_path = {contract.path: contract for contract in PAGINATION_CONTRACTS}

    assert len(_NEWLY_BOUNDED_OFFSET_PATHS) == 43
    for path in _NEWLY_BOUNDED_OFFSET_PATHS:
        contract = contract_by_path[path]
        route = route_by_key[("GET", path)]
        query_params = {param.name: param for param in route.dependant.query_params}

        assert contract.style == "offset"
        assert contract.offset_param == "offset"
        assert contract.limit_default is not None
        assert contract.limit_max is not None
        assert "limit" in query_params
        assert "offset" in query_params
        assert query_params["offset"].default == 0
        assert _field_bound(query_params["offset"], "ge") == 0
        assert query_params["limit"].default == contract.limit_default
        assert _field_bound(query_params["limit"], "ge") == 1
        assert _field_bound(query_params["limit"], "le") == contract.limit_max
        assert contract.deterministic_order


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS04-01B-R1")
def test_collection_limit_helpers_clamp_before_queries() -> None:
    assert bounded_collection_offset(-10) == 0
    assert bounded_collection_offset(5) == 5
    assert bounded_collection_limit(0) == 1
    assert bounded_collection_limit(25) == 25
    assert bounded_collection_limit(999, max_limit=MAX_COLLECTION_LIMIT) == 100


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS04-01B-R3")
def test_admin_money_cursors_reject_foreign_query_context() -> None:
    sort_value = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    row_id = uuid.uuid4()
    context = {
        "kind": "admin_money_payments",
        "payment_status": "succeeded",
        "query": "alex",
    }
    cursor = encode_money_cursor(sort_value, row_id, context=context)

    assert parse_money_cursor(cursor, context=context) == (sort_value, row_id)

    with pytest.raises(HTTPException) as exc_info:
        parse_money_cursor(
            cursor,
            context={
                "kind": "admin_money_payments",
                "payment_status": "failed",
                "query": "alex",
            },
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "cursor does not match the current query."


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS04-01B-R3")
def test_admin_money_cursors_reject_malformed_values_stably() -> None:
    with pytest.raises(HTTPException) as exc_info:
        parse_money_cursor("not-a-valid-cursor", context={"kind": "x"})

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "cursor is not valid."


@pytest.mark.requirement("WS04-01B-R3")
def test_changed_admin_money_cursor_families_reject_invalid_and_mismatched_contexts() -> None:
    from backend.models import (
        GameCredit,
        MoneyIssue,
        Payment,
        Refund,
        RefundEvent,
    )
    from backend.services.admin_money_credit_service import list_admin_money_credits
    from backend.services.admin_money_issue_query_service import list_admin_money_issues_page
    from backend.services.admin_money_payment_service import list_admin_money_payments
    from backend.services.admin_money_refund_query_service import (
        list_admin_money_refunds,
        list_refund_events,
    )

    now = datetime(2026, 8, 22, 12, tzinfo=timezone.utc)
    with _session() as db:
        user = _user(10)
        db.add(user)
        db.commit()

        venue = _venue(creator_id=user.id)
        db.add(venue)
        db.commit()

        game = _game(creator_id=user.id, venue_id=venue.id)
        db.add(game)
        db.commit()

        booking = _booking(game_id=game.id, buyer_user_id=user.id)
        db.add(booking)
        db.commit()

        payments = [
            Payment(
                id=uuid.uuid4(),
                payer_user_id=user.id,
                booking_id=booking.id,
                game_id=game.id,
                payment_type="booking",
                provider="stripe",
                provider_payment_intent_id=f"pi_ws04_01b_{index}_{uuid.uuid4().hex[:8]}",
                provider_charge_id=f"ch_ws04_01b_{index}_{uuid.uuid4().hex[:8]}",
                idempotency_key=f"ws04-01b-payment-{index}-{uuid.uuid4()}",
                amount_cents=1200,
                currency="USD",
                payment_status=status,
                paid_at=now + timedelta(minutes=index) if status == "succeeded" else None,
                created_at=now + timedelta(minutes=index),
                updated_at=now + timedelta(minutes=index),
            )
            for index, status in enumerate(("succeeded", "succeeded", "failed"), start=1)
        ]
        db.add_all(payments)
        db.commit()

        refunds = [
            Refund(
                id=uuid.uuid4(),
                payment_id=payments[0].id,
                booking_id=booking.id,
                provider_refund_id=f"re_ws04_01b_{index}_{uuid.uuid4().hex[:8]}",
                origin_workflow="direct_admin_refund",
                provider="stripe",
                provider_status="processing",
                provider_status_observed_at=now + timedelta(minutes=index),
                provider_charge_id=payments[0].provider_charge_id,
                amount_cents=300,
                currency="USD",
                refund_reason="admin_refund",
                refund_status=status,
                requested_by_user_id=user.id,
                requested_at=now + timedelta(minutes=index),
                created_at=now + timedelta(minutes=index),
                updated_at=now + timedelta(minutes=index),
            )
            for index, status in enumerate(("pending", "pending", "failed"), start=1)
        ]
        db.add_all(refunds)
        db.commit()

        refund_events = [
            RefundEvent(
                id=uuid.uuid4(),
                refund_id=refunds[0].id,
                event_type=event_type,
                event_source="system",
                provider="stripe",
                provider_event_id=f"evt_ws04_01b_{index}_{uuid.uuid4().hex[:8]}",
                provider_refund_id=refunds[0].provider_refund_id,
                provider_charge_id=refunds[0].provider_charge_id,
                provider_status="processing",
                idempotency_key=f"ws04-01b-refund-event-{index}-{uuid.uuid4()}",
                occurred_at=now + timedelta(minutes=index),
                created_at=now + timedelta(minutes=index),
            )
            for index, event_type in enumerate(
                (
                    "provider_result_recorded",
                    "provider_result_recorded",
                    "reconciliation_checked",
                ),
                start=1,
            )
        ]
        credits = [
            GameCredit(
                id=uuid.uuid4(),
                user_id=user.id,
                amount_cents=300,
                available_cents=300 if status == "active" else 0,
                currency="USD",
                credit_status=status,
                credit_reason="admin_credit",
                source_game_id=game.id,
                source_booking_id=booking.id,
                source_payment_id=payments[0].id,
                issued_by_user_id=user.id,
                idempotency_key=f"ws04-01b-credit-{index}-{uuid.uuid4()}",
                created_at=now + timedelta(minutes=index),
                updated_at=now + timedelta(minutes=index),
            )
            for index, status in enumerate(("active", "active", "used"), start=1)
        ]
        issues = [
            MoneyIssue(
                id=uuid.uuid4(),
                operation_key=f"ws04-01b-refund-failed-{index}-{uuid.uuid4()}",
                status="open",
                issue_type="refund_failed",
                origin_workflow="direct_admin_refund",
                value_kind="cash_refund",
                amount_cents=300,
                currency="USD",
                target_user_id=user.id,
                target_game_id=game.id,
                target_booking_id=booking.id,
                target_payment_id=payments[0].id,
                target_refund_id=refunds[0].id,
                latest_reason_code="provider_failed",
                latest_summary="Synthetic refund failure.",
                recommended_action_code="verify_provider_refund",
                occurrence_count=1,
                reopen_count=0,
                first_detected_at=now + timedelta(minutes=index),
                last_detected_at=now + timedelta(minutes=index),
                last_activity_at=now + timedelta(minutes=index),
                created_at=now + timedelta(minutes=index),
                updated_at=now + timedelta(minutes=index),
            )
            for index in range(1, 3)
        ]
        db.add_all(refund_events + credits + issues)
        db.commit()

        family_calls = (
            (
                "payments",
                lambda cursor=None: list_admin_money_payments(
                    db,
                    payment_status="succeeded",
                    limit=1,
                    cursor=cursor,
                ),
                lambda cursor: list_admin_money_payments(
                    db,
                    payment_status="failed",
                    limit=1,
                    cursor=cursor,
                ),
            ),
            (
                "refunds",
                lambda cursor=None: list_admin_money_refunds(
                    db,
                    refund_status="pending",
                    limit=1,
                    cursor=cursor,
                ),
                lambda cursor: list_admin_money_refunds(
                    db,
                    refund_status="failed",
                    limit=1,
                    cursor=cursor,
                ),
            ),
            (
                "refund events",
                lambda cursor=None: list_refund_events(
                    db,
                    refunds[0].id,
                    event_type="provider_result_recorded",
                    limit=1,
                    cursor=cursor,
                ),
                lambda cursor: list_refund_events(
                    db,
                    refunds[0].id,
                    event_type="reconciliation_checked",
                    limit=1,
                    cursor=cursor,
                ),
            ),
            (
                "credits",
                lambda cursor=None: list_admin_money_credits(
                    db,
                    credit_status="active",
                    limit=1,
                    cursor=cursor,
                ),
                lambda cursor: list_admin_money_credits(
                    db,
                    credit_status="used",
                    limit=1,
                    cursor=cursor,
                ),
            ),
            (
                "issues",
                lambda cursor=None: list_admin_money_issues_page(
                    db,
                    issue_status="open",
                    limit=1,
                    cursor=cursor,
                ),
                lambda cursor: list_admin_money_issues_page(
                    db,
                    issue_status="open",
                    issue_type="refund_failed",
                    limit=1,
                    cursor=cursor,
                ),
            ),
        )

        for family_name, matching_page, mismatched_page in family_calls:
            first_page = matching_page()
            assert first_page.has_more is True, family_name
            assert first_page.next_cursor, family_name
            assert len(first_page.items) == 1, family_name

            second_page = matching_page(first_page.next_cursor)
            assert len(second_page.items) == 1, family_name
            assert second_page.items[0].id != first_page.items[0].id, family_name

            with pytest.raises(HTTPException) as mismatch:
                mismatched_page(first_page.next_cursor)
            assert mismatch.value.status_code == 400, family_name
            assert mismatch.value.detail == "cursor does not match the current query."

            with pytest.raises(HTTPException) as invalid:
                matching_page("not-a-valid-cursor")
            assert invalid.value.status_code == 400, family_name
            assert invalid.value.detail == "cursor is not valid."


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS04-01B-R4")
@pytest.mark.requirement("WS04-01B-R6")
def test_scoped_service_lists_keep_binding_and_limits_in_query_source() -> None:
    from backend.services import (
        booking_service,
        need_a_sub_request_service,
        payment_method_service,
        venue_image_service,
    )

    source_checks = {
        payment_method_service.list_current_user_payment_methods: (
            "UserPaymentMethod.user_id == current_user.id",
            ".offset(",
            ".limit(",
        ),
        booking_service.list_current_user_bookings: (
            "Booking.buyer_user_id == current_user.id",
            ".offset(",
            ".limit(",
        ),
        venue_image_service.list_venue_images_statement: (
            "VenueImage.venue_id == venue_id",
            ".offset(",
            ".limit(",
        ),
        need_a_sub_request_service.list_owner_sub_post_requests: (
            "require_owner(sub_post, owner)",
            "serialize_sub_post_request_page",
            ".offset(",
            ".limit(",
        ),
        need_a_sub_request_service.list_requester_sub_post_requests: (
            "SubPostRequest.requester_user_id == requester.id",
            "serialize_sub_post_request_page",
            ".offset(",
            ".limit(",
        ),
    }

    for func, fragments in source_checks.items():
        source = inspect.getsource(func)
        for fragment in fragments:
            assert fragment in source


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS04-01B-R6")
def test_need_a_sub_request_list_serialization_batches_related_rows() -> None:
    from backend.services import need_a_sub_request_service

    serializer_source = inspect.getsource(
        need_a_sub_request_service.serialize_sub_post_request_page
    )

    assert "load_requester_users" in serializer_source
    assert "load_waitlist_ahead_counts" in serializer_source
    assert "for sub_request in requests" in serializer_source


@pytest.mark.requirement("WS04-01B-R6")
def test_need_a_sub_request_list_response_batches_related_database_reads() -> None:
    from backend.database import engine
    from backend.services.need_a_sub_request_service import list_owner_sub_post_requests

    statements: list[str] = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        del conn, cursor, parameters, context, executemany
        normalized = " ".join(statement.lower().split())
        if normalized.startswith("select"):
            statements.append(normalized)

    now = datetime(2026, 8, 22, 12, tzinfo=timezone.utc)
    with _session() as db:
        owner = _user(20)
        requesters = [_user(index) for index in range(21, 29)]
        db.add_all([owner, *requesters])
        db.commit()

        sub_post = _sub_post(owner_id=owner.id)
        db.add(sub_post)
        db.commit()

        position = _sub_post_position(sub_post_id=sub_post.id)
        db.add(position)
        db.commit()

        requests = [
            _sub_post_request(
                sub_post_id=sub_post.id,
                position_id=position.id,
                requester_id=requester.id,
                index=index,
            )
            for index, requester in enumerate(requesters, start=1)
        ]
        db.add_all(requests)
        db.commit()

        event.listen(engine, "before_cursor_execute", before_cursor_execute)
        try:
            response = list_owner_sub_post_requests(
                db,
                sub_post.id,
                owner,
                limit=2,
                offset=5,
            )
        finally:
            event.remove(engine, "before_cursor_execute", before_cursor_execute)

    assert len(response) == 2
    assert [item["id"] for item in response] == [request.id for request in requests[5:7]]
    assert [item["requester_user_id"] for item in response] == [
        requester.id for requester in requesters[5:7]
    ]
    assert [item["requester_display_name"] for item in response] == [
        f"{requester.first_name} {requester.last_name}"
        for requester in requesters[5:7]
    ]
    assert [item["waitlist_ahead_count"] for item in response] == [5, 6]

    requester_batch_queries = [
        statement
        for statement in statements
        if "from users" in statement and "users.id in" in statement
    ]
    waitlist_batch_queries = [
        statement
        for statement in statements
        if "from sub_post_requests as sub_post_requests_1" in statement
        and "left outer join sub_post_requests as sub_post_requests_2" in statement
        and "sub_post_requests_1.id in" in statement
        and "group by sub_post_requests_1.id" in statement
    ]

    assert len(requester_batch_queries) == 1
    assert len(waitlist_batch_queries) == 1
    assert "order by" not in waitlist_batch_queries[0]


@pytest.mark.requirement("WS04-01B-R6")
def test_need_a_sub_post_lists_batch_positions_and_request_counts() -> None:
    from backend.database import engine
    from backend.services.need_a_sub_post_service import (
        list_owner_sub_posts,
        list_visible_sub_posts,
    )

    def capture_selects(call):
        statements: list[str] = []

        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            del conn, cursor, parameters, context, executemany
            normalized = " ".join(statement.lower().split())
            if normalized.startswith("select"):
                statements.append(normalized)

        event.listen(engine, "before_cursor_execute", before_cursor_execute)
        try:
            response = call()
        finally:
            event.remove(engine, "before_cursor_execute", before_cursor_execute)

        return response, statements

    with _session() as db:
        owner = _user(30)
        requesters = [_user(index) for index in range(31, 40)]
        db.add_all([owner, *requesters])
        db.commit()

        posts = []
        city = None
        requester_index = 0
        for post_index in range(3):
            post = _sub_post(owner_id=owner.id)
            starts_at = datetime(2026, 9, 2 + post_index, 18, tzinfo=timezone.utc)
            city = city or post.city
            post.city = city
            post.starts_at = starts_at
            post.ends_at = starts_at + timedelta(hours=1)
            post.starts_on_local = starts_at.date()
            post.expires_at = starts_at - timedelta(hours=1)
            db.add(post)
            db.flush()

            position = _sub_post_position(sub_post_id=post.id)
            db.add(position)
            db.flush()

            for status_value in ("pending", "confirmed", "sub_waitlist"):
                db.add(
                    _sub_post_request(
                        sub_post_id=post.id,
                        position_id=position.id,
                        requester_id=requesters[requester_index].id,
                        index=(post_index * 3) + requester_index + 1,
                        request_status=status_value,
                    )
                )
                requester_index += 1

            posts.append(post)

        db.commit()

        public_response, public_statements = capture_selects(
            lambda: list_visible_sub_posts(db, city=city, limit=2, offset=0)
        )
        owner_response, owner_statements = capture_selects(
            lambda: list_owner_sub_posts(db, owner, limit=2, offset=0)
        )

    def assert_post_list_batch(response, statements):
        assert len(response) == 2
        for item in response:
            assert item["pending_count"] == 1
            assert item["confirmed_count"] == 1
            assert item["sub_waitlist_count"] == 1
            assert len(item["positions"]) == 1
            position = item["positions"][0]
            assert position["pending_count"] == 1
            assert position["confirmed_count"] == 1
            assert position["sub_waitlist_count"] == 1

        post_count_queries = [
            statement
            for statement in statements
            if "from sub_post_requests" in statement
            and "sub_post_requests.sub_post_id in" in statement
            and "group by sub_post_requests.sub_post_id" in statement
        ]
        position_queries = [
            statement
            for statement in statements
            if "from sub_post_positions" in statement
            and "sub_post_positions.sub_post_id in" in statement
            and "order by sub_post_positions.sub_post_id" in statement
        ]
        position_count_queries = [
            statement
            for statement in statements
            if "from sub_post_requests" in statement
            and "sub_post_requests.sub_post_position_id in" in statement
            and "group by sub_post_requests.sub_post_position_id" in statement
        ]

        assert len(post_count_queries) == 1
        assert len(position_queries) == 1
        assert len(position_count_queries) == 1

    assert_post_list_batch(public_response, public_statements)
    assert_post_list_batch(owner_response, owner_statements)


@pytest.mark.requirement("WS04-01B-R6")
def test_notification_list_batches_related_action_records() -> None:
    from backend.database import engine
    from backend.services.notification_service import list_user_notifications_workflow

    statements: list[str] = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        del conn, cursor, parameters, context, executemany
        normalized = " ".join(statement.lower().split())
        if normalized.startswith("select"):
            statements.append(normalized)

    with _session() as db:
        owner = _user(50)
        requester = _user(51)
        db.add_all([owner, requester])
        db.commit()

        venue = _venue(creator_id=owner.id)
        db.add(venue)
        db.commit()

        game = _game(creator_id=owner.id, venue_id=venue.id)
        sub_post = _sub_post(owner_id=owner.id)
        db.add_all([game, sub_post])
        db.flush()

        position = _sub_post_position(sub_post_id=sub_post.id)
        db.add(position)
        db.flush()
        db.add(
            _sub_post_request(
                sub_post_id=sub_post.id,
                position_id=position.id,
                requester_id=requester.id,
                index=1,
                request_status="confirmed",
            )
        )
        db.add_all(
            [
                _notification(
                    user_id=requester.id,
                    index=1,
                    notification_type="game_updated",
                    notification_domain="game",
                    source_type="official_game",
                    action_key="view_game",
                    related_game_id=game.id,
                ),
                _notification(
                    user_id=requester.id,
                    index=2,
                    notification_type="game_reminder",
                    notification_domain="game",
                    source_type="official_game",
                    action_key="view_game",
                    related_game_id=game.id,
                ),
                _notification(
                    user_id=requester.id,
                    index=3,
                    notification_type="sub_chat_message",
                    notification_domain="need_a_sub",
                    source_type="need_a_sub",
                    action_key="view_sub_post",
                    related_sub_post_id=sub_post.id,
                    related_sub_post_chat_id=uuid.uuid4(),
                ),
                _notification(
                    user_id=requester.id,
                    index=4,
                    notification_type="sub_chat_message",
                    notification_domain="need_a_sub",
                    source_type="need_a_sub",
                    action_key="view_sub_post",
                    related_sub_post_id=sub_post.id,
                    related_sub_post_chat_id=uuid.uuid4(),
                ),
            ]
        )
        db.commit()

        event.listen(engine, "before_cursor_execute", before_cursor_execute)
        try:
            response = list_user_notifications_workflow(
                db,
                user_id=requester.id,
                limit=4,
                offset=0,
            )
        finally:
            event.remove(engine, "before_cursor_execute", before_cursor_execute)

    assert len(response) == 4
    assert all(item["action"] is not None for item in response)

    game_batch_queries = [
        statement
        for statement in statements
        if "from games" in statement and "games.id in" in statement
    ]
    sub_post_batch_queries = [
        statement
        for statement in statements
        if "from sub_posts" in statement and "sub_posts.id in" in statement
    ]
    sub_chat_access_queries = [
        statement
        for statement in statements
        if "from sub_post_requests" in statement
        and "sub_post_requests.request_status" in statement
        and "sub_post_requests.requester_user_id" in statement
    ]

    assert len(game_batch_queries) == 1
    assert len(sub_post_batch_queries) == 1
    assert len(sub_chat_access_queries) == 1


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS04-01B-R5")
def test_reviewed_query_shapes_have_current_model_index_support() -> None:
    from backend.models import (
        Booking,
        Game,
        GameCredit,
        GameImage,
        MoneyIssue,
        Notification,
        Payment,
        PaymentEvent,
        PolicyAcceptance,
        Refund,
        RefundEvent,
        SubPost,
        SubPostRequest,
        User,
        UserPaymentMethod,
        VenueImage,
        WaitlistEntry,
    )

    required_indexes = {
        Booking: {
            "ix_bookings_buyer_user_id_booking_status",
            "ix_bookings_game_status_expires_payment",
        },
        Game: {
            "ix_games_browse_cards_local_starts_created_id",
            "ix_games_admin_official_status_local_starts_created_id",
            "ix_games_admin_community_status_local_starts_created_id",
        },
        GameCredit: {
            "ix_game_credits_user_created",
            "ix_game_credits_credit_status_created",
            "ix_game_credits_source_game_id",
            "ix_game_credits_source_booking_id",
            "ix_game_credits_source_payment_id",
        },
        MoneyIssue: {
            "ix_money_issues_open_queue",
            "ix_money_issues_resolved",
            "ix_money_issues_activity",
            "ix_money_issues_issue_type_status",
            "ix_money_issues_target_user_id",
            "ix_money_issues_target_payment_id",
            "ix_money_issues_target_refund_id",
        },
        Payment: {
            "ix_payments_payer_created",
            "ix_payments_payment_status_created",
            "ix_payments_payment_type_created",
            "ix_payments_booking_id",
            "ix_payments_game_id",
        },
        PaymentEvent: {
            "ix_payment_events_payment_id_created_at",
            "ix_payment_events_processing_status_created_at",
        },
        PolicyAcceptance: {
            "ix_policy_acceptances_user_id",
            "ix_policy_acceptances_policy_document_id",
        },
        Refund: {
            "ix_refunds_payment_id",
            "ix_refunds_refund_status_created",
            "ix_refunds_origin_workflow_created",
            "ix_refunds_last_refund_event_at",
        },
        RefundEvent: {"ix_refund_events_refund_id_occurred_id"},
        SubPost: {
            "ix_sub_posts_cards_active_local_starts_created_id",
            "ix_sub_posts_owner_cards_active_local_starts_created_id",
            "ix_sub_posts_admin_status_local_starts_created_id",
        },
        SubPostRequest: {
            "ix_sub_post_requests_sub_post_id",
            "ix_sub_post_requests_requester_status",
            "ix_sub_post_requests_position_status",
        },
        User: {
            "ix_users_admin_list_created_id",
            "ix_users_admin_email_lower",
        },
        UserPaymentMethod: {"ix_user_payment_methods_user_status"},
        GameImage: {"ix_game_images_game_id_image_status_sort_order"},
        Notification: {
            "ix_notifications_user_id_is_read_event_at",
            "ix_notifications_user_event_created_id",
        },
        VenueImage: {
            "ix_venue_images_venue_id_image_status_sort_order",
        },
        WaitlistEntry: {
            "ix_waitlist_entries_game_id_waitlist_status_position",
            "ix_waitlist_entries_user_id_waitlist_status",
        },
    }

    for model, expected_names in required_indexes.items():
        model_index_names = {index.name for index in model.__table__.indexes}
        assert expected_names <= model_index_names, model.__tablename__


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS04-01B-R5")
@pytest.mark.requirement("WS04-01B-R7")
def test_ws04_01b_evidence_does_not_claim_production_query_plan_proof() -> None:
    testing_record = (
        _REPO_ROOT
        / "backend/tests/workflows/query_cursor_database_access_behavior/TESTING_RECORD.md"
    )
    if not testing_record.exists():
        pytest.skip("WS04-01B testing record is created with the pass evidence.")

    text = testing_record.read_text()
    assert "does not prove production query plans" in text
    assert "provider latency" in text
    assert "production row counts" in text


@pytest.mark.requirement("WS04-01B-R1")
@pytest.mark.requirement("WS04-01B-R2")
@pytest.mark.requirement("WS04-01B-R4")
def test_user_payment_method_route_bounds_and_scopes_page(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        user = _user(1)
        other_user = _user(2)
        own_first = _payment_method(user.id, 1)
        own_second = _payment_method(user.id, 2)
        other_card = _payment_method(other_user.id, 3)
        db.add_all([user, other_user, own_first, own_second, other_card])
        db.commit()
        auth_user_id = user.auth_user_id
        email = user.email
        expected_card_id = str(own_second.id)
        other_card_id = str(other_card.id)

    _install_auth_identities(
        monkeypatch,
        {"card-token": (auth_user_id, email)},
    )

    response = client.get(
        "/user-payment-methods",
        params={"limit": 1, "offset": 1},
        headers=_auth_headers("card-token"),
    )

    assert response.status_code == 200
    items = response.json()
    assert [item["id"] for item in items] == [expected_card_id]
    assert other_card_id not in {item["id"] for item in items}
    assert (
        client.get(
            "/user-payment-methods",
            params={"limit": 101},
            headers=_auth_headers("card-token"),
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/user-payment-methods",
            params={"offset": -1},
            headers=_auth_headers("card-token"),
        ).status_code
        == 422
    )


@pytest.mark.requirement("WS04-01B-R1")
@pytest.mark.requirement("WS04-01B-R2")
def test_mixed_self_admin_routes_expose_shared_effective_limit(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        user = _user(70)
        db.add(user)
        db.commit()
        auth_user_id = user.auth_user_id
        email = user.email

    _install_auth_identities(
        monkeypatch,
        {"mixed-limit-token": (auth_user_id, email)},
    )

    for path in ("/bookings", "/payments", "/refunds", "/game-credits"):
        max_response = client.get(
            path,
            params={"limit": MAX_COLLECTION_LIMIT, "offset": 0},
            headers=_auth_headers("mixed-limit-token"),
        )
        too_large_response = client.get(
            path,
            params={"limit": MAX_COLLECTION_LIMIT + 1, "offset": 0},
            headers=_auth_headers("mixed-limit-token"),
        )

        assert max_response.status_code == 200, path
        assert too_large_response.status_code == 422, path
