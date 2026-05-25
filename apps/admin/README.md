# LearningEnglish Admin

LearningEnglish Admin 是 Phase 1 的 production-shaped 多租户后台原型，用于验证后台信息架构、页面密度、租户范围、双语 UI 和高风险操作模式。

## Scope

- 仅使用 typed mock data。
- 无真实 admin auth。
- 无真实 admin API。
- 无 production mutation。
- 验证 `Platform -> Tenant -> ParentAccount -> ChildProfile -> CourseMaterial -> MaterialParseJob -> LearningAsset -> ReviewTask / PracticeSession / SpeakingAttempt -> WeeklyReport` 的后台运营视角。
- 支持 Chinese / English UI switching。
- API paths、env keys、model names、task names、permission keys 保持 English。

## Commands

```bash
make admin-install
make admin-dev
make admin-test
make admin-build
```

## Implemented Pages

- Command Center
- Tenant Detail
- Content Pipeline

## Target-State Placeholder Pages

- Users & Children
- Learning Assets
- Learning Outcomes
- Provider Ops
- Infrastructure
- Audit & Access
- Developer API

这些页面在 Phase 1 只保留导航入口和租户范围上下文，后续需要接入真实 admin read API、admin auth、权限模型、审计链路和受控 mutation 后才能作为生产后台能力使用。
