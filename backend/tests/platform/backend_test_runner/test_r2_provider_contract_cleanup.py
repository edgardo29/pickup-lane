from __future__ import annotations

import uuid

import pytest

from backend.tests.provider_contract.r2.test_r2_object_semantics_contract import (
    R2ContractCleanupError,
    _cleanup_r2_contract_objects,
    _r2_contract_object_keys,
)

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.pass_provenance("WS06-02"),
]

_RUN_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")


def test_cleanup_attempts_only_the_predeclared_exact_keys() -> None:
    prefix, object_keys = _r2_contract_object_keys(_RUN_ID)
    deleted: list[str] = []

    _cleanup_r2_contract_objects(
        prefix=prefix,
        object_keys=object_keys,
        delete_exact_key=deleted.append,
    )

    assert prefix == (
        "provider-contract/r2-object-semantics/"
        "12345678-1234-5678-1234-567812345678/"
    )
    assert deleted == list(object_keys)
    assert all(key.startswith(prefix) for key in deleted)


def test_cleanup_failure_cannot_leave_an_otherwise_passing_test_green() -> None:
    prefix, object_keys = _r2_contract_object_keys(_RUN_ID)
    deleted: list[str] = []

    def fail_one_delete(key: str) -> None:
        deleted.append(key)
        if key == object_keys[1]:
            raise RuntimeError("r2-private cleanup detail")

    with pytest.raises(
        R2ContractCleanupError,
        match="exact-key cleanup failed for 1 owned object",
    ) as exc_info:
        _cleanup_r2_contract_objects(
            prefix=prefix,
            object_keys=object_keys,
            delete_exact_key=fail_one_delete,
        )

    assert deleted == list(object_keys)
    assert "r2-private cleanup detail" not in str(exc_info.value)
    assert all(key not in str(exc_info.value) for key in object_keys)


def test_cleanup_failure_preserves_and_annotates_the_original_failure() -> None:
    prefix, object_keys = _r2_contract_object_keys(_RUN_ID)

    class OriginalFailure(RuntimeError):
        pass

    with pytest.raises(OriginalFailure, match="original R2 assertion") as exc_info:
        try:
            raise OriginalFailure("original R2 assertion")
        finally:
            _cleanup_r2_contract_objects(
                prefix=prefix,
                object_keys=object_keys,
                delete_exact_key=lambda _key: (_ for _ in ()).throw(
                    RuntimeError("cleanup failure")
                ),
            )

    assert exc_info.value.__notes__ == [
        "R2 provider-contract exact-key cleanup failed for 3 owned object(s)."
    ]


def test_cleanup_refuses_keys_outside_the_owned_run_prefix() -> None:
    prefix, object_keys = _r2_contract_object_keys(_RUN_ID)
    unsafe_keys = (
        *object_keys[:-1],
        "provider-contract/r2-object-semantics/other/key.bin",
    )
    deleted: list[str] = []

    with pytest.raises(R2ContractCleanupError, match="invalid owned-key set"):
        _cleanup_r2_contract_objects(
            prefix=prefix,
            object_keys=unsafe_keys,
            delete_exact_key=deleted.append,
        )

    assert deleted == []


def test_cleanup_refuses_a_non_unique_run_prefix() -> None:
    prefix = "provider-contract/r2-object-semantics/shared/"
    object_keys = tuple(
        f"{prefix}{name}"
        for name in ("staging.bin", "publication.bin", "collision.bin")
    )
    deleted: list[str] = []

    with pytest.raises(R2ContractCleanupError, match="invalid owned-key set"):
        _cleanup_r2_contract_objects(
            prefix=prefix,
            object_keys=object_keys,
            delete_exact_key=deleted.append,
        )

    assert deleted == []


def test_invalid_cleanup_state_does_not_replace_an_original_failure() -> None:
    prefix = "provider-contract/r2-object-semantics/shared/"

    class OriginalFailure(RuntimeError):
        pass

    with pytest.raises(OriginalFailure, match="original failure") as exc_info:
        try:
            raise OriginalFailure("original failure")
        finally:
            _cleanup_r2_contract_objects(
                prefix=prefix,
                object_keys=(),
                delete_exact_key=lambda _key: None,
            )

    assert exc_info.value.__notes__ == [
        "R2 provider-contract cleanup refused an invalid owned-key set."
    ]
