-- ══════════════════════════════════════════════════════════════════
-- Migration 002: Analytics, Notifications, and User Settings
-- Adds usage tracking, notification inbox, user preferences, and
-- idea comparison support.
-- ══════════════════════════════════════════════════════════════════

-- ── Usage Tracking ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'workflow_run', 'agent_run', 'simulation_run',
        'report_export', 'api_call', 'llm_call'
    )),
    idea_id UUID REFERENCES ideas(id) ON DELETE SET NULL,
    tokens_used INTEGER DEFAULT 0,
    cost_usd DECIMAL(10,6) DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Notifications ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    body TEXT,
    notification_type TEXT DEFAULT 'info' CHECK (notification_type IN (
        'info', 'success', 'warning', 'error', 'workflow_complete',
        'simulation_complete', 'credit_low'
    )),
    is_read BOOLEAN DEFAULT FALSE,
    action_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── User Settings ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_settings (
    user_id UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
    llm_provider TEXT DEFAULT 'gemini',
    llm_model TEXT DEFAULT 'gemini-2.5-flash',
    max_iterations INTEGER DEFAULT 5 CHECK (max_iterations BETWEEN 1 AND 15),
    quality_threshold DECIMAL(3,2) DEFAULT 0.70 CHECK (quality_threshold BETWEEN 0 AND 1),
    notification_email BOOLEAN DEFAULT TRUE,
    notification_in_app BOOLEAN DEFAULT TRUE,
    webhook_url TEXT,
    theme TEXT DEFAULT 'dark',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Add credits tracking to profiles ────────────────────────────
-- (credits column already exists, add usage summary fields)
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS total_ideas_created INTEGER DEFAULT 0;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS total_workflows_run INTEGER DEFAULT 0;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS total_tokens_used BIGINT DEFAULT 0;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS tier TEXT DEFAULT 'free';

-- ── Row-Level Security ──────────────────────────────────────────
ALTER TABLE usage_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own usage" ON usage_events
    FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users manage own notifications" ON notifications
    FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users manage own settings" ON user_settings
    FOR ALL USING (auth.uid() = user_id);

-- ── Indexes ─────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_usage_events_user ON usage_events(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_type ON usage_events(event_type);
CREATE INDEX IF NOT EXISTS idx_usage_events_created ON usage_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(user_id, is_read) WHERE NOT is_read;

-- ── Realtime ────────────────────────────────────────────────────
ALTER PUBLICATION supabase_realtime ADD TABLE notifications;
