from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.sql.elements import ColumnElement

from backend.models import AdminReviewCase, Game, SubPost

CONTENT_MODERATION_CASE_CATEGORY = "content_moderation"
NON_ACTIONABLE_SUB_POST_CONTENT_REVIEW_STATUSES = (
    "cancelled",
    "completed",
    "expired",
    "removed",
)
NON_ACTIONABLE_GAME_CONTENT_REVIEW_STATUSES = (
    "cancelled",
    "completed",
    "expired",
    "removed",
)


def is_sub_post_content_review_actionable(sub_post: SubPost | None) -> bool:
    if sub_post is None:
        return False
    return sub_post.post_status not in NON_ACTIONABLE_SUB_POST_CONTENT_REVIEW_STATUSES


def is_game_content_review_actionable(game: Game | None) -> bool:
    if game is None:
        return False
    if game.deleted_at is not None:
        return False
    return game.game_status not in NON_ACTIONABLE_GAME_CONTENT_REVIEW_STATUSES


def build_open_content_review_case_actionable_condition() -> ColumnElement[bool]:
    actionable_sub_post_exists = (
        select(SubPost.id)
        .where(
            SubPost.id == AdminReviewCase.target_sub_post_id,
            ~SubPost.post_status.in_(NON_ACTIONABLE_SUB_POST_CONTENT_REVIEW_STATUSES),
        )
        .exists()
    )
    actionable_game_exists = (
        select(Game.id)
        .where(
            Game.id == AdminReviewCase.target_game_id,
            Game.deleted_at.is_(None),
            ~Game.game_status.in_(NON_ACTIONABLE_GAME_CONTENT_REVIEW_STATUSES),
        )
        .exists()
    )

    return or_(
        AdminReviewCase.case_category != CONTENT_MODERATION_CASE_CATEGORY,
        and_(
            AdminReviewCase.target_sub_post_id.is_not(None),
            actionable_sub_post_exists,
        ),
        and_(
            AdminReviewCase.case_type == "community_game",
            AdminReviewCase.target_game_id.is_not(None),
            actionable_game_exists,
        ),
    )
