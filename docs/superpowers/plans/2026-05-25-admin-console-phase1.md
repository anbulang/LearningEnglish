# Admin Console Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-shaped multi-tenant admin console prototype with mock data, bilingual UI, tenant scoping, and the first three core pages.

**Architecture:** Add a new `apps/admin` React + Vite + TypeScript app. Keep Phase 1 fully client-side with typed mock data, local UI state, and no real admin API or production mutations. Implement the target admin information architecture while making target-state-only capabilities visually explicit.

**Tech Stack:** React 18, Vite, TypeScript, Vitest, Testing Library, CSS modules/plain CSS, no backend integration in Phase 1.

---

## Locked Decisions

1. `Tenant` includes both organizations and personal pilot spaces. Use `tenantType: "school" | "organization" | "pilot_family" | "internal"` so the model can represent schools, institutions, family pilots, and internal test workspaces.
2. Admin identity is separate from `ParentAccount`. Phase 1 uses a static mock `AdminUser`; future models may add `linkedParentAccountId` only for traceability, not shared login state.
3. Phase 1 does not implement real admin auth or real admin APIs. It is a mock-data UI prototype that validates navigation, language switching, tenant scope, page structure, table density, and high-risk action patterns.
4. Phase 1 does not support content editing. It supports view, filter, inspect, retry/archive confirmation mocks, and disabled high-risk controls with audit reason UI.
5. Provider policy precedence is: emergency global kill switch, tenant override, tenant tier default, global default. The UI must show both the effective policy and whether it came from global or tenant-level configuration.

## Scope

Implement these pages:

1. `Command Center`
2. `Tenant Detail`
3. `Content Pipeline`

Create shell routes for these future pages, but render a scoped placeholder in Phase 1:

- `Users & Children`
- `Learning Assets`
- `Learning Outcomes`
- `Provider Ops`
- `Infrastructure`
- `Audit & Access`
- `Developer API`

## File Structure

Create:

- `apps/admin/package.json`
  Vite app scripts and dependencies.
- `apps/admin/index.html`
  HTML entrypoint.
- `apps/admin/tsconfig.json`
  TypeScript config for app code.
- `apps/admin/tsconfig.node.json`
  TypeScript config for Vite config.
- `apps/admin/vite.config.ts`
  Vite + Vitest config.
- `apps/admin/vitest.setup.ts`
  Testing Library setup.
- `apps/admin/src/main.tsx`
  React root render.
- `apps/admin/src/App.tsx`
  App composition and route/page selection.
- `apps/admin/src/styles.css`
  Warm Ops Console tokens, layout, table, form, and responsive styles.
- `apps/admin/src/domain/types.ts`
  Target-state admin domain types.
- `apps/admin/src/domain/mockData.ts`
  Deterministic mock tenant, user, material, provider, audit, and metric data.
- `apps/admin/src/domain/selectors.ts`
  Pure functions for scope filtering, lifecycle metrics, tenant health, and provider policy precedence.
- `apps/admin/src/domain/selectors.test.ts`
  Unit tests for pure selectors.
- `apps/admin/src/i18n/messages.ts`
  Chinese and English UI strings.
- `apps/admin/src/i18n/i18n.ts`
  Typed translation helper.
- `apps/admin/src/i18n/i18n.test.ts`
  Unit tests for language fallback and code-token handling.
- `apps/admin/src/components/AppShell.tsx`
  Top bar, sidebar, tenant scope selector, language selector, and page frame.
- `apps/admin/src/components/AppShell.test.tsx`
  Tests for language switch and tenant scope visibility.
- `apps/admin/src/components/ui.tsx`
  Shared UI primitives: status chips, metric cards, table actions, tabs, inspector panel.
- `apps/admin/src/pages/CommandCenter.tsx`
  Cross-tenant risk inbox and lifecycle overview.
- `apps/admin/src/pages/CommandCenter.test.tsx`
  Tests for risk inbox and tenant scope.
- `apps/admin/src/pages/TenantDetail.tsx`
  Tenant operational profile, quotas, modules, users, and tenant pipeline summary.
- `apps/admin/src/pages/TenantDetail.test.tsx`
  Tests for selected tenant data and provider policy source.
- `apps/admin/src/pages/ContentPipeline.tsx`
  Table-first material/job lifecycle workbench with inspector.
- `apps/admin/src/pages/ContentPipeline.test.tsx`
  Tests for filters, lifecycle status, and selected material inspector.
- `apps/admin/src/pages/PlaceholderPage.tsx`
  Explicit Phase 1 placeholders for future pages.
- `apps/admin/README.md`
  Admin prototype purpose, commands, scope, and target-state caveats.

Modify:

- `Makefile`
  Add `admin-install`, `admin-dev`, `admin-test`, and `admin-build`.
- `README.md`
  Add a short admin prototype entry under repository map or common commands.

## Task 1: Scaffold Admin App

**Files:**
- Create: `apps/admin/package.json`
- Create: `apps/admin/index.html`
- Create: `apps/admin/tsconfig.json`
- Create: `apps/admin/tsconfig.node.json`
- Create: `apps/admin/vite.config.ts`
- Create: `apps/admin/vitest.setup.ts`
- Create: `apps/admin/src/main.tsx`
- Create: `apps/admin/src/App.tsx`
- Create: `apps/admin/src/styles.css`

- [ ] **Step 1: Create package manifest**

Create `apps/admin/package.json`:

```json
{
  "name": "learning-english-admin",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc -b && vite build",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.0",
    "typescript": "^5.7.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "lucide-react": "^0.468.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.1.0",
    "@testing-library/user-event": "^14.5.2",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "jsdom": "^25.0.1",
    "vitest": "^2.1.8"
  }
}
```

- [ ] **Step 2: Create HTML entrypoint**

Create `apps/admin/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>LearningEnglish Admin</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 3: Create TypeScript configs**

Create `apps/admin/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

Create `apps/admin/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Create Vite and Vitest config**

Create `apps/admin/vite.config.ts`:

```ts
/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./vitest.setup.ts"
  }
});
```

Create `apps/admin/vitest.setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 5: Create minimal React entry**

Create `apps/admin/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

Create `apps/admin/src/App.tsx`:

```tsx
export function App() {
  return (
    <main className="app-boot">
      <h1>LearningEnglish Admin</h1>
      <p>Phase 1 admin console prototype</p>
    </main>
  );
}
```

Create `apps/admin/src/styles.css`:

```css
:root {
  color: #251910;
  background: #fff8f5;
  font-family: "Plus Jakarta Sans", "Be Vietnam Pro", Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: #fff8f5;
}

button,
input,
select,
textarea {
  font: inherit;
}

.app-boot {
  min-height: 100vh;
  display: grid;
  place-content: center;
  gap: 8px;
  text-align: center;
}
```

- [ ] **Step 6: Install dependencies**

Run:

```bash
cd apps/admin && npm install
```

Expected: `package-lock.json` is created and dependencies install successfully. If network access is blocked, rerun with the required sandbox escalation instead of changing package choices.

- [ ] **Step 7: Verify scaffold**

Run:

```bash
cd apps/admin && npm run build
```

Expected: TypeScript and Vite build complete successfully and create `apps/admin/dist`.

- [ ] **Step 8: Commit scaffold**

```bash
git add apps/admin
git commit -m "feat(admin): scaffold admin console app"
```

## Task 2: Add Domain Types and Selector Tests

**Files:**
- Create: `apps/admin/src/domain/types.ts`
- Create: `apps/admin/src/domain/mockData.ts`
- Create: `apps/admin/src/domain/selectors.ts`
- Create: `apps/admin/src/domain/selectors.test.ts`

- [ ] **Step 1: Write selector tests first**

Create `apps/admin/src/domain/selectors.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { mockMaterials, mockProviderPolicies, mockTenants } from "./mockData";
import {
  getEffectiveProviderPolicy,
  getLifecycleCounts,
  getMaterialsForScope,
  getTenantHealthRows
} from "./selectors";

describe("admin domain selectors", () => {
  it("filters materials by all tenants or a selected tenant", () => {
    expect(getMaterialsForScope(mockMaterials, "all")).toHaveLength(mockMaterials.length);
    expect(getMaterialsForScope(mockMaterials, "tenant_bright_future").every((item) => item.tenantId === "tenant_bright_future")).toBe(true);
  });

  it("counts lifecycle stages from material, job, and media status", () => {
    const counts = getLifecycleCounts(mockMaterials);
    expect(counts.upload).toBeGreaterThan(0);
    expect(counts.parse).toBeGreaterThan(0);
    expect(counts.parentReview).toBeGreaterThan(0);
    expect(counts.media).toBeGreaterThan(0);
    expect(counts.ready).toBeGreaterThan(0);
    expect(counts.failed).toBeGreaterThan(0);
  });

  it("applies provider policy precedence with tenant override above global default", () => {
    const effective = getEffectiveProviderPolicy(mockProviderPolicies, "tenant_bright_future");
    expect(effective.aiProvider).toBe("doubao");
    expect(effective.mediaProvider).toBe("real");
    expect(effective.source).toBe("tenant_override");
  });

  it("sorts tenant health rows by risk before healthy tenants", () => {
    const rows = getTenantHealthRows(mockTenants, mockMaterials);
    expect(rows[0].blockedJobs).toBeGreaterThanOrEqual(rows[rows.length - 1].blockedJobs);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd apps/admin && npm test -- src/domain/selectors.test.ts
```

Expected: FAIL because `mockData.ts`, `types.ts`, and `selectors.ts` do not exist yet.

- [ ] **Step 3: Define domain types**

Create `apps/admin/src/domain/types.ts`:

```ts
export type Language = "zh" | "en";
export type TenantScope = "all" | string;

export type TenantType = "school" | "organization" | "pilot_family" | "internal";
export type TenantStatus = "active" | "warning" | "suspended";

export interface Tenant {
  id: string;
  name: string;
  tenantType: TenantType;
  status: TenantStatus;
  region: string;
  ownerContact: string;
  tier: string;
  createdAt: string;
  activeParents: number;
  children: number;
}

export type MaterialStatus = "uploaded" | "processing" | "needs_review" | "ready" | "failed" | "archived";
export type JobStatus = "queued" | "processing" | "needs_review" | "ready" | "failed";
export type MediaStatus = "pending" | "processing" | "ready" | "failed";

export interface AdminMaterial {
  id: string;
  tenantId: string;
  parentName: string;
  childName: string;
  childAge: number;
  title: string;
  pageCount: number;
  materialStatus: MaterialStatus;
  jobStatus: JobStatus;
  provider: "stub" | "doubao";
  learningAssets: number;
  mediaStatus: MediaStatus;
  slaMinutes: number;
  updatedAt: string;
  warnings: string[];
}

export interface ProviderPolicy {
  tenantId: "global" | string;
  aiProvider: "stub" | "doubao";
  mediaProvider: "mock" | "real";
  fallbackMode: "global_stub" | "auto_to_mock" | "per_tenant";
  monthlyGuardrail: number;
  source: "global_default" | "tenant_override" | "tier_default" | "emergency_global";
}

export interface TenantHealthRow {
  tenant: Tenant;
  blockedJobs: number;
  mediaFailures: number;
  healthScore: number;
}

export interface LifecycleCounts {
  upload: number;
  parse: number;
  parentReview: number;
  knowledgePack: number;
  media: number;
  ready: number;
  failed: number;
}

export interface AdminUser {
  id: string;
  name: string;
  role: "Platform Owner" | "Support Admin" | "Content QA" | "Provider Operator" | "Read-only Auditor";
}
```

- [ ] **Step 4: Add deterministic mock data**

Create `apps/admin/src/domain/mockData.ts`:

```ts
import type { AdminMaterial, AdminUser, ProviderPolicy, Tenant } from "./types";

export const mockAdminUser: AdminUser = {
  id: "admin_001",
  name: "Admin",
  role: "Platform Owner"
};

export const mockTenants: Tenant[] = [
  {
    id: "tenant_bright_future",
    name: "Bright Future School",
    tenantType: "school",
    status: "active",
    region: "Asia / Shanghai",
    ownerContact: "ops@brightfuture.edu.cn",
    tier: "Pilot Plus",
    createdAt: "2025-03-18",
    activeParents: 1248,
    children: 1735
  },
  {
    id: "tenant_maple_pilot",
    name: "Maple Pilot Group",
    tenantType: "organization",
    status: "warning",
    region: "Asia / Shanghai",
    ownerContact: "pilot@maple.example",
    tier: "Pilot",
    createdAt: "2025-09-02",
    activeParents: 318,
    children: 462
  },
  {
    id: "tenant_sunny_kids",
    name: "Sunny Kids English",
    tenantType: "school",
    status: "warning",
    region: "Asia / Singapore",
    ownerContact: "admin@sunnykids.example",
    tier: "Standard",
    createdAt: "2025-11-20",
    activeParents: 214,
    children: 331
  },
  {
    id: "tenant_little_star",
    name: "Little Star Family Pilot",
    tenantType: "pilot_family",
    status: "active",
    region: "Asia / Shanghai",
    ownerContact: "family-pilot@example.com",
    tier: "Family Pilot",
    createdAt: "2026-01-06",
    activeParents: 12,
    children: 17
  }
];

export const mockMaterials: AdminMaterial[] = [
  {
    id: "mat_014",
    tenantId: "tenant_bright_future",
    parentName: "Emily Zhang",
    childName: "Tom Zhang",
    childAge: 6,
    title: "HN-014 Phonics Worksheet",
    pageCount: 6,
    materialStatus: "ready",
    jobStatus: "processing",
    provider: "doubao",
    learningAssets: 68,
    mediaStatus: "processing",
    slaMinutes: 72,
    updatedAt: "2026-05-24 10:23",
    warnings: ["Media generation still running"]
  },
  {
    id: "mat_queen_quilt",
    tenantId: "tenant_maple_pilot",
    parentName: "Sophia Liu",
    childName: "Lucy Liu",
    childAge: 5,
    title: "Queen / Quilt Review Pack",
    pageCount: 8,
    materialStatus: "needs_review",
    jobStatus: "needs_review",
    provider: "doubao",
    learningAssets: 92,
    mediaStatus: "pending",
    slaMinutes: 225,
    updatedAt: "2026-05-24 09:41",
    warnings: ["Parent review waiting over 48h"]
  },
  {
    id: "mat_weekend",
    tenantId: "tenant_sunny_kids",
    parentName: "Grace Li",
    childName: "Leo Li",
    childAge: 7,
    title: "Weekend Reading Worksheet",
    pageCount: 4,
    materialStatus: "ready",
    jobStatus: "ready",
    provider: "stub",
    learningAssets: 52,
    mediaStatus: "ready",
    slaMinutes: 20,
    updatedAt: "2026-05-23 08:12",
    warnings: []
  },
  {
    id: "mat_animals",
    tenantId: "tenant_sunny_kids",
    parentName: "Michael Chen",
    childName: "Emma Chen",
    childAge: 6,
    title: "Animal Sounds Practice",
    pageCount: 5,
    materialStatus: "failed",
    jobStatus: "failed",
    provider: "doubao",
    learningAssets: 0,
    mediaStatus: "failed",
    slaMinutes: 182,
    updatedAt: "2026-05-22 11:02",
    warnings: ["OCR request failed", "Retry requires audit reason"]
  },
  {
    id: "mat_colors",
    tenantId: "tenant_little_star",
    parentName: "Kevin Wang",
    childName: "Mia Wang",
    childAge: 5,
    title: "Colors Mini Test",
    pageCount: 1,
    materialStatus: "archived",
    jobStatus: "ready",
    provider: "stub",
    learningAssets: 26,
    mediaStatus: "ready",
    slaMinutes: 0,
    updatedAt: "2026-05-21 18:30",
    warnings: ["Archived by parent request"]
  }
];

export const mockProviderPolicies: ProviderPolicy[] = [
  {
    tenantId: "global",
    aiProvider: "stub",
    mediaProvider: "mock",
    fallbackMode: "global_stub",
    monthlyGuardrail: 1000,
    source: "global_default"
  },
  {
    tenantId: "tenant_bright_future",
    aiProvider: "doubao",
    mediaProvider: "real",
    fallbackMode: "per_tenant",
    monthlyGuardrail: 1000,
    source: "tenant_override"
  },
  {
    tenantId: "tenant_maple_pilot",
    aiProvider: "doubao",
    mediaProvider: "mock",
    fallbackMode: "auto_to_mock",
    monthlyGuardrail: 500,
    source: "tenant_override"
  }
];
```

- [ ] **Step 5: Implement selectors**

Create `apps/admin/src/domain/selectors.ts`:

```ts
import type { AdminMaterial, LifecycleCounts, ProviderPolicy, Tenant, TenantHealthRow, TenantScope } from "./types";

export function getMaterialsForScope(materials: AdminMaterial[], scope: TenantScope): AdminMaterial[] {
  if (scope === "all") {
    return materials;
  }
  return materials.filter((material) => material.tenantId === scope);
}

export function getLifecycleCounts(materials: AdminMaterial[]): LifecycleCounts {
  return materials.reduce<LifecycleCounts>(
    (counts, material) => {
      counts.upload += 1;
      if (material.jobStatus === "queued" || material.jobStatus === "processing") {
        counts.parse += 1;
      }
      if (material.jobStatus === "needs_review" || material.materialStatus === "needs_review") {
        counts.parentReview += 1;
      }
      if (material.jobStatus === "ready" || material.materialStatus === "ready") {
        counts.knowledgePack += 1;
      }
      if (material.mediaStatus === "pending" || material.mediaStatus === "processing") {
        counts.media += 1;
      }
      if (material.materialStatus === "ready" && material.mediaStatus === "ready") {
        counts.ready += 1;
      }
      if (material.materialStatus === "failed" || material.jobStatus === "failed" || material.mediaStatus === "failed") {
        counts.failed += 1;
      }
      return counts;
    },
    { upload: 0, parse: 0, parentReview: 0, knowledgePack: 0, media: 0, ready: 0, failed: 0 }
  );
}

export function getEffectiveProviderPolicy(policies: ProviderPolicy[], tenantId: string): ProviderPolicy {
  const globalPolicy = policies.find((policy) => policy.tenantId === "global");
  const tenantPolicy = policies.find((policy) => policy.tenantId === tenantId);
  if (tenantPolicy) {
    return tenantPolicy;
  }
  if (globalPolicy) {
    return globalPolicy;
  }
  return {
    tenantId: "global",
    aiProvider: "stub",
    mediaProvider: "mock",
    fallbackMode: "global_stub",
    monthlyGuardrail: 0,
    source: "global_default"
  };
}

export function getTenantHealthRows(tenants: Tenant[], materials: AdminMaterial[]): TenantHealthRow[] {
  return tenants
    .map((tenant) => {
      const tenantMaterials = materials.filter((material) => material.tenantId === tenant.id);
      const blockedJobs = tenantMaterials.filter(
        (material) => material.materialStatus === "failed" || material.jobStatus === "failed" || material.slaMinutes > 180
      ).length;
      const mediaFailures = tenantMaterials.filter((material) => material.mediaStatus === "failed").length;
      const healthScore = Math.max(0, 100 - blockedJobs * 12 - mediaFailures * 8);
      return { tenant, blockedJobs, mediaFailures, healthScore };
    })
    .sort((a, b) => b.blockedJobs - a.blockedJobs || a.healthScore - b.healthScore);
}
```

- [ ] **Step 6: Run selector tests**

Run:

```bash
cd apps/admin && npm test -- src/domain/selectors.test.ts
```

Expected: PASS.

- [ ] **Step 7: Commit domain model**

```bash
git add apps/admin/src/domain
git commit -m "feat(admin): add mock admin domain model"
```

## Task 3: Add I18n and App Shell

**Files:**
- Create: `apps/admin/src/i18n/messages.ts`
- Create: `apps/admin/src/i18n/i18n.ts`
- Create: `apps/admin/src/i18n/i18n.test.ts`
- Create: `apps/admin/src/components/AppShell.tsx`
- Create: `apps/admin/src/components/AppShell.test.tsx`
- Modify: `apps/admin/src/App.tsx`
- Modify: `apps/admin/src/styles.css`

- [ ] **Step 1: Write i18n tests**

Create `apps/admin/src/i18n/i18n.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { createTranslator } from "./i18n";

describe("i18n", () => {
  it("translates navigation labels", () => {
    expect(createTranslator("zh")("nav.commandCenter")).toBe("指挥台");
    expect(createTranslator("en")("nav.commandCenter")).toBe("Command Center");
  });

  it("keeps code tokens outside translation", () => {
    expect(createTranslator("zh")("code.aiProvider")).toBe("AI_PROVIDER");
    expect(createTranslator("en")("code.aiProvider")).toBe("AI_PROVIDER");
  });
});
```

- [ ] **Step 2: Add translations**

Create `apps/admin/src/i18n/messages.ts`:

```ts
import type { Language } from "../domain/types";

export const messages = {
  zh: {
    "nav.commandCenter": "指挥台",
    "nav.tenants": "租户管理",
    "nav.usersChildren": "用户与孩子",
    "nav.contentPipeline": "内容流水线",
    "nav.learningAssets": "学习资产",
    "nav.learningOutcomes": "学习结果",
    "nav.providerOps": "Provider 运维",
    "nav.infrastructure": "基础设施",
    "nav.auditAccess": "审计与权限",
    "nav.developerApi": "Developer API",
    "top.allTenants": "所有租户",
    "top.production": "生产",
    "top.healthy": "健康",
    "top.openapi": "OpenAPI",
    "page.commandCenter.title": "平台指挥台",
    "page.commandCenter.subtitle": "多租户学习内容生产、AI 处理和学习结果的统一运营入口",
    "page.tenantDetail.title": "租户详情",
    "page.contentPipeline.title": "内容流水线",
    "placeholder.phase1": "Phase 1 仅保留导航入口；具体页面将在后续任务实现。",
    "code.aiProvider": "AI_PROVIDER"
  },
  en: {
    "nav.commandCenter": "Command Center",
    "nav.tenants": "Tenants",
    "nav.usersChildren": "Users & Children",
    "nav.contentPipeline": "Content Pipeline",
    "nav.learningAssets": "Learning Assets",
    "nav.learningOutcomes": "Learning Outcomes",
    "nav.providerOps": "Provider Ops",
    "nav.infrastructure": "Infrastructure",
    "nav.auditAccess": "Audit & Access",
    "nav.developerApi": "Developer API",
    "top.allTenants": "All tenants",
    "top.production": "Production",
    "top.healthy": "Healthy",
    "top.openapi": "OpenAPI",
    "page.commandCenter.title": "Platform Command Center",
    "page.commandCenter.subtitle": "Unified operations for multi-tenant content production, AI processing, and learning outcomes.",
    "page.tenantDetail.title": "Tenant Detail",
    "page.contentPipeline.title": "Content Pipeline",
    "placeholder.phase1": "Phase 1 keeps this navigation entry only; the full page will be implemented later.",
    "code.aiProvider": "AI_PROVIDER"
  }
} as const;

export type MessageKey = keyof typeof messages.zh;
```

- [ ] **Step 3: Add translator helper**

Create `apps/admin/src/i18n/i18n.ts`:

```ts
import type { Language } from "../domain/types";
import { messages, type MessageKey } from "./messages";

export function createTranslator(language: Language) {
  return function translate(key: MessageKey): string {
    return messages[language][key] ?? messages.en[key] ?? key;
  };
}
```

- [ ] **Step 4: Run i18n tests**

Run:

```bash
cd apps/admin && npm test -- src/i18n/i18n.test.ts
```

Expected: PASS.

- [ ] **Step 5: Write app shell test**

Create `apps/admin/src/components/AppShell.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "../App";

describe("AppShell", () => {
  it("shows tenant scope and switches language", async () => {
    render(<App />);
    expect(screen.getByText("所有租户")).toBeInTheDocument();
    expect(screen.getByText("指挥台")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "English" }));

    expect(screen.getByText("All tenants")).toBeInTheDocument();
    expect(screen.getByText("Command Center")).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Implement app shell**

Create `apps/admin/src/components/AppShell.tsx`:

```tsx
import { BarChart3, BookOpenCheck, Boxes, Building2, ClipboardList, Code2, Database, Home, ShieldCheck, Users } from "lucide-react";
import type { ReactNode } from "react";
import type { Language, Tenant, TenantScope } from "../domain/types";
import { createTranslator } from "../i18n/i18n";

export type PageKey =
  | "command"
  | "tenants"
  | "users"
  | "pipeline"
  | "assets"
  | "outcomes"
  | "providers"
  | "infrastructure"
  | "audit"
  | "developer";

interface AppShellProps {
  children: ReactNode;
  activePage: PageKey;
  language: Language;
  tenantScope: TenantScope;
  tenants: Tenant[];
  onLanguageChange: (language: Language) => void;
  onTenantScopeChange: (scope: TenantScope) => void;
  onPageChange: (page: PageKey) => void;
}

const navItems = [
  { key: "command", label: "nav.commandCenter", icon: Home },
  { key: "tenants", label: "nav.tenants", icon: Building2 },
  { key: "users", label: "nav.usersChildren", icon: Users },
  { key: "pipeline", label: "nav.contentPipeline", icon: ClipboardList },
  { key: "assets", label: "nav.learningAssets", icon: Boxes },
  { key: "outcomes", label: "nav.learningOutcomes", icon: BarChart3 },
  { key: "providers", label: "nav.providerOps", icon: BookOpenCheck },
  { key: "infrastructure", label: "nav.infrastructure", icon: Database },
  { key: "audit", label: "nav.auditAccess", icon: ShieldCheck },
  { key: "developer", label: "nav.developerApi", icon: Code2 }
] as const;

export function AppShell(props: AppShellProps) {
  const t = createTranslator(props.language);
  return (
    <div className="admin-shell">
      <aside className="sidebar">
        <div className="brand-mark">LE</div>
        <nav className="sidebar-nav" aria-label="Admin navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                className={props.activePage === item.key ? "nav-item active" : "nav-item"}
                onClick={() => props.onPageChange(item.key)}
              >
                <Icon size={18} />
                <span>{t(item.label)}</span>
              </button>
            );
          })}
        </nav>
      </aside>
      <div className="admin-frame">
        <header className="topbar">
          <strong>LearningEnglish Admin</strong>
          <select value={props.tenantScope} onChange={(event) => props.onTenantScopeChange(event.target.value)}>
            <option value="all">{t("top.allTenants")}</option>
            {props.tenants.map((tenant) => (
              <option key={tenant.id} value={tenant.id}>
                {tenant.name}
              </option>
            ))}
          </select>
          <span className="status-chip success">{t("top.production")}</span>
          <div className="language-toggle" aria-label="Language">
            <button className={props.language === "zh" ? "active" : ""} onClick={() => props.onLanguageChange("zh")}>
              中文
            </button>
            <button className={props.language === "en" ? "active" : ""} onClick={() => props.onLanguageChange("en")}>
              English
            </button>
          </div>
          <span className="status-chip success">{t("top.healthy")}</span>
          <button className="ghost-button">{t("top.openapi")}</button>
        </header>
        <main className="page-content">{props.children}</main>
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Wire App shell state**

Replace `apps/admin/src/App.tsx`:

```tsx
import { useMemo, useState } from "react";
import { AppShell, type PageKey } from "./components/AppShell";
import { mockMaterials, mockTenants } from "./domain/mockData";
import type { Language, TenantScope } from "./domain/types";
import { createTranslator } from "./i18n/i18n";

export function App() {
  const [language, setLanguage] = useState<Language>("zh");
  const [tenantScope, setTenantScope] = useState<TenantScope>("all");
  const [activePage, setActivePage] = useState<PageKey>("command");
  const t = createTranslator(language);
  const scopedMaterials = useMemo(
    () => (tenantScope === "all" ? mockMaterials : mockMaterials.filter((material) => material.tenantId === tenantScope)),
    [tenantScope]
  );

  return (
    <AppShell
      activePage={activePage}
      language={language}
      tenantScope={tenantScope}
      tenants={mockTenants}
      onLanguageChange={setLanguage}
      onTenantScopeChange={setTenantScope}
      onPageChange={setActivePage}
    >
      <section className="page-header">
        <p className="eyebrow">Phase 1 mock prototype</p>
        <h1>{t("page.commandCenter.title")}</h1>
        <p>{t("page.commandCenter.subtitle")}</p>
      </section>
      <section className="surface">
        <strong>{scopedMaterials.length}</strong> materials in current scope
      </section>
    </AppShell>
  );
}
```

- [ ] **Step 8: Replace base styles with shell styles**

Replace `apps/admin/src/styles.css` with:

```css
:root {
  --warm-linen: #fff8f5;
  --soft-sheet: #fff1e9;
  --paper-white: #ffffff;
  --coral-jam: #f28c6b;
  --cocoa-coral: #98462a;
  --mint-leaf: #9df3df;
  --forest-mint: #006b5c;
  --butter-yellow: #ffd86a;
  --sky-blue: #bfe7ff;
  --ink-cocoa: #251910;
  --dust-brown: #55433d;
  --outline-variant: #dbc1b9;
  color: var(--ink-cocoa);
  background: var(--warm-linen);
  font-family: "Plus Jakarta Sans", "Be Vietnam Pro", Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--warm-linen);
}

button,
input,
select,
textarea {
  font: inherit;
}

button {
  cursor: pointer;
}

.admin-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
}

.sidebar {
  border-right: 1px solid var(--outline-variant);
  background: linear-gradient(180deg, #fffaf7 0%, #fff1e9 100%);
  padding: 20px 16px;
}

.brand-mark {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: var(--paper-white);
  border: 1px solid var(--outline-variant);
  color: var(--cocoa-coral);
  font-weight: 800;
}

.sidebar-nav {
  display: grid;
  gap: 6px;
  margin-top: 28px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 0;
  border-radius: 10px;
  padding: 11px 12px;
  color: var(--ink-cocoa);
  background: transparent;
  text-align: left;
}

.nav-item.active {
  background: #ffe5da;
  color: var(--cocoa-coral);
  box-shadow: inset 3px 0 0 var(--coral-jam);
}

.admin-frame {
  min-width: 0;
}

.topbar {
  min-height: 68px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.72);
  border-bottom: 1px solid var(--outline-variant);
  backdrop-filter: blur(16px);
}

.topbar select,
.ghost-button {
  border: 1px solid var(--outline-variant);
  background: var(--paper-white);
  border-radius: 9px;
  padding: 9px 12px;
}

.language-toggle {
  display: inline-flex;
  padding: 3px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: var(--paper-white);
  margin-left: auto;
}

.language-toggle button {
  border: 0;
  border-radius: 8px;
  background: transparent;
  padding: 7px 14px;
}

.language-toggle button.active {
  color: white;
  background: var(--coral-jam);
}

.status-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 13px;
  font-weight: 700;
}

.status-chip.success {
  color: var(--forest-mint);
  background: #eafbf6;
}

.page-content {
  padding: 24px;
}

.page-header {
  display: grid;
  gap: 8px;
  margin-bottom: 18px;
}

.page-header h1,
.page-header p {
  margin: 0;
}

.eyebrow {
  color: var(--cocoa-coral);
  font-size: 13px;
  font-weight: 800;
}

.surface {
  background: var(--paper-white);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 18px;
  box-shadow: 0 14px 30px rgba(37, 25, 16, 0.06);
}
```

- [ ] **Step 9: Run app shell tests**

Run:

```bash
cd apps/admin && npm test -- src/i18n/i18n.test.ts src/components/AppShell.test.tsx
```

Expected: PASS.

- [ ] **Step 10: Commit shell and i18n**

```bash
git add apps/admin/src
git commit -m "feat(admin): add shell and bilingual navigation"
```

## Task 4: Build Command Center Page

**Files:**
- Create: `apps/admin/src/components/ui.tsx`
- Create: `apps/admin/src/pages/CommandCenter.tsx`
- Create: `apps/admin/src/pages/CommandCenter.test.tsx`
- Modify: `apps/admin/src/App.tsx`
- Modify: `apps/admin/src/styles.css`

- [ ] **Step 1: Write Command Center tests**

Create `apps/admin/src/pages/CommandCenter.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockMaterials, mockTenants } from "../domain/mockData";
import { CommandCenter } from "./CommandCenter";

describe("CommandCenter", () => {
  it("shows risk inbox and lifecycle funnel", () => {
    render(<CommandCenter language="zh" tenantScope="all" tenants={mockTenants} materials={mockMaterials} />);
    expect(screen.getByText("平台指挥台")).toBeInTheDocument();
    expect(screen.getByText("今日待处理")).toBeInTheDocument();
    expect(screen.getByText("内容生产生命周期")).toBeInTheDocument();
    expect(screen.getByText("Animal Sounds Practice")).toBeInTheDocument();
  });

  it("filters risk inbox by selected tenant", () => {
    render(<CommandCenter language="en" tenantScope="tenant_sunny_kids" tenants={mockTenants} materials={mockMaterials} />);
    expect(screen.getByText("Platform Command Center")).toBeInTheDocument();
    expect(screen.getByText("Animal Sounds Practice")).toBeInTheDocument();
    expect(screen.queryByText("Queen / Quilt Review Pack")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd apps/admin && npm test -- src/pages/CommandCenter.test.tsx
```

Expected: FAIL because `CommandCenter.tsx` and shared UI primitives do not exist.

- [ ] **Step 3: Create shared UI primitives**

Create `apps/admin/src/components/ui.tsx`:

```tsx
import type { ReactNode } from "react";

export function StatusChip({ tone, children }: { tone: "success" | "warning" | "danger" | "neutral"; children: ReactNode }) {
  return <span className={`status-chip ${tone}`}>{children}</span>;
}

export function MetricCard({ label, value, detail }: { label: string; value: ReactNode; detail: string }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

export function EmptyPhase({ title, detail }: { title: string; detail: string }) {
  return (
    <section className="surface empty-phase">
      <h2>{title}</h2>
      <p>{detail}</p>
    </section>
  );
}
```

- [ ] **Step 4: Implement Command Center**

Create `apps/admin/src/pages/CommandCenter.tsx`:

```tsx
import { MetricCard, StatusChip } from "../components/ui";
import { getLifecycleCounts, getMaterialsForScope, getTenantHealthRows } from "../domain/selectors";
import type { AdminMaterial, Language, Tenant, TenantScope } from "../domain/types";

interface CommandCenterProps {
  language: Language;
  tenantScope: TenantScope;
  tenants: Tenant[];
  materials: AdminMaterial[];
}

export function CommandCenter({ language, tenantScope, tenants, materials }: CommandCenterProps) {
  const scopedMaterials = getMaterialsForScope(materials, tenantScope);
  const counts = getLifecycleCounts(scopedMaterials);
  const tenantRows = getTenantHealthRows(tenants, materials).slice(0, 4);
  const riskRows = scopedMaterials.filter((material) => material.materialStatus === "failed" || material.jobStatus === "failed" || material.slaMinutes > 120);
  const copy = language === "zh" ? zhCopy : enCopy;

  return (
    <div className="page-grid">
      <section className="page-header wide">
        <p className="eyebrow">Platform Admin Console</p>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
      </section>

      <div className="metric-row wide">
        <MetricCard label={copy.activeTenants} value={tenants.length} detail={copy.activeTenantsDetail} />
        <MetricCard label={copy.blockedJobs} value={riskRows.length} detail={copy.blockedJobsDetail} />
        <MetricCard label={copy.mediaFailures} value={scopedMaterials.filter((item) => item.mediaStatus === "failed").length} detail={copy.mediaFailuresDetail} />
        <MetricCard label={copy.providerIncidents} value={2} detail="Doubao Text / OpenAI Media" />
      </div>

      <section className="surface table-panel span-7">
        <div className="section-title">
          <h2>{copy.inbox}</h2>
          <StatusChip tone={riskRows.length > 0 ? "warning" : "success"}>{riskRows.length} SLA</StatusChip>
        </div>
        <table>
          <thead>
            <tr>
              <th>{copy.tenant}</th>
              <th>{copy.issue}</th>
              <th>{copy.scope}</th>
              <th>{copy.status}</th>
              <th>SLA</th>
            </tr>
          </thead>
          <tbody>
            {riskRows.map((material) => (
              <tr key={material.id}>
                <td>{tenants.find((tenant) => tenant.id === material.tenantId)?.name}</td>
                <td>{material.title}</td>
                <td>{material.childName}</td>
                <td><StatusChip tone={material.materialStatus === "failed" ? "danger" : "warning"}>{material.materialStatus}</StatusChip></td>
                <td>{material.slaMinutes}m</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="surface span-5">
        <div className="section-title">
          <h2>{copy.lifecycle}</h2>
        </div>
        <div className="funnel-list">
          {[
            ["Upload", counts.upload],
            ["OCR / Parse", counts.parse],
            ["Parent Review", counts.parentReview],
            ["Knowledge Pack", counts.knowledgePack],
            ["Media / TTS", counts.media],
            ["Ready", counts.ready],
            ["Failed", counts.failed]
          ].map(([label, value]) => (
            <div className="funnel-row" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="surface wide">
        <div className="section-title">
          <h2>{copy.tenantHealth}</h2>
        </div>
        <div className="tenant-health-grid">
          {tenantRows.map((row) => (
            <article key={row.tenant.id} className="tenant-health-card">
              <strong>{row.tenant.name}</strong>
              <span>{row.tenant.tenantType}</span>
              <b>{row.healthScore}</b>
              <small>{row.blockedJobs} blocked / {row.mediaFailures} media</small>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

const zhCopy = {
  title: "平台指挥台",
  subtitle: "多租户学习内容生产、AI 处理和学习结果的统一运营入口",
  activeTenants: "活跃租户",
  activeTenantsDetail: "学校、机构与家庭试点",
  blockedJobs: "阻塞任务",
  blockedJobsDetail: "超过 SLA 或失败",
  mediaFailures: "媒体失败",
  mediaFailuresDetail: "配图或 TTS 失败",
  providerIncidents: "Provider 事件",
  inbox: "今日待处理",
  tenant: "租户",
  issue: "问题",
  scope: "影响范围",
  status: "状态",
  lifecycle: "内容生产生命周期",
  tenantHealth: "租户健康排行"
};

const enCopy = {
  title: "Platform Command Center",
  subtitle: "Unified operations for multi-tenant content production, AI processing, and learning outcomes.",
  activeTenants: "Active tenants",
  activeTenantsDetail: "Schools, organizations, and family pilots",
  blockedJobs: "Blocked jobs",
  blockedJobsDetail: "Failed or over SLA",
  mediaFailures: "Media failures",
  mediaFailuresDetail: "Image or TTS failures",
  providerIncidents: "Provider incidents",
  inbox: "Action inbox",
  tenant: "Tenant",
  issue: "Issue",
  scope: "Scope",
  status: "Status",
  lifecycle: "Content lifecycle",
  tenantHealth: "Tenant health ranking"
};
```

- [ ] **Step 5: Wire Command Center in App**

Modify `apps/admin/src/App.tsx` to import `CommandCenter` and render it when `activePage === "command"`:

```tsx
import { useMemo, useState } from "react";
import { AppShell, type PageKey } from "./components/AppShell";
import { mockMaterials, mockTenants } from "./domain/mockData";
import type { Language, TenantScope } from "./domain/types";
import { createTranslator } from "./i18n/i18n";
import { CommandCenter } from "./pages/CommandCenter";

export function App() {
  const [language, setLanguage] = useState<Language>("zh");
  const [tenantScope, setTenantScope] = useState<TenantScope>("all");
  const [activePage, setActivePage] = useState<PageKey>("command");
  const t = createTranslator(language);
  const scopedMaterials = useMemo(
    () => (tenantScope === "all" ? mockMaterials : mockMaterials.filter((material) => material.tenantId === tenantScope)),
    [tenantScope]
  );

  return (
    <AppShell
      activePage={activePage}
      language={language}
      tenantScope={tenantScope}
      tenants={mockTenants}
      onLanguageChange={setLanguage}
      onTenantScopeChange={setTenantScope}
      onPageChange={setActivePage}
    >
      {activePage === "command" ? (
        <CommandCenter language={language} tenantScope={tenantScope} tenants={mockTenants} materials={mockMaterials} />
      ) : (
        <section className="page-header">
          <p className="eyebrow">Phase 1 mock prototype</p>
          <h1>{t("placeholder.phase1")}</h1>
          <p>{scopedMaterials.length} materials in current scope</p>
        </section>
      )}
    </AppShell>
  );
}
```

- [ ] **Step 6: Add table and grid styles**

Append to `apps/admin/src/styles.css`:

```css
.page-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 16px;
}

.wide {
  grid-column: 1 / -1;
}

.span-7 {
  grid-column: span 7;
}

.span-5 {
  grid-column: span 5;
}

.metric-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  display: grid;
  gap: 6px;
  background: var(--paper-white);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 16px;
}

.metric-card strong {
  font-size: 30px;
}

.metric-card small {
  color: var(--dust-brown);
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-title h2 {
  margin: 0;
  font-size: 18px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 11px 10px;
  border-bottom: 1px solid #f0d9d1;
  text-align: left;
  font-size: 14px;
}

th {
  color: var(--dust-brown);
  font-size: 12px;
  font-weight: 800;
}

.status-chip.warning {
  color: #8a5a00;
  background: #fff4d9;
}

.status-chip.danger {
  color: #98462a;
  background: #ffe6e0;
}

.status-chip.neutral {
  color: var(--dust-brown);
  background: var(--soft-sheet);
}

.funnel-list {
  display: grid;
  gap: 8px;
}

.funnel-row {
  display: flex;
  justify-content: space-between;
  border-radius: 10px;
  background: var(--soft-sheet);
  padding: 10px 12px;
}

.tenant-health-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.tenant-health-card {
  display: grid;
  gap: 4px;
  border-radius: 10px;
  background: var(--soft-sheet);
  padding: 14px;
}

.tenant-health-card b {
  color: var(--forest-mint);
  font-size: 24px;
}
```

- [ ] **Step 7: Run Command Center tests**

Run:

```bash
cd apps/admin && npm test -- src/pages/CommandCenter.test.tsx src/components/AppShell.test.tsx
```

Expected: PASS.

- [ ] **Step 8: Commit Command Center**

```bash
git add apps/admin/src
git commit -m "feat(admin): add command center prototype"
```

## Task 5: Build Tenant Detail Page

**Files:**
- Create: `apps/admin/src/pages/TenantDetail.tsx`
- Create: `apps/admin/src/pages/TenantDetail.test.tsx`
- Modify: `apps/admin/src/App.tsx`
- Modify: `apps/admin/src/styles.css`

- [ ] **Step 1: Write Tenant Detail tests**

Create `apps/admin/src/pages/TenantDetail.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockMaterials, mockProviderPolicies, mockTenants } from "../domain/mockData";
import { TenantDetail } from "./TenantDetail";

describe("TenantDetail", () => {
  it("shows tenant identity, quota, modules, and policy source", () => {
    render(
      <TenantDetail
        language="en"
        tenantId="tenant_bright_future"
        tenants={mockTenants}
        materials={mockMaterials}
        policies={mockProviderPolicies}
      />
    );
    expect(screen.getByText("Bright Future School")).toBeInTheDocument();
    expect(screen.getByText("tenant_override")).toBeInTheDocument();
    expect(screen.getByText("Worksheet import")).toBeInTheDocument();
    expect(screen.getByText("Tenant materials")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Implement Tenant Detail**

Create `apps/admin/src/pages/TenantDetail.tsx`:

```tsx
import { MetricCard, StatusChip } from "../components/ui";
import { getEffectiveProviderPolicy } from "../domain/selectors";
import type { AdminMaterial, Language, ProviderPolicy, Tenant } from "../domain/types";

interface TenantDetailProps {
  language: Language;
  tenantId: string;
  tenants: Tenant[];
  materials: AdminMaterial[];
  policies: ProviderPolicy[];
}

export function TenantDetail({ language, tenantId, tenants, materials, policies }: TenantDetailProps) {
  const tenant = tenants.find((item) => item.id === tenantId) ?? tenants[0];
  const tenantMaterials = materials.filter((material) => material.tenantId === tenant.id);
  const policy = getEffectiveProviderPolicy(policies, tenant.id);
  const copy = language === "zh" ? zhCopy : enCopy;

  return (
    <div className="page-grid">
      <section className="page-header wide">
        <p className="eyebrow">Tenants / {tenant.name}</p>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
      </section>

      <section className="surface span-5">
        <div className="tenant-profile">
          <div className="tenant-badge">{tenant.name.slice(0, 2).toUpperCase()}</div>
          <div>
            <h2>{tenant.name}</h2>
            <StatusChip tone={tenant.status === "active" ? "success" : "warning"}>{tenant.status}</StatusChip>
          </div>
        </div>
        <dl className="detail-list">
          <dt>Tenant ID</dt><dd>{tenant.id}</dd>
          <dt>Type</dt><dd>{tenant.tenantType}</dd>
          <dt>Region</dt><dd>{tenant.region}</dd>
          <dt>Owner</dt><dd>{tenant.ownerContact}</dd>
          <dt>Tier</dt><dd>{tenant.tier}</dd>
        </dl>
      </section>

      <section className="metric-row span-7">
        <MetricCard label="Parents" value={tenant.activeParents} detail="active parent accounts" />
        <MetricCard label="Children" value={tenant.children} detail="child profiles" />
        <MetricCard label="Materials" value={tenantMaterials.length} detail="current tenant scope" />
        <MetricCard label="Failed jobs" value={tenantMaterials.filter((item) => item.jobStatus === "failed").length} detail="requires attention" />
      </section>

      <section className="surface span-5">
        <div className="section-title"><h2>{copy.policy}</h2></div>
        <dl className="detail-list">
          <dt>AI_PROVIDER</dt><dd>{policy.aiProvider}</dd>
          <dt>MEDIA_PROVIDER</dt><dd>{policy.mediaProvider}</dd>
          <dt>Fallback</dt><dd>{policy.fallbackMode}</dd>
          <dt>Policy source</dt><dd>{policy.source}</dd>
        </dl>
      </section>

      <section className="surface span-7">
        <div className="section-title"><h2>{copy.modules}</h2></div>
        <div className="module-grid">
          {["Worksheet import", "AI review", "Real media", "Speaking score", "Weekly reports"].map((module) => (
            <div key={module} className="module-row">
              <span>{module}</span>
              <StatusChip tone="success">Enabled</StatusChip>
            </div>
          ))}
        </div>
      </section>

      <section className="surface wide table-panel">
        <div className="section-title"><h2>{copy.materials}</h2></div>
        <table>
          <thead>
            <tr><th>Material</th><th>Child</th><th>Material status</th><th>Job status</th><th>Media</th><th>Updated</th></tr>
          </thead>
          <tbody>
            {tenantMaterials.map((material) => (
              <tr key={material.id}>
                <td>{material.title}</td>
                <td>{material.childName}</td>
                <td><StatusChip tone={material.materialStatus === "failed" ? "danger" : "neutral"}>{material.materialStatus}</StatusChip></td>
                <td>{material.jobStatus}</td>
                <td>{material.mediaStatus}</td>
                <td>{material.updatedAt}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

const zhCopy = {
  title: "租户详情",
  subtitle: "运营资料、配额、模块、用户和租户级内容健康。",
  policy: "租户 Provider 策略",
  modules: "模块访问",
  materials: "Tenant materials"
};

const enCopy = {
  title: "Tenant Detail",
  subtitle: "Operational profile, quota, module access, users, and tenant-level content health.",
  policy: "Tenant provider policy",
  modules: "Module access",
  materials: "Tenant materials"
};
```

- [ ] **Step 3: Wire Tenant Detail route**

Modify `apps/admin/src/App.tsx`:

```tsx
import { useMemo, useState } from "react";
import { AppShell, type PageKey } from "./components/AppShell";
import { mockMaterials, mockProviderPolicies, mockTenants } from "./domain/mockData";
import type { Language, TenantScope } from "./domain/types";
import { createTranslator } from "./i18n/i18n";
import { CommandCenter } from "./pages/CommandCenter";
import { TenantDetail } from "./pages/TenantDetail";

export function App() {
  const [language, setLanguage] = useState<Language>("zh");
  const [tenantScope, setTenantScope] = useState<TenantScope>("all");
  const [activePage, setActivePage] = useState<PageKey>("command");
  const t = createTranslator(language);
  const selectedTenantId = tenantScope === "all" ? mockTenants[0].id : tenantScope;
  const scopedMaterials = useMemo(
    () => (tenantScope === "all" ? mockMaterials : mockMaterials.filter((material) => material.tenantId === tenantScope)),
    [tenantScope]
  );

  return (
    <AppShell
      activePage={activePage}
      language={language}
      tenantScope={tenantScope}
      tenants={mockTenants}
      onLanguageChange={setLanguage}
      onTenantScopeChange={setTenantScope}
      onPageChange={setActivePage}
    >
      {activePage === "command" && (
        <CommandCenter language={language} tenantScope={tenantScope} tenants={mockTenants} materials={mockMaterials} />
      )}
      {activePage === "tenants" && (
        <TenantDetail language={language} tenantId={selectedTenantId} tenants={mockTenants} materials={mockMaterials} policies={mockProviderPolicies} />
      )}
      {activePage !== "command" && activePage !== "tenants" && (
        <section className="page-header">
          <p className="eyebrow">Phase 1 mock prototype</p>
          <h1>{t("placeholder.phase1")}</h1>
          <p>{scopedMaterials.length} materials in current scope</p>
        </section>
      )}
    </AppShell>
  );
}
```

- [ ] **Step 4: Add detail styles**

Append to `apps/admin/src/styles.css`:

```css
.tenant-profile {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 18px;
}

.tenant-badge {
  width: 68px;
  height: 68px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  color: var(--cocoa-coral);
  background: var(--soft-sheet);
  border: 1px solid var(--outline-variant);
  font-weight: 900;
}

.detail-list {
  display: grid;
  grid-template-columns: 140px minmax(0, 1fr);
  gap: 10px 14px;
  margin: 0;
}

.detail-list dt {
  color: var(--dust-brown);
  font-weight: 700;
}

.detail-list dd {
  margin: 0;
}

.module-grid {
  display: grid;
  gap: 10px;
}

.module-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-radius: 10px;
  padding: 10px 12px;
  background: var(--soft-sheet);
}
```

- [ ] **Step 5: Run Tenant Detail tests**

Run:

```bash
cd apps/admin && npm test -- src/pages/TenantDetail.test.tsx src/pages/CommandCenter.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit Tenant Detail**

```bash
git add apps/admin/src
git commit -m "feat(admin): add tenant detail prototype"
```

## Task 6: Build Content Pipeline Page

**Files:**
- Create: `apps/admin/src/pages/ContentPipeline.tsx`
- Create: `apps/admin/src/pages/ContentPipeline.test.tsx`
- Modify: `apps/admin/src/App.tsx`
- Modify: `apps/admin/src/styles.css`

- [ ] **Step 1: Write Content Pipeline tests**

Create `apps/admin/src/pages/ContentPipeline.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { mockMaterials, mockTenants } from "../domain/mockData";
import { ContentPipeline } from "./ContentPipeline";

describe("ContentPipeline", () => {
  it("shows lifecycle table and selected material inspector", () => {
    render(<ContentPipeline language="zh" tenantScope="all" tenants={mockTenants} materials={mockMaterials} />);
    expect(screen.getByText("内容流水线")).toBeInTheDocument();
    expect(screen.getByText("生产队列")).toBeInTheDocument();
    expect(screen.getByText("HN-014 Phonics Worksheet")).toBeInTheDocument();
    expect(screen.getByText("生命周期时间线")).toBeInTheDocument();
  });

  it("filters failed materials", async () => {
    render(<ContentPipeline language="en" tenantScope="all" tenants={mockTenants} materials={mockMaterials} />);
    await userEvent.selectOptions(screen.getByLabelText("Status filter"), "failed");
    expect(screen.getByText("Animal Sounds Practice")).toBeInTheDocument();
    expect(screen.queryByText("Weekend Reading Worksheet")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Implement Content Pipeline**

Create `apps/admin/src/pages/ContentPipeline.tsx`:

```tsx
import { useMemo, useState } from "react";
import { StatusChip } from "../components/ui";
import { getMaterialsForScope } from "../domain/selectors";
import type { AdminMaterial, Language, MaterialStatus, Tenant, TenantScope } from "../domain/types";

interface ContentPipelineProps {
  language: Language;
  tenantScope: TenantScope;
  tenants: Tenant[];
  materials: AdminMaterial[];
}

export function ContentPipeline({ language, tenantScope, tenants, materials }: ContentPipelineProps) {
  const [statusFilter, setStatusFilter] = useState<"all" | MaterialStatus>("all");
  const scopedMaterials = getMaterialsForScope(materials, tenantScope);
  const filteredMaterials = useMemo(
    () => (statusFilter === "all" ? scopedMaterials : scopedMaterials.filter((material) => material.materialStatus === statusFilter)),
    [scopedMaterials, statusFilter]
  );
  const selected = filteredMaterials[0] ?? scopedMaterials[0];
  const copy = language === "zh" ? zhCopy : enCopy;

  return (
    <div className="page-grid">
      <section className="page-header wide">
        <p className="eyebrow">CourseMaterial -> MaterialParseJob -> LearningAsset</p>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
      </section>

      <section className="surface wide filter-bar">
        <label>
          {copy.status}
          <select aria-label="Status filter" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "all" | MaterialStatus)}>
            <option value="all">{copy.all}</option>
            <option value="processing">processing</option>
            <option value="needs_review">needs_review</option>
            <option value="ready">ready</option>
            <option value="failed">failed</option>
            <option value="archived">archived</option>
          </select>
        </label>
        <button className="primary-button">{copy.bulkRetry}</button>
        <button className="ghost-button">{copy.exportFailures}</button>
      </section>

      <section className="surface table-panel span-8">
        <div className="section-title"><h2>{copy.queue}</h2></div>
        <table>
          <thead>
            <tr>
              <th>{copy.tenant}</th>
              <th>{copy.child}</th>
              <th>{copy.material}</th>
              <th>Material</th>
              <th>Job</th>
              <th>Provider</th>
              <th>Assets</th>
              <th>Media</th>
              <th>SLA</th>
            </tr>
          </thead>
          <tbody>
            {filteredMaterials.map((material) => (
              <tr key={material.id}>
                <td>{tenants.find((tenant) => tenant.id === material.tenantId)?.name}</td>
                <td>{material.childName}</td>
                <td>{material.title}</td>
                <td><StatusChip tone={toneForStatus(material.materialStatus)}>{material.materialStatus}</StatusChip></td>
                <td>{material.jobStatus}</td>
                <td>{material.provider}</td>
                <td>{material.learningAssets}</td>
                <td>{material.mediaStatus}</td>
                <td>{material.slaMinutes > 120 ? `! ${material.slaMinutes}m` : `${material.slaMinutes}m`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <aside className="surface span-4 inspector">
        <div className="section-title"><h2>{copy.inspector}</h2></div>
        {selected ? (
          <>
            <h3>{selected.title}</h3>
            <dl className="detail-list compact">
              <dt>Material ID</dt><dd>{selected.id}</dd>
              <dt>Tenant</dt><dd>{tenants.find((tenant) => tenant.id === selected.tenantId)?.name}</dd>
              <dt>Parent</dt><dd>{selected.parentName}</dd>
              <dt>Child</dt><dd>{selected.childName} ({selected.childAge})</dd>
              <dt>Pages</dt><dd>{selected.pageCount}</dd>
              <dt>Warnings</dt><dd>{selected.warnings.length || "None"}</dd>
            </dl>
            <div className="timeline" aria-label="Lifecycle timeline">
              <h4>{copy.timeline}</h4>
              {["uploaded", "job queued", "OCR parse", selected.jobStatus, selected.materialStatus, selected.mediaStatus].map((item) => (
                <div className="timeline-row" key={item}>
                  <span />
                  <p>{item}</p>
                </div>
              ))}
            </div>
            <div className="audit-reason">
              <label>
                {copy.auditReason}
                <textarea maxLength={200} placeholder={copy.auditPlaceholder} />
              </label>
              <button className="primary-button">{copy.retryMock}</button>
            </div>
          </>
        ) : (
          <p>{copy.empty}</p>
        )}
      </aside>
    </div>
  );
}

function toneForStatus(status: MaterialStatus) {
  if (status === "ready") return "success";
  if (status === "failed") return "danger";
  if (status === "needs_review" || status === "processing") return "warning";
  return "neutral";
}

const zhCopy = {
  title: "内容流水线",
  subtitle: "跨租户追踪讲义从上传到复习包的生产状态",
  status: "状态",
  all: "全部",
  bulkRetry: "批量重试",
  exportFailures: "导出失败",
  queue: "生产队列",
  tenant: "租户",
  child: "孩子",
  material: "讲义",
  inspector: "当前选中",
  timeline: "生命周期时间线",
  auditReason: "审计原因",
  auditPlaceholder: "输入重试或归档原因，Phase 1 不会提交真实 mutation",
  retryMock: "模拟重试",
  empty: "当前范围没有讲义"
};

const enCopy = {
  title: "Content Pipeline",
  subtitle: "Track worksheet production from upload to reviewable learning packs across tenants.",
  status: "Status",
  all: "All",
  bulkRetry: "Bulk retry",
  exportFailures: "Export failures",
  queue: "Production queue",
  tenant: "Tenant",
  child: "Child",
  material: "Worksheet",
  inspector: "Selected item",
  timeline: "Lifecycle timeline",
  auditReason: "Audit reason",
  auditPlaceholder: "Enter retry or archive reason. Phase 1 will not submit a real mutation.",
  retryMock: "Mock retry",
  empty: "No materials in this scope"
};
```

- [ ] **Step 3: Wire Content Pipeline route**

Modify `apps/admin/src/App.tsx` to import and render `ContentPipeline`:

```tsx
import { useMemo, useState } from "react";
import { AppShell, type PageKey } from "./components/AppShell";
import { mockMaterials, mockProviderPolicies, mockTenants } from "./domain/mockData";
import type { Language, TenantScope } from "./domain/types";
import { createTranslator } from "./i18n/i18n";
import { CommandCenter } from "./pages/CommandCenter";
import { ContentPipeline } from "./pages/ContentPipeline";
import { TenantDetail } from "./pages/TenantDetail";

export function App() {
  const [language, setLanguage] = useState<Language>("zh");
  const [tenantScope, setTenantScope] = useState<TenantScope>("all");
  const [activePage, setActivePage] = useState<PageKey>("command");
  const t = createTranslator(language);
  const selectedTenantId = tenantScope === "all" ? mockTenants[0].id : tenantScope;
  const scopedMaterials = useMemo(
    () => (tenantScope === "all" ? mockMaterials : mockMaterials.filter((material) => material.tenantId === tenantScope)),
    [tenantScope]
  );

  return (
    <AppShell
      activePage={activePage}
      language={language}
      tenantScope={tenantScope}
      tenants={mockTenants}
      onLanguageChange={setLanguage}
      onTenantScopeChange={setTenantScope}
      onPageChange={setActivePage}
    >
      {activePage === "command" && (
        <CommandCenter language={language} tenantScope={tenantScope} tenants={mockTenants} materials={mockMaterials} />
      )}
      {activePage === "tenants" && (
        <TenantDetail language={language} tenantId={selectedTenantId} tenants={mockTenants} materials={mockMaterials} policies={mockProviderPolicies} />
      )}
      {activePage === "pipeline" && (
        <ContentPipeline language={language} tenantScope={tenantScope} tenants={mockTenants} materials={mockMaterials} />
      )}
      {activePage !== "command" && activePage !== "tenants" && activePage !== "pipeline" && (
        <section className="page-header">
          <p className="eyebrow">Phase 1 mock prototype</p>
          <h1>{t("placeholder.phase1")}</h1>
          <p>{scopedMaterials.length} materials in current scope</p>
        </section>
      )}
    </AppShell>
  );
}
```

- [ ] **Step 4: Add pipeline styles**

Append to `apps/admin/src/styles.css`:

```css
.filter-bar {
  display: flex;
  align-items: end;
  gap: 12px;
}

.filter-bar label {
  display: grid;
  gap: 6px;
  color: var(--dust-brown);
  font-size: 13px;
  font-weight: 800;
}

.filter-bar select,
.audit-reason textarea {
  border: 1px solid var(--outline-variant);
  border-radius: 9px;
  background: var(--paper-white);
  padding: 9px 12px;
}

.primary-button {
  border: 0;
  border-radius: 9px;
  padding: 10px 14px;
  color: white;
  background: var(--coral-jam);
  font-weight: 800;
}

.inspector h3 {
  margin-top: 0;
}

.detail-list.compact {
  grid-template-columns: 96px minmax(0, 1fr);
}

.timeline {
  margin-top: 18px;
}

.timeline-row {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
}

.timeline-row span {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--forest-mint);
}

.timeline-row p {
  margin: 6px 0;
}

.audit-reason {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.audit-reason label {
  display: grid;
  gap: 8px;
  font-weight: 800;
}

.audit-reason textarea {
  min-height: 88px;
  resize: vertical;
}
```

- [ ] **Step 5: Run Content Pipeline tests**

Run:

```bash
cd apps/admin && npm test -- src/pages/ContentPipeline.test.tsx src/pages/TenantDetail.test.tsx src/pages/CommandCenter.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit Content Pipeline**

```bash
git add apps/admin/src
git commit -m "feat(admin): add content pipeline workbench"
```

## Task 7: Add Placeholder Pages, Commands, and Documentation

**Files:**
- Create: `apps/admin/src/pages/PlaceholderPage.tsx`
- Create: `apps/admin/README.md`
- Modify: `apps/admin/src/App.tsx`
- Modify: `Makefile`
- Modify: `README.md`

- [ ] **Step 1: Create placeholder page**

Create `apps/admin/src/pages/PlaceholderPage.tsx`:

```tsx
import type { Language } from "../domain/types";

export function PlaceholderPage({ language, title }: { language: Language; title: string }) {
  const detail =
    language === "zh"
      ? "Phase 1 只实现导航入口和范围上下文；该页面将在后续 admin read API 或目标态页面任务中展开。"
      : "Phase 1 only implements the navigation entry and scope context; this page will be expanded with later admin read APIs or target-state page work.";

  return (
    <section className="surface empty-phase">
      <p className="eyebrow">Target-state module</p>
      <h1>{title}</h1>
      <p>{detail}</p>
    </section>
  );
}
```

- [ ] **Step 2: Wire placeholders in App**

In `apps/admin/src/App.tsx`, replace the fallback section with:

```tsx
<PlaceholderPage language={language} title={t("placeholder.phase1")} />
```

Also add:

```tsx
import { PlaceholderPage } from "./pages/PlaceholderPage";
```

- [ ] **Step 3: Add admin Makefile commands**

Modify `.PHONY` in `Makefile` to include:

```make
admin-install admin-dev admin-test admin-build
```

Add targets:

```make
admin-install:
	cd apps/admin && npm install

admin-dev:
	cd apps/admin && npm run dev

admin-test:
	cd apps/admin && npm test

admin-build:
	cd apps/admin && npm run build
```

- [ ] **Step 4: Add admin README**

Create `apps/admin/README.md`:

```md
# LearningEnglish Admin

Phase 1 production-shaped multi-tenant admin prototype.

## Scope

- Mock data only.
- No real admin auth.
- No production mutation.
- Validates `Platform -> Tenant -> ParentAccount -> ChildProfile -> CourseMaterial -> MaterialParseJob -> LearningAsset -> ReviewTask / PracticeSession / SpeakingAttempt -> WeeklyReport`.
- Supports Chinese / English UI switching.
- Keeps API paths, env keys, model names, task names, and permission keys in English.

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

## Target-State Pages Stubbed In Navigation

- Users & Children
- Learning Assets
- Learning Outcomes
- Provider Ops
- Infrastructure
- Audit & Access
- Developer API
```

- [ ] **Step 5: Update root README**

In `README.md`, add one row to the repository map:

```md
| [`apps/admin`](apps/admin) | React/Vite 多租户后台原型，Phase 1 使用 mock 数据验证后台信息架构 |
```

Add admin commands to the common commands table:

```md
| Admin 原型安装 | `make admin-install` |
| Admin 原型开发 | `make admin-dev` |
| Admin 原型测试 | `make admin-test` |
| Admin 原型构建 | `make admin-build` |
```

- [ ] **Step 6: Run full admin verification**

Run:

```bash
make admin-test
make admin-build
git diff --check
```

Expected:

- `make admin-test`: all Vitest tests pass.
- `make admin-build`: TypeScript and Vite build pass.
- `git diff --check`: no whitespace errors.

- [ ] **Step 7: Commit docs and commands**

```bash
git add apps/admin README.md Makefile
git commit -m "docs(admin): document admin prototype commands"
```

## Task 8: Browser Verification and Visual QA

**Files:**
- Modify only if QA finds issues:
  - `apps/admin/src/styles.css`
  - `apps/admin/src/pages/CommandCenter.tsx`
  - `apps/admin/src/pages/TenantDetail.tsx`
  - `apps/admin/src/pages/ContentPipeline.tsx`

- [ ] **Step 1: Start dev server**

Run:

```bash
make admin-dev
```

Expected: Vite prints a local URL, usually `http://127.0.0.1:5173/`.

- [ ] **Step 2: Open in Browser plugin**

Open the local Vite URL in the Browser plugin. Verify:

- `Command Center` renders by default.
- Sidebar labels are readable.
- Tenant selector is visible in the top bar.
- Language switch changes navigation and page labels.
- `Tenants` page shows tenant detail for selected scope.
- `Content Pipeline` page shows table, filters, and inspector.

- [ ] **Step 3: Check desktop viewport**

Use a 1440px wide viewport and verify:

- No text overlaps inside top bar.
- Tables fit without horizontal page overflow.
- Right inspector remains visible on `Content Pipeline`.
- Status chips do not wrap awkwardly.
- Warm theme is present but not visually noisy.

- [ ] **Step 4: Check narrow viewport**

Use an approximately 390px wide viewport and verify:

- Top bar controls wrap without overlap.
- Sidebar does not make content unreadable. If needed for Phase 1, allow horizontal scroll only inside tables, not the whole page.
- `Content Pipeline` inspector appears below the table or remains readable.

- [ ] **Step 5: Fix visual QA issues**

If desktop or narrow viewport has overlap, update `apps/admin/src/styles.css` with concrete responsive rules:

```css
@media (max-width: 900px) {
  .admin-shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    border-right: 0;
    border-bottom: 1px solid var(--outline-variant);
  }

  .sidebar-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .topbar {
    flex-wrap: wrap;
    padding: 12px;
  }

  .span-7,
  .span-5,
  .span-8,
  .span-4 {
    grid-column: 1 / -1;
  }

  .metric-row,
  .tenant-health-grid {
    grid-template-columns: 1fr;
  }

  .table-panel {
    overflow-x: auto;
  }
}
```

- [ ] **Step 6: Run final verification**

Run:

```bash
make admin-test
make admin-build
git diff --check
```

Expected: all pass.

- [ ] **Step 7: Commit QA fixes**

```bash
git add apps/admin
git commit -m "fix(admin): polish prototype responsive layout"
```

If no QA fixes were needed, skip this commit and record that no visual fixes were necessary in the final handoff.

## Self-Review Checklist

- Spec coverage:
  - `Command Center`: Task 4.
  - `Tenant Detail`: Task 5.
  - `Content Pipeline`: Task 6.
  - Bilingual UI: Task 3.
  - Tenant scope: Tasks 2 and 3.
  - Mock data only: Tasks 2 through 7.
  - High-risk action reason UI: Task 6.
  - Developer/API and later modules as placeholders: Task 7.
- Known intentional gaps:
  - No real admin auth.
  - No admin backend API.
  - No real mutation.
  - No provider/infrastructure/audit full pages in Phase 1.
- Required final verification:
  - `make admin-test`
  - `make admin-build`
  - Browser desktop and narrow viewport QA
  - `git diff --check`
