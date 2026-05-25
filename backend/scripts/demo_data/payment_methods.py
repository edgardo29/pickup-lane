from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models import User, UserPaymentMethod
from backend.scripts.demo_data.helpers import demo_uuid, now_utc, upsert_by_id
from backend.scripts.demo_data.users import CURRENT_USER_KEY


def seed_user_payment_methods(
    db: Session, users: dict[str, User]
) -> dict[str, UserPaymentMethod]:
    timestamp = now_utc()
    current_user = users[CURRENT_USER_KEY]
    payment_method_id = demo_uuid(f"user-payment-method:{CURRENT_USER_KEY}:visa-4242")

    payment_method = upsert_by_id(
        db,
        UserPaymentMethod,
        payment_method_id,
        {
            "user_id": current_user.id,
            "stripe_customer_id": "cus_demo_alex",
            "stripe_payment_method_id": "pm_demo_alex_visa_4242",
            "card_fingerprint": "fp_demo_alex_visa_4242",
            "card_brand": "visa",
            "card_last4": "4242",
            "exp_month": 12,
            "exp_year": 2030,
            "method_status": "active",
            "is_default": True,
            "updated_at": timestamp,
        },
    )

    return {"alex-visa-4242": payment_method}
