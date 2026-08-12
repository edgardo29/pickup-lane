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


def test_generated_identifier_is_valid_canonical_uuidv4():
    correlation_id = generate_correlation_id()

    parsed = uuid.UUID(correlation_id)

    assert parsed.version == 4
    assert str(parsed) == correlation_id
    assert validate_correlation_id(correlation_id) == correlation_id


def test_accepted_valid_identifier_is_returned_unchanged():
    correlation_id = str(uuid.uuid4())

    assert validate_correlation_id(correlation_id) == correlation_id
    assert resolve_correlation_id(correlation_id) == correlation_id


@pytest.mark.parametrize(
    "candidate",
    [
        "",
        "not-a-request-id",
        "123",
        str(uuid.uuid4()).upper(),
        str(uuid.uuid1()),
        f" {uuid.uuid4()}",
        f"{uuid.uuid4()} ",
        "user@example.com",
        "payment-evt_123",
        "venues/example/object.jpg",
        "x" * 100,
    ],
)
def test_malformed_or_unsafe_identifier_is_rejected(candidate):
    with pytest.raises(CorrelationIdError):
        validate_correlation_id(candidate)


def test_control_character_identifier_is_rejected():
    with pytest.raises(CorrelationIdError):
        validate_correlation_id(f"{uuid.uuid4()}\n")


def test_resolve_identifier_generates_when_absent():
    correlation_id = resolve_correlation_id()

    assert validate_correlation_id(correlation_id) == correlation_id


def test_nested_context_restores_previous_value():
    outer_id = str(uuid.uuid4())
    inner_id = str(uuid.uuid4())

    outer_token = set_correlation_id(outer_id)
    try:
        assert get_correlation_id() == outer_id
        inner_token = set_correlation_id(inner_id)
        try:
            assert get_correlation_id() == inner_id
        finally:
            reset_correlation_id(inner_token)
        assert get_correlation_id() == outer_id
    finally:
        reset_correlation_id(outer_token)

    assert get_correlation_id() is None


def test_context_manager_cleans_up_after_exit():
    correlation_id = str(uuid.uuid4())

    with correlation_context(correlation_id) as active_id:
        assert active_id == correlation_id
        assert get_correlation_id() == correlation_id

    assert get_correlation_id() is None


def test_async_tasks_keep_correlation_context_isolated():
    async def worker(correlation_id: str) -> tuple[str | None, str | None]:
        token = set_correlation_id(correlation_id)
        try:
            await asyncio.sleep(0)
            inside_context = get_correlation_id()
        finally:
            reset_correlation_id(token)
        return inside_context, get_correlation_id()

    async def run_workers():
        first_id = str(uuid.uuid4())
        second_id = str(uuid.uuid4())
        return first_id, second_id, await asyncio.gather(
            worker(first_id),
            worker(second_id),
        )

    first_id, second_id, results = asyncio.run(run_workers())

    assert results == [(first_id, None), (second_id, None)]
    assert get_correlation_id() is None
