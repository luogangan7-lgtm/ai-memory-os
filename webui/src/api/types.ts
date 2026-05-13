// ── API Response Types ──────────────────────────────────────────────

export interface ServiceHealth {
  postgres: boolean;
  qdrant: boolean;
  neo4j: boolean;
  redis: boolean;
  minio: boolean;
}

export interface HealthResponse {
  status: string;
  services: ServiceHealth;
}

export interface DashboardStats {
  total: number;
  active_users: number;
  today_writes: number;
  tokens_saved: number;
  memory_growth?: string;
}

export interface ThroughputPoint {
  labels: string[];
  values: number[];
}

export interface MonitoringData {
  token_labels: string[];
  token_values: number[];
  writes_labels: string[];
  writes_values: number[];
  latency_buckets: number[];
  top_tenants: TopTenant[];
}

export interface TopTenant {
  team_id: string;
  memory_count: number;
  token_usage: number;
}

export interface AuditLog {
  created_at: string;
  username: string;
  user_id: string;
  team_id: string;
  action: string;
  target_id: string;
  ip_address: string;
  success: boolean;
}

export interface AuditLogResponse {
  logs: AuditLog[];
}

export interface Tenant {
  team_id: string;
  name: string;
  user_count: number;
  memory_count: number;
  active: boolean;
  created_at: string;
}

export interface TenantResponse {
  tenants: Tenant[];
}

export interface User {
  user_id: string;
  username: string;
  team_id: string;
  memory_count: number;
  token_usage: number;
  active: boolean;
  created_at: string;
}

export interface UserResponse {
  users: User[];
}

export interface ProviderConfig {
  provider: string;
  api_key: string;
  model: string;
  base_url?: string;
}

export interface LLMEngineConfig {
  classifier?: {
    provider: string;
    model: string;
    has_key: boolean;
    base_url: string;
  };
  reflection?: {
    provider: string;
    model: string;
    has_key: boolean;
    base_url: string;
  };
}

export interface LLMEngineResponse {
  config: LLMEngineConfig;
}

export interface LLMSaveBody {
  engine: "classifier" | "reflection";
  provider: string;
  model: string;
  api_key: string;
  base_url?: string;
  batch_size?: number;
}

export interface LLMTestBody {
  engine: "classifier" | "reflection";
  provider: string;
  model: string;
  api_key: string;
  base_url?: string;
}

export interface LLMTestResponse {
  success: boolean;
  latency_ms?: number;
  model?: string;
  error?: string;
}

export interface RAGConfig {
  top_k: number;
  min_similarity: number;
  max_context_tokens: number;
  history_count: number;
}

export interface SecurityConfig {
  rate_write: number;
  rate_read: number;
  max_mem_len: number;
  jwt_expire: number;
}

export interface ReflectionConfig {
  decay_rate: number;
  quality_threshold: number;
  interval_hours: number;
}

export interface ReflectionTriggerResponse {
  status: string;
  message?: string;
}

export interface ApiError {
  detail: string;
}
