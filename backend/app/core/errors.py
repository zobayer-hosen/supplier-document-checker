"""One error type for the whole app, so every API error has the same JSON shape:

    {"error": {"code": "BATCH_NOT_FOUND", "message": "...", "details": [...]}}
"""

from typing import Any


class AppError(Exception):
    """An expected error that is safe to show to the user."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[Any] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


def not_found(what: str, identifier: object) -> AppError:
    return AppError(404, f"{what.upper()}_NOT_FOUND", f"{what.capitalize()} '{identifier}' was not found.")
