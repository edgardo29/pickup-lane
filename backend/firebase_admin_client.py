import os
from pathlib import Path

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import auth, credentials

load_dotenv(Path(__file__).resolve().parent / ".env", override=False)


class FirebaseAdminConfigError(RuntimeError):
    pass


def initialize_firebase_admin() -> None:
    if firebase_admin._apps:
        return

    credentials_path = os.getenv("FIREBASE_ADMIN_CREDENTIALS")

    if not credentials_path:
        raise FirebaseAdminConfigError("FIREBASE_ADMIN_CREDENTIALS is not configured.")

    if not os.path.exists(credentials_path):
        raise FirebaseAdminConfigError(
            "FIREBASE_ADMIN_CREDENTIALS does not point to a readable file."
        )

    cred = credentials.Certificate(credentials_path)
    firebase_admin.initialize_app(cred)


def verify_firebase_token(id_token: str) -> dict:
    initialize_firebase_admin()
    return auth.verify_id_token(id_token)


def firebase_email_exists(email: str) -> bool:
    initialize_firebase_admin()

    try:
        auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        return False

    return True


def delete_firebase_user(auth_user_id: str) -> None:
    initialize_firebase_admin()

    try:
        auth.delete_user(auth_user_id)
    except auth.UserNotFoundError:
        return
