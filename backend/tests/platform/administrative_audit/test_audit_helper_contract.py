from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.models import AdminAction, User
from backend.observability.correlation import correlation_context, get_correlation_id
from backend.schemas.admin_action_schema import AdminActionNoteCreate

pytestmark = pytest.mark.suite_type("ordinary")


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _service():
    from backend.services import admin_action_service

    return admin_action_service


def _user(
    label: str,
    *,
    role: str = "player",
    account_status: str = "active",
) -> User:
    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws09-02a-helper-{label}-{unique}",
        role=role,
        email=f"ws09-02a-helper-{label}-{unique}@example.invalid",
        first_name="Audit",
        last_name=label,
        account_status=account_status,
        hosting_status="eligible",
    )


def _persist_users(*users: User) -> None:
    with _session() as db:
        db.add_all(list(users))
        db.commit()
        for user in users:
            db.refresh(user)
            db.expunge(user)


def _install_sensitive_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.services.admin_action_policy import ADMIN_ACTION_POLICIES

    monkeypatch.setitem(
        ADMIN_ACTION_POLICIES,
        "suspend_user",
        replace(ADMIN_ACTION_POLICIES["suspend_user"], category="sensitive_read"),
    )


def _record_original(actor_id: uuid.UUID, target_id: uuid.UUID) -> uuid.UUID:
    with _session() as db:
        action = _service().record_admin_action(
            db,
            admin_user_id=actor_id,
            action_type="suspend_user",
            outcome="succeeded",
            target_user_id=target_id,
            reason="Original immutable action.",
        )
        db.commit()
        return action.id


@pytest.mark.requirement("WS09-02A-R5")
def test_sensitive_read_helper_commits_correlation_before_disclosure_and_uses_minimal_target_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_action_service = _service()
    actor = _user("actor", role="admin")
    target = _user("target")
    _persist_users(actor, target)
    _install_sensitive_policy(monkeypatch)
    correlation_id = uuid.uuid4()
    generic_loader_calls: list[object] = []
    monkeypatch.setattr(
        admin_action_service,
        "validate_reference_exists",
        lambda *args, **kwargs: generic_loader_calls.append((args, kwargs)),
    )
    statements: list[tuple[str, object]] = []

    from sqlalchemy import event

    from backend.database import engine

    def capture_statement(conn, cursor, statement, parameters, context, executemany):
        del conn, cursor, context, executemany
        statements.append((statement, parameters))

    event.listen(engine, "before_cursor_execute", capture_statement)
    try:
        disclosed = False
        with correlation_context(str(correlation_id)):
            action_id = admin_action_service.record_sensitive_admin_read(
                authenticated_admin_id=actor.id,
                action_type="suspend_user",
                reason="Approved support investigation.",
                metadata={"source": "ci"},
                target_user_id=target.id,
            )
        with _session() as observer_db:
            action = observer_db.get(AdminAction, action_id)
            assert action is not None
            assert action.outcome == "succeeded"
            assert action.correlation_id == correlation_id
        disclosed = True
        assert disclosed
    finally:
        event.remove(engine, "before_cursor_execute", capture_statement)

    assert generic_loader_calls == []
    target_selects = [
        statement
        for statement, parameters in statements
        if str(target.id) in repr(parameters) and "FROM users" in statement
    ]
    assert any(
        "SELECT users.id, users.deleted_at" in statement for statement in target_selects
    )
    assert all("users.email" not in statement for statement in target_selects)


@pytest.mark.requirement("WS09-02A-R5")
def test_sensitive_read_helper_preserves_safe_4xx_contracts_and_rejects_protected_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_action_service = _service()
    actor = _user("actor", role="admin")
    ordinary = _user("ordinary")
    suspended = _user("suspended", role="admin", account_status="suspended")
    target = _user("target")
    _persist_users(actor, ordinary, suspended, target)
    _install_sensitive_policy(monkeypatch)

    cases = [
        (
            {
                "authenticated_admin_id": ordinary.id,
                "action_type": "suspend_user",
                "target_user_id": target.id,
                "reason": "Approved investigation.",
            },
            403,
        ),
        (
            {
                "authenticated_admin_id": suspended.id,
                "action_type": "suspend_user",
                "target_user_id": target.id,
                "reason": "Approved investigation.",
            },
            403,
        ),
        (
            {
                "authenticated_admin_id": actor.id,
                "action_type": "append_audit_note",
                "target_admin_action_id": uuid.uuid4(),
                "reason": "Not a read category.",
            },
            400,
        ),
        (
            {
                "authenticated_admin_id": actor.id,
                "action_type": "suspend_user",
                "target_user_id": uuid.uuid4(),
                "reason": "Missing target.",
            },
            404,
        ),
        (
            {
                "authenticated_admin_id": actor.id,
                "action_type": "suspend_user",
                "target_user_id": target.id,
                "reason": "Approved investigation.",
                "metadata": {"password": "must-not-be-stored"},
            },
            400,
        ),
        (
            {
                "authenticated_admin_id": actor.id,
                "action_type": "suspend_user",
                "target_user_id": target.id,
                "reason": "Approved investigation.",
                "protected_payload": "must-not-be-accepted",
            },
            400,
        ),
    ]
    for kwargs, expected_status in cases:
        with pytest.raises(HTTPException) as exc_info:
            admin_action_service.record_sensitive_admin_read(**kwargs)
        assert exc_info.value.status_code == expected_status

    with _session() as db:
        assert db.scalar(select(func.count()).select_from(AdminAction)) == 0


@pytest.mark.requirement("WS09-02A-R4", "WS09-02A-R5")
def test_canonical_writer_rejects_sensitive_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_action_service = _service()
    actor = _user("actor", role="admin")
    target = _user("target")
    _persist_users(actor, target)
    _install_sensitive_policy(monkeypatch)
    with _session() as db, pytest.raises(HTTPException) as exc_info:
        admin_action_service.record_admin_action(
            db,
            admin_user_id=actor.id,
            action_type="suspend_user",
            outcome="succeeded",
            target_user_id=target.id,
            reason="Wrong writer.",
        )
    assert exc_info.value.status_code == 400


@pytest.mark.requirement("WS09-02A-R5")
def test_sensitive_read_success_does_not_commit_caller_pending_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_action_service = _service()
    actor = _user("actor", role="admin")
    target = _user("target")
    _persist_users(actor, target)
    _install_sensitive_policy(monkeypatch)
    pending = _user("pending-caller")

    with _session() as caller_db:
        caller_db.add(pending)
        caller_db.flush()
        action_id = admin_action_service.record_sensitive_admin_read(
            authenticated_admin_id=actor.id,
            action_type="suspend_user",
            target_user_id=target.id,
            reason="Approved investigation.",
        )
        with _session() as observer_db:
            assert observer_db.get(AdminAction, action_id) is not None
            assert observer_db.get(User, pending.id) is None
        caller_db.rollback()

    with _session() as observer_db:
        assert observer_db.get(User, pending.id) is None
        assert observer_db.get(AdminAction, action_id) is not None


def _install_failing_session_factory(
    monkeypatch: pytest.MonkeyPatch,
    *,
    commit_before_error: bool,
) -> None:
    admin_action_service = _service()
    real_factory = admin_action_service.SessionLocal

    def failing_factory():
        db = real_factory()
        real_commit = db.commit

        def fail_commit() -> None:
            if commit_before_error:
                real_commit()
            raise RuntimeError("postgresql://secret-host/private-audit-detail")

        db.commit = fail_commit
        return db

    monkeypatch.setattr(admin_action_service, "SessionLocal", failing_factory)


@pytest.mark.requirement("WS09-02A-R3", "WS09-02A-R5")
@pytest.mark.no_db_cleanup
def test_private_helpers_fail_closed_when_session_creation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_action_service = _service()

    def fail_session_creation():
        raise RuntimeError("postgresql://secret-host/private-audit-detail")

    monkeypatch.setattr(admin_action_service, "SessionLocal", fail_session_creation)

    calls = (
        lambda: admin_action_service.append_admin_action_note(
            authenticated_admin_id=uuid.uuid4(),
            target_admin_action_id=uuid.uuid4(),
            payload=AdminActionNoteCreate(note="Valid correction note."),
        ),
        lambda: admin_action_service.record_sensitive_admin_read(
            authenticated_admin_id=uuid.uuid4(),
            action_type="suspend_user",
            target_user_id=uuid.uuid4(),
            reason="Approved investigation.",
        ),
    )
    for call in calls:
        with pytest.raises(HTTPException) as exc_info:
            call()
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail == "Administrative audit recording is unavailable."
        assert "secret-host" not in str(exc_info.value.detail)


@pytest.mark.requirement("WS09-02A-R5")
@pytest.mark.parametrize("commit_before_error", [False, True])
def test_sensitive_read_failure_is_safe_and_does_not_touch_caller_transaction(
    monkeypatch: pytest.MonkeyPatch,
    commit_before_error: bool,
) -> None:
    admin_action_service = _service()
    actor = _user("actor", role="admin")
    target = _user("target")
    _persist_users(actor, target)
    _install_sensitive_policy(monkeypatch)
    _install_failing_session_factory(
        monkeypatch,
        commit_before_error=commit_before_error,
    )
    pending = _user("pending-caller")
    disclosed = False

    with _session() as caller_db:
        caller_db.add(pending)
        caller_db.flush()
        with pytest.raises(HTTPException) as exc_info:
            admin_action_service.record_sensitive_admin_read(
                authenticated_admin_id=actor.id,
                action_type="suspend_user",
                target_user_id=target.id,
                reason="Approved investigation.",
            )
            disclosed = True
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail == "Administrative audit recording is unavailable."
        assert "secret-host" not in str(exc_info.value.detail)
        assert not disclosed
        with _session() as observer_db:
            assert observer_db.get(User, pending.id) is None
        assert caller_db.get(User, pending.id) is pending
        caller_db.rollback()


@pytest.mark.requirement("WS09-02A-R3", "WS09-02A-R5")
def test_correction_success_and_failure_are_isolated_from_caller_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_action_service = _service()
    actor = _user("actor", role="admin")
    target = _user("target")
    _persist_users(actor, target)
    original_id = _record_original(actor.id, target.id)
    pending = _user("pending-caller")

    with _session() as caller_db:
        caller_db.add(pending)
        caller_db.flush()
        correction_id = admin_action_service.append_admin_action_note(
            authenticated_admin_id=actor.id,
            target_admin_action_id=original_id,
            payload=AdminActionNoteCreate(note="Committed correction."),
        )
        with _session() as observer_db:
            assert observer_db.get(AdminAction, correction_id) is not None
            assert observer_db.get(User, pending.id) is None

        _install_failing_session_factory(monkeypatch, commit_before_error=False)
        with pytest.raises(HTTPException) as exc_info:
            admin_action_service.append_admin_action_note(
                authenticated_admin_id=actor.id,
                target_admin_action_id=original_id,
                payload=AdminActionNoteCreate(note="Failed correction."),
            )
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail == "Administrative audit recording is unavailable."
        assert caller_db.get(User, pending.id) is pending
        caller_db.rollback()


@pytest.mark.requirement("WS09-02A-R5")
def test_private_helper_revalidates_current_admin_state_before_recording(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_action_service = _service()
    actor = _user("actor", role="admin")
    target = _user("target")
    _persist_users(actor, target)
    _install_sensitive_policy(monkeypatch)
    stale_route_actor = actor

    with _session() as db:
        current_actor = db.get(User, actor.id)
        assert current_actor is not None
        current_actor.account_status = "suspended"
        db.commit()

    assert stale_route_actor.account_status == "active"
    disclosed = False
    with pytest.raises(HTTPException) as exc_info:
        admin_action_service.record_sensitive_admin_read(
            authenticated_admin_id=stale_route_actor.id,
            action_type="suspend_user",
            target_user_id=target.id,
            reason="Must revalidate.",
        )
        disclosed = True
    assert exc_info.value.status_code == 403
    assert not disclosed
    with _session() as db:
        assert db.scalar(select(func.count()).select_from(AdminAction)) == 0


@pytest.mark.requirement("WS09-02A-R3", "WS09-02A-R5")
@pytest.mark.parametrize(
    ("role", "account_status", "mark_deleted"),
    [
        ("player", "active", False),
        ("admin", "suspended", False),
        ("admin", "deleted", True),
    ],
)
def test_correction_helper_revalidates_stale_actor_in_private_session(
    role: str,
    account_status: str,
    mark_deleted: bool,
) -> None:
    actor = _user("correction-actor", role="admin")
    target = _user("correction-target")
    _persist_users(actor, target)
    original_id = _record_original(actor.id, target.id)

    with _session() as db:
        current_actor = db.get(User, actor.id)
        assert current_actor is not None
        current_actor.role = role
        current_actor.account_status = account_status
        if mark_deleted:
            current_actor.deleted_at = datetime.now(timezone.utc)
        db.commit()

    assert actor.role == "admin"
    assert actor.account_status == "active"
    assert actor.deleted_at is None
    with pytest.raises(HTTPException) as exc_info:
        _service().append_admin_action_note(
            authenticated_admin_id=actor.id,
            target_admin_action_id=original_id,
            payload=AdminActionNoteCreate(note="Must revalidate the current actor."),
        )
    assert exc_info.value.status_code == 403

    with _session() as db:
        assert db.scalar(select(func.count()).select_from(AdminAction)) == 1


@pytest.mark.requirement("WS09-02A-R3")
def test_correction_helper_hides_unexpected_integrity_error_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_action_service = _service()
    actor = _user("integrity-actor", role="admin")
    target = _user("integrity-target")
    _persist_users(actor, target)
    original_id = _record_original(actor.id, target.id)
    real_factory = admin_action_service.SessionLocal

    def failing_factory():
        db = real_factory()

        def fail_commit() -> None:
            raise IntegrityError(
                "INSERT INTO admin_actions ...",
                {},
                RuntimeError("postgresql://secret-host/private-schema-detail"),
            )

        db.commit = fail_commit
        return db

    monkeypatch.setattr(admin_action_service, "SessionLocal", failing_factory)

    with pytest.raises(HTTPException) as exc_info:
        admin_action_service.append_admin_action_note(
            authenticated_admin_id=actor.id,
            target_admin_action_id=original_id,
            payload=AdminActionNoteCreate(note="Valid correction note."),
        )
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Administrative audit recording is unavailable."
    assert "secret-host" not in str(exc_info.value.detail)
    assert "private-schema-detail" not in str(exc_info.value.detail)

    with _session() as db:
        assert db.scalar(select(func.count()).select_from(AdminAction)) == 1


@pytest.mark.requirement("WS09-02A-R6")
@pytest.mark.no_db_cleanup
def test_non_request_correlation_fallback_generates_and_sets_fresh_uuid_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_action_service = _service()
    generated = [str(uuid.uuid4()), str(uuid.uuid4())]
    monkeypatch.setattr(admin_action_service, "get_correlation_id", lambda: None)
    monkeypatch.setattr(
        admin_action_service, "resolve_correlation_id", lambda: generated.pop(0)
    )

    first = admin_action_service.current_correlation_uuid()
    second = admin_action_service.current_correlation_uuid()

    assert first.version == 4
    assert second.version == 4
    assert first != second
    assert generated == []
    assert get_correlation_id() is None
