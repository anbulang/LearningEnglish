import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import Response

from app.api.router import api_router


logger = logging.getLogger("learning_english.api")

app = FastAPI(
    title="LearningEnglish API",
    version="0.1.0",
    description="Parent-led English review vertical slice with stub OCR and parsing.",
)

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
