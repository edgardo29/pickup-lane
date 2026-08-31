from __future__ import annotations

import ast
import json
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache, partial
from inspect import isfunction, ismethod
from pathlib import Path
from typing import Any

import pytest
from fastapi.routing import APIRoute

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

REPO_ROOT = Path(__file__).resolve().parents[4]
MATRIX_PATH = (
    REPO_ROOT
    / "backend/tests/workflows/authorization_matrix_foundation/authorization_matrix.json"
)
REQUIREMENTS_PATH = REPO_ROOT / "backend/tests/support/requirements/ws03_04c.json"
AUTH_PREFIX = "backend.services.auth_service:"
EXCLUDED_METHODS = {"HEAD", "OPTIONS"}
WORKFLOW_SCOPE = "workflows/game_community_roster_chat_need_a_sub_relationship_authorization"
REQUIREMENT_IDS = {f"WS03-04C-R{number}" for number in range(1, 13)}
REQUIRED_REQUIREMENT_IDS = {f"WS03-04C-R{number}" for number in range(1, 12)}
DEFERRED_REQUIREMENT_ID = "WS03-04C-R12"
EXPECTED_C_ROUTE_KEYS = {
    ("GET", "/bookings"),
    ("GET", "/bookings/me"),
    ("GET", "/bookings/{booking_id}"),
    ("GET", "/chat-messages"),
    ("POST", "/chat-messages"),
    ("GET", "/chat-messages/{chat_message_id}"),
    ("GET", "/checkout/bookings/{booking_id}/status"),
    ("POST", "/checkout/games/{game_id}/payment-intent"),
    ("GET", "/community-game-details"),
    ("GET", "/community-game-details/games/{game_id}/host-edit"),
    ("PUT", "/community-game-details/games/{game_id}/host-edit"),
    ("GET", "/community-game-details/{community_game_detail_id}"),
    ("POST", "/community-games/publish"),
    ("GET", "/community-games/publish-attempts/{attempt_id}"),
    ("POST", "/game-chats/for-game/{game_id}"),
    ("POST", "/game-chats/{game_chat_id}/read"),
    ("GET", "/game-chats/{game_chat_id}/read-state"),
    ("GET", "/game-participants/me"),
    ("GET", "/game-participants/{participant_id}"),
    ("GET", "/games"),
    ("GET", "/games/browse"),
    ("GET", "/games/participant-counts"),
    ("GET", "/games/{game_id}"),
    ("POST", "/games/{game_id}/booking-guests/add"),
    ("POST", "/games/{game_id}/cancel"),
    ("POST", "/games/{game_id}/guests/add"),
    ("POST", "/games/{game_id}/guests/remove"),
    ("PATCH", "/games/{game_id}/host-edit"),
    ("POST", "/games/{game_id}/join"),
    ("POST", "/games/{game_id}/leave"),
    ("GET", "/games/{game_id}/participants"),
    ("GET", "/my-games"),
    ("GET", "/my-games/need-a-sub"),
    ("GET", "/need-a-sub/posts"),
    ("POST", "/need-a-sub/posts"),
    ("GET", "/need-a-sub/posts/cards"),
    ("GET", "/need-a-sub/posts/mine"),
    ("GET", "/need-a-sub/posts/{sub_post_id}"),
    ("PATCH", "/need-a-sub/posts/{sub_post_id}"),
    ("PATCH", "/need-a-sub/posts/{sub_post_id}/cancel"),
    ("GET", "/need-a-sub/posts/{sub_post_id}/chat"),
    ("POST", "/need-a-sub/posts/{sub_post_id}/chat"),
    ("GET", "/need-a-sub/posts/{sub_post_id}/chat/messages"),
    ("POST", "/need-a-sub/posts/{sub_post_id}/chat/messages"),
    ("POST", "/need-a-sub/posts/{sub_post_id}/chat/read"),
    ("GET", "/need-a-sub/posts/{sub_post_id}/chat/read-state"),
    ("GET", "/need-a-sub/posts/{sub_post_id}/positions"),
    ("GET", "/need-a-sub/posts/{sub_post_id}/status-history"),
    ("GET", "/need-a-sub/my-requests"),
    ("GET", "/need-a-sub/posts/{sub_post_id}/requests"),
    ("POST", "/need-a-sub/posts/{sub_post_id}/requests"),
    ("PATCH", "/need-a-sub/requests/{request_id}/accept"),
    ("PATCH", "/need-a-sub/requests/{request_id}/cancel"),
    ("PATCH", "/need-a-sub/requests/{request_id}/cancel-by-owner"),
    ("PATCH", "/need-a-sub/requests/{request_id}/decline"),
    ("PATCH", "/need-a-sub/requests/{request_id}/no-show"),
    ("GET", "/need-a-sub/requests/{request_id}/status-history"),
    ("GET", "/game-images"),
    ("GET", "/game-images/{game_image_id}"),
    ("GET", "/venue-images"),
    ("GET", "/venues"),
    ("GET", "/venues/{venue_id}"),
    ("GET", "/waitlist-entries/me"),
    ("GET", "/waitlist-entries/{waitlist_entry_id}"),
}
VERIFIED_MUTATION_KEYS = {
    ("POST", "/chat-messages"),
    ("POST", "/checkout/games/{game_id}/payment-intent"),
    ("PUT", "/community-game-details/games/{game_id}/host-edit"),
    ("POST", "/community-games/publish"),
    ("POST", "/game-chats/for-game/{game_id}"),
    ("POST", "/games/{game_id}/booking-guests/add"),
    ("POST", "/games/{game_id}/cancel"),
    ("POST", "/games/{game_id}/guests/add"),
    ("POST", "/games/{game_id}/guests/remove"),
    ("PATCH", "/games/{game_id}/host-edit"),
    ("POST", "/games/{game_id}/join"),
    ("POST", "/games/{game_id}/leave"),
    ("POST", "/need-a-sub/posts"),
    ("PATCH", "/need-a-sub/posts/{sub_post_id}"),
    ("PATCH", "/need-a-sub/posts/{sub_post_id}/cancel"),
    ("POST", "/need-a-sub/posts/{sub_post_id}/chat"),
    ("POST", "/need-a-sub/posts/{sub_post_id}/chat/messages"),
    ("POST", "/need-a-sub/posts/{sub_post_id}/requests"),
    ("PATCH", "/need-a-sub/requests/{request_id}/accept"),
    ("PATCH", "/need-a-sub/requests/{request_id}/cancel"),
    ("PATCH", "/need-a-sub/requests/{request_id}/cancel-by-owner"),
    ("PATCH", "/need-a-sub/requests/{request_id}/decline"),
    ("PATCH", "/need-a-sub/requests/{request_id}/no-show"),
}
PUBLIC_ROUTE_KEYS = {
    ("GET", "/games"),
    ("GET", "/games/browse"),
    ("GET", "/games/participant-counts"),
    ("GET", "/need-a-sub/posts"),
    ("GET", "/need-a-sub/posts/{sub_post_id}/positions"),
    ("GET", "/game-images"),
    ("GET", "/game-images/{game_image_id}"),
    ("GET", "/venue-images"),
    ("GET", "/venues"),
    ("GET", "/venues/{venue_id}"),
}
OPTIONAL_AUTH_ROUTE_KEYS = {
    ("GET", "/community-game-details"),
    ("GET", "/community-game-details/{community_game_detail_id}"),
    ("GET", "/games/{game_id}"),
    ("GET", "/games/{game_id}/participants"),
    ("GET", "/need-a-sub/posts/cards"),
    ("GET", "/need-a-sub/posts/{sub_post_id}"),
}
CURRENT_OR_ACTIVE_READ_KEYS = (
    EXPECTED_C_ROUTE_KEYS
    - PUBLIC_ROUTE_KEYS
    - OPTIONAL_AUTH_ROUTE_KEYS
    - VERIFIED_MUTATION_KEYS
)


@dataclass(frozen=True)
class _Identity:
    auth_user_id: str
    email: str
    email_verified: bool
    authenticated_at: datetime | None


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _recent_time() -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=30)


def _install_auth_identities(
    monkeypatch: pytest.MonkeyPatch,
    identities: dict[str, _Identity],
) -> None:
    from backend.services import auth_service

    def verify_token(id_token: str) -> dict[str, object]:
        if id_token not in identities:
            raise ValueError("synthetic invalid token")

        identity = identities[id_token]
        payload: dict[str, object] = {
            "uid": identity.auth_user_id,
            "email": identity.email,
            "email_verified": identity.email_verified,
        }
        if identity.authenticated_at is not None:
            payload["auth_time"] = int(identity.authenticated_at.timestamp())
        return payload

    monkeypatch.setattr(auth_service, "verify_firebase_token", verify_token)


def _user(
    label: str,
    *,
    account_status: str = "active",
    role: str = "player",
    email_verified: bool = True,
    hosting_status: str = "eligible",
) -> Any:
    from backend.models import User

    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"firebase-ws03-04c-{label}-{unique}",
        role=role,
        email=f"ws03-04c-{label}-{unique}@example.invalid",
        email_verified_at=datetime.now(timezone.utc) if email_verified else None,
        first_name=f"WS03C{label}",
        last_name="User",
        date_of_birth=date(1990, 1, 1),
        account_status=account_status,
        hosting_status=hosting_status,
    )


def _venue(user_id: uuid.UUID, label: str, *, is_active: bool = True) -> Any:
    from backend.models import Venue

    return Venue(
        id=uuid.uuid4(),
        name=f"WS03C Venue {label}",
        address_line_1=f"{label} Test Ave",
        city="Chicago",
        state="IL",
        postal_code="60601",
        country_code="US",
        venue_status="approved" if is_active else "inactive",
        created_by_user_id=user_id,
        approved_by_user_id=user_id,
        approved_at=datetime.now(timezone.utc) if is_active else None,
        is_active=is_active,
    )


def _game(
    *,
    host_user_id: uuid.UUID,
    venue_id: uuid.UUID,
    label: str,
    game_type: str = "community",
    publish_status: str = "published",
    game_status: str = "active",
    public_visibility_status: str = "visible",
    join_enforcement_status: str = "open",
    payment_collection_type: str = "none",
    total_spots: int = 10,
    starts_delta_days: int = 30,
) -> Any:
    from backend.models import Game

    starts_at = datetime.now(timezone.utc) + timedelta(days=starts_delta_days)
    ends_at = starts_at + timedelta(hours=1)
    return Game(
        id=uuid.uuid4(),
        game_type=game_type,
        payment_collection_type=payment_collection_type,
        publish_status=publish_status,
        game_status=game_status,
        public_visibility_status=public_visibility_status,
        join_enforcement_status=join_enforcement_status,
        title=f"WS03C Game {label}",
        description=f"WS03C game {label}",
        venue_id=venue_id,
        venue_name_snapshot=f"WS03C Venue {label}",
        address_snapshot=f"{label} Test Ave",
        city_snapshot="Chicago",
        state_snapshot="IL",
        host_user_id=host_user_id,
        created_by_user_id=host_user_id,
        starts_at=starts_at,
        ends_at=ends_at,
        starts_on_local=starts_at.date(),
        timezone="America/Chicago",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="outdoor",
        total_spots=total_spots,
        price_per_player_cents=0,
        currency="USD",
        minimum_age=None,
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=0 if game_type == "official" else 2,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="custom_hosted" if game_type == "community" else "official_standard",
        published_at=datetime.now(timezone.utc) if publish_status == "published" else None,
    )


def _booking(
    *,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
    label: str,
    booking_status: str = "confirmed",
    payment_status: str = "not_required",
    participant_count: int = 1,
) -> Any:
    from backend.models import Booking

    now = datetime.now(timezone.utc)
    reservation_status = {
        "pending_payment": "held",
        "confirmed": "confirmed",
        "waitlisted": "not_required",
        "partially_cancelled": "confirmed",
        "cancelled": "released",
        "expired": "released",
        "failed": "released",
        "capacity_conflict": "capacity_conflict",
    }[booking_status]
    return Booking(
        id=uuid.uuid4(),
        game_id=game_id,
        buyer_user_id=user_id,
        booking_status=booking_status,
        payment_status=payment_status,
        reservation_status=reservation_status,
        participant_count=participant_count,
        subtotal_cents=0,
        platform_fee_cents=0,
        discount_cents=0,
        total_cents=0,
        currency="USD",
        price_per_player_snapshot_cents=0,
        platform_fee_snapshot_cents=0,
        booked_at=now if booking_status == "confirmed" else None,
        cancelled_at=now if booking_status == "cancelled" else None,
        expires_at=(
            now + timedelta(minutes=30)
            if booking_status == "pending_payment"
            else None
        ),
        cancel_reason=f"ws03c-{label}" if booking_status == "cancelled" else None,
    )


def _participant(
    *,
    game_id: uuid.UUID,
    user_id: uuid.UUID | None,
    booking_id: uuid.UUID | None,
    label: str,
    participant_type: str = "registered_user",
    participant_status: str = "confirmed",
    guest_of_user_id: uuid.UUID | None = None,
    roster_order: int | None = 1,
) -> Any:
    from backend.models import GameParticipant

    now = datetime.now(timezone.utc)
    return GameParticipant(
        id=uuid.uuid4(),
        game_id=game_id,
        booking_id=booking_id,
        participant_type=participant_type,
        user_id=user_id,
        guest_of_user_id=guest_of_user_id,
        guest_name=f"Guest {label}" if participant_type == "guest" else None,
        display_name_snapshot=f"WS03C Participant {label}",
        participant_status=participant_status,
        attendance_status="unknown",
        cancellation_type="none",
        price_cents=0,
        currency="USD",
        roster_order=roster_order,
        joined_at=now,
        confirmed_at=now if participant_status == "confirmed" else None,
    )


def _waitlist_entry(
    *,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
    label: str,
    waitlist_status: str = "active",
    position: int = 1,
) -> Any:
    from backend.models import WaitlistEntry

    return WaitlistEntry(
        id=uuid.uuid4(),
        game_id=game_id,
        user_id=user_id,
        party_size=1,
        position=position,
        waitlist_status=waitlist_status,
        joined_at=datetime.now(timezone.utc),
        auto_charge_consent_version=f"ws03c-{label}",
    )


def _game_chat(game_id: uuid.UUID, *, chat_status: str = "active") -> Any:
    from backend.models import GameChat

    return GameChat(
        id=uuid.uuid4(),
        game_id=game_id,
        chat_status=chat_status,
        closed_at=datetime.now(timezone.utc) if chat_status == "closed" else None,
    )


def _chat_message(
    *,
    chat_id: uuid.UUID,
    sender_user_id: uuid.UUID,
    label: str,
    visibility_status: str = "visible",
    review_status: str = "clear",
) -> Any:
    from backend.models import ChatMessage

    return ChatMessage(
        id=uuid.uuid4(),
        chat_id=chat_id,
        sender_user_id=sender_user_id,
        message_type="text",
        message_body=f"WS03C message {label}",
        is_pinned=False,
        visibility_status=visibility_status,
        review_status=review_status,
        removed_at=datetime.now(timezone.utc) if visibility_status == "removed" else None,
        removed_source="system" if visibility_status == "removed" else None,
    )


def _community_detail(
    *,
    game_id: uuid.UUID,
    payment_text_moderation_status: str = "visible",
) -> Any:
    from backend.models import CommunityGameDetail

    return CommunityGameDetail(
        id=uuid.uuid4(),
        game_id=game_id,
        payment_methods_snapshot=[],
        payment_instructions_snapshot=None,
        payment_text_moderation_status=payment_text_moderation_status,
        payment_text_hidden_at=(
            datetime.now(timezone.utc)
            if payment_text_moderation_status == "hidden"
            else None
        ),
        payment_text_hidden_reason=(
            "synthetic moderation"
            if payment_text_moderation_status == "hidden"
            else None
        ),
    )


def _sub_post(
    *,
    owner_user_id: uuid.UUID,
    label: str,
    post_status: str = "active",
    public_visibility_status: str = "visible",
    starts_delta_days: int = 5,
) -> Any:
    from backend.models import SubPost

    starts_at = datetime.now(timezone.utc) + timedelta(days=starts_delta_days)
    ends_at = starts_at + timedelta(hours=2)
    return SubPost(
        id=uuid.uuid4(),
        owner_user_id=owner_user_id,
        post_status=post_status,
        public_visibility_status=public_visibility_status,
        sport_type="soccer",
        format_label="5v5",
        environment_type="outdoor",
        skill_level="any",
        game_player_group="coed",
        team_name=f"WS03C Team {label}",
        starts_at=starts_at,
        ends_at=ends_at,
        starts_on_local=starts_at.date(),
        timezone="America/Chicago",
        location_name=f"WS03C Field {label}",
        address_line_1=f"{label} Sub Ave",
        city="Chicago",
        state="IL",
        postal_code="60601",
        country_code="US",
        subs_needed=1,
        price_due_at_venue_cents=0,
        currency="USD",
        expires_at=starts_at - timedelta(hours=1),
        filled_at=datetime.now(timezone.utc) if post_status == "completed" else None,
        canceled_at=datetime.now(timezone.utc) if post_status == "cancelled" else None,
        removed_at=datetime.now(timezone.utc) if post_status == "removed" else None,
    )


def _sub_position(sub_post_id: uuid.UUID, label: str) -> Any:
    from backend.models import SubPostPosition

    return SubPostPosition(
        id=uuid.uuid4(),
        sub_post_id=sub_post_id,
        position_label="field_player",
        player_group="open",
        spots_needed=1,
        sort_order=1,
    )


def _sub_request(
    *,
    sub_post_id: uuid.UUID,
    position_id: uuid.UUID,
    requester_user_id: uuid.UUID,
    request_status: str = "pending",
) -> Any:
    from backend.models import SubPostRequest

    now = datetime.now(timezone.utc)
    return SubPostRequest(
        id=uuid.uuid4(),
        sub_post_id=sub_post_id,
        sub_post_position_id=position_id,
        requester_user_id=requester_user_id,
        request_status=request_status,
        confirmed_at=now if request_status == "confirmed" else None,
    )


def _sub_chat(sub_post_id: uuid.UUID, *, chat_status: str = "active") -> Any:
    from backend.models import SubPostChat

    return SubPostChat(
        id=uuid.uuid4(),
        sub_post_id=sub_post_id,
        chat_status=chat_status,
        closed_at=datetime.now(timezone.utc) if chat_status == "closed" else None,
    )


def _sub_chat_message(
    *,
    chat_id: uuid.UUID,
    sender_user_id: uuid.UUID,
    label: str,
    visibility_status: str = "visible",
    review_status: str = "clear",
) -> Any:
    from backend.models import SubPostChatMessage

    return SubPostChatMessage(
        id=uuid.uuid4(),
        chat_id=chat_id,
        sender_user_id=sender_user_id,
        sender_display_name_snapshot=f"WS03C Sender {label}",
        sender_initials_snapshot="WS",
        message_type="text",
        message_body=f"WS03C sub message {label}",
        visibility_status=visibility_status,
        review_status=review_status,
        removed_at=datetime.now(timezone.utc) if visibility_status == "removed" else None,
        removed_source="system" if visibility_status == "removed" else None,
    )


def _callable_identity(callable_obj: Any) -> str:
    if isinstance(callable_obj, partial):
        raise AssertionError(  # noqa: TRY004
            f"Unrepresentable partial dependency: {callable_obj!r}"
        )
    if not (isfunction(callable_obj) or ismethod(callable_obj)):
        raise AssertionError(f"Unrepresentable callable dependency: {callable_obj!r}")

    module = getattr(callable_obj, "__module__", None)
    qualname = getattr(callable_obj, "__qualname__", None)
    if not module or not qualname or "<locals>" in qualname or qualname == "<lambda>":
        raise AssertionError(f"Unstable dependency identity: {callable_obj!r}")

    identity = f"{module}:{qualname}"
    wrapped_seen: set[int] = set()
    wrapped_parts: list[str] = []
    wrapped = getattr(callable_obj, "__wrapped__", None)
    while wrapped is not None:
        if id(wrapped) in wrapped_seen:
            raise AssertionError(f"Wrapper cycle in dependency identity: {callable_obj!r}")
        wrapped_seen.add(id(wrapped))
        wrapped_module = getattr(wrapped, "__module__", None)
        wrapped_qualname = getattr(wrapped, "__qualname__", None)
        if not wrapped_module or not wrapped_qualname or "<locals>" in wrapped_qualname:
            raise AssertionError(f"Unstable wrapped dependency identity: {wrapped!r}")
        wrapped_parts.append(f"{wrapped_module}:{wrapped_qualname}")
        wrapped = getattr(wrapped, "__wrapped__", None)

    if wrapped_parts:
        return f"{identity}[wrapped={'|'.join(wrapped_parts)}]"
    return identity


def _walk_dependency_calls(dependant: Any) -> list[Any]:
    calls: list[Any] = []
    for dependency in dependant.dependencies:
        if dependency.call is not None:
            calls.append(dependency.call)
        calls.extend(_walk_dependency_calls(dependency))
    return calls


def _auth_dependencies(route: APIRoute) -> list[str]:
    identities: dict[str, int] = {}
    for call in _walk_dependency_calls(route.dependant):
        identity = _callable_identity(call)
        if identity.startswith(AUTH_PREFIX):
            previous_id = identities.setdefault(identity, id(call))
            assert previous_id == id(call), f"auth dependency identity collision: {identity}"
    return sorted(identities)


@lru_cache(maxsize=1)
def _matrix() -> dict[str, Any]:
    with MATRIX_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _requirement_declarations() -> dict[str, dict[str, Any]]:
    with REQUIREMENTS_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["schema_version"] == 1
    return {entry["id"]: entry for entry in payload["requirements"]}


@lru_cache(maxsize=1)
def _current_route_map() -> dict[tuple[str, str], APIRoute]:
    from backend.main import app

    routes: dict[tuple[str, str], APIRoute] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods - EXCLUDED_METHODS):
            key = (method, route.path_format)
            assert key not in routes, f"duplicate current route key: {key}"
            routes[key] = route
    return routes


def _flatten_matrix_routes() -> dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]]:
    routes: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]] = {}
    for family in _matrix()["route_families"]:
        for route in family["routes"]:
            key = (route["method"], route["path"])
            assert key not in routes, f"duplicate matrix route key: {key}"
            routes[key] = (family, route)
    return routes


def _collect_requirement_marker_ids() -> dict[str, set[str]]:
    marker_ids: dict[str, set[str]] = {}
    for path in sorted(Path(__file__).parent.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != "requirement":
                continue
            value = node.func.value
            if not (
                isinstance(value, ast.Attribute)
                and value.attr == "mark"
                and isinstance(value.value, ast.Name)
                and value.value.id == "pytest"
            ):
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    marker_ids.setdefault(arg.value, set()).add(path.name)
    return marker_ids


_QUOTED_SQL_VALUE_RE = re.compile(r"'([^']+)'")


def _constraint_allowed_values(
    model_cls: Any,
    *,
    constraint_name: str,
    column_name: str,
) -> set[str]:
    from sqlalchemy import CheckConstraint

    for constraint in model_cls.__table__.constraints:
        if not isinstance(constraint, CheckConstraint):
            continue
        if constraint.name != constraint_name:
            continue

        sql_text = str(constraint.sqltext)
        match = re.search(
            rf"\b{re.escape(column_name)}\s+IN\s*\((?P<values>[^)]*)\)",
            sql_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        assert match is not None, (
            f"{constraint_name} no longer exposes {column_name} IN values: {sql_text}"
        )
        values = set(_QUOTED_SQL_VALUE_RE.findall(match.group("values")))
        assert values, f"{constraint_name} did not expose any allowed values"
        return values

    raise AssertionError(f"{model_cls.__name__}.{constraint_name} was not found")


def _assert_service_source_matches_model_constraint(
    family: str,
    source_values: set[str],
    model_cls: Any,
    *,
    constraint_name: str,
    column_name: str,
) -> set[str]:
    constraint_values = _constraint_allowed_values(
        model_cls,
        constraint_name=constraint_name,
        column_name=column_name,
    )
    assert source_values == constraint_values, (
        f"{family} service constants and model constraint drifted: "
        f"service={sorted(source_values)} model={sorted(constraint_values)}"
    )
    return source_values


def _assert_complete_state_classification(
    family: str,
    authoritative_values: set[str],
    classification: dict[str, set[str]],
) -> None:
    assert authoritative_values, f"{family} has no authoritative values"

    classified: dict[str, str] = {}
    for bucket, values in classification.items():
        assert values, f"{family}.{bucket} is an empty behavior bucket"
        unknown = values - authoritative_values
        assert not unknown, (
            f"{family}.{bucket} classifies values not present in source: "
            f"{sorted(unknown)}"
        )
        overlap = set(classified) & values
        assert not overlap, (
            f"{family}.{bucket} overlaps another behavior bucket: {sorted(overlap)}"
        )
        for value in values:
            classified[value] = bucket

    missing = authoritative_values - set(classified)
    assert not missing, (
        f"{family} has unclassified authoritative values: {sorted(missing)}"
    )


@pytest.mark.requirement("WS03-04C-R1", "WS03-04C-R2", "WS03-04C-R11")
def test_matrix_scope_guard_and_route_dependencies_match_current_app() -> None:
    matrix_routes = _flatten_matrix_routes()
    c_routes = {
        key: route
        for key, (family, route) in matrix_routes.items()
        if family["primary_child_owner"] == "WS03-04C"
    }
    c_families = [
        family
        for family in _matrix()["route_families"]
        if family["primary_child_owner"] == "WS03-04C"
    ]

    assert len(c_families) == 15
    assert set(c_routes) == EXPECTED_C_ROUTE_KEYS
    assert len(c_routes) == 64
    assert set(c_routes) <= set(_current_route_map())
    assert not (
        set(EXPECTED_C_ROUTE_KEYS)
        & {
            key
            for key, (family, _route) in matrix_routes.items()
            if family["primary_child_owner"] in {"WS03-04B", "WS03-04D"}
        }
    )

    for key, route_entry in c_routes.items():
        family, _route = matrix_routes[key]
        assert family["primary_child_owner"] == "WS03-04C"
        assert route_entry["child_owner"] == "WS03-04C"
        assert route_entry["child_owner"] != "blocked"
        assert route_entry["route_disposition"] in {"public", "optional_auth", "protected"}
        assert _auth_dependencies(_current_route_map()[key]) == route_entry[
            "auth_dependencies"
        ]

    for key in PUBLIC_ROUTE_KEYS:
        assert c_routes[key]["route_disposition"] == "public"
        assert c_routes[key]["auth_dependencies"] == []

    for key in OPTIONAL_AUTH_ROUTE_KEYS:
        assert c_routes[key]["route_disposition"] == "optional_auth"
        assert c_routes[key]["auth_dependencies"] == [
            "backend.services.auth_service:get_optional_current_app_user"
        ]

    for key in CURRENT_OR_ACTIVE_READ_KEYS:
        dependencies = set(c_routes[key]["auth_dependencies"])
        assert "backend.services.auth_service:get_verified_firebase_identity" in dependencies
        assert "backend.services.auth_service:require_verified_user" not in dependencies

    for key in VERIFIED_MUTATION_KEYS:
        dependencies = set(c_routes[key]["auth_dependencies"])
        assert "backend.services.auth_service:require_verified_user" in dependencies
        assert "backend.services.auth_service:get_verified_firebase_identity" in dependencies


@pytest.mark.requirement("WS03-04C-R11")
def test_requirement_declaration_and_pytest_markers_match_c_contract() -> None:
    declarations = _requirement_declarations()
    assert set(declarations) == REQUIREMENT_IDS

    for requirement_id in REQUIRED_REQUIREMENT_IDS:
        declaration = declarations[requirement_id]
        assert declaration["owning_pass"] == "WS03-04C"
        assert declaration["state"] == "required"
        assert declaration["scope"] == WORKFLOW_SCOPE
        assert declaration["source_controls"]
        assert declaration["reason"].strip()

    deferred = declarations[DEFERRED_REQUIREMENT_ID]
    assert deferred["owning_pass"] == "WS03-04C"
    assert deferred["state"] == "deferred"
    assert deferred["scope"] == "governance"
    assert deferred["reason"].strip()

    marker_files = _collect_requirement_marker_ids()
    assert REQUIRED_REQUIREMENT_IDS <= set(marker_files)
    assert DEFERRED_REQUIREMENT_ID not in marker_files


@pytest.mark.requirement("WS03-04C-R2", "WS03-04C-R3", "WS03-04C-R10")
def test_frozen_finite_state_classification_covers_c_lifecycle_values() -> None:
    from backend.models import (
        Booking,
        ChatMessage,
        CommunityGameDetail,
        CommunityPublishAttempt,
        Game,
        GameChat,
        GameImage,
        GameParticipant,
        SubPost,
        SubPostChat,
        SubPostChatMessage,
        SubPostRequest,
        User,
        Venue,
        VenueImage,
        WaitlistEntry,
    )
    from backend.services import (
        booking_rules,
        game_participant_rules,
        game_rules,
        need_a_sub_rules,
    )

    assert {"is_active", "deleted_at"} <= set(Venue.__table__.columns.keys())

    state_families = {
        "user.account_status": (
            _constraint_allowed_values(
                User,
                constraint_name="ck_users_account_status",
                column_name="account_status",
            ),
            {
                "allowed": {"active"},
                "denied": {"suspended", "pending_deletion", "deleted"},
            },
        ),
        "provider.email_verified": (
            {f"email_verified={value}" for value in (True, False)},
            {
                "allowed": {"email_verified=True"},
                "relationship_only": {"email_verified=False"},
            },
        ),
        "game.game_type": (
            _assert_service_source_matches_model_constraint(
                "game.game_type",
                set(game_rules.VALID_GAME_TYPES),
                Game,
                constraint_name="ck_games_game_type",
                column_name="game_type",
            ),
            {"allowed": {"official", "community"}},
        ),
        "game.publish_status": (
            _assert_service_source_matches_model_constraint(
                "game.publish_status",
                set(game_rules.VALID_PUBLISH_STATUSES),
                Game,
                constraint_name="ck_games_publish_status",
                column_name="publish_status",
            ),
            {
                "public_only": {"published"},
                "concealed": {"draft", "archived"},
            },
        ),
        "game.game_status": (
            _assert_service_source_matches_model_constraint(
                "game.game_status",
                set(game_rules.VALID_GAME_STATUSES),
                Game,
                constraint_name="ck_games_game_status",
                column_name="game_status",
            ),
            {
                "allowed": {"active"},
                "relationship_only": {"completed"},
                "denied": {"cancelled", "expired"},
                "concealed": {"removed"},
            },
        ),
        "game.public_visibility_status": (
            _assert_service_source_matches_model_constraint(
                "game.public_visibility_status",
                set(game_rules.VALID_PUBLIC_VISIBILITY_STATUSES),
                Game,
                constraint_name="ck_games_public_visibility_status",
                column_name="public_visibility_status",
            ),
            {
                "public_only": {"visible"},
                "relationship_only": {"hidden"},
            },
        ),
        "game.join_enforcement_status": (
            _assert_service_source_matches_model_constraint(
                "game.join_enforcement_status",
                set(game_rules.VALID_JOIN_ENFORCEMENT_STATUSES),
                Game,
                constraint_name="ck_games_join_enforcement_status",
                column_name="join_enforcement_status",
            ),
            {
                "allowed": {"open"},
                "denied": {"paused"},
            },
        ),
        "booking.booking_status": (
            _assert_service_source_matches_model_constraint(
                "booking.booking_status",
                set(booking_rules.VALID_BOOKING_STATUSES),
                Booking,
                constraint_name="ck_bookings_booking_status",
                column_name="booking_status",
            ),
            {
                "relationship_only": {
                    "pending_payment",
                    "confirmed",
                    "waitlisted",
                    "partially_cancelled",
                },
                "denied": {"cancelled", "expired", "failed", "capacity_conflict"},
            },
        ),
        "booking.payment_status": (
            _assert_service_source_matches_model_constraint(
                "booking.payment_status",
                set(booking_rules.VALID_PAYMENT_STATUSES),
                Booking,
                constraint_name="ck_bookings_payment_status",
                column_name="payment_status",
            ),
            {
                "relationship_only": {
                    "not_required",
                    "unpaid",
                    "requires_action",
                    "processing",
                    "paid",
                    "failed",
                    "partially_refunded",
                    "refunded",
                    "credit_restored",
                    "disputed",
                },
            },
        ),
        "game_participant.participant_type": (
            _assert_service_source_matches_model_constraint(
                "game_participant.participant_type",
                set(game_participant_rules.VALID_PARTICIPANT_TYPES),
                GameParticipant,
                constraint_name="ck_game_participants_participant_type",
                column_name="participant_type",
            ),
            {
                "allowed": {"registered_user", "guest", "host"},
                "later_owner": {"admin_added"},
            },
        ),
        "game_participant.participant_status": (
            _assert_service_source_matches_model_constraint(
                "game_participant.participant_status",
                set(game_participant_rules.VALID_PARTICIPANT_STATUSES),
                GameParticipant,
                constraint_name="ck_game_participants_participant_status",
                column_name="participant_status",
            ),
            {
                "relationship_only": {"pending_payment", "confirmed", "waitlisted"},
                "denied": {"cancelled", "late_cancelled", "removed", "refunded"},
            },
        ),
        "game_participant.attendance_status": (
            _assert_service_source_matches_model_constraint(
                "game_participant.attendance_status",
                set(game_participant_rules.VALID_ATTENDANCE_STATUSES),
                GameParticipant,
                constraint_name="ck_game_participants_attendance_status",
                column_name="attendance_status",
            ),
            {
                "relationship_only": {
                    "unknown",
                    "attended",
                    "no_show",
                    "excused_absence",
                    "not_applicable",
                },
            },
        ),
        "game_participant.cancellation_type": (
            _assert_service_source_matches_model_constraint(
                "game_participant.cancellation_type",
                set(game_participant_rules.VALID_CANCELLATION_TYPES),
                GameParticipant,
                constraint_name="ck_game_participants_cancellation_type",
                column_name="cancellation_type",
            ),
            {
                "allowed": {"none"},
                "relationship_only": {"on_time", "late", "host_cancelled"},
                "later_owner": {"admin_cancelled", "payment_failed"},
            },
        ),
        "waitlist_entry.waitlist_status": (
            _constraint_allowed_values(
                WaitlistEntry,
                constraint_name="ck_waitlist_entries_waitlist_status",
                column_name="waitlist_status",
            ),
            {
                "relationship_only": {
                    "active",
                    "promoted",
                    "accepted",
                    "payment_processing",
                },
                "denied": {
                    "declined",
                    "expired",
                    "cancelled",
                    "removed",
                    "payment_failed",
                },
            },
        ),
        "game_chat.chat_status": (
            _constraint_allowed_values(
                GameChat,
                constraint_name="ck_game_chats_chat_status",
                column_name="chat_status",
            ),
            {
                "allowed": {"active"},
                "denied": {"closed"},
            },
        ),
        "sub_post_chat.chat_status": (
            _constraint_allowed_values(
                SubPostChat,
                constraint_name="ck_sub_post_chats_chat_status",
                column_name="chat_status",
            ),
            {
                "allowed": {"active"},
                "denied": {"closed"},
            },
        ),
        "chat_message.visibility_status": (
            _constraint_allowed_values(
                ChatMessage,
                constraint_name="ck_chat_messages_visibility_status",
                column_name="visibility_status",
            ),
            {
                "allowed": {"visible"},
                "concealed": {"removed"},
            },
        ),
        "chat_message.review_status": (
            _constraint_allowed_values(
                ChatMessage,
                constraint_name="ck_chat_messages_review_status",
                column_name="review_status",
            ),
            {
                "allowed": {"clear"},
                "later_owner": {"needs_review", "reviewed"},
            },
        ),
        "sub_post_chat_message.visibility_status": (
            _constraint_allowed_values(
                SubPostChatMessage,
                constraint_name="ck_sub_post_chat_messages_visibility_status",
                column_name="visibility_status",
            ),
            {
                "allowed": {"visible"},
                "concealed": {"removed"},
            },
        ),
        "sub_post_chat_message.review_status": (
            _constraint_allowed_values(
                SubPostChatMessage,
                constraint_name="ck_sub_post_chat_messages_review_status",
                column_name="review_status",
            ),
            {
                "allowed": {"clear"},
                "later_owner": {"needs_review", "reviewed"},
            },
        ),
        "community_game_detail.payment_text_moderation_status": (
            _constraint_allowed_values(
                CommunityGameDetail,
                constraint_name="ck_community_game_details_payment_text_moderation_status",
                column_name="payment_text_moderation_status",
            ),
            {
                "allowed": {"visible"},
                "concealed": {"hidden"},
            },
        ),
        "community_publish_attempt.attempt_status": (
            _constraint_allowed_values(
                CommunityPublishAttempt,
                constraint_name="ck_community_publish_attempts_status",
                column_name="attempt_status",
            ),
            {
                "relationship_only": {
                    "requires_payment_method",
                    "requires_action",
                    "processing",
                    "succeeded",
                    "failed",
                    "cancelled",
                    "expired",
                },
            },
        ),
        "venue.venue_status": (
            _constraint_allowed_values(
                Venue,
                constraint_name="ck_venues_venue_status",
                column_name="venue_status",
            ),
            {
                "public_only": {"approved"},
                "concealed": {"pending_review", "rejected", "inactive"},
            },
        ),
        "venue.active_deleted_state": (
            {
                f"is_active={is_active};deleted_at={deleted_at}"
                for is_active in (True, False)
                for deleted_at in ("null", "present")
            },
            {
                "public_only": {"is_active=True;deleted_at=null"},
                "concealed": {
                    "is_active=True;deleted_at=present",
                    "is_active=False;deleted_at=null",
                    "is_active=False;deleted_at=present",
                },
            },
        ),
        "venue_image.image_status": (
            _constraint_allowed_values(
                VenueImage,
                constraint_name="ck_venue_images_image_status",
                column_name="image_status",
            ),
            {
                "public_only": {"active"},
                "concealed": {"pending_upload", "hidden", "removed"},
            },
        ),
        "game_image.image_status": (
            _constraint_allowed_values(
                GameImage,
                constraint_name="ck_game_images_image_status",
                column_name="image_status",
            ),
            {
                "public_only": {"active"},
                "concealed": {"hidden", "removed"},
            },
        ),
        "sub_post.post_status": (
            _assert_service_source_matches_model_constraint(
                "sub_post.post_status",
                set(need_a_sub_rules.POST_STATUSES),
                SubPost,
                constraint_name="ck_sub_posts_post_status",
                column_name="post_status",
            ),
            {
                "public_only": {"active"},
                "relationship_only": {"completed", "expired"},
                "denied": {"cancelled"},
                "concealed": {"removed"},
            },
        ),
        "sub_post.public_visibility_status": (
            _assert_service_source_matches_model_constraint(
                "sub_post.public_visibility_status",
                set(need_a_sub_rules.PUBLIC_VISIBILITY_STATUSES),
                SubPost,
                constraint_name="ck_sub_posts_public_visibility_status",
                column_name="public_visibility_status",
            ),
            {
                "public_only": {"visible"},
                "relationship_only": {"hidden"},
            },
        ),
        "sub_post_request.request_status": (
            _assert_service_source_matches_model_constraint(
                "sub_post_request.request_status",
                set(need_a_sub_rules.REQUEST_STATUSES),
                SubPostRequest,
                constraint_name="ck_sub_post_requests_request_status",
                column_name="request_status",
            ),
            {
                "relationship_only": {"pending", "confirmed", "sub_waitlist"},
                "denied": {
                    "declined",
                    "canceled_by_player",
                    "canceled_by_owner",
                    "no_show_reported",
                    "expired",
                },
                "later_owner": {"closed_by_admin"},
            },
        ),
    }

    for family, (authoritative_values, classification) in state_families.items():
        _assert_complete_state_classification(
            family,
            authoritative_values,
            classification,
        )
