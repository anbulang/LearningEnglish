# LearningEnglish Contracts

这个包保存 Flutter 侧共享契约，并与 `services/api/app/models/contracts.py` 保持对齐。

## 当前契约范围

- `ChildProfile`
- `ParentAccount`
- `CourseMaterial`
- `MaterialImageRecord`
- `MaterialParseJob`
- `LearningAsset`
- `KnowledgePack`
- `VocabularyItem`
- `SentencePattern`
- `ReviewTask`
- `PracticeSession`
- `SpeakingAttempt`
- `WeeklyReport`

## 参考文档

- [data-models.md](/Users/chaucermini/Code/LearningEnglish/docs/architecture/data-models.md)
- [backend-architecture.md](/Users/chaucermini/Code/LearningEnglish/docs/architecture/backend-architecture.md)

## 说明

- JSON 序列化当前是手写维护，不依赖代码生成。
- 契约已经覆盖 `image_records`、`learning_assets`、媒体状态和主发音切换等当前 MVP 能力。
- 后端对应模型位于 [contracts.py](/Users/chaucermini/Code/LearningEnglish/services/api/app/models/contracts.py)。
