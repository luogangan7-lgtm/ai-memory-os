
-- Payment orders table
CREATE TABLE IF NOT EXISTS orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id         VARCHAR NOT NULL,
    out_trade_no    VARCHAR(64) UNIQUE NOT NULL,
    payjs_order_id  VARCHAR(64),
    plan            VARCHAR(20) NOT NULL DEFAULT 'pro',
    duration_months INTEGER DEFAULT 1,
    total_fee       INTEGER NOT NULL,
    status          VARCHAR(20) DEFAULT 'pending',
    payjs_raw       JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    paid_at         TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_orders_team ON orders(team_id);
CREATE INDEX IF NOT EXISTS idx_orders_out_trade ON orders(out_trade_no);
