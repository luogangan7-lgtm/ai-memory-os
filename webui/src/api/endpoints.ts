// ── Typed API Endpoints ──────────────────────────────────────────────
import { api } from "./client";
import type {
  HealthResponse,
  DashboardStats,
  ThroughputPoint,
  MonitoringData,
  AuditLogResponse,
  TenantResponse,
  UserResponse,
  LLMEngineResponse,
  LLMSaveBody,
  LLMTestBody,
  LLMTestResponse,
  RAGConfig,
  SecurityConfig,
  ReflectionConfig,
  ReflectionTriggerResponse,
} from "./types";

// Health
export const getHealth = () => api.get<HealthResponse>("/health");

// Dashboard
export const getStats = () => api.get<DashboardStats>("/stats");
export const getThroughput = () => api.get<ThroughputPoint>("/stats/throughput");

// Monitoring
export const getMonitoring = () => api.get<MonitoringData>("/stats/monitoring");

// Audit
export const getAuditLogs = (action?: string, user?: string) => {
  const params = new URLSearchParams();
  if (action) params.set("action", action);
  if (user) params.set("user", user);
  params.set("limit", "50");
  return api.get<AuditLogResponse>(`/audit-logs?${params.toString()}`);
};

// Tenants
export const getTenants = () => api.get<TenantResponse>("/tenants");
export const createTenant = (body: {
  team_id: string;
  name: string;
  admin_username: string;
  admin_password: string;
}) => api.post("/tenants", body);

// Users
export const getUsers = (q?: string) => {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  params.set("limit", "50");
  return api.get<UserResponse>(`/users?${params.toString()}`);
};
export const toggleUserStatus = (userId: string, isActive: boolean) =>
  api.post(`/users/${userId}/${isActive ? "suspend" : "activate"}`);

// LLM Engine
export const getLLMEngineConfig = () => api.get<LLMEngineResponse>("/providers/llm-engine");
export const saveLLMEngineConfig = (body: LLMSaveBody) => api.post("/providers/llm-engine", body);
export const testLLMEngineConfig = (body: LLMTestBody) =>
  api.post<LLMTestResponse>("/providers/test-llm", body);

// Providers
export const saveEmbedConfig = (body: {
  provider: string;
  api_key: string;
  model: string;
  base_url: string;
}) => api.post("/providers/embedding", body);

export const saveRerankConfig = (body: {
  provider: string;
  api_key: string;
  model: string;
  threshold: number;
}) => api.post("/providers/rerank", body);

export const detectLocalModels = () => api.post<{ detected: { name: string; url: string; models: string[] }[] }>("/providers/detect-local");

// RAG & Security Config
export const saveRAGConfig = (body: RAGConfig) => api.post("/config/rag", body);
export const saveSecurityConfig = (body: SecurityConfig) => api.post("/config/security", body);

// Reflection
export const triggerReflection = () => api.post<ReflectionTriggerResponse>("/reflection/trigger");
export const saveReflectionConfig = (body: ReflectionConfig) => api.post("/reflection/config", body);

// Auth
export const login = (id: string, password: string, isUserApp: boolean = false) => {
  const url = isUserApp ? "/auth/token" : "/auth/login";
  return api.post<{ api_key?: string; access_token?: string }>(url, {
    username: id,
    email: id, // Send both, backend will decide
    password,
  });
};

export const signup = (username: string, email: string, password: string) =>
  api.post("/auth/register", {
    username,
    email,
    password,
    team_id: username // Auto-assign team_id
  });
