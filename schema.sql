-- aiInvest database schema for Supabase

-- Portfolio: single-row table tracking overall state
CREATE TABLE IF NOT EXISTS portfolio (
    id TEXT PRIMARY KEY DEFAULT 'main',
    cash_balance NUMERIC NOT NULL DEFAULT 2000.0,
    total_value NUMERIC NOT NULL DEFAULT 2000.0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Initialize portfolio
INSERT INTO portfolio (id, cash_balance, total_value)
VALUES ('main', 2000.0, 2000.0)
ON CONFLICT (id) DO NOTHING;

-- Holdings: current stock positions
CREATE TABLE IF NOT EXISTS holdings (
    ticker TEXT PRIMARY KEY,
    shares NUMERIC NOT NULL,
    avg_cost NUMERIC NOT NULL,
    current_price NUMERIC NOT NULL DEFAULT 0,
    sector TEXT NOT NULL,
    purchased_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Transactions: trade history log
CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action TEXT NOT NULL,
    ticker TEXT NOT NULL,
    shares NUMERIC NOT NULL,
    price NUMERIC NOT NULL,
    total_cost NUMERIC NOT NULL,
    reasoning TEXT,
    portfolio_value_after NUMERIC,
    cash_after NUMERIC
);

CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_ticker ON transactions (ticker);

-- Analysis runs: log of each AI analysis
CREATE TABLE IF NOT EXISTS analysis_runs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    market_data JSONB,
    ai_analysis TEXT,
    recommendations JSONB,
    actions_taken JSONB,
    run_duration NUMERIC,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_timestamp ON analysis_runs (timestamp DESC);

-- Stop-loss events
CREATE TABLE IF NOT EXISTS stop_loss_events (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ticker TEXT NOT NULL,
    trigger_price NUMERIC NOT NULL,
    avg_cost NUMERIC NOT NULL,
    shares NUMERIC NOT NULL,
    loss_pct NUMERIC NOT NULL
);

-- Row Level Security
ALTER TABLE portfolio ENABLE ROW LEVEL SECURITY;
ALTER TABLE holdings ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE stop_loss_events ENABLE ROW LEVEL SECURITY;

-- Service role has full access
CREATE POLICY "service_role_all_portfolio" ON portfolio FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_holdings" ON holdings FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_transactions" ON transactions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_analysis_runs" ON analysis_runs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_stop_loss_events" ON stop_loss_events FOR ALL USING (true) WITH CHECK (true);
