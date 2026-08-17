"""Firebase App Check verification boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from backend.firebase_admin_client import (
    FirebaseAppCheckUnavailableError,
    FirebaseAdminConfigError,
    verify_firebase_app_check_token,
)
from backend.observability.timeouts import DependencyReadTimeoutError
from backend.settings import BackendSettings


APP_CHECK_HEADER_NAME = "X-Firebase-AppCheck"


class AppCheckVerificationOutcome(str, Enum):
    VALID = "valid"
    MISSING = "missing"
    INVALID = "invalid"
    PROVIDER_UNAVAILABLE = "provider_unavailable"


@dataclass(frozen=True)
class AppCheckVerificationResult:
    outcome: AppCheckVerificationOutcome


def verify_app_check_token(
    headers: Mapping[str, str],
    settings: BackendSettings,
) -> AppCheckVerificationResult:
    token = _header_token(headers)
    if token is None:
        return AppCheckVerificationResult(AppCheckVerificationOutcome.MISSING)

    expected_app_id = settings.firebase_app_check_app_id
    if not expected_app_id:
        return AppCheckVerificationResult(
            AppCheckVerificationOutcome.PROVIDER_UNAVAILABLE
        )

    try:
        verified_claims = verify_firebase_app_check_token(token)
    except FirebaseAdminConfigError:
        return AppCheckVerificationResult(
            AppCheckVerificationOutcome.PROVIDER_UNAVAILABLE
        )
    except ValueError:
        return AppCheckVerificationResult(AppCheckVerificationOutcome.INVALID)
    except (DependencyReadTimeoutError, FirebaseAppCheckUnavailableError):
        return AppCheckVerificationResult(
            AppCheckVerificationOutcome.PROVIDER_UNAVAILABLE
        )

    verified_app_id = verified_claims.get("app_id")
    if not isinstance(verified_app_id, str) or verified_app_id != expected_app_id:
        return AppCheckVerificationResult(AppCheckVerificationOutcome.INVALID)

    return AppCheckVerificationResult(AppCheckVerificationOutcome.VALID)


def _header_token(headers: Mapping[str, str]) -> str | None:
    value = headers.get(APP_CHECK_HEADER_NAME)
    if value is None:
        for name, candidate in headers.items():
            if name.lower() == APP_CHECK_HEADER_NAME.lower():
                value = candidate
                break
    if value is None:
        return None
    token = value.strip()
    return token or None
