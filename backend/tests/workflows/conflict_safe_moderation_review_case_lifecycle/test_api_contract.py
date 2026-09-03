from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from backend.models import (
    AdminAction,
    AdminReviewCase,
    AdminReviewCaseEvent,
    AdminReviewCaseNote,
    AdminReviewCaseResolutionReference,
)
from backend.schemas.admin_review_schema import (
    AdminReviewCaseAssignment,
    AdminReviewCaseClose,
    AdminReviewCaseMerge,
    AdminReviewCaseNoteCreate,
    AdminReviewCaseReopen,
)
from backend.services.admin_review_service import close_review_case
from backend.services.moderation_surfacing_service import surface_community_game_text
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    _add_users,
    _auth_headers,
    _client,
    _install_tokens_for_users,
    _user,
)
from backend.tests.workflows.conflict_safe_moderation_review_case_lifecycle.conftest import (
    create_chat_case,
    create_content_case,
    seed_game,
    session,
)

pytestmark = pytest.mark.suite_type("ordinary")

INVALID_EXPECTED_VERSIONS = (
    ("zero", 0),
    ("negative", -1),
    ("boolean", True),
    ("string", "2"),
    ("float", 2.0),
    ("null", None),
    ("list", [2]),
    ("object", {"value": 2}),
)

VERSIONED_REQUEST_MODELS = (
    (
        "close",
        AdminReviewCaseClose,
        {
            "outcome": "no_action_needed",
            "reason": "Strict version contract.",
            "expected_case_version": 2,
            "idempotency_key": "strict-close-key",
        },
        ("expected_case_version",),
    ),
    (
        "note",
        AdminReviewCaseNoteCreate,
        {
            "body": "Strict version contract.",
            "expected_case_version": 2,
            "idempotency_key": "strict-note-key",
        },
        ("expected_case_version",),
    ),
    (
        "assignment",
        AdminReviewCaseAssignment,
        {
            "assignee_user_id": None,
            "reason": "Strict version contract.",
            "expected_case_version": 2,
            "idempotency_key": "strict-assignment-key",
        },
        ("expected_case_version",),
    ),
    (
        "reopen",
        AdminReviewCaseReopen,
        {
            "reason": "Strict version contract.",
            "expected_case_version": 2,
            "idempotency_key": "strict-reopen-key",
        },
        ("expected_case_version",),
    ),
    (
        "merge",
        AdminReviewCaseMerge,
        {
            "destination_case_id": "33333333-3333-4333-8333-333333333333",
            "reason": "Strict version contract.",
            "expected_source_version": 2,
            "expected_destination_version": 2,
            "idempotency_key": "strict-merge-key",
        },
        ("expected_source_version", "expected_destination_version"),
    ),
)


@pytest.mark.requirement("WS03-05B-R4", "WS03-05B-R6")
@pytest.mark.parametrize(
    ("invalid_label", "invalid_value"),
    INVALID_EXPECTED_VERSIONS,
    ids=[item[0] for item in INVALID_EXPECTED_VERSIONS],
)
@pytest.mark.parametrize(
    ("request_name", "model_type", "valid_payload", "version_fields"),
    VERSIONED_REQUEST_MODELS,
    ids=[item[0] for item in VERSIONED_REQUEST_MODELS],
)
def test_mutation_schemas_reject_coercible_non_integer_expected_versions(
    request_name: str,
    model_type,
    valid_payload: dict[str, object],
    version_fields: tuple[str, ...],
    invalid_label: str,
    invalid_value: object,
) -> None:
    del request_name, invalid_label
    for version_field in version_fields:
        with pytest.raises(ValidationError):
            model_type(**{**valid_payload, version_field: invalid_value})


@pytest.mark.requirement("WS03-05B-R4", "WS03-05B-R6")
def test_admin_api_lists_filters_and_applies_versioned_lifecycle_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("ws03-05b-api-admin", role="admin")
    second_admin = _user("ws03-05b-api-second", role="admin")
    _add_users(admin, second_admin)
    with session() as db:
        game = seed_game(db)
        content_case_id = create_content_case(db, game).id
        chat_case_id = create_chat_case(db, game).id

    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "second-admin-token": second_admin},
    )
    client = _client()

    all_cases = client.get(
        "/admin/review-cases?case_status=open&assignment=all",
        headers=_auth_headers("admin-token"),
    )
    assert all_cases.status_code == 200
    assert {item["id"] for item in all_cases.json()["cases"]} == {
        str(content_case_id),
        str(chat_case_id),
    }
    chat_cases = client.get(
        "/admin/review-cases?case_category=chat_moderation",
        headers=_auth_headers("admin-token"),
    )
    assert [item["id"] for item in chat_cases.json()["cases"]] == [str(chat_case_id)]

    for case_id, key in (
        (content_case_id, "content"),
        (chat_case_id, "chat"),
    ):
        assignment = client.post(
            f"/admin/review-cases/{case_id}/assignment",
            json={
                "assignee_user_id": str(admin.id),
                "reason": f"Claim {key} review.",
                "expected_case_version": 2,
                "idempotency_key": f"ws03-05b-api-assign-{key}",
            },
            headers=_auth_headers("admin-token"),
        )
        assert assignment.status_code == 200
        assert assignment.json()["review_case"]["assigned_to_user_id"] == str(admin.id)
        assert assignment.json()["resulting_case_version"] == 3

    mine_page = client.get(
        "/admin/review-cases?case_status=open&assignment=mine&limit=1",
        headers=_auth_headers("admin-token"),
    )
    assert mine_page.status_code == 200
    assert mine_page.json()["has_more"] is True
    cursor = mine_page.json()["next_cursor"]
    assert cursor
    wrong_assignment = client.get(
        f"/admin/review-cases?case_status=open&assignment=all&limit=1&cursor={cursor}",
        headers=_auth_headers("admin-token"),
    )
    assert wrong_assignment.status_code == 400
    wrong_viewer = client.get(
        f"/admin/review-cases?case_status=open&assignment=mine&limit=1&cursor={cursor}",
        headers=_auth_headers("second-admin-token"),
    )
    assert wrong_viewer.status_code == 400

    note = client.post(
        f"/admin/review-cases/{content_case_id}/notes",
        json={
            "body": "API lifecycle note.",
            "expected_case_version": 3,
            "idempotency_key": "ws03-05b-api-note",
        },
        headers=_auth_headers("admin-token"),
    )
    assert note.status_code == 200
    assert note.json()["resulting_case_version"] == 4
    close = client.post(
        f"/admin/review-cases/{content_case_id}/close",
        json={
            "outcome": "no_action_needed",
            "reason": "Complete API review.",
            "expected_case_version": 4,
            "idempotency_key": "ws03-05b-api-close",
        },
        headers=_auth_headers("admin-token"),
    )
    assert close.status_code == 200
    assert close.json()["review_case"]["case_status"] == "closed"
    assert close.json()["resulting_case_version"] == 5
    reopen = client.post(
        f"/admin/review-cases/{content_case_id}/reopen",
        json={
            "reason": "Reconsider after new context.",
            "expected_case_version": 5,
            "idempotency_key": "ws03-05b-api-reopen",
        },
        headers=_auth_headers("admin-token"),
    )
    assert reopen.status_code == 200
    assert reopen.json()["review_case"]["case_status"] == "open"
    assert reopen.json()["resulting_case_version"] == 6
    detail = client.get(
        f"/admin/review-cases/{content_case_id}",
        headers=_auth_headers("admin-token"),
    )
    assert detail.status_code == 200
    detail_body = detail.json()
    assert [item["event_sequence"] for item in detail_body["events"]] == list(
        range(1, 7)
    )
    assert detail_body["resolution_references"]
    assert detail_body["resolution_history"] == [
        {
            "closure_event_id": detail_body["events"][-2]["id"],
            "event_sequence": 5,
            "outcome": "no_action_needed",
            "mode": "manual",
            "reason": "Complete API review.",
            "actor_kind": "admin",
            "actor_user_id": str(admin.id),
            "automation_rule_id": None,
            "automation_rule_version": None,
            "trigger_actor_user_id": None,
            "admin_action_id": detail_body["events"][-2]["admin_action_id"],
            "closed_at": detail_body["events"][-2]["created_at"],
            "references": detail_body["resolution_references"],
        }
    ]


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R4", "WS03-05B-R6")
def test_admin_api_merge_and_safe_conflict_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("ws03-05b-merge-admin", role="admin")
    _add_users(admin)
    with session() as db:
        game = seed_game(db)
        game_id = game.id
        source = create_content_case(db, game)
        close_review_case(
            db,
            review_case_id=source.id,
            admin_user=db.get(type(admin), admin.id),
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Create merge source.",
                expected_case_version=2,
                idempotency_key="ws03-05b-api-source-close",
            ),
        )
        source_id = source.id
        game.description = "Text me at 214-555-0100"
        db.commit()
        surface_community_game_text(db, game_id=game_id)
        destination = db.scalar(
            select(AdminReviewCase).where(
                AdminReviewCase.target_game_id == game_id,
                AdminReviewCase.case_status == "open",
                AdminReviewCase.case_category == "content_moderation",
            )
        )
        destination_id = destination.id

    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()
    merge = client.post(
        f"/admin/review-cases/{source_id}/merge",
        json={
            "destination_case_id": str(destination_id),
            "reason": "Link compatible historical review.",
            "expected_source_version": 3,
            "expected_destination_version": 2,
            "idempotency_key": "ws03-05b-api-merge",
        },
        headers=_auth_headers("admin-token"),
    )
    assert merge.status_code == 200
    assert merge.json()["source_case"]["merged_into_case_id"] == str(destination_id)
    assert merge.json()["destination_case"]["case_status"] == "open"
    assert merge.json()["source_case"]["resolution_history"][0]["reason"] == (
        "Create merge source."
    )

    canary = "PRIVATE REVIEW EVIDENCE"
    stale = client.post(
        f"/admin/review-cases/{destination_id}/notes",
        json={
            "body": canary,
            "expected_case_version": 2,
            "idempotency_key": "ws03-05b-api-stale-note",
        },
        headers=_auth_headers("admin-token"),
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "review_case_version_conflict"
    assert canary not in stale.text
    assert set(stale.json()["detail"]["current"]) == {
        "id",
        "case_status",
        "case_version",
        "priority",
        "assigned_to_user_id",
        "closure_outcome",
        "merged_into_case_id",
        "updated_at",
    }

    missing_version = client.post(
        f"/admin/review-cases/{destination_id}/notes",
        json={
            "body": "Missing version.",
            "idempotency_key": "ws03-05b-api-missing-version",
        },
        headers=_auth_headers("admin-token"),
    )
    unknown_field = client.post(
        f"/admin/review-cases/{destination_id}/assignment",
        json={
            "assignee_user_id": str(admin.id),
            "reason": "Reject unknown input.",
            "expected_case_version": 3,
            "idempotency_key": "ws03-05b-api-unknown-field",
            "unexpected": True,
        },
        headers=_auth_headers("admin-token"),
    )
    assert missing_version.status_code == 422
    assert unknown_field.status_code == 422

    close_destination = client.post(
        f"/admin/review-cases/{destination_id}/close",
        json={
            "outcome": "no_action_needed",
            "reason": "Close destination before a new current case.",
            "expected_case_version": 3,
            "idempotency_key": "ws03-05b-api-close-chain-middle",
        },
        headers=_auth_headers("admin-token"),
    )
    assert close_destination.status_code == 200
    with session() as db:
        game = db.get(type(game), game_id)
        game.description = "Call 312-555-1212"
        db.commit()
        surface_community_game_text(db, game_id=game_id)
        next_destination = db.scalar(
            select(AdminReviewCase).where(
                AdminReviewCase.target_game_id == game_id,
                AdminReviewCase.case_status == "open",
                AdminReviewCase.case_category == "content_moderation",
            )
        )
        next_destination_id = next_destination.id
        action_count = db.scalar(select(func.count(AdminAction.id)))
        event_count = db.scalar(select(func.count(AdminReviewCaseEvent.id)))

    chain = client.post(
        f"/admin/review-cases/{destination_id}/merge",
        json={
            "destination_case_id": str(next_destination_id),
            "reason": "Reject a merge chain.",
            "expected_source_version": 4,
            "expected_destination_version": 2,
            "idempotency_key": "ws03-05b-api-reject-chain",
        },
        headers=_auth_headers("admin-token"),
    )
    assert chain.status_code == 409
    assert chain.json()["detail"]["code"] == "review_case_transition_conflict"
    with session() as db:
        assert db.get(AdminReviewCase, source_id).merged_into_case_id == destination_id
        assert db.get(AdminReviewCase, destination_id).merged_into_case_id is None
        assert db.scalar(select(func.count(AdminAction.id))) == action_count
        assert db.scalar(select(func.count(AdminReviewCaseEvent.id))) == event_count


STRICT_VERSION_API_FIELDS = (
    ("assignment", "expected_case_version"),
    ("notes", "expected_case_version"),
    ("close", "expected_case_version"),
    ("reopen", "expected_case_version"),
    ("merge", "expected_source_version"),
    ("merge", "expected_destination_version"),
)


@pytest.mark.requirement("WS03-05B-R4", "WS03-05B-R6")
@pytest.mark.parametrize(
    ("invalid_label", "invalid_value"),
    INVALID_EXPECTED_VERSIONS,
    ids=[item[0] for item in INVALID_EXPECTED_VERSIONS],
)
@pytest.mark.parametrize(
    ("endpoint", "version_field"),
    STRICT_VERSION_API_FIELDS,
    ids=[f"{endpoint}-{field}" for endpoint, field in STRICT_VERSION_API_FIELDS],
)
def test_mutation_apis_reject_non_integer_versions_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    version_field: str,
    invalid_label: str,
    invalid_value: object,
) -> None:
    admin = _user(
        f"ws03-05b-strict-{endpoint}-{version_field}-{invalid_label}", role="admin"
    )
    _add_users(admin)
    with session() as db:
        game = seed_game(db)
        review_case_id = create_content_case(db, game).id
        before = review_case_side_effect_snapshot(db)

    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    payloads = {
        "assignment": {
            "assignee_user_id": str(admin.id),
            "reason": "Strict version API contract.",
            "expected_case_version": 2,
            "idempotency_key": "strict-api-assignment",
        },
        "notes": {
            "body": "Strict version API contract.",
            "expected_case_version": 2,
            "idempotency_key": "strict-api-note",
        },
        "close": {
            "outcome": "no_action_needed",
            "reason": "Strict version API contract.",
            "expected_case_version": 2,
            "idempotency_key": "strict-api-close",
        },
        "reopen": {
            "reason": "Strict version API contract.",
            "expected_case_version": 2,
            "idempotency_key": "strict-api-reopen",
        },
        "merge": {
            "destination_case_id": str(review_case_id),
            "reason": "Strict version API contract.",
            "expected_source_version": 2,
            "expected_destination_version": 2,
            "idempotency_key": "strict-api-merge",
        },
    }
    payload = {**payloads[endpoint], version_field: invalid_value}

    response = _client().post(
        f"/admin/review-cases/{review_case_id}/{endpoint}",
        json=payload,
        headers=_auth_headers("admin-token"),
    )

    assert response.status_code == 422
    with session() as db:
        assert review_case_side_effect_snapshot(db) == before


DENIED_REVIEW_ACTORS = (
    ("anonymous", None, "active", False, False, 401),
    ("player", "player", "active", False, False, 403),
    ("suspended", "admin", "suspended", False, False, 403),
    ("pending", "admin", "pending_deletion", False, False, 404),
    ("deleted", "admin", "active", True, False, 404),
    ("stale-admin", "admin", "active", False, True, 403),
)
DENIED_REVIEW_ENDPOINTS = (
    ("list", "GET", False),
    ("detail", "GET", False),
    ("assignment", "POST", True),
    ("note", "POST", True),
    ("close", "POST", True),
    ("reopen", "POST", True),
    ("merge", "POST", True),
)


def review_case_side_effect_snapshot(db) -> tuple[object, ...]:
    case_rows = tuple(
        db.execute(
            select(
                AdminReviewCase.id,
                AdminReviewCase.case_status,
                AdminReviewCase.case_version,
                AdminReviewCase.assigned_to_user_id,
                AdminReviewCase.assigned_at,
                AdminReviewCase.closure_outcome,
                AdminReviewCase.closure_mode,
                AdminReviewCase.merged_into_case_id,
            ).order_by(AdminReviewCase.id.asc())
        ).all()
    )
    return (
        case_rows,
        db.scalar(select(func.count(AdminReviewCaseNote.id))),
        db.scalar(select(func.count(AdminReviewCaseEvent.id))),
        db.scalar(select(func.count(AdminReviewCaseResolutionReference.id))),
        db.scalar(select(func.count(AdminAction.id))),
    )


def denied_review_request(
    client,
    *,
    endpoint: str,
    review_case_id,
    destination_case_id,
    actor_id,
    headers,
):
    if endpoint == "list":
        return client.get("/admin/review-cases", headers=headers)
    if endpoint == "detail":
        return client.get(f"/admin/review-cases/{review_case_id}", headers=headers)
    payloads = {
        "assignment": {
            "assignee_user_id": str(actor_id) if actor_id is not None else None,
            "reason": "Denied assignment must not persist.",
            "expected_case_version": 2,
            "idempotency_key": "ws03-05b-denied-assignment",
        },
        "note": {
            "body": "Denied internal note must not persist.",
            "expected_case_version": 2,
            "idempotency_key": "ws03-05b-denied-note",
        },
        "close": {
            "outcome": "no_action_needed",
            "reason": "Denied closure must not persist.",
            "expected_case_version": 2,
            "idempotency_key": "ws03-05b-denied-close",
        },
        "reopen": {
            "reason": "Denied reopen must not persist.",
            "expected_case_version": 2,
            "idempotency_key": "ws03-05b-denied-reopen",
        },
        "merge": {
            "destination_case_id": str(destination_case_id),
            "reason": "Denied merge must not persist.",
            "expected_source_version": 2,
            "expected_destination_version": 2,
            "idempotency_key": "ws03-05b-denied-merge",
        },
    }
    path_suffix = "notes" if endpoint == "note" else endpoint
    return client.post(
        f"/admin/review-cases/{review_case_id}/{path_suffix}",
        json=payloads[endpoint],
        headers=headers,
    )


@pytest.mark.requirement("WS03-05B-R4", "WS03-05B-R6")
@pytest.mark.parametrize(
    ("actor_label", "role", "account_status", "deleted", "demote", "status_code"),
    DENIED_REVIEW_ACTORS,
)
@pytest.mark.parametrize(
    ("endpoint", "method", "mutation"),
    DENIED_REVIEW_ENDPOINTS,
)
def test_every_review_endpoint_enforces_current_active_admin_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    actor_label: str,
    role: str | None,
    account_status: str,
    deleted: bool,
    demote: bool,
    status_code: int,
    endpoint: str,
    method: str,
    mutation: bool,
) -> None:
    del method
    actor = None
    if role is not None:
        actor = _user(
            f"ws03-05b-denied-{endpoint}-{actor_label}",
            role=role,
            account_status=account_status,
        )
        if deleted:
            actor.deleted_at = datetime.now(timezone.utc)
        _add_users(actor)
        _install_tokens_for_users(monkeypatch, {"denied-token": actor})
        if demote:
            with session() as db:
                persisted_actor = db.get(type(actor), actor.id)
                persisted_actor.role = "player"
                db.commit()

    with session() as db:
        game = seed_game(db)
        destination_game = seed_game(db)
        review_case_id = create_content_case(db, game).id
        destination_case_id = create_content_case(db, destination_game).id
        before = review_case_side_effect_snapshot(db)

    headers = _auth_headers("denied-token") if actor is not None else None
    response = denied_review_request(
        _client(),
        endpoint=endpoint,
        review_case_id=review_case_id,
        destination_case_id=destination_case_id,
        actor_id=actor.id if actor is not None else None,
        headers=headers,
    )
    assert response.status_code == status_code

    if mutation:
        with session() as db:
            assert review_case_side_effect_snapshot(db) == before
