# LearningEnglish Contracts

This package contains the shared Dart-side contracts for the first vertical slice.

The current contract surface covers:
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

The package mirrors the naming and status model defined in:
- [data-models.md](/Users/chaucermini/Code/LearningEnglish/docs/architecture/data-models.md)
- [backend-architecture.md](/Users/chaucermini/Code/LearningEnglish/docs/architecture/backend-architecture.md)

## Notes
- JSON serialization is hand-maintained to keep the first scaffold simple.
- The backend uses matching Pydantic models under [contracts.py](/Users/chaucermini/Code/LearningEnglish/services/api/app/models/contracts.py).
