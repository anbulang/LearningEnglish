# docs/project 目录说明

这个目录当前只保留一类内容：

1. 项目运行状态文档

## 当前文件约定

### 运行状态

- `YYYY-MM-DD-status-and-todo.md`
  - 当前项目阶段
  - 里程碑状态
  - 项目级 ToDo
  - 建议执行顺序

同一时间只保留最新一份状态快照；旧版本应删除或被新版本替换，避免多个近似快照同时存在。
当前最新快照：`2026-06-08-status-and-todo.md`。

### 当前治理规则

- `docs/project/` 现在只保留当前状态快照。
- 文章草稿、素材图和复盘稿如果不再直接服务当前工程治理，应从本目录移除，避免和真相源竞争。

## 真相源优先级

如果信息冲突，按下面顺序判断：

1. 代码与测试
2. `Makefile`
3. `docs/harness/`
4. `docs/architecture/`
5. 服务 README / `apps/mobile/README.md`
6. 本目录下的状态文档
