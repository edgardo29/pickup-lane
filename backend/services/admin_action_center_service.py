from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from backend.models import AdminReviewCase, Game, User, VenueImage
from backend.schemas.admin_action_center_schema import (
    AdminActionCenterItemRead,
    AdminActionCenterRead,
    AdminActionCenterSectionRead,
)
from backend.services.admin_review_actionability_service import (
    build_open_content_review_case_actionable_condition,
)
from backend.services.admin_review_service import CASE_ACTIVE_STATUSES
from backend.services.game_rules import OPEN_GAME_STATUSES

ACTION_CENTER_ITEM_LIMIT = 50
OFFICIAL_GAMES_SECTION_KEY = "official_games"
OFFICIAL_GAMES_SECTION_LABEL = "Official Games"
REVIEW_CASES_SECTION_KEY = "review_cases"
REVIEW_CASES_SECTION_LABEL = "Review Cases"


def get_admin_action_center(db: Session, *, viewer_user: User) -> AdminActionCenterRead:
    generated_at = datetime.now(timezone.utc)
    sections: list[AdminActionCenterSectionRead] = []

    official_game_items = list_official_game_action_items(
        db,
        viewer_user=viewer_user,
        generated_at=generated_at,
    )
    if official_game_items:
        sections.append(
            AdminActionCenterSectionRead(
                section_key=OFFICIAL_GAMES_SECTION_KEY,
                label=OFFICIAL_GAMES_SECTION_LABEL,
                items=official_game_items,
            )
        )

    review_case_items = list_review_case_action_items(
        db,
        generated_at=generated_at,
    )
    if review_case_items:
        sections.append(
            AdminActionCenterSectionRead(
                section_key=REVIEW_CASES_SECTION_KEY,
                label=REVIEW_CASES_SECTION_LABEL,
                items=review_case_items,
            )
        )

    return AdminActionCenterRead(
        generated_at=generated_at,
        total_count=sum(len(section.items) for section in sections),
        sections=sections,
    )


def list_official_game_action_items(
    db: Session,
    *,
    viewer_user: User,
    generated_at: datetime,
) -> list[AdminActionCenterItemRead]:
    items = [
        *list_official_games_missing_host_items(db, generated_at=generated_at),
        *list_official_games_missing_primary_photo_items(
            db,
            generated_at=generated_at,
        ),
    ]

    return sorted(items, key=lambda item: (item.due_at or generated_at, item.item_id))


def list_review_case_action_items(
    db: Session,
    *,
    generated_at: datetime,
) -> list[AdminActionCenterItemRead]:
    priority_order = case(
        (AdminReviewCase.priority == "critical", 0),
        (AdminReviewCase.priority == "urgent", 1),
        else_=2,
    )
    review_cases = db.scalars(
        select(AdminReviewCase)
        .where(
            AdminReviewCase.case_status.in_(CASE_ACTIVE_STATUSES),
            build_open_content_review_case_actionable_condition(),
        )
        .order_by(
            priority_order.asc(),
            AdminReviewCase.updated_at.desc(),
            AdminReviewCase.created_at.desc(),
        )
        .limit(ACTION_CENTER_ITEM_LIMIT)
    ).all()

    return [
        build_review_case_item(review_case, generated_at=generated_at)
        for review_case in review_cases
    ]


def build_review_case_item(
    review_case: AdminReviewCase,
    *,
    generated_at: datetime,
) -> AdminActionCenterItemRead:
    return AdminActionCenterItemRead(
        item_id=f"review_case:{review_case.id}",
        item_type="review_case",
        section_key=REVIEW_CASES_SECTION_KEY,
        source="review_case",
        severity=review_case.priority,
        status=review_case.case_status,
        title=review_case.title,
        summary=review_case.summary,
        entity_type="review_case",
        entity_id=review_case.id,
        entity_label=review_case.title,
        related_entity_type=review_case.case_type,
        related_entity_id=(
            review_case.target_game_id
            or review_case.target_sub_post_id
            or review_case.target_sub_post_request_id
            or review_case.target_payment_id
            or review_case.target_financial_outcome_id
            or review_case.target_user_id
        ),
        related_entity_label=review_case.case_category,
        detected_at=review_case.created_at,
        due_at=review_case.updated_at or generated_at,
        action_label="Open case",
        action_path=f"/admin/review-cases/{review_case.id}",
        metadata={
            "case_status": review_case.case_status,
            "case_category": review_case.case_category,
            "case_type": review_case.case_type,
        },
    )


def list_official_games_missing_host_items(
    db: Session,
    *,
    generated_at: datetime,
) -> list[AdminActionCenterItemRead]:
    games = db.scalars(
        base_upcoming_official_games_query(generated_at)
        .where(Game.host_user_id.is_(None))
        .limit(ACTION_CENTER_ITEM_LIMIT)
    ).all()

    return [
        build_official_game_item(
            game,
            generated_at=generated_at,
            item_type="official_game_missing_host",
            title="Official game missing host",
            summary=f"{game.title} at {game.venue_name_snapshot} needs a host.",
            action_label="Assign host",
        )
        for game in games
    ]


def list_official_games_missing_primary_photo_items(
    db: Session,
    *,
    generated_at: datetime,
) -> list[AdminActionCenterItemRead]:
    active_primary_image_exists = (
        select(VenueImage.id)
        .where(
            VenueImage.venue_id == Game.venue_id,
            VenueImage.image_status == "active",
            VenueImage.is_primary.is_(True),
            VenueImage.deleted_at.is_(None),
        )
        .exists()
    )
    games = db.scalars(
        base_upcoming_official_games_query(generated_at)
        .where(~active_primary_image_exists)
        .limit(ACTION_CENTER_ITEM_LIMIT)
    ).all()

    return [
        build_official_game_item(
            game,
            generated_at=generated_at,
            item_type="official_game_missing_primary_venue_photo",
            title="Official game venue missing primary photo",
            summary=(
                f"{game.venue_name_snapshot} needs an active primary venue photo "
                f"for {game.title}."
            ),
            action_label="Add venue photo",
            related_entity_type="venue",
            related_entity_id=game.venue_id,
            related_entity_label=game.venue_name_snapshot,
        )
        for game in games
    ]


def base_upcoming_official_games_query(generated_at: datetime):
    return (
        select(Game)
        .where(
            Game.game_type == "official",
            Game.publish_status == "published",
            Game.game_status.in_(OPEN_GAME_STATUSES),
            Game.deleted_at.is_(None),
            Game.starts_at >= generated_at,
        )
        .order_by(Game.starts_at.asc(), Game.created_at.asc())
    )


def build_official_game_item(
    game: Game,
    *,
    generated_at: datetime,
    item_type: str,
    title: str,
    summary: str,
    action_label: str,
    related_entity_type: str | None = None,
    related_entity_id: UUID | None = None,
    related_entity_label: str | None = None,
) -> AdminActionCenterItemRead:
    return AdminActionCenterItemRead(
        item_id=f"{item_type}:{game.id}",
        item_type=item_type,
        section_key=OFFICIAL_GAMES_SECTION_KEY,
        source="derived",
        severity="attention",
        status="open",
        title=title,
        summary=summary,
        entity_type="game",
        entity_id=game.id,
        entity_label=game.title,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        related_entity_label=related_entity_label,
        detected_at=generated_at,
        due_at=game.starts_at,
        action_label=action_label,
        action_path=f"/admin/official-games/{game.id}",
        metadata={
            "game_status": game.game_status,
            "venue_id": str(game.venue_id),
            "venue_name": game.venue_name_snapshot,
        },
    )
