import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


class AppError(Exception):
    """Base application exception."""

    def __init__(
        self,
        error: str,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> None:
        super().__init__(message)
        self.error = error
        self.message = message
        self.status_code = status_code


class LLMError(AppError):
    """Raised when an LLM provider operation fails."""

    def __init__(self, message: str = "LLM service unavailable") -> None:
        super().__init__(
            error="llm_error",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class EmptyMessageError(AppError):
    """Raised when a chat message is empty or whitespace only."""

    def __init__(self, message: str = "Message cannot be empty") -> None:
        super().__init__(
            error="empty_message",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        "app_error",
        error=exc.error,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error,
            "message": exc.message,
            "request_id": request_id,
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "unhandled_exception",
        error=str(exc),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred",
            "request_id": request_id,
        },
    )
