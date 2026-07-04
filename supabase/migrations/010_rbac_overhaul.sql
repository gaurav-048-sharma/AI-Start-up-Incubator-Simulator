-- ══════════════════════════════════════════════════════════════════
-- Migration 010: RBAC Overhaul
--
-- Consolidates the 15 tenant roles to 6 canonical roles, adds
-- department-level scoping, fixes the workflow_states RLS gap,
-- and updates helper functions for the new hierarchy.
--
-- New tenant roles: org_owner, org_admin, dept_manager,
--                   member, viewer, billing_admin
-- ══════════════════════════════════════════════════════════════════

-- ── 1. Add department support to organizations ─────────────────
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS is_department BOOLEAN DEFAULT false;

-- ── 2. Add department assignment to organization_members ───────
ALTER TABLE organization_members ADD COLUMN IF NOT EXISTS department_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_org_members_dept ON organization_members(department_id);

-- ── 3. Add department_id to ideas for dept-scoped data ─────────
ALTER TABLE ideas ADD COLUMN IF NOT EXISTS department_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_ideas_dept ON ideas(department_id);

-- ── 4. Data migration: map old roles → new canonical roles ─────
-- Must run BEFORE the new CHECK constraint is applied.

UPDATE organization_members SET role = 'org_owner'
  WHERE role = 'workspace_owner';

UPDATE organization_members SET role = 'org_admin'
  WHERE role = 'admin';

UPDATE organization_members SET role = 'dept_manager'
  WHERE role IN ('incubator_manager', 'innovation_lead');

UPDATE organization_members SET role = 'member'
  WHERE role IN (
    'founder', 'founder_product_lead', 'team_member',
    'investor_advisor', 'fullstack_engineer', 'ai_engineer',
    'backend_engineer', 'devops_engineer', 'ui_ux_designer',
    'security_consultant', 'growth_marketing_lead'
  );

-- 'viewer' stays 'viewer' — no update needed.
-- 'super_admin' was already migrated to 'admin' in 009, then to 'org_admin' above.

-- ── 5. Replace role CHECK constraint ───────────────────────────
ALTER TABLE organization_members
  DROP CONSTRAINT IF EXISTS organization_members_role_check;

ALTER TABLE organization_members
  ADD CONSTRAINT organization_members_role_check
  CHECK (role IN (
    'org_owner',
    'org_admin',
    'dept_manager',
    'billing_admin',
    'member',
    'viewer'
  ));

-- ── 6. Update RLS helper: get_auth_user_org_role ───────────────
-- Now returns the user's role within an organization (including dept membership).
CREATE OR REPLACE FUNCTION public.get_auth_user_org_role(p_org_id UUID)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $body$
DECLARE
    user_role TEXT;
BEGIN
    -- Direct org membership
    SELECT role INTO user_role
    FROM organization_members
    WHERE organization_id = p_org_id
      AND user_id = auth.uid();

    IF user_role IS NOT NULL THEN
        RETURN user_role;
    END IF;

    -- Check if p_org_id is a department; if so, check parent org membership
    SELECT om.role INTO user_role
    FROM organizations dept
    JOIN organization_members om ON om.organization_id = dept.parent_id AND om.user_id = auth.uid()
    WHERE dept.id = p_org_id
      AND dept.is_department = true;

    RETURN user_role;
END;
$body$;

-- ── 7. New helper: get user's department IDs within an org ─────
CREATE OR REPLACE FUNCTION public.get_auth_user_dept_ids(p_org_id UUID)
RETURNS UUID[]
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $body$
DECLARE
    dept_ids UUID[];
    user_org_role TEXT;
BEGIN
    -- Check the user's role in the parent org
    SELECT role INTO user_org_role
    FROM organization_members
    WHERE organization_id = p_org_id AND user_id = auth.uid();

    -- org_owner and org_admin see ALL departments
    IF user_org_role IN ('org_owner', 'org_admin') THEN
        SELECT ARRAY_AGG(id) INTO dept_ids
        FROM organizations
        WHERE parent_id = p_org_id AND is_department = true;
        RETURN COALESCE(dept_ids, ARRAY[]::UUID[]);
    END IF;

    -- dept_manager, member, viewer see only their assigned departments
    SELECT ARRAY_AGG(om.department_id) INTO dept_ids
    FROM organization_members om
    JOIN organizations dept ON dept.id = om.department_id AND dept.is_department = true
    WHERE om.organization_id = p_org_id
      AND om.user_id = auth.uid()
      AND om.department_id IS NOT NULL;

    RETURN COALESCE(dept_ids, ARRAY[]::UUID[]);
END;
$body$;

-- ── 8. Fix workflow_states RLS (was never updated for org scope) ─
DROP POLICY IF EXISTS "Users view own workflow" ON workflow_states;
CREATE POLICY "Users view org workflow" ON workflow_states
  FOR ALL USING (
    idea_id IN (SELECT id FROM ideas WHERE user_id = auth.uid())
    OR (
      organization_id IS NOT NULL
      AND organization_id IN (SELECT id FROM organizations WHERE status = 'active')
      AND public.get_auth_user_org_role(organization_id) IS NOT NULL
    )
    OR public.get_auth_platform_role() = 'super_admin'
  );

-- ── 9. Update ideas RLS for department scoping ─────────────────
DROP POLICY IF EXISTS "Users manage own ideas (org active)" ON ideas;
CREATE POLICY "Users manage ideas (org + dept)" ON ideas
  FOR ALL USING (
    -- Owner always has access
    auth.uid() = user_id
    -- Org member with active org
    OR (
      organization_id IS NOT NULL
      AND organization_id IN (SELECT id FROM organizations WHERE status = 'active')
      AND (
        -- org_owner/org_admin see all ideas in the org
        public.get_auth_user_org_role(organization_id) IN ('org_owner', 'org_admin')
        -- dept-scoped roles see ideas in their department(s)
        OR (
          department_id IS NULL
          AND public.get_auth_user_org_role(organization_id) IS NOT NULL
        )
        OR department_id = ANY(public.get_auth_user_dept_ids(organization_id))
      )
    )
    -- Platform super_admin bypass
    OR public.get_auth_platform_role() = 'super_admin'
  );

-- ── 10. Update invitations role constraint ─────────────────────
-- Allow the new role names in invitation defaults
ALTER TABLE invitations
  DROP CONSTRAINT IF EXISTS invitations_role_check;
-- No CHECK on invitations.role — the backend validates before insert.

-- ── 11. Update organization_members SELECT policy ──────────────
-- Expand visibility so dept_manager can also view memberships in their dept
DROP POLICY IF EXISTS "Members view memberships" ON organization_members;
CREATE POLICY "Members view memberships" ON organization_members
  FOR SELECT USING (
    user_id = auth.uid()
    OR public.get_auth_user_org_role(organization_id) IN ('org_owner', 'org_admin', 'dept_manager')
    OR public.get_auth_platform_role() = 'super_admin'
  );

-- ── 12. Grant execute on new functions ─────────────────────────
GRANT EXECUTE ON FUNCTION public.get_auth_user_dept_ids(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_auth_user_dept_ids(UUID) TO service_role;
