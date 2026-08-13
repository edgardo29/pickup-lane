from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.schemas.platform_notice_schema import PlatformNoticeCancel, PlatformNoticeCreate

pytestmark = pytest.mark.suite_type("ordinary")


def _count(db: Session, model: type[object]) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _user(index: int, *, role: str = "player", account_status: str = "active") -> User:
    from backend.models import User

    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04b1-user-{index}-{uuid.uuid4()}",
        role=role,
        email=f"ws02-04b1-user-{index}-{uuid.uuid4()}@example.invalid",
        first_name="WS02",
        last_name=f"B1-{index}",
        account_status=account_status,
        hosting_status="eligible",
    )


def _create_notice_payload(
    *,
    audience_type: str = "selected_users",
    selected_user_ids: list[uuid.UUID] | None = None,
    idempotency_key: str | None = None,
    title: str = "Boundary notice",
    message: str = "Source-owned boundary notice.",
) -> PlatformNoticeCreate:
    return PlatformNoticeCreate(
        idempotency_key=idempotency_key or f"idempotency-{uuid.uuid4()}",
        title=title,
        message=message,
        audience_type=audience_type,
        selected_user_ids=selected_user_ids or [],
    )


@contextmanager
def _client_overrides(
    client: TestClient,
    *,
    admin: User,
    db: Session,
) -> Iterator[None]:
    from backend.database import get_db
    from backend.services.auth_service import require_active_admin, require_recent_active_admin

    def override_db() -> Iterator[Session]:
        yield db

    client.app.dependency_overrides[get_db] = override_db
    client.app.dependency_overrides[require_active_admin] = lambda: admin
    client.app.dependency_overrides[require_recent_active_admin] = lambda: admin
    try:
        yield
    finally:
        client.app.dependency_overrides.clear()


@pytest.mark.requirement("WS02-04B1-R1")
def test_selected_notice_accepts_500_unique_users_and_dedupes_before_cap() -> None:
    from backend.models import AdminAction, Notification, PlatformNotice, PlatformNoticeRecipient
    from backend.services import platform_notice_service

    with _session() as db:
        admin = _user(0, role="admin")
        selected_users = [_user(index + 1) for index in range(platform_notice_service.MAX_SELECTED_PLATFORM_NOTICE_USERS)]
        db.add(admin)
        db.add_all(selected_users)
        db.commit()

        duplicated_ids = [user.id for user in selected_users] + [selected_users[0].id]
        result = platform_notice_service.create_platform_notice(
            db,
            creator_user=admin,
            payload=_create_notice_payload(selected_user_ids=duplicated_ids),
        )

        assert result.notice.audience_type == platform_notice_service.AUDIENCE_TYPE_SELECTED
        assert result.notice.selected_recipient_count == platform_notice_service.MAX_SELECTED_PLATFORM_NOTICE_USERS
        assert _count(db, PlatformNotice) == 1
        assert _count(db, PlatformNoticeRecipient) == platform_notice_service.MAX_SELECTED_PLATFORM_NOTICE_USERS
        assert _count(db, AdminAction) == 1
        assert _count(db, Notification) == 0


@pytest.mark.requirement("WS02-04B1-R1")
def test_selected_notice_rejects_501_unique_users_before_partial_state() -> None:
    from backend.models import AdminAction, Notification, PlatformNotice, PlatformNoticeRecipient
    from backend.services import platform_notice_service

    with _session() as db:
        admin = _user(0, role="admin")
        db.add(admin)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            platform_notice_service.create_platform_notice(
                db,
                creator_user=admin,
                payload=_create_notice_payload(
                    selected_user_ids=[
                        uuid.uuid4()
                        for _ in range(platform_notice_service.MAX_SELECTED_PLATFORM_NOTICE_USERS + 1)
                    ]
                ),
            )

        assert exc_info.value.status_code == 400
        assert _count(db, PlatformNotice) == 0
        assert _count(db, PlatformNoticeRecipient) == 0
        assert _count(db, AdminAction) == 0
        assert _count(db, Notification) == 0


@pytest.mark.requirement("WS02-04B1-R1")
@pytest.mark.parametrize(
    ("selected_user_status", "expected_code"),
    [
        (None, "selected_user_not_found"),
        ("suspended", "selected_user_ineligible"),
    ],
)
def test_missing_or_ineligible_selected_user_rejects_before_notice_persistence(
    selected_user_status: str | None,
    expected_code: str,
) -> None:
    from backend.models import AdminAction, Notification, PlatformNotice, PlatformNoticeRecipient
    from backend.services import platform_notice_service

    with _session() as db:
        admin = _user(0, role="admin")
        selected_user = (
            _user(9, account_status=selected_user_status)
            if selected_user_status is not None
            else None
        )
        db.add(admin)
        if selected_user is not None:
            db.add(selected_user)
        db.commit()

        selected_user_id = selected_user.id if selected_user is not None else uuid.uuid4()
        with pytest.raises(HTTPException) as exc_info:
            platform_notice_service.create_platform_notice(
                db,
                creator_user=admin,
                payload=_create_notice_payload(selected_user_ids=[selected_user_id]),
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == expected_code
        assert _count(db, PlatformNotice) == 0
        assert _count(db, PlatformNoticeRecipient) == 0
        assert _count(db, AdminAction) == 0
        assert _count(db, Notification) == 0


@pytest.mark.requirement("WS02-04B1-R1")
def test_global_notice_uses_sparse_global_state_without_recipient_or_notification_rows() -> None:
    from backend.models import Notification, PlatformNotice, PlatformNoticeRecipient
    from backend.services import platform_notice_service

    with _session() as db:
        admin = _user(0, role="admin")
        db.add(admin)
        db.commit()

        result = platform_notice_service.create_platform_notice(
            db,
            creator_user=admin,
            payload=_create_notice_payload(
                audience_type=platform_notice_service.AUDIENCE_TYPE_ALL_ELIGIBLE,
                selected_user_ids=[],
            ),
        )

        assert result.notice.audience_type == platform_notice_service.AUDIENCE_TYPE_ALL_ELIGIBLE
        assert result.notice.global_sequence is not None
        assert result.notice.selected_recipient_count == 0
        assert _count(db, PlatformNotice) == 1
        assert _count(db, PlatformNoticeRecipient) == 0
        assert _count(db, Notification) == 0


@pytest.mark.requirement("WS02-04B1-R2")
def test_platform_notice_field_and_search_boundaries_are_enforced() -> None:
    from backend.services import platform_notice_service

    assert platform_notice_service.normalize_single_line_text("T" * 150, field_name="title", max_length=150) == "T" * 150
    assert platform_notice_service.normalize_message("M" * 4000) == "M" * 4000
    assert platform_notice_service.normalize_cancellation_reason("C" * 1000) == "C" * 1000
    assert platform_notice_service.normalize_notice_search(
        "S" * platform_notice_service.MAX_NOTICE_HISTORY_SEARCH_LENGTH
    ) == "s" * platform_notice_service.MAX_NOTICE_HISTORY_SEARCH_LENGTH

    with pytest.raises(HTTPException) as title_exc:
        platform_notice_service.normalize_single_line_text("T" * 151, field_name="title", max_length=150)
    with pytest.raises(HTTPException) as message_exc:
        platform_notice_service.normalize_message("M" * 4001)
    with pytest.raises(HTTPException) as cancel_exc:
        platform_notice_service.normalize_cancellation_reason("C" * 1001)
    with pytest.raises(HTTPException) as search_length_exc:
        platform_notice_service.normalize_notice_search(
            "S" * (platform_notice_service.MAX_NOTICE_HISTORY_SEARCH_LENGTH + 1)
        )
    with pytest.raises(HTTPException) as search_meaning_exc:
        platform_notice_service.normalize_notice_search("?!a")

    assert title_exc.value.status_code == 400
    assert message_exc.value.status_code == 400
    assert cancel_exc.value.status_code == 400
    assert search_length_exc.value.status_code == 400
    assert search_meaning_exc.value.status_code == 400


@pytest.mark.requirement("WS02-04B1-R2")
def test_notice_history_and_recipient_page_limits_are_bounded() -> None:
    from backend.services import platform_notice_service

    with _session() as db:
        admin = _user(0, role="admin")
        users = [_user(index + 1) for index in range(2)]
        db.add(admin)
        db.add_all(users)
        db.commit()

        platform_notice_service.create_platform_notice(
            db,
            creator_user=admin,
            payload=_create_notice_payload(selected_user_ids=[user.id for user in users]),
        )
        history = platform_notice_service.list_platform_notices(db, limit=30)
        clamped_history = platform_notice_service.list_platform_notices(db, limit=31)

        assert history.limit == 30
        assert clamped_history.limit == 30


@pytest.mark.requirement("WS02-04B1-R2")
def test_recipient_route_bounds_cursor_and_preserves_ws02_04a_validation_behavior(
    client: TestClient,
) -> None:
    from backend.services import platform_notice_service

    with _session() as db:
        admin = _user(0, role="admin")
        users = [_user(index + 1) for index in range(2)]
        db.add(admin)
        db.add_all(users)
        db.commit()
        result = platform_notice_service.create_platform_notice(
            db,
            creator_user=admin,
            payload=_create_notice_payload(selected_user_ids=[user.id for user in users]),
        )

        with _client_overrides(client, admin=admin, db=db):
            default_response = client.get(f"/admin/platform-notices/{result.notice.id}/recipients")
            max_response = client.get(
                f"/admin/platform-notices/{result.notice.id}/recipients?limit={platform_notice_service.MAX_RECIPIENT_LIST_LIMIT}"
            )
            service_cursor_response = client.get(
                f"/admin/platform-notices/{result.notice.id}/recipients",
                params={"cursor": "x" * 2000},
            )
            route_cursor_response = client.get(
                f"/admin/platform-notices/{result.notice.id}/recipients",
                params={"cursor": "x" * 2001},
            )

        assert default_response.status_code == 200
        assert default_response.json()["limit"] == 50
        assert max_response.status_code == 200
        assert max_response.json()["limit"] == platform_notice_service.MAX_RECIPIENT_LIST_LIMIT
        assert service_cursor_response.status_code == 400
        assert "X-Request-ID" in service_cursor_response.headers
        assert route_cursor_response.status_code == 422
        assert route_cursor_response.json()["code"] == "API.VALIDATION_FAILED"
        assert "X-Request-ID" in route_cursor_response.headers


@pytest.mark.requirement("WS02-04B1-R2")
def test_cancellation_reason_accepts_boundary_and_rejects_over_bound() -> None:
    from backend.services import platform_notice_service

    with _session() as db:
        admin = _user(0, role="admin")
        db.add(admin)
        db.commit()
        result = platform_notice_service.create_platform_notice(
            db,
            creator_user=admin,
            payload=_create_notice_payload(
                audience_type=platform_notice_service.AUDIENCE_TYPE_ALL_ELIGIBLE,
                selected_user_ids=[],
            ),
        )

        cancelled = platform_notice_service.cancel_platform_notice(
            db,
            admin_user=admin,
            notice_id=result.notice.id,
            payload=PlatformNoticeCancel(cancellation_reason="C" * 1000),
        )

        assert cancelled.cancellation_reason == "C" * 1000
        with pytest.raises(HTTPException) as exc_info:
            platform_notice_service.normalize_cancellation_reason("C" * 1001)
        assert exc_info.value.status_code == 400
