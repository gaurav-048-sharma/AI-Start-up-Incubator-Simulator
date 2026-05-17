-- ══════════════════════════════════════════════════════════════════
-- Migration 003: Enterprise RBAC & Multi-Tenant Organizations
-- Adds organizations, team memberships, role hierarchy, audit logs,
-- and invitation system for enterprise-grade access control.
-- ══════════════════════════════════════════════════════════════════

-- ── Organizations / Workspaces ──────────────────────────────────
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    logo_url TEXT,
    plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'enterprise')),
    owner_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    settings JSONB DEFAULT '{}',
    max_members INTEGER DEFAULT 5,
    max_ideas INTEGER DEFAULT 20,
    sso_provider TEXT,           -- For enterprise SSO (e.g. 'okta', 'azure_ad')
    sso_entity_id TEXT,         -- IdP Entity ID
    sso_acs_url TEXT,           -- Assertion Consumer Service URL
    sso_x509_cert TEXT,         -- Public Certificate for validation
    sso_enforced BOOLEAN DEFAULT FALSE, -- Require SSO login
    sso_metadata JSONB,         -- Extra SSO config data
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Organization Members ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN (
        'super_admin',
        'admin',
        'incubator_manager',
        'innovation_lead',
        'investor_advisor',
        'founder',
        'team_member',
        'viewer'
    )),
    permissions JSONB DEFAULT '[]',
    invited_by UUID REFERENCES profiles(id),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, user_id)
);

-- ── Invitations ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'team_member',
    invited_by UUID REFERENCES profiles(id),
    token TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'expired', 'revoked')),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Audit Log ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details JSONB DEFAULT '{}',
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Update profiles with organization link ──────────────────────
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS current_org_id UUID REFERENCES organizations(id);

-- ── Update ideas with organization scope ────────────────────────
ALTER TABLE ideas ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id);

-- ── Row-Level Security ──────────────────────────────────────────
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Org policies: members can view their org
CREATE POLICY "Members view own org" ON organizations
    FOR SELECT USING (
        id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid())
        OR owner_id = auth.uid()
    );

-- Owners and admins can update org
CREATE POLICY "Admins manage org" ON organizations
    FOR ALL USING (
        owner_id = auth.uid()
        OR id IN (
            SELECT organization_id FROM organization_members
            WHERE user_id = auth.uid() AND role IN ('super_admin', 'admin')
        )
    );

-- Members see their own membership
CREATE POLICY "Members view memberships" ON organization_members
    FOR SELECT USING (
        user_id = auth.uid()
        OR organization_id IN (
            SELECT organization_id FROM organization_members
            WHERE user_id = auth.uid() AND role IN ('super_admin', 'admin', 'incubator_manager')
        )
    );

-- Admins manage members
CREATE POLICY "Admins manage members" ON organization_members
    FOR ALL USING (
        organization_id IN (
            SELECT organization_id FROM organization_members
            WHERE user_id = auth.uid() AND role IN ('super_admin', 'admin')
        )
    );

-- Admins can manage invitations
CREATE POLICY "Admins manage invitations" ON invitations
    FOR ALL USING (
        organization_id IN (
            SELECT organization_id FROM organization_members
            WHERE user_id = auth.uid() AND role IN ('super_admin', 'admin', 'incubator_manager')
        )
    );

-- Audit log viewable by admins
CREATE POLICY "Admins view audit log" ON audit_log
    FOR SELECT USING (
        user_id = auth.uid()
        OR organization_id IN (
            SELECT organization_id FROM organization_members
            WHERE user_id = auth.uid() AND role IN ('super_admin', 'admin')
        )
    );

-- ── Update ideas RLS for org-scoped access ──────────────────────
-- Team members in the same org can view org ideas
DROP POLICY IF EXISTS "Users manage own ideas" ON ideas;
CREATE POLICY "Users manage own ideas" ON ideas
    FOR ALL USING (
        auth.uid() = user_id
        OR organization_id IN (
            SELECT organization_id FROM organization_members
            WHERE user_id = auth.uid()
        )
    );

-- ── Indexes ─────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_org_members_org ON organization_members(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_members(user_id);
CREATE INDEX IF NOT EXISTS idx_org_members_role ON organization_members(role);
CREATE INDEX IF NOT EXISTS idx_invitations_org ON invitations(organization_id);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON invitations(email);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(token);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_org ON audit_log(organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ideas_org ON ideas(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_slug ON organizations(slug);

-- ── Functions ───────────────────────────────────────────────────
-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, full_name, avatar_url, role)
    VALUES (
        NEW.id,
        NEW.raw_user_meta_data->>'full_name',
        NEW.raw_user_meta_data->>'avatar_url',
        COALESCE(NEW.raw_user_meta_data->>'role', 'founder')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();
