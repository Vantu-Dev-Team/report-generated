"""Logging middleware — correlation ID and request timing."""

import time
import uuid

from aws_lambda_powertools import Logger
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = Logger(service="report-generated")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log every request/response with correlation ID and duration."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4())[:8])
        logger.append_keys(
            correlation_id=correlation_id, method=request.method, path=request.url.path
        )
        logger.info("Request started")
        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000)
        logger.append_keys(status_code=response.status_code, duration_ms=duration_ms)
        logger.info("Request completed")
        logger.remove_keys(["correlation_id", "method", "path", "status_code", "duration_ms"])
        response.headers["x-correlation-id"] = correlation_id
        return response
