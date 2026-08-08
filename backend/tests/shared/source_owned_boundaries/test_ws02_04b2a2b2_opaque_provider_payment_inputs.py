from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select

from backend.database import SessionLocal
from backend.models import (
    AdminAction,
    GameCredit,
    GameCreditUsage,
    Payment,
    PaymentEvent,
    PlatformNoticeGlobalSeenState,
    Refund,
    User,
)
from backend.schemas.game_credit_schema import GameCreditIssueCreate, GameCreditReverseCreate
from backend.schemas.inbox_schema import InboxGlobalSeenUpdate
from backend.schemas.payment_event_schema import PaymentEventUpdate
from backend.schemas.user_payment_method_schema import UserPaymentMethodSyncCreate
from backend.services.auth_service import get_current_app_user
from backend.services.checkout_service import validate_checkout_return_url
from backend.services.inbox_service import encode_global_seen_token
from backend.services.stripe_service import (
    StripePaymentMethodCardResult,
    StripeSetupIntentResult,
)
from backend.tests.helpers import (
    create_booking,
    create_game,
    create_payment,
    create_payment_event,
    create_user,
    create_venue,
    set_user_role,
    unique_suffix,
)


def authenticate_client_as(client: TestClient, user_id: str) -> None:
    from backend.main import app

    def override_current_user() -> User:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return db_user

    app.dependency_overrides[get_current_app_user] = override_current_user
    client.app.dependency_overrides[get_current_app_user] = override_current_user


def assert_stable_error(response, *, status_code: int) -> dict:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert "code" in body
    assert "message" in body
    assert "correlation_id" in body
    return body


def assert_retired_response(response, *, expected_code: str) -> None:
    body = assert_stable_error(response, status_code=410)
    assert body["detail"]["code"] == expected_code


def model_count(model) -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(model)) or 0


def count_admin_actions(action_type: str) -> int:
    with SessionLocal() as db:
        return (
            db.scalar(
                select(func.count())
                .select_from(AdminAction)
                .where(AdminAction.action_type == action_type)
            )
            or 0
        )


def get_global_seen_state_sequence(user_id: str) -> int | None:
    with SessionLocal() as db:
        state = db.get(PlatformNoticeGlobalSeenState, UUID(user_id))
        return state.last_seen_global_sequence if state is not None else None


def set_user_stripe_customer_id(user_id: str, customer_id: str) -> None:
    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        db_user.stripe_customer_id = customer_id
        db.commit()


def get_payment_event_raw_payload(payment_event_id: str) -> dict:
    with SessionLocal() as db:
        payment_event = db.get(PaymentEvent, UUID(payment_event_id))
        assert payment_event is not None
        return dict(payment_event.raw_payload)


def get_credit_usage_amounts(game_credit_id: str) -> list[int]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(GameCreditUsage.amount_cents)
                .where(GameCreditUsage.game_credit_id == UUID(game_credit_id))
                .order_by(GameCreditUsage.created_at.asc(), GameCreditUsage.id.asc())
            )
        )


def reduce_credit_available(game_credit_id: str, amount_cents: int) -> None:
    with SessionLocal() as db:
        credit = db.get(GameCredit, UUID(game_credit_id))
        assert credit is not None
        credit.available_cents = amount_cents
        credit.updated_at = datetime.now(UTC)
        db.commit()


def create_admin_user(client: TestClient) -> dict:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    return admin


def create_source_payment_fixture(client: TestClient) -> tuple[dict, dict, dict, dict, dict]:
    admin = create_admin_user(client)
    player = create_user(client)
    venue = create_venue(client, admin["id"])
    authenticate_client_as(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(client, player["id"], booking["id"])
    return admin, player, game, booking, payment


def issue_credit_payload(player: dict, game: dict, booking: dict, payment: dict, **overrides):
    payload = {
        "user_id": player["id"],
        "amount_cents": payment["amount_cents"],
        "credit_reason": "admin_credit",
        "source_game_id": game["id"],
        "source_booking_id": booking["id"],
        "source_payment_id": payment["id"],
        "idempotency_key": f"credit-{unique_suffix()}",
        "note": "Source-linked support credit.",
    }
    payload.update(overrides)
    return payload


def test_payment_method_sync_schema_trims_and_bounds_setup_intent_id() -> None:
    assert (
        UserPaymentMethodSyncCreate.model_validate(
            {"setup_intent_id": "  opaque-provider-id  "}
        ).setup_intent_id
        == "opaque-provider-id"
    )
    UserPaymentMethodSyncCreate.model_validate({"setup_intent_id": "x" * 255})

    for invalid_value in ("   ", "x" * 256):
        with pytest.raises(ValidationError):
            UserPaymentMethodSyncCreate.model_validate(
                {"setup_intent_id": invalid_value}
            )


def test_payment_method_sync_rejects_invalid_id_before_provider_lookup(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = create_user(client)
    authenticate_client_as(client, user["id"])
    provider_calls: list[str] = []

    def fail_if_called(setup_intent_id):
        provider_calls.append(str(setup_intent_id))
        raise AssertionError("provider lookup should not run")

    monkeypatch.setattr(
        "backend.services.payment_method_service.retrieve_setup_intent",
        fail_if_called,
    )

    response = client.post(
        "/user-payment-methods/sync",
        json={"setup_intent_id": "   "},
    )

    assert_stable_error(response, status_code=422)
    assert provider_calls == []


def test_payment_method_sync_accepts_opaque_255_and_keeps_provider_legitimacy(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = create_user(client)
    customer_id = f"customer-{unique_suffix()}"
    setup_intent_id = "s" * 255
    provider_calls: list[str] = []
    set_user_stripe_customer_id(user["id"], customer_id)

    def fake_retrieve_setup_intent(requested_setup_intent_id):
        provider_calls.append(str(requested_setup_intent_id))
        return StripeSetupIntentResult(
            id=str(requested_setup_intent_id),
            client_secret=None,
            status="succeeded",
            customer_id=customer_id,
            payment_method_id=f"payment-method-{unique_suffix()}",
        )

    def fake_retrieve_payment_method(stripe_payment_method_id):
        return StripePaymentMethodCardResult(
            id=str(stripe_payment_method_id),
            customer_id=customer_id,
            card_fingerprint=f"fingerprint-{unique_suffix()}",
            card_brand="visa",
            card_last4="4242",
            exp_month=12,
            exp_year=2030,
        )

    monkeypatch.setattr(
        "backend.services.payment_method_service.retrieve_setup_intent",
        fake_retrieve_setup_intent,
    )
    monkeypatch.setattr(
        "backend.services.payment_method_service.retrieve_payment_method",
        fake_retrieve_payment_method,
    )
    monkeypatch.setattr(
        "backend.services.payment_method_service.set_customer_default_payment_method",
        lambda **kwargs: None,
    )

    authenticate_client_as(client, user["id"])
    response = client.post(
        "/user-payment-methods/sync",
        json={"setup_intent_id": f" {setup_intent_id} "},
    )

    assert response.status_code == 201, response.text
    assert provider_calls == [setup_intent_id]
    assert response.json()["user_id"] == user["id"]


def test_inbox_global_seen_schema_trims_and_bounds_seen_token() -> None:
    assert (
        InboxGlobalSeenUpdate.model_validate({"seen_token": "  token  "}).seen_token
        == "token"
    )
    InboxGlobalSeenUpdate.model_validate({"seen_token": "x" * 512})

    for invalid_value in ("   ", "x" * 513):
        with pytest.raises(ValidationError):
            InboxGlobalSeenUpdate.model_validate({"seen_token": invalid_value})


def test_inbox_global_seen_rejects_oversized_token_before_state_mutation(
    client: TestClient,
) -> None:
    user = create_user(client)
    authenticate_client_as(client, user["id"])

    response = client.put(
        "/inbox/app-updates/global-seen",
        json={"seen_token": "x" * 513},
    )

    assert_stable_error(response, status_code=422)
    assert get_global_seen_state_sequence(user["id"]) is None


def test_inbox_global_seen_accepts_issued_token_and_preserves_signature_checks(
    client: TestClient,
) -> None:
    user = create_user(client)
    authenticate_client_as(client, user["id"])
    token = encode_global_seen_token(
        highest_global_sequence=7,
        user_id=UUID(user["id"]),
    )

    accepted_response = client.put(
        "/inbox/app-updates/global-seen",
        json={"seen_token": token},
    )
    invalid_response = client.put(
        "/inbox/app-updates/global-seen",
        json={"seen_token": "x" * 64},
    )

    assert accepted_response.status_code == 200, accepted_response.text
    assert get_global_seen_state_sequence(user["id"]) == 7
    assert_stable_error(invalid_response, status_code=400)
    assert "x" * 64 not in invalid_response.text


@pytest.mark.parametrize(
    "return_url",
    (
        "https://frontend.example/games/{game_id}/checkout",
        "ftp://localhost:5173/games/{game_id}/checkout",
        "http://userinfo@localhost:5173/games/{game_id}/checkout",
        "http://localhost:5173/games/{game_id}/checkout#done",
        "http://localhost:5173/games/{game_id}/checkout?step=done",
        "http://localhost:5173/games/{other_game_id}/checkout",
        "http://localhost:5173/games/{game_id}/checkout/extra",
    ),
)
def test_checkout_return_url_rejects_external_or_unexpected_values(
    return_url: str,
) -> None:
    game_id = uuid4()
    other_game_id = uuid4()
    formatted_url = return_url.format(game_id=game_id, other_game_id=other_game_id)

    with pytest.raises(HTTPException):
        validate_checkout_return_url(formatted_url, game_id=game_id)


def test_checkout_return_url_accepts_current_frontend_checkout_path() -> None:
    game_id = uuid4()
    return_url = f"http://localhost:5173/games/{game_id}/checkout"

    assert validate_checkout_return_url(return_url, game_id=game_id) == return_url


def test_checkout_return_url_rejects_before_game_lookup_or_provider_work(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = create_user(client)
    game_id = uuid4()
    authenticate_client_as(client, user["id"])

    def fail_if_game_lookup_runs(*args, **kwargs):
        raise AssertionError("game lookup should not run")

    def fail_if_provider_runs(*args, **kwargs):
        raise AssertionError("provider work should not run")

    monkeypatch.setattr(
        "backend.services.checkout_service.get_locked_active_game_or_404",
        fail_if_game_lookup_runs,
    )
    monkeypatch.setattr(
        "backend.services.checkout_service.create_payment_intent",
        fail_if_provider_runs,
    )

    response = client.post(
        f"/checkout/games/{game_id}/payment-intent",
        json={
            "guest_count": 0,
            "payment_method_id": str(uuid4()),
            "return_url": f"https://frontend.example/games/{game_id}/checkout",
        },
    )

    assert_stable_error(response, status_code=400)


@pytest.mark.parametrize(
    ("method", "path", "expected_code", "model"),
    (
        ("POST", "/payments", "payment_generic_mutation_removed", Payment),
        ("PATCH", f"/payments/{uuid4()}", "payment_generic_mutation_removed", Payment),
        ("POST", "/refunds", "refund_generic_mutation_removed", Refund),
        ("PATCH", f"/refunds/{uuid4()}", "refund_generic_mutation_removed", Refund),
        (
            "POST",
            "/payment-events",
            "payment_event_generic_creation_removed",
            PaymentEvent,
        ),
    ),
)
def test_b2_generic_payment_refund_event_mutations_are_bodyless_tombstones(
    client: TestClient,
    method: str,
    path: str,
    expected_code: str,
    model,
) -> None:
    admin = create_admin_user(client)
    authenticate_client_as(client, admin["id"])
    before_count = model_count(model)

    response = client.request(
        method,
        path,
        content="{",
        headers={"Content-Type": "application/json"},
    )

    assert_retired_response(response, expected_code=expected_code)
    assert model_count(model) == before_count


def test_payment_event_repair_schema_excludes_provider_owned_fields() -> None:
    PaymentEventUpdate.model_validate(
        {
            "payment_id": uuid4(),
            "processing_status": "failed",
            "processing_error": "x" * 1000,
        }
    )

    for invalid_payload in (
        {"provider": "stripe"},
        {"provider_event_id": "event-id"},
        {"event_type": "payment_intent.succeeded"},
        {"raw_payload": {"provider": "payload"}},
        {"processed_at": datetime.now(UTC)},
        {"processing_error": "x" * 1001},
    ):
        with pytest.raises(ValidationError):
            PaymentEventUpdate.model_validate(invalid_payload)


def test_payment_event_repair_route_rejects_provider_payload_mutation(
    client: TestClient,
) -> None:
    admin = create_admin_user(client)
    payment_event = create_payment_event(client)
    original_payload = get_payment_event_raw_payload(payment_event["id"])
    authenticate_client_as(client, admin["id"])

    rejected_response = client.patch(
        f"/payment-events/{payment_event['id']}",
        json={"raw_payload": {"replacement": True}},
    )
    accepted_response = client.patch(
        f"/payment-events/{payment_event['id']}",
        json={
            "processing_status": "failed",
            "processing_error": "Safe processing repair note.",
        },
    )

    assert_stable_error(rejected_response, status_code=422)
    assert get_payment_event_raw_payload(payment_event["id"]) == original_payload
    assert accepted_response.status_code == 200, accepted_response.text
    accepted_body = accepted_response.json()
    assert accepted_body["processing_status"] == "failed"
    assert accepted_body["processing_error"] == "Safe processing repair note."


def test_game_credit_issue_schema_preserves_operational_field_bounds() -> None:
    payload = {
        "user_id": uuid4(),
        "amount_cents": 1,
        "idempotency_key": "x" * 160,
        "note": "n" * 1000,
    }
    GameCreditIssueCreate.model_validate(payload)
    GameCreditReverseCreate.model_validate(
        {"idempotency_key": "x" * 160, "note": "n" * 1000}
    )

    for schema_class, invalid_payload in (
        (GameCreditIssueCreate, {**payload, "idempotency_key": "x" * 161}),
        (GameCreditIssueCreate, {**payload, "note": "n" * 1001}),
        (GameCreditReverseCreate, {"idempotency_key": "x" * 161}),
        (GameCreditReverseCreate, {"note": "n" * 1001}),
    ):
        with pytest.raises(ValidationError):
            schema_class.model_validate(invalid_payload)


def test_source_linked_game_credit_at_eligible_amount_is_accepted(
    client: TestClient,
) -> None:
    admin, player, game, booking, payment = create_source_payment_fixture(client)
    authenticate_client_as(client, admin["id"])

    response = client.post(
        "/admin/game-credits/issue",
        json=issue_credit_payload(player, game, booking, payment),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["amount_cents"] == payment["amount_cents"]
    assert body["available_cents"] == payment["amount_cents"]
    assert body["source_booking_id"] == booking["id"]
    assert body["source_payment_id"] == payment["id"]
    assert count_admin_actions("issue_credit") == 1


def test_source_linked_game_credit_above_eligible_amount_rejected_before_mutation(
    client: TestClient,
) -> None:
    admin, player, game, booking, payment = create_source_payment_fixture(client)
    authenticate_client_as(client, admin["id"])

    response = client.post(
        "/admin/game-credits/issue",
        json=issue_credit_payload(
            player,
            game,
            booking,
            payment,
            amount_cents=payment["amount_cents"] + 1,
        ),
    )

    assert_stable_error(response, status_code=400)
    assert model_count(GameCredit) == 0
    assert count_admin_actions("issue_credit") == 0


def test_repeated_source_linked_game_credit_cannot_exceed_remaining_source_value(
    client: TestClient,
) -> None:
    admin, player, game, booking, payment = create_source_payment_fixture(client)
    authenticate_client_as(client, admin["id"])
    first_response = client.post(
        "/admin/game-credits/issue",
        json=issue_credit_payload(
            player,
            game,
            booking,
            payment,
            amount_cents=500,
        ),
    )
    assert first_response.status_code == 201, first_response.text

    rejected_response = client.post(
        "/admin/game-credits/issue",
        json=issue_credit_payload(
            player,
            game,
            booking,
            payment,
            amount_cents=payment["amount_cents"] - 499,
        ),
    )

    assert_stable_error(rejected_response, status_code=400)
    assert model_count(GameCredit) == 1
    assert count_admin_actions("issue_credit") == 1


@pytest.mark.parametrize(
    "payload_overrides",
    (
        {"source_game_id": None, "source_booking_id": None, "source_payment_id": None},
        {"source_booking_id": None, "source_payment_id": None},
    ),
)
def test_game_credit_issue_requires_source_with_server_derived_value(
    client: TestClient,
    payload_overrides: dict,
) -> None:
    admin, player, game, booking, payment = create_source_payment_fixture(client)
    authenticate_client_as(client, admin["id"])

    response = client.post(
        "/admin/game-credits/issue",
        json=issue_credit_payload(
            player,
            game,
            booking,
            payment,
            **payload_overrides,
        ),
    )

    assert_stable_error(response, status_code=400)
    assert model_count(GameCredit) == 0
    assert count_admin_actions("issue_credit") == 0


@pytest.mark.parametrize("amount_cents", (0, -1))
def test_game_credit_issue_rejects_non_positive_amount_before_mutation(
    client: TestClient,
    amount_cents: int,
) -> None:
    admin, player, game, booking, payment = create_source_payment_fixture(client)
    authenticate_client_as(client, admin["id"])

    response = client.post(
        "/admin/game-credits/issue",
        json=issue_credit_payload(
            player,
            game,
            booking,
            payment,
            amount_cents=amount_cents,
        ),
    )

    assert_stable_error(response, status_code=422)
    assert model_count(GameCredit) == 0
    assert count_admin_actions("issue_credit") == 0


def test_game_credit_reversal_uses_existing_unused_eligible_amount(
    client: TestClient,
) -> None:
    admin, player, game, booking, payment = create_source_payment_fixture(client)
    authenticate_client_as(client, admin["id"])
    issue_response = client.post(
        "/admin/game-credits/issue",
        json=issue_credit_payload(player, game, booking, payment),
    )
    assert issue_response.status_code == 201, issue_response.text
    credit = issue_response.json()
    reduce_credit_available(credit["id"], 400)

    reverse_response = client.post(
        f"/admin/game-credits/{credit['id']}/reverse",
        json={
            "idempotency_key": f"reverse-{unique_suffix()}",
            "note": "Reverse unused credit.",
        },
    )

    assert reverse_response.status_code == 200, reverse_response.text
    reversed_credit = reverse_response.json()
    assert reversed_credit["credit_status"] == "reversed"
    assert reversed_credit["available_cents"] == 0
    assert get_credit_usage_amounts(credit["id"]) == [400]
    assert count_admin_actions("reverse_credit") == 1
