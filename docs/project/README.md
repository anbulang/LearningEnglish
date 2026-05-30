# docs/project 目录说明

这个目录只保留两类内容：

1. 项目运行状态文档
2. 与项目相关但不直接参与运行/验收的文章草稿或配图素材

## 当前文件约定

### 运行状态

- `YYYY-MM-DD-status-and-todo.md`
  - 当前项目阶段
  - 里程碑状态
  - 项目级 ToDo
  - 建议执行顺序

同一时间只保留最新一份状态快照；旧版本应删除或被新版本替换，避免多个近似快照同时存在。
当前最新快照：`2026-05-27-status-and-todo.md`。

### 内容草稿与素材

- `article_draft_*.md`
- `article_assets_*/`

这些文件用于对外写作或项目复盘，不作为工程真相源，不应替代 `README.md`、`docs/harness/`、`docs/architecture/` 和服务 README。
如果草稿内容与当前仓库事实冲突，应以真相源为准，而不是回写真相源去迎合草稿。

## 真相源优先级

如果信息冲突，按下面顺序判断：

1. 代码与测试
2. `Makefile`
3. `docs/harness/`
4. `docs/architecture/`
5. 服务 README / `apps/mobile/README.md`
6. 本目录下的状态文档
7. 本目录下的文章草稿与素材
