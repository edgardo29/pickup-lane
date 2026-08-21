from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest

from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    _add_users,
    _auth_headers,
    _client,
    _count_model_rows,
    _install_tokens_for_users,
    _session,
    _user,
)

pytestmark = pytest.mark.suite_type("ordinary")


def _venue(label: str, *, creator_id: uuid.UUID, admin_id: uuid.UUID) -> Any:
    from backend.models import Venue

    unique = uuid.uuid4()
    return Venue(
        id=uuid.uuid4(),
        name=f"WS03D Venue {label}",
        address_line_1=f"{unique.int % 10000} Test Avenue",
        city="Chicago",
        state="IL",
        postal_code="60601",
        country_code="US",
        venue_status="approved",
        created_by_user_id=creator_id,
        approved_by_user_id=admin_id,
        approved_at=datetime.now(timezone.utc),
        is_active=True,
    )


def _official_game(
    label: str,
    *,
    venue: Venue,
    admin_id: uuid.UUID,
) -> Any:
    from backend.models import Game

    starts_at = datetime.now(timezone.utc) + timedelta(days=7)
    return Game(
        id=uuid.uuid4(),
        game_type="official",
        payment_collection_type="in_app",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title=f"WS03D Official Game {label}",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=None,
        created_by_user_id=admin_id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        starts_on_local=starts_at.date(),
        timezone="America/Chicago",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=10,
        price_per_player_cents=1200,
        allow_guests=False,
        max_guests_per_booking=0,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="official_standard",
        published_at=datetime.now(timezone.utc),
    )


def _community_game(
    label: str,
    *,
    venue: Venue,
    host_user_id: uuid.UUID,
    creator_id: uuid.UUID,
) -> Any:
    from backend.models import Game

    starts_at = datetime.now(timezone.utc) + timedelta(days=8)
    return Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="external_host",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title=f"WS03D Community Game {label}",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=host_user_id,
        created_by_user_id=creator_id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        starts_on_local=starts_at.date(),
        timezone="America/Chicago",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=10,
        price_per_player_cents=1200,
        allow_guests=True,
        max_guests_per_booking=2,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="custom_hosted",
        published_at=datetime.now(timezone.utc),
    )


def _persist_game_fixture(label: str, *, admin: Any, creator: Any) -> tuple[uuid.UUID, uuid.UUID]:
    with _session() as db:
        venue = _venue(label, creator_id=creator.id, admin_id=admin.id)
        db.add(venue)
        db.flush()
        game = _official_game(label, venue=venue, admin_id=admin.id)
        db.add(game)
        db.commit()
        return game.id, venue.id


def _persist_community_game_fixture(
    label: str,
    *,
    admin: Any,
    host: Any,
) -> tuple[uuid.UUID, uuid.UUID]:
    from backend.models import CommunityGameDetail

    with _session() as db:
        venue = _venue(label, creator_id=host.id, admin_id=admin.id)
        db.add(venue)
        db.flush()
        game = _community_game(
            label,
            venue=venue,
            host_user_id=host.id,
            creator_id=host.id,
        )
        db.add(game)
        db.flush()
        db.add(
            CommunityGameDetail(
                id=uuid.uuid4(),
                game_id=game.id,
                payment_methods_snapshot=[],
                payment_instructions_snapshot=f"{label} host payment instructions",
                payment_text_moderation_status="visible",
            )
        )
        db.commit()
        return game.id, venue.id


def _persist_venue_image_fixture(
    label: str,
    *,
    venue_id: uuid.UUID,
    admin_id: uuid.UUID,
) -> uuid.UUID:
    from backend.models import VenueImage

    with _session() as db:
        image = VenueImage(
            id=uuid.uuid4(),
            venue_id=venue_id,
            uploaded_by_user_id=admin_id,
            storage_provider="r2",
            storage_object_key=f"ws03d/{label}/{uuid.uuid4()}.jpg",
            storage_bucket="test-venue-images",
            storage_account_id="test-storage-account",
            content_type="image/jpeg",
            size_bytes=1200,
            etag="test-etag",
            image_role="gallery",
            image_status="active",
            is_primary=False,
            sort_order=0,
            alt_text="Original venue image alt text.",
            caption="Original venue image caption.",
            upload_requested_at=datetime.now(timezone.utc),
            upload_completed_at=datetime.now(timezone.utc),
        )
        db.add(image)
        db.commit()
        return image.id


def _persist_sub_post_fixture(label: str, *, owner: Any) -> uuid.UUID:
    from backend.models import SubPost

    starts_at = datetime.now(timezone.utc) + timedelta(days=5)
    with _session() as db:
        post = SubPost(
            id=uuid.uuid4(),
            owner_user_id=owner.id,
            post_status="active",
            public_visibility_status="visible",
            sport_type="soccer",
            format_label="5v5",
            environment_type="indoor",
            skill_level="any",
            game_player_group="coed",
            team_name=f"WS03D Need a Sub {label}",
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            starts_on_local=starts_at.date(),
            timezone="America/Chicago",
            location_name=f"WS03D Sub Field {label}",
            address_line_1="400 Test Avenue",
            city="Chicago",
            state="IL",
            postal_code="60601",
            country_code="US",
            subs_needed=1,
            price_due_at_venue_cents=0,
            currency="USD",
            expires_at=starts_at - timedelta(hours=2),
        )
        db.add(post)
        db.commit()
        return post.id


def _persist_waitlist_entry_fixture(
    *,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
) -> uuid.UUID:
    from backend.models import WaitlistEntry

    now = datetime.now(timezone.utc)
    with _session() as db:
        entry = WaitlistEntry(
            id=uuid.uuid4(),
            game_id=game_id,
            user_id=user_id,
            party_size=1,
            position=1,
            waitlist_status="active",
            joined_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(entry)
        db.commit()
        return entry.id


def _persist_sub_post_request_fixture(
    *,
    post_id: uuid.UUID,
    requester_user_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    from backend.models import SubPostPosition, SubPostRequest

    now = datetime.now(timezone.utc)
    with _session() as db:
        position = SubPostPosition(
            id=uuid.uuid4(),
            sub_post_id=post_id,
            position_label="field_player",
            player_group="open",
            spots_needed=1,
            sort_order=0,
            created_at=now,
            updated_at=now,
        )
        db.add(position)
        db.flush()
        request = SubPostRequest(
            id=uuid.uuid4(),
            sub_post_id=post_id,
            sub_post_position_id=position.id,
            requester_user_id=requester_user_id,
            request_status="pending",
            created_at=now,
            updated_at=now,
        )
        db.add(request)
        db.commit()
        return {
            "position_id": position.id,
            "request_id": request.id,
        }


def _persist_game_chat_message_fixture(
    *,
    game_id: uuid.UUID,
    sender_user_id: uuid.UUID,
) -> uuid.UUID:
    from backend.models import ChatMessage, GameChat

    now = datetime.now(timezone.utc)
    with _session() as db:
        chat = GameChat(
            id=uuid.uuid4(),
            game_id=game_id,
            chat_status="active",
            message_count=1,
            needs_review_count=1,
            removed_count=0,
            latest_message_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(chat)
        db.flush()
        message = ChatMessage(
            id=uuid.uuid4(),
            chat_id=chat.id,
            sender_user_id=sender_user_id,
            message_type="text",
            message_body="Admin moderation review fixture.",
            visibility_status="visible",
            review_status="needs_review",
            created_at=now,
            updated_at=now,
        )
        chat.latest_message_id = message.id
        chat.latest_message_preview = message.message_body
        db.add(message)
        db.commit()
        return message.id


def _persist_sub_post_chat_message_fixture(
    *,
    post_id: uuid.UUID,
    sender_user_id: uuid.UUID,
) -> uuid.UUID:
    from backend.models import SubPostChat, SubPostChatMessage

    now = datetime.now(timezone.utc)
    with _session() as db:
        chat = SubPostChat(
            id=uuid.uuid4(),
            sub_post_id=post_id,
            chat_status="active",
            message_count=1,
            needs_review_count=1,
            removed_count=0,
            latest_message_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(chat)
        db.flush()
        message = SubPostChatMessage(
            id=uuid.uuid4(),
            chat_id=chat.id,
            sender_user_id=sender_user_id,
            sender_display_name_snapshot="Local Sender",
            sender_initials_snapshot="LS",
            message_type="text",
            message_body="Need a Sub admin moderation fixture.",
            visibility_status="visible",
            review_status="needs_review",
            created_at=now,
            updated_at=now,
        )
        chat.latest_message_id = message.id
        chat.latest_message_preview = message.message_body
        db.add(message)
        db.commit()
        return message.id


def _official_game_create_payload(label: str) -> dict[str, object]:
    starts_at = datetime.now(timezone.utc) + timedelta(days=12)
    return {
        "title": f"WS03D API Official Game {label}",
        "venue": {
            "name": f"WS03D API Venue {label}",
            "address_line_1": "777 Admin Test Avenue",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "country_code": "US",
        },
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
        "timezone": "America/Chicago",
        "format_label": "5v5",
        "game_player_group": "coed",
        "skill_level": "any",
        "environment_type": "indoor",
        "total_spots": 10,
        "price_per_player_cents": 1200,
        "allow_guests": True,
        "max_guests_per_booking": 2,
        "waitlist_enabled": True,
        "is_chat_enabled": True,
        "reason": "Create local admin authorization proof game.",
    }


def _generic_game_create_payload(*, venue_id: uuid.UUID, host_user_id: uuid.UUID) -> dict[str, object]:
    starts_at = datetime.now(timezone.utc) + timedelta(days=13)
    return {
        "game_type": "community",
        "title": "WS03D Generic Admin Game",
        "description": "Local generic admin game fixture.",
        "venue_id": str(venue_id),
        "host_user_id": str(host_user_id),
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
        "timezone": "America/Chicago",
        "format_label": "5v5",
        "game_player_group": "coed",
        "skill_level": "any",
        "environment_type": "indoor",
        "total_spots": 10,
        "price_per_player_cents": 800,
        "allow_guests": True,
        "max_guests_per_booking": 2,
        "waitlist_enabled": True,
        "is_chat_enabled": True,
        "custom_rules_text": "Local test custom rules.",
    }


def _game_status(game_id: uuid.UUID) -> str:
    from backend.models import Game

    with _session() as db:
        game = db.get(Game, game_id)
        assert game is not None
        return str(game.game_status)


def _game_state(game_id: uuid.UUID) -> dict[str, object]:
    from backend.models import Game

    with _session() as db:
        game = db.get(Game, game_id)
        assert game is not None
        return {
            "game_status": game.game_status,
            "public_visibility_status": game.public_visibility_status,
            "join_enforcement_status": game.join_enforcement_status,
            "host_user_id": game.host_user_id,
            "cancelled_at": game.cancelled_at,
            "cancelled_by_user_id": game.cancelled_by_user_id,
            "cancellation_source": game.cancellation_source,
            "cancel_reason": game.cancel_reason,
        }


def _participant_state(participant_id: uuid.UUID) -> dict[str, object]:
    from backend.models import GameParticipant

    with _session() as db:
        participant = db.get(GameParticipant, participant_id)
        assert participant is not None
        return {
            "participant_status": participant.participant_status,
            "attendance_status": participant.attendance_status,
            "cancellation_type": participant.cancellation_type,
            "user_id": participant.user_id,
            "booking_id": participant.booking_id,
            "cancelled_at": participant.cancelled_at,
        }


def _booking_state(booking_id: uuid.UUID) -> dict[str, object]:
    from backend.models import Booking

    with _session() as db:
        booking = db.get(Booking, booking_id)
        assert booking is not None
        return {
            "booking_status": booking.booking_status,
            "payment_status": booking.payment_status,
            "participant_count": booking.participant_count,
            "cancelled_at": booking.cancelled_at,
            "cancelled_by_user_id": booking.cancelled_by_user_id,
            "cancel_reason": booking.cancel_reason,
        }


def _persist_official_paid_booking_with_credit_fixture(
    label: str,
    *,
    game_id: uuid.UUID,
    buyer_user_id: uuid.UUID,
    admin_user_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    from backend.models import (
        Booking,
        GameCredit,
        GameCreditUsage,
        GameParticipant,
        Payment,
    )

    now = datetime.now(timezone.utc)
    with _session() as db:
        booking = Booking(
            id=uuid.uuid4(),
            game_id=game_id,
            buyer_user_id=buyer_user_id,
            booking_status="confirmed",
            payment_status="paid",
            participant_count=1,
            subtotal_cents=1200,
            platform_fee_cents=0,
            discount_cents=0,
            total_cents=1200,
            price_per_player_snapshot_cents=1200,
            platform_fee_snapshot_cents=0,
            booked_at=now,
        )
        db.add(booking)
        db.flush()

        payment = Payment(
            id=uuid.uuid4(),
            payer_user_id=buyer_user_id,
            booking_id=booking.id,
            game_id=game_id,
            payment_type="booking",
            provider="stripe",
            provider_payment_intent_id=f"pi_ws03d_cancel_{uuid.uuid4().hex}",
            provider_charge_id=f"ch_ws03d_cancel_{uuid.uuid4().hex}",
            idempotency_key=f"ws03d-cancel-payment-{uuid.uuid4()}",
            amount_cents=800,
            currency="USD",
            payment_status="succeeded",
            paid_at=now,
        )
        db.add(payment)
        db.flush()

        participant = GameParticipant(
            id=uuid.uuid4(),
            game_id=game_id,
            booking_id=booking.id,
            participant_type="registered_user",
            user_id=buyer_user_id,
            display_name_snapshot=f"WS03D Cancellation Player {label}",
            participant_status="confirmed",
            attendance_status="unknown",
            cancellation_type="none",
            price_cents=1200,
            currency="USD",
            joined_at=now,
            confirmed_at=now,
        )
        db.add(participant)
        db.flush()

        credit = GameCredit(
            id=uuid.uuid4(),
            user_id=buyer_user_id,
            amount_cents=400,
            available_cents=0,
            currency="USD",
            credit_status="used",
            credit_reason="admin_credit",
            source_game_id=game_id,
            source_booking_id=booking.id,
            source_payment_id=payment.id,
            issued_by_user_id=admin_user_id,
            idempotency_key=f"ws03d-cancel-credit-{uuid.uuid4()}",
            note="Local official-game cancellation credit fixture.",
        )
        db.add(credit)
        db.flush()

        credit_usage = GameCreditUsage(
            id=uuid.uuid4(),
            game_credit_id=credit.id,
            booking_id=booking.id,
            game_id=game_id,
            payment_id=payment.id,
            amount_cents=400,
            currency="USD",
            usage_type="redeem",
            usage_status="redeemed",
            idempotency_key=f"ws03d-cancel-credit-usage-{uuid.uuid4()}",
            reason_code="local_test_redeem",
            redeemed_at=now,
        )
        db.add(credit_usage)
        db.commit()
        return {
            "booking_id": booking.id,
            "payment_id": payment.id,
            "participant_id": participant.id,
            "credit_id": credit.id,
            "credit_usage_id": credit_usage.id,
        }


def _payment_state(payment_id: uuid.UUID) -> dict[str, object]:
    from backend.models import Payment

    with _session() as db:
        payment = db.get(Payment, payment_id)
        assert payment is not None
        return {
            "payment_status": payment.payment_status,
            "provider_payment_intent_id": payment.provider_payment_intent_id,
            "provider_charge_id": payment.provider_charge_id,
            "failure_code": payment.failure_code,
            "failure_message": payment.failure_message,
        }


def _game_credit_state(game_credit_id: uuid.UUID) -> dict[str, object]:
    from backend.models import GameCredit

    with _session() as db:
        credit = db.get(GameCredit, game_credit_id)
        assert credit is not None
        return {
            "credit_status": credit.credit_status,
            "available_cents": credit.available_cents,
            "amount_cents": credit.amount_cents,
            "reversed_by_user_id": credit.reversed_by_user_id,
            "reversed_at": credit.reversed_at,
        }


def _credit_usage_status_counts(game_credit_id: uuid.UUID) -> dict[str, int]:
    from sqlalchemy import func, select

    from backend.models import GameCreditUsage

    with _session() as db:
        rows = db.execute(
            select(GameCreditUsage.usage_status, func.count())
            .where(GameCreditUsage.game_credit_id == game_credit_id)
            .group_by(GameCreditUsage.usage_status)
        ).all()
        return {str(status): int(count) for status, count in rows}


def _notification_types_for_user_game(
    *,
    user_id: uuid.UUID,
    game_id: uuid.UUID,
) -> set[str]:
    from sqlalchemy import select

    from backend.models import Notification

    with _session() as db:
        return set(
            db.scalars(
                select(Notification.notification_type).where(
                    Notification.user_id == user_id,
                    Notification.related_game_id == game_id,
                )
            ).all()
        )


def _refunds_for_booking(booking_id: uuid.UUID) -> list[dict[str, object]]:
    from sqlalchemy import select

    from backend.models import Refund

    with _session() as db:
        refunds = list(
            db.scalars(
                select(Refund)
                .where(Refund.booking_id == booking_id)
                .order_by(Refund.created_at.asc(), Refund.id.asc())
            ).all()
        )
        return [
            {
                "id": refund.id,
                "payment_id": refund.payment_id,
                "provider_refund_id": refund.provider_refund_id,
                "provider_charge_id": refund.provider_charge_id,
                "refund_status": refund.refund_status,
                "provider_status": refund.provider_status,
                "amount_cents": refund.amount_cents,
                "refund_reason": refund.refund_reason,
                "origin_workflow": refund.origin_workflow,
                "approved_by_user_id": refund.approved_by_user_id,
                "refunded_at": refund.refunded_at,
            }
            for refund in refunds
        ]


def _venue_image_state(venue_image_id: uuid.UUID) -> dict[str, object]:
    from backend.models import VenueImage

    with _session() as db:
        image = db.get(VenueImage, venue_image_id)
        assert image is not None
        return {
            "venue_id": image.venue_id,
            "storage_object_key": image.storage_object_key,
            "image_role": image.image_role,
            "image_status": image.image_status,
            "is_primary": image.is_primary,
            "sort_order": image.sort_order,
            "alt_text": image.alt_text,
            "caption": image.caption,
            "etag": image.etag,
            "upload_completed_at": image.upload_completed_at,
            "deleted_at": image.deleted_at,
        }


def _venue_deleted_at(venue_id: uuid.UUID):
    from backend.models import Venue

    with _session() as db:
        venue = db.get(Venue, venue_id)
        assert venue is not None
        return venue.deleted_at


def _sub_post_state(post_id: uuid.UUID) -> dict[str, object]:
    from backend.models import SubPost

    with _session() as db:
        post = db.get(SubPost, post_id)
        assert post is not None
        return {
            "post_status": post.post_status,
            "public_visibility_status": post.public_visibility_status,
            "removed_at": post.removed_at,
            "removed_by_user_id": post.removed_by_user_id,
            "remove_reason": post.remove_reason,
        }


def _chat_message_state(message_id: uuid.UUID) -> dict[str, object]:
    from backend.models import ChatMessage

    with _session() as db:
        message = db.get(ChatMessage, message_id)
        assert message is not None
        return {
            "visibility_status": message.visibility_status,
            "review_status": message.review_status,
            "reviewed_by_user_id": message.reviewed_by_user_id,
            "removed_by_user_id": message.removed_by_user_id,
            "removed_source": message.removed_source,
            "removed_reason": message.removed_reason,
        }


def _sub_chat_message_state(message_id: uuid.UUID) -> dict[str, object]:
    from backend.models import SubPostChatMessage

    with _session() as db:
        message = db.get(SubPostChatMessage, message_id)
        assert message is not None
        return {
            "visibility_status": message.visibility_status,
            "review_status": message.review_status,
            "reviewed_by_user_id": message.reviewed_by_user_id,
            "removed_by_user_id": message.removed_by_user_id,
            "removed_source": message.removed_source,
            "restored_by_user_id": message.restored_by_user_id,
        }


@pytest.mark.requirement("WS03-04D-R4", "WS03-04D-R6", "WS03-04D-R10")
def test_admin_official_game_reads_apply_filters_child_lookups_and_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("official-read-admin", role="admin")
    ordinary = _user("official-read-ordinary")
    creator = _user("official-read-creator")
    buyer = _user("official-read-buyer")
    waitlisted = _user("official-read-waitlisted")
    search_user = _user("official-read-search-player")
    _add_users(admin, ordinary, creator, buyer, waitlisted, search_user)
    first_game_id, _first_venue_id = _persist_game_fixture(
        "official-read-alpha",
        admin=admin,
        creator=creator,
    )
    second_game_id, _second_venue_id = _persist_game_fixture(
        "official-read-beta",
        admin=admin,
        creator=creator,
    )
    money_fixture = _persist_official_paid_booking_with_credit_fixture(
        "official-read",
        game_id=first_game_id,
        buyer_user_id=buyer.id,
        admin_user_id=admin.id,
    )
    waitlist_entry_id = _persist_waitlist_entry_fixture(
        game_id=first_game_id,
        user_id=waitlisted.id,
    )
    chat_message_id = _persist_game_chat_message_fixture(
        game_id=first_game_id,
        sender_user_id=buyer.id,
    )
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "ordinary-token": ordinary},
    )
    client = _client()

    ordinary_response = client.get(
        "/admin/official-games?search=official-read",
        headers=_auth_headers("ordinary-token"),
    )
    assert ordinary_response.status_code == 403

    list_response = client.get(
        f"/admin/official-games?search=official-read&starts_on="
        f"{datetime.now(timezone.utc).date()}&limit=10",
        headers=_auth_headers("admin-token"),
    )
    assert list_response.status_code == 200
    assert list_response.json()["games"] == []

    scoped_list = client.get(
        "/admin/official-games?search=official-read&limit=10",
        headers=_auth_headers("admin-token"),
    )
    assert scoped_list.status_code == 200
    scoped_ids = {item["id"] for item in scoped_list.json()["games"]}
    assert {str(first_game_id), str(second_game_id)}.issubset(scoped_ids)

    page_one = client.get(
        "/admin/official-games?search=official-read&limit=1",
        headers=_auth_headers("admin-token"),
    )
    assert page_one.status_code == 200
    page_one_body = page_one.json()
    assert page_one_body["has_more"] is True
    assert page_one_body["next_cursor"]
    page_one_ids = {item["id"] for item in page_one_body["games"]}
    assert len(page_one_ids) == 1

    page_two = client.get(
        f"/admin/official-games?search=official-read&limit=1&cursor="
        f"{page_one_body['next_cursor']}",
        headers=_auth_headers("admin-token"),
    )
    assert page_two.status_code == 200
    page_two_ids = {item["id"] for item in page_two.json()["games"]}
    assert page_two_ids
    assert page_one_ids.isdisjoint(page_two_ids)

    mismatched_cursor = client.get(
        f"/admin/official-games?search=other-read&cursor="
        f"{page_one_body['next_cursor']}",
        headers=_auth_headers("admin-token"),
    )
    assert mismatched_cursor.status_code == 400

    unsupported_view = client.get(
        "/admin/official-games?view=unsupported",
        headers=_auth_headers("admin-token"),
    )
    assert unsupported_view.status_code == 400

    missing_game_id = uuid.uuid4()
    detail_response = client.get(
        f"/admin/official-games/{first_game_id}",
        headers=_auth_headers("admin-token"),
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["game"]["id"] == str(first_game_id)
    assert (
        client.get(
            f"/admin/official-games/{missing_game_id}",
            headers=_auth_headers("admin-token"),
        ).status_code
        == 404
    )

    participant_response = client.get(
        f"/admin/official-games/{first_game_id}/participants",
        headers=_auth_headers("admin-token"),
    )
    assert participant_response.status_code == 200
    assert {row["id"] for row in participant_response.json()} == {
        str(money_fixture["participant_id"])
    }

    booking_response = client.get(
        f"/admin/official-games/{first_game_id}/bookings",
        headers=_auth_headers("admin-token"),
    )
    assert booking_response.status_code == 200
    assert {row["id"] for row in booking_response.json()} == {
        str(money_fixture["booking_id"])
    }

    waitlist_response = client.get(
        f"/admin/official-games/{first_game_id}/waitlist",
        headers=_auth_headers("admin-token"),
    )
    assert waitlist_response.status_code == 200
    assert {row["id"] for row in waitlist_response.json()} == {
        str(waitlist_entry_id)
    }

    money_response = client.get(
        f"/admin/official-games/{first_game_id}/money",
        headers=_auth_headers("admin-token"),
    )
    assert money_response.status_code == 200
    money_body = money_response.json()
    assert {row["id"] for row in money_body["payments"]} == {
        str(money_fixture["payment_id"])
    }
    assert {row["id"] for row in money_body["credits"]} == {
        str(money_fixture["credit_id"])
    }
    assert {row["id"] for row in money_body["credit_usages"]} == {
        str(money_fixture["credit_usage_id"])
    }

    user_search = client.get(
        f"/admin/official-games/{first_game_id}/user-search?q="
        f"{search_user.email.split('@')[0]}",
        headers=_auth_headers("admin-token"),
    )
    assert user_search.status_code == 200
    assert str(search_user.id) in {
        row["user_id"] for row in user_search.json()["results"]
    }

    chat_summary = client.get(
        f"/admin/official-games/{first_game_id}/chat/summary",
        headers=_auth_headers("admin-token"),
    )
    assert chat_summary.status_code == 200
    assert chat_summary.json()["latest_message_id"] == str(chat_message_id)
    chat_messages = client.get(
        f"/admin/official-games/{first_game_id}/chat/messages?view=needs_review",
        headers=_auth_headers("admin-token"),
    )
    assert chat_messages.status_code == 200
    assert {row["id"] for row in chat_messages.json()["messages"]} == {
        str(chat_message_id)
    }
    unsupported_chat_view = client.get(
        f"/admin/official-games/{first_game_id}/chat/messages?view=unsupported",
        headers=_auth_headers("admin-token"),
    )
    assert unsupported_chat_view.status_code == 400
    assert (
        client.get(
            f"/admin/official-games/{missing_game_id}/chat/messages",
            headers=_auth_headers("admin-token"),
        ).status_code
        == 404
    )


@pytest.mark.requirement("WS03-04D-R4", "WS03-04D-R6", "WS03-04D-R10")
def test_admin_community_game_reads_apply_filters_cursors_detail_chat_and_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("community-read-admin", role="admin")
    ordinary = _user("community-read-ordinary")
    host = _user("community-read-host")
    second_host = _user("community-read-second-host")
    sender = _user("community-read-sender")
    _add_users(admin, ordinary, host, second_host, sender)
    first_game_id, _first_venue_id = _persist_community_game_fixture(
        "community-read-alpha",
        admin=admin,
        host=host,
    )
    second_game_id, _second_venue_id = _persist_community_game_fixture(
        "community-read-beta",
        admin=admin,
        host=second_host,
    )
    chat_message_id = _persist_game_chat_message_fixture(
        game_id=first_game_id,
        sender_user_id=sender.id,
    )
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "ordinary-token": ordinary},
    )
    client = _client()

    ordinary_response = client.get(
        "/admin/community-games?query=community-read",
        headers=_auth_headers("ordinary-token"),
    )
    assert ordinary_response.status_code == 403

    list_response = client.get(
        "/admin/community-games?query=community-read&view=active"
        "&publish_status=published&limit=10",
        headers=_auth_headers("admin-token"),
    )
    assert list_response.status_code == 200
    assert {str(first_game_id), str(second_game_id)}.issubset(
        {item["id"] for item in list_response.json()["games"]}
    )

    page_one = client.get(
        "/admin/community-games?query=community-read&publish_status=published"
        "&limit=1",
        headers=_auth_headers("admin-token"),
    )
    assert page_one.status_code == 200
    page_one_body = page_one.json()
    assert page_one_body["has_more"] is True
    assert page_one_body["next_cursor"]
    page_one_ids = {item["id"] for item in page_one_body["games"]}

    page_two = client.get(
        "/admin/community-games?query=community-read&publish_status=published"
        f"&limit=1&cursor={page_one_body['next_cursor']}",
        headers=_auth_headers("admin-token"),
    )
    assert page_two.status_code == 200
    page_two_ids = {item["id"] for item in page_two.json()["games"]}
    assert page_two_ids
    assert page_one_ids.isdisjoint(page_two_ids)

    mismatched_cursor = client.get(
        "/admin/community-games?query=community-read&publish_status=draft"
        f"&cursor={page_one_body['next_cursor']}",
        headers=_auth_headers("admin-token"),
    )
    assert mismatched_cursor.status_code == 400

    unsupported_view = client.get(
        "/admin/community-games?view=unsupported",
        headers=_auth_headers("admin-token"),
    )
    assert unsupported_view.status_code == 400
    unsupported_publish_status = client.get(
        "/admin/community-games?publish_status=unsupported",
        headers=_auth_headers("admin-token"),
    )
    assert unsupported_publish_status.status_code == 400

    missing_game_id = uuid.uuid4()
    detail_response = client.get(
        f"/admin/community-games/{first_game_id}?support_flag_limit=1&audit_limit=1",
        headers=_auth_headers("admin-token"),
    )
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["game"]["id"] == str(first_game_id)
    assert detail_body["host"]["id"] == str(host.id)
    assert (
        client.get(
            f"/admin/community-games/{missing_game_id}",
            headers=_auth_headers("admin-token"),
        ).status_code
        == 404
    )

    chat_summary = client.get(
        f"/admin/community-games/{first_game_id}/chat/summary",
        headers=_auth_headers("admin-token"),
    )
    assert chat_summary.status_code == 200
    assert chat_summary.json()["latest_message_id"] == str(chat_message_id)
    chat_messages = client.get(
        f"/admin/community-games/{first_game_id}/chat/messages?view=needs_review",
        headers=_auth_headers("admin-token"),
    )
    assert chat_messages.status_code == 200
    assert {row["id"] for row in chat_messages.json()["messages"]} == {
        str(chat_message_id)
    }
    unsupported_chat_view = client.get(
        f"/admin/community-games/{first_game_id}/chat/messages?view=unsupported",
        headers=_auth_headers("admin-token"),
    )
    assert unsupported_chat_view.status_code == 400
    assert (
        client.get(
            f"/admin/community-games/{missing_game_id}/chat/summary",
            headers=_auth_headers("admin-token"),
        ).status_code
        == 404
    )


@pytest.mark.requirement("WS03-04D-R4", "WS03-04D-R6", "WS03-04D-R10")
def test_admin_need_a_sub_reads_apply_filters_cursors_detail_request_chat_and_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("sub-read-admin", role="admin")
    ordinary = _user("sub-read-ordinary")
    owner_one = _user("sub-read-owner-one")
    owner_two = _user("sub-read-owner-two")
    requester = _user("sub-read-requester")
    sender = _user("sub-read-sender")
    _add_users(admin, ordinary, owner_one, owner_two, requester, sender)
    first_post_id = _persist_sub_post_fixture("sub-read-alpha", owner=owner_one)
    second_post_id = _persist_sub_post_fixture("sub-read-beta", owner=owner_two)
    request_fixture = _persist_sub_post_request_fixture(
        post_id=first_post_id,
        requester_user_id=requester.id,
    )
    chat_message_id = _persist_sub_post_chat_message_fixture(
        post_id=first_post_id,
        sender_user_id=sender.id,
    )
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "ordinary-token": ordinary},
    )
    client = _client()

    ordinary_response = client.get(
        "/admin/need-a-sub?query=sub-read",
        headers=_auth_headers("ordinary-token"),
    )
    assert ordinary_response.status_code == 403

    list_response = client.get(
        "/admin/need-a-sub?query=sub-read&view=active&limit=10",
        headers=_auth_headers("admin-token"),
    )
    assert list_response.status_code == 200
    assert {str(first_post_id), str(second_post_id)}.issubset(
        {item["id"] for item in list_response.json()["posts"]}
    )

    page_one = client.get(
        "/admin/need-a-sub?query=sub-read&limit=1",
        headers=_auth_headers("admin-token"),
    )
    assert page_one.status_code == 200
    page_one_body = page_one.json()
    assert page_one_body["has_more"] is True
    assert page_one_body["next_cursor"]
    page_one_ids = {item["id"] for item in page_one_body["posts"]}

    page_two = client.get(
        f"/admin/need-a-sub?query=sub-read&limit=1&cursor="
        f"{page_one_body['next_cursor']}",
        headers=_auth_headers("admin-token"),
    )
    assert page_two.status_code == 200
    page_two_ids = {item["id"] for item in page_two.json()["posts"]}
    assert page_two_ids
    assert page_one_ids.isdisjoint(page_two_ids)

    mismatched_cursor = client.get(
        f"/admin/need-a-sub?query=other-sub&cursor={page_one_body['next_cursor']}",
        headers=_auth_headers("admin-token"),
    )
    assert mismatched_cursor.status_code == 400

    unsupported_view = client.get(
        "/admin/need-a-sub?view=unsupported",
        headers=_auth_headers("admin-token"),
    )
    assert unsupported_view.status_code == 400

    missing_post_id = uuid.uuid4()
    detail_response = client.get(
        f"/admin/need-a-sub/{first_post_id}?request_limit=1&audit_limit=1",
        headers=_auth_headers("admin-token"),
    )
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["post"]["id"] == str(first_post_id)
    assert detail_body["owner"]["id"] == str(owner_one.id)
    assert detail_body["request_counts"]["total_count"] == 1
    assert {row["id"] for row in detail_body["requests"]} == {
        str(request_fixture["request_id"])
    }
    assert (
        client.get(
            f"/admin/need-a-sub/{missing_post_id}",
            headers=_auth_headers("admin-token"),
        ).status_code
        == 404
    )

    request_response = client.get(
        f"/admin/need-a-sub/requests/{request_fixture['request_id']}",
        headers=_auth_headers("admin-token"),
    )
    assert request_response.status_code == 200
    request_body = request_response.json()
    assert request_body["post"]["id"] == str(first_post_id)
    assert request_body["request"]["id"] == str(request_fixture["request_id"])
    assert request_body["request"]["requester"]["id"] == str(requester.id)
    assert (
        client.get(
            f"/admin/need-a-sub/requests/{uuid.uuid4()}",
            headers=_auth_headers("admin-token"),
        ).status_code
        == 404
    )

    chat_summary = client.get(
        f"/admin/need-a-sub/{first_post_id}/chat/summary",
        headers=_auth_headers("admin-token"),
    )
    assert chat_summary.status_code == 200
    assert chat_summary.json()["latest_message_id"] == str(chat_message_id)
    chat_messages = client.get(
        f"/admin/need-a-sub/{first_post_id}/chat/messages?view=needs_review",
        headers=_auth_headers("admin-token"),
    )
    assert chat_messages.status_code == 200
    assert {row["id"] for row in chat_messages.json()["messages"]} == {
        str(chat_message_id)
    }
    unsupported_chat_view = client.get(
        f"/admin/need-a-sub/{first_post_id}/chat/messages?view=unsupported",
        headers=_auth_headers("admin-token"),
    )
    assert unsupported_chat_view.status_code == 400
    assert (
        client.get(
            f"/admin/need-a-sub/{missing_post_id}/chat/messages",
            headers=_auth_headers("admin-token"),
        ).status_code
        == 404
    )


@pytest.mark.requirement("WS03-04D-R3", "WS03-04D-R6", "WS03-04D-R10")
def test_stale_admin_cannot_run_recent_game_or_venue_destructive_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction

    admin = _user("game-stale-admin", role="admin")
    creator = _user("game-stale-creator")
    _add_users(admin, creator)
    game_id, venue_id = _persist_game_fixture("stale", admin=admin, creator=creator)
    _install_tokens_for_users(
        monkeypatch,
        {"stale-admin-token": admin},
        stale_tokens={"stale-admin-token"},
    )
    client = _client()
    before_admin_actions = _count_model_rows(AdminAction)

    game_response = client.delete(
        f"/games/{game_id}",
        headers=_auth_headers("stale-admin-token"),
    )
    venue_response = client.delete(
        f"/venues/{venue_id}",
        headers=_auth_headers("stale-admin-token"),
    )

    assert game_response.status_code == 403
    assert venue_response.status_code == 403
    assert _game_status(game_id) == "active"
    assert _venue_deleted_at(venue_id) is None
    assert _count_model_rows(AdminAction) == before_admin_actions


@pytest.mark.requirement("WS03-04D-R6", "WS03-04D-R9", "WS03-04D-R10")
def test_admin_official_game_create_update_cancel_and_host_removal_persist_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, Game, Notification

    admin = _user("official-api-admin", role="admin")
    stale_admin = _user("official-api-stale-admin", role="admin")
    host = _user("official-api-host")
    _add_users(admin, stale_admin, host)
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "stale-admin-token": stale_admin},
        stale_tokens={"stale-admin-token"},
    )
    client = _client()
    before_games = _count_model_rows(Game)
    before_actions = _count_model_rows(AdminAction)

    create_response = client.post(
        "/admin/official-games",
        json=_official_game_create_payload("create"),
        headers=_auth_headers("admin-token"),
    )
    assert create_response.status_code == 201
    game = create_response.json()["game"]
    game_id = uuid.UUID(game["id"])
    assert game["game_type"] == "official"
    assert game["created_by_user_id"] == str(admin.id)
    assert _count_model_rows(Game) == before_games + 1

    extra_field_update = client.patch(
        f"/admin/official-games/{game_id}",
        json={
            "title": "Caller must not override server fields.",
            "created_by_user_id": str(host.id),
        },
        headers=_auth_headers("admin-token"),
    )
    assert extra_field_update.status_code == 422
    assert _game_state(game_id)["host_user_id"] is None

    update_response = client.patch(
        f"/admin/official-games/{game_id}",
        json={
            "title": "WS03D Updated Official Game",
            "reason": "Update local official game through admin API.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert update_response.status_code == 200
    assert update_response.json()["game"]["title"] == "WS03D Updated Official Game"

    add_host_player = client.post(
        f"/admin/official-games/{game_id}/players",
        json={
            "user_id": str(host.id),
            "reason": "Add host before host assignment removal proof.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert add_host_player.status_code == 201
    assign_host = client.post(
        f"/admin/official-games/{game_id}/host",
        json={
            "host_user_id": str(host.id),
            "reason": "Assign host before removal proof.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert assign_host.status_code == 200
    assert _game_state(game_id)["host_user_id"] == host.id

    remove_host = client.post(
        f"/admin/official-games/{game_id}/host/remove",
        json={"reason": "Remove official game host through current action route."},
        headers=_auth_headers("admin-token"),
    )
    assert remove_host.status_code == 200
    assert _game_state(game_id)["host_user_id"] is None

    preview = client.post(
        f"/admin/official-games/{game_id}/cancel-preview",
        headers=_auth_headers("admin-token"),
    )
    assert preview.status_code == 200
    preview_token = preview.json()["preview_token"]
    before_cancel_state = _game_state(game_id)
    before_cancel_actions = _count_model_rows(AdminAction)
    before_cancel_notifications = _count_model_rows(Notification)

    stale_cancel = client.post(
        f"/admin/official-games/{game_id}/cancel",
        json={
            "preview_token": preview_token,
            "reason": "Stale admin must not cancel official games.",
        },
        headers=_auth_headers("stale-admin-token"),
    )
    assert stale_cancel.status_code == 403
    assert _game_state(game_id) == before_cancel_state
    assert _count_model_rows(AdminAction) == before_cancel_actions
    assert _count_model_rows(Notification) == before_cancel_notifications

    cancel = client.post(
        f"/admin/official-games/{game_id}/cancel",
        json={
            "preview_token": preview_token,
            "reason": "Cancel local official game through admin API.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert cancel.status_code == 200
    cancelled = _game_state(game_id)
    assert cancelled["game_status"] == "cancelled"
    assert cancelled["cancelled_by_user_id"] == admin.id
    assert cancelled["cancellation_source"] == "admin"
    assert _count_model_rows(AdminAction) >= before_actions + 2


@pytest.mark.requirement("WS03-04D-R6", "WS03-04D-R10")
def test_admin_official_game_cancellation_exercises_booking_refund_credit_notification_and_follow_up_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, Notification, Refund, RefundEvent
    from backend.services import game_cancellation_service
    from backend.services.stripe_service import StripeRefundResult

    admin = _user("official-cancel-admin", role="admin")
    stale_admin = _user("official-cancel-stale-admin", role="admin")
    creator = _user("official-cancel-creator")
    player = _user("official-cancel-player")
    _add_users(admin, stale_admin, creator, player)
    game_id, _venue_id = _persist_game_fixture(
        "official-cancel-financial",
        admin=admin,
        creator=creator,
    )
    fixture = _persist_official_paid_booking_with_credit_fixture(
        "financial",
        game_id=game_id,
        buyer_user_id=player.id,
        admin_user_id=admin.id,
    )
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "stale-admin-token": stale_admin},
        stale_tokens={"stale-admin-token"},
    )
    provider_calls: list[dict[str, object]] = []

    def fake_create_refund(
        *,
        charge_id: str,
        amount_cents: int,
        currency: str,
        idempotency_key: str,
        metadata: dict[str, object],
    ) -> StripeRefundResult:
        provider_calls.append(
            {
                "charge_id": charge_id,
                "amount_cents": amount_cents,
                "currency": currency,
                "idempotency_key": idempotency_key,
                "metadata": metadata,
            }
        )
        return StripeRefundResult(
            id=f"re_ws03d_cancel_{uuid.uuid4().hex}",
            status="succeeded",
            amount_cents=amount_cents,
            currency=currency,
            charge_id=charge_id,
            payment_intent_id=None,
        )

    monkeypatch.setattr(
        game_cancellation_service,
        "create_stripe_refund",
        fake_create_refund,
    )
    client = _client()

    preview = client.post(
        f"/admin/official-games/{game_id}/cancel-preview",
        headers=_auth_headers("admin-token"),
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    assert preview_body["booking_count"] == 1
    assert preview_body["participant_count"] == 1
    assert preview_body["cash_refundable_cents"] == 800
    assert preview_body["credit_restorable_cents"] == 400
    assert preview_body["refund_follow_up_required"] is False
    assert preview_body["payment_follow_up_required"] is False
    assert preview_body["booking_impacts"] == [
        {
            **preview_body["booking_impacts"][0],
            "booking_id": str(fixture["booking_id"]),
            "buyer_user_id": str(player.id),
            "result_category": "stripe_refund_and_credit_restore",
            "cash_refundable_cents": 800,
            "credit_restorable_cents": 400,
            "follow_up_required": False,
        }
    ]

    before_game = _game_state(game_id)
    before_booking = _booking_state(fixture["booking_id"])
    before_participant = _participant_state(fixture["participant_id"])
    before_payment = _payment_state(fixture["payment_id"])
    before_credit = _game_credit_state(fixture["credit_id"])
    before_usage_counts = _credit_usage_status_counts(fixture["credit_id"])
    before_refunds = _count_model_rows(Refund)
    before_refund_events = _count_model_rows(RefundEvent)
    before_notifications = _count_model_rows(Notification)
    before_admin_actions = _count_model_rows(AdminAction)

    stale_cancel = client.post(
        f"/admin/official-games/{game_id}/cancel",
        json={
            "preview_token": preview_body["preview_token"],
            "reason": "Stale admin must not cancel paid official games.",
        },
        headers=_auth_headers("stale-admin-token"),
    )
    assert stale_cancel.status_code == 403
    assert provider_calls == []
    assert _game_state(game_id) == before_game
    assert _booking_state(fixture["booking_id"]) == before_booking
    assert _participant_state(fixture["participant_id"]) == before_participant
    assert _payment_state(fixture["payment_id"]) == before_payment
    assert _game_credit_state(fixture["credit_id"]) == before_credit
    assert _credit_usage_status_counts(fixture["credit_id"]) == before_usage_counts
    assert _count_model_rows(Refund) == before_refunds
    assert _count_model_rows(RefundEvent) == before_refund_events
    assert _count_model_rows(Notification) == before_notifications
    assert _count_model_rows(AdminAction) == before_admin_actions

    cancel = client.post(
        f"/admin/official-games/{game_id}/cancel",
        json={
            "preview_token": preview_body["preview_token"],
            "reason": "Cancel paid official game and return player value.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert cancel.status_code == 200
    cancel_body = cancel.json()
    assert cancel_body["cancelled_booking_count"] == 1
    assert cancel_body["cancelled_participant_count"] == 1
    assert cancel_body["notified_user_count"] == 1
    assert cancel_body["refund_created_count"] == 1
    assert cancel_body["refund_failed_count"] == 0
    assert cancel_body["refund_processing_count"] == 0
    assert cancel_body["refund_missing_charge_count"] == 0
    assert cancel_body["credit_restored_count"] == 1
    assert cancel_body["credit_restored_cents"] == 400
    assert cancel_body["refund_follow_up_required"] is False
    assert cancel_body["payment_follow_up_required"] is False
    assert cancel_body["money_issue_ids"] == []
    assert cancel_body["booking_results"][0]["booking_id"] == str(
        fixture["booking_id"]
    )
    assert cancel_body["booking_results"][0]["refunds"][0]["amount_cents"] == 800
    assert cancel_body["booking_results"][0]["cash_refunded_cents"] == 800
    assert cancel_body["booking_results"][0]["credit_restored_cents"] == 400
    assert cancel_body["booking_results"][0]["follow_up_required"] is False

    assert provider_calls == [
        {
            **provider_calls[0],
            "charge_id": before_payment["provider_charge_id"],
            "amount_cents": 800,
            "currency": "USD",
        }
    ]
    assert provider_calls[0]["metadata"] == {
        "source": "official_game_cancel",
        "game_id": str(game_id),
        "booking_id": str(fixture["booking_id"]),
        "payment_id": str(fixture["payment_id"]),
        "admin_user_id": str(admin.id),
    }

    cancelled_game = _game_state(game_id)
    assert cancelled_game["game_status"] == "cancelled"
    assert cancelled_game["public_visibility_status"] == before_game[
        "public_visibility_status"
    ]
    assert cancelled_game["join_enforcement_status"] == before_game[
        "join_enforcement_status"
    ]
    assert cancelled_game["cancelled_by_user_id"] == admin.id
    assert cancelled_game["cancellation_source"] == "admin"

    cancelled_booking = _booking_state(fixture["booking_id"])
    assert cancelled_booking["booking_status"] == "cancelled"
    assert cancelled_booking["payment_status"] == "refunded"
    assert cancelled_booking["cancelled_by_user_id"] == admin.id

    cancelled_participant = _participant_state(fixture["participant_id"])
    assert cancelled_participant["participant_status"] == "cancelled"
    assert cancelled_participant["attendance_status"] == "not_applicable"
    assert cancelled_participant["cancellation_type"] == "admin_cancelled"

    assert _payment_state(fixture["payment_id"]) == before_payment
    assert _game_credit_state(fixture["credit_id"]) == {
        **before_credit,
        "credit_status": "active",
        "available_cents": 400,
    }
    assert _credit_usage_status_counts(fixture["credit_id"]) == {
        **before_usage_counts,
        "restored": 1,
    }
    refunds = _refunds_for_booking(fixture["booking_id"])
    assert len(refunds) == 1
    assert refunds[0]["payment_id"] == fixture["payment_id"]
    assert refunds[0]["refund_status"] == "succeeded"
    assert refunds[0]["provider_status"] == "succeeded"
    assert refunds[0]["amount_cents"] == 800
    assert refunds[0]["refund_reason"] == "game_cancelled"
    assert refunds[0]["origin_workflow"] == "official_game_cancellation"
    assert refunds[0]["approved_by_user_id"] == admin.id
    assert refunds[0]["refunded_at"] is not None
    assert _count_model_rows(Refund) == before_refunds + 1
    assert _count_model_rows(RefundEvent) == before_refund_events + 1
    assert _notification_types_for_user_game(
        user_id=player.id,
        game_id=game_id,
    ) >= {"game_cancelled", "booking_refunded"}
    assert _count_model_rows(Notification) == before_notifications + 2
    assert _count_model_rows(AdminAction) == before_admin_actions + 1


@pytest.mark.requirement("WS03-04D-R6", "WS03-04D-R9", "WS03-04D-R10")
def test_admin_generic_game_create_update_delete_preserves_admin_and_state_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, Game

    admin = _user("generic-game-admin", role="admin")
    stale_admin = _user("generic-game-stale-admin", role="admin")
    host = _user("generic-game-host")
    _add_users(admin, stale_admin, host)
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "stale-admin-token": stale_admin},
        stale_tokens={"stale-admin-token"},
    )
    with _session() as db:
        venue = _venue("generic-game", creator_id=host.id, admin_id=admin.id)
        db.add(venue)
        db.commit()
        venue_id = venue.id

    client = _client()
    before_games = _count_model_rows(Game)
    before_actions = _count_model_rows(AdminAction)

    create_response = client.post(
        "/games",
        json=_generic_game_create_payload(venue_id=venue_id, host_user_id=host.id),
        headers=_auth_headers("admin-token"),
    )
    assert create_response.status_code == 201
    game_id = uuid.UUID(create_response.json()["id"])
    assert create_response.json()["created_by_user_id"] == str(admin.id)
    assert _count_model_rows(Game) == before_games + 1

    rejected_update = client.patch(
        f"/games/{game_id}",
        json={
            "title": "Rejected extra field update",
            "created_by_user_id": str(host.id),
        },
        headers=_auth_headers("admin-token"),
    )
    assert rejected_update.status_code == 422
    assert _game_state(game_id)["game_status"] == "active"

    update_response = client.patch(
        f"/games/{game_id}",
        json={"title": "WS03D Generic Game Updated"},
        headers=_auth_headers("admin-token"),
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "WS03D Generic Game Updated"

    before_delete_state = _game_state(game_id)
    stale_delete = client.delete(
        f"/games/{game_id}",
        headers=_auth_headers("stale-admin-token"),
    )
    assert stale_delete.status_code == 403
    assert _game_state(game_id) == before_delete_state
    assert _count_model_rows(AdminAction) == before_actions

    delete_response = client.delete(
        f"/games/{game_id}",
        headers=_auth_headers("admin-token"),
    )
    assert delete_response.status_code == 200
    with _session() as db:
        deleted_game = db.get(Game, game_id)
        assert deleted_game is not None
        assert deleted_game.deleted_at is not None


@pytest.mark.requirement("WS03-04D-R6", "WS03-04D-R10")
def test_admin_official_game_host_player_and_participant_actions_persist_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, Booking, GameParticipant, Notification

    admin = _user("official-roster-admin", role="admin")
    stale_admin = _user("official-roster-stale-admin", role="admin")
    ordinary = _user("official-roster-ordinary")
    creator = _user("official-roster-creator")
    host = _user("official-roster-host")
    player = _user("official-roster-player")
    removed_player = _user("official-roster-removed-player")
    _add_users(admin, stale_admin, ordinary, creator, host, player, removed_player)
    game_id, _venue_id = _persist_game_fixture(
        "official-roster-actions",
        admin=admin,
        creator=creator,
    )
    _install_tokens_for_users(
        monkeypatch,
        {
            "admin-token": admin,
            "stale-admin-token": stale_admin,
            "ordinary-token": ordinary,
        },
        stale_tokens={"stale-admin-token"},
    )
    client = _client()
    before_participants = _count_model_rows(GameParticipant)
    before_bookings = _count_model_rows(Booking)
    before_admin_actions = _count_model_rows(AdminAction)
    before_notifications = _count_model_rows(Notification)

    ordinary_add = client.post(
        f"/admin/official-games/{game_id}/players",
        json={
            "user_id": str(player.id),
            "reason": "Ordinary users must not add official-game players.",
        },
        headers=_auth_headers("ordinary-token"),
    )
    assert ordinary_add.status_code == 403
    assert _count_model_rows(GameParticipant) == before_participants
    assert _count_model_rows(Booking) == before_bookings
    assert _count_model_rows(AdminAction) == before_admin_actions
    assert _count_model_rows(Notification) == before_notifications

    host_add = client.post(
        f"/admin/official-games/{game_id}/players",
        json={
            "user_id": str(host.id),
            "reason": "Add host candidate before assigning host.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert host_add.status_code == 201
    host_participant = host_add.json()
    assert host_participant["user_id"] == str(host.id)
    assert host_participant["participant_status"] == "confirmed"

    assign_host = client.post(
        f"/admin/official-games/{game_id}/host",
        json={
            "host_user_id": str(host.id),
            "reason": "Assign rostered player as official-game host.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert assign_host.status_code == 200
    assert _game_state(game_id)["host_user_id"] == host.id

    removable_add = client.post(
        f"/admin/official-games/{game_id}/players",
        json={
            "user_id": str(removed_player.id),
            "reason": "Add player for admin removal proof.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert removable_add.status_code == 201
    removable_participant = removable_add.json()
    participant_id = uuid.UUID(removable_participant["id"])
    booking_id = uuid.UUID(removable_participant["booking_id"])
    before_remove_participant = _participant_state(participant_id)
    before_remove_booking = _booking_state(booking_id)
    before_remove_game = _game_state(game_id)
    before_remove_admin_actions = _count_model_rows(AdminAction)
    before_remove_notifications = _count_model_rows(Notification)

    preview = client.post(
        f"/admin/official-games/{game_id}/participants/{participant_id}/remove-preview",
        headers=_auth_headers("admin-token"),
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    assert "remove_only" in preview_body["allowed_outcomes"]

    stale_remove = client.post(
        f"/admin/official-games/{game_id}/participants/{participant_id}/remove",
        json={
            "preview_token": preview_body["preview_token"],
            "outcome": "remove_only",
            "reason": "Stale admin must not remove roster players.",
        },
        headers=_auth_headers("stale-admin-token"),
    )
    assert stale_remove.status_code == 403
    assert _participant_state(participant_id) == before_remove_participant
    assert _booking_state(booking_id) == before_remove_booking
    assert _game_state(game_id) == before_remove_game
    assert _count_model_rows(AdminAction) == before_remove_admin_actions
    assert _count_model_rows(Notification) == before_remove_notifications

    remove = client.post(
        f"/admin/official-games/{game_id}/participants/{participant_id}/remove",
        json={
            "preview_token": preview_body["preview_token"],
            "outcome": "remove_only",
            "reason": "Admin removes local test roster player.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert remove.status_code == 200
    participant_after = _participant_state(participant_id)
    assert participant_after["participant_status"] == "removed"
    assert participant_after["attendance_status"] == "not_applicable"
    assert participant_after["cancellation_type"] == "admin_cancelled"
    booking_after = _booking_state(booking_id)
    assert booking_after["booking_status"] == "cancelled"
    assert booking_after["payment_status"] == "not_required"
    assert booking_after["cancelled_by_user_id"] == admin.id
    assert _count_model_rows(AdminAction) == before_remove_admin_actions + 1
    assert _count_model_rows(Notification) == before_remove_notifications + 1


@pytest.mark.requirement("WS03-04D-R6", "WS03-04D-R10")
def test_admin_community_game_and_venue_image_actions_persist_state_and_denials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, AdminTargetNotice

    admin = _user("community-actions-admin", role="admin")
    stale_admin = _user("community-actions-stale-admin", role="admin")
    ordinary = _user("community-actions-ordinary")
    host = _user("community-actions-host")
    _add_users(admin, stale_admin, ordinary, host)
    game_id, venue_id = _persist_community_game_fixture(
        "community-actions",
        admin=admin,
        host=host,
    )
    image_id = _persist_venue_image_fixture(
        "community-actions",
        venue_id=venue_id,
        admin_id=admin.id,
    )
    _install_tokens_for_users(
        monkeypatch,
        {
            "admin-token": admin,
            "stale-admin-token": stale_admin,
            "ordinary-token": ordinary,
        },
        stale_tokens={"stale-admin-token"},
    )
    client = _client()
    before_game = _game_state(game_id)
    before_image = _venue_image_state(image_id)
    before_admin_actions = _count_model_rows(AdminAction)
    before_notices = _count_model_rows(AdminTargetNotice)

    ordinary_hide = client.post(
        f"/admin/community-games/{game_id}/hide",
        json={
            "reason": "Ordinary users must not hide community games.",
            "idempotency_key": f"ws03d-community-ordinary-hide-{uuid.uuid4()}",
        },
        headers=_auth_headers("ordinary-token"),
    )
    ordinary_image_update = client.patch(
        f"/admin/venue-images/{image_id}",
        json={
            "image_status": "hidden",
            "reason": "Ordinary users must not update venue images.",
        },
        headers=_auth_headers("ordinary-token"),
    )
    assert ordinary_hide.status_code == 403
    assert ordinary_image_update.status_code == 403
    assert _game_state(game_id) == before_game
    assert _venue_image_state(image_id) == before_image
    assert _count_model_rows(AdminAction) == before_admin_actions
    assert _count_model_rows(AdminTargetNotice) == before_notices

    hide = client.post(
        f"/admin/community-games/{game_id}/hide",
        json={
            "reason": "Hide community game during local moderation review.",
            "idempotency_key": f"ws03d-community-hide-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert hide.status_code == 200
    assert _game_state(game_id)["public_visibility_status"] == "hidden"

    pause = client.post(
        f"/admin/community-games/{game_id}/pause-joining",
        json={
            "reason": "Pause joins during local moderation review.",
            "idempotency_key": f"ws03d-community-pause-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert pause.status_code == 200
    assert _game_state(game_id)["join_enforcement_status"] == "paused"

    before_cancel = _game_state(game_id)
    before_cancel_admin_actions = _count_model_rows(AdminAction)
    before_cancel_notices = _count_model_rows(AdminTargetNotice)
    cancel_payload = {
        "reason": "Cancel community game during local admin review.",
        "idempotency_key": f"ws03d-community-cancel-{uuid.uuid4()}",
    }
    stale_cancel = client.post(
        f"/admin/community-games/{game_id}/cancel",
        json=cancel_payload,
        headers=_auth_headers("stale-admin-token"),
    )
    assert stale_cancel.status_code == 403
    assert _game_state(game_id) == before_cancel
    assert _count_model_rows(AdminAction) == before_cancel_admin_actions
    assert _count_model_rows(AdminTargetNotice) == before_cancel_notices

    cancel = client.post(
        f"/admin/community-games/{game_id}/cancel",
        json=cancel_payload,
        headers=_auth_headers("admin-token"),
    )
    assert cancel.status_code == 200
    cancelled_state = _game_state(game_id)
    assert cancelled_state["game_status"] == "cancelled"
    assert cancelled_state["cancelled_by_user_id"] == admin.id
    assert cancelled_state["cancellation_source"] == "admin"

    cancel_replay = client.post(
        f"/admin/community-games/{game_id}/cancel",
        json=cancel_payload,
        headers=_auth_headers("admin-token"),
    )
    assert cancel_replay.status_code == 200
    assert cancel_replay.json()["idempotent_replay"] is True
    assert _count_model_rows(AdminAction) == before_cancel_admin_actions + 1

    update_image = client.patch(
        f"/admin/venue-images/{image_id}",
        json={
            "image_status": "hidden",
            "alt_text": "Updated safe venue image alt text.",
            "caption": "Updated local test venue image caption.",
            "reason": "Hide venue image during local admin review.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert update_image.status_code == 200
    image_state = _venue_image_state(image_id)
    assert image_state["image_status"] == "hidden"
    assert image_state["alt_text"] == "Updated safe venue image alt text."
    assert image_state["storage_object_key"] == before_image["storage_object_key"]


@pytest.mark.requirement("WS03-04D-R6", "WS03-04D-R9", "WS03-04D-R10")
def test_admin_community_review_payment_restore_and_venue_image_upload_provider_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, AdminTargetNotice, SupportFlag, VenueImage
    from backend.services import venue_image_service
    from backend.services.r2_storage_service import (
        R2ObjectProperties,
        R2ObjectUploadTicket,
        R2StorageConfig,
    )

    admin = _user("community-more-admin", role="admin")
    ordinary = _user("community-more-ordinary")
    host = _user("community-more-host")
    _add_users(admin, ordinary, host)
    game_id, venue_id = _persist_community_game_fixture(
        "community-more",
        admin=admin,
        host=host,
    )
    _install_tokens_for_users(
        monkeypatch,
        {"admin-token": admin, "ordinary-token": ordinary},
    )
    provider_calls: list[str] = []

    def fake_storage_config() -> R2StorageConfig:
        provider_calls.append("config")
        return R2StorageConfig(
            account_id="local-test-account",
            access_key_id="local-test-key",
            secret_access_key="local-test-placeholder",
            endpoint_url="https://r2.local.invalid",
            bucket_name="local-test-bucket",
            upload_url_minutes=10,
            read_url_minutes=10,
            max_image_bytes=5_000_000,
            allowed_image_types=frozenset({"image/jpeg"}),
            metadata_connect_timeout_seconds=1,
            metadata_read_timeout_seconds=1,
        )

    def fake_upload_url(*, object_key: str, content_type: str) -> R2ObjectUploadTicket:
        provider_calls.append(f"upload:{content_type}")
        return R2ObjectUploadTicket(
            upload_url="https://upload.local.invalid",
            upload_headers={"Content-Type": content_type},
            object_url=f"https://read.local.invalid/{object_key}",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )

    def fake_read_url(object_key: str) -> str:
        provider_calls.append("read")
        return f"https://read.local.invalid/{object_key}"

    object_properties_by_key: dict[str, R2ObjectProperties] = {}

    def fake_object_properties(object_key: str) -> R2ObjectProperties:
        provider_calls.append("head")
        return object_properties_by_key[object_key]

    monkeypatch.setattr(venue_image_service, "get_r2_storage_config", fake_storage_config)
    monkeypatch.setattr(venue_image_service, "create_object_upload_url", fake_upload_url)
    monkeypatch.setattr(venue_image_service, "create_object_read_url", fake_read_url)
    monkeypatch.setattr(venue_image_service, "get_object_properties", fake_object_properties)

    client = _client()
    before_game = _game_state(game_id)
    before_actions = _count_model_rows(AdminAction)
    before_notices = _count_model_rows(AdminTargetNotice)
    before_support_flags = _count_model_rows(SupportFlag)
    before_images = _count_model_rows(VenueImage)

    hide_payment = client.post(
        f"/admin/community-games/{game_id}/hide-payment-text",
        json={
            "reason": "Hide unsafe local payment text.",
            "idempotency_key": f"ws03d-payment-text-hide-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert hide_payment.status_code == 200
    assert hide_payment.json()["moderation_state"]["unsafe_payment_text_hidden"] is True

    restore_payment = client.post(
        f"/admin/community-games/{game_id}/restore-payment-text",
        json={
            "reason": "Restore local payment text after review.",
            "idempotency_key": f"ws03d-payment-text-restore-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert restore_payment.status_code == 200
    assert (
        restore_payment.json()["moderation_state"]["unsafe_payment_text_hidden"]
        is False
    )

    hide = client.post(
        f"/admin/community-games/{game_id}/hide",
        json={
            "reason": "Hide before restore branch.",
            "idempotency_key": f"ws03d-community-hide-more-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert hide.status_code == 200
    restore = client.post(
        f"/admin/community-games/{game_id}/restore",
        json={
            "reason": "Restore hidden local community game.",
            "idempotency_key": f"ws03d-community-restore-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert restore.status_code == 200
    assert _game_state(game_id)["public_visibility_status"] == "visible"

    pause = client.post(
        f"/admin/community-games/{game_id}/pause-joining",
        json={
            "reason": "Pause before resume branch.",
            "idempotency_key": f"ws03d-community-pause-more-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert pause.status_code == 200
    resume = client.post(
        f"/admin/community-games/{game_id}/resume-joining",
        json={
            "reason": "Resume local community joining.",
            "idempotency_key": f"ws03d-community-resume-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert resume.status_code == 200
    assert _game_state(game_id)["join_enforcement_status"] == "open"

    review_flag = client.post(
        f"/admin/community-games/{game_id}/flag-for-review",
        json={
            "reason": "Flag local community game for review.",
            "idempotency_key": f"ws03d-community-review-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert review_flag.status_code == 200
    assert _count_model_rows(SupportFlag) == before_support_flags + 1

    ordinary_upload = client.post(
        f"/admin/venues/{venue_id}/images/upload-url",
        json={
            "file_name": "ordinary.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 1200,
        },
        headers=_auth_headers("ordinary-token"),
    )
    assert ordinary_upload.status_code == 403
    assert provider_calls == []
    assert _count_model_rows(VenueImage) == before_images

    upload = client.post(
        f"/admin/venues/{venue_id}/images/upload-url",
        json={
            "file_name": "admin.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 1200,
            "image_role": "gallery",
            "alt_text": "Local admin upload alt text.",
        },
        headers=_auth_headers("admin-token"),
    )
    assert upload.status_code == 201
    upload_body = upload.json()
    image_id = uuid.UUID(upload_body["image"]["id"])
    assert upload_body["image"]["uploaded_by_user_id"] == str(admin.id)
    assert provider_calls == ["config", "config", "upload:image/jpeg", "read"]
    assert _count_model_rows(VenueImage) == before_images + 1

    image_state = _venue_image_state(image_id)
    assert image_state["image_status"] == "pending_upload"
    object_properties_by_key[str(image_state["storage_object_key"])] = R2ObjectProperties(
        content_type="image/jpeg",
        size_bytes=1200,
        etag="local-test-etag",
    )
    complete = client.post(
        f"/admin/venue-images/{image_id}/complete",
        json={"etag": "local-complete-etag"},
        headers=_auth_headers("admin-token"),
    )
    assert complete.status_code == 200
    completed_state = _venue_image_state(image_id)
    assert completed_state["image_status"] == "active"
    assert completed_state["etag"] == "local-complete-etag"
    assert completed_state["upload_completed_at"] is not None
    assert provider_calls[-2:] == ["head", "read"]
    assert _game_state(game_id) == before_game
    assert _count_model_rows(AdminAction) >= before_actions + 7
    assert _count_model_rows(AdminTargetNotice) >= before_notices


@pytest.mark.requirement("WS03-04D-R3", "WS03-04D-R6", "WS03-04D-R10")
def test_stale_admin_cannot_remove_need_a_sub_post_or_create_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, AdminTargetNotice

    admin = _user("sub-remove-admin", role="admin")
    owner = _user("sub-remove-owner")
    _add_users(admin, owner)
    post_id = _persist_sub_post_fixture("stale-remove", owner=owner)
    _install_tokens_for_users(
        monkeypatch,
        {"stale-admin-token": admin},
        stale_tokens={"stale-admin-token"},
    )
    before_post = _sub_post_state(post_id)
    before_admin_actions = _count_model_rows(AdminAction)
    before_notices = _count_model_rows(AdminTargetNotice)

    response = _client().post(
        f"/admin/need-a-sub/{post_id}/remove",
        json={
            "reason": "Stale admin must not remove Need a Sub posts.",
            "idempotency_key": f"ws03d-stale-sub-real-{uuid.uuid4()}",
        },
        headers=_auth_headers("stale-admin-token"),
    )

    assert response.status_code == 403
    assert _sub_post_state(post_id) == before_post
    assert _count_model_rows(AdminAction) == before_admin_actions
    assert _count_model_rows(AdminTargetNotice) == before_notices


@pytest.mark.requirement("WS03-04D-R6", "WS03-04D-R8", "WS03-04D-R10")
def test_admin_need_a_sub_enforcement_and_chat_review_remove_restore_persist_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction, AdminTargetNotice

    admin = _user("sub-actions-admin", role="admin")
    owner = _user("sub-actions-owner")
    sender = _user("sub-actions-sender")
    _add_users(admin, owner, sender)
    post_id = _persist_sub_post_fixture("actions", owner=owner)
    message_id = _persist_sub_post_chat_message_fixture(
        post_id=post_id,
        sender_user_id=sender.id,
    )
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()
    before_actions = _count_model_rows(AdminAction)
    before_notices = _count_model_rows(AdminTargetNotice)

    hide = client.post(
        f"/admin/need-a-sub/{post_id}/hide",
        json={
            "reason": "Hide local Need a Sub post.",
            "idempotency_key": f"ws03d-sub-hide-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert hide.status_code == 200
    assert _sub_post_state(post_id)["public_visibility_status"] == "hidden"

    restore = client.post(
        f"/admin/need-a-sub/{post_id}/restore",
        json={
            "reason": "Restore local Need a Sub post.",
            "idempotency_key": f"ws03d-sub-restore-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert restore.status_code == 200
    assert _sub_post_state(post_id)["public_visibility_status"] == "visible"

    review = client.post(
        f"/admin/need-a-sub/{post_id}/chat/messages/{message_id}/review",
        json={
            "reason": "Review local Need a Sub chat message.",
            "idempotency_key": f"ws03d-sub-chat-review-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert review.status_code == 200
    assert _sub_chat_message_state(message_id)["review_status"] == "reviewed"

    remove_message = client.post(
        f"/admin/need-a-sub/{post_id}/chat/messages/{message_id}/remove",
        json={
            "reason": "Remove local Need a Sub chat message.",
            "idempotency_key": f"ws03d-sub-chat-remove-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert remove_message.status_code == 200
    assert _sub_chat_message_state(message_id)["visibility_status"] == "removed"

    restore_message = client.post(
        f"/admin/need-a-sub/{post_id}/chat/messages/{message_id}/restore",
        json={
            "reason": "Restore local Need a Sub chat message.",
            "idempotency_key": f"ws03d-sub-chat-restore-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert restore_message.status_code == 200
    assert _sub_chat_message_state(message_id)["visibility_status"] == "visible"

    before_remove_post = _sub_post_state(post_id)
    remove_post = client.post(
        f"/admin/need-a-sub/{post_id}/remove",
        json={
            "reason": "Remove local Need a Sub post.",
            "idempotency_key": f"ws03d-sub-remove-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert remove_post.status_code == 200
    removed_state = _sub_post_state(post_id)
    assert before_remove_post["post_status"] == "active"
    assert removed_state["post_status"] == "removed"
    assert removed_state["removed_by_user_id"] == admin.id
    assert _count_model_rows(AdminAction) >= before_actions + 6
    assert _count_model_rows(AdminTargetNotice) >= before_notices + 1


@pytest.mark.requirement("WS03-04D-R6", "WS03-04D-R8", "WS03-04D-R10")
def test_admin_chat_moderation_enforces_parent_binding_and_records_removal_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction

    admin = _user("chat-moderation-admin", role="admin")
    creator = _user("chat-moderation-creator")
    sender = _user("chat-moderation-sender")
    _add_users(admin, creator, sender)
    game_id, _venue_id = _persist_game_fixture(
        "chat-parent",
        admin=admin,
        creator=creator,
    )
    other_game_id, _other_venue_id = _persist_game_fixture(
        "chat-other-parent",
        admin=admin,
        creator=creator,
    )
    message_id = _persist_game_chat_message_fixture(
        game_id=game_id,
        sender_user_id=sender.id,
    )
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()
    before_message = _chat_message_state(message_id)
    before_admin_actions = _count_model_rows(AdminAction)

    wrong_parent = client.post(
        f"/admin/official-games/{other_game_id}/chat/messages/{message_id}/remove",
        json={
            "reason": "The message belongs to a different game.",
            "idempotency_key": f"ws03d-chat-wrong-parent-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )
    assert wrong_parent.status_code == 404
    assert _chat_message_state(message_id) == before_message
    assert _count_model_rows(AdminAction) == before_admin_actions

    response = client.post(
        f"/admin/official-games/{game_id}/chat/messages/{message_id}/remove",
        json={
            "reason": "Remove unsafe local test chat message.",
            "idempotency_key": f"ws03d-chat-remove-{uuid.uuid4()}",
        },
        headers=_auth_headers("admin-token"),
    )

    assert response.status_code == 200
    body = response.json()["message"]
    assert body["id"] == str(message_id)
    assert body["visibility_status"] == "removed"
    assert body["review_status"] == "reviewed"
    after_message = _chat_message_state(message_id)
    assert after_message["visibility_status"] == "removed"
    assert after_message["review_status"] == "reviewed"
    assert after_message["reviewed_by_user_id"] == admin.id
    assert after_message["removed_by_user_id"] == admin.id
    assert after_message["removed_source"] == "admin"
    assert _count_model_rows(AdminAction) == before_admin_actions + 1
