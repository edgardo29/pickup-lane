from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from backend.database import SessionLocal
from backend.models import Game, HostPublishFee, Payment, Venue, VenueImage
from backend.schemas.admin_money_financial_outcome_schema import (
    AdminMoneyFinancialOutcomeCreate,
)
from backend.services.admin_financial_outcome_service import resolve_outcome_context
from backend.services.venue_image_service import validate_selected_image_capacity
from backend.tests.support.factories import create_user


def create_user_id() -> UUID:
    return UUID(create_user()["id"])


def create_venue(db, *, user_id: UUID) -> Venue:
    venue = Venue(
        id=uuid4(),
        name="A2A Field",
        address_line_1="10 Boundaries Ave",
        city="Chicago",
        state="IL",
        postal_code="60601",
        country_code="US",
        venue_status="approved",
        created_by_user_id=user_id,
        approved_by_user_id=user_id,
        approved_at=datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(venue)
    db.flush()
    return venue


def create_community_game(db, *, host_user_id: UUID, venue: Venue) -> Game:
    starts_at = datetime.now(timezone.utc) + timedelta(days=7)
    game = Game(
        id=uuid4(),
        game_type="community",
        payment_collection_type="external_host",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="A2A Match",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        neighborhood_snapshot=venue.neighborhood,
        host_user_id=host_user_id,
        created_by_user_id=host_user_id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        starts_on_local=starts_at.date(),
        timezone="America/Chicago",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=10,
        price_per_player_cents=1200,
        currency="USD",
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=4,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="custom_hosted",
        published_at=datetime.now(timezone.utc),
    )
    db.add(game)
    db.flush()
    return game


def create_paid_host_publish_fee(
    db,
    *,
    host_user_id: UUID,
    game: Game,
    amount_cents: int,
) -> HostPublishFee:
    payment = Payment(
        id=uuid4(),
        payer_user_id=host_user_id,
        game_id=game.id,
        payment_type="community_publish_fee",
        provider="stripe",
        provider_payment_intent_id=f"test-payment-intent-{uuid4().hex}",
        idempotency_key=f"a2a-payment-{uuid4().hex}",
        amount_cents=amount_cents,
        currency="USD",
        payment_status="succeeded",
        paid_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    db.flush()

    host_publish_fee = HostPublishFee(
        id=uuid4(),
        game_id=game.id,
        host_user_id=host_user_id,
        payment_id=payment.id,
        amount_cents=amount_cents,
        currency="USD",
        fee_status="paid",
        waiver_reason="none",
        paid_at=datetime.now(timezone.utc),
    )
    db.add(host_publish_fee)
    db.flush()
    return host_publish_fee


def add_venue_image(
    db,
    *,
    venue_id: UUID,
    uploaded_by_user_id: UUID,
    index: int,
    image_status: str,
) -> None:
    db.add(
        VenueImage(
            id=uuid4(),
            venue_id=venue_id,
            uploaded_by_user_id=uploaded_by_user_id,
            storage_provider="r2",
            storage_object_key=f"venues/{venue_id}/a2a-{index}.jpg",
            storage_bucket="test-bucket",
            storage_account_id="test-account",
            content_type="image/jpeg",
            size_bytes=1024 + index,
            image_role="gallery",
            image_status=image_status,
            is_primary=False,
            sort_order=index,
        )
    )


def test_admin_money_amount_cannot_exceed_target_host_publish_fee() -> None:
    host_user_id = create_user_id()
    with SessionLocal() as db:
        venue = create_venue(db, user_id=host_user_id)
        game = create_community_game(db, host_user_id=host_user_id, venue=venue)
        host_publish_fee = create_paid_host_publish_fee(
            db,
            host_user_id=host_user_id,
            game=game,
            amount_cents=499,
        )
        db.commit()

        payload = AdminMoneyFinancialOutcomeCreate(
            outcome="credit",
            reason="Target-bounded credit",
            idempotency_key="a2a-target-credit",
            host_publish_fee_id=host_publish_fee.id,
            amount_cents=500,
        )

        with pytest.raises(HTTPException) as exc_info:
            resolve_outcome_context(db, payload=payload, outcome=payload.outcome)

        assert exc_info.value.status_code == 400


def test_admin_money_without_target_allows_only_zero_amount() -> None:
    host_user_id = create_user_id()
    with SessionLocal() as db:
        zero_payload = AdminMoneyFinancialOutcomeCreate(
            outcome="manual_review",
            reason="No eligible target",
            idempotency_key="a2a-zero-amount",
            host_user_id=host_user_id,
            amount_cents=0,
        )
        resolved = resolve_outcome_context(
            db,
            payload=zero_payload,
            outcome=zero_payload.outcome,
        )
        assert resolved[-1] == 0

        nonzero_payload = AdminMoneyFinancialOutcomeCreate(
            outcome="manual_review",
            reason="No eligible target",
            idempotency_key="a2a-nonzero-amount",
            host_user_id=host_user_id,
            amount_cents=1,
        )
        with pytest.raises(HTTPException) as exc_info:
            resolve_outcome_context(
                db,
                payload=nonzero_payload,
                outcome=nonzero_payload.outcome,
            )

        assert exc_info.value.status_code == 400


def test_venue_image_selected_capacity_counts_pending_and_active_images() -> None:
    admin_user_id = create_user_id()
    with SessionLocal() as db:
        venue = create_venue(db, user_id=admin_user_id)
        add_venue_image(
            db,
            venue_id=venue.id,
            uploaded_by_user_id=admin_user_id,
            index=0,
            image_status="active",
        )
        add_venue_image(
            db,
            venue_id=venue.id,
            uploaded_by_user_id=admin_user_id,
            index=1,
            image_status="pending_upload",
        )
        add_venue_image(
            db,
            venue_id=venue.id,
            uploaded_by_user_id=admin_user_id,
            index=2,
            image_status="active",
        )
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            validate_selected_image_capacity(db, venue.id)

        assert exc_info.value.status_code == 400


def test_venue_image_selected_capacity_excludes_hidden_images() -> None:
    admin_user_id = create_user_id()
    with SessionLocal() as db:
        venue = create_venue(db, user_id=admin_user_id)
        for index, image_status in enumerate(("active", "pending_upload", "hidden")):
            add_venue_image(
                db,
                venue_id=venue.id,
                uploaded_by_user_id=admin_user_id,
                index=index,
                image_status=image_status,
            )
        db.commit()

        validate_selected_image_capacity(db, venue.id)
