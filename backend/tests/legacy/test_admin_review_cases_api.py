from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.database import SessionLocal
from backend.models import (
    AdminAction,
    AdminContentModerationFinding,
    AdminReviewCase,
    AdminReviewCaseEvent,
    AdminReviewCaseNote,
)
from backend.services import content_moderation_finding_service
from backend.services.content_moderation_evidence_service import (
    ContentModerationFinding,
)
from backend.services.content_moderation_scanner_service import content_hash
from backend.tests.helpers import (
    authenticate_as,
    create_game,
    create_sub_post,
    create_user,
    create_venue,
    set_user_role,
    unique_suffix,
)


def create_community_game(client: TestClient, host: dict, **overrides: object) -> dict:
    venue = create_venue(client, host["id"])
    payload = {
        "game_type": "community",
        "host_user_id": host["id"],
        "created_by_user_id": host["id"],
        "policy_mode": "custom_hosted",
    }
    payload.update(overrides)
    return create_game(client, host["id"], venue, **payload)


def build_test_evidence(
    *,
    text: str = "Text me at 312-555-1234",
    matched_text: str = "312-555-1234",
    rule_id: str = "personal_info.phone_number",
    evidence_type: str = "phone",
) -> list[dict]:
    start = text.index(matched_text)
    end = start + len(matched_text)
    return [
        {
            "evidence_type": evidence_type,
            "display_text": text,
            "start": 0,
            "end": len(text),
            "matches": [
                {
                    "rule_id": rule_id,
                    "evidence_type": evidence_type,
                    "matched_text": matched_text,
                    "start": start,
                    "end": end,
                }
            ],
            "truncated_before": False,
            "truncated_after": False,
            "additional_match_count": 0,
        }
    ]


def build_test_content_moderation_finding(
    *,
    source_field: str = "notes",
    text: str = "Text me at 312-555-1234",
    finding_type: str = "off_app_contact",
    risk_area: str = "unsafe_post_text",
    priority: str = "attention",
    evidence_fingerprint: str | None = None,
) -> ContentModerationFinding:
    evidence = build_test_evidence(text=text)
    return ContentModerationFinding(
        risk_area=risk_area,
        finding_type=finding_type,
        priority=priority,
        source_field=source_field,
        source_content_hash=content_hash(text),
        evidence_fingerprint=evidence_fingerprint or uuid4().hex,
        evidence=evidence,
        matched_rule_ids=("personal_info.phone_number",),
    )


def create_content_review_case(
    *,
    target_game_id: str | None = None,
    target_sub_post_id: str | None = None,
    priority: str = "attention",
    finding_type: str = "off_app_contact",
    risk_area: str = "unsafe_post_text",
    source_field: str = "notes",
) -> str:
    now = datetime.now(timezone.utc)
    if target_game_id is not None:
        case_type = "community_game"
        title = "Community Game needs review"
        summary = "Review moderation findings attached to this Community Game."
        target_data = {"target_game_id": UUID(target_game_id)}
    else:
        assert target_sub_post_id is not None
        case_type = "need_a_sub"
        title = "Need a Sub post needs review"
        summary = "Review moderation findings attached to this Need a Sub post."
        target_data = {"target_sub_post_id": UUID(target_sub_post_id)}

    with SessionLocal() as db:
        review_case = AdminReviewCase(
            id=uuid4(),
            case_type=case_type,
            case_status="open",
            case_category="content_moderation",
            priority=priority,
            title=title,
            summary=summary,
            created_at=now,
            updated_at=now,
            **target_data,
        )
        db.add(review_case)
        db.flush()

        text = "Text me at 312-555-1234"
        finding = AdminContentModerationFinding(
            id=uuid4(),
            review_case_id=review_case.id,
            risk_area=risk_area,
            finding_type=finding_type,
            priority=priority,
            source_field=source_field,
            source_content_hash=content_hash(text),
            evidence_fingerprint=uuid4().hex,
            evidence=build_test_evidence(text=text),
            current_match=True,
            first_detected_at=now,
            last_detected_at=now,
            cleared_at=None,
            scanner_version="test-scanner",
            metadata_={
                "source": "content_moderation_scanner",
                "matched_rule_ids": ["personal_info.phone_number"],
                "scanner_version": "test-scanner",
            },
            created_at=now,
            updated_at=now,
        )
        db.add(finding)
        db.flush()
        db.add(
            AdminReviewCaseEvent(
                id=uuid4(),
                review_case_id=review_case.id,
                event_type="case_created",
                event_metadata={"source": "test"},
                created_at=now,
            )
        )
        db.add(
            AdminReviewCaseEvent(
                id=uuid4(),
                review_case_id=review_case.id,
                event_type="finding_attached",
                content_moderation_finding_id=finding.id,
                event_metadata={
                    "finding_type": finding.finding_type,
                    "risk_area": finding.risk_area,
                    "source_field": finding.source_field,
                },
                created_at=now,
            )
        )
        db.commit()
        return str(review_case.id)


def test_admin_review_content_case_links_enforcement_action(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    host = create_user(client)
    game = create_community_game(client, host)
    case_id = create_content_review_case(
        target_game_id=game["id"],
        priority="urgent",
        risk_area="unsafe_payment_text",
        source_field="payment_instructions_snapshot",
    )

    authenticate_as(admin["id"])
    hide_response = client.post(
        f"/admin/community-games/{game['id']}/hide",
        json={
            "reason": "Hide while review case is open.",
            "idempotency_key": f"review-link-hide-{unique_suffix()}",
        },
    )

    assert hide_response.status_code == 200, hide_response.text
    with SessionLocal() as db:
        linked_action = db.scalar(
            select(AdminAction).where(
                AdminAction.id == UUID(hide_response.json()["audit_action_id"])
            )
        )
        assert linked_action is not None
        assert str(linked_action.target_review_case_id) == case_id

    detail_response = client.get(f"/admin/review-cases/{case_id}")

    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["finding_summary"]["current_finding_count"] == 1
    assert len(detail["findings"]) == 1
    assert "enforcement_action_linked" in {
        event["event_type"] for event in detail["events"]
    }


def test_admin_review_cases_list_uses_cursor_and_target_filter(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    host = create_user(client)
    game = create_community_game(client, host)
    owner = create_user(client)
    post = create_sub_post(client, owner["id"], team_name="Review Cursor FC")

    authenticate_as(admin["id"])
    create_content_review_case(
        target_game_id=game["id"],
        source_field="game_notes",
    )
    create_content_review_case(
        target_sub_post_id=post["id"],
        source_field="notes",
    )

    first_page_response = client.get(
        "/admin/review-cases?case_status=open&case_category=content_moderation"
        "&target_type=content_targets&limit=1"
    )

    assert first_page_response.status_code == 200, first_page_response.text
    first_page = first_page_response.json()
    assert len(first_page["cases"]) == 1
    assert first_page["has_more"] is True
    assert first_page["next_cursor"]
    assert first_page["total_count"] is None

    second_page_response = client.get(
        "/admin/review-cases?case_status=open&case_category=content_moderation"
        f"&target_type=content_targets&limit=1&cursor={first_page['next_cursor']}"
    )

    assert second_page_response.status_code == 200, second_page_response.text
    second_page = second_page_response.json()
    assert len(second_page["cases"]) == 1
    assert second_page["cases"][0]["id"] != first_page["cases"][0]["id"]

    sub_filter_response = client.get(
        "/admin/review-cases?case_status=open&case_category=content_moderation"
        "&target_type=need_a_sub"
    )
    game_filter_response = client.get(
        "/admin/review-cases?case_status=open&case_category=content_moderation"
        "&target_type=community_game"
    )

    assert sub_filter_response.status_code == 200, sub_filter_response.text
    assert game_filter_response.status_code == 200, game_filter_response.text
    sub_cases = sub_filter_response.json()["cases"]
    game_cases = game_filter_response.json()["cases"]
    assert {case["target_sub_post_id"] for case in sub_cases} == {post["id"]}
    assert {case["target_game_id"] for case in game_cases} == {game["id"]}
    assert sub_cases[0]["target_summary"]["label"] == "Need a Sub Post"
    assert sub_cases[0]["target_summary"]["title"] == "Review Cursor FC"
    assert game_cases[0]["target_summary"]["label"] == "Community Game"
    assert game_cases[0]["target_summary"]["title"] == game["title"]


def test_admin_review_closed_content_target_filter_includes_unavailable_target(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    owner = create_user(client)
    post = create_sub_post(client, owner["id"], team_name="Deleted Target FC")
    case_id = create_content_review_case(
        target_sub_post_id=post["id"],
        source_field="notes",
    )

    with SessionLocal() as db:
        review_case = db.get(AdminReviewCase, UUID(case_id))
        assert review_case is not None
        review_case.case_status = "closed"
        review_case.closure_outcome = "no_action_needed"
        review_case.closure_reason = "Target is no longer available."
        review_case.closed_at = datetime.now(timezone.utc)
        review_case.target_sub_post_id = None
        db.add(review_case)
        db.commit()

    authenticate_as(admin["id"])
    list_response = client.get(
        "/admin/review-cases?case_status=closed&case_category=content_moderation"
        "&target_type=content_targets"
    )
    detail_response = client.get(f"/admin/review-cases/{case_id}")

    assert list_response.status_code == 200, list_response.text
    assert case_id in {case["id"] for case in list_response.json()["cases"]}
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["target_summary"] == {
        "label": "Need a Sub Post",
        "title": "Post unavailable",
        "subtitle": None,
        "status": "unavailable",
        "starts_at": None,
        "location": None,
    }


def test_admin_review_case_notes_and_closure(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    owner = create_user(client)
    post = create_sub_post(client, owner["id"], team_name="Review Case FC")

    authenticate_as(admin["id"])
    case_id = create_content_review_case(
        target_sub_post_id=post["id"],
        source_field="notes",
    )

    note_payload = {
        "body": "Internal note: owner follow-up is needed.",
        "idempotency_key": f"review-note-{unique_suffix()}",
    }
    note_response = client.post(
        f"/admin/review-cases/{case_id}/notes",
        json=note_payload,
    )
    note_replay_response = client.post(
        f"/admin/review-cases/{case_id}/notes",
        json=note_payload,
    )

    assert note_response.status_code == 200, note_response.text
    assert note_response.json()["note"]["body"] == note_payload["body"]
    assert note_response.json()["note"]["author_display_name"] == "Test User"
    assert note_replay_response.status_code == 200, note_replay_response.text
    assert note_replay_response.json()["idempotent_replay"] is True
    assert len(note_replay_response.json()["review_case"]["notes"]) == 1

    too_long_note_response = client.post(
        f"/admin/review-cases/{case_id}/notes",
        json={
            "body": "x" * 1001,
            "idempotency_key": f"review-note-long-{unique_suffix()}",
        },
    )
    assert too_long_note_response.status_code == 422, too_long_note_response.text

    close_payload = {
        "outcome": "no_action_needed",
        "reason": "Admin reviewed the case and no public change is needed.",
        "idempotency_key": f"review-close-{unique_suffix()}",
    }
    close_response = client.post(
        f"/admin/review-cases/{case_id}/close",
        json=close_payload,
    )
    close_replay_response = client.post(
        f"/admin/review-cases/{case_id}/close",
        json=close_payload,
    )

    assert close_response.status_code == 200, close_response.text
    assert close_response.json()["review_case"]["case_status"] == "closed"
    assert close_response.json()["review_case"]["closure_outcome"] == (
        "no_action_needed"
    )
    assert close_replay_response.status_code == 200, close_replay_response.text
    assert close_replay_response.json()["idempotent_replay"] is True

    with SessionLocal() as db:
        event_types = set(
            db.scalars(
                select(AdminReviewCaseEvent.event_type).where(
                    AdminReviewCaseEvent.review_case_id == UUID(case_id)
                )
            ).all()
        )
        assert {
            "case_created",
            "finding_attached",
            "note_added",
            "closed",
        }.issubset(event_types)


def test_admin_review_case_notes_have_hard_case_limit(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    post = create_sub_post(client, admin["id"])

    authenticate_as(admin["id"])
    case_id = create_content_review_case(
        target_sub_post_id=post["id"],
        source_field="notes",
    )

    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        for index in range(100):
            db.add(
                AdminReviewCaseNote(
                    id=uuid4(),
                    review_case_id=UUID(case_id),
                    author_user_id=UUID(admin["id"]),
                    body=f"Existing note {index}",
                    created_at=now,
                    updated_at=now,
                )
            )
        db.commit()

    limit_response = client.post(
        f"/admin/review-cases/{case_id}/notes",
        json={
            "body": "One note too many.",
            "idempotency_key": f"review-note-limit-{unique_suffix()}",
        },
    )

    assert limit_response.status_code == 400, limit_response.text
    assert "at most 100 notes" in limit_response.json()["detail"]


def test_content_moderation_finding_retries_after_flush_conflict(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    host = create_user(client)
    game = create_community_game(client, host)
    finding = build_test_content_moderation_finding(
        source_field="game_notes",
        text="Text me at 312-555-1234",
    )

    with SessionLocal() as db:
        original_flush = db.flush
        state = {"raised": False}

        def flaky_flush(*args: object, **kwargs: object) -> None:
            if not state["raised"]:
                state["raised"] = True
                raise IntegrityError(
                    "forced review case flush conflict",
                    {},
                    RuntimeError("forced"),
                )
            original_flush(*args, **kwargs)

        monkeypatch.setattr(db, "flush", flaky_flush)

        result = (
            content_moderation_finding_service.reconcile_content_moderation_findings(
                db,
                target_data={"target_game_id": UUID(game["id"])},
                findings=[finding],
                scanned_field_values={"game_notes": "Text me at 312-555-1234"},
            )
        )

    assert state["raised"] is True
    assert result is not None
    assert result.target_game_id == UUID(game["id"])
    with SessionLocal() as db:
        findings = db.scalars(
            select(AdminContentModerationFinding).where(
                AdminContentModerationFinding.review_case_id == result.id
            )
        ).all()
        assert len(findings) == 1


def test_content_moderation_finding_refreshes_priority_for_existing_identity(
    client: TestClient,
):
    host = create_user(client)
    game = create_community_game(client, host)
    text = "Text me at 312-555-1234"
    evidence_fingerprint = uuid4().hex
    first_finding = build_test_content_moderation_finding(
        source_field="game_notes",
        text=text,
        priority="attention",
        evidence_fingerprint=evidence_fingerprint,
    )
    upgraded_finding = build_test_content_moderation_finding(
        source_field="game_notes",
        text=text,
        priority="urgent",
        evidence_fingerprint=evidence_fingerprint,
    )

    with SessionLocal() as db:
        first_case = (
            content_moderation_finding_service.reconcile_content_moderation_findings(
                db,
                target_data={"target_game_id": UUID(game["id"])},
                findings=[first_finding],
                scanned_field_values={"game_notes": text},
            )
        )
        assert first_case is not None
        review_case_id = first_case.id

    with SessionLocal() as db:
        second_case = (
            content_moderation_finding_service.reconcile_content_moderation_findings(
                db,
                target_data={"target_game_id": UUID(game["id"])},
                findings=[upgraded_finding],
                scanned_field_values={"game_notes": text},
            )
        )
        assert second_case is not None
        assert second_case.id == review_case_id

    with SessionLocal() as db:
        review_case = db.get(AdminReviewCase, review_case_id)
        findings = db.scalars(
            select(AdminContentModerationFinding).where(
                AdminContentModerationFinding.review_case_id == review_case_id
            )
        ).all()
        assert review_case is not None
        assert review_case.priority == "urgent"
        assert len(findings) == 1
        assert findings[0].priority == "urgent"
