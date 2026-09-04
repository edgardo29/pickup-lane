from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

os.environ.setdefault("APP_ENV", "test")
from backend.tests.support.environment_safety import DEDICATED_TEST_DATABASE_NAME

_DATABASE_URL_CONFIGURED_FOR_RUNTIME = bool(os.getenv("DATABASE_URL"))
if not _DATABASE_URL_CONFIGURED_FOR_RUNTIME:
    os.environ["DATABASE_URL"] = (
        f"postgresql+psycopg://localhost:5432/{DEDICATED_TEST_DATABASE_NAME}"
    )

try:
    from backend.models import AdminReviewCase, Game, SubPost, User, Venue
    from backend.services.admin_review_service import create_internal_review_signal
    from backend.services.moderation_surfacing_service import (
        surface_community_game_text,
        surface_need_a_sub_post_text,
    )
finally:
    if not _DATABASE_URL_CONFIGURED_FOR_RUNTIME:
        os.environ.pop("DATABASE_URL", None)

BASE_TIME = datetime(2038, 3, 1, 18, 0, tzinfo=timezone.utc)


def make_user(label: str, *, role: str = "player") -> User:
    token = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws03-05b-{label}-{token}",
        role=role,
        email=f"ws03-05b-{label}-{token}@example.invalid",
        first_name="Review",
        last_name=label.title(),
        account_status="active",
        hosting_status="eligible",
    )


def seed_game(db, *, description: str = "Text me at 312-555-1212") -> Game:
    owner = make_user("owner")
    venue = Venue(
        id=uuid.uuid4(),
        name="Review Field",
        address_line_1="1 Test Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        is_active=True,
    )
    game = Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="none",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="Review Game",
        description=description,
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=owner.id,
        created_by_user_id=owner.id,
        starts_at=BASE_TIME,
        ends_at=BASE_TIME + timedelta(hours=2),
        starts_on_local=BASE_TIME.date(),
        timezone="UTC",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=10,
        price_per_player_cents=0,
        currency="USD",
        policy_mode="custom_hosted",
        published_at=BASE_TIME - timedelta(days=1),
    )
    db.add_all([owner, venue])
    db.commit()
    db.add(game)
    db.commit()
    return game


def seed_admin(db, label: str = "admin") -> User:
    admin = make_user(label, role="admin")
    db.add(admin)
    db.commit()
    return admin


def seed_sub_post(db) -> SubPost:
    owner = make_user("sub-owner")
    post = SubPost(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        post_status="active",
        public_visibility_status="visible",
        sport_type="soccer",
        format_label="5v5",
        environment_type="indoor",
        skill_level="any",
        game_player_group="coed",
        starts_at=BASE_TIME + timedelta(days=2),
        ends_at=BASE_TIME + timedelta(days=2, hours=2),
        starts_on_local=(BASE_TIME + timedelta(days=2)).date(),
        timezone="UTC",
        location_name="Review Field",
        address_line_1="1 Test Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        subs_needed=1,
        price_due_at_venue_cents=0,
        currency="USD",
        expires_at=BASE_TIME + timedelta(days=1),
        notes="Text me at 312-555-1212",
    )
    db.add(owner)
    db.commit()
    db.add(post)
    db.commit()
    return post


def create_content_case(db, game: Game) -> AdminReviewCase:
    surface_community_game_text(db, game_id=game.id)
    return db.scalar(
        select(AdminReviewCase).where(
            AdminReviewCase.target_game_id == game.id,
            AdminReviewCase.case_type == "community_game",
            AdminReviewCase.case_category == "content_moderation",
            AdminReviewCase.case_status == "open",
        )
    )


def create_chat_case(
    db,
    game: Game,
    *,
    idempotency_key: str | None = None,
) -> AdminReviewCase:
    review_case, _signal, _created, _replayed = create_internal_review_signal(
        db,
        signal_category="chat_moderation",
        source="chat_moderation",
        priority="urgent",
        title="Chat review signal",
        summary="Review persisted chat moderation evidence.",
        target_data={"target_game_id": game.id},
        metadata={"current_match": True, "detected_categories": ["abuse"]},
        idempotency_key=idempotency_key or f"ws03-05b-chat-{uuid.uuid4()}",
    )
    return review_case


def create_sub_content_case(db, post: SubPost) -> AdminReviewCase:
    surface_need_a_sub_post_text(db, sub_post_id=post.id)
    return db.scalar(
        select(AdminReviewCase).where(
            AdminReviewCase.target_sub_post_id == post.id,
            AdminReviewCase.case_type == "need_a_sub",
            AdminReviewCase.case_category == "content_moderation",
            AdminReviewCase.case_status == "open",
        )
    )


def create_sub_chat_case(db, post: SubPost) -> AdminReviewCase:
    review_case, _signal, _created, _replayed = create_internal_review_signal(
        db,
        signal_category="chat_moderation",
        source="chat_moderation",
        priority="urgent",
        title="Need a Sub chat review signal",
        summary="Review persisted Need a Sub chat moderation evidence.",
        target_data={"target_sub_post_id": post.id},
        metadata={"current_match": True, "detected_categories": ["abuse"]},
        idempotency_key=f"ws03-05b-sub-chat-{uuid.uuid4()}",
    )
    return review_case


def session():
    from backend.database import SessionLocal

    return SessionLocal()
