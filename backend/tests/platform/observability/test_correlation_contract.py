from __future__ import annotations

import asyncio
import uuid

import pytest

from backend.observability.correlation import (
    CorrelationIdError,
    correlation_context,
    generate_correlation_id,
    get_correlation_id,
    reset_correlation_id,
    resolve_correlation_id,
    set_correlation_id,
    validate_correlation_id,
)


pytestmark = pytest.mark.no_db_cleanup


@pytest.mark.requirement("EN02-CORR-001")
def test_generated_correlation_id_is_canonical_uuidv4_without_domain_material():
    correlation_id = generate_correlation_id()
    parsed = uuid.UUID(correlation_id)

    assert parsed.version == 4
    assert str(parsed) == correlation_id
    assert correlation_id == correlation_id.lower()
    assert "user" not in correlation_id
    assert "provider" not in correlation_id
    assert "secret" not in correlation_id


@pytest.mark.requirement("EN02-CORR-001")
def test_canonical_uuidv4_is_accepted_and_unsafe_forms_are_rejected():
    valid = "123e4567-e89b-42d3-a456-426614174000"

    assert validate_correlation_id(valid) == valid

    rejected_values = [
        "not-a-uuid",
        "123e4567-e89b-12d3-a456-426614174000",
        valid.upper(),
        f" {valid}",
        f"{valid}\n",
        valid.replace("-", ""),
        None,
    ]
    for value in rejected_values:
        with pytest.raises(CorrelationIdError):
            validate_correlation_id(value)


@pytest.mark.requirement("EN02-CORR-001")
def test_untrusted_incoming_request_id_is_rejected_or_replaced_when_absent():
    invalid_domain_id = "booking_12345"

    generated_for_missing = resolve_correlation_id(None)
    generated_for_empty = resolve_correlation_id("")

    assert validate_correlation_id(generated_for_missing) == generated_for_missing
    assert validate_correlation_id(generated_for_empty) == generated_for_empty
    with pytest.raises(CorrelationIdError):
        resolve_correlation_id(invalid_domain_id)


@pytest.mark.requirement("EN02-CORR-002")
def test_set_reset_and_nested_context_restore_prior_correlation_id():
    outer = "123e4567-e89b-42d3-a456-426614174000"
    inner = "123e4567-e89b-42d3-a456-426614174001"
    token = set_correlation_id(outer)
    try:
        assert get_correlation_id() == outer
        with correlation_context(inner) as active:
            assert active == inner
            assert get_correlation_id() == inner
        assert get_correlation_id() == outer
    finally:
        reset_correlation_id(token)

    assert get_correlation_id() is None


@pytest.mark.requirement("EN02-CORR-002")
def test_correlation_context_resets_after_failure_path():
    outer = "123e4567-e89b-42d3-a456-426614174002"
    inner = "123e4567-e89b-42d3-a456-426614174003"
    token = set_correlation_id(outer)
    try:
        with pytest.raises(RuntimeError):
            with correlation_context(inner):
                assert get_correlation_id() == inner
                raise RuntimeError("synthetic failure")
        assert get_correlation_id() == outer
    finally:
        reset_correlation_id(token)

    assert get_correlation_id() is None


@pytest.mark.requirement("EN02-CORR-002")
def test_async_tasks_keep_independent_correlation_contexts():
    first = "123e4567-e89b-42d3-a456-426614174004"
    second = "123e4567-e89b-42d3-a456-426614174005"

    async def read_inside_context(correlation_id: str) -> tuple[str, str | None]:
        with correlation_context(correlation_id):
            await asyncio.sleep(0)
            return correlation_id, get_correlation_id()

    async def run_workers() -> list[tuple[str, str | None]]:
        results = await asyncio.gather(
            read_inside_context(first),
            read_inside_context(second),
        )
        return list(results)

    assert asyncio.run(run_workers()) == [(first, first), (second, second)]
    assert get_correlation_id() is None
