"""FastAPI application entry point — routes, middleware, and exception handlers."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from configs.router import router as configs_router
from generate.router import router as generate_router
from ubidots.router import router as ubidots_router
from shared.exception_handlers import setup_exception_handlers
from shared.middleware import LoggingMiddleware
from shared.settings import settings

app = FastAPI(
    title="Report Generated API",
    description="API for building and generating IoT data reports from Ubidots.",
    version="1.0.0",
    root_path=f"/{settings.environment}",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

app.include_router(configs_router)
app.include_router(generate_router)
app.include_router(ubidots_router)

setup_exception_handlers(app)


@app.get("/health", summary="Health Check")
async def health_check() -> dict[str, str]:
    """System health endpoint."""
    return {"status": "healthy", "environment": settings.environment}
