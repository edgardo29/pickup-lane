from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.schemas.game_credit_schema import GameCreditIssueCreate, GameCreditReverseCreate

pytestmark = pytest.mark.suite_type("ordinary")

_STARTS_AT = datetime(2035, 2, 1, 18, 0, tzinfo=timezone.utc)
_ENDS_AT = _STARTS_AT + timedelta(hours=2)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _count(db: Session, model: type[object]) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _user(index: int, *, role: str = "player"):
    from backend.models import User

    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04b2a2b2-credit-{index}-{unique}",
        role=role,
        email=f"ws02-04b2a2b2-credit-{index}-{unique}@example.invalid",
        first_name="Credit",
        last_name=f"User{index}",
        account_status="active",
        hosting_status="eligible",
    )


def _venue(admin):
    from backend.models import Venue

    return Venue(
        id=uuid.uuid4(),
        name="B2A2B2 Credit Field",
        address_line_1="1 Credit Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        created_by_user_id=admin.id,
        approved_by_user_id=admin.id,
        approved_at=datetime.now(timezone.utc),
    )


def _game(
    admin,
    venue,
    *,
    official: bool = True,
    payment_collection_type: str | None = None,
):
    from backend.models import Game

    collection_type = payment_collection_type or ("in_app" if official else "external_host")

    return Game(
        id=uuid.uuid4(),
        game_type="official" if official else "community",
        payment_collection_type=collection_type,
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="B2A2B2 Credit Game",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=None if official else admin.id,
        created_by_user_id=admin.id,
        starts_at=_STARTS_AT,
        ends_at=_ENDS_AT,
        starts_on_local=_STARTS_AT.date(),
        timezone="UTC",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=12,
        price_per_player_cents=0 if collection_type == "none" else 1200,
        currency="USD",
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=0,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="official_standard" if official else "custom_hosted",
        published_at=datetime.now(timezone.utc),
    )


def _booking(user, game, *, total_cents: int = 1300):
    from backend.models import Booking

    return Booking(
        id=uuid.uuid4(),
        game_id=game.id,
        buyer_user_id=user.id,
        booking_status="confirmed",
        payment_status="paid",
        participant_count=1,
        subtotal_cents=max(total_cents - 100, 0),
        platform_fee_cents=100,
        discount_cents=0,
        total_cents=total_cents,
        currency="USD",
        price_per_player_snapshot_cents=max(total_cents - 100, 0),
        platform_fee_snapshot_cents=100,
        booked_at=datetime.now(timezone.utc),
    )


def _payment(user, *, booking=None, game=None, amount_cents: int = 1300, index: int = 1):
    from backend.models import Payment

    return Payment(
        id=uuid.uuid4(),
        payer_user_id=user.id,
        booking_id=booking.id if booking is not None else None,
        game_id=game.id if game is not None else None,
        payment_type="booking" if booking is not None else "admin_charge",
        provider="stripe",
        provider_payment_intent_id=f"pi_ws02_04b2a2b2_{index}_{uuid.uuid4()}",
        provider_charge_id=None,
        idempotency_key=f"payment-{index}-{uuid.uuid4()}",
        amount_cents=amount_cents,
        currency="USD",
        payment_status="succeeded",
        paid_at=datetime.now(timezone.utc),
        payment_metadata={"test": "ws02-04b2a2b2"},
    )


def _target_state(db: Session):
    admin = _user(0, role="admin")
    user = _user(1)
    db.add_all([admin, user])
    db.flush()

    venue = _venue(admin)
    db.add(venue)
    db.flush()

    game = _game(admin, venue, official=True)
    other_game = _game(admin, venue, official=True)
    community_game = _game(admin, venue, official=False)
    db.add_all([game, other_game, community_game])
    db.flush()

    booking = _booking(user, game)
    other_booking = _booking(user, other_game)
    db.add_all([booking, other_booking])
    db.flush()

    payment = _payment(user, booking=booking, game=game, index=1)
    booking_only_payment = _payment(user, booking=booking, game=None, index=2)
    second_booking_payment = _payment(user, booking=booking, game=game, index=3)
    unlinked_payment = _payment(user, game=None, index=4)
    mismatched_payment = _payment(user, booking=booking, game=other_game, index=5)
    db.add_all([
        payment,
        booking_only_payment,
        second_booking_payment,
        unlinked_payment,
        mismatched_payment,
    ])
    db.commit()
    return {
        "admin": admin,
        "user": user,
        "venue": venue,
        "game": game,
        "other_game": other_game,
        "community_game": community_game,
        "booking": booking,
        "other_booking": other_booking,
        "payment": payment,
        "booking_only_payment": booking_only_payment,
        "second_booking_payment": second_booking_payment,
        "unlinked_payment": unlinked_payment,
        "mismatched_payment": mismatched_payment,
    }


def _payload(user, *, amount_cents: int = 1300, **overrides: object) -> GameCreditIssueCreate:
    payload = {
        "user_id": user.id,
        "amount_cents": amount_cents,
        "credit_reason": "official_game_cancelled",
        "idempotency_key": f"credit-{uuid.uuid4()}",
        "note": "source-owned credit",
    }
    payload.update(overrides)
    return GameCreditIssueCreate(**payload)


def _issue(db: Session, state: dict[str, object], **payload_overrides: object):
    from backend.services.game_credit_admin_service import issue_admin_game_credit

    return issue_admin_game_credit(
        db,
        admin_user=state["admin"],
        payload=_payload(state["user"], **payload_overrides),
    )


def _reverse(
    db: Session,
    state: dict[str, object],
    game_credit_id: uuid.UUID,
    **payload_overrides: object,
):
    from backend.services.game_credit_admin_service import reverse_admin_game_credit

    return reverse_admin_game_credit(
        db,
        admin_user=state["admin"],
        game_credit_id=game_credit_id,
        payload=GameCreditReverseCreate(**payload_overrides),
    )


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_payment_source_requires_authoritative_official_in_app_context() -> None:
    from backend.models import GameCredit

    with _session() as db:
        state = _target_state(db)

        credit = _issue(db, state, source_payment_id=state["payment"].id)
        assert credit.amount_cents == 1300
        assert credit.source_payment_id == state["payment"].id

        with pytest.raises(HTTPException):
            _issue(
                db,
                state,
                source_payment_id=state["unlinked_payment"].id,
                source_game_id=state["game"].id,
            )
        db.rollback()
        assert _count(db, GameCredit) == 1


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_credit_source_rejects_non_official_non_in_app_game_contexts() -> None:
    from backend.models import GameCredit

    with _session() as db:
        state = _target_state(db)
        community_host = _user(20)
        db.add(community_host)
        db.flush()
        community_none_game = _game(
            community_host,
            state["venue"],
            official=False,
            payment_collection_type="none",
        )
        db.add(community_none_game)
        db.flush()

        community_booking = _booking(state["user"], state["community_game"])
        community_payment = _payment(
            state["user"],
            booking=community_booking,
            game=state["community_game"],
            index=20,
        )
        no_collection_booking = _booking(state["user"], community_none_game)
        no_collection_payment = _payment(
            state["user"],
            booking=no_collection_booking,
            game=community_none_game,
            index=21,
        )
        db.add_all([
            community_booking,
            community_payment,
            no_collection_booking,
            no_collection_payment,
        ])
        db.commit()

        with pytest.raises(HTTPException) as community_exc:
            _issue(
                db,
                state,
                source_booking_id=community_booking.id,
                source_payment_id=community_payment.id,
            )
        db.rollback()
        with pytest.raises(HTTPException) as no_collection_exc:
            _issue(
                db,
                state,
                source_booking_id=no_collection_booking.id,
                source_payment_id=no_collection_payment.id,
            )
        db.rollback()

        assert community_exc.value.status_code == 400
        assert no_collection_exc.value.status_code == 400
        assert _count(db, GameCredit) == 0


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_credit_source_rejects_booking_and_payment_owned_by_another_user() -> None:
    from backend.models import GameCredit

    with _session() as db:
        state = _target_state(db)
        other_user = _user(22)
        db.add(other_user)
        db.flush()

        other_user_booking = _booking(other_user, state["game"])
        other_user_payment = _payment(
            other_user,
            booking=other_user_booking,
            game=state["game"],
            index=22,
        )
        db.add_all([other_user_booking, other_user_payment])
        db.commit()

        with pytest.raises(HTTPException) as booking_exc:
            _issue(db, state, source_booking_id=other_user_booking.id)
        db.rollback()
        with pytest.raises(HTTPException) as payment_exc:
            _issue(db, state, source_payment_id=other_user_payment.id)
        db.rollback()

        assert booking_exc.value.status_code == 400
        assert payment_exc.value.status_code == 400
        assert _count(db, GameCredit) == 0


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_booking_only_payment_source_and_matching_source_game_remain_supported() -> None:
    with _session() as db:
        state = _target_state(db)

        credit = _issue(
            db,
            state,
            source_payment_id=state["booking_only_payment"].id,
            source_game_id=state["game"].id,
        )

        assert credit.source_payment_id == state["booking_only_payment"].id
        assert credit.amount_cents == 1300


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_payment_booking_and_caller_source_game_must_agree() -> None:
    from backend.models import GameCredit

    with _session() as db:
        state = _target_state(db)

        with pytest.raises(HTTPException):
            _issue(db, state, source_payment_id=state["mismatched_payment"].id)
        db.rollback()
        with pytest.raises(HTTPException):
            _issue(
                db,
                state,
                source_payment_id=state["payment"].id,
                source_game_id=state["other_game"].id,
            )
        db.rollback()

        assert _count(db, GameCredit) == 0


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_source_game_only_does_not_manufacture_monetary_eligibility() -> None:
    from backend.models import GameCredit

    with _session() as db:
        state = _target_state(db)

        with pytest.raises(HTTPException) as exc_info:
            _issue(db, state, source_game_id=state["game"].id)
        db.rollback()

        assert exc_info.value.status_code == 400
        assert _count(db, GameCredit) == 0


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_same_booking_and_payment_source_share_one_remaining_budget_payment_first() -> None:
    from backend.models import GameCredit

    with _session() as db:
        state = _target_state(db)

        _issue(db, state, amount_cents=800, source_payment_id=state["payment"].id)
        _issue(db, state, amount_cents=500, source_booking_id=state["booking"].id)

        with pytest.raises(HTTPException):
            _issue(db, state, amount_cents=1, source_booking_id=state["booking"].id)
        db.rollback()

        assert _count(db, GameCredit) == 2


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_same_booking_and_payment_source_share_one_remaining_budget_booking_first() -> None:
    from backend.models import GameCredit

    with _session() as db:
        state = _target_state(db)

        _issue(db, state, amount_cents=700, source_booking_id=state["booking"].id)
        _issue(db, state, amount_cents=600, source_payment_id=state["payment"].id)

        with pytest.raises(HTTPException):
            _issue(db, state, amount_cents=1, source_payment_id=state["payment"].id)
        db.rollback()

        assert _count(db, GameCredit) == 2


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_multiple_payments_for_same_booking_share_one_budget() -> None:
    from backend.models import GameCredit

    with _session() as db:
        state = _target_state(db)

        _issue(db, state, amount_cents=900, source_payment_id=state["payment"].id)

        with pytest.raises(HTTPException):
            _issue(
                db,
                state,
                amount_cents=401,
                source_payment_id=state["second_booking_payment"].id,
            )
        db.rollback()

        assert _count(db, GameCredit) == 1


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_linked_booking_and_payment_source_ceiling_uses_minimum_amount() -> None:
    from backend.models import GameCredit

    with _session() as db:
        state = _target_state(db)
        booking = _booking(state["user"], state["game"], total_cents=1300)
        payment = _payment(
            state["user"],
            booking=booking,
            game=state["game"],
            amount_cents=900,
            index=30,
        )
        db.add_all([booking, payment])
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            _issue(
                db,
                state,
                amount_cents=901,
                source_booking_id=booking.id,
                source_payment_id=payment.id,
            )
        db.rollback()
        assert _count(db, GameCredit) == 0

        credit = _issue(
            db,
            state,
            amount_cents=900,
            source_booking_id=booking.id,
            source_payment_id=payment.id,
        )

        assert exc_info.value.status_code == 400
        assert credit.amount_cents == 900
        assert _count(db, GameCredit) == 1


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_initial_credit_amount_is_positive_and_within_source_ceiling() -> None:
    from backend.models import GameCredit

    for amount_cents in (0, -1):
        with pytest.raises(ValidationError):
            GameCreditIssueCreate(
                user_id=uuid.uuid4(),
                amount_cents=amount_cents,
                credit_reason="official_game_cancelled",
                source_booking_id=uuid.uuid4(),
            )

    with _session() as db:
        state = _target_state(db)

        with pytest.raises(HTTPException) as exc_info:
            _issue(
                db,
                state,
                amount_cents=1301,
                source_booking_id=state["booking"].id,
            )
        db.rollback()
        assert _count(db, GameCredit) == 0

        credit = _issue(
            db,
            state,
            amount_cents=1300,
            source_booking_id=state["booking"].id,
        )

        assert exc_info.value.status_code == 400
        assert credit.amount_cents == 1300
        assert _count(db, GameCredit) == 1


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_reversed_credits_do_not_reduce_remaining_source_budget() -> None:
    from backend.models import GameCredit

    with _session() as db:
        state = _target_state(db)
        now = datetime.now(timezone.utc)
        db.add(
            GameCredit(
                id=uuid.uuid4(),
                user_id=state["user"].id,
                amount_cents=1300,
                available_cents=0,
                currency="USD",
                credit_status="reversed",
                credit_reason="official_game_cancelled",
                source_booking_id=state["booking"].id,
                issued_by_user_id=state["admin"].id,
                reversed_by_user_id=state["admin"].id,
                reversed_at=now,
                idempotency_key=f"reversed-{uuid.uuid4()}",
            )
        )
        db.commit()

        active_credit = _issue(db, state, amount_cents=1300, source_booking_id=state["booking"].id)

        assert active_credit.amount_cents == 1300
        assert _count(db, GameCredit) == 2


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_credit_operational_text_is_trimmed_before_persistence() -> None:
    with _session() as db:
        state = _target_state(db)

        credit = _issue(
            db,
            state,
            amount_cents=100,
            source_booking_id=state["booking"].id,
            idempotency_key="  trimmed-key  ",
            note="  source-owned reason  ",
        )

        assert credit.idempotency_key == "trimmed-key"
        assert credit.note == "source-owned reason"


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_credit_reverse_request_text_bounds_and_rejects_client_amount() -> None:
    assert GameCreditReverseCreate(idempotency_key="  reverse-key  ").idempotency_key == "reverse-key"
    assert GameCreditReverseCreate(note="  reverse note  ").note == "reverse note"
    assert GameCreditReverseCreate(idempotency_key="x" * 160).idempotency_key == "x" * 160
    assert GameCreditReverseCreate(note="n" * 1000).note == "n" * 1000
    assert GameCreditReverseCreate(idempotency_key="   ").idempotency_key == ""
    assert GameCreditReverseCreate(note="   ").note == ""

    with pytest.raises(ValidationError):
        GameCreditReverseCreate(amount_cents=1)
    with pytest.raises(ValidationError):
        GameCreditReverseCreate(idempotency_key="x" * 161)
    with pytest.raises(ValidationError):
        GameCreditReverseCreate(note="n" * 1001)


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_credit_reverse_uses_current_unused_amount_and_persists_reversal() -> None:
    from backend.models import AdminAction, GameCredit, GameCreditUsage

    with _session() as db:
        state = _target_state(db)
        credit = _issue(db, state, amount_cents=1300, source_booking_id=state["booking"].id)
        credit_id = credit.id
        credit.available_cents = 450
        db.add(credit)
        db.commit()

        reversed_credit = _reverse(
            db,
            state,
            credit_id,
            idempotency_key="  reverse-key  ",
            note="  reverse reason  ",
        )
        usage = db.scalar(
            select(GameCreditUsage).where(GameCreditUsage.game_credit_id == credit_id)
        )
        action = db.scalar(
            select(AdminAction).where(
                AdminAction.action_type == "reverse_credit",
                AdminAction.target_game_credit_id == credit_id,
            )
        )
        persisted_credit = db.get(GameCredit, credit_id)

        assert reversed_credit.credit_status == "reversed"
        assert reversed_credit.available_cents == 0
        assert reversed_credit.reversed_by_user_id == state["admin"].id
        assert reversed_credit.reversed_at is not None
        assert usage.amount_cents == 450
        assert usage.usage_type == "reverse"
        assert usage.usage_status == "reversed"
        assert usage.idempotency_key == "reverse-key"
        assert usage.reason_code == "admin_credit_reversal"
        assert action.reason == "reverse reason"
        assert persisted_credit.credit_status == "reversed"
        assert persisted_credit.available_cents == 0


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_credit_reverse_blank_idempotency_generates_server_owned_key() -> None:
    from backend.models import GameCreditUsage

    with _session() as db:
        state = _target_state(db)
        credit = _issue(db, state, amount_cents=100, source_booking_id=state["booking"].id)
        credit_id = credit.id

        _reverse(
            db,
            state,
            credit_id,
            idempotency_key="   ",
            note="reverse reason",
        )
        usage = db.scalar(
            select(GameCreditUsage).where(GameCreditUsage.game_credit_id == credit_id)
        )

        assert usage.amount_cents == 100
        assert usage.idempotency_key.startswith(f"reverse-credit:{credit_id}:")


@pytest.mark.requirement("WS02-04B2A2B2-R6")
def test_credit_reverse_blank_note_rejects_without_persisted_reversal() -> None:
    from backend.models import AdminAction, GameCredit, GameCreditUsage

    with _session() as db:
        state = _target_state(db)
        credit = _issue(db, state, amount_cents=100, source_booking_id=state["booking"].id)
        credit_id = credit.id

        with pytest.raises(HTTPException) as exc_info:
            _reverse(
                db,
                state,
                credit_id,
                idempotency_key="reverse-key",
                note="   ",
            )
        db.rollback()

        persisted_credit = db.get(GameCredit, credit_id)
        usage_count = _count(db, GameCreditUsage)
        reverse_action_count = int(
            db.scalar(
                select(func.count())
                .select_from(AdminAction)
                .where(
                    AdminAction.action_type == "reverse_credit",
                    AdminAction.target_game_credit_id == credit_id,
                )
            )
            or 0
        )

        assert exc_info.value.status_code == 400
        assert persisted_credit.credit_status == "active"
        assert persisted_credit.available_cents == 100
        assert usage_count == 0
        assert reverse_action_count == 0
