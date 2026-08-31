from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.suite_type("ordinary"),
]

REPO_ROOT = Path(__file__).resolve().parents[4]
FRONTEND_SRC = REPO_ROOT / "frontend/src"

CURRENT_STEP_UP_CALLERS = {
    "frontend/src/pages/profile/useDeleteAccountSettings.js": (
        "runWithStepUp(",
        "deleteAccount(deleteConfirmation)",
        "delete your account",
    ),
    "frontend/src/pages/profile/PaymentMethodsPage.jsx": (
        "runWithStepUp(",
        "setDefaultPaymentMethod(firebaseUser, paymentMethodId, operationId)",
        "removePaymentMethod(firebaseUser, removeCandidate.id, operationId)",
    ),
    "frontend/src/pages/admin/users/AdminUserDeletePreviewModal.jsx": (
        "runWithStepUp(",
        "deleteAdminUser({",
        "delete this account",
    ),
    "frontend/src/pages/admin/users/AdminUserSuspensionModal.jsx": (
        "runWithStepUp(",
        "suspendAdminUser({",
        "suspend this account",
    ),
    "frontend/src/pages/admin/users/AdminUserUnsuspensionModal.jsx": (
        "runWithStepUp(",
        "unsuspendAdminUser({",
        "unsuspend this account",
    ),
    "frontend/src/pages/admin/money/AdminMoneyIssuePage.jsx": (
        "runWithStepUp(",
        "retryAdminMoneyRefund({",
        "retryAdminMoneyIssueCredit({",
        "resolveAdminMoneyIssue({",
    ),
    "frontend/src/pages/admin/money/AdminMoneyRefundPage.jsx": (
        "runWithStepUp(",
        "retryAdminMoneyRefund({",
        "reconcileAdminMoneyRefund({",
    ),
    "frontend/src/pages/admin/community-games/AdminCommunityGameActionModal.jsx": (
        "runWithStepUp(",
        "cancelAdminCommunityGame,",
        "action === 'cancel'",
        "cancel this community game",
        "createAdminFinancialOutcome({",
        "record this financial outcome",
    ),
    "frontend/src/pages/admin/need-a-sub/AdminNeedASubRemovalModal.jsx": (
        "runWithStepUp(",
        "removeAdminNeedASubPost,",
        "action === 'remove'",
        "remove this Need a Sub post",
    ),
    "frontend/src/pages/admin/users/AdminUserHostingRestrictionModal.jsx": (
        "runWithStepUp(",
        "restrictAdminUserHosting({",
        "restrict hosting for this user",
    ),
    "frontend/src/pages/admin/users/AdminUserHostingRestorationModal.jsx": (
        "runWithStepUp(",
        "restoreAdminUserHosting({",
        "restore hosting for this user",
    ),
    "frontend/src/pages/admin/official-games/manage/AdminOfficialGamePage.jsx": (
        "runWithStepUp(",
        "cancelAdminOfficialGame({",
        "cancel this official game",
        "executeAdminOfficialGamePlayerRemoval({",
        "remove this official-game player",
    ),
    "frontend/src/pages/admin/platform-notices/AdminPlatformNoticesPage.jsx": (
        "runWithStepUp(",
        "createPlatformNotice({",
        "cancelPlatformNotice({",
    ),
}


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _frontend_source_files() -> list[Path]:
    excluded_parts = {"node_modules", "dist", "playwright-report", "test-results"}
    return sorted(
        path
        for path in FRONTEND_SRC.rglob("*")
        if path.is_file()
        and path.suffix in {".js", ".jsx", ".ts", ".tsx"}
        and excluded_parts.isdisjoint(path.parts)
    )


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _assert_ordered(source: str, *snippets: str) -> None:
    last_index = -1
    for snippet in snippets:
        index = source.find(snippet, last_index + 1)
        assert index > last_index, f"{snippet!r} was not found after prior snippet"
        last_index = index


def _source_between(source: str, start_snippet: str, end_snippet: str) -> str:
    start = source.index(start_snippet)
    end = source.index(end_snippet, start)
    return source[start:end]


@pytest.mark.requirement("WS03-03A-R7")
def test_email_password_and_google_step_up_use_firebase_reauthentication() -> None:
    reauth = _read("frontend/src/lib/reauthentication.js")
    provider_actions = _read("frontend/src/context/authProviderReauthenticationActions.js")

    assert "EMAIL_PASSWORD_PROVIDER_ID = 'password'" in reauth
    assert "GOOGLE_PROVIDER_ID = 'google.com'" in reauth
    assert "providerIds.has(EMAIL_PASSWORD_PROVIDER_ID)" in reauth
    assert "providerIds.has(GOOGLE_PROVIDER_ID)" in reauth

    assert "if (!password)" in reauth
    _assert_ordered(
        reauth,
        "EmailAuthProvider.credential(firebaseUser.email, password)",
        "reauthenticateWithCredential(firebaseUser, credential)",
        "firebaseUser.getIdToken(true)",
    )
    _assert_ordered(
        reauth,
        "reauthenticateWithPopup(firebaseUser, googleProvider)",
        "firebaseUser.getIdToken(true)",
    )

    assert "EmailAuthProvider" in provider_actions
    assert "GoogleAuthProvider" in provider_actions
    assert "reauthenticateWithCredential" in provider_actions
    assert "reauthenticateWithPopup" in provider_actions
    assert "const googleProvider = new GoogleAuthProvider()" in provider_actions


@pytest.mark.requirement("WS03-03A-R7", "WS03-03A-R8")
def test_step_up_provider_fails_closed_and_exposes_only_caller_owned_actions() -> None:
    provider = _read("frontend/src/context/StepUpProvider.jsx")
    step_up_action = _read("frontend/src/lib/stepUpAction.js")
    context = _read("frontend/src/context/stepUpContext.js")
    hook = _read("frontend/src/hooks/useStepUp.js")

    assert "STEP_UP_REQUIRED_CODE = 'AUTH.RECENT_AUTH_REQUIRED'" in step_up_action
    assert "if (!isStepUpRequiredError(error))" in step_up_action
    _assert_ordered(
        step_up_action,
        "await requestStepUp()",
        "return action()",
    )

    assert "pendingRequest.reject(new StepUpCancelledError())" in provider
    assert "closeRequest('success')" in provider
    assert "closeRequest('cancel')" in provider
    assert "catch (reauthError)" in provider
    assert "setError(getAuthErrorMessage(reauthError))" in provider
    assert "setIsSubmitting(false)" in provider
    assert "confirmStepUp" in provider
    assert "runWithStepUp" in provider
    assert "createContext(null)" in context
    assert "useStepUp must be used within a StepUpProvider." in hook


@pytest.mark.requirement("WS03-03A-R8")
def test_current_high_risk_frontend_callers_opt_into_step_up() -> None:
    for relative_path, required_snippets in CURRENT_STEP_UP_CALLERS.items():
        source = _read(relative_path)
        for snippet in required_snippets:
            assert snippet in source, f"{relative_path} missing {snippet!r}"

    # The backend admin role and game-credit routes are protected even though
    # no current UI source invokes their API functions. If those callers appear,
    # this source inventory must classify them instead of silently relying on
    # low-level transport behavior.
    frontend_text = "\n".join(
        path.read_text(encoding="utf-8") for path in _frontend_source_files()
    )
    assert "await changeAdminUserRole({" not in frontend_text
    assert "() => changeAdminUserRole({" not in frontend_text
    assert "/admin/game-credits/issue" not in frontend_text
    assert "/admin/game-credits/${game_credit_id}/reverse" not in frontend_text


@pytest.mark.requirement("WS03-03A-R7", "WS03-03A-R8")
def test_admin_community_cancel_uses_caller_owned_step_up_without_rekeying_or_merging_financial_outcome() -> None:
    modal_source = _read(
        "frontend/src/pages/admin/community-games/AdminCommunityGameActionModal.jsx"
    )
    submit_body = _source_between(
        modal_source,
        "async function handleSubmit(event) {",
        "  function resetActionKeys",
    )
    action_section = _source_between(
        submit_body,
        "const executeAction = () => config.api({",
        "if (shouldRecordFinancialOutcome)",
    )
    financial_outcome_section = _source_between(
        submit_body,
        "if (shouldRecordFinancialOutcome)",
        "onCompleted(actionResult)",
    )

    assert "const executeAction = () => config.api({" in action_section
    assert "idempotencyKey," in action_section
    assert "createActionIdempotencyKey(" not in action_section
    _assert_ordered(
        action_section,
        "const actionResult = action === 'cancel'",
        "await runWithStepUp(",
        "executeAction,",
        "{ actionLabel: 'cancel this community game' }",
        ": await executeAction()",
    )

    assert "createAdminFinancialOutcome({" not in action_section
    _assert_ordered(
        financial_outcome_section,
        "await runWithStepUp(",
        "createAdminFinancialOutcome({",
        "financialOutcomeIdempotencyKey,",
        "record this financial outcome",
    )
    assert "executeAction" not in financial_outcome_section
    assert "cancelAdminCommunityGame" not in financial_outcome_section

    reset_section = modal_source[modal_source.index("function resetActionKeys") :]
    assert "setIdempotencyKey(createActionIdempotencyKey(config.keyPrefix" in reset_section
    assert action_section.count("idempotencyKey") == 1


@pytest.mark.requirement("WS03-03A-R7", "WS03-03A-R8")
def test_need_a_sub_remove_uses_step_up_without_wrapping_reversible_actions_or_rekeying() -> None:
    modal_source = _read(
        "frontend/src/pages/admin/need-a-sub/AdminNeedASubRemovalModal.jsx"
    )
    submit_body = _source_between(
        modal_source,
        "async function handleSubmit(event) {",
        "  function handleReasonChange",
    )

    assert "const executeAction = () => config.api({" in submit_body
    assert "idempotencyKey," in submit_body
    assert "createActionIdempotencyKey(" not in submit_body
    _assert_ordered(
        submit_body,
        "const result = action === 'remove'",
        "await runWithStepUp(",
        "executeAction,",
        "{ actionLabel: 'remove this Need a Sub post' }",
        ": await executeAction()",
    )


@pytest.mark.requirement("WS03-03A-R7", "WS03-03A-R8")
def test_hosting_restriction_wraps_execution_only_and_preserves_preview_and_idempotency() -> None:
    modal_source = _read(
        "frontend/src/pages/admin/users/AdminUserHostingRestrictionModal.jsx"
    )
    preview_section = _source_between(
        modal_source,
        "async function handleRefreshPreview() {",
        "  async function handleSubmit(event) {",
    )
    submit_body = _source_between(
        modal_source,
        "async function handleSubmit(event) {",
        "  function handleReasonChange",
    )

    assert "runWithStepUp(" not in preview_section
    assert "previewAdminUserHostingRestriction({" in preview_section
    assert "const executeRestriction = () => restrictAdminUserHosting({" in submit_body
    assert "idempotencyKey," in submit_body
    assert "previewToken: preview.preview_token" in submit_body
    assert "createIdempotencyKey(" not in submit_body
    _assert_ordered(
        submit_body,
        "const executeRestriction = () => restrictAdminUserHosting({",
        "previewToken: preview.preview_token",
        "const nextResult = await runWithStepUp(",
        "executeRestriction,",
        "{ actionLabel: 'restrict hosting for this user' }",
    )


@pytest.mark.requirement("WS03-03A-R7", "WS03-03A-R8")
def test_hosting_restoration_wraps_execution_only_and_preserves_idempotency() -> None:
    modal_source = _read(
        "frontend/src/pages/admin/users/AdminUserHostingRestorationModal.jsx"
    )
    submit_body = _source_between(
        modal_source,
        "async function handleSubmit(event) {",
        "  function handleBackdropClick",
    )

    assert "const executeRestoration = () => restoreAdminUserHosting({" in submit_body
    assert "idempotencyKey," in submit_body
    assert "createIdempotencyKey(" not in submit_body
    _assert_ordered(
        submit_body,
        "const executeRestoration = () => restoreAdminUserHosting({",
        "const nextResult = await runWithStepUp(",
        "executeRestoration,",
        "{ actionLabel: 'restore hosting for this user' }",
    )


@pytest.mark.requirement("WS03-03A-R7", "WS03-03A-R8")
def test_official_player_removal_wraps_execution_only_and_preserves_preview_decision() -> None:
    page_source = _read(
        "frontend/src/pages/admin/official-games/manage/AdminOfficialGamePage.jsx"
    )
    preview_section = _source_between(
        page_source,
        "async function handlePreviewRemoval(participant) {",
        "  const handleCloseRemovalPreview",
    )
    execute_section = _source_between(
        page_source,
        "async function handleExecuteRemoval({ outcome, reason }) {",
        "  async function loadCancelPreview() {",
    )

    assert "runWithStepUp(" not in preview_section
    assert "previewAdminOfficialGamePlayerRemoval({" in preview_section
    assert "const executeRemoval = () => executeAdminOfficialGamePlayerRemoval({" in execute_section
    assert "participantId: previewParticipant.id" in execute_section
    assert "previewToken: removalPreview.preview_token" in execute_section
    assert "outcome," in execute_section
    assert "reason," in execute_section
    assert "error.status === 409" in execute_section
    _assert_ordered(
        execute_section,
        "const executeRemoval = () => executeAdminOfficialGamePlayerRemoval({",
        "previewToken: removalPreview.preview_token",
        "outcome,",
        "reason,",
        "const result = await runWithStepUp(",
        "executeRemoval,",
        "{ actionLabel: 'remove this official-game player' }",
    )


@pytest.mark.requirement("WS03-03A-R8")
def test_no_current_frontend_caller_exists_for_backend_only_protected_routes() -> None:
    destructive_callers: list[str] = []
    payment_event_callers: list[str] = []

    for path in _frontend_source_files():
        relative_path = _relative(path)
        source = path.read_text(encoding="utf-8")
        if "/payment-events/" in source:
            payment_event_callers.append(relative_path)
        if "method: 'DELETE'" in source and (
            "/games/${" in source or "/venues/${" in source
        ):
            destructive_callers.append(relative_path)

    assert payment_event_callers == []
    assert destructive_callers == []


@pytest.mark.requirement("WS03-03A-R8")
def test_low_level_api_client_does_not_globally_replay_recent_auth_failures() -> None:
    api_client = _read("frontend/src/lib/apiClient.js")
    frontend_occurrences: list[str] = []

    assert "AUTH.RECENT_AUTH_REQUIRED" not in api_client
    assert "STEP_UP_REQUIRED_CODE" not in api_client
    assert "runWithStepUp" not in api_client
    assert "requestStepUp" not in api_client
    assert "getIdToken" not in api_client
    assert "forceRefresh" not in api_client
    assert api_client.count("fetch(") == 1
    assert api_client.count("apiRequest(") == 1

    for path in _frontend_source_files():
        relative_path = _relative(path)
        source = path.read_text(encoding="utf-8")
        if "AUTH.RECENT_AUTH_REQUIRED" in source:
            frontend_occurrences.append(relative_path)

    assert frontend_occurrences == ["frontend/src/lib/stepUpAction.js"]


@pytest.mark.requirement("WS03-03A-R7", "WS03-03A-R9")
def test_add_password_linking_requires_step_up_before_firebase_linking() -> None:
    add_password = _read("frontend/src/pages/profile/useAddPasswordSettings.js")
    settings_model = _read("frontend/src/pages/profile/useSettingsPageModel.jsx")
    credential_actions = _read("frontend/src/context/authProviderCredentialActions.js")

    _assert_ordered(
        add_password,
        "await confirmStepUp({ actionLabel: 'add password sign-in' })",
        "await addPasswordToCurrentAccount(newPassword)",
    )
    assert "const { confirmStepUp, runWithStepUp } = useStepUp()" in settings_model
    assert "confirmStepUp," in settings_model
    assert "addPasswordToCurrentAccount," in settings_model

    _assert_ordered(
        credential_actions,
        "EmailAuthProvider.credential(firebaseUser.email, password)",
        "linkWithCredential(firebaseUser, credential)",
        "firebaseUser.reload()",
        "setFirebaseUser(auth.currentUser)",
    )
    assert "apiRequest(" not in credential_actions


@pytest.mark.requirement("WS03-03A-R7", "WS03-03A-R8", "WS03-03A-R9")
def test_step_up_source_does_not_forward_passwords_or_provider_credentials_to_backend() -> None:
    step_up_related_sources = {
        "frontend/src/lib/reauthentication.js": _read("frontend/src/lib/reauthentication.js"),
        "frontend/src/lib/stepUpAction.js": _read("frontend/src/lib/stepUpAction.js"),
        "frontend/src/context/StepUpProvider.jsx": _read(
            "frontend/src/context/StepUpProvider.jsx"
        ),
        "frontend/src/context/authProviderReauthenticationActions.js": _read(
            "frontend/src/context/authProviderReauthenticationActions.js"
        ),
        "frontend/src/pages/profile/useAddPasswordSettings.js": _read(
            "frontend/src/pages/profile/useAddPasswordSettings.js"
        ),
    }
    combined = "\n".join(step_up_related_sources.values())

    assert "apiRequest(" not in combined
    assert "fetch(" not in combined
    assert "localStorage" not in combined
    assert "sessionStorage" not in combined
    assert "indexedDB" not in combined
    assert "providerCredential" not in combined
    assert "accessToken" not in combined
    assert "refreshToken" not in combined
