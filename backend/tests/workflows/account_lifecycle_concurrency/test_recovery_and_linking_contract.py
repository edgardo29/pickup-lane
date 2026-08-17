from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.suite_type("ordinary"),
]

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text(encoding="utf-8")


@pytest.mark.requirement("WS03-02-R8")
def test_sign_in_errors_do_not_distinguish_missing_account_from_wrong_secret() -> None:
    auth_errors = _read("frontend/src/lib/authErrors.js")
    sign_in_form = _read("frontend/src/pages/auth/useSignInForm.js")

    assert "invalid-credential" in auth_errors
    assert "wrong-password" in auth_errors
    assert "user-not-found" in auth_errors
    assert "Email or password is incorrect." in auth_errors
    assert "No account was found with that email." not in auth_errors
    assert "getAuthErrorMessage(requestError)" in sign_in_form


@pytest.mark.requirement("WS03-02-R8")
def test_forgot_password_treats_user_not_found_like_successful_reset_request() -> None:
    forgot_password = _read("frontend/src/pages/auth/ForgotPasswordPage.jsx")
    check_email = _read("frontend/src/pages/auth/CheckEmailPage.jsx")

    assert "await sendPasswordReset(trimmedEmail)" in forgot_password
    assert "requestError?.code?.includes('auth/user-not-found')" in forgot_password
    assert "navigate('/check-email'" in forgot_password
    assert forgot_password.count("navigate('/check-email'") == 2

    assert "await sendPasswordReset(email)" in check_email
    assert "requestError?.code?.includes('auth/user-not-found')" in check_email
    assert "Reset email sent again." in check_email
    assert "If an account exists" in check_email


@pytest.mark.requirement("WS03-02-R8")
def test_reset_password_and_password_linking_remain_provider_owned() -> None:
    credential_actions = _read("frontend/src/context/authProviderCredentialActions.js")
    reset_form = _read("frontend/src/pages/auth/usePasswordResetForm.js")

    assert "sendPasswordResetEmail" in credential_actions
    assert "verifyPasswordResetCode" in credential_actions
    assert "confirmFirebasePasswordReset" in credential_actions
    assert "linkWithCredential(firebaseUser, credential)" in credential_actions
    assert "await verifyPasswordReset(code)" in reset_form
    assert "await confirmPasswordReset(code, password)" in reset_form
    assert "/auth/sync-user" not in reset_form
    assert "fetch(" not in reset_form


@pytest.mark.requirement("WS03-02-R1", "WS03-02-R5", "WS03-02-R8")
def test_local_source_has_conflict_not_email_based_relink_or_merge_authority() -> None:
    auth_account_service = _read("backend/services/auth_account_service.py")
    auth_routes = _read("backend/routes/auth_routes.py")
    user_routes = _read("backend/routes/user_routes.py")

    assert "sync_user_workflow(authorization, db)" in auth_routes
    assert "authorization: str | None = Header(default=None)" in auth_routes
    assert "A user with this email already exists." in auth_account_service
    assert "email_owner.auth_user_id == payload.auth_user_id" in auth_account_service
    assert (
        re.search(
            r"email_owner\.auth_user_id\s*=(?!=)",
            auth_account_service,
        )
        is None
    )
    assert ".auth_user_id = payload.auth_user_id" not in auth_account_service
    assert "reject_generic_user_mutation()" in user_routes
