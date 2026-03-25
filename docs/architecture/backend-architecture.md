# Backend Architecture

## Stack
- FastAPI for REST API
- Celery for asynchronous jobs
- Redis for queueing, cache, and short-lived coordination
- PostgreSQL for structured business data
- Object storage for images, PDFs, audio, and exports

## Service Shape
The first release uses a modular monolith with clean domain boundaries.

### API domains
- `identity`: parent accounts, child profiles, active child context
- `materials`: uploads, metadata, OCR status, source asset retrieval
- `knowledge`: parsed vocabulary, sentences, dialogues, topic summaries
- `review`: review pack generation, task scheduling, completion tracking
- `speaking`: TTS prompts, ASR transcripts, pronunciation feedback
- `reporting`: progress summaries, weak points, weekly report generation

### Worker jobs
- image enhancement and PDF assembly
- OCR extraction
- worksheet parsing and structuring
- review task generation
- TTS asset generation
- ASR and pronunciation scoring
- report aggregation

## API Surface
### Primary resources
- `GET/POST /v1/children`
- `GET/POST /v1/materials`
- `GET /v1/material-jobs/{job_id}`
- `GET /v1/knowledge-packs/{material_id}`
- `GET/POST /v1/review-tasks`
- `GET/POST /v1/practice-sessions`
- `GET/POST /v1/speaking-attempts`
- `GET /v1/reports/weekly`

### State machines
#### Material parse job
`uploaded -> processing -> needs_review -> ready -> archived`

#### Speaking attempt
`queued -> recording_uploaded -> transcribing -> scored -> failed`

## Provider Abstraction
All external AI capabilities must sit behind provider interfaces:
- `OCRProvider`
- `LanguageParsingProvider`
- `SpeechSynthesisProvider`
- `SpeechRecognitionProvider`
- `PronunciationScoringProvider`

This keeps vendor changes isolated from API and worker orchestration code.

## Storage Rules
- Raw assets never go into PostgreSQL.
- PostgreSQL stores metadata, foreign keys, task state, and learning records.
- Object storage keeps source images, normalized PDFs, generated audio, and voice attempt files.

## Operational Defaults
- API handles fast synchronous reads/writes only.
- Jobs that can take longer than a request cycle always go to workers.
- Reports are precomputed or cached where possible to keep parent dashboards responsive.
