from fastapi import FastAPI

from app.api.router import api_router


app = FastAPI(
    title="LearningEnglish API",
    version="0.1.0",
    description="Parent-led English review vertical slice with stub OCR and parsing.",
)

app.include_router(api_router)


@app.get("/healthz", tags=["health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
