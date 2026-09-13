from __future__ import annotations

import uuid

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from backend.models import AdminAction, User
from backend.schemas.admin_action_schema import AdminActionCreate, AdminActionRead
from backend.services.admin_action_display_service import (
    ACTION_DISPLAY_RULES,
    build_target_summary,
    collect_primary_target_ids,
    load_target_records,
    selected_target_rules,
)
from backend.services.admin_action_policy import (
    ADMIN_ACTION_POLICIES,
    ADMIN_ACTION_TARGET_FIELDS,
    TARGET_GAME_ID,
    TARGET_PAYMENT_EVENT_ID,
    TARGET_PAYMENT_ID,
    TARGET_VENUE_ID,
)

pytestmark = pytest.mark.suite_type("ordinary")

_EXPECTED_POLICIES = {
    "create_community_game_detail": ({TARGET_GAME_ID}, {TARGET_GAME_ID}, "support"),
    "update_community_game_detail": ({TARGET_GAME_ID}, {TARGET_GAME_ID}, "support"),
    "delete_game": ({TARGET_GAME_ID}, {TARGET_GAME_ID}, "support"),
    "delete_venue": ({TARGET_VENUE_ID}, {TARGET_VENUE_ID}, "support"),
    "update_payment_event": (
        {TARGET_PAYMENT_EVENT_ID},
        {TARGET_PAYMENT_EVENT_ID, TARGET_PAYMENT_ID},
        "money",
    ),
}

_EXPECTED_DISPLAY = {
    "create_community_game_detail": ("Community game detail created", TARGET_GAME_ID),
    "update_community_game_detail": ("Community game detail updated", TARGET_GAME_ID),
    "delete_game": ("Game deleted", TARGET_GAME_ID),
    "delete_venue": ("Venue deleted", TARGET_VENUE_ID),
    "update_payment_event": ("Payment event updated", TARGET_PAYMENT_EVENT_ID),
}


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _admin() -> User:
    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws09-02b-display-admin-{unique}",
        role="admin",
        email=f"ws09-02b-display-admin-{unique}@example.invalid",
        first_name="Audit",
        last_name="Display",
        account_status="active",
        hosting_status="eligible",
    )


def test_new_policy_target_and_display_registries_are_exact() -> None:
    assert TARGET_PAYMENT_EVENT_ID in ADMIN_ACTION_TARGET_FIELDS

    for action_type, (required, allowed, builder) in _EXPECTED_POLICIES.items():
        policy = ADMIN_ACTION_POLICIES[action_type]
        assert policy.category == "mutation"
        assert policy.required_target_rules[0].all_of == tuple(required)
        assert policy.allowed_target_fields == frozenset(allowed)
        assert policy.metadata_builder_key == builder
        assert policy.requires_reason is False
        assert policy.allows_audit_note is True

    for action_type, (label, primary_field) in _EXPECTED_DISPLAY.items():
        display = ACTION_DISPLAY_RULES[action_type]
        assert display.label == label
        assert display.primary_targets[0].field_name == primary_field


def test_payment_event_target_is_present_in_create_and_read_schemas() -> None:
    target_id = uuid.uuid4()
    create = AdminActionCreate(
        action_type="update_payment_event",
        target_payment_event_id=target_id,
    )
    assert create.target_payment_event_id == target_id
    assert "target_payment_event_id" in AdminActionRead.model_fields


def test_payment_event_target_display_is_id_only_and_never_queries_payment_events() -> (
    None
):
    target_id = uuid.uuid4()
    action = AdminAction(
        id=uuid.uuid4(),
        admin_user_id=uuid.uuid4(),
        action_type="update_payment_event",
        outcome="succeeded",
        correlation_id=uuid.uuid4(),
        target_payment_event_id=target_id,
    )

    assert collect_primary_target_ids([action]) == {}
    target_rule = selected_target_rules(action)[0]
    summary = build_target_summary(action, target_rule, {})
    assert summary is not None
    assert summary.target_field == TARGET_PAYMENT_EVENT_ID
    assert summary.target_type == "payment_event"
    assert summary.target_type_label == "Payment event"
    assert summary.label == f"Payment event {target_id}"
    assert summary.destination_path is None

    with _session() as db:
        queried_payment_events = False

        def capture_statement(
            conn,
            cursor,
            statement,
            parameters,
            context,
            executemany,
        ):
            nonlocal queried_payment_events
            del conn, cursor, parameters, context, executemany
            if "payment_events" in statement.lower():
                queried_payment_events = True

        event.listen(db.bind, "before_cursor_execute", capture_statement)
        try:
            assert load_target_records(db, [action]) == {}
        finally:
            event.remove(db.bind, "before_cursor_execute", capture_statement)
        assert queried_payment_events is False


def test_audit_note_copies_payment_event_target_without_reference_hydration() -> None:
    from backend.services.admin_action_service import build_copied_note_targets

    event_id = uuid.uuid4()
    original = AdminAction(
        id=uuid.uuid4(),
        admin_user_id=uuid.uuid4(),
        action_type="update_payment_event",
        outcome="succeeded",
        correlation_id=uuid.uuid4(),
        target_payment_event_id=event_id,
    )
    copied = build_copied_note_targets(
        original,
        ADMIN_ACTION_POLICIES["append_audit_note"],
    )
    assert copied[TARGET_PAYMENT_EVENT_ID] == event_id
    assert copied["target_admin_action_id"] == original.id


def test_covered_domain_conflict_fallbacks_do_not_expose_database_details() -> None:
    from backend.services.game_rules import build_game_conflict_detail
    from backend.services.payment_event_service import (
        build_payment_event_conflict_detail,
    )
    from backend.services.venue_service import build_venue_conflict_detail

    private_detail = "private_schema.private_table violated private_constraint"
    error = IntegrityError("INSERT", {}, RuntimeError(private_detail))

    assert build_game_conflict_detail(error) == "Game could not be saved."
    assert (
        build_payment_event_conflict_detail(error)
        == "Payment event could not be saved."
    )
    assert build_venue_conflict_detail(error) == "Venue could not be saved."
