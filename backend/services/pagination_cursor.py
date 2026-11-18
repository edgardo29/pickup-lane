"""Signed, context-bound pagination cursors.

A cursor carries the position of the last row a client received. It is signed
with ``CURSOR_SIGNING_SECRET`` so a client cannot construct or modify it, and it
records the context that created it (endpoint, sort direction, filter values,
and any authorization context). A cursor presented with a different context is
rejected.
"""

from __future__ import annotations

import hashlib
import hmac
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as BinasciiError
from json import JSONDecodeError, dumps, loads

from fastapi import HTTPException, status

from backend.settings import SettingsError, get_cursor_signing_secret

CURSOR_INVALID_DETAIL = "cursor is invalid."
CURSOR_CONTEXT_MISMATCH_DETAIL = "cursor does not match the current query."


def encode_signed_cursor(
    payload: dict[str, object],
    *,
    context: dict[str, str],
) -> str:
    body = _serialize({"context": context, "payload": payload})
    signature = hmac.new(_signing_key(), body, hashlib.sha256).digest()
    return f"{_b64encode(body)}.{_b64encode(signature)}"


def decode_signed_cursor(
    cursor: str,
    *,
    context: dict[str, str],
) -> dict[str, object]:
    encoded_body, separator, encoded_signature = cursor.partition(".")
    if not separator:
        raise _invalid_cursor()

    try:
        body = _b64decode(encoded_body)
        signature = _b64decode(encoded_signature)
    except (BinasciiError, ValueError) as exc:
        raise _invalid_cursor() from exc

    expected_signature = hmac.new(_signing_key(), body, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected_signature):
        raise _invalid_cursor()

    try:
        envelope = loads(body.decode("utf-8"))
    except (JSONDecodeError, UnicodeDecodeError) as exc:
        raise _invalid_cursor() from exc

    if not isinstance(envelope, dict) or not isinstance(envelope.get("payload"), dict):
        raise _invalid_cursor()

    if envelope.get("context") != context:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=CURSOR_CONTEXT_MISMATCH_DETAIL,
        )

    return envelope["payload"]


def _signing_key() -> bytes:
    try:
        return get_cursor_signing_secret().encode("utf-8")
    except SettingsError as exc:
        raise RuntimeError(str(exc)) from exc


def _serialize(value: dict[str, object]) -> bytes:
    return dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _b64encode(value: bytes) -> str:
    return urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return urlsafe_b64decode((value + padding).encode("ascii"))


def _invalid_cursor() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=CURSOR_INVALID_DETAIL,
    )
