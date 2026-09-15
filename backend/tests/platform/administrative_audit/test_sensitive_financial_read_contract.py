"""PostgreSQL evidence for WS09-02C's shared read-audit contract."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import event, func, select

from backend.database import SessionLocal, engine
from backend.models import (
    AdminAction,
    AdminFinancialOutcome,
    Booking,
    CommunityGameDetail,
    Game,
    GameCredit,
    GameParticipant,
    HostPublishFee,
    MoneyIssue,
    Payment,
    Refund,
    User,
    WaitlistEntry,
)
from backend.observability.correlation import correlation_context
from backend.services.admin_action_policy import (
    ADMIN_ACTION_POLICIES,
    SENSITIVE_FINANCIAL_READ_TARGETS,
    SENSITIVE_READ_LIST_LIMITS,
)
from backend.services.admin_action_service import (
    AUDIT_UNAVAILABLE_DETAIL,
    load_frozen_audited_rows,
    record_admin_action,
    record_financial_sensitive_read,
    record_sensitive_admin_read,
    record_sensitive_admin_read_batch,
)
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_game_roster_moderation_contract import (
    _community_game,
    _persist_community_game_fixture,
    _persist_game_fixture,
    _venue,
)
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    _auth_headers,
    _client,
    _install_tokens_for_users,
)
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_money_credit_refund_contract import (
    _persist_host_publish_fee_fixture,
    _persist_money_repair_fixture,
    _persist_paid_booking,
)
from backend.tests.workflows.payment_booking_state_machines_webhook_authority.test_payment_booking_transitions import (
    _create_booking_payment_state,
)

pytestmark = pytest.mark.suite_type("ordinary")


def _user(label: str, *, role: str = "player", status: str = "active") -> User:
    token = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws09-02c-{label}-{token}",
        role=role,
        email=f"ws09-02c-{label}-{token}@example.invalid",
        first_name="Audit",
        last_name=label,
        account_status=status,
        hosting_status="eligible",
    )


def _payment(payer: User) -> Payment:
    token = uuid.uuid4()
    return Payment(
        id=token,
        payer_user_id=payer.id,
        payment_type="admin_charge",
        provider="stripe",
        idempotency_key=f"ws09-02c-{token}",
        amount_cents=500,
        currency="USD",
        payment_status="failed",
    )


def _persist(*records: User | Payment) -> None:
    users = [record for record in records if isinstance(record, User)]
    payments = [record for record in records if isinstance(record, Payment)]
    with SessionLocal() as db:
        db.add_all(users)
        db.flush()
        db.add_all(payments)
        db.commit()
        for record in records:
            db.refresh(record)
            db.expunge(record)


def _rows_for(*target_ids: uuid.UUID) -> list[AdminAction]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AdminAction).where(AdminAction.target_payment_id.in_(target_ids))
            ).all()
        )


def _action_rows(action_type: str) -> list[AdminAction]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AdminAction).where(AdminAction.action_type == action_type)
            ).all()
        )


def _assert_one_action(
    action_type: str,
    *,
    actor_id: uuid.UUID,
    target_field: str,
    target_id: uuid.UUID,
) -> None:
    rows = _action_rows(action_type)
    assert len(rows) == 1, action_type
    row = rows[0]
    assert row.admin_user_id == actor_id
    assert getattr(row, target_field) == target_id
    assert row.outcome == "succeeded"
    assert row.correlation_id is not None
    assert row.reason is None
    assert row.metadata_ is None


def _persist_cross_user_fixture(
    *,
    admin: User,
    owner: User,
) -> dict[str, uuid.UUID]:
    game_id, _venue_id = _persist_game_fixture(
        f"ws09-02c-cross-user-{uuid.uuid4()}", admin=admin, creator=owner
    )
    booking_id = _persist_paid_booking(
        game_id=game_id,
        buyer_user_id=owner.id,
        amount_cents=1200,
    )
    money = _persist_money_repair_fixture(
        game_id=game_id,
        booking_id=booking_id,
        target_user_id=owner.id,
    )
    waitlist_entry_id = uuid.uuid4()
    with SessionLocal() as db:
        db.add(
            WaitlistEntry(
                id=waitlist_entry_id,
                game_id=game_id,
                user_id=owner.id,
                position=1,
                waitlist_status="removed",
            )
        )
        db.commit()
    host_fee_id = _persist_host_publish_fee_fixture(
        game_id=game_id,
        host_user_id=owner.id,
    )
    return {
        "game_id": game_id,
        "booking_id": booking_id,
        "payment_id": money["payment_id"],
        "refund_id": money["retry_refund_id"],
        "credit_id": money["credit_id"],
        "waitlist_entry_id": waitlist_entry_id,
        "host_fee_id": host_fee_id,
    }


def _persist_expired_checkout_state():
    with SessionLocal() as db:
        expires_at = db.scalar(select(func.now())) - timedelta(seconds=1)
        state = _create_booking_payment_state(
            db,
            now=expires_at - timedelta(minutes=2),
            expires_at=expires_at,
            payment_status="processing",
            provider_status="processing",
        )
        admin = db.get(User, state.admin_id)
        owner = db.get(User, state.user_id)
        assert admin is not None and owner is not None
        db.expunge(admin)
        db.expunge(owner)
    return state, admin, owner


def _checkout_action_rows(booking_id: uuid.UUID) -> list[AdminAction]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AdminAction).where(
                    AdminAction.action_type == "read_staff_checkout_status",
                    AdminAction.target_booking_id == booking_id,
                )
            ).all()
        )


def test_all_31_read_actions_have_exact_target_and_private_payload_policy() -> None:
    assert len(SENSITIVE_FINANCIAL_READ_TARGETS) == 31
    assert len(SENSITIVE_READ_LIST_LIMITS) == 10
    assert set(SENSITIVE_READ_LIST_LIMITS) == {
        name for name in SENSITIVE_FINANCIAL_READ_TARGETS if name.endswith("_list_item")
    }
    for action_type, target_field in SENSITIVE_FINANCIAL_READ_TARGETS.items():
        policy = ADMIN_ACTION_POLICIES[action_type]
        assert policy.category == "sensitive_read"
        assert policy.allowed_target_fields == frozenset({target_field})
        assert policy.required_target_rules[0].all_of == (target_field,)
        assert policy.metadata_builder_key == "none"
        assert not policy.allows_audit_note
        assert policy.allows_deleted_user_target == (
            action_type == "read_admin_money_user_detail"
        )


def test_single_read_commits_one_minimal_row_and_ordinary_writer_rejects_it() -> None:
    actor = _user("actor", role="admin")
    target = _user("target")
    _persist(actor, target)
    correlation_id = uuid.uuid4()
    with correlation_context(str(correlation_id)):
        action_id = record_financial_sensitive_read(
            authenticated_admin_id=actor.id,
            action_type="read_admin_money_user_detail",
            target_id=target.id,
        )
    with SessionLocal() as db:
        row = db.get(AdminAction, action_id)
        assert row is not None
        assert row.admin_user_id == actor.id
        assert row.target_user_id == target.id
        assert row.action_type == "read_admin_money_user_detail"
        assert row.outcome == "succeeded"
        assert row.reason is None and row.metadata_ is None
        assert row.correlation_id == correlation_id
        with pytest.raises(HTTPException) as exc:
            record_admin_action(
                db,
                admin_user_id=actor.id,
                action_type="read_admin_money_user_detail",
                outcome="succeeded",
                target_user_id=target.id,
            )
        assert exc.value.status_code == 400


def test_deleted_user_exception_is_narrow_and_deleted_actor_is_rejected() -> None:
    actor = _user("actor", role="admin")
    deleted_target = _user("deleted-target")
    deleted_target.deleted_at = datetime.now(timezone.utc)
    deleted_actor = _user("deleted-actor", role="admin")
    deleted_actor.deleted_at = datetime.now(timezone.utc)
    _persist(actor, deleted_target, deleted_actor)
    action_id = record_financial_sensitive_read(
        authenticated_admin_id=actor.id,
        action_type="read_admin_money_user_detail",
        target_id=deleted_target.id,
    )
    with SessionLocal() as db:
        assert db.get(AdminAction, action_id).target_user_id == deleted_target.id
    with pytest.raises(HTTPException) as exc:
        record_financial_sensitive_read(
            authenticated_admin_id=deleted_actor.id,
            action_type="read_admin_money_user_detail",
            target_id=deleted_target.id,
        )
    assert exc.value.status_code == 403


def test_missing_target_and_wrong_server_action_return_safe_503() -> None:
    actor = _user("actor", role="admin")
    _persist(actor)
    for action_type in ("read_admin_money_payment_detail", "not_a_read_policy"):
        with pytest.raises(HTTPException) as exc:
            record_financial_sensitive_read(
                authenticated_admin_id=actor.id,
                action_type=action_type,
                target_id=uuid.uuid4(),
            )
        assert exc.value.status_code == 503
        assert exc.value.detail == AUDIT_UNAVAILABLE_DETAIL


def test_read_policy_rejects_even_empty_metadata_and_extra_typed_targets() -> None:
    actor = _user("actor", role="admin")
    target = _user("target")
    _persist(actor, target)
    invalid_calls = (
        {"target_user_id": target.id, "metadata": {}},
        {"target_user_id": target.id, "target_game_id": uuid.uuid4()},
    )
    for invalid in invalid_calls:
        with pytest.raises(HTTPException) as exc:
            record_sensitive_admin_read(
                authenticated_admin_id=actor.id,
                action_type="read_admin_money_user_detail",
                **invalid,
            )
        assert exc.value.status_code == 400


def test_batch_commits_exact_selected_targets_with_one_correlation() -> None:
    actor = _user("actor", role="admin")
    payer = _user("payer")
    payments = [_payment(payer) for _ in range(3)]
    _persist(actor, payer, *payments)
    selected = [payment.id for payment in payments[:2]]
    correlation_id = uuid.uuid4()
    with correlation_context(str(correlation_id)):
        action_ids = record_sensitive_admin_read_batch(
            authenticated_admin_id=actor.id,
            action_type="read_staff_payment_list_item",
            target_ids=selected,
        )
    assert len(action_ids) == 2
    with SessionLocal() as db:
        rows = list(
            db.scalars(select(AdminAction).where(AdminAction.id.in_(action_ids)))
        )
        assert {row.target_payment_id for row in rows} == set(selected)
        assert {row.admin_user_id for row in rows} == {actor.id}
        assert {row.correlation_id for row in rows} == {correlation_id}
        assert all(row.reason is None and row.metadata_ is None for row in rows)
    assert not _rows_for(payments[2].id)


def test_batch_invalid_or_missing_target_is_atomic_and_safe() -> None:
    actor = _user("actor", role="admin")
    payer = _user("payer")
    payment = _payment(payer)
    _persist(actor, payer, payment)
    missing = uuid.uuid4()
    for selected in ([payment.id, missing], [payment.id, payment.id], []):
        with pytest.raises(HTTPException) as exc:
            record_sensitive_admin_read_batch(
                authenticated_admin_id=actor.id,
                action_type="read_staff_payment_list_item",
                target_ids=selected,
            )
        assert exc.value.status_code == 503
        assert exc.value.detail == AUDIT_UNAVAILABLE_DETAIL
    assert _rows_for(payment.id) == []


def test_batch_reloads_actor_and_rejects_stale_nonadmin() -> None:
    ordinary = _user("ordinary")
    payer = _user("payer")
    payment = _payment(payer)
    _persist(ordinary, payer, payment)
    with pytest.raises(HTTPException) as exc:
        record_sensitive_admin_read_batch(
            authenticated_admin_id=ordinary.id,
            action_type="read_staff_payment_list_item",
            target_ids=[payment.id],
        )
    assert exc.value.status_code == 403
    assert _rows_for(payment.id) == []


def test_uncertain_batch_commit_fails_closed_without_retry_or_schema_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import admin_action_service

    actor = _user("actor", role="admin")
    payer = _user("payer")
    payment = _payment(payer)
    _persist(actor, payer, payment)
    commits = 0

    @contextmanager
    def uncertain_session():
        nonlocal commits
        with SessionLocal() as db:
            real_commit = db.commit

            def uncertain_commit() -> None:
                nonlocal commits
                commits += 1
                real_commit()
                raise RuntimeError("private database schema and provider detail")

            monkeypatch.setattr(db, "commit", uncertain_commit)
            yield db

    monkeypatch.setattr(
        admin_action_service, "open_audit_session_or_503", uncertain_session
    )
    with pytest.raises(HTTPException) as exc:
        record_sensitive_admin_read_batch(
            authenticated_admin_id=actor.id,
            action_type="read_staff_payment_list_item",
            target_ids=[payment.id],
        )
    assert exc.value.status_code == 503
    assert exc.value.detail == AUDIT_UNAVAILABLE_DETAIL
    assert commits == 1
    rows = _rows_for(payment.id)
    assert len(rows) == 1


def test_disappearing_selected_row_after_commit_fails_closed_and_retains_audit() -> (
    None
):
    actor = _user("actor", role="admin")
    payer = _user("payer")
    payment = _payment(payer)
    _persist(actor, payer, payment)
    action_ids = record_sensitive_admin_read_batch(
        authenticated_admin_id=actor.id,
        action_type="read_staff_payment_list_item",
        target_ids=[payment.id],
    )
    with SessionLocal() as db:
        db.delete(db.get(Payment, payment.id))
        db.commit()
    with SessionLocal() as db, pytest.raises(HTTPException) as exc:
        load_frozen_audited_rows(db, model=Payment, target_ids=[payment.id])
    assert exc.value.status_code == 503
    assert exc.value.detail == AUDIT_UNAVAILABLE_DETAIL
    with SessionLocal() as db:
        assert db.get(AdminAction, action_ids[0]) is not None


def test_admin_money_payment_page_and_detail_emit_only_returned_read_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("admin", role="admin")
    payer = _user("payer")
    payments = [_payment(payer) for _ in range(2)]
    _persist(admin, payer, *payments)
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()

    first = client.get(
        "/admin/money/payments?limit=1",
        headers=_auth_headers("admin-token"),
    )
    assert first.status_code == 200, first.text
    page = first.json()
    assert len(page["items"]) == 1
    assert page["has_more"] is True
    assert page["next_cursor"]
    selected_id = uuid.UUID(page["items"][0]["id"])
    with SessionLocal() as db:
        actions = list(
            db.scalars(
                select(AdminAction).where(
                    AdminAction.action_type == "read_admin_money_payment_list_item",
                    AdminAction.target_payment_id.in_(
                        [payment.id for payment in payments]
                    ),
                )
            )
        )
        assert len(actions) == 1
        assert actions[0].target_payment_id == selected_id
        assert actions[0].admin_user_id == admin.id
        assert actions[0].reason is None and actions[0].metadata_ is None

    detail = client.get(
        f"/admin/money/payments/{selected_id}",
        headers=_auth_headers("admin-token"),
    )
    assert detail.status_code == 200, detail.text
    with SessionLocal() as db:
        detail_actions = list(
            db.scalars(
                select(AdminAction).where(
                    AdminAction.action_type == "read_admin_money_payment_detail",
                    AdminAction.target_payment_id == selected_id,
                )
            )
        )
        assert len(detail_actions) == 1
        assert detail_actions[0].admin_user_id == admin.id


def test_all_four_admin_money_collection_families_audit_exact_returned_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("admin-money-collections", role="admin")
    payer = _user("admin-money-collection-payer")
    _persist(admin, payer)
    game_id, _ = _persist_game_fixture(
        "ws09-02c-admin-money-collections", admin=admin, creator=payer
    )
    booking_id = _persist_paid_booking(
        game_id=game_id, buyer_user_id=payer.id, amount_cents=1200
    )
    _persist_money_repair_fixture(
        game_id=game_id,
        booking_id=booking_id,
        target_user_id=payer.id,
    )
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()

    routes = (
        (
            "/admin/money/issues?limit=100",
            "read_admin_money_issue_list_item",
            "target_money_issue_id",
        ),
        (
            "/admin/money/credits?limit=100",
            "read_admin_money_credit_list_item",
            "target_game_credit_id",
        ),
        (
            "/admin/money/payments?limit=100",
            "read_admin_money_payment_list_item",
            "target_payment_id",
        ),
        (
            "/admin/money/refunds?limit=100",
            "read_admin_money_refund_list_item",
            "target_refund_id",
        ),
    )
    for route, action_type, target_field in routes:
        response = client.get(route, headers=_auth_headers("admin-token"))
        assert response.status_code == 200, (route, response.text)
        returned_ids = {uuid.UUID(item["id"]) for item in response.json()["items"]}
        assert returned_ids
        rows = _action_rows(action_type)
        assert len(rows) == len(returned_ids)
        assert {getattr(row, target_field) for row in rows} == returned_ids
        assert {row.admin_user_id for row in rows} == {admin.id}
        assert len({row.correlation_id for row in rows}) == 1
        assert all(row.reason is None and row.metadata_ is None for row in rows)


def test_admin_money_detail_audit_failure_never_calls_protected_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import admin_money_sensitive_read_service

    admin = _user("admin", role="admin")
    payer = _user("payer")
    payment = _payment(payer)
    _persist(admin, payer, payment)
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    loader_called = False

    def forbidden_loader(*args: object, **kwargs: object) -> object:
        nonlocal loader_called
        loader_called = True
        raise AssertionError("protected loader ran before audit commit")

    def failed_audit(**kwargs: object) -> None:
        raise HTTPException(status_code=503, detail=AUDIT_UNAVAILABLE_DETAIL)

    monkeypatch.setattr(
        admin_money_sensitive_read_service,
        "get_admin_money_payment_detail",
        forbidden_loader,
    )
    monkeypatch.setattr(
        admin_money_sensitive_read_service,
        "record_financial_sensitive_read",
        failed_audit,
    )
    response = _client().get(
        f"/admin/money/payments/{payment.id}",
        headers=_auth_headers("admin-token"),
    )
    assert response.status_code == 503
    assert response.json()["detail"] == AUDIT_UNAVAILABLE_DETAIL
    assert not loader_called


def test_new_read_audit_list_and_detail_display_only_an_id_without_payment_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("admin", role="admin")
    payer = _user("payer")
    payment = _payment(payer)
    payment.failure_message = "private payment failure narrative"
    _persist(admin, payer, payment)
    action_id = record_financial_sensitive_read(
        authenticated_admin_id=admin.id,
        action_type="read_admin_money_payment_detail",
        target_id=payment.id,
    )
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    statements: list[str] = []

    def capture_statement(conn, cursor, statement, parameters, context, executemany):
        del conn, cursor, parameters, context, executemany
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture_statement)
    try:
        detail = _client().get(
            f"/admin/actions/{action_id}",
            headers=_auth_headers("admin-token"),
        )
        listing = _client().get(
            "/admin/actions/log?action_type=read_admin_money_payment_detail",
            headers=_auth_headers("admin-token"),
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture_statement)
    assert detail.status_code == 200, detail.text
    assert listing.status_code == 200, listing.text
    target = detail.json()["primary_target"]
    assert target["label"] == f"Payment {payment.id}"
    assert target["destination_path"] == f"/admin/money/payments/{payment.id}"
    assert detail.json()["action_label"] == "Admin money payment detail viewed"
    assert "private payment failure narrative" not in detail.text + listing.text
    assert all("FROM payments" not in statement for statement in statements)


def test_admin_waitlist_200_item_page_commits_200_typed_actions_in_one_batch() -> None:
    from backend.services.waitlist_entry_service import list_waitlist_entries

    admin = _user("admin", role="admin")
    owner = _user("owner")
    _persist(admin, owner)
    game_id, _venue_id = _persist_game_fixture(
        "ws09-02c-waitlist", admin=admin, creator=owner
    )
    entries = [
        WaitlistEntry(
            id=uuid.uuid4(),
            game_id=game_id,
            user_id=owner.id,
            position=index,
            waitlist_status="removed",
        )
        for index in range(1, 201)
    ]
    entry_ids_ordered = [row.id for row in entries]
    entry_ids = set(entry_ids_ordered)
    with SessionLocal() as db:
        db.add_all(entries)
        db.commit()
    full_correlation = uuid.uuid4()
    first_correlation = uuid.uuid4()
    with SessionLocal() as db:
        with correlation_context(str(full_correlation)):
            returned = list_waitlist_entries(
                db,
                authenticated_admin_id=admin.id,
                game_id=game_id,
                limit=200,
                offset=0,
            )
        assert [row.position for row in returned] == list(range(1, 201))
        with correlation_context(str(first_correlation)):
            first = list_waitlist_entries(
                db,
                authenticated_admin_id=admin.id,
                game_id=game_id,
                limit=101,
                offset=0,
            )
        assert [row.position for row in first] == list(range(1, 102))
    with SessionLocal() as db:
        actions = list(
            db.scalars(
                select(AdminAction).where(
                    AdminAction.action_type == "read_staff_waitlist_entry_list_item",
                    AdminAction.target_waitlist_entry_id.in_(entry_ids),
                )
            )
        )
        assert len(actions) == 301
        assert {row.target_waitlist_entry_id for row in actions} == entry_ids
        assert sum(row.correlation_id == full_correlation for row in actions) == 200
        assert sum(row.correlation_id == first_correlation for row in actions) == 101
        assert all(row.reason is None and row.metadata_ is None for row in actions)
    with pytest.raises(HTTPException) as exc:
        record_sensitive_admin_read_batch(
            authenticated_admin_id=admin.id,
            action_type="read_staff_waitlist_entry_list_item",
            target_ids=[*entry_ids_ordered[:199], uuid.uuid4()],
        )
    assert exc.value.status_code == 503
    assert exc.value.detail == AUDIT_UNAVAILABLE_DETAIL
    with SessionLocal() as db:
        count_after_failure = list(
            db.scalars(
                select(AdminAction.id).where(
                    AdminAction.action_type == "read_staff_waitlist_entry_list_item",
                    AdminAction.target_waitlist_entry_id.in_(entry_ids),
                )
            )
        )
        assert len(count_after_failure) == 301


def test_admin_host_fee_101_and_200_item_pages_preserve_batch_bounds() -> None:
    from backend.services.host_publish_fee_service import list_host_publish_fee_records

    admin = _user("admin", role="admin")
    host = _user("host")
    _persist(admin, host)
    with SessionLocal() as db:
        venue = _venue("ws09-02c-fee-pages", creator_id=host.id, admin_id=admin.id)
        db.add(venue)
        db.flush()
        games = [
            _community_game(
                f"ws09-02c-fee-{index}",
                venue=venue,
                host_user_id=host.id,
                creator_id=host.id,
            )
            for index in range(200)
        ]
        for game in games:
            game.game_status = "completed"
            game.completed_at = datetime.now(timezone.utc)
            game.completed_by_user_id = admin.id
        db.add_all(games)
        db.flush()
        fees = [
            HostPublishFee(
                id=uuid.uuid4(),
                game_id=game.id,
                host_user_id=host.id,
                amount_cents=500,
                currency="USD",
                fee_status="pending",
                waiver_reason="none",
            )
            for game in games
        ]
        fee_ids = {fee.id for fee in fees}
        db.add_all(fees)
        db.commit()
    with SessionLocal() as db:
        first_correlation = uuid.uuid4()
        full_correlation = uuid.uuid4()
        with correlation_context(str(first_correlation)):
            first = list_host_publish_fee_records(
                db, authenticated_admin_id=admin.id, host_user_id=host.id, limit=101
            )
        assert len(first) == 101
        first_ids = {fee.id for fee in first}
        with correlation_context(str(full_correlation)):
            full = list_host_publish_fee_records(
                db, authenticated_admin_id=admin.id, host_user_id=host.id, limit=200
            )
        assert len(full) == 200
        assert {fee.id for fee in full} == fee_ids
        assert first_ids <= fee_ids
    with SessionLocal() as db:
        actions = list(
            db.scalars(
                select(AdminAction).where(
                    AdminAction.action_type == "read_staff_host_publish_fee_list_item",
                    AdminAction.target_host_publish_fee_id.in_(fee_ids),
                )
            )
        )
        assert len(actions) == 301
        assert (
            sum(action.correlation_id == first_correlation for action in actions) == 101
        )
        assert (
            sum(action.correlation_id == full_correlation for action in actions) == 200
        )
        assert all(action.admin_user_id == admin.id for action in actions)
        assert all(
            action.reason is None and action.metadata_ is None for action in actions
        )


def test_admin_money_user_invalid_cursor_is_rejected_before_audit_and_deleted_user_is_retained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("admin", role="admin")
    deleted_target = _user("deleted-target")
    deleted_target.deleted_at = datetime.now(timezone.utc)
    _persist(admin, deleted_target)
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()
    invalid = client.get(
        f"/admin/money/users/{deleted_target.id}?saved_cards_cursor=not-a-cursor",
        headers=_auth_headers("admin-token"),
    )
    assert invalid.status_code == 400
    with SessionLocal() as db:
        assert not list(
            db.scalars(
                select(AdminAction).where(
                    AdminAction.action_type == "read_admin_money_user_detail",
                    AdminAction.target_user_id == deleted_target.id,
                )
            )
        )
    retained = client.get(
        f"/admin/money/users/{deleted_target.id}",
        headers=_auth_headers("admin-token"),
    )
    assert retained.status_code == 200, retained.text
    with SessionLocal() as db:
        actions = list(
            db.scalars(
                select(AdminAction).where(
                    AdminAction.action_type == "read_admin_money_user_detail",
                    AdminAction.target_user_id == deleted_target.id,
                )
            )
        )
        assert len(actions) == 1


def test_removal_preview_rejects_wrong_parent_before_sensitive_audit() -> None:
    from backend.services.admin_game_sensitive_read_service import (
        read_official_game_removal_preview,
    )

    admin = _user("admin", role="admin")
    player = _user("player")
    _persist(admin, player)
    first_game_id, _ = _persist_game_fixture(
        "ws09-02c-parent-one", admin=admin, creator=player
    )
    second_game_id, _ = _persist_game_fixture(
        "ws09-02c-parent-two", admin=admin, creator=player
    )
    participant_id = uuid.uuid4()
    with SessionLocal() as db:
        db.add(
            GameParticipant(
                id=participant_id,
                game_id=first_game_id,
                participant_type="registered_user",
                user_id=player.id,
                display_name_snapshot="Player",
                participant_status="pending_payment",
                price_cents=500,
                currency="USD",
            )
        )
        db.commit()
    with SessionLocal() as db, pytest.raises(HTTPException) as exc:
        read_official_game_removal_preview(
            db,
            admin=admin,
            game_id=second_game_id,
            participant_id=participant_id,
        )
    assert exc.value.status_code == 404
    with SessionLocal() as db:
        assert not list(
            db.scalars(
                select(AdminAction).where(
                    AdminAction.action_type
                    == "read_admin_official_game_remove_preview",
                    AdminAction.target_participant_id == participant_id,
                )
            )
        )


def test_empty_official_game_financial_views_each_commit_one_game_bound_read() -> None:
    from backend.services.admin_game_sensitive_read_service import (
        read_official_game_bookings,
        read_official_game_money,
        read_official_game_waitlist,
    )

    admin = _user("admin", role="admin")
    creator = _user("creator")
    _persist(admin, creator)
    game_id, _ = _persist_game_fixture(
        "ws09-02c-empty-official", admin=admin, creator=creator
    )
    with SessionLocal() as db:
        assert (
            read_official_game_bookings(
                db, admin=admin, game_id=game_id, limit=20, offset=0
            )
            == []
        )
        assert (
            read_official_game_waitlist(
                db, admin=admin, game_id=game_id, limit=20, offset=0
            )
            == []
        )
        assert read_official_game_money(db, admin=admin, game_id=game_id) is not None
    expected = {
        "read_admin_official_game_bookings",
        "read_admin_official_game_waitlist",
        "read_admin_official_game_money",
    }
    with SessionLocal() as db:
        actions = list(
            db.scalars(
                select(AdminAction).where(
                    AdminAction.target_game_id == game_id,
                    AdminAction.action_type.in_(expected),
                )
            )
        )
        assert {row.action_type for row in actions} == expected
        assert len(actions) == 3
        assert all(row.admin_user_id == admin.id for row in actions)
        assert all(row.reason is None and row.metadata_ is None for row in actions)


def test_embedded_payment_refund_and_credit_histories_exclude_reads_before_limit() -> (
    None
):
    from backend.services.admin_money_credit_service import list_credit_audit_actions
    from backend.services.admin_money_payment_service import list_payment_audit_actions
    from backend.services.admin_money_refund_query_service import (
        list_refund_admin_activity,
    )

    admin = _user("admin", role="admin")
    payer = _user("payer")
    _persist(admin, payer)
    game_id, _ = _persist_game_fixture("ws09-02c-history", admin=admin, creator=payer)
    booking_id = _persist_paid_booking(
        game_id=game_id, buyer_user_id=payer.id, amount_cents=1200
    )
    fixture = _persist_money_repair_fixture(
        game_id=game_id, booking_id=booking_id, target_user_id=payer.id
    )
    payment_id = fixture["payment_id"]
    refund_id = fixture["retry_refund_id"]
    credit_id = fixture["credit_id"]
    issue_id = fixture["resolve_issue_id"]
    old_ids = {kind: uuid.uuid4() for kind in ("payment", "refund", "credit")}
    with SessionLocal() as db:
        db.add_all(
            [
                AdminAction(
                    id=old_ids["payment"],
                    admin_user_id=admin.id,
                    action_type="create_payment",
                    outcome="succeeded",
                    correlation_id=uuid.uuid4(),
                    target_payment_id=payment_id,
                ),
                AdminAction(
                    id=old_ids["refund"],
                    admin_user_id=admin.id,
                    action_type="create_refund",
                    outcome="succeeded",
                    correlation_id=uuid.uuid4(),
                    target_refund_id=refund_id,
                ),
                AdminAction(
                    id=old_ids["credit"],
                    admin_user_id=admin.id,
                    action_type="issue_credit",
                    outcome="succeeded",
                    correlation_id=uuid.uuid4(),
                    target_game_credit_id=credit_id,
                ),
            ]
        )
        db.commit()
        db.add_all(
            [
                AdminAction(
                    id=uuid.uuid4(),
                    admin_user_id=admin.id,
                    action_type=action_type,
                    outcome="succeeded",
                    correlation_id=uuid.uuid4(),
                    **{target_field: target_id},
                )
                for action_type, target_field, target_id in (
                    (
                        "read_admin_money_payment_detail",
                        "target_payment_id",
                        payment_id,
                    ),
                    (
                        "read_admin_money_credit_detail",
                        "target_game_credit_id",
                        credit_id,
                    ),
                    (
                        "read_admin_money_issue_detail",
                        "target_money_issue_id",
                        issue_id,
                    ),
                )
                for _ in range(101)
            ]
        )
        db.commit()
        payment = db.get(Payment, payment_id)
        refund = db.get(Refund, refund_id)
        credit = db.get(GameCredit, credit_id)
        issue = db.get(MoneyIssue, issue_id)
        payment_history = list_payment_audit_actions(
            db,
            viewer_user=admin,
            payment=payment,
            booking_id=booking_id,
            refunds=[refund],
            credit_grants=[credit],
            money_issues=[issue],
        )
        refund_history = list_refund_admin_activity(
            db,
            viewer_user=admin,
            refund=refund,
            linked_money_issue=issue,
        )
        credit_history = list_credit_audit_actions(
            db,
            viewer_user=admin,
            credit=credit,
            credit_usages=[],
        )
        assert old_ids["payment"] in {row.id for row in payment_history}
        assert old_ids["refund"] in {row.id for row in refund_history}
        assert old_ids["credit"] in {row.id for row in credit_history}
        assert not any(
            row.action_type in SENSITIVE_FINANCIAL_READ_TARGETS
            for row in refund_history
        )


def test_all_seven_admin_money_detail_and_history_routes_record_exactly_one_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("admin", role="admin")
    payer = _user("payer")
    _persist(admin, payer)
    game_id, _ = _persist_game_fixture(
        "ws09-02c-money-details", admin=admin, creator=payer
    )
    booking_id = _persist_paid_booking(
        game_id=game_id, buyer_user_id=payer.id, amount_cents=1200
    )
    fixture = _persist_money_repair_fixture(
        game_id=game_id, booking_id=booking_id, target_user_id=payer.id
    )
    outcome_id = uuid.uuid4()
    with SessionLocal() as db:
        db.add(
            AdminFinancialOutcome(
                id=outcome_id,
                target_game_id=game_id,
                host_user_id=payer.id,
                outcome="manual_review",
                applied_status="pending",
                amount_cents=0,
                currency="USD",
                reason="Local test outcome",
                created_by_user_id=admin.id,
            )
        )
        db.commit()
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()
    routes = (
        (
            f"/admin/money/financial-outcomes/{outcome_id}",
            "read_admin_money_financial_outcome_detail",
            "target_financial_outcome_id",
            outcome_id,
        ),
        (
            f"/admin/money/users/{payer.id}",
            "read_admin_money_user_detail",
            "target_user_id",
            payer.id,
        ),
        (
            f"/admin/money/issues/{fixture['resolve_issue_id']}",
            "read_admin_money_issue_detail",
            "target_money_issue_id",
            fixture["resolve_issue_id"],
        ),
        (
            f"/admin/money/credits/{fixture['credit_id']}",
            "read_admin_money_credit_detail",
            "target_game_credit_id",
            fixture["credit_id"],
        ),
        (
            f"/admin/money/payments/{fixture['payment_id']}",
            "read_admin_money_payment_detail",
            "target_payment_id",
            fixture["payment_id"],
        ),
        (
            f"/admin/money/refunds/{fixture['retry_refund_id']}",
            "read_admin_money_refund_detail",
            "target_refund_id",
            fixture["retry_refund_id"],
        ),
        (
            f"/admin/money/refunds/{fixture['retry_refund_id']}/events",
            "read_admin_money_refund_events",
            "target_refund_id",
            fixture["retry_refund_id"],
        ),
    )
    for route, action_type, target_field, target_id in routes:
        response = client.get(route, headers=_auth_headers("admin-token"))
        assert response.status_code == 200, (route, response.text)
        with SessionLocal() as db:
            rows = list(
                db.scalars(
                    select(AdminAction).where(
                        AdminAction.action_type == action_type,
                        getattr(AdminAction, target_field) == target_id,
                    )
                )
            )
            assert len(rows) == 1, action_type
            assert rows[0].admin_user_id == admin.id
            assert rows[0].outcome == "succeeded"
            assert rows[0].correlation_id is not None
            assert rows[0].reason is None and rows[0].metadata_ is None


def test_all_new_action_display_rules_are_explicit_id_only_and_never_collect_targets() -> (
    None
):
    from backend.services.admin_action_display_service import (
        ACTION_DISPLAY_RULES,
        collect_primary_target_ids,
        primary_target_summary,
    )

    actions: list[AdminAction] = []
    for action_type, target_field in SENSITIVE_FINANCIAL_READ_TARGETS.items():
        target_id = uuid.uuid4()
        action = AdminAction(
            id=uuid.uuid4(),
            admin_user_id=uuid.uuid4(),
            action_type=action_type,
            outcome="succeeded",
            correlation_id=uuid.uuid4(),
            **{target_field: target_id},
        )
        rule = ACTION_DISPLAY_RULES[action_type]
        assert rule.action_type == action_type
        assert rule.label.strip()
        assert len(rule.primary_targets) == 1
        assert rule.primary_targets[0].field_name == target_field
        summary = primary_target_summary(action, {})
        assert summary is not None
        assert summary.target_id == target_id
        assert str(target_id) in summary.label
        actions.append(action)

    assert collect_primary_target_ids(actions) == {}


def test_all_generic_staff_detail_and_collection_routes_emit_exact_actions_and_own_reads_do_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("generic-admin", role="admin")
    owner = _user("generic-owner")
    _persist(admin, owner)
    fixture = _persist_cross_user_fixture(admin=admin, owner=owner)
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "owner-token": owner},
    )
    client = _client()

    detail_routes = (
        (
            f"/payments/{fixture['payment_id']}",
            "read_staff_payment_detail",
            "target_payment_id",
            fixture["payment_id"],
        ),
        (
            f"/refunds/{fixture['refund_id']}",
            "read_staff_refund_detail",
            "target_refund_id",
            fixture["refund_id"],
        ),
        (
            f"/bookings/{fixture['booking_id']}",
            "read_staff_booking_detail",
            "target_booking_id",
            fixture["booking_id"],
        ),
        (
            f"/waitlist-entries/{fixture['waitlist_entry_id']}",
            "read_staff_waitlist_entry_detail",
            "target_waitlist_entry_id",
            fixture["waitlist_entry_id"],
        ),
        (
            f"/host-publish-fees/{fixture['host_fee_id']}",
            "read_staff_host_publish_fee_detail",
            "target_host_publish_fee_id",
            fixture["host_fee_id"],
        ),
        (
            f"/checkout/bookings/{fixture['booking_id']}/status",
            "read_staff_checkout_status",
            "target_booking_id",
            fixture["booking_id"],
        ),
    )
    for route, action_type, target_field, target_id in detail_routes:
        response = client.get(route, headers=_auth_headers("admin-token"))
        assert response.status_code == 200, (route, response.text)
        _assert_one_action(
            action_type,
            actor_id=admin.id,
            target_field=target_field,
            target_id=target_id,
        )

    collection_routes = (
        ("/payments?limit=100", "read_staff_payment_list_item", "target_payment_id"),
        ("/refunds?limit=100", "read_staff_refund_list_item", "target_refund_id"),
        ("/bookings?limit=100", "read_staff_booking_list_item", "target_booking_id"),
        (
            f"/game-credits?user_id={owner.id}&limit=100",
            "read_staff_game_credit_list_item",
            "target_game_credit_id",
        ),
        (
            "/waitlist-entries?limit=200",
            "read_staff_waitlist_entry_list_item",
            "target_waitlist_entry_id",
        ),
        (
            "/host-publish-fees?limit=200",
            "read_staff_host_publish_fee_list_item",
            "target_host_publish_fee_id",
        ),
    )
    for route, action_type, target_field in collection_routes:
        response = client.get(route, headers=_auth_headers("admin-token"))
        assert response.status_code == 200, (route, response.text)
        returned_ids = {uuid.UUID(item["id"]) for item in response.json()}
        rows = _action_rows(action_type)
        assert len(rows) == len(returned_ids)
        assert {getattr(row, target_field) for row in rows} == returned_ids
        assert {row.admin_user_id for row in rows} == {admin.id}
        assert len({row.correlation_id for row in rows}) == (1 if rows else 0)
        assert all(row.reason is None and row.metadata_ is None for row in rows)

    before_own_reads = {
        name: len(_action_rows(name))
        for name in SENSITIVE_FINANCIAL_READ_TARGETS
        if name.startswith("read_staff_")
    }
    own_routes = (
        f"/payments/{fixture['payment_id']}",
        f"/refunds/{fixture['refund_id']}",
        f"/bookings/{fixture['booking_id']}",
        f"/waitlist-entries/{fixture['waitlist_entry_id']}",
        f"/checkout/bookings/{fixture['booking_id']}/status",
        "/payments",
        "/refunds",
        "/bookings",
        "/game-credits",
        "/host-publish-fees/me",
        "/waitlist-entries/me",
    )
    for route in own_routes:
        response = client.get(route, headers=_auth_headers("owner-token"))
        assert response.status_code == 200, (route, response.text)
    assert {
        name: len(_action_rows(name)) for name in before_own_reads
    } == before_own_reads


def test_all_ten_sensitive_collections_return_empty_without_audit_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("empty-collection-admin", role="admin")
    _persist(admin)
    missing_user_id = uuid.uuid4()
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()

    routes = (
        f"/admin/money/issues?user_id={missing_user_id}&limit=100",
        f"/admin/money/credits?user_id={missing_user_id}&limit=100",
        f"/admin/money/payments?user_id={missing_user_id}&limit=100",
        f"/admin/money/refunds?user_id={missing_user_id}&limit=100",
        f"/payments?payer_user_id={missing_user_id}&limit=100",
        f"/refunds?requested_by_user_id={missing_user_id}&limit=100",
        f"/game-credits?user_id={missing_user_id}&limit=100",
        f"/bookings?buyer_user_id={missing_user_id}&limit=100",
        f"/waitlist-entries?user_id={missing_user_id}&limit=200",
        f"/host-publish-fees?host_user_id={missing_user_id}&limit=200",
    )
    for route in routes:
        response = client.get(route, headers=_auth_headers("admin-token"))
        assert response.status_code == 200, (route, response.text)
        body = response.json()
        assert (body["items"] if isinstance(body, dict) else body) == [], route

    with SessionLocal() as db:
        assert not list(
            db.scalars(
                select(AdminAction).where(
                    AdminAction.action_type.in_(SENSITIVE_READ_LIST_LIMITS)
                )
            )
        )


def test_all_ten_sensitive_collections_fail_before_protected_hydration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import (
        admin_money_credit_service,
        admin_money_issue_query_service,
        admin_money_payment_service,
        admin_money_refund_query_service,
        booking_service,
        game_credit_service,
        host_publish_fee_service,
        payment_service,
        refund_service,
        waitlist_entry_service,
    )

    admin = _user("collection-order-admin", role="admin")
    owner = _user("collection-order-owner")
    _persist(admin, owner)
    _persist_cross_user_fixture(admin=admin, owner=owner)
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()
    calls: list[tuple[str, tuple[uuid.UUID, ...]]] = []

    def audit_unavailable(
        *, action_type: str, target_ids: list[uuid.UUID], **_: object
    ) -> None:
        calls.append((action_type, tuple(target_ids)))
        raise HTTPException(status_code=503, detail=AUDIT_UNAVAILABLE_DETAIL)

    modules = (
        admin_money_issue_query_service,
        admin_money_credit_service,
        admin_money_payment_service,
        admin_money_refund_query_service,
        payment_service,
        refund_service,
        game_credit_service,
        booking_service,
        waitlist_entry_service,
        host_publish_fee_service,
    )
    for module in modules:
        monkeypatch.setattr(
            module,
            "record_sensitive_admin_read_batch",
            audit_unavailable,
        )

    cases = (
        (
            "/admin/money/issues?limit=100",
            "read_admin_money_issue_list_item",
            "money_issues",
            "money_issues.latest_summary",
        ),
        (
            "/admin/money/credits?limit=100",
            "read_admin_money_credit_list_item",
            "game_credits",
            "game_credits.amount_cents",
        ),
        (
            "/admin/money/payments?limit=100",
            "read_admin_money_payment_list_item",
            "payments",
            "payments.amount_cents",
        ),
        (
            "/admin/money/refunds?limit=100",
            "read_admin_money_refund_list_item",
            "refunds",
            "refunds.amount_cents",
        ),
        (
            "/payments?limit=100",
            "read_staff_payment_list_item",
            "payments",
            "payments.amount_cents",
        ),
        (
            "/refunds?limit=100",
            "read_staff_refund_list_item",
            "refunds",
            "refunds.amount_cents",
        ),
        (
            f"/game-credits?user_id={owner.id}&limit=100",
            "read_staff_game_credit_list_item",
            "game_credits",
            "game_credits.amount_cents",
        ),
        (
            "/bookings?limit=100",
            "read_staff_booking_list_item",
            "bookings",
            "bookings.total_cents",
        ),
        (
            "/waitlist-entries?limit=200",
            "read_staff_waitlist_entry_list_item",
            "waitlist_entries",
            "waitlist_entries.payment_method_last4",
        ),
        (
            "/host-publish-fees?limit=200",
            "read_staff_host_publish_fee_list_item",
            "host_publish_fees",
            "host_publish_fees.amount_cents",
        ),
    )
    statements: list[str] = []

    def capture_statement(
        _conn: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: object,
    ) -> None:
        statements.append(" ".join(statement.lower().split()))

    event.listen(engine, "before_cursor_execute", capture_statement)
    try:
        for route, action_type, table_name, protected_column in cases:
            calls.clear()
            statements.clear()
            response = client.get(route, headers=_auth_headers("admin-token"))
            assert response.status_code == 503, (route, response.text)
            assert response.json()["detail"] == AUDIT_UNAVAILABLE_DETAIL
            assert len(calls) == 1 and calls[0][0] == action_type, route
            assert calls[0][1], route
            target_selects = [
                statement
                for statement in statements
                if statement.startswith("select ")
                and f" from {table_name}" in statement
            ]
            assert target_selects, route
            assert all(
                protected_column not in statement for statement in target_selects
            ), (route, target_selects)
    finally:
        event.remove(engine, "before_cursor_execute", capture_statement)


def test_expired_checkout_admin_read_audits_before_normal_expiration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state, admin, _owner = _persist_expired_checkout_state()
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})

    response = _client().get(
        f"/checkout/bookings/{state.booking_id}/status",
        headers=_auth_headers("admin-token"),
    )

    assert response.status_code == 200, response.text
    assert response.json()["booking_status"] == "expired"
    with SessionLocal() as db:
        booking = db.get(Booking, state.booking_id)
        assert booking is not None
        assert (booking.booking_status, booking.reservation_status) == (
            "expired",
            "released",
        )
        assert booking.expires_at is None
    rows = _checkout_action_rows(state.booking_id)
    assert len(rows) == 1 and rows[0].admin_user_id == admin.id


def test_expired_checkout_audit_failure_discloses_nothing_and_does_not_expire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import checkout_service

    state, admin, _owner = _persist_expired_checkout_state()
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})

    def audit_unavailable(**_: object) -> None:
        raise HTTPException(status_code=503, detail=AUDIT_UNAVAILABLE_DETAIL)

    monkeypatch.setattr(
        checkout_service,
        "record_financial_sensitive_read",
        audit_unavailable,
    )
    response = _client().get(
        f"/checkout/bookings/{state.booking_id}/status",
        headers=_auth_headers("admin-token"),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == AUDIT_UNAVAILABLE_DETAIL
    with SessionLocal() as db:
        booking = db.get(Booking, state.booking_id)
        assert booking is not None
        assert (booking.booking_status, booking.reservation_status) == (
            "pending_payment",
            "held",
        )
        assert booking.expires_at is not None
    assert _checkout_action_rows(state.booking_id) == []


def test_expired_checkout_failure_after_audit_keeps_audit_and_rolls_back_expiration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import checkout_service

    state, admin, _owner = _persist_expired_checkout_state()
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})

    def expiration_unavailable(*_: object, **__: object) -> None:
        raise HTTPException(status_code=503, detail="Checkout status is unavailable.")

    monkeypatch.setattr(
        checkout_service,
        "expire_stale_pending_checkouts",
        expiration_unavailable,
    )
    response = _client().get(
        f"/checkout/bookings/{state.booking_id}/status",
        headers=_auth_headers("admin-token"),
    )

    assert response.status_code == 503
    with SessionLocal() as db:
        booking = db.get(Booking, state.booking_id)
        assert booking is not None
        assert (booking.booking_status, booking.reservation_status) == (
            "pending_payment",
            "held",
        )
    assert len(_checkout_action_rows(state.booking_id)) == 1


def test_expired_checkout_response_failure_keeps_audit_and_committed_expiration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import checkout_service

    state, admin, _owner = _persist_expired_checkout_state()
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})

    def response_unavailable(*_: object, **__: object) -> None:
        raise HTTPException(status_code=503, detail="Checkout status is unavailable.")

    monkeypatch.setattr(
        checkout_service,
        "get_credit_application_for_booking",
        response_unavailable,
    )
    response = _client().get(
        f"/checkout/bookings/{state.booking_id}/status",
        headers=_auth_headers("admin-token"),
    )

    assert response.status_code == 503
    with SessionLocal() as db:
        booking = db.get(Booking, state.booking_id)
        assert booking is not None
        assert (booking.booking_status, booking.reservation_status) == (
            "expired",
            "released",
        )
    assert len(_checkout_action_rows(state.booking_id)) == 1


def test_expired_checkout_owner_path_stays_unaudited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state, _admin, owner = _persist_expired_checkout_state()
    _install_tokens_for_users(monkeypatch, {"owner-token": owner})

    response = _client().get(
        f"/checkout/bookings/{state.booking_id}/status",
        headers=_auth_headers("owner-token"),
    )

    assert response.status_code == 200, response.text
    assert response.json()["booking_status"] == "expired"
    assert _checkout_action_rows(state.booking_id) == []


def test_remaining_game_bound_routes_emit_exact_actions_before_calculation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("game-bound-admin", role="admin")
    host = _user("game-bound-host")
    _persist(admin, host)
    official_game_id, _ = _persist_game_fixture(
        "ws09-02c-preview", admin=admin, creator=host
    )
    community_game_id, _ = _persist_community_game_fixture(
        "ws09-02c-admin-community", admin=admin, host=host
    )
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()

    cancellation = client.post(
        f"/admin/official-games/{official_game_id}/cancel-preview",
        headers=_auth_headers("admin-token"),
    )
    assert cancellation.status_code == 200, cancellation.text
    _assert_one_action(
        "read_admin_official_game_cancel_preview",
        actor_id=admin.id,
        target_field="target_game_id",
        target_id=official_game_id,
    )

    community = client.get(
        f"/admin/community-games/{community_game_id}",
        headers=_auth_headers("admin-token"),
    )
    assert community.status_code == 200, community.text
    _assert_one_action(
        "read_admin_community_game_payment_detail",
        actor_id=admin.id,
        target_field="target_game_id",
        target_id=community_game_id,
    )


def test_hidden_community_detail_and_filtered_list_audit_admin_but_not_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import Game

    admin = _user("hidden-admin", role="admin")
    host = _user("hidden-host")
    _persist(admin, host)
    game_id, _ = _persist_community_game_fixture(
        "ws09-02c-hidden", admin=admin, host=host
    )
    with SessionLocal() as db:
        game = db.get(Game, game_id)
        game.public_visibility_status = "hidden"
        detail_id = db.scalar(
            select(CommunityGameDetail.id).where(CommunityGameDetail.game_id == game_id)
        )
        db.commit()
    assert detail_id is not None
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "host-token": host},
    )
    client = _client()

    for token in ("host-token", "admin-token"):
        detail = client.get(
            f"/community-game-details/{detail_id}",
            headers=_auth_headers(token),
        )
        listing = client.get(
            f"/community-game-details?game_id={game_id}",
            headers=_auth_headers(token),
        )
        assert detail.status_code == 200, detail.text
        assert listing.status_code == 200, listing.text
        assert detail.headers["Cache-Control"] == "private, no-store"
        assert listing.headers["Cache-Control"] == "private, no-store"

    _assert_one_action(
        "read_staff_hidden_community_payment_detail",
        actor_id=admin.id,
        target_field="target_game_id",
        target_id=game_id,
    )
    _assert_one_action(
        "read_staff_hidden_community_payment_list",
        actor_id=admin.id,
        target_field="target_game_id",
        target_id=game_id,
    )


def test_hidden_community_invalid_targets_never_disclose_or_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("hidden-invalid-admin", role="admin")
    wrong_kind_host = _user("hidden-wrong-kind-host")
    deleted_host = _user("hidden-deleted-host")
    _persist(admin, wrong_kind_host, deleted_host)
    wrong_kind_game_id, _ = _persist_game_fixture(
        "ws09-02c-wrong-kind", admin=admin, creator=wrong_kind_host
    )
    deleted_game_id, _ = _persist_community_game_fixture(
        "ws09-02c-deleted", admin=admin, host=deleted_host
    )
    with SessionLocal() as db:
        wrong_kind_game = db.get(Game, wrong_kind_game_id)
        deleted_game = db.get(Game, deleted_game_id)
        assert wrong_kind_game is not None and deleted_game is not None
        wrong_kind_detail = CommunityGameDetail(
            id=uuid.uuid4(),
            game_id=wrong_kind_game_id,
            payment_methods_snapshot=[],
            payment_instructions_snapshot=None,
        )
        db.add(wrong_kind_detail)
        deleted_game.deleted_at = datetime.now(timezone.utc)
        wrong_kind_detail_id = wrong_kind_detail.id
        deleted_detail_id = db.scalar(
            select(CommunityGameDetail.id).where(
                CommunityGameDetail.game_id == deleted_game_id
            )
        )
        db.commit()
    assert wrong_kind_detail_id is not None and deleted_detail_id is not None
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()

    routes = (
        f"/community-game-details/{uuid.uuid4()}",
        f"/community-game-details/{wrong_kind_detail_id}",
        f"/community-game-details/{deleted_detail_id}",
        f"/community-game-details?game_id={uuid.uuid4()}",
        f"/community-game-details?game_id={wrong_kind_game_id}",
        f"/community-game-details?game_id={deleted_game_id}",
    )
    for route in routes:
        response = client.get(route, headers=_auth_headers("admin-token"))
        assert response.status_code == 404, (route, response.text)
        assert response.json()["detail"] == "Community game details not found."
        assert "payment_methods_snapshot" not in response.text
        assert "payment_instructions_snapshot" not in response.text

    assert _action_rows("read_staff_hidden_community_payment_detail") == []
    assert _action_rows("read_staff_hidden_community_payment_list") == []


def test_hidden_filtered_empty_page_audits_once_and_unfiltered_list_excludes_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("hidden-list-admin", role="admin")
    empty_host = _user("hidden-empty-host")
    hidden_host = _user("hidden-populated-host")
    visible_host = _user("visible-list-host")
    _persist(admin, empty_host, hidden_host, visible_host)
    hidden_game_id, _ = _persist_community_game_fixture(
        "ws09-02c-hidden-empty", admin=admin, host=empty_host
    )
    hidden_populated_game_id, _ = _persist_community_game_fixture(
        "ws09-02c-hidden-populated", admin=admin, host=hidden_host
    )
    visible_game_id, _ = _persist_community_game_fixture(
        "ws09-02c-visible-list", admin=admin, host=visible_host
    )
    with SessionLocal() as db:
        hidden_game = db.get(Game, hidden_game_id)
        hidden_detail = db.scalar(
            select(CommunityGameDetail).where(
                CommunityGameDetail.game_id == hidden_game_id
            )
        )
        visible_detail_id = db.scalar(
            select(CommunityGameDetail.id).where(
                CommunityGameDetail.game_id == visible_game_id
            )
        )
        hidden_populated_game = db.get(Game, hidden_populated_game_id)
        hidden_populated_detail_id = db.scalar(
            select(CommunityGameDetail.id).where(
                CommunityGameDetail.game_id == hidden_populated_game_id
            )
        )
        assert hidden_game is not None and hidden_detail is not None
        assert hidden_populated_game is not None
        assert hidden_populated_detail_id is not None and visible_detail_id is not None
        hidden_game.public_visibility_status = "hidden"
        hidden_populated_game.public_visibility_status = "hidden"
        db.delete(hidden_detail)
        db.commit()
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()

    filtered = client.get(
        f"/community-game-details?game_id={hidden_game_id}",
        headers=_auth_headers("admin-token"),
    )
    assert filtered.status_code == 200, filtered.text
    assert filtered.json() == []
    _assert_one_action(
        "read_staff_hidden_community_payment_list",
        actor_id=admin.id,
        target_field="target_game_id",
        target_id=hidden_game_id,
    )

    unfiltered = client.get(
        "/community-game-details",
        headers=_auth_headers("admin-token"),
    )
    assert unfiltered.status_code == 200, unfiltered.text
    returned_ids = {uuid.UUID(item["id"]) for item in unfiltered.json()}
    assert visible_detail_id in returned_ids
    assert hidden_populated_detail_id not in returned_ids
    assert len(_action_rows("read_staff_hidden_community_payment_list")) == 1


@pytest.mark.parametrize(
    ("role", "account_status", "deleted"),
    (
        ("player", "active", False),
        ("admin", "suspended", False),
        ("admin", "pending_deletion", False),
        ("admin", "deleted", True),
    ),
)
def test_batch_private_transaction_rejects_every_inactive_admin_state(
    role: str,
    account_status: str,
    deleted: bool,
) -> None:
    actor = _user(f"batch-{role}-{account_status}", role=role, status=account_status)
    if deleted:
        actor.deleted_at = datetime.now(timezone.utc)
    payer = _user("batch-payer")
    payment = _payment(payer)
    _persist(actor, payer, payment)

    with pytest.raises(HTTPException) as exc:
        record_sensitive_admin_read_batch(
            authenticated_admin_id=actor.id,
            action_type="read_staff_payment_list_item",
            target_ids=[payment.id],
        )
    assert exc.value.status_code == 403
    assert _rows_for(payment.id) == []


def test_invalid_route_inputs_are_rejected_before_any_sensitive_read_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("invalid-admin", role="admin")
    owner = _user("invalid-owner")
    _persist(admin, owner)
    fixture = _persist_cross_user_fixture(admin=admin, owner=owner)
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()
    invalid_routes = (
        "/admin/money/payments?payment_status=not-real",
        "/admin/money/refunds?refund_status=not-real",
        "/admin/money/credits?credit_status=not-real",
        "/admin/money/issues?status=not-real",
        "/admin/money/payments?unsupported=true",
        f"/admin/money/refunds/{fixture['refund_id']}/events?cursor=not-a-cursor",
        "/payments?payment_status=not-real",
        "/refunds?refund_status=not-real",
        "/bookings?booking_status=not-real",
        "/waitlist-entries?waitlist_status=not-real",
        "/host-publish-fees?fee_status=not-real",
    )
    for route in invalid_routes:
        response = client.get(route, headers=_auth_headers("admin-token"))
        assert response.status_code in {400, 422}, (route, response.text)
    with SessionLocal() as db:
        assert not list(
            db.scalars(
                select(AdminAction).where(
                    AdminAction.action_type.in_(SENSITIVE_FINANCIAL_READ_TARGETS)
                )
            )
        )


def test_distinct_service_patterns_fail_closed_before_protected_loading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import (
        admin_game_sensitive_read_service,
        community_game_detail_service,
        payment_service,
    )

    admin = _user("failure-admin", role="admin")
    owner = _user("failure-owner")
    _persist(admin, owner)
    fixture = _persist_cross_user_fixture(admin=admin, owner=owner)
    hidden_game_id, _ = _persist_community_game_fixture(
        "ws09-02c-failure-hidden", admin=admin, host=owner
    )
    with SessionLocal() as db:
        game = db.get(Game, hidden_game_id)
        assert game is not None
        game.public_visibility_status = "hidden"
        hidden_detail_id = db.scalar(
            select(CommunityGameDetail.id).where(
                CommunityGameDetail.game_id == hidden_game_id
            )
        )
        db.commit()
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    community_serializer_called = False

    def audit_unavailable(**kwargs: object) -> None:
        raise HTTPException(status_code=503, detail=AUDIT_UNAVAILABLE_DETAIL)

    def forbidden_community_serializer(*args: object, **kwargs: object) -> object:
        nonlocal community_serializer_called
        community_serializer_called = True
        raise AssertionError("hidden payment snapshot loaded before audit commit")

    monkeypatch.setattr(
        admin_game_sensitive_read_service,
        "record_financial_sensitive_read",
        audit_unavailable,
    )
    monkeypatch.setattr(
        payment_service,
        "record_financial_sensitive_read",
        audit_unavailable,
    )
    monkeypatch.setattr(
        payment_service,
        "record_sensitive_admin_read_batch",
        audit_unavailable,
    )
    monkeypatch.setattr(
        community_game_detail_service,
        "record_financial_sensitive_read",
        audit_unavailable,
    )
    monkeypatch.setattr(
        community_game_detail_service,
        "serialize_public_community_game_detail",
        forbidden_community_serializer,
    )
    client = _client()
    routes = (
        f"/admin/official-games/{fixture['game_id']}/money",
        f"/payments/{fixture['payment_id']}",
        "/payments",
        f"/community-game-details/{hidden_detail_id}",
        f"/community-game-details?game_id={hidden_game_id}",
    )
    for route in routes:
        response = client.get(route, headers=_auth_headers("admin-token"))
        assert response.status_code == 503, (route, response.text)
        assert response.json()["detail"] == AUDIT_UNAVAILABLE_DETAIL
    assert not community_serializer_called


def test_shared_preview_calculators_remain_free_of_read_audit_side_effects() -> None:
    import inspect

    from backend.services.game_cancellation_service import (
        build_official_game_cancellation_preview,
    )
    from backend.services.official_game_player_removal_service import (
        preview_official_game_player_removal,
    )

    for calculator in (
        build_official_game_cancellation_preview,
        preview_official_game_player_removal,
    ):
        source = inspect.getsource(calculator)
        assert "record_financial_sensitive_read" not in source
        assert "record_sensitive_admin_read" not in source
