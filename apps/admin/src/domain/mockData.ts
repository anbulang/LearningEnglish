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
