-- Users (profiles)
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    full_name TEXT,
    avatar_url TEXT,
    company_name TEXT,
    role TEXT DEFAULT 'founder',
    credits INTEGER DEFAULT 10,
    total_ideas_created INTEGER DEFAULT 0,
    total_workflows_run INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    tier TEXT DEFAULT 'free',
    password_hash TEXT,
    is_verified INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Startup Ideas
CREATE TABLE IF NOT EXISTS ideas (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES profiles(id) ON DELETE CASCADE,
    organization_id TEXT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    industry TEXT,
    target_market TEXT,
    problem_statement TEXT,
    proposed_solution TEXT,
    status TEXT DEFAULT 'draft',
    current_phase TEXT,
    progress INTEGER DEFAULT 0,
    metadata TEXT DEFAULT '{}',
    is_public INTEGER DEFAULT 0,
    public_slug TEXT UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Agent Activities
CREATE TABLE IF NOT EXISTS agent_activities (
    id TEXT PRIMARY KEY,
    idea_id TEXT REFERENCES ideas(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    agent_role TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT DEFAULT 'running',
    input_data TEXT,
    output_data TEXT,
    duration_ms INTEGER,
    tokens_used INTEGER,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

-- Workflow States
CREATE TABLE IF NOT EXISTS workflow_states (
    id TEXT PRIMARY KEY,
    idea_id TEXT REFERENCES ideas(id) ON DELETE CASCADE UNIQUE,
    graph_state TEXT NOT NULL,
    current_node TEXT NOT NULL,
    iteration INTEGER DEFAULT 0,
    quality_score REAL,
    decision_log TEXT DEFAULT '[]',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Generated Reports
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    idea_id TEXT REFERENCES ideas(id) ON DELETE CASCADE,
    report_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    file_url TEXT,
    version INTEGER DEFAULT 1,
    status TEXT DEFAULT 'completed',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Investor Simulations
CREATE TABLE IF NOT EXISTS simulations (
    id TEXT PRIMARY KEY,
    idea_id TEXT REFERENCES ideas(id) ON DELETE CASCADE,
    organization_id TEXT,
    simulation_type TEXT DEFAULT 'pitch',
    status TEXT DEFAULT 'active',
    investor_profiles TEXT NOT NULL,
    transcript TEXT DEFAULT '[]',
    outcome TEXT,
    funding_offered REAL,
    valuation REAL,
    feedback TEXT,
    score REAL,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Usage Events
CREATE TABLE IF NOT EXISTS usage_events (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES profiles(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    idea_id TEXT REFERENCES ideas(id) ON DELETE SET NULL,
    tokens_used INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    metadata TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    body TEXT,
    notification_type TEXT DEFAULT 'info',
    is_read INTEGER DEFAULT 0,
    action_url TEXT,
    metadata TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User Settings
CREATE TABLE IF NOT EXISTS user_settings (
    user_id TEXT PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
    llm_provider TEXT DEFAULT 'gemini',
    llm_model TEXT DEFAULT 'gemini-2.5-flash',
    max_iterations INTEGER DEFAULT 5,
    quality_threshold REAL DEFAULT 0.70,
    notification_email INTEGER DEFAULT 1,
    notification_in_app INTEGER DEFAULT 1,
    webhook_url TEXT,
    theme TEXT DEFAULT 'dark',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ideas_user_id ON ideas(user_id);
CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status);
CREATE INDEX IF NOT EXISTS idx_agent_activities_idea ON agent_activities(idea_id);
CREATE INDEX IF NOT EXISTS idx_reports_idea ON reports(idea_id);
CREATE INDEX IF NOT EXISTS idx_simulations_idea ON simulations(idea_id);
CREATE INDEX IF NOT EXISTS idx_workflow_states_idea ON workflow_states(idea_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_user ON usage_events(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
