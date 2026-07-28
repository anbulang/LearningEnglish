# LearningEnglish 项目状态与 ToDo（2026-07-19）

> 本文是当前项目级状态快照与 backlog 真相源。
> 判断依据以当前代码、测试目录、`Makefile`、`README.md`、`docs/harness/*`、`docs/architecture/*`、`services/api/README.md`、`services/workers/README.md`、`apps/mobile/README.md`、`apps/admin/README.md` 为准；历史 spec / plan 继续保留在 `docs/superpowers/*`，但不作为当前状态结论。

## 一句话判断

**截至 2026-07-19，项目已经具备“家长端主链 + admin 运维原型 + phonics 课程 MVP + Harness 回归入口 + 公网部署脚手架”，但仍未跨过“真实家庭拿真实设备直接稳定使用”的交付线，当前不能把仓库描述为已完成可交付 MVP。**

## 当前阶段判断

从整个项目看，LearningEnglish 现在处于：

**“主链、拼读课程、运维骨架和交付脚手架已成型，正在从工程可运行收口到真实家庭可交付。”**

这意味着：

- 已经不是只有上传识别 demo，也不再只是上传/校对/复习/报告单链路。
- 当前主问题不再是“有没有这些接口和页面”，而是“公网交付、真实身份、真机/provider 复验、家长试用闭环是否成立”。
- `phonics` 已进入当前仓库能力边界，但还没有升级成独立交付结论或真实家长试用结论。

## 当前已完成到什么程度

### 1. 家长端主链已经落到当前代码边界

- API、worker、mobile 都围绕同一条主链组织：`ParentAccount -> ChildProfile -> CourseMaterial -> MaterialParseJob -> KnowledgePack -> ReviewTask -> PracticeSession -> WeeklyReport`。
- `services/api/app/api/parent/*` 已覆盖登录、孩子档案、讲义、AI 校对、课程详情、复习、口语与报告。
- `services/workers/workers_app/tasks.py` 已覆盖讲义处理、学习资产媒体补齐、口语评分等异步任务。
- `apps/mobile` 已具备登录、资料库、上传、AI 校对、课程详情、复习、口语、报告主页面和相应状态流转。

### 2. 拼读课程 MVP 已进入当前仓库能力边界

- 新增 `phonics` 课程数据、迁移、种子、API、worker 任务和端上页面，不再只是设计稿或 mock 概念。
- `services/api/alembic/versions/20260716_0009_add_phonics.py` 已引入 `phonics_units`、`phonics_sound_cards`、`child_phonics_progress`、`phonics_attempts`。
- `services/api/app/api/parent/phonics.py` 已提供 `units`、`progress`、`attempts`、`attempts/audio` 等家长端接口。
- `services/api/tests/test_phonics_mvp.py`、`apps/mobile/test/phonics/` 说明这条链路已经进入当前自动化测试范围。

### 3. provider / readiness / 部署治理已进入当前默认路径

- 默认 AI 路径仍是 `AI_PROVIDER=qwen`。
- 默认媒体路径仍是 `MEDIA_PROVIDER=real` + `MEDIA_IMAGE_PROVIDER=dashscope` + `MEDIA_TTS_PROVIDER=dashscope`。
- 默认 speaking 路径仍是 `SPEECH_PROVIDER=dashscope` + `SPEECH_ASSESSMENT_PROVIDER=dashscope`。
- `services/api/app/core/readiness.py` 与 `/readyz` 已把关键 provider/runtime 缺配置前移到启动期和健康检查层。
- `Makefile` 已提供 `deploy-prod-up/-down/-logs`，`docs/harness/public-deploy-runbook.md` 已给出最小公网交付脚手架。

### 4. admin 已进入“可消费真实合同”的运维原型阶段

- `apps/admin` 已覆盖 `Command Center`、`Tenant Detail`、`Users & Children`、`Content Pipeline`、`Learning Assets`、`Provider Ops`、`Infrastructure`、`Audit & Access` 等 live/read 路径。
- `services/api/README.md` 记录的 `/v1/admin/*` read endpoints 和首批受控 mutation 已与前端页面对应。
- 当前 admin 仍是受控运维控制台原型，不应写成完整生产后台。

### 5. Harness 文档与证据入口已经收敛

- `README.md`、`docs/harness/README.md`、`docs/project/README.md` 已形成项目入口、验收入口和项目状态入口三层结构。
- `docs/harness/*` 已覆盖主链、provider、真机回归、家长试用、部署与 evidence 归档五类入口。
- `make harness-evidence-index` 仍是统一证据索引入口。

## 当前仍卡在哪里

### P0 级现实阻塞

#### 1. 公网交付链还没有形成“当前环境已复验”的完成态

- 虽然 `deploy-prod-*` 和公网部署 runbook 已存在，但当前仓库没有新的同日证据说明生产或试点环境已经按该脚手架复验通过。
- speaking 真实评分仍依赖公网可拉取录音 URL；没有稳定的 `PUBLIC_BASE_URL` / `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL`，就不能把真实家庭交付写成 ready。
- 当前文档应表述为“已具备最小公网交付脚手架”，而不是“公网交付已完成”。

#### 2. 真实身份体系没有落地

- 当前登录代码仍以开发/试点身份路径为主。
- 真实 WeChat OAuth、真实短信 OTP、真实账号运营边界尚未落地，因此不能写成“真实家庭已可自助注册使用”。

#### 3. 真机与真实 provider 结论仍受环境影响

- HN-017 / HN-019 / HN-020 都已有 runbook 和历史 evidence，但当前文档不能把历史 evidence 直接表述成今天已复验。
- Android 构建环境、iOS 分发策略、公网 `/uploads`、provider key、代理环境，仍决定这条链路能否真实跑通。

### P1 级产品与运营缺口

#### 1. HN-020 家长试用还没有形成真实闭环

- 家长试用模板、preflight、validate 都已具备。
- 但缺一轮基于当前环境的真实家长或非技术试用者 evidence，无法把体验问题压缩成明确批次。

#### 2. phonics 课程还缺“真实孩子可用”的项目级验收

- 当前 `phonics` 已具备课程内容、进度、点按练习、音频上传与评分链路。
- 但还没有进入 `HN-020` 风格的人类试用闭环，也没有当前环境的专项 harness/readiness 结论。
- 因此当前更准确的表述是“功能已进入仓库能力边界”，不是“已形成独立交付能力”。

#### 3. 报告页与“可追踪”价值还需要继续打磨

- 当前报告页已经独立存在，也能返回学习资产掌握度、复习表现、口语表现和推荐动作。
- 但是否足以回答“这周学了什么、哪里薄弱、下次该练什么”，还需要真实家长反馈确认。

## 当前项目进度总结

### 已完成

- 家长端主链的代码骨架已经成型：登录、建档、上传、AI 校对、课程详情、复习、口语、报告都能在当前仓库中找到对应实现。
- `phonics` 课程已经进入 API、worker、mobile 与测试，不再只是概念或未来计划。
- API、worker、mobile、admin 四条工程线都已经有独立 README、测试入口和 `make` 命令。
- provider readiness、真机回归、家长试用、部署脚手架、evidence 归档都有固定入口，不再是散落脚本或口头流程。

### 进行中

- iOS 内部分发、provider readiness、真机回归、家长试用都已有 runbook 和历史 evidence，但还缺一轮基于当前环境的重新执行。
- 公网部署脚手架已经在仓库里，但仍缺当前环境的最新落地证据。
- `phonics` 课程已进入代码和测试，但还缺面向真实孩子/家长的试用结论。

### 未完成

- 真实身份体系、真实交付路径、跨设备分发策略、家长长期留存体验还没有到可以直接对外承诺的程度。
- Android 是否进入当前内测交付范围仍没有最终项目级结论。

## 项目级 ToDo List

下面只保留当前还值得推进的工作，按 `P0 / P1 / P2` 排序；每项都尽量拆成可以直接执行或验收的子任务。

### P0：先补齐真实家庭可用的交付临界点

#### P0-1 公网部署与对象访问闭环

- 选定当前试点环境是否真的采用 `docs/harness/public-deploy-runbook.md` 的单机交付形态。
- 固定 `PUBLIC_BASE_URL`、对象存储暴露方式、HTTPS 和上传文件公网访问方式。
- 为 speaking 固定 `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL`，确保 DashScope 可公网拉取录音。
- 用真实公网地址重新跑一次 `/readyz`、媒体 provider smoke、speaking smoke，并把结果归档到 `dist/harness/`。
- 产出一份最小交付记录：域名、部署机器、对象访问方式、证据目录、当前 blocker。

#### P0-2 真实身份与账户边界

- 明确 MVP 第一阶段到底采用真实短信、真实微信，还是受控白名单试点账号。
- 为登录、绑定、切换、退出分别写清 happy path / failure path。
- 把“第二个家庭登录后看不到第一个家庭数据”提升为明确 harness 验收项。
- 增加一条最小验收脚本或 checklist，确保每次环境切换后都能重做账户隔离检查。

#### P0-3 iOS/Android 分发口径收口

- iOS 当前默认仍走 development / UDID；需要明确这是否只作为短期试点口径，还是要恢复 TestFlight。
- Android 至少要形成一个明确结论：当前承诺交付、暂不承诺交付，或后置到下一阶段。
- 把“拿到包 -> 指向正确服务 -> 开始 HN-019/HN-020”压缩成最短操作卡。
- 为 iOS 和 Android 分别写明当前状态、前置条件、阻塞项和推荐下一步，避免“历史上做过一次”继续被误读成当前可交付。

#### P0-4 真机与真实 provider 复验

- 先做环境 preflight，再做 provider smoke，再做真机/试用，避免把环境问题误记成产品缺陷。
- 用当前环境重新跑一轮 HN-017 / HN-019 / HN-020。
- 所有 summary JSON 统一写明日期、设备、provider 模式、API base URL、最终判定和 blocker。
- 每轮完成后立即更新 `dist/harness/evidence-index.json`。
- 把 `partial / blocked / failed / passed` 的使用口径固定到各 HN summary，减少新旧字段混用。

### P1：让试用不只是能跑，而是值得继续用

#### P1-1 HN-020 家长试用闭环

- 真实找一位非开发试用者按 `docs/harness/non-technical-pilot-guide.md` 跑一轮。
- 依据 `docs/harness/hn020-parent-pilot-acceptance.md` 记录 `P0/P1/P2` 问题和 Batch 0-4 修复批次。
- 把试用问题回写到项目 backlog，而不是留在截图或聊天里。
- 试用结束后补一份简短结论：哪些问题属于交付阻塞，哪些只是体验优化。

#### P1-2 phonics 课程专项验收

- 为 `phonics` 补一份当前阶段的验收口径：最小命令、最小人工路径、证据目录和 blocker 定义。
- 至少跑一轮“课程列表 -> 进入单元 -> 点按练习 -> 录音上传 -> 进度回写”的当前环境验收。
- 明确 `phonics` 和主链报告页、学习资产、家长试用之间的项目关系，避免它长期停留在“功能存在但治理缺席”的状态。
- 补齐一份项目级判断：`phonics` 是主链增强项、试点卖点，还是单独验收子项目；后续 backlog 应据此排序。

#### P1-3 报告页与学习价值表达

- 审核当前周报是否足够回答“这周学了什么、哪里薄弱、下次练什么”。
- 如果需要趋势、掌握度或推荐动作增强，先明确数据来源和计算口径，再改 UI。
- 把报告页问题拆成“数据口径问题”和“信息呈现问题”，避免 UI 修改掩盖指标定义不清。

### P2：继续给文档与证据减重

#### P2-1 入口文档继续压缩

- `README.md`、`docs/project/README.md`、`docs/harness/README.md` 只回答“现在是什么、从哪里开始、下一步做什么”。
- 历史 spec / plan 继续保留在 `docs/superpowers/*`，但不再承担状态判断职责。
- 后续新增 runbook 或总结文档时，先决定它属于“当前真相源”还是“历史背景”，避免再次堆出第二套入口。

#### P2-2 evidence 命名与索引统一

- 统一 `dist/harness/HN-*` summary 字段风格。
- 新证据进入目录后固定执行 `make harness-evidence-index`。
- 让非开发同学也能区分“最终结论”“日志”“截图”三类文件。
- 逐步把目录内仅用于历史说明、已不再参与当前判断的文件移出默认入口描述。

## 建议执行顺序

1. 先做 `P0-1`、`P0-2`、`P0-3` 的交付与环境决策。
2. 随后执行 `P0-4`，拿到最新一轮真实复验证据。
3. 再推进 `P1-1` 家长试用闭环，把真实体验问题收敛成批次。
4. 补上 `P1-2` 的 phonics 专项验收，避免新增能力长期脱离项目治理。
5. 最后继续做 `P1-3` 与 `P2` 的治理压缩。

## 本轮文档治理结论

- `docs/project/` 只保留这一份 `2026-07-19` 当前状态快照；旧 snapshot 应从入口中移除。
- `docs/harness/` 保留当前可复查的入口与 runbook，不再把历史运行过程写成当前结论。
- `docs/superpowers/*` 保留为历史设计/计划，不作为当前项目阶段判断的第一入口。
