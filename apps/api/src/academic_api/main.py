import logging
from contextlib import asynccontextmanager

import uvicorn
from academic_engine.config import get_settings
from academic_engine.exceptions import AcademixError
from academic_engine.logging import configure_logging
from academic_engine.models import HealthStatus, SafeConfiguration
from academic_engine.providers import provider_metadata
from academic_engine.storage import SQLiteStore
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from academic_api.routes import router

settings = get_settings()
configure_logging(settings)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.ensure_directories()
    SQLiteStore(settings.database_path).initialize()
    logger.info("Academic Humanizer API initialized")
    yield


app = FastAPI(
    title="Academic Humanizer API",
    version="0.1.0",
    docs_url="/api/docs",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(router, prefix="/api/v1")


@app.exception_handler(AcademixError)
async def handle_application_error(_: Request, error: AcademixError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(error)})


@app.get("/api/v1/health", response_model=HealthStatus, tags=["system"])
def health() -> HealthStatus:
    return HealthStatus(status="ok", version=app.version, environment=settings.app_env)


@app.get("/api/v1/configuration", response_model=SafeConfiguration, tags=["system"])
def configuration() -> SafeConfiguration:
    return SafeConfiguration(
        environment=settings.app_env,
        api_host=settings.api_host,
        api_port=settings.api_port,
        cors_origins=settings.cors_origin_list,
        max_upload_bytes=settings.max_upload_bytes,
        configured_providers=[
            item.provider for item in provider_metadata(settings) if item.configured
        ],
    )


def run() -> None:
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
