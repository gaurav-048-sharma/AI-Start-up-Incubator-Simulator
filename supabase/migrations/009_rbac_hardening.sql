-- ══════════════════════════════════════════════════════════════════
-- Migration 009: RBAC Hardening & Data Integrity
-- 
-- 1. Cleans up role confusion by removing 'super_admin' from tenant level
-- 2. Restricts root organization provisioning RPC to service_role only
-- 3. Fixes IDOR and privilege escalation paths in RLS policies
-- ══════════════════════════════════════════════════════════════════

-- 1. Data Integrity: Clean up existing role confusion
-- Any tenant member with 'super_admin' role (which was allowed before) 
-- is demoted to 'admin' to ensure platform privileges are separate.
UPDATE organization_members 
SET role = 'admin' 
WHERE role = 'super_admin';

-- 2. Structural Restraint: Enforce valid tenant roles ONLY
-- Removes 'super_admin' from the allowed check constraint on memberships.
ALTER TABLE organization_members
  DROP CONSTRAINT IF EXISTS organization_members_role_check;

ALTER TABLE organization_members
  ADD CONSTRAINT organization_members_role_check
  CHECK (role IN (
    'admin', 
    'incubator_manager', 
    'innovation_lead', 
    'investor_advisor',
    'founder', 
    'team_member', 
    'viewer',
    'workspace_owner'
  ));

-- 3. Provisioning Security: Stop public/authenticated RPC access
-- Only the backend agent (service_role) should trigger the provisioning logic.
REVOKE EXECUTE ON FUNCTION public.create_organization_from_request(uuid, uuid) FROM authenticated;
REVOKE EXECUTE ON FUNCTION public.create_organization_from_request(uuid, uuid) FROM public;
GRANT EXECUTE ON FUNCTION public.create_organization_from_request(uuid, uuid) TO service_role;

-- 4. RLS Hardening: Fix enterprise_requests oversight
-- Ensure management of requests uses platform_role exclusively.
DROP POLICY IF EXISTS "Super admins can manage enterprise requests" ON enterprise_requests;
CREATE POLICY "Super admins manage enterprise requests" ON enterprise_requests
  FOR ALL USING (
    public.get_auth_platform_role() = 'super_admin'
  );

-- 5. Organization Visibility Bypass for Support
-- Allow 'support' platform role to see all organizations for troubleshooting.
DROP POLICY IF EXISTS "Super admins view all orgs" ON organizations;
CREATE POLICY "Platform oversight view all orgs" ON organizations
  FOR SELECT USING (
    public.get_auth_platform_role() IN ('super_admin', 'support')
  );

-- 6. Members Management Oversight
-- Super admins should be able to manage all memberships globally for security response.
DROP POLICY IF EXISTS "Admins manage members (server-only)" ON organization_members;
CREATE POLICY "Platform admins manage all members" ON organization_members
  FOR ALL USING (
    public.get_auth_platform_role() = 'super_admin'
    OR auth.role() = 'service_role'
  );
