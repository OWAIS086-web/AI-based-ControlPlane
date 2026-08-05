import re
from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel

# Accepts any address of the form local@domain — no TLD/DNS restrictions.
# Allows internal domains like .local, .internal, .factory, etc.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", re.IGNORECASE)


def _validate_email(v: str) -> str:
    if not _EMAIL_RE.match(v):
        raise ValueError("Enter a valid email address.")
    return v.lower()


EmailField = Annotated[str, AfterValidator(_validate_email)]

T = TypeVar("T")


class PaginationMeta(BaseModel):
    total: int
    page: int
    limit: int
    totalPages: int


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: PaginationMeta


def make_paginated(items: list, total: int, page: int, limit: int) -> dict:
    total_pages = max(1, (total + limit - 1) // limit)
    return {
        "data": items,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": total_pages,
        },
    }
