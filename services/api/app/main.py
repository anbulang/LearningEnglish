import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.db import init_db
from app.core.settings import ensure_local_paths, get_settings


logger = logging.getLogger("learning_english.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    ensure_local_paths(settings)
    init_db()
    yield


app = FastAPI(
    title="LearningEnglish API",
    version="0.2.0",
    description="Parent-led English review MVP with auth, persistence, multipart upload, and provider-backed parsing.",
    lifespan=lifespan,
)

settings = get_settings()
ensure_local_paths(settings)
app.mount("/uploads", StaticFiles(directory=settings.local_storage_path), name="uploads")
app.include_router(api_router)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("x-request-id", f"req_{uuid4().hex[:8]}")
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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(item) for item in first_error.get("loc", [])[1:])
    message = first_error.get("msg", "Request validation failed")
    detail = f"{location}: {message}" if location else message
    return JSONResponse(status_code=422, content={"detail": detail})
