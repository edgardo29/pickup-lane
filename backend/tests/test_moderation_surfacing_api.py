from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.database import SessionLocal
from backend.models import (
    AdminContentModerationFinding,
    AdminReviewCase,
    AdminReviewCaseEvent,
    AdminReviewSignal,
    Notification,
    SubPost,
)
from backend.services.need_a_sub_lifecycle_service import expire_due_posts_and_requests
from backend.tests.helpers import (
    authenticate_as,
    create_chat_message,
    create_community_game_detail,
    create_game,
    create_game_chat,
    create_game_participant,
    create_sub_post,
    create_user,
    create_venue,
    set_user_role,
    unique_suffix,
)


def request_spot(client: TestClient, requester_id: str, post: dict) -> dict:
    authenticate_as(requester_id)
    response = client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][0]["id"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def accept_request(client: TestClient, owner_id: str, request_id: str) -> dict:
    authenticate_as(owner_id)
    response = client.patch(f"/need-a-sub/requests/{request_id}/accept")
    assert response.status_code == 200, response.text
    return response.json()


def ensure_sub_post_chat(client: TestClient, user_id: str, post_id: str) -> dict:
    authenticate_as(user_id)
    response = client.post(f"/need-a-sub/posts/{post_id}/chat", json={})
    assert response.status_code == 200, response.text
    return response.json()


def send_sub_chat_message(
    client: TestClient,
    user_id: str,
    post_id: str,
    chat_id: str,
    body: str,
) -> dict:
    authenticate_as(user_id)
    response = client.post(
        f"/need-a-sub/posts/{post_id}/chat/messages",
        json={"chat_id": chat_id, "message_body": body},
    )
    assert response.status_code == 201, response.text
    return response.json()


def get_review_signals_for_sub_post(sub_post_id: str) -> list[AdminReviewSignal]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AdminReviewSignal)
                .where(AdminReviewSignal.target_sub_post_id == UUID(sub_post_id))
                .order_by(AdminReviewSignal.created_at.asc())
            ).all()
        )


def get_review_findings_for_sub_post(
    sub_post_id: str,
) -> list[AdminContentModerationFinding]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AdminContentModerationFinding)
                .select_from(AdminContentModerationFinding)
                .join(
                    AdminReviewCase,
                    AdminReviewCase.id
                    == AdminContentModerationFinding.review_case_id,
                )
                .where(AdminReviewCase.target_sub_post_id == UUID(sub_post_id))
                .order_by(
                    AdminContentModerationFinding.created_at.asc(),
                    AdminContentModerationFinding.id.asc(),
                )
            ).all()
        )


def get_review_cases_for_sub_post(sub_post_id: str) -> list[AdminReviewCase]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AdminReviewCase)
                .where(AdminReviewCase.target_sub_post_id == UUID(sub_post_id))
                .order_by(AdminReviewCase.created_at.asc())
            ).all()
        )


def get_review_signals_for_game(game_id: str) -> list[AdminReviewSignal]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AdminReviewSignal)
                .where(AdminReviewSignal.target_game_id == UUID(game_id))
                .order_by(AdminReviewSignal.created_at.asc())
            ).all()
        )


def get_review_findings_for_game(game_id: str) -> list[AdminContentModerationFinding]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AdminContentModerationFinding)
                .select_from(AdminContentModerationFinding)
                .join(
                    AdminReviewCase,
                    AdminReviewCase.id
                    == AdminContentModerationFinding.review_case_id,
                )
                .where(AdminReviewCase.target_game_id == UUID(game_id))
                .order_by(
                    AdminContentModerationFinding.created_at.asc(),
                    AdminContentModerationFinding.id.asc(),
                )
            ).all()
        )


def get_review_cases_for_game(game_id: str) -> list[AdminReviewCase]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AdminReviewCase)
                .where(AdminReviewCase.target_game_id == UUID(game_id))
                .order_by(AdminReviewCase.created_at.asc())
            ).all()
        )


def close_review_case_directly(review_case_id: UUID) -> None:
    with SessionLocal() as db:
        review_case = db.get(AdminReviewCase, review_case_id)
        assert review_case is not None
        review_case.case_status = "closed"
        review_case.closure_outcome = "no_action_needed"
        review_case.closure_reason = "Closed for test."
        review_case.closed_at = datetime.now(UTC)
        db.add(review_case)
        db.commit()


def get_review_case_snapshot(review_case_id: UUID) -> dict[str, object]:
    with SessionLocal() as db:
        review_case = db.get(AdminReviewCase, review_case_id)
        assert review_case is not None
        return {
            "case_status": review_case.case_status,
            "closure_outcome": review_case.closure_outcome,
            "closure_reason": review_case.closure_reason,
            "closed_by_user_id": (
                str(review_case.closed_by_user_id)
                if review_case.closed_by_user_id is not None
                else None
            ),
            "closed_at": review_case.closed_at,
        }


def get_closed_event_metadata(review_case_id: UUID) -> dict:
    with SessionLocal() as db:
        event = db.scalar(
            select(AdminReviewCaseEvent)
            .where(
                AdminReviewCaseEvent.review_case_id == review_case_id,
                AdminReviewCaseEvent.event_type == "closed",
            )
            .order_by(
                AdminReviewCaseEvent.created_at.desc(),
                AdminReviewCaseEvent.id.desc(),
            )
            .limit(1)
        )
        assert event is not None
        return event.event_metadata or {}


def list_review_case_ids(
    client: TestClient,
    admin_id: str,
    *,
    case_status: str,
) -> set[str]:
    authenticate_as(admin_id)
    response = client.get(
        f"/admin/review-cases?case_status={case_status}&target_type=content_targets"
    )
    assert response.status_code == 200, response.text
    return {item["id"] for item in response.json()["cases"]}


def create_risky_community_game(
    client: TestClient,
    host: dict,
    *,
    note_suffix: str = "",
) -> tuple[dict, AdminReviewCase]:
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )

    authenticate_as(host["id"])
    response = client.patch(
        f"/games/{game['id']}/host-edit",
        json={
            "game_notes": (
                "Text me at 312-555-1212 before kickoff. "
                f"{note_suffix}"
            ).strip()
        },
    )
    assert response.status_code == 200, response.text
    cases = get_review_cases_for_game(game["id"])
    assert len(cases) == 1
    assert cases[0].case_status == "open"
    return response.json(), cases[0]


def move_sub_post_expiration_into_past(post_id: str) -> None:
    with SessionLocal() as db:
        post = db.get(SubPost, UUID(post_id))
        assert post is not None
        now = datetime.now(UTC)
        post.starts_at = now - timedelta(minutes=10)
        post.ends_at = now + timedelta(minutes=50)
        post.expires_at = post.starts_at
        post.updated_at = now
        db.add(post)
        db.commit()


def count_admin_notice_notifications(user_id: str) -> int:
    with SessionLocal() as db:
        return int(
            db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.user_id == UUID(user_id),
                    Notification.notification_type == "admin_notice",
                )
            )
            or 0
        )


def test_normal_need_a_sub_payment_note_does_not_surface_review_case(
    client: TestClient,
):
    owner = create_user(client)
    post = create_sub_post(
        client,
        owner["id"],
        payment_note="Venmo @pickup-host accepted after the match.",
    )

    assert get_review_findings_for_sub_post(post["id"]) == []
    assert count_admin_notice_notifications(owner["id"]) == 0


def test_need_a_sub_risky_text_surfaces_and_marks_stale_after_clean_edit(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    owner = create_user(client)
    risky_notes = (
        "Text me at 312-555-1234, send deposit before approval, "
        "visit https://pay.example.com"
    )
    post = create_sub_post(
        client,
        owner["id"],
        notes=risky_notes,
    )

    findings = get_review_findings_for_sub_post(post["id"])
    cases = get_review_cases_for_sub_post(post["id"])
    assert len(cases) == 1
    assert cases[0].case_category == "content_moderation"
    assert cases[0].case_type == "need_a_sub"
    assert len(findings) == 2
    assert {finding.finding_type for finding in findings} == {
        "off_app_contact",
        "payment_pressure",
    }
    assert {finding.risk_area for finding in findings} == {
        "unsafe_post_text",
        "unsafe_payment_text",
    }
    assert {finding.review_case_id for finding in findings} == {cases[0].id}
    assert all(finding.current_match is True for finding in findings)
    assert all(finding.scanner_version for finding in findings)
    excerpts = [
        item["display_text"]
        for finding in findings
        for item in finding.evidence
    ]
    assert any("312-555-1234" in excerpt for excerpt in excerpts)
    assert any("https://pay.example.com" in excerpt for excerpt in excerpts)
    assert all("***" not in excerpt for excerpt in excerpts)
    assert all("[link]" not in excerpt for excerpt in excerpts)
    assert count_admin_notice_notifications(owner["id"]) == 0
    authenticate_as(admin["id"])
    list_response = client.get("/admin/review-cases?case_status=open")
    assert list_response.status_code == 200, list_response.text
    list_case = list_response.json()["cases"][0]
    assert list_case["case_category"] == "content_moderation"
    assert list_case["finding_summary"]["current_finding_count"] == 2
    assert set(list_case["finding_summary"]["current_issue_labels"]) == {
        "off_app_contact",
        "payment_pressure",
    }

    authenticate_as(owner["id"])
    same_text_response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json={"notes": risky_notes},
    )

    assert same_text_response.status_code == 200, same_text_response.text
    assert len(get_review_cases_for_sub_post(post["id"])) == 1
    assert len(get_review_findings_for_sub_post(post["id"])) == len(findings)

    authenticate_as(owner["id"])
    response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json={"notes": "Message me through Pickup Lane."},
    )

    assert response.status_code == 200, response.text
    updated_findings = get_review_findings_for_sub_post(post["id"])
    assert len(updated_findings) == len(findings)
    assert all(finding.current_match is False for finding in updated_findings)
    assert all(finding.cleared_at is not None for finding in updated_findings)
    assert len(get_review_cases_for_sub_post(post["id"])) == 1


def test_new_need_a_sub_risk_attaches_to_existing_content_moderation_case(
    client: TestClient,
):
    owner = create_user(client)
    post = create_sub_post(
        client,
        owner["id"],
        notes="Text me at 312-555-1234.",
    )
    cases = get_review_cases_for_sub_post(post["id"])
    assert len(cases) == 1

    authenticate_as(owner["id"])
    response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json={"payment_note": "Send deposit before approval."},
    )

    assert response.status_code == 200, response.text
    updated_cases = get_review_cases_for_sub_post(post["id"])
    findings = get_review_findings_for_sub_post(post["id"])
    assert len(updated_cases) == 1
    assert updated_cases[0].id == cases[0].id
    assert {finding.risk_area for finding in findings} == {
        "unsafe_post_text",
        "unsafe_payment_text",
    }
    assert {finding.finding_type for finding in findings} == {
        "off_app_contact",
        "payment_pressure",
    }
    assert {finding.review_case_id for finding in findings} == {cases[0].id}


def test_need_a_sub_owner_cancel_closes_open_content_moderation_case(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    owner = create_user(client)
    post = create_sub_post(
        client,
        owner["id"],
        notes="Text me at 312-555-1234 before approval.",
    )
    case = get_review_cases_for_sub_post(post["id"])[0]

    authenticate_as(owner["id"])
    cancel_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "No longer need a sub."},
    )

    assert cancel_response.status_code == 200, cancel_response.text
    snapshot = get_review_case_snapshot(case.id)
    assert snapshot["case_status"] == "closed"
    assert snapshot["closure_outcome"] == "no_action_needed"
    assert "cancelled by its owner" in str(snapshot["closure_reason"])
    assert snapshot["closed_by_user_id"] is None
    assert snapshot["closed_at"] is not None
    metadata = get_closed_event_metadata(case.id)
    assert metadata["closure_mode"] == "automatic"
    assert metadata["lifecycle_action"] == "owner_cancelled"
    assert metadata["trigger_actor_type"] == "owner"
    assert str(case.id) not in list_review_case_ids(
        client,
        admin["id"],
        case_status="open",
    )
    assert str(case.id) in list_review_case_ids(
        client,
        admin["id"],
        case_status="closed",
    )


def test_need_a_sub_admin_remove_closes_case_as_enforcement_and_notices_owner(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    owner = create_user(client)
    post = create_sub_post(
        client,
        owner["id"],
        notes="Text me at 312-555-1234 before approval.",
    )
    case = get_review_cases_for_sub_post(post["id"])[0]
    notice_count_before = count_admin_notice_notifications(owner["id"])

    authenticate_as(admin["id"])
    remove_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/remove",
        json={
            "remove_reason": "Unsafe off-app payment request.",
            "idempotency_key": f"remove-sub-review-{unique_suffix()}",
        },
    )

    assert remove_response.status_code == 200, remove_response.text
    snapshot = get_review_case_snapshot(case.id)
    assert snapshot["case_status"] == "closed"
    assert snapshot["closure_outcome"] == "enforcement_applied"
    assert "removed by an admin" in str(snapshot["closure_reason"])
    assert snapshot["closed_by_user_id"] == admin["id"]
    metadata = get_closed_event_metadata(case.id)
    assert metadata["lifecycle_action"] == "admin_removed"
    assert metadata["trigger_actor_type"] == "admin"
    assert metadata["linked_admin_action_id"]
    assert count_admin_notice_notifications(owner["id"]) == notice_count_before + 1
    assert str(case.id) not in list_review_case_ids(
        client,
        admin["id"],
        case_status="open",
    )


def test_community_game_host_cancel_closes_open_case_as_no_action_needed(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    host = create_user(client)
    game, case = create_risky_community_game(client, host)

    authenticate_as(host["id"])
    cancel_response = client.post(
        f"/games/{game['id']}/cancel",
        json={"cancel_reason": "Weather changed."},
    )

    assert cancel_response.status_code == 200, cancel_response.text
    snapshot = get_review_case_snapshot(case.id)
    assert snapshot["case_status"] == "closed"
    assert snapshot["closure_outcome"] == "no_action_needed"
    assert "cancelled by its host" in str(snapshot["closure_reason"])
    assert snapshot["closed_by_user_id"] is None
    metadata = get_closed_event_metadata(case.id)
    assert metadata["lifecycle_action"] == "host_cancelled"
    assert metadata["trigger_actor_type"] == "host"
    assert str(case.id) not in list_review_case_ids(
        client,
        admin["id"],
        case_status="open",
    )


def test_community_game_admin_cancellations_close_cases_with_locked_outcomes(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    moderation_host = create_user(client)
    operational_host = create_user(client)
    moderation_game, moderation_case = create_risky_community_game(
        client,
        moderation_host,
        note_suffix="moderation",
    )
    operational_game, operational_case = create_risky_community_game(
        client,
        operational_host,
        note_suffix="operations",
    )

    authenticate_as(admin["id"])
    moderation_cancel_response = client.post(
        f"/admin/community-games/{moderation_game['id']}/cancel",
        json={
            "reason": "Admin enforcement cancellation.",
            "idempotency_key": f"community-review-cancel-{unique_suffix()}",
        },
    )
    operational_cancel_response = client.post(
        f"/games/{operational_game['id']}/cancel",
        json={"cancel_reason": "Operational cancellation."},
    )

    assert moderation_cancel_response.status_code == 200, (
        moderation_cancel_response.text
    )
    assert operational_cancel_response.status_code == 200, (
        operational_cancel_response.text
    )
    moderation_snapshot = get_review_case_snapshot(moderation_case.id)
    operational_snapshot = get_review_case_snapshot(operational_case.id)
    assert moderation_snapshot["case_status"] == "closed"
    assert moderation_snapshot["closure_outcome"] == "enforcement_applied"
    assert moderation_snapshot["closed_by_user_id"] == admin["id"]
    assert get_closed_event_metadata(moderation_case.id)["lifecycle_action"] == (
        "admin_moderation_cancelled"
    )
    assert operational_snapshot["case_status"] == "closed"
    assert operational_snapshot["closure_outcome"] == "no_action_needed"
    assert operational_snapshot["closed_by_user_id"] == admin["id"]
    assert get_closed_event_metadata(operational_case.id)["lifecycle_action"] == (
        "admin_operational_cancelled"
    )


def test_community_game_admin_soft_delete_closes_case_as_enforcement(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    host = create_user(client)
    game, case = create_risky_community_game(client, host)

    authenticate_as(admin["id"])
    delete_response = client.delete(f"/games/{game['id']}")

    assert delete_response.status_code == 200, delete_response.text
    snapshot = get_review_case_snapshot(case.id)
    assert snapshot["case_status"] == "closed"
    assert snapshot["closure_outcome"] == "enforcement_applied"
    assert "deleted by an admin" in str(snapshot["closure_reason"])
    assert snapshot["closed_by_user_id"] == admin["id"]
    assert get_closed_event_metadata(case.id)["lifecycle_action"] == (
        "admin_soft_deleted"
    )
    assert str(case.id) not in list_review_case_ids(
        client,
        admin["id"],
        case_status="open",
    )
    detail_response = client.get(f"/admin/review-cases/{case.id}")
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["target_summary"]["status"] == "deleted"


def test_hidden_content_stays_open_but_completed_and_expired_content_cases_close(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    hidden_host = create_user(client)
    completed_game_host = create_user(client)
    hidden_post_owner = create_user(client)
    expired_owner = create_user(client)
    completed_post_owner = create_user(client)
    completed_post_requester = create_user(client)
    hidden_game, hidden_case = create_risky_community_game(
        client,
        hidden_host,
        note_suffix="hidden",
    )
    completed_game, completed_game_case = create_risky_community_game(
        client,
        completed_game_host,
        note_suffix="completed",
    )
    hidden_post = create_sub_post(
        client,
        hidden_post_owner["id"],
        notes="Text me at 312-555-1234 before approval.",
    )
    hidden_post_case = get_review_cases_for_sub_post(hidden_post["id"])[0]
    expired_post = create_sub_post(
        client,
        expired_owner["id"],
        notes="Text me at 312-555-1234 before approval.",
    )
    expired_case = get_review_cases_for_sub_post(expired_post["id"])[0]
    completed_post = create_sub_post(
        client,
        completed_post_owner["id"],
        notes="Text me at 312-555-1234 before approval.",
        subs_needed=1,
        positions=[
            {
                "position_label": "field_player",
                "player_group": "open",
                "spots_needed": 1,
                "sort_order": 0,
            },
        ],
    )
    completed_post_case = get_review_cases_for_sub_post(completed_post["id"])[0]
    completed_post_request = request_spot(
        client,
        completed_post_requester["id"],
        completed_post,
    )
    accept_request(client, completed_post_owner["id"], completed_post_request["id"])

    authenticate_as(admin["id"])
    hide_response = client.post(
        f"/admin/community-games/{hidden_game['id']}/hide",
        json={
            "reason": "Hide while review continues.",
            "idempotency_key": f"community-hide-review-{unique_suffix()}",
        },
    )
    assert hide_response.status_code == 200, hide_response.text
    hide_post_response = client.post(
        f"/admin/need-a-sub/{hidden_post['id']}/hide",
        json={
            "reason": "Hide while review continues.",
            "idempotency_key": f"need-sub-hide-review-{unique_suffix()}",
        },
    )
    assert hide_post_response.status_code == 200, hide_post_response.text
    completed_game_response = client.patch(
        f"/games/{completed_game['id']}",
        json={"game_status": "completed"},
    )
    assert completed_game_response.status_code == 200, completed_game_response.text
    move_sub_post_expiration_into_past(expired_post["id"])
    move_sub_post_expiration_into_past(completed_post["id"])
    with SessionLocal() as db:
        expiry_counts = expire_due_posts_and_requests(db)
    assert expiry_counts["posts_completed"] == 1
    assert expiry_counts["posts_expired"] == 1

    assert get_review_case_snapshot(hidden_case.id)["case_status"] == "open"
    assert get_review_case_snapshot(hidden_post_case.id)["case_status"] == "open"
    completed_game_snapshot = get_review_case_snapshot(completed_game_case.id)
    expired_snapshot = get_review_case_snapshot(expired_case.id)
    completed_post_snapshot = get_review_case_snapshot(completed_post_case.id)
    assert completed_game_snapshot["case_status"] == "closed"
    assert completed_game_snapshot["closure_outcome"] == "no_action_needed"
    assert completed_game_snapshot["closed_by_user_id"] == admin["id"]
    assert get_closed_event_metadata(completed_game_case.id)["lifecycle_action"] == (
        "game_completed"
    )
    assert expired_snapshot["case_status"] == "closed"
    assert expired_snapshot["closure_outcome"] == "no_action_needed"
    assert expired_snapshot["closed_by_user_id"] is None
    assert get_closed_event_metadata(expired_case.id)["lifecycle_action"] == (
        "post_expired"
    )
    assert completed_post_snapshot["case_status"] == "closed"
    assert completed_post_snapshot["closure_outcome"] == "no_action_needed"
    assert completed_post_snapshot["closed_by_user_id"] is None
    assert get_closed_event_metadata(completed_post_case.id)["lifecycle_action"] == (
        "post_completed"
    )
    open_case_ids = list_review_case_ids(client, admin["id"], case_status="open")
    assert str(hidden_case.id) in open_case_ids
    assert str(hidden_post_case.id) in open_case_ids
    assert str(completed_game_case.id) not in open_case_ids
    assert str(expired_case.id) not in open_case_ids
    assert str(completed_post_case.id) not in open_case_ids
    closed_case_ids = list_review_case_ids(client, admin["id"], case_status="closed")
    assert str(completed_game_case.id) in closed_case_ids
    assert str(expired_case.id) in closed_case_ids
    assert str(completed_post_case.id) in closed_case_ids
    hidden_detail_response = client.get(f"/admin/review-cases/{hidden_case.id}")
    hidden_post_detail_response = client.get(
        f"/admin/review-cases/{hidden_post_case.id}"
    )
    completed_detail_response = client.get(
        f"/admin/review-cases/{completed_game_case.id}"
    )
    expired_detail_response = client.get(f"/admin/review-cases/{expired_case.id}")
    completed_post_detail_response = client.get(
        f"/admin/review-cases/{completed_post_case.id}"
    )
    assert hidden_detail_response.status_code == 200, hidden_detail_response.text
    assert hidden_post_detail_response.status_code == 200, (
        hidden_post_detail_response.text
    )
    assert completed_detail_response.status_code == 200, (
        completed_detail_response.text
    )
    assert expired_detail_response.status_code == 200, expired_detail_response.text
    assert completed_post_detail_response.status_code == 200, (
        completed_post_detail_response.text
    )
    assert hidden_detail_response.json()["target_summary"]["status"] == "hidden"
    assert hidden_post_detail_response.json()["target_summary"]["status"] == "hidden"
    assert completed_detail_response.json()["target_summary"]["status"] == "completed"
    assert expired_detail_response.json()["target_summary"]["status"] == "expired"
    assert (
        completed_post_detail_response.json()["target_summary"]["status"]
        == "completed"
    )


def test_closed_content_moderation_case_is_not_reused_for_new_risk(
    client: TestClient,
):
    owner = create_user(client)
    post = create_sub_post(
        client,
        owner["id"],
        notes="Text me at 312-555-1234.",
    )
    first_case = get_review_cases_for_sub_post(post["id"])[0]
    close_review_case_directly(first_case.id)

    authenticate_as(owner["id"])
    clean_response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json={"notes": "Message me through Pickup Lane."},
    )
    risky_response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json={"notes": "Text me at 312-555-1234."},
    )

    assert clean_response.status_code == 200, clean_response.text
    assert risky_response.status_code == 200, risky_response.text
    cases = get_review_cases_for_sub_post(post["id"])
    assert len(cases) == 2
    assert cases[0].id == first_case.id
    assert cases[0].case_status == "closed"
    assert cases[1].case_status == "open"
    assert cases[1].case_category == "content_moderation"


def test_need_a_sub_create_still_succeeds_when_scanner_fails(
    client: TestClient,
    monkeypatch,
):
    from backend.services import moderation_surfacing_service

    owner = create_user(client)

    def raise_scanner(_fields):
        raise RuntimeError("scanner failed")

    monkeypatch.setattr(
        moderation_surfacing_service,
        "build_content_moderation_findings",
        raise_scanner,
    )

    post = create_sub_post(
        client,
        owner["id"],
        notes="Text me at 312-555-1234 and send deposit before approval.",
    )

    assert post["id"]
    assert get_review_findings_for_sub_post(post["id"]) == []
    assert count_admin_notice_notifications(owner["id"]) == 0


def test_community_game_host_edit_risky_text_surfaces_review_case(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )

    authenticate_as(host["id"])
    response = client.patch(
        f"/games/{game['id']}/host-edit",
        json={"game_notes": "Text me at 312-555-1212 before kickoff."},
    )

    assert response.status_code == 200, response.text
    cases = get_review_cases_for_game(game["id"])
    findings = get_review_findings_for_game(game["id"])
    assert len(cases) == 1
    assert cases[0].case_category == "content_moderation"
    assert cases[0].case_type == "community_game"
    assert len(findings) == 1
    finding = findings[0]
    assert finding.review_case_id == cases[0].id
    assert finding.risk_area == "unsafe_post_text"
    assert finding.finding_type == "off_app_contact"
    assert finding.source_field == "game_notes"
    assert finding.scanner_version
    assert "personal_info.phone_number" in (
        finding.metadata_ or {}
    )["matched_rule_ids"]
    evidence_text = " ".join(item["display_text"] for item in finding.evidence)
    assert "312-555-1212" in evidence_text
    assert count_admin_notice_notifications(host["id"]) == 0


def test_community_game_payment_detail_surfaces_payment_review_case(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )

    create_community_game_detail(
        client,
        game["id"],
        payment_methods_snapshot=[{"type": "venmo", "value": "@pickup-host"}],
        payment_instructions_snapshot=(
            "Send deposit before approval to hold your spot."
        ),
    )

    cases = get_review_cases_for_game(game["id"])
    findings = get_review_findings_for_game(game["id"])
    assert len(cases) == 1
    assert cases[0].case_category == "content_moderation"
    assert len(findings) == 1
    finding = findings[0]
    assert finding.review_case_id == cases[0].id
    assert finding.risk_area == "unsafe_payment_text"
    assert finding.finding_type == "payment_pressure"
    assert finding.source_field == "payment_instructions_snapshot"
    assert "payment_pressure.phrase" in (
        finding.metadata_ or {}
    )["matched_rule_ids"]
    assert count_admin_notice_notifications(host["id"]) == 0


def test_community_game_chat_detection_creates_parent_review_case(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    create_game_participant(
        client,
        host["id"],
        game["id"],
        participant_type="host",
        price_cents=0,
        roster_order=1,
    )
    chat = create_game_chat(client, game["id"])

    message = create_chat_message(
        client,
        chat["id"],
        host["id"],
        message_body="Text me at 312-555-9999 before kickoff.",
    )

    cases = get_review_cases_for_game(game["id"])
    signals = get_review_signals_for_game(game["id"])
    assert len(cases) == 1
    assert cases[0].case_category == "chat_moderation"
    assert get_review_findings_for_game(game["id"]) == []
    assert len(signals) == 1
    signal = signals[0]
    assert signal.review_case_id == cases[0].id
    assert signal.signal_category == "chat_moderation"
    assert signal.source == "chat_moderation"
    assert signal.created_by_user_id is None
    metadata = signal.metadata_ or {}
    assert metadata["chat_scope"] == "community_game"
    assert metadata["message_id"] == message["id"]
    assert metadata["field_name"] == "message_body"
    assert metadata["current_match"] is True
    assert "312-555-9999" in metadata["excerpt"]


def test_need_a_sub_chat_detection_creates_parent_case(
    client: TestClient,
):
    owner = create_user(client)
    player = create_user(client)
    post = create_sub_post(
        client,
        owner["id"],
        notes="Text me at 312-555-1234.",
    )
    initial_cases = get_review_cases_for_sub_post(post["id"])
    assert len(initial_cases) == 1
    assert initial_cases[0].case_category == "content_moderation"

    sub_request = request_spot(client, player["id"], post)
    accept_request(client, owner["id"], sub_request["id"])
    chat = ensure_sub_post_chat(client, owner["id"], post["id"])

    message = send_sub_chat_message(
        client,
        owner["id"],
        post["id"],
        chat["id"],
        "Text me at 312-555-0000 before the match.",
    )

    cases = get_review_cases_for_sub_post(post["id"])
    signals = get_review_signals_for_sub_post(post["id"])
    assert len(cases) == 2
    chat_case = next(
        review_case
        for review_case in cases
        if review_case.case_category == "chat_moderation"
    )
    assert len(signals) == 1
    chat_signal = signals[0]
    assert chat_signal.signal_category == "chat_moderation"
    assert chat_signal.review_case_id == chat_case.id
    assert chat_signal.source == "chat_moderation"
    metadata = chat_signal.metadata_ or {}
    assert metadata["chat_scope"] == "need_a_sub"
    assert metadata["message_id"] == message["id"]
    assert metadata["current_match"] is True
    assert "312-555-0000" in metadata["excerpt"]


def test_game_chat_send_still_succeeds_when_detector_fails(
    client: TestClient,
    monkeypatch,
):
    from backend.services import game_chat_service

    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    create_game_participant(
        client,
        host["id"],
        game["id"],
        participant_type="host",
        price_cents=0,
        roster_order=1,
    )
    chat = create_game_chat(client, game["id"])

    def raise_detector(_message_body, *, is_repeated_message=False):
        raise RuntimeError("detector failed")

    monkeypatch.setattr(game_chat_service, "detect_chat_message", raise_detector)

    message = create_chat_message(
        client,
        chat["id"],
        host["id"],
        message_body="Text me at 312-555-9999 before kickoff.",
    )

    assert message["id"]
    assert message["review_status"] == "clear"
    assert get_review_signals_for_game(game["id"]) == []
