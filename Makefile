PYTHON ?= python3
FLUTTER ?= flutter
IOS_SCHEME ?= Runner
IOS_WORKSPACE ?= apps/mobile/ios/Runner.xcworkspace
IOS_CONFIGURATION ?= Profile
IOS_FLUTTER_MODE ?= profile
IOS_ARCHIVE_PATH ?= /Users/chaucermini/Code/LearningEnglish/dist/ios/LearningEnglish-Internal.xcarchive
IOS_EXPORT_PATH ?= /Users/chaucermini/Code/LearningEnglish/dist/ios/export
IOS_EXPORT_OPTIONS ?= /Users/chaucermini/Code/LearningEnglish/apps/mobile/ios/ExportOptions.internal.plist
# Real-device builds must override this with the current LAN host IP.
IOS_API_BASE_URL ?= http://127.0.0.1:8000/v1
IOS_PREFLIGHT_URL ?= $(subst /v1,,$(IOS_API_BASE_URL))/healthz
IOS_DEVELOPMENT_TEAM ?= 95RDXKW54K
API_DATABASE_URL ?= postgresql+psycopg://learning_english:learning_english@127.0.0.1:5432/learning_english
ADMIN_API_BASE_URL ?= http://127.0.0.1:8000
ADMIN_API_TOKEN ?= local-admin-token

.PHONY: api-install api-dev api-test api-migrate worker-install worker-dev worker-test admin-install admin-dev admin-dev-live admin-test admin-build infra-up infra-down infra-reset mobile-bootstrap mobile-test mobile-analyze mobile-apk mobile-ios-prep mobile-ios-archive mobile-ios-ipa harness-main-chain-smoke harness-mvp-readiness harness-doubao-smoke harness-hn019-real-device-main-chain harness-reset-ios-sim harness-capture-ios-screen harness-evidence-index

api-install:
	cd services/api && UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync --group dev

api-migrate:
	cd services/api && DATABASE_URL=$(API_DATABASE_URL) .venv/bin/alembic upgrade head

api-dev:
	cd services/api && ADMIN_API_TOKEN=$(ADMIN_API_TOKEN) .venv/bin/uvicorn app.main:app --reload

api-test:
	cd services/api && .venv/bin/pytest

worker-install:
	cd services/workers && UV_CACHE_DIR=/tmp/learning_english_uv_cache uv sync

worker-dev:
	cd services/workers && .venv/bin/celery -A workers_app.celery_app.celery_app worker --loglevel=info

worker-test:
	cd services/workers && .venv/bin/pytest

admin-install:
	cd apps/admin && npm install

admin-dev:
	cd apps/admin && npm run dev

admin-dev-live:
	cd apps/admin && VITE_ADMIN_API_BASE_URL=$(ADMIN_API_BASE_URL) VITE_ADMIN_API_TOKEN=$(ADMIN_API_TOKEN) npm run dev

admin-test:
	cd apps/admin && npm test

admin-build:
	cd apps/admin && npm run build

infra-up:
	docker compose --env-file infra/.env -f infra/docker-compose.yml up -d

infra-down:
	docker compose --env-file infra/.env -f infra/docker-compose.yml down

infra-reset:
	docker compose --env-file infra/.env -f infra/docker-compose.yml down -v --remove-orphans

mobile-bootstrap:
	cd packages/contracts && $(FLUTTER) pub get
	cd packages/design_tokens && $(FLUTTER) pub get
	cd apps/mobile && $(FLUTTER) pub get

mobile-test:
	cd apps/mobile && $(FLUTTER) test

mobile-analyze:
	cd apps/mobile && $(FLUTTER) analyze

mobile-apk:
	cd apps/mobile && $(FLUTTER) build apk --debug

mobile-ios-prep:
	mkdir -p /Users/chaucermini/Code/LearningEnglish/dist/ios
	cd apps/mobile && $(FLUTTER) build ios --$(IOS_FLUTTER_MODE) --no-codesign --dart-define=API_BASE_URL=$(IOS_API_BASE_URL)

mobile-ios-archive: mobile-ios-prep
	mkdir -p /Users/chaucermini/Code/LearningEnglish/dist/ios
	xcodebuild \
		-workspace $(IOS_WORKSPACE) \
		-scheme $(IOS_SCHEME) \
		-configuration $(IOS_CONFIGURATION) \
		-sdk iphoneos \
		-allowProvisioningUpdates \
		-archivePath $(IOS_ARCHIVE_PATH) \
		CODE_SIGN_STYLE=Automatic \
		DEVELOPMENT_TEAM=$(IOS_DEVELOPMENT_TEAM) \
		LEARNING_ENGLISH_PREFLIGHT_URL=$(IOS_PREFLIGHT_URL) \
		archive

mobile-ios-ipa: mobile-ios-archive
	rm -rf $(IOS_EXPORT_PATH)
	mkdir -p $(IOS_EXPORT_PATH)
	xcodebuild \
		-exportArchive \
		-allowProvisioningUpdates \
		-archivePath $(IOS_ARCHIVE_PATH) \
		-exportPath $(IOS_EXPORT_PATH) \
		-exportOptionsPlist $(IOS_EXPORT_OPTIONS)

harness-main-chain-smoke:
	bash /Users/chaucermini/Code/LearningEnglish/scripts/harness/run_main_chain_smoke.sh

harness-mvp-readiness:
	bash /Users/chaucermini/Code/LearningEnglish/scripts/harness/run_mvp_readiness.sh

harness-doubao-smoke:
	bash /Users/chaucermini/Code/LearningEnglish/scripts/harness/run_doubao_smoke.sh

harness-hn019-real-device-main-chain:
	$(PYTHON) scripts/harness/run_hn019_real_device_main_chain.py

harness-reset-ios-sim:
	bash /Users/chaucermini/Code/LearningEnglish/scripts/harness/reset_ios_simulator_app.sh

harness-capture-ios-screen:
	bash /Users/chaucermini/Code/LearningEnglish/scripts/harness/capture_ios_simulator_screen.sh "$(SCREEN)"

harness-evidence-index:
	$(PYTHON) /Users/chaucermini/Code/LearningEnglish/scripts/harness/generate_evidence_index.py
