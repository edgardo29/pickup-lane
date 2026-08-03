def constraint_values(model: type, constraint_name: str) -> set[str]:
    for constraint in model.__table__.constraints:
        if constraint.name != constraint_name:
            continue

        return set(str(constraint.sqltext).split("'")[1::2])

    raise AssertionError(f"{constraint_name} not found on {model.__name__}")
