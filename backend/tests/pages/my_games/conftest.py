from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest

from backend.database import SessionLocal
from backend.models import (
    Game,
    GameImage,
    GameParticipant,
    ParticipantStatusHistory,
    SubPost,
    SubPostPosition,
    SubPostRequest,
    SubPostRequestStatusHistory,
    Venue,
)
from backend.tests.compliance.runtime import backend_test_evidence as backend_test_evidence


MY_GAMES_TEST_TZ = "America/Chicago"


def local_start_date(starts_at: datetime, timezone_name: str = MY_GAMES_TEST_TZ):
    return starts_at.astimezone(ZoneInfo(timezone_name)).date()


@pytest.fixture
def freeze_my_games_now(monkeypatch: pytest.MonkeyPatch) -> Callable[[datetime], None]:
    def _freeze(now: datetime) -> None:
        import backend.services.game_service as game_service
        import backend.services.need_a_sub_lifecycle_service as need_a_sub_lifecycle_service
        import backend.services.need_a_sub_post_service as need_a_sub_post_service

        class FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                if tz is None:
                    return now.replace(tzinfo=None)
                return now.astimezone(tz)

        monkeypatch.setattr(game_service, "datetime", FrozenDatetime)
        monkeypatch.setattr(need_a_sub_lifecycle_service, "now_utc", lambda: now)
        monkeypatch.setattr(need_a_sub_post_service, "now_utc", lambda: now)

    return _freeze


@pytest.fixture
def my_games_factory():
    return MyGamesFactory()


class MyGamesFactory:
    def create_venue(self, user_id: str | UUID, **overrides: object) -> Venue:
        now = datetime.now(UTC).replace(microsecond=0)
        venue = Venue(
            id=overrides.pop("id", uuid4()),
            name=overrides.pop("name", "My Games Test Field"),
            address_line_1=overrides.pop("address_line_1", "123 Test Ave"),
            city=overrides.pop("city", "Chicago"),
            state=overrides.pop("state", "IL"),
            postal_code=overrides.pop("postal_code", "60601"),
            country_code=overrides.pop("country_code", "US"),
            neighborhood=overrides.pop("neighborhood", None),
            venue_status=overrides.pop("venue_status", "approved"),
            created_by_user_id=UUID(str(user_id)),
            approved_by_user_id=UUID(str(user_id)),
            approved_at=overrides.pop("approved_at", now),
            is_active=overrides.pop("is_active", True),
            created_at=overrides.pop("created_at", now),
            updated_at=overrides.pop("updated_at", now),
            deleted_at=overrides.pop("deleted_at", None),
        )
        for key, value in overrides.items():
            setattr(venue, key, value)

        with SessionLocal() as db:
            db.add(venue)
            db.commit()
            db.refresh(venue)
            return venue

    def create_game(
        self,
        *,
        user_id: str | UUID,
        starts_at: datetime,
        ends_at: datetime | None = None,
        host_user_id: str | UUID | None = None,
        created_by_user_id: str | UUID | None = None,
        venue_id: str | UUID | None = None,
        **overrides: object,
    ) -> Game:
        now = datetime.now(UTC).replace(microsecond=0)
        created_by = UUID(str(created_by_user_id or user_id))
        host_id = UUID(str(host_user_id)) if host_user_id is not None else created_by
        if venue_id is None:
            venue = self.create_venue(created_by)
            venue_uuid = venue.id
        else:
            venue_uuid = UUID(str(venue_id))

        game_status = str(overrides.pop("game_status", "active"))
        publish_status = str(overrides.pop("publish_status", "published"))
        game_type = str(overrides.pop("game_type", "community"))
        payment_collection_type = str(
            overrides.pop(
                "payment_collection_type",
                "external_host" if game_type == "community" else "in_app",
            )
        )
        policy_mode = str(
            overrides.pop(
                "policy_mode",
                "custom_hosted" if game_type == "community" else "official_standard",
            )
        )
        ended_at = ends_at or starts_at + timedelta(hours=2)
        cancelled_at = overrides.pop(
            "cancelled_at",
            now if game_status == "cancelled" else None,
        )
        completed_at = overrides.pop(
            "completed_at",
            ended_at if game_status == "completed" else None,
        )
        price_per_player_cents = int(overrides.pop("price_per_player_cents", 0))

        game = Game(
            id=overrides.pop("id", uuid4()),
            game_type=game_type,
            payment_collection_type=payment_collection_type,
            publish_status=publish_status,
            game_status=game_status,
            public_visibility_status=overrides.pop(
                "public_visibility_status", "visible"
            ),
            join_enforcement_status=overrides.pop("join_enforcement_status", "open"),
            title=overrides.pop("title", "My Games Test Match"),
            description=overrides.pop("description", None),
            venue_id=venue_uuid,
            venue_name_snapshot=overrides.pop(
                "venue_name_snapshot", "My Games Test Field"
            ),
            address_snapshot=overrides.pop("address_snapshot", "123 Test Ave"),
            city_snapshot=overrides.pop("city_snapshot", "Chicago"),
            state_snapshot=overrides.pop("state_snapshot", "IL"),
            neighborhood_snapshot=overrides.pop("neighborhood_snapshot", None),
            host_user_id=host_id,
            created_by_user_id=created_by,
            starts_at=starts_at,
            ends_at=ended_at,
            starts_on_local=local_start_date(starts_at),
            timezone=overrides.pop("timezone", MY_GAMES_TEST_TZ),
            sport_type=overrides.pop("sport_type", "soccer"),
            format_label=overrides.pop("format_label", "5v5"),
            game_player_group=overrides.pop("game_player_group", "coed"),
            skill_level=overrides.pop("skill_level", "any"),
            environment_type=overrides.pop("environment_type", "indoor"),
            total_spots=overrides.pop("total_spots", 10),
            price_per_player_cents=price_per_player_cents,
            currency=overrides.pop("currency", "USD"),
            minimum_age=overrides.pop("minimum_age", None),
            allow_guests=overrides.pop("allow_guests", True),
            max_guests_per_booking=overrides.pop("max_guests_per_booking", 2),
            host_guest_max=overrides.pop("host_guest_max", 0),
            waitlist_enabled=overrides.pop("waitlist_enabled", True),
            is_chat_enabled=overrides.pop("is_chat_enabled", True),
            policy_mode=policy_mode,
            custom_rules_text=overrides.pop("custom_rules_text", None),
            custom_cancellation_text=overrides.pop("custom_cancellation_text", None),
            game_notes=overrides.pop("game_notes", None),
            parking_notes=overrides.pop("parking_notes", None),
            published_at=overrides.pop(
                "published_at",
                now if publish_status == "published" else None,
            ),
            cancelled_at=cancelled_at,
            cancelled_by_user_id=overrides.pop("cancelled_by_user_id", None),
            cancellation_source=overrides.pop(
                "cancellation_source",
                "host" if game_status == "cancelled" else None,
            ),
            cancel_reason=overrides.pop("cancel_reason", None),
            completed_at=completed_at,
            completed_by_user_id=overrides.pop("completed_by_user_id", None),
            created_at=overrides.pop("created_at", now),
            updated_at=overrides.pop("updated_at", now),
            deleted_at=overrides.pop("deleted_at", None),
        )
        for key, value in overrides.items():
            setattr(game, key, value)

        with SessionLocal() as db:
            db.add(game)
            db.commit()
            db.refresh(game)
            return game

    def create_participant(
        self,
        *,
        game_id: str | UUID,
        user_id: str | UUID | None,
        participant_status: str = "confirmed",
        participant_type: str = "registered_user",
        guest_of_user_id: str | UUID | None = None,
        **overrides: object,
    ) -> GameParticipant:
        now = datetime.now(UTC).replace(microsecond=0)
        cancelled_statuses = {"cancelled", "late_cancelled", "removed", "refunded"}
        participant = GameParticipant(
            id=overrides.pop("id", uuid4()),
            game_id=UUID(str(game_id)),
            booking_id=overrides.pop("booking_id", None),
            participant_type=participant_type,
            user_id=UUID(str(user_id)) if user_id is not None else None,
            guest_of_user_id=UUID(str(guest_of_user_id))
            if guest_of_user_id is not None
            else None,
            guest_name=overrides.pop(
                "guest_name", "Guest Player" if participant_type == "guest" else None
            ),
            guest_email=overrides.pop("guest_email", None),
            guest_phone=overrides.pop("guest_phone", None),
            display_name_snapshot=overrides.pop("display_name_snapshot", "Test User"),
            participant_status=participant_status,
            attendance_status=overrides.pop("attendance_status", "unknown"),
            cancellation_type=overrides.pop("cancellation_type", "none"),
            price_cents=overrides.pop("price_cents", 0),
            currency=overrides.pop("currency", "USD"),
            roster_order=overrides.pop("roster_order", 1),
            joined_at=overrides.pop("joined_at", now),
            confirmed_at=overrides.pop(
                "confirmed_at",
                now if participant_status == "confirmed" else None,
            ),
            cancelled_at=overrides.pop(
                "cancelled_at",
                now if participant_status in cancelled_statuses else None,
            ),
            checked_in_at=overrides.pop("checked_in_at", None),
            marked_attendance_by_user_id=overrides.pop(
                "marked_attendance_by_user_id", None
            ),
            attendance_decided_at=overrides.pop("attendance_decided_at", None),
            attendance_notes=overrides.pop("attendance_notes", None),
            created_at=overrides.pop("created_at", now),
            updated_at=overrides.pop("updated_at", now),
        )
        for key, value in overrides.items():
            setattr(participant, key, value)

        with SessionLocal() as db:
            db.add(participant)
            db.commit()
            db.refresh(participant)
            return participant

    def create_participant_history(
        self,
        *,
        participant_id: str | UUID,
        old_status: str | None,
        new_status: str,
        change_source: str,
        created_at: datetime,
        **overrides: object,
    ) -> ParticipantStatusHistory:
        history = ParticipantStatusHistory(
            id=overrides.pop("id", uuid4()),
            participant_id=UUID(str(participant_id)),
            old_participant_status=old_status,
            new_participant_status=new_status,
            old_attendance_status=overrides.pop("old_attendance_status", None),
            new_attendance_status=overrides.pop("new_attendance_status", None),
            changed_by_user_id=overrides.pop("changed_by_user_id", None),
            change_source=change_source,
            change_reason=overrides.pop("change_reason", None),
            created_at=created_at,
        )
        for key, value in overrides.items():
            setattr(history, key, value)

        with SessionLocal() as db:
            db.add(history)
            db.commit()
            db.refresh(history)
            return history

    def create_game_image(
        self,
        *,
        game_id: str | UUID,
        image_url: str = "https://example.com/my-games-primary.jpg",
        **overrides: object,
    ) -> GameImage:
        now = datetime.now(UTC).replace(microsecond=0)
        image = GameImage(
            id=overrides.pop("id", uuid4()),
            game_id=UUID(str(game_id)),
            uploaded_by_user_id=overrides.pop("uploaded_by_user_id", None),
            image_url=image_url,
            image_role=overrides.pop("image_role", "card"),
            image_status=overrides.pop("image_status", "active"),
            is_primary=overrides.pop("is_primary", True),
            sort_order=overrides.pop("sort_order", 0),
            created_at=overrides.pop("created_at", now),
            updated_at=overrides.pop("updated_at", now),
            deleted_at=overrides.pop("deleted_at", None),
        )
        for key, value in overrides.items():
            setattr(image, key, value)

        with SessionLocal() as db:
            db.add(image)
            db.commit()
            db.refresh(image)
            return image

    def create_sub_post(
        self,
        *,
        owner_user_id: str | UUID,
        starts_at: datetime,
        ends_at: datetime | None = None,
        **overrides: object,
    ) -> tuple[SubPost, SubPostPosition]:
        now = datetime.now(UTC).replace(microsecond=0)
        post_status = str(overrides.pop("post_status", "active"))
        ended_at = ends_at or starts_at + timedelta(hours=2)
        post = SubPost(
            id=overrides.pop("id", uuid4()),
            owner_user_id=UUID(str(owner_user_id)),
            post_status=post_status,
            public_visibility_status=overrides.pop(
                "public_visibility_status", "visible"
            ),
            sport_type=overrides.pop("sport_type", "soccer"),
            format_label=overrides.pop("format_label", "5v5"),
            environment_type=overrides.pop("environment_type", "indoor"),
            skill_level=overrides.pop("skill_level", "any"),
            game_player_group=overrides.pop("game_player_group", "coed"),
            team_name=overrides.pop("team_name", None),
            starts_at=starts_at,
            ends_at=ended_at,
            starts_on_local=local_start_date(starts_at),
            timezone=overrides.pop("timezone", MY_GAMES_TEST_TZ),
            location_name=overrides.pop("location_name", "Sub Test Field"),
            address_line_1=overrides.pop("address_line_1", "321 Sub Ave"),
            city=overrides.pop("city", "Chicago"),
            state=overrides.pop("state", "IL"),
            postal_code=overrides.pop("postal_code", "60601"),
            country_code=overrides.pop("country_code", "US"),
            neighborhood=overrides.pop("neighborhood", None),
            subs_needed=overrides.pop("subs_needed", 1),
            price_due_at_venue_cents=overrides.pop("price_due_at_venue_cents", 0),
            currency=overrides.pop("currency", "USD"),
            payment_note=overrides.pop("payment_note", None),
            notes=overrides.pop("notes", None),
            expires_at=overrides.pop("expires_at", starts_at),
            filled_at=overrides.pop(
                "filled_at",
                now if post_status == "completed" else None,
            ),
            canceled_at=overrides.pop(
                "canceled_at",
                now if post_status == "cancelled" else None,
            ),
            canceled_by_user_id=overrides.pop("canceled_by_user_id", None),
            cancel_reason=overrides.pop("cancel_reason", None),
            removed_at=overrides.pop(
                "removed_at",
                now if post_status == "removed" else None,
            ),
            removed_by_user_id=overrides.pop("removed_by_user_id", None),
            remove_reason=overrides.pop("remove_reason", None),
            created_at=overrides.pop("created_at", now),
            updated_at=overrides.pop("updated_at", now),
        )
        for key, value in overrides.items():
            setattr(post, key, value)

        position = SubPostPosition(
            id=uuid4(),
            sub_post_id=post.id,
            position_label="field_player",
            player_group="open",
            spots_needed=1,
            sort_order=0,
            created_at=now,
            updated_at=now,
        )

        with SessionLocal() as db:
            db.add(post)
            db.add(position)
            db.commit()
            db.refresh(post)
            db.refresh(position)
            return post, position

    def create_sub_position(
        self,
        *,
        post_id: str | UUID,
        position_label: str = "goalkeeper",
        player_group: str = "open",
        **overrides: object,
    ) -> SubPostPosition:
        now = datetime.now(UTC).replace(microsecond=0)
        position = SubPostPosition(
            id=overrides.pop("id", uuid4()),
            sub_post_id=UUID(str(post_id)),
            position_label=position_label,
            player_group=player_group,
            spots_needed=overrides.pop("spots_needed", 1),
            sort_order=overrides.pop("sort_order", 1),
            created_at=overrides.pop("created_at", now),
            updated_at=overrides.pop("updated_at", now),
        )
        for key, value in overrides.items():
            setattr(position, key, value)

        with SessionLocal() as db:
            db.add(position)
            db.commit()
            db.refresh(position)
            return position

    def create_sub_request(
        self,
        *,
        post_id: str | UUID,
        position_id: str | UUID,
        requester_user_id: str | UUID,
        request_status: str = "confirmed",
        **overrides: object,
    ) -> SubPostRequest:
        now = datetime.now(UTC).replace(microsecond=0)
        request = SubPostRequest(
            id=overrides.pop("id", uuid4()),
            sub_post_id=UUID(str(post_id)),
            sub_post_position_id=UUID(str(position_id)),
            requester_user_id=UUID(str(requester_user_id)),
            request_status=request_status,
            confirmed_at=overrides.pop(
                "confirmed_at", now if request_status == "confirmed" else None
            ),
            declined_at=overrides.pop(
                "declined_at", now if request_status == "declined" else None
            ),
            sub_waitlisted_at=overrides.pop(
                "sub_waitlisted_at",
                now if request_status == "sub_waitlist" else None,
            ),
            canceled_at=overrides.pop(
                "canceled_at",
                now
                if request_status in {"canceled_by_player", "canceled_by_owner"}
                else None,
            ),
            expired_at=overrides.pop(
                "expired_at", now if request_status == "expired" else None
            ),
            no_show_reported_at=overrides.pop(
                "no_show_reported_at",
                now if request_status == "no_show_reported" else None,
            ),
            created_at=overrides.pop("created_at", now),
            updated_at=overrides.pop("updated_at", now),
        )
        for key, value in overrides.items():
            setattr(request, key, value)

        with SessionLocal() as db:
            db.add(request)
            db.commit()
            db.refresh(request)
            return request

    def create_sub_request_history(
        self,
        *,
        request_id: str | UUID,
        old_status: str | None,
        new_status: str,
        change_source: str,
        created_at: datetime,
        **overrides: object,
    ) -> SubPostRequestStatusHistory:
        history = SubPostRequestStatusHistory(
            id=overrides.pop("id", uuid4()),
            sub_post_request_id=UUID(str(request_id)),
            old_status=old_status,
            new_status=new_status,
            changed_by_user_id=overrides.pop("changed_by_user_id", None),
            change_source=change_source,
            change_reason=overrides.pop("change_reason", None),
            created_at=created_at,
        )
        for key, value in overrides.items():
            setattr(history, key, value)

        with SessionLocal() as db:
            db.add(history)
            db.commit()
            db.refresh(history)
            return history
