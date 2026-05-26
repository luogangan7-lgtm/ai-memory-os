-- V7.1 数据库回滚 — 移除新增的表、视图、字段与版本记录
BEGIN;

-- 1. 删除视图
DROP VIEW IF EXISTS memory_category_stats;

-- 2. 删除反馈表
DROP TABLE IF EXISTS skill_feedback;

-- 3. 移除 memories 表的字段
ALTER TABLE memories
    DROP COLUMN IF EXISTS category,
    DROP COLUMN IF EXISTS agent_source;

-- 4. 移除 memory_skills 表的的字段
ALTER TABLE memory_skills
    DROP COLUMN IF EXISTS source_agents,
    DROP COLUMN IF EXISTS verified_by,
    DROP COLUMN IF EXISTS fail_count,
    DROP COLUMN IF EXISTS last_used_at,
    DROP COLUMN IF EXISTS evolved_count;

-- 5. 移除版本迁移记录
DELETE FROM schema_migrations WHERE version = 'v7_1';

COMMIT;
