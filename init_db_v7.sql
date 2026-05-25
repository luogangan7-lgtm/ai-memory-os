-- V7.0 数据库增量迁移 — 纯增量，不改现有表
BEGIN;

-- L4 程序性技能表
CREATE TABLE IF NOT EXISTS memory_skills (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id         VARCHAR NOT NULL,
    skill_name      VARCHAR(200) NOT NULL,
    skill_content   TEXT NOT NULL,
    trigger_pattern VARCHAR(300),
    source_atom_ids UUID[] DEFAULT '{}',
    usage_count     INTEGER DEFAULT 0,
    effectiveness   FLOAT DEFAULT 1.0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_skills_team ON memory_skills(team_id);

-- 代码实体表
CREATE TABLE IF NOT EXISTS code_entities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id         VARCHAR NOT NULL,
    project_path    VARCHAR(500),
    entity_type     VARCHAR(50) NOT NULL,
    name            VARCHAR(300) NOT NULL,
    qualified_name  VARCHAR(500),
    file_path       VARCHAR(500),
    language        VARCHAR(50),
    description     TEXT,
    signature       TEXT,
    start_line      INTEGER,
    end_line        INTEGER,
    indexed_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_code_team ON code_entities(team_id, project_path);

-- memories 表追加列
ALTER TABLE memories ADD COLUMN IF NOT EXISTS layer VARCHAR(2) DEFAULT 'L1';
ALTER TABLE memories ADD COLUMN IF NOT EXISTS dedup_hash VARCHAR(64);
CREATE INDEX IF NOT EXISTS idx_memories_dedup ON memories(team_id, dedup_hash) WHERE dedup_hash IS NOT NULL;

-- 迁移版本追踪
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     VARCHAR(50) PRIMARY KEY,
    applied_at  TIMESTAMPTZ DEFAULT NOW(),
    description TEXT
);
INSERT INTO schema_migrations (version, description) VALUES ('v7', 'V7.0: memory_skills, code_entities, layer/dedup_hash') ON CONFLICT DO NOTHING;

COMMIT;
