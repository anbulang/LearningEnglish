FROM python:3.11-slim

WORKDIR /app

COPY services/workers/pyproject.toml ./pyproject.toml
COPY services/workers/workers_app ./workers_app
COPY services/api/app ./app
RUN pip install --no-cache-dir uv && uv pip install --system .

CMD ["celery", "-A", "workers_app.celery_app.celery_app", "worker", "--loglevel=info"]
