from fastapi import HTTPException, status


def raise_retired_mutation_route(*, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "code": code,
            "message": message,
        },
    )
