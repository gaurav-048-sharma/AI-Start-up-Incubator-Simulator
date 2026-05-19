-- =========================================================================
-- Fix Infinite Recursion in Row Level Security (RLS)
-- =========================================================================

-- 1. Create a SECURITY DEFINER function to read members without triggering RLS
CREATE OR REPLACE FUNCTION public.get_auth_user_org_role(org_id UUID)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $body$
DECLARE
    user_role TEXT;
BEGIN
    SELECT role INTO user_role
    FROM organization_members
    WHERE organization_id = org_id 
      AND user_id = auth.uid();

    RETURN user_role;
END;
$body$;

-- 2. Drop the recursive policies from organization_members
DROP POLICY IF EXISTS "Members view memberships" ON organization_members;
DROP POLICY IF EXISTS "Admins manage members" ON organization_members;

-- 3. Create non-recursive policies for organization_members
CREATE POLICY "Members view memberships" ON organization_members
    FOR SELECT USING (
        user_id = auth.uid()
        OR public.get_auth_user_org_role(organization_id) IN ('super_admin', 'admin', 'incubator_manager')
    );

CREATE POLICY "Admins manage members" ON organization_members
    FOR ALL USING (
        public.get_auth_user_org_role(organization_id) IN ('super_admin', 'admin')
    );

-- 4. Re-apply to other tables (optional but recommended for consistency)
DROP POLICY IF EXISTS "Admins manage org" ON organizations;
CREATE POLICY "Admins manage org" ON organizations
    FOR ALL USING (
        owner_id = auth.uid()
        OR public.get_auth_user_org_role(id) IN ('super_admin', 'admin')
    );

DROP POLICY IF EXISTS "Admins manage invitations" ON invitations;
CREATE POLICY "Admins manage invitations" ON invitations
    FOR ALL USING (
        public.get_auth_user_org_role(organization_id) IN ('super_admin', 'admin', 'incubator_manager')
    );

DROP POLICY IF EXISTS "Admins view audit log" ON audit_log;
CREATE POLICY "Admins view audit log" ON audit_log
    FOR SELECT USING (
        user_id = auth.uid()
        OR public.get_auth_user_org_role(organization_id) IN ('super_admin', 'admin')
    );

DROP POLICY IF EXISTS "Users manage own ideas" ON ideas;
CREATE POLICY "Users manage own ideas" ON ideas
    FOR ALL USING (
        user_id = auth.uid()
        OR public.get_auth_user_org_role(organization_id) IS NOT NULL
    );
