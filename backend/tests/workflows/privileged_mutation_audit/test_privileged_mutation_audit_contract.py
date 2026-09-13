from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from threading import Barrier

import pytest
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from backend.models import (
    AdminAction,
    CommunityGameDetail,
    DurableJob,
    DurableJobEvent,
    Game,
    Payment,
    PaymentEvent,
    User,
    Venue,
)
from backend.schemas.community_game_detail_schema import (
    CommunityGameDetailCreate,
    CommunityGameDetailUpdate,
)
from backend.schemas.game_schema import GameUpdate
from backend.schemas.payment_event_schema import PaymentEventUpdate
from backend.services.admin_action_display_service import (
    list_admin_action_log,
    serialize_admin_action_detail_read,
)
from backend.services.admin_action_service import AUDIT_UNAVAILABLE_DETAIL

pytestmark = pytest.mark.suite_type("ordinary")

_BASE_TIME = datetime(2035, 7, 10, 18, 0, tzinfo=timezone.utc)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _user(label: str, *, role: str = "player") -> User:
    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws09-02b-{label}-{unique}",
        role=role,
        email=f"ws09-02b-{label}-{unique}@example.invalid",
        first_name="Audit",
        last_name=label,
        date_of_birth=date(1990, 1, 1),
        account_status="active",
        hosting_status="eligible",
    )


def _venue(label: str, creator_id: uuid.UUID | None = None) -> Venue:
    return Venue(
        id=uuid.uuid4(),
        name=f"Audit venue {label}",
        address_line_1="1 Audit Way",
        city="Chicago",
        state="IL",
        postal_code="60601",
        country_code="US",
        venue_status="approved",
        created_by_user_id=creator_id,
        approved_by_user_id=creator_id,
        approved_at=_BASE_TIME - timedelta(days=2),
        is_active=True,
    )


def _game(host: User, venue: Venue, label: str) -> Game:
    starts_at = _BASE_TIME + timedelta(days=len(label))
    return Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="none",
        publish_status="draft",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title=f"Audit game {label}",
        description="original description",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=host.id,
        created_by_user_id=host.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        starts_on_local=starts_at.date(),
        timezone="UTC",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=10,
        price_per_player_cents=0,
        currency="USD",
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=2,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="custom_hosted",
    )


def _payment(user: User) -> Payment:
    unique = uuid.uuid4()
    return Payment(
        id=uuid.uuid4(),
        payer_user_id=user.id,
        booking_id=None,
        game_id=None,
        payment_type="admin_charge",
        provider="stripe",
        provider_payment_intent_id=f"pi_ws09_02b_{unique}",
        idempotency_key=f"ws09-02b-payment-{unique}",
        amount_cents=500,
        currency="USD",
        payment_status="processing",
        payment_metadata={"test": "ws09-02b"},
    )


def _payment_event(*, processing_status: str = "pending") -> PaymentEvent:
    return PaymentEvent(
        id=uuid.uuid4(),
        payment_id=None,
        provider="stripe",
        provider_event_id=f"evt_ws09_02b_{uuid.uuid4()}",
        event_type="payment_intent.payment_failed",
        event_envelope={"private_provider_payload": "must-not-enter-audit"},
        provider_created_at=_BASE_TIME,
        processing_status=processing_status,
        processed_at=_BASE_TIME if processing_status == "processed" else None,
        processing_error_code=(
            "provider_private_failure" if processing_status == "failed" else None
        ),
    )


def _actions(db, action_type: str) -> list[AdminAction]:
    return list(
        db.scalars(
            select(AdminAction)
            .where(AdminAction.action_type == action_type)
            .order_by(AdminAction.created_at, AdminAction.id)
        ).all()
    )


def _persist_game_fixture(
    db,
    admin: User,
    host: User,
    venue: Venue,
    game: Game,
) -> None:
    db.add_all([admin, host])
    db.commit()
    db.add(venue)
    db.commit()
    db.add(game)
    db.commit()


def test_game_update_records_only_effective_field_names() -> None:
    from backend.services.game_service import update_game_workflow

    with _session() as db:
        admin = _user("admin", role="admin")
        host = _user("host")
        venue = _venue("game-update", host.id)
        game = _game(host, venue, "update")
        _persist_game_fixture(db, admin, host, venue, game)

        update_game_workflow(
            db,
            game.id,
            GameUpdate(
                title="Changed audit title",
                description="private free text that must not be audited",
                waitlist_enabled=True,
            ),
            admin,
        )

        actions = _actions(db, "update_game")
        assert len(actions) == 1
        assert actions[0].admin_user_id == admin.id
        assert actions[0].target_game_id == game.id
        assert actions[0].outcome == "succeeded"
        assert actions[0].metadata_ == {"changed_fields": ["description", "title"]}
        assert "private free text" not in str(actions[0].metadata_)


def test_staff_community_detail_create_and_update_use_safe_exact_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.community_game_detail_service as detail_service

    surfaced: list[uuid.UUID] = []
    monkeypatch.setattr(
        detail_service,
        "surface_community_game_text",
        lambda db, *, game_id: surfaced.append(game_id),
    )

    with _session() as db:
        admin = _user("detail-admin", role="admin")
        host = _user("detail-host")
        venue = _venue("detail", host.id)
        game = _game(host, venue, "detail")
        _persist_game_fixture(db, admin, host, venue, game)

        detail = detail_service.create_community_game_detail_workflow(
            db,
            CommunityGameDetailCreate(
                game_id=game.id,
                payment_methods_snapshot=[
                    {"type": "venmo", "value": "private-payment-handle"}
                ],
            ),
            admin,
        )
        detail_service.update_community_game_detail_workflow(
            db,
            detail.id,
            CommunityGameDetailUpdate(
                payment_methods_snapshot=[{"type": "cash", "value": "Cash"}]
            ),
            admin,
        )

        created = _actions(db, "create_community_game_detail")
        updated = _actions(db, "update_community_game_detail")
        assert len(created) == len(updated) == 1
        assert created[0].target_game_id == game.id
        assert created[0].metadata_ == {
            "source": "admin_community_game_detail",
            "after": {"detail_present": True, "game_id": str(game.id)},
        }
        assert updated[0].target_game_id == game.id
        assert updated[0].metadata_ == {
            "source": "admin_community_game_detail",
            "before": {"game_id": str(game.id)},
            "after": {
                "game_id": str(game.id),
                "changed_fields": ["payment_methods_snapshot"],
            },
        }
        assert "private-payment-handle" not in str(created[0].metadata_)
        assert "private-payment-handle" not in str(updated[0].metadata_)
        assert surfaced == [game.id, game.id]


def test_staff_detail_reassignment_records_both_game_ids_and_rejects_invalid_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.community_game_detail_service as detail_service

    monkeypatch.setattr(
        detail_service, "surface_community_game_text", lambda *a, **k: None
    )
    with _session() as db:
        admin = _user("reassign-admin", role="admin")
        host = _user("reassign-host")
        venue = _venue("reassign", host.id)
        first_game = _game(host, venue, "first-detail")
        second_game = _game(host, venue, "second-detail")
        official_game = _game(host, venue, "official-detail")
        official_game.game_type = "official"
        official_game.payment_collection_type = "in_app"
        official_game.policy_mode = "official_standard"
        official_game.host_guest_max = 0
        _persist_game_fixture(db, admin, host, venue, first_game)
        db.add_all([second_game, official_game])
        db.commit()
        detail = CommunityGameDetail(
            id=uuid.uuid4(),
            game_id=first_game.id,
            payment_methods_snapshot=[],
        )
        occupied_detail = CommunityGameDetail(
            id=uuid.uuid4(),
            game_id=first_game.id,
            payment_methods_snapshot=[],
        )
        db.add(detail)
        db.commit()

        detail_service.update_community_game_detail_workflow(
            db,
            detail.id,
            CommunityGameDetailUpdate(
                game_id=second_game.id,
                payment_methods_snapshot=[
                    {"type": "venmo", "value": "private-payment-handle"}
                ],
            ),
            admin,
        )
        action = _actions(db, "update_community_game_detail")[0]
        assert action.target_game_id == second_game.id
        assert action.metadata_ == {
            "source": "admin_community_game_detail",
            "before": {"game_id": str(first_game.id)},
            "after": {
                "game_id": str(second_game.id),
                "changed_fields": ["game_id", "payment_methods_snapshot"],
            },
        }
        assert "private-payment-handle" not in str(action.metadata_)

        db.add(occupied_detail)
        db.commit()
        for target_id, expected_status in (
            (first_game.id, status.HTTP_409_CONFLICT),
            (official_game.id, status.HTTP_400_BAD_REQUEST),
            (uuid.uuid4(), status.HTTP_404_NOT_FOUND),
        ):
            with pytest.raises(HTTPException) as exc_info:
                detail_service.update_community_game_detail_workflow(
                    db,
                    detail.id,
                    CommunityGameDetailUpdate(game_id=target_id),
                    admin,
                )
            assert exc_info.value.status_code == expected_status
            db.rollback()
            assert len(_actions(db, "update_community_game_detail")) == 1
            db.expire_all()
            assert db.get(CommunityGameDetail, detail.id).game_id == second_game.id


def test_game_and_venue_soft_delete_record_bounded_transitions() -> None:
    from backend.services.game_service import delete_game_workflow
    from backend.services.venue_service import delete_venue_record

    with _session() as db:
        admin = _user("delete-admin", role="admin")
        host = _user("delete-host")
        venue = _venue("game-delete", host.id)
        other_venue = _venue("venue-delete", host.id)
        game = _game(host, venue, "delete")
        _persist_game_fixture(db, admin, host, venue, game)
        db.add(other_venue)
        db.commit()

        delete_game_workflow(db, game.id, admin)
        delete_venue_record(db, other_venue.id, admin)

        game_action = _actions(db, "delete_game")[0]
        venue_action = _actions(db, "delete_venue")[0]
        assert game_action.metadata_ == {
            "source": "admin_soft_delete",
            "before": {"deleted": False},
            "after": {"deleted": True},
        }
        assert venue_action.metadata_ == {
            "source": "admin_soft_delete",
            "before": {
                "is_active": True,
                "venue_status": "approved",
                "deleted": False,
            },
            "after": {
                "is_active": False,
                "venue_status": "inactive",
                "deleted": True,
            },
        }
        assert other_venue.name not in str(venue_action.metadata_)

        game_action_id = game_action.id
        venue_action_id = venue_action.id
        game_id = game.id
        venue_id = other_venue.id
        admin_id = admin.id

    with _session() as db:
        viewer = db.get(User, admin_id)
        assert viewer is not None
        log_items = {
            item.id: item
            for item in list_admin_action_log(db, viewer_user=viewer).actions
        }
        for action_id, expected_label in (
            (game_action_id, f"Game {game_id}"),
            (venue_action_id, f"Venue {venue_id}"),
        ):
            assert log_items[action_id].target_label == expected_label
            detail = serialize_admin_action_detail_read(
                db,
                db.get(AdminAction, action_id),
                viewer_user=viewer,
            )
            assert detail.primary_target is not None
            assert detail.primary_target.label == expected_label
            assert detail.primary_target.destination_path is None


def test_payment_event_audit_classifies_work_and_omits_provider_content() -> None:
    from backend.services.payment_event_service import update_payment_event_record

    with _session() as db:
        admin = _user("payment-admin", role="admin")
        payer = _user("payer")
        payment = _payment(payer)
        event = _payment_event(processing_status="failed")
        db.add_all([admin, payer])
        db.commit()
        db.add_all([payment, event])
        db.commit()

        update_payment_event_record(
            db,
            event.id,
            PaymentEventUpdate(payment_id=payment.id, reprocess=True),
            admin,
        )

        actions = _actions(db, "update_payment_event")
        assert len(actions) == 1
        action = actions[0]
        assert action.target_payment_event_id == event.id
        assert action.target_payment_id == payment.id
        assert action.metadata_ == {
            "before": {"payment_id": None, "processing_status": "failed"},
            "after": {
                "payment_id": str(payment.id),
                "processing_status": "pending",
                "reprocess_requested": True,
                "durable_work_action": "ensured",
            },
        }
        metadata_text = str(action.metadata_)
        assert event.provider_event_id not in metadata_text
        assert event.event_type not in metadata_text
        assert "private_provider_payload" not in metadata_text
        assert "provider_private_failure" not in metadata_text

        update_payment_event_record(db, event.id, PaymentEventUpdate(), admin)
        update_payment_event_record(
            db,
            event.id,
            PaymentEventUpdate(payment_id=payment.id),
            admin,
        )
        update_payment_event_record(
            db,
            event.id,
            PaymentEventUpdate(reprocess=True),
            admin,
        )
        assert len(_actions(db, "update_payment_event")) == 1


def test_payment_event_requeue_and_active_job_classifications() -> None:
    from backend.services.payment_event_service import update_payment_event_record

    with _session() as db:
        admin = _user("reprocess-admin", role="admin")
        event = _payment_event(processing_status="failed")
        db.add_all([admin, event])
        db.commit()

        update_payment_event_record(
            db,
            event.id,
            PaymentEventUpdate(reprocess=True),
            admin,
        )
        job = db.scalar(
            select(DurableJob).where(
                DurableJob.origin_reference_id == str(event.id),
            )
        )
        assert job is not None
        job.status = "exhausted"
        job.attempt_count = job.maximum_attempts
        job.exhausted_at = datetime.now(timezone.utc)
        db.commit()

        update_payment_event_record(
            db,
            event.id,
            PaymentEventUpdate(reprocess=True),
            admin,
        )
        actions = _actions(db, "update_payment_event")
        assert actions[-1].metadata_["after"]["durable_work_action"] == "requeued"

        event.processing_status = "failed"
        event.processing_error_code = "internal-code"
        db.commit()
        update_payment_event_record(
            db,
            event.id,
            PaymentEventUpdate(reprocess=True),
            admin,
        )
        actions = _actions(db, "update_payment_event")
        assert actions[-1].metadata_["after"]["durable_work_action"] == "already_active"
        assert "internal-code" not in str(actions[-1].metadata_)


def test_payment_event_link_unlink_relink_and_same_value_noop() -> None:
    from backend.services.payment_event_service import update_payment_event_record

    with _session() as db:
        admin = _user("link-admin", role="admin")
        payer = _user("link-payer")
        first_payment = _payment(payer)
        second_payment = _payment(payer)
        event = _payment_event()
        db.add_all([admin, payer])
        db.commit()
        db.add_all([first_payment, second_payment, event])
        db.commit()
        event_id = event.id
        first_id = first_payment.id
        second_id = second_payment.id
        admin_id = admin.id

        for target_id in (first_id, None, second_id, second_id):
            update_payment_event_record(
                db, event_id, PaymentEventUpdate(payment_id=target_id), admin
            )

    with _session() as db:
        actions = _actions(db, "update_payment_event")
        assert len(actions) == 3
        assert [action.admin_user_id for action in actions] == [admin_id] * 3
        assert [action.target_payment_event_id for action in actions] == [event_id] * 3
        assert [action.target_payment_id for action in actions] == [
            first_id,
            None,
            second_id,
        ]
        assert [action.metadata_["before"]["payment_id"] for action in actions] == [
            None,
            str(first_id),
            None,
        ]
        assert [action.metadata_["after"]["payment_id"] for action in actions] == [
            str(first_id),
            None,
            str(second_id),
        ]
        assert all(
            action.metadata_["after"]["durable_work_action"] == "none"
            for action in actions
        )
        assert db.get(PaymentEvent, event_id).payment_id == second_id


def test_payment_event_reprocess_conflict_preserves_event_job_and_audit() -> None:
    from backend.services.payment_event_service import update_payment_event_record
    from backend.services.payment_job_service import enqueue_webhook_event_job

    with _session() as db:
        admin = _user("conflict-admin", role="admin")
        payer = _user("conflict-payer")
        payment = _payment(payer)
        event = _payment_event(processing_status="failed")
        db.add_all([admin, payer])
        db.commit()
        db.add_all([payment, event])
        db.commit()
        job = enqueue_webhook_event_job(db, event.id)
        job.status = "succeeded"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        event_id = event.id
        job_id = job.id

        with pytest.raises(HTTPException) as exc_info:
            update_payment_event_record(
                db,
                event_id,
                PaymentEventUpdate(payment_id=payment.id, reprocess=True),
                admin,
            )
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        db.rollback()

    with _session() as db:
        persisted_event = db.get(PaymentEvent, event_id)
        assert persisted_event.payment_id is None
        assert persisted_event.processing_status == "failed"
        assert db.get(DurableJob, job_id).status == "succeeded"
        assert _actions(db, "update_payment_event") == []


def test_payment_event_idempotent_enqueue_race_records_ensured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import payment_event_service
    from backend.services.payment_job_service import enqueue_webhook_event_job

    with _session() as db:
        admin = _user("ensure-race-admin", role="admin")
        event = _payment_event(processing_status="pending")
        db.add_all([admin, event])
        db.commit()
        event_id = event.id
        competing_job_id = None

        def competing_enqueue(owner_db, requested_event_id):
            nonlocal competing_job_id
            with _session() as competing_db:
                competing_job = enqueue_webhook_event_job(
                    competing_db, requested_event_id
                )
                competing_db.commit()
                competing_job_id = competing_job.id
            return enqueue_webhook_event_job(owner_db, requested_event_id)

        monkeypatch.setattr(
            payment_event_service, "enqueue_webhook_event_job", competing_enqueue
        )
        payment_event_service.update_payment_event_record(
            db, event_id, PaymentEventUpdate(reprocess=True), admin
        )

    with _session() as db:
        jobs = list(
            db.scalars(
                select(DurableJob).where(
                    DurableJob.origin_reference_id == str(event_id)
                )
            ).all()
        )
        assert len(jobs) == 1
        assert jobs[0].id == competing_job_id
        actions = _actions(db, "update_payment_event")
        assert len(actions) == 1
        assert actions[0].metadata_["after"]["durable_work_action"] == "ensured"
        assert db.get(PaymentEvent, event_id).processing_status == "pending"


@pytest.mark.parametrize(
    "workflow_name",
    [
        "game_update",
        "detail_create",
        "detail_update",
        "game_delete",
        "venue_delete",
        "payment_update",
    ],
)
@pytest.mark.parametrize("audit_failure_mode", ["validation", "constraint"])
def test_audit_failure_rolls_back_each_covered_mutation(
    monkeypatch: pytest.MonkeyPatch,
    workflow_name: str,
    audit_failure_mode: str,
) -> None:
    import backend.services.community_game_detail_service as detail_service
    from backend.services import game_service, payment_event_service, venue_service

    def fail_recording(*args, **kwargs):
        if audit_failure_mode == "validation":
            raise HTTPException(status_code=400, detail="private policy detail")
        db = args[0]
        db.add(
            AdminAction(
                id=uuid.uuid4(),
                admin_user_id=kwargs["admin_user_id"],
                action_type="invalid_private_action",
                outcome="succeeded",
                correlation_id=uuid.uuid4(),
                target_game_id=uuid.uuid4(),
            )
        )

    service_by_workflow = {
        "game_update": game_service,
        "detail_create": detail_service,
        "detail_update": detail_service,
        "game_delete": game_service,
        "venue_delete": venue_service,
        "payment_update": payment_event_service,
    }
    monkeypatch.setattr(
        service_by_workflow[workflow_name],
        "record_admin_action",
        fail_recording,
    )
    monkeypatch.setattr(
        detail_service, "surface_community_game_text", lambda *a, **k: None
    )

    with _session() as db:
        admin = _user(f"{workflow_name}-admin", role="admin")
        host = _user(f"{workflow_name}-host")
        venue = _venue(workflow_name, host.id)
        game = _game(host, venue, workflow_name)
        event = _payment_event(
            processing_status="failed"
            if workflow_name == "payment_update"
            else "pending"
        )
        _persist_game_fixture(db, admin, host, venue, game)
        db.add(event)
        payment_id = None
        prior_job_event_count = None
        if workflow_name == "payment_update":
            payment = _payment(host)
            db.add(payment)
            payment_id = payment.id
        db.commit()
        if workflow_name == "payment_update":
            prior_job_event_count = db.scalar(
                select(func.count()).select_from(DurableJobEvent)
            )
        detail = CommunityGameDetail(
            id=uuid.uuid4(),
            game_id=game.id,
            payment_methods_snapshot=[],
        )
        if workflow_name == "detail_update":
            db.add(detail)
            db.commit()

        with pytest.raises(HTTPException) as exc_info:
            if workflow_name == "game_update":
                game_service.update_game_workflow(
                    db, game.id, GameUpdate(title="must roll back"), admin
                )
            elif workflow_name == "detail_create":
                detail_service.create_community_game_detail_workflow(
                    db,
                    CommunityGameDetailCreate(game_id=game.id),
                    admin,
                )
            elif workflow_name == "detail_update":
                detail_service.update_community_game_detail_workflow(
                    db,
                    detail.id,
                    CommunityGameDetailUpdate(
                        payment_methods_snapshot=[{"type": "cash", "value": "Cash"}]
                    ),
                    admin,
                )
            elif workflow_name == "game_delete":
                game_service.delete_game_workflow(db, game.id, admin)
            elif workflow_name == "venue_delete":
                venue_service.delete_venue_record(db, venue.id, admin)
            else:
                assert payment_id is not None
                payment_event_service.update_payment_event_record(
                    db,
                    event.id,
                    PaymentEventUpdate(payment_id=payment_id, reprocess=True),
                    admin,
                )

        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert exc_info.value.detail == AUDIT_UNAVAILABLE_DETAIL
        db.expire_all()
        persisted_game = db.get(Game, game.id)
        persisted_venue = db.get(Venue, venue.id)
        persisted_event = db.get(PaymentEvent, event.id)
        assert persisted_game is not None
        assert persisted_game.title != "must roll back"
        assert persisted_game.deleted_at is None
        assert persisted_venue is not None
        assert persisted_venue.deleted_at is None
        assert persisted_event is not None
        assert persisted_event.payment_id is None
        if workflow_name == "payment_update":
            assert persisted_event.processing_status == "failed"
            with _session() as verification_db:
                assert (
                    verification_db.scalar(
                        select(func.count())
                        .select_from(DurableJob)
                        .where(DurableJob.origin_reference_id == str(event.id))
                    )
                    == 0
                )
                assert (
                    verification_db.scalar(
                        select(func.count()).select_from(DurableJobEvent)
                    )
                    == prior_job_event_count
                )
        if workflow_name == "detail_create":
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(CommunityGameDetail)
                    .where(CommunityGameDetail.game_id == game.id)
                )
                == 0
            )
        if workflow_name == "detail_update":
            persisted_detail = db.get(CommunityGameDetail, detail.id)
            assert persisted_detail is not None
            assert persisted_detail.payment_methods_snapshot == []
        assert db.scalar(select(func.count()).select_from(AdminAction)) == 0


@pytest.mark.parametrize("audit_failure_mode", ["validation", "constraint"])
def test_payment_event_audit_failure_rolls_back_exhausted_job_requeue(
    monkeypatch: pytest.MonkeyPatch,
    audit_failure_mode: str,
) -> None:
    from backend.services import payment_event_service
    from backend.services.payment_job_service import enqueue_webhook_event_job

    with _session() as db:
        admin = _user("requeue-rollback-admin", role="admin")
        event = _payment_event(processing_status="failed")
        db.add_all([admin, event])
        db.commit()
        job = enqueue_webhook_event_job(db, event.id)
        job.status = "exhausted"
        job.attempt_count = job.maximum_attempts
        job.exhausted_at = datetime.now(timezone.utc)
        db.commit()
        event_id = event.id
        job_id = job.id
        original_attempt_count = job.attempt_count
        original_event_count = db.scalar(
            select(func.count())
            .select_from(DurableJobEvent)
            .where(DurableJobEvent.job_id == job_id)
        )

        def fail_recording(owner_db, **kwargs):
            if audit_failure_mode == "validation":
                raise HTTPException(status_code=400, detail="private policy detail")
            owner_db.add(
                AdminAction(
                    id=uuid.uuid4(),
                    admin_user_id=kwargs["admin_user_id"],
                    action_type="invalid_private_action",
                    outcome="succeeded",
                    correlation_id=uuid.uuid4(),
                    target_payment_event_id=event_id,
                )
            )

        monkeypatch.setattr(
            payment_event_service, "record_admin_action", fail_recording
        )
        with pytest.raises(HTTPException) as exc_info:
            payment_event_service.update_payment_event_record(
                db,
                event_id,
                PaymentEventUpdate(reprocess=True),
                admin,
            )
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert exc_info.value.detail == AUDIT_UNAVAILABLE_DETAIL

    with _session() as verification_db:
        persisted_event = verification_db.get(PaymentEvent, event_id)
        persisted_job = verification_db.get(DurableJob, job_id)
        assert persisted_event is not None
        assert persisted_event.processing_status == "failed"
        assert persisted_job is not None
        assert persisted_job.status == "exhausted"
        assert persisted_job.attempt_count == original_attempt_count
        assert persisted_job.exhausted_at is not None
        assert (
            verification_db.scalar(
                select(func.count())
                .select_from(DurableJobEvent)
                .where(DurableJobEvent.job_id == job_id)
            )
            == original_event_count
        )
        assert _actions(verification_db, "update_payment_event") == []


def _concurrent_delete(
    kind: str, target_id: uuid.UUID, admin_id: uuid.UUID, barrier: Barrier
) -> str:
    barrier.wait(timeout=10)
    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        try:
            if kind == "game":
                from backend.services.game_service import delete_game_workflow

                delete_game_workflow(db, target_id, admin)
            else:
                from backend.services.venue_service import delete_venue_record

                delete_venue_record(db, target_id, admin)
            return "succeeded"
        except HTTPException as exc:
            db.rollback()
            return f"http-{exc.status_code}"


@pytest.mark.parametrize(
    ("kind", "action_type"), [("game", "delete_game"), ("venue", "delete_venue")]
)
def test_concurrent_soft_deletes_commit_one_action(
    kind: str,
    action_type: str,
) -> None:
    with _session() as db:
        admin = _user(f"{kind}-concurrent-admin", role="admin")
        host = _user(f"{kind}-concurrent-host")
        venue = _venue(f"{kind}-concurrent", host.id)
        game = _game(host, venue, f"{kind}-concurrent")
        _persist_game_fixture(db, admin, host, venue, game)
        target_id = game.id if kind == "game" else venue.id
        admin_id = admin.id

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: _concurrent_delete(kind, target_id, admin_id, barrier),
                range(2),
            )
        )

    assert sorted(results) == ["http-404", "succeeded"]
    with _session() as db:
        assert len(_actions(db, action_type)) == 1


def _concurrent_game_update(
    game_id: uuid.UUID,
    admin_id: uuid.UUID,
    barrier: Barrier,
) -> str:
    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        barrier.wait(timeout=10)
        from backend.services.game_service import update_game_workflow

        update_game_workflow(
            db,
            game_id,
            GameUpdate(title="Serialized title"),
            admin,
        )
        return "succeeded"


def test_concurrent_game_updates_derive_changes_from_locked_predecessor() -> None:
    with _session() as db:
        admin = _user("game-update-concurrent-admin", role="admin")
        host = _user("game-update-concurrent-host")
        venue = _venue("game-update-concurrent", host.id)
        game = _game(host, venue, "game-update-concurrent")
        _persist_game_fixture(db, admin, host, venue, game)
        game_id = game.id
        admin_id = admin.id

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: _concurrent_game_update(game_id, admin_id, barrier),
                range(2),
            )
        )

    assert results == ["succeeded", "succeeded"]
    with _session() as db:
        assert sorted(
            action.metadata_["changed_fields"] for action in _actions(db, "update_game")
        ) == [[], ["title"]]


def _concurrent_detail_update(
    detail_id: uuid.UUID,
    admin_id: uuid.UUID,
    barrier: Barrier,
) -> str:
    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        barrier.wait(timeout=10)
        from backend.services.community_game_detail_service import (
            update_community_game_detail_workflow,
        )

        update_community_game_detail_workflow(
            db,
            detail_id,
            CommunityGameDetailUpdate(
                payment_methods_snapshot=[{"type": "cash", "value": "Cash"}]
            ),
            admin,
        )
        return "succeeded"


def test_concurrent_detail_updates_derive_changes_from_locked_predecessor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.community_game_detail_service as detail_service

    monkeypatch.setattr(
        detail_service, "surface_community_game_text", lambda *a, **k: None
    )
    with _session() as db:
        admin = _user("detail-update-concurrent-admin", role="admin")
        host = _user("detail-update-concurrent-host")
        venue = _venue("detail-update-concurrent", host.id)
        game = _game(host, venue, "detail-update-concurrent")
        _persist_game_fixture(db, admin, host, venue, game)
        detail = CommunityGameDetail(
            id=uuid.uuid4(), game_id=game.id, payment_methods_snapshot=[]
        )
        db.add(detail)
        db.commit()
        detail_id = detail.id
        admin_id = admin.id

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: _concurrent_detail_update(detail_id, admin_id, barrier),
                range(2),
            )
        )

    assert results == ["succeeded", "succeeded"]
    with _session() as db:
        assert sorted(
            action.metadata_["after"]["changed_fields"]
            for action in _actions(db, "update_community_game_detail")
        ) == [[], ["payment_methods_snapshot"]]


def _concurrent_detail_create(
    game_id: uuid.UUID,
    admin_id: uuid.UUID,
    barrier: Barrier,
) -> str:
    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        barrier.wait(timeout=10)
        from backend.services.community_game_detail_service import (
            create_community_game_detail_workflow,
        )

        try:
            create_community_game_detail_workflow(
                db,
                CommunityGameDetailCreate(game_id=game_id),
                admin,
            )
            return "succeeded"
        except HTTPException as exc:
            db.rollback()
            return f"http-{exc.status_code}"


def test_concurrent_detail_creates_commit_one_detail_and_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.community_game_detail_service as detail_service

    monkeypatch.setattr(
        detail_service, "surface_community_game_text", lambda *a, **k: None
    )
    with _session() as db:
        admin = _user("detail-create-concurrent-admin", role="admin")
        host = _user("detail-create-concurrent-host")
        venue = _venue("detail-create-concurrent", host.id)
        game = _game(host, venue, "detail-create-concurrent")
        _persist_game_fixture(db, admin, host, venue, game)
        game_id = game.id
        admin_id = admin.id

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: _concurrent_detail_create(game_id, admin_id, barrier),
                range(2),
            )
        )

    assert sorted(results) == ["http-409", "succeeded"]
    with _session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(CommunityGameDetail)
                .where(CommunityGameDetail.game_id == game_id)
            )
            == 1
        )
        assert len(_actions(db, "create_community_game_detail")) == 1


def _concurrent_payment_reprocess(
    payment_event_id: uuid.UUID,
    admin_id: uuid.UUID,
    barrier: Barrier,
) -> str:
    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        barrier.wait(timeout=10)
        from backend.services.payment_event_service import update_payment_event_record

        update_payment_event_record(
            db,
            payment_event_id,
            PaymentEventUpdate(reprocess=True),
            admin,
        )
        return "succeeded"


def test_concurrent_payment_reprocess_records_only_effective_locked_change() -> None:
    with _session() as db:
        admin = _user("payment-concurrent-admin", role="admin")
        event = _payment_event(processing_status="failed")
        db.add_all([admin, event])
        db.commit()
        payment_event_id = event.id
        admin_id = admin.id

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: _concurrent_payment_reprocess(
                    payment_event_id, admin_id, barrier
                ),
                range(2),
            )
        )

    assert results == ["succeeded", "succeeded"]
    with _session() as db:
        actions = _actions(db, "update_payment_event")
        assert len(actions) == 1
        assert actions[0].metadata_["after"]["durable_work_action"] == "ensured"
        assert (
            db.scalar(
                select(func.count())
                .select_from(DurableJob)
                .where(DurableJob.origin_reference_id == str(payment_event_id))
            )
            == 1
        )


def test_commit_uncertainty_does_not_retry_or_claim_a_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_service import delete_venue_record

    with _session() as db:
        admin = _user("uncertain-commit-admin", role="admin")
        host = _user("uncertain-commit-host")
        venue = _venue("uncertain-commit", host.id)
        db.add_all([admin, host])
        db.commit()
        db.add(venue)
        db.commit()
        venue_id = venue.id
        real_commit = db.commit
        commit_calls = 0

        def commit_then_report_unknown() -> None:
            nonlocal commit_calls
            commit_calls += 1
            real_commit()
            raise OperationalError(
                "COMMIT",
                {},
                RuntimeError("simulated connection loss after commit"),
            )

        monkeypatch.setattr(db, "commit", commit_then_report_unknown)
        with pytest.raises(OperationalError):
            delete_venue_record(db, venue_id, admin)
        assert commit_calls == 1

    with _session() as verification_db:
        persisted_venue = verification_db.get(Venue, venue_id)
        assert persisted_venue is not None
        assert persisted_venue.deleted_at is not None
        assert len(_actions(verification_db, "delete_venue")) == 1


def test_post_commit_refresh_failure_keeps_mutation_and_action_committed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_service import delete_venue_record

    with _session() as db:
        admin = _user("refresh-failure-admin", role="admin")
        host = _user("refresh-failure-host")
        venue = _venue("refresh-failure", host.id)
        db.add_all([admin, host])
        db.commit()
        db.add(venue)
        db.commit()
        venue_id = venue.id

        def fail_refresh(*args, **kwargs) -> None:
            del args, kwargs
            raise RuntimeError("simulated post-commit serialization failure")

        monkeypatch.setattr(db, "refresh", fail_refresh)
        with pytest.raises(
            RuntimeError, match="simulated post-commit serialization failure"
        ):
            delete_venue_record(db, venue_id, admin)

    with _session() as verification_db:
        persisted_venue = verification_db.get(Venue, venue_id)
        assert persisted_venue is not None
        assert persisted_venue.deleted_at is not None
        assert len(_actions(verification_db, "delete_venue")) == 1


def test_post_commit_detail_surfacing_failure_keeps_detail_and_action_committed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.community_game_detail_service as detail_service

    with _session() as db:
        admin = _user("surface-failure-admin", role="admin")
        host = _user("surface-failure-host")
        venue = _venue("surface-failure", host.id)
        game = _game(host, venue, "surface-failure")
        _persist_game_fixture(db, admin, host, venue, game)
        game_id = game.id

        def fail_surfacing(*args, **kwargs) -> None:
            del args, kwargs
            raise RuntimeError("simulated post-commit moderation failure")

        monkeypatch.setattr(
            detail_service, "surface_community_game_text", fail_surfacing
        )
        with pytest.raises(
            RuntimeError, match="simulated post-commit moderation failure"
        ):
            detail_service.create_community_game_detail_workflow(
                db,
                CommunityGameDetailCreate(game_id=game_id),
                admin,
            )

    with _session() as verification_db:
        assert (
            verification_db.scalar(
                select(func.count())
                .select_from(CommunityGameDetail)
                .where(CommunityGameDetail.game_id == game_id)
            )
            == 1
        )
        assert len(_actions(verification_db, "create_community_game_detail")) == 1
