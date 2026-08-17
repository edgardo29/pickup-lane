from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.suite_type("ordinary")


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _install_sync_identities(
    monkeypatch: pytest.MonkeyPatch,
    identities_by_token: dict[str, tuple[str, str, bool]],
) -> None:
    from backend.services.auth_service import VerifiedFirebaseIdentity
    import backend.services.auth_account_service as auth_account_service

    def identity_from_header(authorization: str | None) -> VerifiedFirebaseIdentity:
        assert authorization is not None
        token = authorization.removeprefix("Bearer ").strip()
        uid, email, email_verified = identities_by_token[token]
        return VerifiedFirebaseIdentity(
            auth_user_id=uid,
            email=email,
            email_verified=email_verified,
        )

    monkeypatch.setattr(
        auth_account_service,
        "get_verified_firebase_identity_from_authorization",
        identity_from_header,
    )


def _count_rows(db: Session, model: type[object], *criteria: object) -> int:
    statement = select(func.count()).select_from(model)
    if criteria:
        statement = statement.where(*criteria)
    return int(db.scalar(statement) or 0)


def _install_commit_barrier(monkeypatch: pytest.MonkeyPatch) -> tuple[threading.Barrier, list[str]]:
    import backend.services.auth_account_service as auth_account_service

    barrier = threading.Barrier(2)
    commit_threads: list[str] = []
    original_commit = auth_account_service.commit_user_sync

    def commit_after_both_inserts(db, user):
        commit_threads.append(threading.current_thread().name)
        barrier.wait(timeout=10)
        return original_commit(db, user)

    monkeypatch.setattr(auth_account_service, "commit_user_sync", commit_after_both_inserts)
    return barrier, commit_threads


def _sync_in_thread(token: str) -> tuple[object, ...]:
    from backend.services.auth_account_service import sync_user_workflow

    with _session() as db:
        backend_pid = int(db.scalar(text("select pg_backend_pid()")) or 0)
        try:
            user = sync_user_workflow(f"Bearer {token}", db)
            return ("ok", str(user.id), user.auth_user_id, user.email, backend_pid)
        except HTTPException as exc:
            return ("http", exc.status_code, exc.detail, backend_pid)


@pytest.mark.requirement("WS03-02-R2", "WS03-02-R3")
def test_concurrent_first_login_same_uid_reuses_single_user_and_context_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import User, UserSettings, UserStats

    uid = f"ws03-02-race-same-{uuid.uuid4()}"
    email = f"ws03-02-race-same-{uuid.uuid4()}@example.invalid"
    _install_sync_identities(
        monkeypatch,
        {
            "same-a": (uid, email, True),
            "same-b": (uid, email, True),
        },
    )
    _barrier, commit_threads = _install_commit_barrier(monkeypatch)

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="same-login") as executor:
        results = list(executor.map(_sync_in_thread, ["same-a", "same-b"]))

    ok_results = [result for result in results if result[0] == "ok"]
    assert len(ok_results) == 2
    assert {result[1] for result in ok_results} == {ok_results[0][1]}
    assert {result[-1] for result in results} and len({result[-1] for result in results}) == 2
    assert sorted(commit_threads) == ["same-login_0", "same-login_1"]

    user_id = uuid.UUID(str(ok_results[0][1]))
    with _session() as db:
        assert _count_rows(db, User, User.auth_user_id == uid) == 1
        assert _count_rows(db, User, User.email == email) == 1
        assert _count_rows(db, UserSettings, UserSettings.user_id == user_id) == 1
        assert _count_rows(db, UserStats, UserStats.user_id == user_id) == 1


@pytest.mark.requirement("WS03-02-R2", "WS03-02-R5")
def test_concurrent_first_login_different_uid_same_email_leaves_single_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import User

    uid_a = f"ws03-02-race-a-{uuid.uuid4()}"
    uid_b = f"ws03-02-race-b-{uuid.uuid4()}"
    email = f"ws03-02-race-conflict-{uuid.uuid4()}@example.invalid"
    _install_sync_identities(
        monkeypatch,
        {
            "conflict-a": (uid_a, email, True),
            "conflict-b": (uid_b, email, True),
        },
    )
    _install_commit_barrier(monkeypatch)

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="email-race") as executor:
        results = list(executor.map(_sync_in_thread, ["conflict-a", "conflict-b"]))

    ok_results = [result for result in results if result[0] == "ok"]
    conflict_results = [result for result in results if result[0] == "http"]
    assert len(ok_results) == 1
    assert conflict_results == [("http", 409, "A user with this email already exists.", conflict_results[0][-1])]
    assert len({result[-1] for result in results}) == 2

    with _session() as db:
        assert _count_rows(db, User, User.email == email) == 1
        assert (
            _count_rows(db, User, User.auth_user_id == uid_a)
            + _count_rows(db, User, User.auth_user_id == uid_b)
        ) == 1
