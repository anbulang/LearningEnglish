# Mobile Architecture

## Stack
- Flutter
- Riverpod for app and feature state
- GoRouter for navigation
- Dio for HTTP networking
- Drift for local persistence and offline-friendly caches

## Layout Strategy
The app uses one semantic IA with adaptive composition.

### Breakpoints
- `<600dp`: phone layout
- `600-840dp`: compact tablet layout
- `>840dp`: full tablet layout

### Layout Rules
- Phone:
  - bottom navigation
  - single primary task per screen
  - full-screen scan, practice, and speaking flows
- Compact tablet:
  - nav bar or drawer
  - grouped dashboard cards
  - partial side panels where useful
- Full tablet:
  - navigation rail
  - master-detail or dual-pane layouts
  - persistent progress or context side panels

## Module Boundaries
- `auth`: parent auth, session, PIN-gated child mode
- `profiles`: child profiles, current child selection, goals and settings
- `materials`: upload, scan flow, OCR status, lesson library
- `lessons`: material detail, source preview, extracted knowledge
- `review`: vocabulary cards, games, practice sessions, scheduling
- `speaking`: voice prompts, recording, transcripts, speaking feedback
- `reports`: weekly report, weak points, recommended next actions

## Suggested Package Shape
```text
apps/mobile/lib/
├─ app/
│  ├─ routing/
│  ├─ shell/
│  └─ responsive/
├─ core/
│  ├─ network/
│  ├─ storage/
│  ├─ theme/
│  └─ utils/
└─ features/
   ├─ auth/
   ├─ profiles/
   ├─ materials/
   ├─ lessons/
   ├─ review/
   ├─ speaking/
   └─ reports/
```

## Data Flow
1. UI requests data from a feature controller/provider.
2. Feature provider uses repository interfaces.
3. Repositories coordinate remote API and local Drift cache.
4. UI renders one of: loading, ready, empty, error.
5. Long-running tasks use polling or push refresh around `material-jobs` and `speaking-attempts`.

## Shared Contracts
The mobile app should import generated or hand-maintained contracts from `packages/contracts` for:
- `ChildProfile`
- `CourseMaterial`
- `MaterialParseJob`
- `KnowledgePack`
- `VocabularyItem`
- `SentencePattern`
- `ReviewTask`
- `PracticeSession`
- `SpeakingAttempt`
- `WeeklyReport`

## UI Token Strategy
- Colors, spacing, radii, shadow, and typography constants should live in `packages/design_tokens`.
- Screen widgets should consume semantic tokens such as `primaryAction`, `reviewListeningSurface`, and `successAccent` instead of raw color values.

## Reliability Considerations
- Preserve partially captured uploads locally until the server confirms storage.
- Persist in-progress review sessions for accidental app close recovery.
- Keep speaking recordings resumable or retryable when upload fails.
