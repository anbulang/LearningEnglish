import type {
  AdminAuditEventsData,
  AdminImpersonationSessionsData,
  AdminLearningAsset,
  AdminMaterial,
  AdminOperationsData,
  AdminTenantDetailData,
  AdminUser,
  AdminUserAccount,
  ModuleKey,
  ProviderPolicy,
  SourcePage,
  Tenant,
  TenantModuleSetting
} from "./types";

function createSourcePages(slug: string, pageCount: number, sourceType: SourcePage["sourceType"]): SourcePage[] {
  return Array.from({ length: pageCount }, (_, index) => ({
    pageIndex: index + 1,
    thumbnailUrl: `/admin-mock/pages/${slug}-${index + 1}.png`,
    sourceType
  }));
}

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
    jobId: "job_hn014_parse",
    confidenceSummary: "OCR parsed successfully; media generation still running.",
    ocrConfidence: 0.92,
    sourcePages: createSourcePages("hn014", 6, "camera"),
    materialStatus: "ready",
    jobStatus: "ready",
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
    jobId: "job_queen_quilt_parse",
    confidenceSummary: "OCR parsing in progress.",
    ocrConfidence: 0.88,
    sourcePages: createSourcePages("queen-quilt", 8, "gallery"),
    materialStatus: "processing",
    jobStatus: "processing",
    provider: "doubao",
    learningAssets: 92,
    mediaStatus: "pending",
    slaMinutes: 225,
    updatedAt: "2026-05-24 09:41",
    warnings: ["OCR parsing in progress"]
  },
  {
    id: "mat_weekend",
    tenantId: "tenant_sunny_kids",
    parentName: "Grace Li",
    childName: "Leo Li",
    childAge: 7,
    title: "Weekend Reading Worksheet",
    pageCount: 4,
    jobId: "job_weekend_parse",
    confidenceSummary: "Waiting for parent review.",
    ocrConfidence: 0.96,
    sourcePages: createSourcePages("weekend", 4, "gallery"),
    materialStatus: "needs_review",
    jobStatus: "needs_review",
    provider: "stub",
    learningAssets: 52,
    mediaStatus: "pending",
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
    jobId: "job_animals_parse",
    confidenceSummary: "OCR request failed before draft assets were generated.",
    ocrConfidence: 0.31,
    sourcePages: createSourcePages("animals", 5, "camera"),
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
    jobId: "job_colors_parse",
    confidenceSummary: "Archived by parent request.",
    ocrConfidence: 0.9,
    sourcePages: createSourcePages("colors", 1, "camera"),
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

export const mockUsers: AdminUserAccount[] = [
  {
    childId: "child_tom_zhang",
    childName: "Tom Zhang",
    age: 6,
    level: "starter",
    learningGoal: "课后稳定复习",
    preferredReviewDurationMinutes: 10,
    parentNotes: "喜欢动物主题。",
    tenantId: "tenant_bright_future",
    parentName: "Emily Zhang",
    materialsCount: 4,
    speakingAttempts: 6,
    latestWeeklyReportId: "report_tom_0610",
    createdAt: "2026-03-18T08:00:00Z"
  },
  {
    childId: "child_ivy_lin",
    childName: "Ivy Lin",
    age: 7,
    level: "mover",
    learningGoal: "提升口语流利度",
    preferredReviewDurationMinutes: 15,
    parentNotes: "",
    tenantId: "tenant_maple_pilot",
    parentName: "Grace Lin",
    materialsCount: 2,
    speakingAttempts: 3,
    latestWeeklyReportId: "report_ivy_0609",
    createdAt: "2026-09-02T09:00:00Z"
  },
  {
    childId: "child_leo_star",
    childName: "Leo",
    age: 5,
    level: "starter",
    learningGoal: "建立字母与发音认知",
    preferredReviewDurationMinutes: 8,
    parentNotes: "注意力时间较短。",
    tenantId: "tenant_little_star",
    parentName: "Family Pilot",
    materialsCount: 1,
    speakingAttempts: 0,
    latestWeeklyReportId: "",
    createdAt: "2026-01-06T10:00:00Z"
  }
];

export const mockLearningAssets: AdminLearningAsset[] = [
  {
    id: "asset_hn014_queen",
    materialId: "mat_014",
    materialTitle: "HN-014 Phonics Worksheet",
    materialStatus: "ready",
    tenantId: "tenant_bright_future",
    parentName: "Emily Zhang",
    childName: "Tom Zhang",
    text: "queen",
    kind: "word",
    translation: "女王",
    primaryAccent: "us",
    mediaStatus: "ready",
    generatedImageStatus: "ready",
    generatedImageUrl: "/admin-mock/media/queen.png",
    ttsUsStatus: "ready",
    ttsUsUrl: "/admin-mock/media/queen-us.mp3",
    ttsUkStatus: "ready",
    ttsUkUrl: "/admin-mock/media/queen-uk.mp3",
    updatedAt: "2026-06-10T08:00:00Z"
  },
  {
    id: "asset_hn014_quiet",
    materialId: "mat_014",
    materialTitle: "HN-014 Phonics Worksheet",
    materialStatus: "ready",
    tenantId: "tenant_bright_future",
    parentName: "Emily Zhang",
    childName: "Tom Zhang",
    text: "The queen is quiet.",
    kind: "sentence",
    translation: "女王很安静。",
    primaryAccent: "uk",
    mediaStatus: "processing",
    generatedImageStatus: "processing",
    generatedImageUrl: "",
    ttsUsStatus: "ready",
    ttsUsUrl: "/admin-mock/media/quiet-us.mp3",
    ttsUkStatus: "processing",
    ttsUkUrl: "",
    updatedAt: "2026-06-10T08:05:00Z"
  },
  {
    id: "asset_maple_rabbit",
    materialId: "mat_maple_01",
    materialTitle: "Maple Pilot Rr Worksheet",
    materialStatus: "ready",
    tenantId: "tenant_maple_pilot",
    parentName: "Grace Lin",
    childName: "Ivy Lin",
    text: "rabbit",
    kind: "word",
    translation: "兔子",
    primaryAccent: "us",
    mediaStatus: "failed",
    generatedImageStatus: "failed",
    generatedImageUrl: "",
    ttsUsStatus: "ready",
    ttsUsUrl: "/admin-mock/media/rabbit-us.mp3",
    ttsUkStatus: "ready",
    ttsUkUrl: "/admin-mock/media/rabbit-uk.mp3",
    updatedAt: "2026-06-09T12:00:00Z"
  },
  {
    id: "asset_little_star_apple",
    materialId: "mat_star_01",
    materialTitle: "Little Star Aa Worksheet",
    materialStatus: "needs_review",
    tenantId: "tenant_little_star",
    parentName: "Family Pilot",
    childName: "Leo",
    text: "apple",
    kind: "word",
    translation: "苹果",
    primaryAccent: "us",
    mediaStatus: "pending",
    generatedImageStatus: "pending",
    generatedImageUrl: "",
    ttsUsStatus: "pending",
    ttsUsUrl: "",
    ttsUkStatus: "pending",
    ttsUkUrl: "",
    updatedAt: "2026-06-08T09:30:00Z"
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

const moduleKeys: ModuleKey[] = ["worksheet_import", "ai_review", "media_pipeline", "speaking_score", "weekly_reports"];

export const mockModuleSettings: TenantModuleSetting[] = mockTenants.flatMap((tenant) =>
  moduleKeys.map((moduleKey) => ({
    tenantId: tenant.id,
    moduleKey,
    enabled: true,
    source: "global_default"
  }))
);

export const mockOperationsData: AdminOperationsData = {
  tenantScope: "all",
  summary: {
    tenant_count: mockTenants.length,
    materials: mockMaterials.length,
    material_parse_jobs: mockMaterials.length,
    media_failures: 2,
    speaking_attempts: 18,
    severity: "critical",
    issue_count: 2
  },
  materialParseJobs: {
    total: mockMaterials.length,
    failed: 1,
    running: 1,
    stale_threshold_minutes: 30,
    stale_processing: 1,
    latest_failed: [{ id: "job_animals_parse", tenant_id: "tenant_sunny_kids", status: "failed" }],
    latest_running: [{ id: "job_queen_quilt_parse", tenant_id: "tenant_maple_pilot", status: "processing" }]
  },
  mediaGeneration: {
    failure_signals: {
      generated_image_status: 1,
      tts_us_status: 0,
      tts_uk_status: 1,
      total: 2
    }
  },
  speakingAttempts: {
    total: 18,
    failed: 1,
    pending: 2,
    stale_pending: 1,
    latest_failed: []
  },
  providerConfiguration: {
    global: mockProviderPolicies[0],
    tenant_overrides: mockProviderPolicies.slice(1),
    runtime: {
      ai_provider: "doubao",
      media_provider: "real",
      readiness: {
        ai_provider_ready: true,
        media_image_provider_ready: true,
        media_tts_provider_ready: true,
        speech_provider_ready: true,
        speech_assessment_provider_ready: true
      }
    }
  },
  moduleToggleCoverage: {
    tenant_count: mockTenants.length,
    module_keys: moduleKeys,
    total: mockTenants.length * moduleKeys.length,
    enabled: mockTenants.length * moduleKeys.length - 1,
    disabled: 1,
    overrides: 1
  },
  issues: [
    {
      id: "issue_material_job_job_animals_parse_failed",
      severity: "critical",
      statusLabel: "Parse failed",
      reason: "OCR request failed before draft assets were generated.",
      recommendedAction: "retry_material_job",
      requiredPermission: "admin.material.retry",
      relatedResource: {
        type: "material_parse_job",
        id: "job_animals_parse",
        tenantId: "tenant_sunny_kids",
        materialId: "mat_animals"
      },
      source: "database_snapshot"
    },
    {
      id: "issue_material_job_job_queen_quilt_parse_stale",
      severity: "warning",
      statusLabel: "Parse processing stale",
      reason: "Material parse job has been processing for at least 30 minutes.",
      recommendedAction: "inspect_material_job",
      requiredPermission: "admin.operations.read",
      relatedResource: {
        type: "material_parse_job",
        id: "job_queen_quilt_parse",
        tenantId: "tenant_maple_pilot",
        materialId: "mat_queen_quilt"
      },
      source: "database_snapshot"
    }
  ]
};

export const mockTenantDetailData: AdminTenantDetailData = {
  requiredPermission: "admin.tenant.read",
  tenant: {
    ...mockTenants[2],
    displayName: mockTenants[2].name,
    avatarUrl: "",
    phoneNumber: "13800138110",
    phoneVerifiedAt: "2026-05-25T10:00:00+00:00",
    wechatUnionId: "wechat_union_tenant_sunny_kids",
    wechatOpenId: "wechat_open_tenant_sunny_kids",
    updatedAt: "2026-05-25T10:05:00+00:00"
  },
  summary: {
    children: mockTenants[2].children,
    materials: 2,
    failed_materials: 1,
    processing_materials: 0
  },
  children: [
    {
      id: "child_sunny_emma",
      name: "Emma Chen",
      age: 6,
      level: "starter",
      learningGoal: "Read short phonics stories",
      preferredReviewDurationMinutes: 12,
      parentNotes: "",
      latestWeeklyReportId: "report_sunny_week_1",
      speakingAttempts: 5
    }
  ],
  materials: mockMaterials.filter((material) => material.tenantId === "tenant_sunny_kids"),
  providerPolicy: mockProviderPolicies[0],
  moduleSettings: mockModuleSettings.filter((setting) => setting.tenantId === "tenant_sunny_kids"),
  weeklyReports: {
    latest: [{ id: "report_sunny_week_1", child_id: "child_sunny_emma", completed_sessions: 3 }],
    aggregate: { completed_sessions: 3, reviewed_words: 48 }
  },
  speakingAttempts: {
    latest: [],
    by_status: { scored: 4, failed: 1 }
  },
  riskSummary: {
    risk_level: "high",
    reasons: ["failed_material_jobs", "media_generation_failed"]
  }
};

export const mockAuditEventsPage: AdminAuditEventsData = {
  items: [
    {
      id: "audit_mock_retry",
      actorId: "admin_001",
      actorRole: "Platform Owner",
      tenantScope: "tenant_sunny_kids",
      action: "admin.material_job.retry",
      resourceType: "material_parse_job",
      resourceId: "job_animals_parse",
      riskLevel: "high",
      result: "success",
      reason: "Provider recovered after incident review.",
      traceId: "req_mock_retry",
      createdAt: "2026-05-25T10:06:00+00:00"
    }
  ],
  nextCursor: "2026-05-25T10:06:00+00:00|audit_mock_retry"
};

export const mockImpersonationSessions: AdminImpersonationSessionsData = {
  requiredPermission: "admin.impersonation.read",
  tenantScope: "all",
  status: "all",
  items: [
    {
      id: "imp_mock_active",
      tenantId: "tenant_sunny_kids",
      targetParentId: "tenant_sunny_kids",
      actorId: "admin_001",
      status: "active",
      reason: "Reproduce parent-reported upload issue.",
      expiresAt: "2026-05-25T10:36:00+00:00",
      createdAt: "2026-05-25T10:06:00+00:00",
      endedAt: "",
      updatedAt: "2026-05-25T10:06:00+00:00",
      tenantDisplayName: "Sunny Kids English",
      targetParentDisplayName: "Sunny Kids English"
    },
    {
      id: "imp_mock_ended",
      tenantId: "tenant_maple_pilot",
      targetParentId: "tenant_maple_pilot",
      actorId: "admin_001",
      status: "ended",
      reason: "Session closed after support handoff.",
      expiresAt: "2026-05-24T09:30:00+00:00",
      createdAt: "2026-05-24T09:00:00+00:00",
      endedAt: "2026-05-24T09:18:00+00:00",
      updatedAt: "2026-05-24T09:18:00+00:00",
      tenantDisplayName: "Maple Pilot Group",
      targetParentDisplayName: "Maple Pilot Group"
    }
  ],
  auditEvent: mockAuditEventsPage.items[0]
};
