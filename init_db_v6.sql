-- V6.0 新增表：在 V5.0 原有表基础上追加

-- L0: 原始对话录制
CREATE TABLE IF NOT EXISTS pipeline_conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id         VARCHAR NOT NULL,
    session_id      VARCHAR NOT NULL,
    agent_id        VARCHAR DEFAULT 'default',
    messages        JSONB NOT NULL,
    processed_l1    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pconv_team ON pipeline_conversations(team_id, processed_l1);
CREATE INDEX IF NOT EXISTS idx_pconv_session ON pipeline_conversations(team_id, session_id);

-- L2: 场景块
CREATE TABLE IF NOT EXISTS memory_scenarios (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id     VARCHAR NOT NULL,
    title       VARCHAR(300) NOT NULL,
    content_md  TEXT NOT NULL,
    atom_ids    UUID[] DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_scenarios_team ON memory_scenarios(team_id);

-- L3: 用户画像
CREATE TABLE IF NOT EXISTS user_persona (
    team_id         VARCHAR PRIMARY KEY,
    persona_md      TEXT NOT NULL DEFAULT '',
    scenario_count  INTEGER DEFAULT 0,
    version         INTEGER DEFAULT 1,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 任务画布 (schema reflects the actual production table; code in api/canvas.py and api/mcp.py
-- writes completed_steps/next_steps as JSONB via ::jsonb casts.)
CREATE TABLE IF NOT EXISTS task_canvas (
    id              SERIAL PRIMARY KEY,
    team_id         TEXT NOT NULL,
    task_id         TEXT NOT NULL,
    agent_id        VARCHAR(50) DEFAULT 'default',
    task_title      VARCHAR(300) DEFAULT '',
    canvas_mermaid  TEXT DEFAULT '',
    completed_steps JSONB DEFAULT '[]'::jsonb,
    next_steps      JSONB DEFAULT '[]'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (team_id, task_id, agent_id)
);

-- 管线用量追踪
CREATE TABLE IF NOT EXISTS pipeline_usage (
    team_id      VARCHAR NOT NULL,
    year_month   VARCHAR(7) NOT NULL,
    l1_calls     INTEGER DEFAULT 0,
    l2_calls     INTEGER DEFAULT 0,
    l3_calls     INTEGER DEFAULT 0,
    l1_tokens    INTEGER DEFAULT 0,
    l2_tokens    INTEGER DEFAULT 0,
    l3_tokens    INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    PRIMARY KEY (team_id, year_month)
);

-- 管线任务队列
CREATE TABLE IF NOT EXISTS pipeline_queue (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id      VARCHAR NOT NULL,
    layer        VARCHAR(2) NOT NULL,
    input_ids    UUID[] NOT NULL,
    status       VARCHAR DEFAULT 'pending',
    retry_count  INTEGER DEFAULT 0,
    scheduled_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at  TIMESTAMPTZ,
    error_msg    TEXT
);
CREATE INDEX IF NOT EXISTS idx_pq_status ON pipeline_queue(status, scheduled_at);

-- V6.1 付费系统
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS plan VARCHAR(20) DEFAULT 'free';
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS plan_expires_at TIMESTAMPTZ;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS mcp_call_count INTEGER DEFAULT 0;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS email TEXT;

CREATE TABLE IF NOT EXISTS orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id         VARCHAR NOT NULL,
    out_trade_no    VARCHAR(64) UNIQUE NOT NULL,
    payjs_order_id  VARCHAR(64),
    plan            VARCHAR(20) NOT NULL,
    duration_months INTEGER DEFAULT 1,
    total_fee       INTEGER NOT NULL,
    status          VARCHAR(20) DEFAULT 'pending',
    payjs_raw       JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    paid_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_orders_team ON orders(team_id);
CREATE INDEX IF NOT EXISTS idx_orders_out_trade ON orders(out_trade_no);
