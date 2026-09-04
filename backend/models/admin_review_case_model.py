import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database_metadata import Base


class AdminReviewCase(Base):
    __tablename__ = "admin_review_cases"
    __table_args__ = (
        CheckConstraint(
            "case_type IN ('community_game', 'need_a_sub', 'money', 'user', 'system')",
            name="ck_admin_review_cases_case_type",
        ),
        CheckConstraint(
            "case_status IN ('open', 'closed')",
            name="ck_admin_review_cases_case_status",
        ),
        CheckConstraint(
            "priority IN ('attention', 'urgent', 'critical')",
            name="ck_admin_review_cases_priority",
        ),
        CheckConstraint(
            ("case_category IN ('content_moderation', 'chat_moderation')"),
            name="ck_admin_review_cases_case_category",
        ),
        CheckConstraint(
            (
                "closure_outcome IS NULL OR closure_outcome IN ("
                "'enforcement_applied', 'no_action_needed', 'invalid_signal')"
            ),
            name="ck_admin_review_cases_closure_outcome",
        ),
        CheckConstraint(
            (
                "(case_status = 'open' "
                "AND closed_by_user_id IS NULL "
                "AND closure_outcome IS NULL "
                "AND closure_reason IS NULL "
                "AND closure_mode IS NULL "
                "AND closure_rule_id IS NULL "
                "AND closure_rule_version IS NULL "
                "AND closed_at IS NULL "
                "AND merged_into_case_id IS NULL) "
                "OR (case_status = 'closed' "
                "AND closure_outcome IS NOT NULL "
                "AND closure_reason IS NOT NULL AND btrim(closure_reason) <> '' "
                "AND closure_mode IS NOT NULL "
                "AND closed_at IS NOT NULL)"
            ),
            name="ck_admin_review_cases_closure_state",
        ),
        CheckConstraint(
            (
                "(closure_mode IS NULL) OR "
                "(closure_mode = 'manual' "
                "AND closure_outcome IN ("
                "'enforcement_applied', 'no_action_needed', 'invalid_signal') "
                "AND closed_by_user_id IS NOT NULL "
                "AND closure_rule_id IS NULL "
                "AND closure_rule_version IS NULL) OR "
                "(closure_mode = 'automatic' "
                "AND closure_outcome IN ("
                "'enforcement_applied', 'no_action_needed', 'invalid_signal') "
                "AND closure_rule_id IS NOT NULL "
                "AND btrim(closure_rule_id) <> '' "
                "AND closure_rule_version IS NOT NULL "
                "AND btrim(closure_rule_version) <> '')"
            ),
            name="ck_admin_review_cases_resolution_shape",
        ),
        CheckConstraint(
            "closure_mode IS NULL OR closure_mode IN ('manual', 'automatic')",
            name="ck_admin_review_cases_closure_mode",
        ),
        CheckConstraint(
            "case_version > 0",
            name="ck_admin_review_cases_case_version_positive",
        ),
        CheckConstraint(
            "btrim(creation_reason) <> ''",
            name="ck_admin_review_cases_creation_reason_nonblank",
        ),
        CheckConstraint(
            (
                "(assigned_to_user_id IS NULL AND assigned_at IS NULL) OR "
                "(case_status = 'open' AND assigned_to_user_id IS NOT NULL "
                "AND assigned_at IS NOT NULL)"
            ),
            name="ck_admin_review_cases_assignment_shape",
        ),
        CheckConstraint(
            "merged_into_case_id IS NULL OR merged_into_case_id <> id",
            name="ck_admin_review_cases_no_self_merge",
        ),
        CheckConstraint(
            (
                "merged_into_case_id IS NULL OR ("
                "case_status = 'closed' "
                "AND closure_mode IN ('manual', 'automatic') "
                "AND closure_outcome IN ("
                "'enforcement_applied', 'no_action_needed', 'invalid_signal') "
                "AND closure_reason IS NOT NULL "
                "AND btrim(closure_reason) <> '' "
                "AND closed_at IS NOT NULL)"
            ),
            name="ck_admin_review_cases_merged_source_resolved",
        ),
        CheckConstraint(
            (
                "case_status = 'closed' "
                "OR target_user_id IS NOT NULL "
                "OR target_game_id IS NOT NULL "
                "OR target_sub_post_id IS NOT NULL "
                "OR target_sub_post_request_id IS NOT NULL "
                "OR target_payment_id IS NOT NULL "
                "OR target_financial_outcome_id IS NOT NULL"
            ),
            name="ck_admin_review_cases_target_required",
        ),
        CheckConstraint(
            (
                "case_type <> 'community_game' OR ("
                "target_game_id IS NOT NULL "
                "AND target_user_id IS NULL "
                "AND target_sub_post_id IS NULL "
                "AND target_sub_post_request_id IS NULL "
                "AND target_payment_id IS NULL "
                "AND target_financial_outcome_id IS NULL)"
            ),
            name="ck_admin_review_cases_community_game_target",
        ),
        CheckConstraint(
            (
                "case_type <> 'need_a_sub' OR ("
                "target_sub_post_id IS NOT NULL "
                "AND target_user_id IS NULL "
                "AND target_game_id IS NULL "
                "AND target_sub_post_request_id IS NULL "
                "AND target_payment_id IS NULL "
                "AND target_financial_outcome_id IS NULL)"
            ),
            name="ck_admin_review_cases_need_sub_target",
        ),
        Index("ix_admin_review_cases_case_status", "case_status"),
        Index("ix_admin_review_cases_case_type", "case_type"),
        Index("ix_admin_review_cases_case_category", "case_category"),
        Index("ix_admin_review_cases_priority", "priority"),
        Index("ix_admin_review_cases_created_at", "created_at"),
        Index(
            "ix_admin_review_cases_status_updated_id",
            "case_status",
            "updated_at",
            "id",
        ),
        Index("ix_admin_review_cases_closed_at", "closed_at"),
        Index("ix_admin_review_cases_assigned_to_user_id", "assigned_to_user_id"),
        Index("ix_admin_review_cases_merged_into_case_id", "merged_into_case_id"),
        Index("ix_admin_review_cases_target_user_id", "target_user_id"),
        Index("ix_admin_review_cases_target_game_id", "target_game_id"),
        Index("ix_admin_review_cases_target_sub_post_id", "target_sub_post_id"),
        Index(
            "ix_admin_review_cases_target_sub_post_request_id",
            "target_sub_post_request_id",
        ),
        Index("ix_admin_review_cases_target_payment_id", "target_payment_id"),
        Index(
            "ix_admin_review_cases_target_financial_outcome_id",
            "target_financial_outcome_id",
        ),
        Index(
            "uq_admin_review_cases_open_community_game_moderation",
            "target_game_id",
            "case_category",
            unique=True,
            postgresql_where=text(
                "target_game_id IS NOT NULL "
                "AND case_type = 'community_game' "
                "AND case_category IN ('content_moderation', 'chat_moderation') "
                "AND case_status = 'open'"
            ),
        ),
        Index(
            "uq_admin_review_cases_open_need_sub_moderation",
            "target_sub_post_id",
            "case_category",
            unique=True,
            postgresql_where=text(
                "target_sub_post_id IS NOT NULL "
                "AND case_type = 'need_a_sub' "
                "AND case_category IN ('content_moderation', 'chat_moderation') "
                "AND case_status = 'open'"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    case_type: Mapped[str] = mapped_column(String(40), nullable=False)
    case_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'open'"),
    )
    case_category: Mapped[str] = mapped_column(String(60), nullable=False)
    priority: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'attention'"),
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    case_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )
    creation_reason: Mapped[str] = mapped_column(String(80), nullable=False)

    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="RESTRICT"),
        nullable=True,
    )
    target_sub_post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_posts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    target_sub_post_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_post_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_financial_outcome_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_financial_outcomes.id", ondelete="SET NULL"),
        nullable=True,
    )

    opened_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    closed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    closure_outcome: Mapped[str | None] = mapped_column(String(60), nullable=True)
    closure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    closure_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    closure_rule_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    closure_rule_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    merged_into_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_cases.id", ondelete="RESTRICT"),
        nullable=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
