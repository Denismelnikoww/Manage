"""Унифицированные ошибки API по контракту 4.4.8."""

from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class ApiError(HTTPException):
    """HTTP-ошибка с машиночитаемым кодом (code/message/details)."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    payload: dict[str, Any] = {"code": exc.code, "message": exc.message}
    if exc.details:
        payload["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=payload)