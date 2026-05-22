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
  PipelineStatus,
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
export const deleteTenant = (teamId: string) => api.delete(`/tenants/${teamId}`);
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
export const deleteUser = (username: string) =>
  api.delete(`/users/${username}`);

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
export const getRAGConfig = () => api.get<RAGConfig>("/config/rag");
export const saveRAGConfig = (body: RAGConfig) => api.post("/config/rag", body);
export const getSecurityConfig = () => api.get<SecurityConfig>("/config/security");
export const saveSecurityConfig = (body: SecurityConfig) => api.post("/config/security", body);

// Reflection
export const getReflectionConfig = () => api.get<ReflectionConfig>("/reflection/config");
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

export const signup = (username: string, email: string, password: string, code: string = "") =>
  api.post("/auth/register", {
    code,
    username,
    email,
    password,
    team_id: username // Auto-assign team_id
  });
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const getRouting = () => api.get<any>("/routing");
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const getProviders = () => api.get<any>("/providers");
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const testEngine = (engineType: string) => api.get<any>(`/routing/test/${engineType}`);

// User-side pipeline status
export const getUserPipelineStatus = () =>
  api.get<PipelineStatus>("/api/user/llm/pipeline/status");

export interface AdminMemory {
  id: string;
  team_id: string;
  category: string;
  subcategory: string;
  topic: string;
  title: string;
  content: string;
  source_type: string;
  created_at: string;
}

export interface AdminMemoriesResponse {
  total: number;
  limit: number;
  offset: number;
  memories: AdminMemory[];
}

export const getAdminMemories = (params: {
  team_id?: string;
  category?: string;
  source_type?: string;
  q?: string;
  limit?: number;
  offset?: number;
}) => {
  const urlParams = new URLSearchParams();
  if (params.team_id) urlParams.set("team_id", params.team_id);
  if (params.category) urlParams.set("category", params.category);
  if (params.source_type) urlParams.set("source_type", params.source_type);
  if (params.q) urlParams.set("q", params.q);
  if (params.limit !== undefined) urlParams.set("limit", String(params.limit));
  if (params.offset !== undefined) urlParams.set("offset", String(params.offset));
  return api.get<AdminMemoriesResponse>(`/memories?${urlParams.toString()}`);
};

export const deleteAdminMemory = (memoryId: string) =>
  api.delete<{ deleted: boolean }>(`/memories/${memoryId}`);


export interface UserDocument {
  id: string;
  team_id: string;
  filename: string;
  minio_key: string;
  chunk_count: number;
  file_size: number;
  tags: string[];
  created_at: string;
}

export interface AdminDocument extends UserDocument {}

export interface AdminDocumentsResponse {
  total: number;
  limit: number;
  offset: number;
  documents: AdminDocument[];
}

export const getUserDocuments = () =>
  api.get<UserDocument[]>("/memory/documents");

export const deleteUserDocument = (docId: string) =>
  api.delete<{ ok: boolean }>(`/memory/documents/${docId}`);

export const getAdminDocuments = (params: {
  team_id?: string;
  q?: string;
  limit?: number;
  offset?: number;
}) => {
  const urlParams = new URLSearchParams();
  if (params.team_id) urlParams.set("team_id", params.team_id);
  if (params.q) urlParams.set("q", params.q);
  if (params.limit !== undefined) urlParams.set("limit", String(params.limit));
  if (params.offset !== undefined) urlParams.set("offset", String(params.offset));
  return api.get<AdminDocumentsResponse>(`/documents?${urlParams.toString()}`);
};

export const deleteAdminDocument = (docId: string) =>
  api.delete<{ deleted: boolean }>(`/documents/${docId}`);


