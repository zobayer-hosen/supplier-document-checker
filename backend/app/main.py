"""FastAPI application. Start it with:

    uvicorn app.main:app --reload

Interactive API docs: http://localhost:8000/docs
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import batches, documents, reviews
from app.core.config import get_settings
from app.core.errors import AppError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


def error_body(code: str, message: str, details: list | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or []}}


def create_app() -> FastAPI:
    app = FastAPI(
        title="Supplier Document Checker",
        description="Checks supplier quotations against a Purchase Request and company rules. "
        "The LLM only extracts information; Python rules make the decision.",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, error: AppError):
        return JSONResponse(status_code=error.status_code, content=error_body(error.code, error.message, error.details))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in item["loc"]), "message": item["msg"]} for item in error.errors()]
        return JSONResponse(status_code=422, content=error_body("INVALID_REQUEST", "The request is not valid.", details))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, error: StarletteHTTPException):
        return JSONResponse(status_code=error.status_code, content=error_body("HTTP_ERROR", str(error.detail)))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception):
        # Log the full stack trace on the server, but never send it to the browser.
        logger.exception("Unexpected error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=error_body("INTERNAL_ERROR", "Something went wrong on the server."))

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(batches.router, prefix=API_PREFIX)
    app.include_router(documents.router, prefix=API_PREFIX)
    app.include_router(reviews.router, prefix=API_PREFIX)
    return app


app = create_app()
