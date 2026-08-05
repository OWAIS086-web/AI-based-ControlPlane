def ev(field) -> str:
    """Return the string value of a Prisma enum field.
    Handles both enum objects (field.value) and plain strings."""
    return field.value if hasattr(field, "value") else str(field)
