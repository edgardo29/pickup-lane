from dataclasses import dataclass
import os
from typing import Any


DEFAULT_STRIPE_CURRENCY = "USD"


class StripeConfigError(RuntimeError):
    """Raised when Stripe cannot be called safely from this environment."""


@dataclass(frozen=True)
class StripePaymentIntentResult:
    id: str
    client_secret: str | None
    status: str
    latest_charge_id: str | None = None


@dataclass(frozen=True)
class StripeCustomerResult:
    id: str


@dataclass(frozen=True)
class StripeSetupIntentResult:
    id: str
    client_secret: str | None
    status: str
    customer_id: str | None
    payment_method_id: str | None


@dataclass(frozen=True)
class StripePaymentMethodCardResult:
    id: str
    customer_id: str | None
    card_fingerprint: str
    card_brand: str
    card_last4: str
    exp_month: int
    exp_year: int


def get_stripe_currency() -> str:
    currency = os.getenv("STRIPE_CURRENCY", DEFAULT_STRIPE_CURRENCY).strip().upper()
    if currency != DEFAULT_STRIPE_CURRENCY:
        raise StripeConfigError("Pickup Lane Stripe payments currently support USD only.")

    return currency


def get_stripe_publishable_key() -> str:
    publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()
    if not publishable_key:
        raise StripeConfigError("STRIPE_PUBLISHABLE_KEY is not configured.")

    return publishable_key


def get_stripe_webhook_secret() -> str:
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        raise StripeConfigError("STRIPE_WEBHOOK_SECRET is not configured.")

    return webhook_secret


def get_stripe_secret_key() -> str:
    secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret_key:
        raise StripeConfigError("STRIPE_SECRET_KEY is not configured.")

    return secret_key


def get_stripe_module() -> Any:
    try:
        import stripe
    except ModuleNotFoundError as exc:
        raise StripeConfigError(
            "The Stripe Python SDK is not installed. Install backend requirements first."
        ) from exc

    stripe.api_key = get_stripe_secret_key()
    return stripe


def normalize_metadata(metadata: dict[str, object]) -> dict[str, str]:
    return {
        key: str(value)
        for key, value in metadata.items()
        if value is not None
    }


def extract_payment_intent_result(payment_intent: Any) -> StripePaymentIntentResult:
    latest_charge = getattr(payment_intent, "latest_charge", None)
    latest_charge_id = latest_charge if isinstance(latest_charge, str) else None

    return StripePaymentIntentResult(
        id=payment_intent.id,
        client_secret=getattr(payment_intent, "client_secret", None),
        status=payment_intent.status,
        latest_charge_id=latest_charge_id,
    )


def extract_setup_intent_result(setup_intent: Any) -> StripeSetupIntentResult:
    payment_method = getattr(setup_intent, "payment_method", None)
    customer = getattr(setup_intent, "customer", None)

    return StripeSetupIntentResult(
        id=setup_intent.id,
        client_secret=getattr(setup_intent, "client_secret", None),
        status=setup_intent.status,
        customer_id=customer if isinstance(customer, str) else None,
        payment_method_id=payment_method if isinstance(payment_method, str) else None,
    )


def extract_card_payment_method_result(
    payment_method: Any,
) -> StripePaymentMethodCardResult:
    if getattr(payment_method, "type", None) != "card":
        raise StripeConfigError("Only card payment methods are supported.")

    card = getattr(payment_method, "card", None)
    if card is None:
        raise StripeConfigError("Stripe payment method is missing card details.")

    card_fingerprint = str(getattr(card, "fingerprint", "") or "")
    if not card_fingerprint:
        raise StripeConfigError("Stripe payment method is missing card fingerprint.")

    customer = getattr(payment_method, "customer", None)
    return StripePaymentMethodCardResult(
        id=payment_method.id,
        customer_id=customer if isinstance(customer, str) else None,
        card_fingerprint=card_fingerprint,
        card_brand=str(getattr(card, "brand", "") or ""),
        card_last4=str(getattr(card, "last4", "") or ""),
        exp_month=int(getattr(card, "exp_month", 0) or 0),
        exp_year=int(getattr(card, "exp_year", 0) or 0),
    )


def create_customer(
    *,
    email: str | None,
    name: str | None,
    idempotency_key: str,
    metadata: dict[str, object],
) -> StripeCustomerResult:
    stripe = get_stripe_module()
    customer = stripe.Customer.create(
        email=email,
        name=name,
        metadata=normalize_metadata(metadata),
        idempotency_key=idempotency_key,
    )
    return StripeCustomerResult(id=customer.id)


def create_setup_intent(
    *,
    customer_id: str,
    idempotency_key: str,
    metadata: dict[str, object],
) -> StripeSetupIntentResult:
    stripe = get_stripe_module()
    setup_intent = stripe.SetupIntent.create(
        customer=customer_id,
        payment_method_types=["card"],
        usage="off_session",
        metadata=normalize_metadata(metadata),
        idempotency_key=idempotency_key,
    )
    return extract_setup_intent_result(setup_intent)


def retrieve_setup_intent(setup_intent_id: str) -> StripeSetupIntentResult:
    stripe = get_stripe_module()
    setup_intent = stripe.SetupIntent.retrieve(setup_intent_id)
    return extract_setup_intent_result(setup_intent)


def retrieve_payment_method(
    payment_method_id: str,
) -> StripePaymentMethodCardResult:
    stripe = get_stripe_module()
    payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
    return extract_card_payment_method_result(payment_method)


def detach_payment_method(payment_method_id: str) -> None:
    stripe = get_stripe_module()
    stripe.PaymentMethod.detach(payment_method_id)


def set_customer_default_payment_method(
    *, customer_id: str, payment_method_id: str
) -> None:
    stripe = get_stripe_module()
    stripe.Customer.modify(
        customer_id,
        invoice_settings={"default_payment_method": payment_method_id},
    )


def create_payment_intent(
    *,
    amount_cents: int,
    currency: str,
    idempotency_key: str,
    metadata: dict[str, object],
    customer_id: str | None = None,
) -> StripePaymentIntentResult:
    stripe = get_stripe_module()
    payment_intent_payload: dict[str, object] = {
        "amount": amount_cents,
        "currency": currency.lower(),
        "payment_method_types": ["card"],
        "metadata": normalize_metadata(metadata),
        "idempotency_key": idempotency_key,
    }
    if customer_id is not None:
        payment_intent_payload["customer"] = customer_id

    payment_intent = stripe.PaymentIntent.create(**payment_intent_payload)

    return extract_payment_intent_result(payment_intent)


def confirm_payment_intent(
    payment_intent_id: str,
    *,
    payment_method_id: str,
    return_url: str | None = None,
) -> StripePaymentIntentResult:
    stripe = get_stripe_module()
    confirm_payload: dict[str, object] = {
        "payment_method": payment_method_id,
    }
    if return_url:
        confirm_payload["return_url"] = return_url

    payment_intent = stripe.PaymentIntent.confirm(
        payment_intent_id,
        **confirm_payload,
    )

    return extract_payment_intent_result(payment_intent)


def retrieve_payment_intent(payment_intent_id: str) -> StripePaymentIntentResult:
    stripe = get_stripe_module()
    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

    return extract_payment_intent_result(payment_intent)


def construct_webhook_event(payload: bytes, signature: str) -> Any:
    stripe = get_stripe_module()
    webhook_secret = get_stripe_webhook_secret()
    return stripe.Webhook.construct_event(payload, signature, webhook_secret)


def map_payment_intent_status(payment_intent_status: str) -> str:
    if payment_intent_status in {
        "requires_payment_method",
        "requires_confirmation",
        "requires_capture",
    }:
        return "requires_payment_method"

    if payment_intent_status == "requires_action":
        return "requires_action"

    if payment_intent_status == "processing":
        return "processing"

    if payment_intent_status == "succeeded":
        return "succeeded"

    if payment_intent_status == "canceled":
        return "canceled"

    return "processing"
