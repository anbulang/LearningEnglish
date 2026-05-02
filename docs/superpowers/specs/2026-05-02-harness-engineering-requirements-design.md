# Harness Engineering Requirements Design

## Purpose

LearningEnglish will use Harness Engineering as the default development operating model after the current MVP baseline. A requirement is not considered ready for development unless it names the user outcome, the system boundary, the acceptance evidence, and the harness command or manual proof that will verify it.

The first requirement batch is the MVP delivery gap from `docs/harness/mvp-readiness-checklist.md`. This keeps the next work grounded in the current app rather than starting a disconnected product roadmap.

## Context

The current app is a parent-led English review product for early learners. The implemented MVP flow covers parent login, phone binding, child profile creation, worksheet upload, AI parsing, parent review, lesson detail, practice sessions, speaking attempts, parent coaching, and weekly reports.

The repository already contains:

- Flutter mobile app in `apps/mobile`
- FastAPI service in `services/api`
- Celery worker service in `services/workers`
- Shared contracts and design tokens in `packages`
- Local infrastructure in `infra/docker-compose.yml`
- Harness scripts in `scripts/harness`
- Readiness evidence in `docs/harness/mvp-readiness-checklist.md` and `dist/harness`

## Design Decision

Use Harness Engineering as the primary requirements structure.

Each requirement will be tracked as a small, testable unit with:

- stable requirement ID
- user or operator goal
- current state
- in-scope behavior
- out-of-scope behavior
- acceptance criteria
- automated harness command
- manual evidence requirement when automation is not enough
- completion definition
- implementation handoff notes

This avoids treating tests, screenshots, build logs, and smoke checks as afterthoughts. For this app, the harness must cover three separate surfaces:

- API and worker behavior
- mobile UI behavior
- packaging and device readiness

## Requirement Lifecycle

### 1. Candidate

A candidate requirement may come from product design, a bug, a readiness gap, provider integration work, or pilot feedback. It can be vague at this stage, but it must name the affected user or operator.

### 2. Ready

A requirement is ready only when these are true:

- The system boundary is clear.
- Acceptance criteria are written as observable behavior.
- At least one harness path is named.
- Manual evidence is defined for flows that cannot be fully automated.
- The out-of-scope section prevents adjacent work from creeping into the task.

### 3. Implemented

The code is merged only after the named harness passes or the failure is documented as an environment limitation.

### 4. Verified

The requirement is verified when evidence is saved under `dist/harness` or referenced from the requirement record. Evidence may include logs, screenshots, test output, build artifacts, or provider smoke output.

## Requirement Record Template

```markdown
### HN-000: Requirement title

**Goal:** One sentence describing the user, parent, child, tester, or operator outcome.

**Current State:** What works today and what gap remains.

**In Scope:**
- Specific behavior included in this requirement.

**Out of Scope:**
- Specific behavior intentionally excluded.

**Acceptance Criteria:**
- Observable condition that must be true.
- Observable condition that must be true.

**Harness:**
- Automated: `make <target>` or exact command.
- Manual: screenshot, install proof, provider console proof, or device proof.

**Evidence Location:**
- `dist/harness/<requirement-id>/...`

**Completion Definition:**
- What must be true before the requirement can be marked done.

**Implementation Notes:**
- Files, APIs, or tests likely involved.
```

## First Batch: MVP Readiness Requirements

### HN-001: Normalize MVP readiness harness reporting

**Goal:** Operators can run one command and understand which MVP readiness checks passed, warned, or failed.

**Current State:** `make harness-mvp-readiness` writes `dist/harness/mvp-readiness.log`, but the iOS step is labeled as `iOS Debug IPA` even though the project now exports a Profile/Internal IPA.

**In Scope:**

- Rename misleading harness step labels.
- Preserve the existing command entry point.
- Keep warning behavior for optional packaging fallbacks.
- Make the log usable as release evidence.

**Out of Scope:**

- Changing the actual iOS build mode.
- Replacing the current shell harness with a new framework.

**Acceptance Criteria:**

- `HARNESS_RESET=1 make harness-mvp-readiness` records Profile/Internal IPA wording.
- The log clearly distinguishes `PASS`, `WARN`, and `FAIL`.
- The command still stops on mandatory readiness failures.
- Optional iOS or Android packaging issues remain visible as warnings when the core MVP harness has passed.

**Harness:**

- Automated: `HARNESS_RESET=1 make harness-mvp-readiness`
- Manual: inspect `dist/harness/mvp-readiness.log`

**Evidence Location:**

- `dist/harness/mvp-readiness.log`

**Completion Definition:** The readiness log is accurate enough to attach to an internal test handoff without extra explanation.

**Implementation Notes:** Likely files are `scripts/harness/run_mvp_readiness.sh`, `Makefile`, and `docs/harness/mvp-readiness-checklist.md`.

### HN-002: Add Android debug APK fallback readiness

**Goal:** Testers have an Android fallback package when iOS provisioning is blocked or unavailable.

**Current State:** `make mobile-apk` exists, but the latest readiness checklist records failure because the local Android SDK is not configured.

**In Scope:**

- Document the Android SDK prerequisites.
- Make the harness output explain whether the failure is an environment problem or a build problem.
- Record APK output location when the build succeeds.

**Out of Scope:**

- Publishing to Google Play.
- Creating release-signed Android builds.
- Supporting multiple product flavors.

**Acceptance Criteria:**

- `make mobile-apk` either produces a debug APK or fails with a clear missing-SDK explanation.
- The readiness checklist names the exact command result and artifact path.
- Android fallback is no longer an ambiguous unchecked item.

**Harness:**

- Automated: `make mobile-apk`
- Manual: verify APK file path from Flutter output when the SDK exists

**Evidence Location:**

- `dist/harness/mvp-readiness.log`
- `apps/mobile/build/app/outputs/flutter-apk/app-debug.apk`

**Completion Definition:** A developer can tell from the evidence whether Android fallback is ready or blocked only by local SDK setup.

**Implementation Notes:** Likely files are `README.md`, `docs/harness/mvp-readiness-checklist.md`, `Makefile`, and optionally `scripts/harness/run_mvp_readiness.sh`.

### HN-003: Complete real UI evidence for the MVP main chain

**Goal:** Internal pilot reviewers can see screenshots proving the app UI supports the primary flow.

**Current State:** Login, home, upload, and report screenshots exist. Phone binding, AI review, and lesson detail screenshots are missing or stale because simulator state and reset backend state diverged.

**In Scope:**

- Define a repeatable clean-state UI capture process.
- Capture missing screenshots for phone binding, upload, AI review, lesson detail, and report.
- Keep screenshots in a stable location.

**Out of Scope:**

- Full visual regression automation.
- Pixel-perfect screenshot comparisons.
- Redesigning the relevant screens.

**Acceptance Criteria:**

- `dist/harness/screens/` contains screenshots for login, phone binding, home, upload, AI review, lesson detail, and report.
- The checklist links or names each screenshot.
- The capture process starts from a clean app session and matching backend state.

**Harness:**

- Automated: mobile widget tests in `make mobile-test`
- Manual: simulator or device screenshot capture for the named screens

**Evidence Location:**

- `dist/harness/screens/*.png`
- `docs/harness/mvp-readiness-checklist.md`

**Completion Definition:** A reviewer can inspect the evidence folder and understand the full MVP UI path without running the app.

**Implementation Notes:** Likely files are `docs/harness/mvp-readiness-checklist.md` and optional capture helper scripts under `scripts/harness`.

### HN-004: Reset mobile session state with backend state

**Goal:** Developers can reset the demo environment without getting stuck in invalid-token UI states.

**Current State:** Backend reset can invalidate mobile cached auth tokens. The readiness checklist records `Invalid access token` during a real UI upload after Docker Postgres reset.

**In Scope:**

- Define a reliable app-session reset procedure for simulator and device testing.
- Make the harness documentation explicit about when local app storage must be cleared.
- Consider a small helper command if the reset can be automated safely.

**Out of Scope:**

- Production token refresh redesign.
- Changing real authentication provider behavior.

**Acceptance Criteria:**

- A tester can run the main UI path after backend reset without token mismatch.
- The reset sequence is documented in the readiness checklist or pilot guide.
- Any helper command is conservative and does not delete unrelated developer data.

**Harness:**

- Automated: `HARNESS_RESET=1 make harness-mvp-readiness`
- Manual: clean simulator or device app state before screenshot capture

**Evidence Location:**

- `dist/harness/mvp-readiness.log`
- `dist/harness/screens/*.png`

**Completion Definition:** Backend reset and mobile UI testing are no longer contradictory steps.

**Implementation Notes:** Likely files are `docs/harness/mvp-readiness-checklist.md`, `docs/harness/non-technical-pilot-guide.md`, and optional harness helper scripts.

### HN-005: Preserve reproducible iOS internal package delivery

**Goal:** Internal testers can install and launch the iOS app from a repeatable Profile/Internal build process.

**Current State:** Profile/Internal IPA export and one real-device launch were verified. The process depends on Team `95RDXKW54K`, Bundle ID `com.anbulang.learningenglish`, provisioned device membership, and a LAN API URL.

**In Scope:**

- Keep `make mobile-ios-ipa` as the canonical local internal package command.
- Document API URL and provisioning prerequisites.
- Record install and launch commands as evidence steps.

**Out of Scope:**

- App Store or TestFlight release automation.
- Enterprise distribution.
- Automatic UDID collection.

**Acceptance Criteria:**

- `make mobile-ios-ipa` exports `dist/ios/export/learning_english_mobile.ipa`.
- The checklist records the API base URL used for the build.
- A device install and launch command is documented for local verification.

**Harness:**

- Automated: `make mobile-ios-ipa`
- Manual: `xcrun devicectl device install app ...` and `xcrun devicectl device process launch ...`

**Evidence Location:**

- `dist/ios/export/learning_english_mobile.ipa`
- `dist/harness/mvp-readiness.log`

**Completion Definition:** The internal iOS package process can be repeated by the repo owner without rediscovering signing and API URL details.

**Implementation Notes:** Likely files are `README.md`, `Makefile`, and `docs/harness/mvp-readiness-checklist.md`.

### HN-006: Separate stub provider and Doubao provider verification

**Goal:** Developers can distinguish baseline MVP correctness from real AI provider availability.

**Current State:** The MVP defaults to stub providers. Doubao text and vision smoke checks exist in `scripts/harness/smoke_doubao.py`, but provider readiness is not yet a first-class requirement record.

**In Scope:**

- Keep stub-provider MVP tests as the default readiness path.
- Define Doubao smoke as an optional provider-readiness path.
- Avoid printing secrets in logs.
- Record missing provider configuration as a clear skipped or blocked state.

**Out of Scope:**

- Adding more AI providers.
- Evaluating model quality beyond connectivity and response shape.
- Changing the mobile API contract.

**Acceptance Criteria:**

- Stub MVP readiness works without real AI credentials.
- Doubao smoke returns text and vision success when credentials and model IDs are configured.
- Missing Doubao configuration reports required variables without exposing secret values.

**Harness:**

- Automated default: `make harness-main-chain-smoke`
- Automated provider: `services/api/.venv/bin/python scripts/harness/smoke_doubao.py`

**Evidence Location:**

- `dist/harness/mvp-readiness.log`
- Future provider smoke log under `dist/harness`

**Completion Definition:** Readiness status can say whether a failure belongs to the product chain or only to external provider configuration.

**Implementation Notes:** Likely files are `README.md`, `scripts/harness/smoke_doubao.py`, `scripts/harness/run_mvp_readiness.sh`, and `docs/harness/mvp-readiness-checklist.md`.

### HN-007: Establish requirement evidence package conventions

**Goal:** Every future requirement leaves reviewable evidence in a predictable place.

**Current State:** Evidence already exists in `dist/harness`, but the naming convention is informal.

**In Scope:**

- Define a directory convention such as `dist/harness/HN-003/`.
- Define expected evidence file names for logs, screenshots, and artifacts.
- Update future specs and plans to reference these locations.

**Out of Scope:**

- Checking large binary artifacts into git.
- Creating a remote artifact store.
- Replacing existing `dist/harness/screens` immediately.

**Acceptance Criteria:**

- New requirements name their evidence directory.
- Logs and screenshots have stable names.
- The checklist can point to evidence without describing ad hoc paths.

**Harness:**

- Manual: inspect generated evidence package
- Automated: future harness scripts should write into the requirement-specific directory

**Evidence Location:**

- `dist/harness/HN-*/`

**Completion Definition:** A future agent or developer can continue work by reading the requirement record and evidence directory alone.

**Implementation Notes:** Likely files are `docs/harness/mvp-readiness-checklist.md`, future Superpowers specs, and harness scripts as they are added.

## Harness Command Taxonomy

Use these commands as the initial verification vocabulary:

- `make api-test`: FastAPI contract, auth, materials, review, report, and provider failure tests
- `make worker-test`: Celery task boundary tests
- `make mobile-test`: Flutter repository and widget tests
- `make mobile-analyze`: Flutter static analysis
- `make harness-main-chain-smoke`: API and mobile main-chain smoke
- `HARNESS_RESET=1 make harness-mvp-readiness`: full local readiness check with infrastructure reset
- `make mobile-ios-ipa`: Profile/Internal iOS package build
- `make mobile-apk`: Android debug APK fallback
- `services/api/.venv/bin/python scripts/harness/smoke_doubao.py`: real Doubao text and vision connectivity smoke

## Evidence Rules

- Logs go under `dist/harness`.
- Screenshots go under `dist/harness/screens` until a requirement-specific directory is introduced.
- Large app build artifacts stay under `dist/ios` or Flutter build output paths and are referenced from docs.
- Secrets must never be printed in logs.
- A warning is acceptable only when the requirement defines that step as optional or environment-dependent.
- A failed mandatory harness blocks completion.

## Handoff To Implementation Planning

After this design is approved, write an implementation plan for the first batch in `docs/superpowers/plans/2026-05-02-harness-engineering-mvp-readiness.md`.

The first implementation plan should prioritize:

1. HN-001, because accurate harness reporting improves all later evidence.
2. HN-004, because clean state is required for reliable screenshots.
3. HN-003, because visible UI evidence is the most important missing internal-pilot proof.
4. HN-006, because provider status must not be confused with product readiness.
5. HN-002, HN-005, and HN-007, because packaging and evidence conventions complete the delivery loop.

## Open Decisions

- Requirement evidence may remain in `dist/harness` and out of git unless the user later asks to archive selected evidence in docs.
- Android fallback remains environment-gated until Android SDK availability is confirmed on the development machine.
- TestFlight is outside this first batch and should become a separate requirement if internal distribution grows beyond provisioned devices.
