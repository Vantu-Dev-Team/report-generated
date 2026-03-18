"""Global exception handlers for FastAPI."""

from aws_lambda_powertools import Logger
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from shared.exceptions import DomainError

logger = Logger(service="report-generated")


def setup_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app."""

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
        errors = [
            {"field": e.get("loc", ["unknown"])[-1], "message": e.get("msg", "Validation error")}
            for e in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"error": "Validation Error", "details": errors})

    @app.exception_handler(DomainError)
    async def domain_exception_handler(request: Request, exc: DomainError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.exception(
                "Domain error: %s %s - %s: %s",
                request.method,
                request.url,
                type(exc).__name__,
                exc.message,
            )
        return JSONResponse(status_code=exc.status_code, content={"error": exc.message})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled exception: %s %s - %s: %s",
            request.method,
            request.url,
            type(exc).__name__,
            str(exc),
        )
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})
