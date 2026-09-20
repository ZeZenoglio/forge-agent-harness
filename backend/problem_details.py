"""RFC 7807 Problem Details implementation (REQ-033 AC 5).

Provides structured error responses following RFC 7807:
https://datatracker.ietf.org/doc/html/rfc7807
"""

from __future__ import annotations

import http
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ProblemDetailsResponse(JSONResponse):
    media_type = "application/problem+json"


def problem_details(
    status_code: int,
    detail: str,
    title: str | None = None,
    instance: str | None = None,
    type_uri: str = "about:blank",
    extra: dict[str, Any] | None = None,
) -> ProblemDetailsResponse:
    """Construct an RFC 7807 Problem Details JSONResponse."""
    if title is None:
        try:
            title = http.HTTPStatus(status_code).phrase
        except ValueError:
            title = "Error"

    payload: dict[str, Any] = {
        "type": type_uri,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance or "",
    }
    if extra:
        payload.update(extra)

    return ProblemDetailsResponse(
        status_code=status_code,
        content=payload,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> ProblemDetailsResponse:
    """Handle standard HTTPExceptions conforming to RFC 7807."""
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return problem_details(
        status_code=exc.status_code,
        detail=detail,
        instance=request.url.path,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> ProblemDetailsResponse:
    """Handle validation errors conforming to RFC 7807."""
    return problem_details(
        status_code=422,
        title="Unprocessable Entity",
        detail="Request payload validation failed.",
        instance=request.url.path,
        extra={"invalid_params": exc.errors()},
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> ProblemDetailsResponse:
    """Handle uncaught exceptions conforming to RFC 7807."""
    return problem_details(
        status_code=500,
        title="Internal Server Error",
        detail="An unexpected internal server error occurred.",
        instance=request.url.path,
    )
