# Harness Evidence 归档策略

更新时间：2026-05-31

## 目的

`dist/harness/` 保存本地验收证据。它不是源码真相源，也默认不提交 git；它的作用是支撑复查、排障、交接和 PR 说明。

## 目录规则

- 每个需求或主题使用 `dist/harness/HN-XXX/`。
- 每个目录优先保留一个 `summary.json` 或等价摘要文件。
- 多次复跑可以覆盖稳定文件名，也可以放进带时间戳的子目录。
- 无论采用哪种方式，summary 都必须说明 `run_id`、`started_at`、`device`、`result` 和关键文件路径。

当前已存在的主要目录包括：

- `dist/harness/HN-003/`
- `dist/harness/HN-006/`
- `dist/harness/HN-012/`
- `dist/harness/HN-014/`
- `dist/harness/HN-015/`
- `dist/harness/HN-016A/`
- `dist/harness/HN-017/`
- `dist/harness/HN-018/`
- `dist/harness/screens/`

## 必须保留的证据类型

| 类型 | 示例 | 要求 |
| --- | --- | --- |
| summary | `summary.json`、`real-device-speaking-summary.json` | JSON 可格式化，说明命令、环境、结果和关键文件 |
| API log | `*-api.log` | 脱敏，保留关键 route、状态码和时间顺序 |
| worker log | `*-worker.log` | 脱敏，保留 job/attempt 状态变化 |
| screenshot | `*.png`、`*.jpg` | 展示用户可见状态，失败截图要能对齐 summary |
| provider output | `*.json`、`*.mp3`、`*.wav`、`*.png` | 不提交 git，由 summary 引用相对路径 |

## 脱敏要求

证据中不得保留以下内容的明文：

- `DASHSCOPE_API_KEY`
- `OPENAI_API_KEY`
- `ARK_API_KEY`
- `Authorization` header
- 签名 URL 的完整 query string
- 真实手机号、真实姓名和长期有效 token

如果日志必须保留 header 或 URL 结构，只保留字段名或主机名，删除敏感值。

## 替代与删除

- 不要直接删除仍可能用于复查的旧证据。
- 需要替代时，在新的 summary 中写明旧证据路径和替代原因。
- 大文件清理属于显式批准动作，必须先确认精确路径和保留范围。

## 索引要求

每次补充、替换或整理 `dist/harness/` 证据后，执行：

```bash
cd /Users/chaucermini/Code/LearningEnglish
make harness-evidence-index
python3 -m json.tool dist/harness/evidence-index.json >/tmp/learningenglish-evidence-index-check.json
```

索引只记录文件系统元数据和目录结构，不读取证据内容，也不写入敏感正文。

## 与文档真相源的关系

- `README.md`、`docs/harness/*`、`docs/architecture/*`、服务 README 和 `Makefile` 才是当前工程真相源。
- `dist/harness/` 证明“这条链路跑过或失败过”，不自动等于“当前代码仍然正确”。
- 如果文档结论与新证据冲突，应优先更新当前真相源，再补 summary 说明证据变化。
