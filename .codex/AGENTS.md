# LearningEnglish Codex Guide

## Project Identity
- Product name: `LearningEnglish`
- Product positioning: Turn printed English worksheets from live classes into digital review packs for children and guided practice flows for parents.
- Primary audiences: parents managing materials and review, children practicing listening, speaking, and lightweight exercises.
- Core promise: `拍下讲义 -> 识别内容 -> 生成复习包 -> 完成陪练与追踪`

## Working Rules
- Treat files under `docs/` as the source of truth for product, UX, and architecture.
- Treat `.stitch/DESIGN.md` as the source of truth for visual language and prompt consistency.
- Keep Chinese as the default UI language. English appears as learning content, words, sentences, and voice prompts.
- Design for both phone and tablet using one information architecture:
  - phone: single-column flows with bottom navigation
  - tablet: navigation rail or side nav with list-detail or dual-pane layouts
- Preserve terminology across docs and future code:
  - child profile
  - course material
  - material parse job
  - knowledge pack
  - review task
  - practice session
  - speaking attempt
  - report

## Tech Direction
- Mobile: Flutter, Riverpod, GoRouter, Dio, Drift
- Backend: FastAPI, Celery, Redis, PostgreSQL, object storage
- AI capabilities: OCR, LLM parsing/generation, TTS, ASR, pronunciation evaluation through provider abstractions

## Repository Intent
- `docs/design`: product and UI/UX design documents
- `docs/architecture`: system, data, mobile, and backend architecture
- `.stitch`: Stitch prompt/design assets
- `apps/mobile`: future Flutter app
- `packages/contracts`: shared API/domain contracts
- `packages/design_tokens`: future app tokens derived from design system
- `services/api`: future FastAPI service
- `services/workers`: future async job workers
- `infra`: future deployment and environment definitions

## Implementation Constraints
- Do not assume Flutter or Dart tooling is available until verified locally.
- Favor documentation-first changes when product scope or UX is evolving.
- Keep modules feature-first and boundary-aware. Avoid mixing OCR, parsing, review, and reporting concerns.
- Parent workflows must remain usable for non-technical caregivers.
- Child-facing flows must keep short instructions, large touch targets, and low text density.

## Prototype Rules
- Use Stitch prompts from `docs/design/stitch-prompts.md`.
- Generate mobile-first screens before tablet variants.
- For tablet variants, preserve the same page purpose and content model while changing layout density and navigation placement.
- Save Stitch project metadata and screen manifests under `.stitch/designs/`.

## Definition of Done For This Phase
- Documentation is complete and internally consistent.
- Stitch project exists with mobile screens and tablet variants covering the end-to-end flow.
- Local repo contains enough architecture and design guidance for a later implementation pass without re-deciding product structure.
