import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from ai_rag.api.router import router as api_router
from ai_rag.core.config import get_settings
from ai_rag.core.errors import AppError, app_error_handler, unhandled_exception_handler
from ai_rag.core.logging import setup_logging

logger = structlog.get_logger()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    # ── Exception Handlers ──
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ── Active Middlewares ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def correlation_id_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        logger.info(
            "http_request.start",
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "http_request.end",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )
        return response

    # ── Future Middlewares (Reserved Seams - Named Only) ──
    # app.add_middleware(AuthMiddleware)        # Future: Keycloak / JWT verification
    # app.add_middleware(RateLimitMiddleware)   # Future: Redis-backed rate limiting
    # app.add_middleware(TelemetryMiddleware)   # Future: OpenTelemetry tracing

    # ── Routers ──
    app.include_router(api_router)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"app": settings.app_name, "version": settings.app_version}

    return app


app = create_app()
