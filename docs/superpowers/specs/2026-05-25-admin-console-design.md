# 生产级多租户后台管理台设计

## 背景

当前 LearningEnglish 已经打通本地 MVP 主链：

`家长登录 -> 孩子档案 -> 上传讲义 -> AI 识别 -> 家长校对 -> KnowledgePack / ReviewTask / ParentCoachingScript -> 学习资产媒体 -> 复习 / 口语 / 周报`

现有后端主要是面向移动端的 `parent-scoped API`，包括 `auth`、`children`、`materials`、`material_jobs`、`knowledge`、`review_tasks`、`practice_sessions`、`speaking_attempts`、`parent_coaching` 和 `reports`。这些接口适合支撑家长端体验，但还不是生产级多租户后台。

本设计把后台定义为目标态的 `Platform Admin Console`：用于管理多个学校、机构、试点组织或客户空间，追踪跨租户内容生产质量、AI provider 状态、学习结果、管理员权限和审计安全。

## 设计目标

后台要回答四类问题：

1. 哪些租户、用户、讲义或任务正在阻塞主链。
2. 每份讲义卡在内容生产生命周期的哪一步。
3. AI / media provider、队列、存储和数据库是否影响了租户体验。
4. 谁在什么时候对哪个租户或资源做了什么高风险操作。

后台的核心对象层级是：

```text
Platform
-> Tenant
-> ParentAccount
-> ChildProfile
-> CourseMaterial
-> MaterialParseJob
-> KnowledgePack
-> LearningAsset
-> ReviewTask / PracticeSession / SpeakingAttempt
-> WeeklyReport
```

## 非目标

首版设计不把现有 API 伪装成完整 admin 能力。以下能力必须明确为目标态或后续后端工作：

- 不假设当前已经存在 `Tenant`、`AdminUser`、`Role`、`AuditEvent` 等生产模型。
- 不把 OpenAPI 页面当作后台首页。
- 不设计完整 CRM、计费、销售线索和财务系统。
- 不设计复杂 BI 报表平台；学习结果只覆盖当前主链需要的运营判断。
- 不把移动端的家长操作路径直接搬到后台。

## 当前事实与目标态边界

### 当前已经具备

- `ParentAccount`、`ChildProfile`、`CourseMaterial`、`MaterialParseJob`、`KnowledgePack`、`ReviewTask`、`PracticeSession`、`SpeakingAttempt`、`ParentCoachingScript`、`WeeklyReport`。
- 讲义上传后创建 `CourseMaterial` 和 `MaterialParseJob`。
- `MaterialParseJob` 支持 `queued`、`processing`、`needs_review`、`ready`、`failed`。
- `CourseMaterial` 支持 `uploaded`、`processing`、`needs_review`、`ready`、`failed`、`archived`。
- `LearningAsset` 已包含配图、US/UK TTS、主发音和媒体状态。
- Worker 已有 `materials.process_material_job`、`materials.process_learning_asset_media`、`reporting.aggregate_weekly_report`。
- Provider 已有 stub / Doubao OCR / Doubao Text / mock media / OpenAI image / OpenAI TTS 的边界。
- 本地运行依赖 FastAPI、Celery、Redis、PostgreSQL、local storage 或 MinIO/S3-compatible storage。

### 目标态必须新增

- `Tenant`：学校、机构、试点组织或客户空间。
- `TenantMembership`：家长、孩子、内容和配置的租户归属。
- `AdminUser`：后台管理员账号。
- `Role` / `Permission`：平台级与租户级权限。
- `AuditEvent`：所有高风险和管理操作的不可变审计记录。
- `TenantProviderPolicy`：租户级 AI / media provider 策略。
- `QuotaUsage`：租户配额、用量和超限状态。
- `ProviderIncident`：provider 事件、降级、影响租户和处理记录。
- `PipelineEvent`：内容生产生命周期事件，支撑时间线和 SLA。

## 产品定位

后台是生产运营和平台管理工具，不是教学端、家长端或纯开发者工具。

目标用户：

- Platform Owner：管理全局租户、权限、provider、基础设施和审计。
- Support Admin：协助租户排查账号、讲义、任务和报告问题。
- Content QA：处理 OCR、AI 草稿、学习资产和媒体生成质量问题。
- Provider Operator：管理 AI / media provider、降级和连接测试。
- Read-only Auditor：查看审计和风险记录，不执行变更。

## 信息架构

### 1. Command Center / 指挥台

职责：跨租户运营首页，只显示需要行动的风险和入口。

核心模块：

- 全局范围选择：`All tenants` / 单个 tenant。
- 关键风险：阻塞 job、media failures、provider incidents、report delays、high-risk audit events。
- 待处理 inbox：按租户、问题类型、影响范围、SLA、操作入口排序。
- 主链漏斗：Upload、OCR/Parse、Parent Review、Knowledge Pack、Media/TTS、Practice/Speaking、Weekly Report。
- 租户健康排行：健康分、活跃家长、失败任务、异常趋势。
- Provider 摘要：Doubao、OpenAI Media、Redis、PostgreSQL、Celery、Storage。

首页不展示完整数据管理细节；每个问题都应能跳转到具体工作台。

### 2. Tenants / 租户管理

职责：管理学校、机构、试点组织或客户空间。

核心模块：

- 租户列表：名称、状态、套餐/阶段、区域、健康分、活跃用户、阻塞任务、配额使用。
- 租户详情：tenant id、owner contact、region、created_at、contract tier、module access。
- 配额和模块：parents、children、materials、AI jobs、media minutes、storage、speaking score、weekly reports。
- 租户级 provider policy：`AI_PROVIDER`、`MEDIA_PROVIDER`、fallback、cost guardrail、proxy trust。
- 租户级用户与孩子预览。
- 租户级 materials / jobs / learning assets / reports / audit tabs。

高风险动作：

- suspend tenant。
- enable / disable module。
- provider policy override。
- impersonate tenant user。

这些动作必须填写 reason 并写入 `AuditEvent`。

### 3. Users & Children / 用户与孩子

职责：支持后台定位家长账号、孩子档案和绑定问题。

核心模块：

- 家长账号列表：租户、手机号绑定状态、最近活跃、孩子数、支持风险。
- 孩子档案列表：年龄、level、learning_goal、active material、review status。
- 账号详情：auth sessions、phone binding、children、materials、weekly report summary。
- 支持操作：重发绑定提示、查看活动、进入 supervised impersonation。

边界：

- 不直接替家长完成学习任务。
- 不绕过手机号、租户和权限校验。
- 跨租户搜索必须显式选择 scope。

### 4. Content Pipeline / 内容流水线

职责：后台核心工作台，追踪讲义从上传到可复习的生产状态。

核心模块：

- 工作流 tabs：全部、上传、识别中、待家长校对、Knowledge Pack、媒体/TTS、可复习、失败、归档。
- 生产队列表：租户、孩子、讲义、Material 状态、Job 状态、Provider、学习资产、媒体状态、SLA、操作。
- 详情 inspector：tenant、parent、child、material id、job id、source pages、OCR confidence、draft assets、warnings。
- 生命周期时间线：uploaded、job queued、OCR parse、needs_review、confirmed、media queued、media ready、ready。
- 失败分析：OCR failed、parse failed、media config missing、queue timeout、archived race。
- 操作：retry job、re-parse、transfer to review、archive、restore if allowed。

设计原则：

- 该页面以 `CourseMaterial` 和 `MaterialParseJob` 为主对象。
- `LearningAsset` 只显示摘要和状态，详细质量管理进入学习资产页。
- 归档、重跑、跨租户操作必须进入审计。

### 5. Learning Assets / 学习资产

职责：管理从讲义中沉淀出的可复习内容和媒体质量。

核心模块：

- 学习资产列表：tenant、material、text、kind、translation、difficulty、source page、is_core。
- 媒体状态：generated image、TTS US、TTS UK、primary_accent。
- 质量状态：missing media、failed image、failed TTS、low confidence、duplicate text。
- asset inspector：原讲义裁剪、AI prompt、source_visual_description、teaching_note、provider error。
- 操作：retry image、retry TTS、switch primary accent、mark non-core、request re-generation。

边界：

- 首版可以只做查看和重试；逐项编辑学习资产属于后续内容 QA 能力。
- 真实媒体审核和人工改写需要独立设计，不塞进生产队列表。

### 6. Learning Outcomes / 学习结果

职责：查看复习、口语和周报效果，帮助平台判断租户和内容质量。

核心模块：

- `ReviewTask` 状态：pending、in_progress、completed。
- `PracticeSession`：score、weak_points、completed_at。
- `SpeakingAttempt`：queued、recording_uploaded、transcribing、scored、failed。
- `WeeklyReport`：completed_sessions、reviewed_words、speaking_attempts、weak_items、recommended_actions。
- 租户、孩子、讲义、学习资产维度的筛选。

边界：

- 当前 speaking 评分仍未生产化，UI 必须能标记 capability status。
- 周报当前是轻量聚合，目标态可以预留掌握度分析，但不能把当前能力说成完整 BI。

### 7. Provider Ops / Provider 运维

职责：跨租户管理 AI、media、降级策略和 provider 事件。

核心模块：

- Provider matrix：Doubao Vision、Doubao Text、OpenAI Media、Redis、Celery、PostgreSQL、MinIO/S3。
- 租户级 provider policy 表：AI provider、media provider、fallback、quota guardrail、error rate、incident。
- 连接测试日志：status、latency、success rate、affected tenants、safe error message。
- 队列视图：material_parse、learning_asset_media、reporting、retry。
- 控制项：global fallback、per-tenant override、proxy trust、quota protection、retry limit。

安全规则：

- provider secret 永远 mask。
- 配置变更必须填写 reason。
- 降级策略必须记录影响范围和恢复时间。

### 8. Infrastructure / 基础设施

职责：观察和诊断平台依赖，不替代专业监控系统。

核心模块：

- Celery workers：heartbeat、running、queued、failed、retry age。
- Redis：connections、latency、memory、ops/sec。
- PostgreSQL：connections、slow queries、migration status。
- Storage：uploads、generated media、mock-media、bucket reachability、object count。
- API health：`/healthz`、OpenAPI availability、error rate。

边界：

- 该页只展示 LearningEnglish 相关运行面。
- 复杂告警、日志检索和 tracing 可以跳到外部工具。

### 9. Audit & Access / 审计与权限

职责：管理后台管理员、权限、租户隔离和高风险操作追踪。

核心模块：

- role matrix：Platform Owner、Support Admin、Content QA、Provider Operator、Read-only Auditor。
- 权限域：Tenants、Users、Content、Providers、Infrastructure、Audit、Impersonation。
- supervised impersonation：租户、家长账号、reason、duration、安全提示。
- audit log：time、actor、tenant、action、resource、risk、result、trace_id。
- secret access log：谁查看了什么 secret metadata，不显示 secret value。

硬规则：

- 审计记录不可删除。
- impersonation 默认 read-only。
- destructive actions disabled during impersonation，除非单独授权。
- 所有高风险操作必须有 reason、trace_id 和 result。
- 管理员只能访问自己权限允许的 tenant scope。

### 10. Developer API / 开发者 API

职责：开发入口，不是后台主流程。

核心模块：

- OpenAPI / ReDoc 链接。
- endpoint groups：Auth、Tenants、Users、Children、Materials、Material Jobs、Learning Assets、Review、Speaking、Reports、Providers、Audit。
- admin endpoint 示例：request、response、error codes、required permission。
- smoke commands：`make api-test`、`make worker-test`、`make harness-main-chain-smoke`、`make harness-doubao-smoke`。
- trace_id 查询入口。

边界：

- Developer API 不和 Audit & Access 长期混在同一页面。
- 安全审计、权限矩阵和 impersonation 属于 `Audit & Access`。

## 双语规则

后台必须支持中文和英文切换。

硬规则：

- 顶部固定语言选择器：`中文 / English`。
- 导航、标题、说明、按钮、状态文案随语言切换。
- API path、env key、model name、task name、permission key 保持英文。
- 审计事件内部 key 保持稳定英文，展示文案本地化。
- 时间显示遵循租户 timezone，审计导出保留 ISO 8601。
- 数字、百分比、货币和日期格式根据语言和租户区域格式化。
- 错误文案分两层：用户可读的本地化说明 + 可复制的英文 error code。

示例：

| 类型 | 中文 UI | English UI | 稳定符号 |
| --- | --- | --- | --- |
| 导航 | 内容流水线 | Content Pipeline | `content_pipeline` |
| 操作 | 批量重试 | Bulk retry | `material_jobs.retry` |
| 配置 | AI Provider | AI Provider | `AI_PROVIDER` |
| 任务 | 媒体生成 | Media generation | `materials.process_learning_asset_media` |
| API | 查看讲义任务 | View material job | `GET /v1/material-jobs/{job_id}` |

## 视觉主题

后台主题名：`Warm Ops Console`。

它继承移动端主题，但降低童趣和装饰比例：

- 背景：`Warm Linen #FFF8F5`
- 分组：`Soft Sheet #FFF1E9`
- 内容面：`Paper White #FFFFFF`
- 主操作：`Coral Jam #F28C6B`
- 强强调：`Cocoa Coral #98462A`
- 成功：`Mint Leaf #9DF3DF` / `Forest Mint #006B5C`
- 警告：`Butter Yellow #FFD86A`
- 媒体/音频：`Sky Blue #BFE7FF`
- 主文本：`Ink Cocoa #251910`
- 次文本：`Dust Brown #55433D`
- 边框：`Outline Variant #DBC1B9`

后台化调整：

- 高密度页面优先表格、列表、inspector、timeline 和 matrix。
- 插画只用于空态、局部提示和品牌锚点，不占据核心操作区。
- 状态标签可以使用贴纸感，但不能影响扫描效率。
- 卡片半径控制在 8 到 12px；移动端 20px+ 的大圆角不直接迁移。
- 避免紫蓝渐变、深色主题、装饰光斑和通用 SaaS 蓝。

## 后端 API 与模型缺口

为了实现目标态后台，需要新增独立 admin API 面，不能复用当前 parent-scoped API 作为后台权限边界。

建议新增命名空间：

```text
/admin/tenants
/admin/users
/admin/children
/admin/materials
/admin/material-jobs
/admin/learning-assets
/admin/review-tasks
/admin/speaking-attempts
/admin/reports
/admin/providers
/admin/infrastructure
/admin/audit-events
/admin/access
```

关键新增模型：

```text
Tenant
TenantMembership
AdminUser
AdminSession
Role
Permission
AdminRoleAssignment
AuditEvent
TenantProviderPolicy
QuotaUsage
ProviderIncident
PipelineEvent
AdminImpersonationSession
```

关键后端要求：

- 所有 admin 查询必须显式 tenant scope。
- 所有 admin mutation 必须生成 `AuditEvent`。
- 高风险 mutation 必须接收 `reason`。
- admin API 不能返回 secret 明文。
- parent-scoped endpoint 不应自动获得跨租户权限。
- 生产后台的统计数据应来自可查询模型或物化视图，不从 JSON 字段临时拼。

## 首版范围建议

首版可以先做目标态 UI 设计和 mock 数据，但规格上要按真实模型组织。

建议首版页面：

1. `Command Center`
2. `Tenant Detail`
3. `Content Pipeline`
4. `Provider Ops`
5. `Audit & Access`
6. `Developer API`

首版可以暂不做：

- 完整 tenant 创建流程。
- 完整 billing / contract 管理。
- 学习资产人工编辑器。
- 复杂报告 BI。
- 外部监控系统集成。

## 分阶段落地

### Phase 0：目标态设计

- 完成后台信息架构。
- 完成 5 到 6 张核心页面设计图。
- 固化 `Warm Ops Console` token 和双语规则。
- 明确目标态模型与当前后端差距。

### Phase 1：Admin Shell + Mock 数据

- 实现后台 shell、导航、语言切换、租户 scope selector。
- 使用 mock 数据实现 Command Center、Tenant Detail、Content Pipeline。
- 不连接生产 mutation。
- 所有高风险按钮先走 disabled 或 confirmation mock。

### Phase 2：Admin Read API

- 新增 `Tenant`、admin auth、read-only admin endpoint。
- 接入真实 materials/jobs/assets/reports 查询。
- 支持跨租户筛选和 tenant-scoped 查询。
- 建立基础 `AuditEvent` 记录。

### Phase 3：受控 Mutation

- 支持 retry job、archive material、provider policy override、module toggle。
- 所有 mutation 必须带 permission、reason、audit、trace_id。
- 支持 supervised impersonation。

### Phase 4：生产运营强化

- provider incident、quota guardrail、SLA、pipeline event、report enrichment。
- 接入外部监控或日志系统。
- 完善安全审计和导出。

## 验收标准

设计验收：

- 任意页面都能看出当前 tenant scope。
- 任意 material/job 都能追溯到 tenant、parent、child。
- 任意高风险操作都能看到 reason、permission 和 audit 规则。
- OpenAPI 是开发入口，不是后台主页。
- 中文和英文切换规则清晰，代码符号不会被翻译。
- 页面能区分当前已实现能力与目标态能力。

实现验收：

- admin API 和 parent API 权限隔离。
- 跨租户查询必须显式 scope。
- admin mutation 全部写入 `AuditEvent`。
- secret 永远不以明文返回给前端。
- 关键表格支持筛选、分页、错误态、空态和 loading state。
- `Content Pipeline` 能按状态和 SLA 定位阻塞任务。

## 风险与决策

### 风险：目标态过大

后台目标态涉及多租户、权限、审计、运维和内容质量。实现时必须拆阶段，不能一次性做完整平台。

决策：先完成目标态设计，再按 read-only admin console 落地。

### 风险：当前 JSON-heavy 模型不利于后台检索

`learning_assets`、`image_records`、`ReviewTask.content_json` 当前大量使用 JSON。后台需要筛选、统计和审计时，可能需要拆表或增加索引/物化视图。

决策：首版 UI 可以按目标态展示；后端实现阶段再决定拆表边界。

### 风险：多租户隔离是安全边界

如果只是给现有 parent API 加筛选参数，会产生越权风险。

决策：生产后台必须有独立 admin auth、admin permission 和 tenant scope 校验。

### 风险：视觉主题影响操作效率

移动端主题偏温暖绘本，后台需要高密度扫描。

决策：保留色彩和纸张层次，减少插画比例，优先表格、inspector 和 timeline。

## 待确认问题

1. `Tenant` 是否只代表学校/机构，还是也包括个人家庭试点空间。
2. 后台管理员账号是否独立于家长账号，还是允许同一身份多角色。
3. 首版是否需要真正接入 admin auth，还是先做静态原型和 mock 数据。
4. 是否需要在后台支持内容人工编辑，还是只支持查看、重试和归档。
5. provider policy 是全局优先，还是 tenant override 优先。
