import logging
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.db import init_db
from app.core.readiness import readiness_problem_summary, readiness_report
from app.core.settings import ensure_local_paths, get_settings
from app.db.models import StoredAssetModel
from app.services.shared.storage import get_storage_service


logger = logging.getLogger("learning_english.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    ensure_local_paths(settings)
    init_db()
    report = readiness_report(settings)
    if not report["ready"]:
        summary = readiness_problem_summary(report)
        if settings.app_env.strip().lower() == "production":
            raise RuntimeError(f"Provider/runtime configuration not ready for production: {summary}")
        logger.warning("Provider/runtime configuration not ready (app_env=%s): %s", settings.app_env, summary)
    yield


app = FastAPI(
    title="LearningEnglish API",
    version="0.2.0",
    description="Parent-led English review MVP with auth, persistence, multipart upload, and provider-backed parsing.",
    lifespan=lifespan,
)

settings = get_settings()
ensure_local_paths(settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.admin_cors_origins),
    allow_origin_regex=settings.admin_cors_origin_regex or None,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Token", "X-Request-ID"],
)
if settings.storage_backend == "s3":
    @app.get("/uploads/{object_key:path}", include_in_schema=False)
    def uploaded_asset(object_key: str) -> FileResponse:
        asset = StoredAssetModel(
            owner_type="material",
            owner_id="",
            bucket=settings.storage_bucket,
            object_key=object_key,
            content_type="application/octet-stream",
            size_bytes=0,
            url="",
        )
        return FileResponse(get_storage_service().resolve_local_path(asset))
else:
    app.mount("/uploads", StaticFiles(directory=settings.local_storage_path), name="uploads")
mock_media_root = Path(__file__).resolve().parent / "static" / "mock_media"
app.mount("/mock-media", StaticFiles(directory=mock_media_root), name="mock-media")
app.include_router(api_router)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("x-request-id", f"req_{uuid4().hex[:8]}")
    request.state.request_id = request_id
    started = perf_counter()
    response = await call_next(request)
    elapsed_ms = (perf_counter() - started) * 1000
    response.headers["x-request-id"] = request_id
    logger.info(
        "%s %s -> %s in %.1fms [%s]",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        request_id,
    )
    return response


@app.get("/healthz", tags=["health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
def readiness() -> JSONResponse:
    report = readiness_report(get_settings())
    return JSONResponse(status_code=200 if report["ready"] else 503, content=report)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(item) for item in first_error.get("loc", [])[1:])
    message = first_error.get("msg", "Request validation failed")
    detail = f"{location}: {message}" if location else message
    return JSONResponse(status_code=422, content={"detail": detail})
