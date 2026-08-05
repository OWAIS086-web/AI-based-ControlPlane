from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppError(HTTPException):
    """Base application exception that serialises as RFC 7807."""

    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        error_type: str = "about:blank",
        errors: list[dict] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.title = title
        self.error_type = error_type
        self.errors = errors


def problem_detail_response(exc: AppError) -> JSONResponse:
    body: dict = {
        "type": exc.error_type,
        "title": exc.title,
        "status": exc.status_code,
        "detail": exc.detail,
    }
    if exc.errors:
        body["errors"] = exc.errors
    return JSONResponse(status_code=exc.status_code, content=body)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return problem_detail_response(exc)


# ── Convenience factories ────────────────────────────────────────────────────


def not_found(entity: str) -> AppError:
    return AppError(404, "Not Found", f"{entity} not found.")


def conflict(detail: str) -> AppError:
    return AppError(409, "Conflict", detail)


def forbidden(detail: str = "Insufficient permissions.") -> AppError:
    return AppError(403, "Forbidden", detail)


def unprocessable(detail: str, errors: list[dict] | None = None) -> AppError:
    return AppError(422, "Unprocessable Entity", detail, errors=errors)


def bad_request(detail: str) -> AppError:
    return AppError(400, "Bad Request", detail)


def unauthorized(detail: str = "Invalid or expired credentials.") -> AppError:
    return AppError(401, "Unauthorized", detail)
