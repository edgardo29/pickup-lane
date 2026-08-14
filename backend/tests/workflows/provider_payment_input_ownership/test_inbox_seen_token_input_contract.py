from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.schemas.inbox_schema import InboxGlobalSeenUpdate

pytestmark = pytest.mark.suite_type("ordinary")


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _user(index: int):
    from backend.models import User

    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04b2a2b2-inbox-{index}-{unique}",
        role="player",
        email=f"ws02-04b2a2b2-inbox-{index}-{unique}@example.invalid",
        first_name="Inbox",
        last_name="User",
        account_status="active",
        hosting_status="eligible",
    )


def _state(user_id: uuid.UUID, sequence: int):
    from backend.models import PlatformNoticeGlobalSeenState

    now = datetime.now(timezone.utc)
    return PlatformNoticeGlobalSeenState(
        user_id=user_id,
        last_seen_global_sequence=sequence,
        created_at=now,
        updated_at=now,
    )


def _tampered_token(payload: dict[str, object]) -> str:
    envelope = {"payload": payload, "signature": "not-valid"}
    return base64.urlsafe_b64encode(json.dumps(envelope).encode("utf-8")).decode("ascii")


def _assert_rejected_token_shape(value: object) -> None:
    with pytest.raises(ValidationError):
        InboxGlobalSeenUpdate(seen_token=value)


@pytest.mark.requirement("WS02-04B2A2B2-R2")
def test_seen_token_is_trimmed_bounded_and_required() -> None:
    assert InboxGlobalSeenUpdate(seen_token="  token  ").seen_token == "token"
    assert InboxGlobalSeenUpdate(seen_token="x" * 512).seen_token == "x" * 512

    with pytest.raises(ValidationError):
        InboxGlobalSeenUpdate()
    _assert_rejected_token_shape("   ")
    _assert_rejected_token_shape("x" * 513)


@pytest.mark.requirement("WS02-04B2A2B2-R2")
def test_valid_seen_token_updates_only_the_signed_user_sequence() -> None:
    from backend.models import PlatformNoticeGlobalSeenState
    from backend.services.inbox_service import encode_global_seen_token, mark_global_platform_notices_seen

    with _session() as db:
        user = _user(1)
        other_user = _user(2)
        db.add_all([user, other_user])
        db.flush()
        db.add_all([_state(user.id, 2), _state(other_user.id, 9)])
        db.commit()

        token = encode_global_seen_token(highest_global_sequence=7, user_id=user.id)
        mark_global_platform_notices_seen(db, seen_token=token, user=user)

        assert db.get(PlatformNoticeGlobalSeenState, user.id).last_seen_global_sequence == 7
        assert db.get(PlatformNoticeGlobalSeenState, other_user.id).last_seen_global_sequence == 9


@pytest.mark.requirement("WS02-04B2A2B2-R2")
@pytest.mark.parametrize(
    "payload_factory",
    [
        lambda user: {
            "kind": "inbox_cursor",
            "version": 1,
            "user_id": str(user.id),
            "highest_global_sequence": 7,
        },
        lambda user: {
            "kind": "global_seen",
            "version": 2,
            "user_id": str(user.id),
            "highest_global_sequence": 7,
        },
        lambda user: {
            "kind": "global_seen",
            "version": 1,
            "user_id": "not-a-uuid",
            "highest_global_sequence": 7,
        },
        lambda user: {
            "kind": "global_seen",
            "version": 1,
            "user_id": str(user.id),
            "highest_global_sequence": "bad",
        },
    ],
)
def test_signed_but_invalid_seen_tokens_do_not_update_seen_state(payload_factory) -> None:
    from backend.models import PlatformNoticeGlobalSeenState
    from backend.services.inbox_service import encode_payload, mark_global_platform_notices_seen

    with _session() as db:
        user = _user(3)
        db.add(user)
        db.flush()
        db.add(_state(user.id, 5))
        db.commit()

        with pytest.raises(HTTPException):
            mark_global_platform_notices_seen(
                db,
                seen_token=encode_payload(payload_factory(user)),
                user=user,
            )
        db.rollback()

        assert db.get(PlatformNoticeGlobalSeenState, user.id).last_seen_global_sequence == 5


@pytest.mark.requirement("WS02-04B2A2B2-R2")
def test_tampered_seen_token_signature_does_not_update_seen_state() -> None:
    from backend.models import PlatformNoticeGlobalSeenState
    from backend.services.inbox_service import mark_global_platform_notices_seen

    with _session() as db:
        user = _user(6)
        db.add(user)
        db.flush()
        db.add(_state(user.id, 8))
        db.commit()

        with pytest.raises(HTTPException):
            mark_global_platform_notices_seen(
                db,
                seen_token=_tampered_token(
                    {
                        "kind": "global_seen",
                        "version": 1,
                        "user_id": str(user.id),
                        "highest_global_sequence": 20,
                    }
                ),
                user=user,
            )
        db.rollback()

        assert db.get(PlatformNoticeGlobalSeenState, user.id).last_seen_global_sequence == 8


@pytest.mark.requirement("WS02-04B2A2B2-R2")
def test_wrong_user_seen_token_rejects_without_side_effect() -> None:
    from backend.models import PlatformNoticeGlobalSeenState
    from backend.services.inbox_service import encode_global_seen_token, mark_global_platform_notices_seen

    with _session() as db:
        user = _user(4)
        other_user = _user(5)
        db.add_all([user, other_user])
        db.flush()
        db.add_all([_state(user.id, 4), _state(other_user.id, 6)])
        db.commit()

        token = encode_global_seen_token(highest_global_sequence=20, user_id=other_user.id)
        with pytest.raises(HTTPException):
            mark_global_platform_notices_seen(db, seen_token=token, user=user)
        db.rollback()

        assert db.get(PlatformNoticeGlobalSeenState, user.id).last_seen_global_sequence == 4
        assert db.get(PlatformNoticeGlobalSeenState, other_user.id).last_seen_global_sequence == 6
