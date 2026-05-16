-- ══════════════════════════════════════════════════════════════════
-- AI Start-up Incubator Simulator — Initial Database Schema
-- Run this in your Supabase SQL Editor
-- ══════════════════════════════════════════════════════════════════

-- Users (extended profiles on top of Supabase Auth)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    avatar_url TEXT,
    company_name TEXT,
    role TEXT DEFAULT 'founder',
    credits INTEGER DEFAULT 10,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Startup Ideas
CREATE TABLE IF NOT EXISTS ideas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    industry TEXT,
    target_market TEXT,
    problem_statement TEXT,
    proposed_solution TEXT,
    status TEXT DEFAULT 'draft' CHECK (status IN (
        'draft','submitted','researching','validating',
        'planning','simulating','completed','failed'
    )),
    current_phase TEXT,
    progress INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent Activities
CREATE TABLE IF NOT EXISTS agent_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID REFERENCES ideas(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    agent_role TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT DEFAULT 'running' CHECK (status IN ('running','completed','failed','waiting')),
    input_data JSONB,
    output_data JSONB,
    duration_ms INTEGER,
    tokens_used INTEGER,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Workflow States
CREATE TABLE IF NOT EXISTS workflow_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID REFERENCES ideas(id) ON DELETE CASCADE,
    graph_state JSONB NOT NULL,
    current_node TEXT NOT NULL,
    iteration INTEGER DEFAULT 0,
    quality_score FLOAT,
    decision_log JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Generated Reports
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID REFERENCES ideas(id) ON DELETE CASCADE,
    report_type TEXT NOT NULL CHECK (report_type IN (
        'market_analysis','tech_architecture','growth_strategy',
        'financial_projection','legal_review','pitch_deck',
        'executive_summary','full_report'
    )),
    title TEXT NOT NULL,
    content JSONB NOT NULL,
    file_url TEXT,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Investor Simulations
CREATE TABLE IF NOT EXISTS simulations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID REFERENCES ideas(id) ON DELETE CASCADE,
    simulation_type TEXT DEFAULT 'pitch',
    investor_profiles JSONB NOT NULL,
    transcript JSONB DEFAULT '[]',
    outcome TEXT,
    funding_offered DECIMAL,
    valuation DECIMAL,
    feedback JSONB,
    score FLOAT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ── Row-Level Security ──────────────────────────────────────────
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE ideas ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulations ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users view own profile" ON profiles FOR ALL USING (auth.uid() = id);
CREATE POLICY "Users manage own ideas" ON ideas FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users view own activities" ON agent_activities
    FOR ALL USING (idea_id IN (SELECT id FROM ideas WHERE user_id = auth.uid()));
CREATE POLICY "Users view own workflow" ON workflow_states
    FOR ALL USING (idea_id IN (SELECT id FROM ideas WHERE user_id = auth.uid()));
CREATE POLICY "Users view own reports" ON reports
    FOR ALL USING (idea_id IN (SELECT id FROM ideas WHERE user_id = auth.uid()));
CREATE POLICY "Users view own simulations" ON simulations
    FOR ALL USING (idea_id IN (SELECT id FROM ideas WHERE user_id = auth.uid()));

-- ── Indexes ─────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_ideas_user_id ON ideas(user_id);
CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status);
CREATE INDEX IF NOT EXISTS idx_agent_activities_idea ON agent_activities(idea_id);
CREATE INDEX IF NOT EXISTS idx_reports_idea ON reports(idea_id);
CREATE INDEX IF NOT EXISTS idx_simulations_idea ON simulations(idea_id);
CREATE INDEX IF NOT EXISTS idx_workflow_states_idea ON workflow_states(idea_id);

-- ── Realtime ────────────────────────────────────────────────────
ALTER PUBLICATION supabase_realtime ADD TABLE agent_activities;
ALTER PUBLICATION supabase_realtime ADD TABLE workflow_states;
ALTER PUBLICATION supabase_realtime ADD TABLE ideas;
