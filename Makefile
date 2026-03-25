PYTHON ?= python3

.PHONY: api-install api-dev api-test worker-install worker-dev infra-up infra-down

api-install:
	cd services/api && UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync --group dev

api-dev:
	cd services/api && .venv/bin/uvicorn app.main:app --reload

api-test:
	cd services/api && .venv/bin/pytest

worker-install:
	cd services/workers && UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync

worker-dev:
	cd services/workers && .venv/bin/celery -A workers_app.celery_app.celery_app worker --loglevel=info

infra-up:
	docker compose -f infra/docker-compose.yml up -d

infra-down:
	docker compose -f infra/docker-compose.yml down
