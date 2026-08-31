from dataclasses import dataclass
from typing import Any

from backend.observability.timeouts import (
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
    is_timeout_like_exception,
)
from backend.settings import SUPPORTED_STRIPE_CURRENCY, SettingsError, get_settings

DEFAULT_STRIPE_CURRENCY = SUPPORTED_STRIPE_CURRENCY


class StripeConfigError(RuntimeError):
    """Raised when Stripe cannot be called safely from this environment."""


@dataclass(frozen=True)
class StripeClientPair:
    read: Any
    mutation: Any


@dataclass(frozen=True)
class StripePaymentIntentResult:
    id: str
    client_secret: str | None
    status: str
    latest_charge_id: str | None = None
    amount_cents: int | None = None
    amount_received_cents: int | None = None
    currency: str | None = None
    customer_id: str | None = None
    metadata: dict[str, str] | None = None
    failure_code: str | None = None


@dataclass(frozen=True)
class StripeRefundResult:
    id: str
    status: str
    amount_cents: int
    currency: str
    charge_id: str | None
    payment_intent_id: str | None


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
    return _stripe_settings().stripe_currency


def stripe_payments_enabled() -> bool:
    return _stripe_settings().enable_stripe_payments


def get_stripe_publishable_key() -> str:
    publishable_key = _stripe_settings().stripe_publishable_key_value
    if not publishable_key:
        raise StripeConfigError("STRIPE_PUBLISHABLE_KEY is not configured.")

    return publishable_key


def get_stripe_webhook_secret() -> str:
    webhook_secret = _stripe_settings().stripe_webhook_secret_value
    if not webhook_secret:
        raise StripeConfigError("STRIPE_WEBHOOK_SECRET is not configured.")

    return webhook_secret


def get_stripe_secret_key() -> str:
    secret_key = _stripe_settings().stripe_secret_key_value
    if not secret_key:
        raise StripeConfigError("STRIPE_SECRET_KEY is not configured.")

    return secret_key


def get_stripe_module() -> Any:
    if not stripe_payments_enabled():
        raise StripeConfigError("Stripe payments are disabled for this demo.")

    stripe = _import_stripe_module()

    stripe.api_key = get_stripe_secret_key()
    return stripe


def get_stripe_client_pair() -> StripeClientPair:
    settings = _stripe_settings()
    if not settings.enable_stripe_payments:
        raise StripeConfigError("Stripe payments are disabled for this demo.")

    stripe = _import_stripe_module()
    secret_key = settings.stripe_secret_key_value
    if not secret_key:
        raise StripeConfigError("STRIPE_SECRET_KEY is not configured.")

    return StripeClientPair(
        read=_build_stripe_client(
            stripe,
            secret_key=secret_key,
            timeout_seconds=settings.stripe_read_timeout_seconds,
        ),
        mutation=_build_stripe_client(
            stripe,
            secret_key=secret_key,
            timeout_seconds=settings.stripe_mutation_timeout_seconds,
        ),
    )


def _import_stripe_module() -> Any:
    try:
        import stripe
    except ModuleNotFoundError as exc:
        raise StripeConfigError(
            "The Stripe Python SDK is not installed. Install backend requirements first."
        ) from exc

    return stripe


def _build_stripe_client(
    stripe: Any,
    *,
    secret_key: str,
    timeout_seconds: int,
) -> Any:
    return stripe.StripeClient(
        secret_key,
        http_client=stripe.RequestsClient(timeout=timeout_seconds),
    )


def _stripe_settings():
    try:
        return get_settings()
    except SettingsError as exc:
        raise StripeConfigError(str(exc)) from exc


def normalize_metadata(metadata: dict[str, object]) -> dict[str, str]:
    return {
        key: str(value)
        for key, value in metadata.items()
        if value is not None
    }


def extract_payment_intent_result(payment_intent: Any) -> StripePaymentIntentResult:
    latest_charge = getattr(payment_intent, "latest_charge", None)
    latest_charge_id = latest_charge if isinstance(latest_charge, str) else None

    customer = getattr(payment_intent, "customer", None)
    metadata = getattr(payment_intent, "metadata", None)
    last_error = getattr(payment_intent, "last_payment_error", None)
    return StripePaymentIntentResult(
        id=payment_intent.id,
        client_secret=getattr(payment_intent, "client_secret", None),
        status=payment_intent.status,
        latest_charge_id=latest_charge_id,
        amount_cents=getattr(payment_intent, "amount", None),
        amount_received_cents=getattr(payment_intent, "amount_received", None),
        currency=str(getattr(payment_intent, "currency", "") or "").upper() or None,
        customer_id=customer if isinstance(customer, str) else None,
        metadata=dict(metadata) if isinstance(metadata, dict) else None,
        failure_code=(
            str(getattr(last_error, "code", "") or "") or None
            if last_error is not None
            else None
        ),
    )


def extract_refund_result(refund: Any) -> StripeRefundResult:
    charge = getattr(refund, "charge", None)
    payment_intent = getattr(refund, "payment_intent", None)

    return StripeRefundResult(
        id=refund.id,
        status=str(getattr(refund, "status", "") or ""),
        amount_cents=int(getattr(refund, "amount", 0) or 0),
        currency=str(getattr(refund, "currency", "") or "").upper(),
        charge_id=charge if isinstance(charge, str) else None,
        payment_intent_id=payment_intent if isinstance(payment_intent, str) else None,
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
    client = get_stripe_client_pair().mutation
    customer = _call_stripe_mutation(
        "customer.create",
        lambda: client.v1.customers.create(
            {
                "email": email,
                "name": name,
                "metadata": normalize_metadata(metadata),
            },
            options={"idempotency_key": idempotency_key},
        ),
    )
    return StripeCustomerResult(id=customer.id)


def create_setup_intent(
    *,
    customer_id: str,
    idempotency_key: str,
    metadata: dict[str, object],
) -> StripeSetupIntentResult:
    client = get_stripe_client_pair().mutation
    setup_intent = _call_stripe_mutation(
        "setup_intent.create",
        lambda: client.v1.setup_intents.create(
            {
                "customer": customer_id,
                "payment_method_types": ["card"],
                "usage": "off_session",
                "metadata": normalize_metadata(metadata),
            },
            options={"idempotency_key": idempotency_key},
        ),
    )
    return extract_setup_intent_result(setup_intent)


def retrieve_setup_intent(setup_intent_id: str) -> StripeSetupIntentResult:
    client = get_stripe_client_pair().read
    setup_intent = _call_stripe_read(
        "setup_intent.retrieve",
        lambda: client.v1.setup_intents.retrieve(setup_intent_id),
    )
    return extract_setup_intent_result(setup_intent)


def retrieve_payment_method(
    payment_method_id: str,
) -> StripePaymentMethodCardResult:
    client = get_stripe_client_pair().read
    payment_method = _call_stripe_read(
        "payment_method.retrieve",
        lambda: client.v1.payment_methods.retrieve(payment_method_id),
    )
    return extract_card_payment_method_result(payment_method)


def detach_payment_method(
    payment_method_id: str,
    *,
    idempotency_key: str | None = None,
) -> None:
    client = get_stripe_client_pair().mutation

    def detach():
        if idempotency_key is None:
            return client.v1.payment_methods.detach(payment_method_id)
        return client.v1.payment_methods.detach(
            payment_method_id,
            options={"idempotency_key": idempotency_key},
        )

    _call_stripe_mutation(
        "payment_method.detach",
        detach,
    )


def set_customer_default_payment_method(
    *,
    customer_id: str,
    payment_method_id: str,
    idempotency_key: str | None = None,
) -> None:
    client = get_stripe_client_pair().mutation

    def set_default():
        payload = {
            "invoice_settings": {"default_payment_method": payment_method_id}
        }
        if idempotency_key is None:
            return client.v1.customers.update(customer_id, payload)
        return client.v1.customers.update(
            customer_id,
            payload,
            options={"idempotency_key": idempotency_key},
        )

    _call_stripe_mutation(
        "customer.default_payment_method.set",
        set_default,
    )


def clear_customer_default_payment_method(
    *,
    customer_id: str,
    idempotency_key: str | None = None,
) -> None:
    client = get_stripe_client_pair().mutation

    def clear_default():
        payload = {"invoice_settings": {"default_payment_method": None}}
        if idempotency_key is None:
            return client.v1.customers.update(customer_id, payload)
        return client.v1.customers.update(
            customer_id,
            payload,
            options={"idempotency_key": idempotency_key},
        )

    _call_stripe_mutation(
        "customer.default_payment_method.clear",
        clear_default,
    )


def create_payment_intent(
    *,
    amount_cents: int,
    currency: str,
    idempotency_key: str,
    metadata: dict[str, object],
    customer_id: str | None = None,
) -> StripePaymentIntentResult:
    client = get_stripe_client_pair().mutation
    payment_intent_payload: dict[str, object] = {
        "amount": amount_cents,
        "currency": currency.lower(),
        "payment_method_types": ["card"],
        "metadata": normalize_metadata(metadata),
    }
    if customer_id is not None:
        payment_intent_payload["customer"] = customer_id

    payment_intent = _call_stripe_mutation(
        "payment_intent.create",
        lambda: client.v1.payment_intents.create(
            payment_intent_payload,
            options={"idempotency_key": idempotency_key},
        ),
    )

    return extract_payment_intent_result(payment_intent)


def confirm_payment_intent(
    payment_intent_id: str,
    *,
    payment_method_id: str,
    return_url: str | None = None,
    off_session: bool = False,
    idempotency_key: str | None = None,
) -> StripePaymentIntentResult:
    confirm_payload: dict[str, object] = {
        "payment_method": payment_method_id,
    }
    if return_url:
        confirm_payload["return_url"] = return_url
    if off_session:
        confirm_payload["off_session"] = True

    client = get_stripe_client_pair().mutation
    def confirm():
        if idempotency_key is None:
            return client.v1.payment_intents.confirm(
                payment_intent_id,
                confirm_payload,
            )
        return client.v1.payment_intents.confirm(
            payment_intent_id,
            confirm_payload,
            options={"idempotency_key": idempotency_key},
        )

    payment_intent = _call_stripe_mutation("payment_intent.confirm", confirm)

    return extract_payment_intent_result(payment_intent)


def retrieve_payment_intent(payment_intent_id: str) -> StripePaymentIntentResult:
    client = get_stripe_client_pair().read
    payment_intent = _call_stripe_read(
        "payment_intent.retrieve",
        lambda: client.v1.payment_intents.retrieve(payment_intent_id),
    )

    return extract_payment_intent_result(payment_intent)


def create_refund(
    *,
    charge_id: str,
    amount_cents: int,
    currency: str,
    idempotency_key: str,
    metadata: dict[str, object],
) -> StripeRefundResult:
    get_stripe_currency()
    if currency.upper() != DEFAULT_STRIPE_CURRENCY:
        raise StripeConfigError("Pickup Lane Stripe refunds currently support USD only.")

    client = get_stripe_client_pair().mutation
    refund = _call_stripe_mutation(
        "refund.create",
        lambda: client.v1.refunds.create(
            {
                "charge": charge_id,
                "amount": amount_cents,
                "metadata": normalize_metadata(metadata),
            },
            options={"idempotency_key": idempotency_key},
        ),
    )

    return extract_refund_result(refund)


def retrieve_refund(refund_id: str) -> StripeRefundResult:
    client = get_stripe_client_pair().read
    refund = _call_stripe_read(
        "refund.retrieve",
        lambda: client.v1.refunds.retrieve(refund_id),
    )

    return extract_refund_result(refund)


def construct_webhook_event(payload: bytes, signature: str) -> Any:
    stripe = get_stripe_module()
    webhook_secret = get_stripe_webhook_secret()
    return stripe.Webhook.construct_event(payload, signature, webhook_secret)


def _call_stripe_read(operation: str, call):
    try:
        return call()
    except Exception as exc:
        if is_timeout_like_exception(exc):
            raise DependencyReadTimeoutError(
                provider_kind="stripe",
                operation=f"stripe.{operation}",
            ) from exc
        raise


def _call_stripe_mutation(operation: str, call):
    try:
        return call()
    except Exception as exc:
        if is_timeout_like_exception(exc):
            raise DependencyMutationTimeoutUnknownError(
                provider_kind="stripe",
                operation=f"stripe.{operation}",
            ) from exc
        raise


def map_payment_intent_status(payment_intent_status: str) -> str:
    if payment_intent_status in {
        "requires_payment_method",
        "requires_confirmation",
        "requires_action",
        "processing",
        "requires_capture",
        "succeeded",
        "canceled",
    }:
        return payment_intent_status

    return "unknown"
