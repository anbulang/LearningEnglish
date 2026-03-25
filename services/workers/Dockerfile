FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY workers_app ./workers_app
RUN pip install --no-cache-dir uv && uv pip install --system .

CMD ["celery", "-A", "workers_app.celery_app.celery_app", "worker", "--loglevel=info"]
