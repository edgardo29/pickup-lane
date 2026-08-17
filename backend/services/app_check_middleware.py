"""Firebase App Check ASGI middleware."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Protocol

from starlette.datastructures import Headers
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from backend.observability.events import EventEnvelope
from backend.observability.http_errors import public_error_response
from backend.services.app_check_policy import AppCheckRouteMatch, AppCheckRoutePolicy
from backend.services.app_check_service import (
    APP_CHECK_HEADER_NAME,
    AppCheckVerificationOutcome,
    AppCheckVerificationResult,
    verify_app_check_token,
)
from backend.settings import BackendSettings, FirebaseAppCheckMode


logger = logging.getLogger(__name__)

APP_CHECK_EVENT_NAME = "app_check.request"
APP_CHECK_REQUIRED_CODE = "APP_CHECK.REQUIRED"
APP_CHECK_INVALID_CODE = "APP_CHECK.INVALID"
APP_CHECK_UNAVAILABLE_CODE = "APP_CHECK.UNAVAILABLE"


class AppCheckVerifier(Protocol):
    def __call__(
        self,
        headers: Headers,
        settings: BackendSettings,
    ) -> AppCheckVerificationResult:
        ...


class AppCheckEventRecorder(Protocol):
    def __call__(
        self,
        event: "AppCheckEvent",
        settings: BackendSettings,
    ) -> None:
        ...


@dataclass(frozen=True)
class AppCheckEvent:
    route_template: str
    route_family: str
    operation: str
    outcome: AppCheckVerificationOutcome
    stable_error_code: str | None = None


class AppCheckMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        settings: BackendSettings,
        route_policy: AppCheckRoutePolicy,
        verifier: AppCheckVerifier = verify_app_check_token,
        event_recorder: AppCheckEventRecorder | None = None,
    ) -> None:
        self.app = app
        self._settings = settings
        self._route_policy = route_policy
        self._verifier = verifier
        self._event_recorder = event_recorder or record_app_check_event

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        route_match = self._route_policy.match(
            method=str(scope.get("method") or ""),
            path=str(scope.get("path") or ""),
        )
        if route_match is None or not route_match.applies:
            await self.app(scope, receive, send)
            return

        if self._settings.firebase_app_check_mode is FirebaseAppCheckMode.DISABLED:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        verification = self._verifier(headers, self._settings)
        operation = (
            "app_check.observe"
            if self._settings.firebase_app_check_mode is FirebaseAppCheckMode.OBSERVE
            else "app_check.enforce"
        )
        stable_error_code = _stable_error_code(verification.outcome)
        _record_best_effort(
            self._event_recorder,
            AppCheckEvent(
                route_template=route_match.route_template,
                route_family=route_match.route_family,
                operation=operation,
                outcome=verification.outcome,
                stable_error_code=stable_error_code,
            ),
            self._settings,
        )

        if self._settings.firebase_app_check_mode is FirebaseAppCheckMode.OBSERVE:
            await self.app(scope, receive, send)
            return

        if verification.outcome is AppCheckVerificationOutcome.VALID:
            await self.app(scope, receive, send)
            return

        response = _denial_response(verification.outcome)
        await response(scope, receive, send)


def record_app_check_event(event: AppCheckEvent, settings: BackendSettings) -> None:
    envelope = EventEnvelope(
        event_name=APP_CHECK_EVENT_NAME,
        occurred_at=datetime.now(timezone.utc),
        environment=settings.app_env.value,
        release=settings.release_identity,
        provider_kind="firebase",
        operation=event.operation,
        resource_kind=event.route_family,
        result=event.outcome.value,
        stable_error_code=event.stable_error_code,
        labels={"route_template": event.route_template},
    )
    logger.info(envelope.to_json())


def app_check_header_name() -> str:
    return APP_CHECK_HEADER_NAME


def _record_best_effort(
    recorder: AppCheckEventRecorder,
    event: AppCheckEvent,
    settings: BackendSettings,
) -> None:
    try:
        recorder(event, settings)
    except Exception:  # noqa: BLE001 - recorder failure must not affect decisions.
        return


def _stable_error_code(outcome: AppCheckVerificationOutcome) -> str | None:
    if outcome is AppCheckVerificationOutcome.MISSING:
        return APP_CHECK_REQUIRED_CODE
    if outcome is AppCheckVerificationOutcome.INVALID:
        return APP_CHECK_INVALID_CODE
    if outcome is AppCheckVerificationOutcome.PROVIDER_UNAVAILABLE:
        return APP_CHECK_UNAVAILABLE_CODE
    return None


def _denial_response(outcome: AppCheckVerificationOutcome) -> Response:
    if outcome is AppCheckVerificationOutcome.PROVIDER_UNAVAILABLE:
        return public_error_response(
            status_code=503,
            code=APP_CHECK_UNAVAILABLE_CODE,
            message="App verification is unavailable.",
            detail="App verification is unavailable.",
        )
    if outcome is AppCheckVerificationOutcome.INVALID:
        return public_error_response(
            status_code=403,
            code=APP_CHECK_INVALID_CODE,
            message="App verification failed.",
            detail="App verification failed.",
        )
    return public_error_response(
        status_code=403,
        code=APP_CHECK_REQUIRED_CODE,
        message="App verification required.",
        detail="App verification required.",
    )
