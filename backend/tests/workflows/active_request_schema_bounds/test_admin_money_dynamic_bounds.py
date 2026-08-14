from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.schemas.admin_money_financial_outcome_schema import AdminMoneyFinancialOutcomeCreate

pytestmark = pytest.mark.suite_type("ordinary")

_STARTS_AT = datetime(2035, 1, 15, 18, 0, tzinfo=timezone.utc)
_ENDS_AT = datetime(2035, 1, 15, 20, 0, tzinfo=timezone.utc)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _count(db: Session, model: type[object]) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _user(role: str = "player") -> User:
    from backend.models import User

    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04b2a2a-user-{unique}",
        role=role,
        email=f"ws02-04b2a2a-{unique}@example.invalid",
        first_name="A2A",
        last_name="Money",
        account_status="active",
        hosting_status="eligible",
    )


def _venue(created_by: User) -> Venue:
    from backend.models import Venue

    return Venue(
        id=uuid.uuid4(),
        name="A2A Money Field",
        address_line_1="1 Target Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        created_by_user_id=created_by.id,
        approved_by_user_id=created_by.id,
        approved_at=datetime.now(timezone.utc),
    )


def _community_game(host: User, venue: Venue) -> Game:
    from backend.models import Game

    return Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="external_host",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="A2A Money Game",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=host.id,
        created_by_user_id=host.id,
        starts_at=_STARTS_AT,
        ends_at=_ENDS_AT,
        starts_on_local=_STARTS_AT.date(),
        timezone="UTC",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=12,
        price_per_player_cents=1200,
        currency="USD",
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=0,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="custom_hosted",
        published_at=datetime.now(timezone.utc),
    )


def _host_publish_fee(game: Game, host: User, amount_cents: int) -> HostPublishFee:
    from backend.models import HostPublishFee

    return HostPublishFee(
        id=uuid.uuid4(),
        game_id=game.id,
        host_user_id=host.id,
        amount_cents=amount_cents,
        currency="USD",
        fee_status="pending",
        waiver_reason="none",
    )


def _target_state(db: Session, *, fee_amount_cents: int = 2500) -> tuple[User, Game, HostPublishFee]:
    host = _user()
    db.add(host)
    db.flush()

    venue = _venue(host)
    db.add(venue)
    db.flush()

    game = _community_game(host, venue)
    db.add(game)
    db.flush()

    fee = _host_publish_fee(game, host, fee_amount_cents)
    db.add(fee)
    db.commit()
    return host, game, fee


def _payload(**overrides: object) -> AdminMoneyFinancialOutcomeCreate:
    payload = {
        "outcome": "no_fee_charged",
        "reason": "valid reason",
        "idempotency_key": f"a2a-{uuid.uuid4()}",
    }
    payload.update(overrides)
    return AdminMoneyFinancialOutcomeCreate(**payload)


@pytest.mark.requirement("WS02-04B2A2A-R6")
def test_amount_cents_schema_rejects_negative_and_accepts_non_negative_values() -> None:
    with pytest.raises(ValidationError):
        _payload(amount_cents=-1)

    assert _payload(amount_cents=0).amount_cents == 0
    assert _payload(amount_cents=1).amount_cents == 1


@pytest.mark.requirement("WS02-04B2A2A-R6")
def test_host_publish_fee_target_allows_equal_amount_and_rejects_amount_above_target() -> None:
    from backend.models import AdminFinancialOutcome
    from backend.services.admin_financial_outcome_service import resolve_outcome_context

    with _session() as db:
        _host, _game, fee = _target_state(db, fee_amount_cents=2500)

        resolved = resolve_outcome_context(
            db,
            payload=_payload(host_publish_fee_id=fee.id, amount_cents=2500),
            outcome="no_fee_charged",
        )
        assert resolved[-1] == 2500

        with pytest.raises(HTTPException) as exc_info:
            resolve_outcome_context(
                db,
                payload=_payload(host_publish_fee_id=fee.id, amount_cents=2501),
                outcome="no_fee_charged",
            )
        db.rollback()

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "amount_cents exceeds the eligible target amount."
        assert _count(db, AdminFinancialOutcome) == 0


@pytest.mark.requirement("WS02-04B2A2A-R6")
def test_no_eligible_positive_target_rejects_positive_amount_but_allows_zero_boundary() -> None:
    from backend.models import AdminFinancialOutcome
    from backend.services.admin_financial_outcome_service import resolve_outcome_context

    with _session() as db:
        host = _user()
        db.add(host)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            resolve_outcome_context(
                db,
                payload=_payload(host_user_id=host.id, amount_cents=1),
                outcome="no_fee_charged",
            )
        db.rollback()

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "amount_cents exceeds the eligible target amount."
        assert _count(db, AdminFinancialOutcome) == 0

        resolved = resolve_outcome_context(
            db,
            payload=_payload(host_user_id=host.id, amount_cents=0),
            outcome="no_fee_charged",
        )
        assert resolved[-1] == 0


@pytest.mark.requirement("WS02-04B2A2A-R6")
def test_rejected_dynamic_amounts_do_not_persist_prohibited_financial_outcomes() -> None:
    from backend.models import AdminFinancialOutcome
    from backend.services.admin_financial_outcome_service import resolve_outcome_context

    with _session() as db:
        host, _game, fee = _target_state(db, fee_amount_cents=2500)
        rejected_payloads = (
            _payload(host_publish_fee_id=fee.id, amount_cents=2501),
            _payload(host_user_id=host.id, amount_cents=1),
        )

        for payload in rejected_payloads:
            with pytest.raises(HTTPException):
                resolve_outcome_context(db, payload=payload, outcome="no_fee_charged")
            db.rollback()
            assert _count(db, AdminFinancialOutcome) == 0
