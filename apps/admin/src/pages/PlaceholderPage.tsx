import type { Language } from "../domain/types";

export function PlaceholderPage({ language, title }: { language: Language; title: string }) {
  const eyebrow = language === "zh" ? "目标态模块" : "Target-state module";
  const detail =
    language === "zh"
      ? "Phase 1 只实现导航入口和租户范围上下文；该页面将在后续 admin read API 或目标态页面任务中展开。"
      : "Phase 1 only implements the navigation entry and tenant scope context; this page will be expanded with later admin read APIs or target-state page work.";

  return (
    <section className="surface empty-phase">
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      <p>{detail}</p>
    </section>
  );
}
