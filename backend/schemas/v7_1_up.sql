-- V7.1 数据库增量迁移 — 纯增量，不改现有表
BEGIN;

-- 0. 创建迁移追踪表（防止之前未创建成功）
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     VARCHAR(50) PRIMARY KEY,
    applied_at  TIMESTAMPTZ DEFAULT NOW(),
    description TEXT
);
INSERT INTO schema_migrations (version, description) VALUES ('v7', 'V7.0: memory_skills, code_entities, layer/dedup_hash') ON CONFLICT DO NOTHING;

-- 1. memory_skills 表新增 3 列（追踪多 Agent 贡献与进化）
ALTER TABLE memory_skills
    ADD COLUMN IF NOT EXISTS source_agents  TEXT[]    DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS verified_by    TEXT[]    DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS fail_count     INTEGER   DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_used_at   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS evolved_count  INTEGER   DEFAULT 0;

-- 2. 技能反馈记录表（每次使用结果都有记录）
CREATE TABLE IF NOT EXISTS skill_feedback (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id     VARCHAR NOT NULL,
    skill_id    UUID REFERENCES memory_skills(id) ON DELETE CASCADE,
    memory_ids  UUID[]    DEFAULT '{}',
    outcome     VARCHAR   NOT NULL CHECK (outcome IN ('success','failure','partial')),
    agent_id    VARCHAR   DEFAULT 'unknown',
    context     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_skill_feedback_skill ON skill_feedback(skill_id);
CREATE INDEX IF NOT EXISTS idx_skill_feedback_team  ON skill_feedback(team_id, created_at DESC);

-- 3. memories 表新增分类列和来源列
ALTER TABLE memories
    ADD COLUMN IF NOT EXISTS category  VARCHAR(50) DEFAULT '其他',
    ADD COLUMN IF NOT EXISTS agent_source VARCHAR(100) DEFAULT 'unknown';

-- 4. 分类统计视图（供前端知识地图使用）
CREATE OR REPLACE VIEW memory_category_stats AS
SELECT
    team_id,
    category,
    COUNT(*) AS count,
    MAX(created_at) AS latest_at,
    array_agg(DISTINCT agent_source) AS contributing_agents
FROM memories
WHERE layer = 'L1'
GROUP BY team_id, category;

-- 5. 记录版本迁移
INSERT INTO schema_migrations (version, description) VALUES ('v7_1', 'V7.1: skill_feedback, memories category & agent_source') ON CONFLICT DO NOTHING;

COMMIT;
