from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import CheckConstraint, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend.models import AdminAction, AdminRejectedAttempt, User
from backend.observability.correlation import correlation_context
from backend.schemas.admin_action_schema import AdminActionNoteCreate

pytestmark = pytest.mark.suite_type("ordinary")

IMMUTABLE_ERROR = "admin audit rows are immutable"


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _record_admin_action(*args, **kwargs):
    from backend.services.admin_action_service import record_admin_action

    return record_admin_action(*args, **kwargs)


def _append_admin_action_note(*args, **kwargs):
    from backend.services.admin_action_service import append_admin_action_note

    return append_admin_action_note(*args, **kwargs)


def _user(label: str, *, role: str = "player") -> User:
    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws09-02a-{label}-{unique}",
        role=role,
        email=f"ws09-02a-{label}-{unique}@example.invalid",
        first_name="Audit",
        last_name=label,
        account_status="active",
        hosting_status="eligible",
    )


def _persist_actor_and_target() -> tuple[uuid.UUID, uuid.UUID]:
    actor = _user("actor", role="admin")
    target = _user("target")
    actor_id = actor.id
    target_id = target.id
    with _session() as db:
        db.add_all([actor, target])
        db.commit()
    return actor_id, target_id


def _persist_action(
    actor_id: uuid.UUID,
    target_id: uuid.UUID,
    *,
    idempotency_key: str | None = None,
) -> uuid.UUID:
    with _session() as db:
        action = _record_admin_action(
            db,
            admin_user_id=actor_id,
            action_type="suspend_user",
            outcome="succeeded",
            target_user_id=target_id,
            reason="Verified policy violation.",
            metadata={"source": "ci"},
            idempotency_key=idempotency_key,
        )
        db.commit()
        return action.id


def _persist_rejected_attempt(
    actor_id: uuid.UUID,
    target_id: uuid.UUID,
) -> uuid.UUID:
    attempt_id = uuid.uuid4()
    attempt = AdminRejectedAttempt(
        id=attempt_id,
        admin_user_id=actor_id,
        attempt_type="suspend_user_rejected",
        rejection_mode="domain_rejected_postload",
        response_status_code=409,
        route_method="POST",
        route_path=f"/admin/users/{target_id}/suspend",
        target_user_id=target_id,
        metadata_={"reason_code": "already_suspended"},
    )
    with _session() as db:
        db.add(attempt)
        db.commit()
    return attempt_id


@pytest.mark.requirement("WS09-02A-R1")
def test_admin_action_insert_requires_explicit_outcome_correlation_and_database_time() -> (
    None
):
    actor_id, target_id = _persist_actor_and_target()
    correlation_id = uuid.uuid4()
    before = datetime.now(timezone.utc)

    with correlation_context(str(correlation_id)), _session() as db:
        action = _record_admin_action(
            db,
            admin_user_id=actor_id,
            action_type="suspend_user",
            outcome="succeeded",
            target_user_id=target_id,
            reason="Verified policy violation.",
        )
        assert action.created_at is None
        db.commit()
        db.refresh(action)
        assert action.outcome == "succeeded"
        assert action.correlation_id == correlation_id
        assert action.created_at >= before


@pytest.mark.requirement("WS09-02A-R1")
@pytest.mark.parametrize(
    ("outcome", "correlation_id", "constraint_fragment"),
    [
        (None, uuid.uuid4(), "outcome"),
        ("succeeded", None, "correlation_id"),
        ("not-final", uuid.uuid4(), "ck_admin_actions_outcome"),
    ],
)
def test_database_rejects_missing_or_invalid_required_audit_disposition(
    outcome: str | None,
    correlation_id: uuid.UUID | None,
    constraint_fragment: str,
) -> None:
    actor_id, target_id = _persist_actor_and_target()
    with _session() as db:
        db.add(
            AdminAction(
                id=uuid.uuid4(),
                admin_user_id=actor_id,
                action_type="suspend_user",
                outcome=outcome,
                correlation_id=correlation_id,
                target_user_id=target_id,
                reason="Invalid persistence fixture.",
            )
        )
        with pytest.raises(IntegrityError) as exc_info:
            db.commit()
        assert constraint_fragment in str(exc_info.value.orig)


def _assert_immutable_error(exc: DBAPIError) -> None:
    assert IMMUTABLE_ERROR in str(exc.orig)
    assert getattr(exc.orig, "sqlstate", None) == "55000"


@pytest.mark.requirement("WS09-02A-R2")
@pytest.mark.parametrize("table_name", ["admin_actions", "admin_rejected_attempts"])
@pytest.mark.parametrize("operation", ["update", "delete"])
@pytest.mark.parametrize("write_style", ["raw", "orm"])
def test_audit_rows_reject_raw_and_orm_updates_and_deletes(
    table_name: str,
    operation: str,
    write_style: str,
) -> None:
    actor_id, target_id = _persist_actor_and_target()
    action_id = _persist_action(actor_id, target_id)
    rejected_id = _persist_rejected_attempt(actor_id, target_id)
    row_id = action_id if table_name == "admin_actions" else rejected_id

    with _session() as db:
        if write_style == "raw":
            statement = (
                f"UPDATE {table_name} SET created_at = created_at WHERE id = :row_id"
                if operation == "update"
                else f"DELETE FROM {table_name} WHERE id = :row_id"
            )
            with pytest.raises(DBAPIError) as exc_info:
                db.execute(text(statement), {"row_id": row_id})
                db.commit()
        else:
            model = (
                AdminAction if table_name == "admin_actions" else AdminRejectedAttempt
            )
            row = db.get(model, row_id)
            assert row is not None
            if operation == "update":
                row.created_at = row.created_at
                if isinstance(row, AdminAction):
                    row.reason = "Attempted rewrite."
                else:
                    row.route_path = "/attempted-rewrite"
            else:
                db.delete(row)
            with pytest.raises(DBAPIError) as exc_info:
                db.commit()
        _assert_immutable_error(exc_info.value)
        db.rollback()

    with _session() as fresh_db:
        if table_name == "admin_actions":
            original = fresh_db.get(AdminAction, row_id)
            assert original is not None
            assert original.reason == "Verified policy violation."
        else:
            original = fresh_db.get(AdminRejectedAttempt, row_id)
            assert original is not None
            assert original.route_path.endswith(f"/{target_id}/suspend")


@pytest.mark.requirement("WS09-02A-R3")
def test_correction_appends_self_linked_row_and_replay_never_rewrites_original() -> (
    None
):
    actor_id, target_id = _persist_actor_and_target()
    original_id = _persist_action(actor_id, target_id)
    payload = AdminActionNoteCreate(
        note="Support confirmed the original audit context.",
        idempotency_key="ws09-02a-correction",
    )

    correction_id = _append_admin_action_note(
        authenticated_admin_id=actor_id,
        target_admin_action_id=original_id,
        payload=payload,
    )
    replay_id = _append_admin_action_note(
        authenticated_admin_id=actor_id,
        target_admin_action_id=original_id,
        payload=payload,
    )
    assert replay_id == correction_id

    with _session() as db:
        original = db.get(AdminAction, original_id)
        correction = db.get(AdminAction, correction_id)
        assert original is not None
        assert correction is not None
        assert original.action_type == "suspend_user"
        assert original.reason == "Verified policy violation."
        assert correction.action_type == "append_audit_note"
        assert correction.outcome == "succeeded"
        assert correction.target_admin_action_id == original.id
        assert correction.target_user_id == original.target_user_id

    with pytest.raises(HTTPException) as reused_key:
        _append_admin_action_note(
            authenticated_admin_id=actor_id,
            target_admin_action_id=original_id,
            payload=AdminActionNoteCreate(
                note="A different correction body.",
                idempotency_key="ws09-02a-correction",
            ),
        )
    assert reused_key.value.status_code == 409

    with pytest.raises(HTTPException) as note_chain:
        _append_admin_action_note(
            authenticated_admin_id=actor_id,
            target_admin_action_id=correction_id,
            payload=AdminActionNoteCreate(note="Forbidden note chain."),
        )
    assert note_chain.value.status_code == 400


def _quoted_values(definition: str) -> set[str]:
    return set(re.findall(r"'([^']+)'", definition))


@pytest.mark.requirement("WS09-02A-R1")
def test_policy_model_and_database_constraints_are_synchronized() -> None:
    from backend.services.admin_action_policy import ADMIN_ACTION_TYPES
    from backend.services.admin_action_service import ADMIN_ACTION_OUTCOMES

    model_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in AdminAction.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert _quoted_values(model_constraints["ck_admin_actions_action_type"]) == set(
        ADMIN_ACTION_TYPES
    )
    assert _quoted_values(model_constraints["ck_admin_actions_outcome"]) == set(
        ADMIN_ACTION_OUTCOMES
    )

    with _session() as db:
        definitions = dict(
            db.execute(
                text(
                    "SELECT conname, pg_get_constraintdef(oid) "
                    "FROM pg_constraint "
                    "WHERE conname IN "
                    "('ck_admin_actions_action_type', 'ck_admin_actions_outcome')"
                )
            ).all()
        )
    assert _quoted_values(definitions["ck_admin_actions_action_type"]) == set(
        ADMIN_ACTION_TYPES
    )
    assert _quoted_values(definitions["ck_admin_actions_outcome"]) == set(
        ADMIN_ACTION_OUTCOMES
    )


@pytest.mark.requirement("WS09-02A-R4")
def test_audit_insert_failure_rolls_back_the_privileged_domain_change() -> None:
    actor_id, target_id = _persist_actor_and_target()
    _persist_action(actor_id, target_id, idempotency_key="duplicate-operation")

    with _session() as db:
        target = db.get(User, target_id)
        assert target is not None
        original_last_name = target.last_name
        target.last_name = "PrivilegedMutation"
        _record_admin_action(
            db,
            admin_user_id=actor_id,
            action_type="suspend_user",
            outcome="succeeded",
            target_user_id=target_id,
            reason="Duplicate operation.",
            idempotency_key="duplicate-operation",
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    with _session() as fresh_db:
        target = fresh_db.get(User, target_id)
        assert target is not None
        assert target.last_name == original_last_name


@pytest.mark.requirement("WS09-02A-R4")
def test_canonical_writer_adds_without_committing() -> None:
    actor_id, target_id = _persist_actor_and_target()
    with _session() as caller_db:
        action = _record_admin_action(
            caller_db,
            admin_user_id=actor_id,
            action_type="suspend_user",
            outcome="succeeded",
            target_user_id=target_id,
            reason="Caller owns this transaction.",
        )
        assert action in caller_db.new
        with _session() as observer_db:
            assert observer_db.get(AdminAction, action.id) is None
        caller_db.rollback()

    with _session() as fresh_db:
        assert fresh_db.get(AdminAction, action.id) is None
