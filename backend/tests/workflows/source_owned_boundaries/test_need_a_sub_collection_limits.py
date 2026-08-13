from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.schemas.sub_post_position_schema import SubPostPositionCreate
from backend.schemas.sub_post_schema import MAX_SUB_POST_POSITION_ROWS, MAX_SUB_POST_TOTAL_SUBS, SubPostCreate

pytestmark = pytest.mark.suite_type("ordinary")

_BASE_START = datetime(2035, 1, 15, 18, 0, tzinfo=timezone.utc)
_BASE_END = datetime(2035, 1, 15, 20, 0, tzinfo=timezone.utc)
_CONTROLLED_NOW = datetime(2035, 1, 2, 12, 0, tzinfo=timezone.utc)


def _user(index: int) -> User:
    from backend.models import User

    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04b1-sub-user-{index}-{uuid.uuid4()}",
        role="player",
        email=f"ws02-04b1-sub-user-{index}-{uuid.uuid4()}@example.invalid",
        first_name="Sub",
        last_name=f"User-{index}",
        account_status="active",
        hosting_status="eligible",
    )


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _position(
    position_label: str = "field_player",
    player_group: str = "open",
    spots_needed: int = 1,
    sort_order: int = 0,
) -> SubPostPositionCreate:
    return SubPostPositionCreate(
        position_label=position_label,
        player_group=player_group,
        spots_needed=spots_needed,
        sort_order=sort_order,
    )


def _payload(
    *,
    positions: list[SubPostPositionCreate],
    subs_needed: int,
    starts_at: datetime = _BASE_START,
    ends_at: datetime = _BASE_END,
) -> SubPostCreate:
    return SubPostCreate(
        format_label="5v5",
        environment_type="indoor",
        skill_level="any",
        game_player_group="coed",
        starts_at=starts_at,
        ends_at=ends_at,
        location_name="Boundary Field",
        address_line_1="1 Test Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        subs_needed=subs_needed,
        positions=positions,
    )


def _count(db: Session, model: type[object]) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _create_post_with_position(db: Session, owner: User) -> tuple[SubPost, SubPostPosition]:
    from backend.models import SubPost, SubPostPosition

    sub_post = SubPost(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        post_status="active",
        public_visibility_status="visible",
        sport_type="soccer",
        format_label="5v5",
        environment_type="indoor",
        skill_level="any",
        game_player_group="coed",
        starts_at=_BASE_START,
        ends_at=_BASE_END,
        starts_on_local=_BASE_START.date(),
        timezone="UTC",
        location_name="Boundary Field",
        address_line_1="1 Test Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        subs_needed=1,
        price_due_at_venue_cents=0,
        currency="USD",
        expires_at=_BASE_START,
    )
    position = SubPostPosition(
        id=uuid.uuid4(),
        sub_post_id=sub_post.id,
        position_label="field_player",
        player_group="open",
        spots_needed=1,
        sort_order=0,
    )
    db.add(sub_post)
    db.add(position)
    db.commit()
    return sub_post, position


@pytest.mark.requirement("WS02-04B1-R4")
def test_schema_accepts_six_position_rows_and_rejects_more_than_six_at_schema_boundary() -> None:
    six_schema_rows = [
        _position("field_player", "open", 1, 0),
        _position("field_player", "men", 1, 1),
        _position("field_player", "women", 1, 2),
        _position("goalkeeper", "open", 1, 3),
        _position("goalkeeper", "men", 1, 4),
        _position("goalkeeper", "women", 1, 5),
    ]

    accepted = _payload(positions=six_schema_rows, subs_needed=MAX_SUB_POST_POSITION_ROWS)

    assert len(accepted.positions) == MAX_SUB_POST_POSITION_ROWS
    with pytest.raises(ValidationError):
        _payload(
            positions=[*six_schema_rows, _position("field_player", "open", 1, 6)],
            subs_needed=MAX_SUB_POST_POSITION_ROWS + 1,
        )


@pytest.mark.requirement("WS02-04B1-R4")
def test_schema_rejects_more_than_eleven_total_substitutes() -> None:
    otherwise_valid_positions = [
        _position("field_player", "men", 3, 0),
        _position("field_player", "women", 3, 1),
        _position("goalkeeper", "men", 3, 2),
        _position("goalkeeper", "women", 3, 3),
    ]

    with pytest.raises(ValidationError) as exc_info:
        _payload(
            positions=otherwise_valid_positions,
            subs_needed=MAX_SUB_POST_TOTAL_SUBS + 1,
        )

    assert any(error["loc"] == ("subs_needed",) for error in exc_info.value.errors())


@pytest.mark.requirement("WS02-04B1-R4")
def test_service_accepts_eleven_total_substitutes_and_persists_when_other_rules_are_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import SubPost, SubPostPosition
    from backend.services import need_a_sub_post_service

    monkeypatch.setattr(need_a_sub_post_service, "now_utc", lambda: _CONTROLLED_NOW)
    positions = [
        _position("field_player", "men", 3, 0),
        _position("field_player", "women", 3, 1),
        _position("goalkeeper", "men", 3, 2),
        _position("goalkeeper", "women", 2, 3),
    ]

    payload = _payload(positions=positions, subs_needed=MAX_SUB_POST_TOTAL_SUBS)

    need_a_sub_post_service.validate_post_creation(payload)
    with _session() as db:
        owner = _user(1)
        db.add(owner)
        db.commit()

        created = need_a_sub_post_service.create_sub_post(db, owner, payload)

        assert created.subs_needed == MAX_SUB_POST_TOTAL_SUBS
        assert _count(db, SubPost) == 1
        assert _count(db, SubPostPosition) == len(positions)


@pytest.mark.requirement("WS02-04B1-R4")
@pytest.mark.parametrize(
    "positions",
    [
        [_position("field_player", "open", 1, 0), _position("field_player", "open", 1, 1)],
        [_position("field_player", "open", 1, 0), _position("field_player", "men", 1, 1)],
    ],
)
def test_invalid_position_rows_reject_before_post_or_position_persistence(
    monkeypatch: pytest.MonkeyPatch,
    positions: list[SubPostPositionCreate],
) -> None:
    from backend.models import SubPost, SubPostPosition
    from backend.services import need_a_sub_post_service

    monkeypatch.setattr(need_a_sub_post_service, "now_utc", lambda: _CONTROLLED_NOW)
    with _session() as db:
        owner = _user(1)
        db.add(owner)
        db.commit()
        payload = _payload(positions=positions, subs_needed=sum(position.spots_needed for position in positions))

        with pytest.raises(HTTPException) as exc_info:
            need_a_sub_post_service.create_sub_post(db, owner, payload)

        assert exc_info.value.status_code == 400
        assert _count(db, SubPost) == 0
        assert _count(db, SubPostPosition) == 0


@pytest.mark.requirement("WS02-04B1-R4")
def test_position_total_mismatch_rejects_before_partial_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import SubPost, SubPostPosition
    from backend.services import need_a_sub_post_service

    monkeypatch.setattr(need_a_sub_post_service, "now_utc", lambda: _CONTROLLED_NOW)
    with _session() as db:
        owner = _user(1)
        db.add(owner)
        db.commit()
        payload = _payload(
            positions=[_position("field_player", "open", 1)],
            subs_needed=2,
        )

        with pytest.raises(HTTPException) as exc_info:
            need_a_sub_post_service.create_sub_post(db, owner, payload)

        assert exc_info.value.status_code == 400
        assert _count(db, SubPost) == 0
        assert _count(db, SubPostPosition) == 0


@pytest.mark.requirement("WS02-04B1-R5")
def test_serial_waitlist_cap_rejects_next_request_without_prohibited_side_effects() -> None:
    from backend.models import Notification, SubPostRequest, SubPostRequestStatusHistory
    from backend.services.need_a_sub_request_service import create_request
    from backend.services.need_a_sub_rules import MAX_WAITLIST_REQUESTS_PER_POST

    with _session() as db:
        owner = _user(1)
        requesters = [_user(index + 2) for index in range(MAX_WAITLIST_REQUESTS_PER_POST + 2)]
        db.add(owner)
        db.add_all(requesters)
        db.commit()
        sub_post, position = _create_post_with_position(db, owner)

        accepted_requests = [
            create_request(db, requester, sub_post.id, position.id)
            for requester in requesters[:-1]
        ]
        waitlisted_requests = [
            sub_request for sub_request in accepted_requests if sub_request.request_status == "sub_waitlist"
        ]
        before_requests = _count(db, SubPostRequest)
        before_history = _count(db, SubPostRequestStatusHistory)
        before_notifications = _count(db, Notification)

        with pytest.raises(HTTPException) as exc_info:
            create_request(db, requesters[-1], sub_post.id, position.id)
        db.rollback()

        assert exc_info.value.status_code == 400
        assert len(waitlisted_requests) == MAX_WAITLIST_REQUESTS_PER_POST
        assert before_requests == MAX_WAITLIST_REQUESTS_PER_POST + 1
        assert _count(db, SubPostRequest) == before_requests
        assert _count(db, SubPostRequestStatusHistory) == before_history
        assert _count(db, Notification) == before_notifications
