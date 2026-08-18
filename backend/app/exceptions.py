"""Custom application exceptions and their FastAPI exception handlers.

Routers/services should raise these instead of `HTTPException` directly so
error handling stays consistent across modules. Handlers are registered on
the `app` instance in `app.main`.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base class for all REVVY application exceptions."""

    def __init__(self, message: str, code: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppException):
    """Raised when a requested resource does not exist. Maps to HTTP 404."""

    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(f"{resource} not found", "NOT_FOUND", status.HTTP_404_NOT_FOUND)


class ConflictError(AppException):
    """Raised on a state conflict (e.g. duplicate email). Maps to HTTP 409."""

    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(message, "CONFLICT", status.HTTP_409_CONFLICT)


class UnauthorizedError(AppException):
    """Raised when auth is missing/invalid. Maps to HTTP 401."""

    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(message, "UNAUTHORIZED", status.HTTP_401_UNAUTHORIZED)


class ValidationError(AppException):
    """Raised for domain-level validation failures. Maps to HTTP 400."""

    def __init__(self, message: str = "Invalid request") -> None:
        super().__init__(message, "VALIDATION_ERROR", status.HTTP_400_BAD_REQUEST)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Convert any `AppException` subclass into a structured JSON response."""
    logger.warning(
        "AppException handled: %s (code=%s, path=%s)",
        exc.message,
        exc.code,
        request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler so unexpected errors never leak stack traces to clients."""
    logger.exception("Unhandled exception on path %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "code": "INTERNAL_ERROR"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the given FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
