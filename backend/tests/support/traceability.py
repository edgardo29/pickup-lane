from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re


REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "domain",
    "authoritative_sources",
    "behaviors",
    "test_refs",
}
OPTIONAL_TOP_LEVEL_KEYS = {
    "applicability",
    "known_gaps",
    "external_boundaries",
}
ALLOWED_TOP_LEVEL_KEYS = REQUIRED_TOP_LEVEL_KEYS | OPTIONAL_TOP_LEVEL_KEYS
MAX_SCALAR_LENGTH = 280
MAX_LIST_ITEMS = 50
DOMAIN_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class TraceabilityValidation:
    data: dict[str, Any] | None
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


class TraceabilitySyntaxError(ValueError):
    """Raised when a lightweight manifest cannot be parsed."""


def validate_traceability_manifest_path(path: Path) -> TraceabilityValidation:
    try:
        text = path.read_text()
    except OSError as exc:
        return TraceabilityValidation(None, (f"could not read manifest: {exc}",))
    return validate_traceability_manifest_text(text)


def validate_traceability_manifest_text(text: str) -> TraceabilityValidation:
    try:
        data = parse_lightweight_yaml(text)
    except TraceabilitySyntaxError as exc:
        return TraceabilityValidation(None, (str(exc),))
    errors = list(validate_traceability_manifest(data))
    return TraceabilityValidation(data, tuple(errors))


def parse_lightweight_yaml(text: str) -> dict[str, Any]:
    """Parse the small flat YAML subset used by traceability manifests.

    The project does not depend on PyYAML. This parser intentionally accepts
    only the simple shape used by `testing_manifest.template.yaml`: top-level
    scalars and top-level lists of scalars or flat mappings.
    """

    data: dict[str, Any] = {}
    current_key: str | None = None
    current_item: dict[str, Any] | None = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line:
            raise TraceabilitySyntaxError(f"line {line_number}: tabs are not allowed")

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()

        if indent == 0:
            key, value = _split_key_value(stripped, line_number)
            if key in data:
                raise TraceabilitySyntaxError(f"line {line_number}: duplicate key {key!r}")
            if value == "":
                data[key] = []
                current_key = key
                current_item = None
            else:
                data[key] = _parse_scalar(value)
                current_key = None
                current_item = None
            continue

        if indent == 2 and stripped.startswith("- "):
            if current_key is None or not isinstance(data.get(current_key), list):
                raise TraceabilitySyntaxError(
                    f"line {line_number}: list item has no top-level list"
                )
            item_text = stripped[2:].strip()
            if not item_text:
                raise TraceabilitySyntaxError(f"line {line_number}: empty list item")
            if _looks_like_mapping_entry(item_text):
                key, value = _split_key_value(item_text, line_number)
                item = {key: _parse_scalar(value)}
                data[current_key].append(item)
                current_item = item
            else:
                data[current_key].append(_parse_scalar(item_text))
                current_item = None
            continue

        if indent == 4:
            if current_item is None:
                raise TraceabilitySyntaxError(
                    f"line {line_number}: nested key has no mapping list item"
                )
            key, value = _split_key_value(stripped, line_number)
            if value == "":
                raise TraceabilitySyntaxError(
                    f"line {line_number}: nested lists are not supported"
                )
            if key in current_item:
                raise TraceabilitySyntaxError(f"line {line_number}: duplicate key {key!r}")
            current_item[key] = _parse_scalar(value)
            continue

        raise TraceabilitySyntaxError(
            f"line {line_number}: unsupported indentation or nesting"
        )

    return data


def validate_traceability_manifest(data: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []

    unknown = sorted(set(data) - ALLOWED_TOP_LEVEL_KEYS)
    if unknown:
        errors.append(f"unknown top-level key(s): {', '.join(unknown)}")

    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - set(data))
    if missing:
        errors.append(f"missing required top-level key(s): {', '.join(missing)}")

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    domain = data.get("domain")
    if not isinstance(domain, str) or not DOMAIN_RE.fullmatch(domain):
        errors.append("domain must be a lowercase token such as games or need_a_sub")

    _validate_list(data, "authoritative_sources", errors, required=True)
    _validate_list(data, "behaviors", errors, required=True, require_mapping=True)
    _validate_list(data, "test_refs", errors, required=True)
    _validate_list(data, "applicability", errors, required=False)
    _validate_list(data, "known_gaps", errors, required=False)
    _validate_list(data, "external_boundaries", errors, required=False)

    for behavior in data.get("behaviors", []):
        if not isinstance(behavior, dict):
            continue
        for key in ("id", "summary", "source"):
            if not _non_empty_scalar(behavior.get(key)):
                errors.append(f"behavior entries require {key}")

    _validate_scalar_lengths(data, errors)
    return tuple(errors)


def _validate_list(
    data: dict[str, Any],
    key: str,
    errors: list[str],
    *,
    required: bool,
    require_mapping: bool = False,
) -> None:
    value = data.get(key)
    if value is None:
        if required:
            errors.append(f"{key} must be provided")
        return
    if not isinstance(value, list):
        errors.append(f"{key} must be a list")
        return
    if required and not value:
        errors.append(f"{key} must not be empty")
    if len(value) > MAX_LIST_ITEMS:
        errors.append(f"{key} must stay small; found {len(value)} entries")
    if require_mapping and any(not isinstance(item, dict) for item in value):
        errors.append(f"{key} entries must be mappings")


def _validate_scalar_lengths(value: Any, errors: list[str]) -> None:
    if isinstance(value, str) and len(value) > MAX_SCALAR_LENGTH:
        errors.append("manifest scalar values must stay concise")
    elif isinstance(value, dict):
        for nested in value.values():
            _validate_scalar_lengths(nested, errors)
    elif isinstance(value, list):
        for nested in value:
            _validate_scalar_lengths(nested, errors)


def _non_empty_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, bool)) and str(value).strip() != ""


def _looks_like_mapping_entry(value: str) -> bool:
    if ":" not in value:
        return False
    prefix = value.split(":", 1)[0]
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", prefix))


def _split_key_value(value: str, line_number: int) -> tuple[str, str]:
    if ":" not in value:
        raise TraceabilitySyntaxError(f"line {line_number}: expected key: value")
    key, scalar = value.split(":", 1)
    key = key.strip()
    if not key:
        raise TraceabilitySyntaxError(f"line {line_number}: empty key")
    return key, scalar.strip()


def _parse_scalar(value: str) -> str | int | bool:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1]
    return value
