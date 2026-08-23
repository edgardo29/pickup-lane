"""Shared bounds for plain collection database reads."""

from __future__ import annotations

DEFAULT_COLLECTION_LIMIT = 50
MAX_COLLECTION_LIMIT = 100
DEFAULT_ADMIN_COLLECTION_LIMIT = 100
MAX_ADMIN_COLLECTION_LIMIT = 200


def bounded_collection_limit(
    limit: int,
    *,
    max_limit: int = MAX_COLLECTION_LIMIT,
) -> int:
    return min(max(limit, 1), max_limit)


def bounded_collection_offset(offset: int) -> int:
    return max(offset, 0)
