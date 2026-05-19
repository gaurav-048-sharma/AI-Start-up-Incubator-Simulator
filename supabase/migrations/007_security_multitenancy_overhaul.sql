-- ══════════════════════════════════════════════════════════════════
-- Migration 007: Security & Multi-Tenancy Overhaul
-- 
-- 1. Separates platform_role from tenant role on profiles
-- 2. Drops current_org_id (anti-pattern for multi-tab usage)
-- 3. Adds organization_id FK to tenant-scoped tables
-- 4. Adds billing/subscription fields to organizations
-- 5. Tightens RLS policies for proper tenant isolation
-- ══════════════════════════════════════════════════════════════════

-- ── 1. Platform role on profiles ────────────────────────────────
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS platform_role TEXT DEFAULT 'user'
    CHECK (platform_role IN ('user', 'support', 'billing_admin', 'super_admin'));

-- Migrate existing super_admin roles
UPDATE profiles SET platform_role = 'super_admin' WHERE role = 'super_admin';

-- ── 2. Deprecate current_org_id ─────────────────────────────────
-- We keep the column but mark it deprecated; frontend now uses X-Org-Id header
-- ALTER TABLE profiles DROP COLUMN IF EXISTS current_org_id;
-- ^ Kept commented to avoid breaking existing queries during transition.
-- New code should never read or write current_org_id.

-- ── 3. Add organization_id to tenant-scoped tables ──────────────
ALTER TABLE agent_activities ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
ALTER TABLE simulations ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
ALTER TABLE workflow_states ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;

-- ── 4. Billing / subscription fields on organizations ───────────
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'active'
    CHECK (subscription_status IN ('active', 'past_due', 'canceled', 'suspended', 'trialing', 'pending_payment'));
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS billing_email TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS current_period_end TIMESTAMPTZ;

-- ── 5. Indexes for new columns ──────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_agent_activities_org ON agent_activities(organization_id);
CREATE INDEX IF NOT EXISTS idx_simulations_org ON simulations(organization_id);
CREATE INDEX IF NOT EXISTS idx_reports_org ON reports(organization_id);
CREATE INDEX IF NOT EXISTS idx_workflow_states_org ON workflow_states(organization_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_org ON usage_events(organization_id);
CREATE INDEX IF NOT EXISTS idx_profiles_platform_role ON profiles(platform_role);
CREATE INDEX IF NOT EXISTS idx_orgs_stripe_customer ON organizations(stripe_customer_id);

-- ── 6. Helper function: check platform role ─────────────────────
CREATE OR REPLACE FUNCTION public.get_auth_platform_role()
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    p_role TEXT;
BEGIN
    SELECT platform_role INTO p_role FROM profiles WHERE id = auth.uid();
    RETURN COALESCE(p_role, 'user');
END;
$$;

-- ── 7. Tighten RLS: agent_activities scoped to org ──────────────
DROP POLICY IF EXISTS "Users view own activities" ON agent_activities;
CREATE POLICY "Users view own activities" ON agent_activities
    FOR ALL USING (
        idea_id IN (SELECT id FROM ideas WHERE user_id = auth.uid())
        OR public.get_auth_user_org_role(organization_id) IS NOT NULL
        OR public.get_auth_platform_role() = 'super_admin'
    );

-- ── 8. Tighten RLS: reports scoped to org ───────────────────────
DROP POLICY IF EXISTS "Users view own reports" ON reports;
CREATE POLICY "Users view own reports" ON reports
    FOR ALL USING (
        idea_id IN (SELECT id FROM ideas WHERE user_id = auth.uid())
        OR public.get_auth_user_org_role(organization_id) IS NOT NULL
        OR public.get_auth_platform_role() = 'super_admin'
    );

-- ── 9. Tighten RLS: simulations scoped to org ──────────────────
DROP POLICY IF EXISTS "Users view own simulations" ON simulations;
CREATE POLICY "Users view own simulations" ON simulations
    FOR ALL USING (
        idea_id IN (SELECT id FROM ideas WHERE user_id = auth.uid())
        OR public.get_auth_user_org_role(organization_id) IS NOT NULL
        OR public.get_auth_platform_role() = 'super_admin'
    );

-- ── 10. Super admin bypass for enterprise_requests ──────────────
DROP POLICY IF EXISTS "Super admins can manage enterprise requests" ON enterprise_requests;
CREATE POLICY "Super admins can manage enterprise requests" ON enterprise_requests
    FOR ALL USING (
        public.get_auth_platform_role() = 'super_admin'
    );

-- ── 11. Super admin bypass for organizations (global view) ──────
DROP POLICY IF EXISTS "Super admins view all orgs" ON organizations;

CREATE POLICY "Super admins view all orgs" ON organizations
    FOR SELECT USING (
        public.get_auth_platform_role() IN ('super_admin', 'support')
    );
-- ── 12. Update handle_new_user to set platform_role ─────────────
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name, avatar_url, role, platform_role)
    VALUES (
        NEW.id,
        NEW.raw_user_meta_data->>'full_name',
        NEW.raw_user_meta_data->>'avatar_url',
        COALESCE(NEW.raw_user_meta_data->>'role', 'founder'),
        'user'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
