from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    logger.info("ROHE service starting up")
    yield
    logger.info("ROHE service shutting down")


def create_app(title: str = "ROHE", version: str = "0.0.8") -> FastAPI:
    app = FastAPI(
        title=title,
        version=version,
        description="Orchestration framework for End-to-End ML Serving on Heterogeneous Edge",
        lifespan=lifespan,
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled error on {request.method} {request.url.path}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": "Internal server error"},
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
