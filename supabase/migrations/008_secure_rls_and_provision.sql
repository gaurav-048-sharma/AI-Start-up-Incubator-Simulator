-- ══════════════════════════════════════════════════════════════════
-- Migration 008: Strict RLS, server-side org provisioning, and member insert guard
--
-- 1) Prevent client-side inserts into organization_members (server-only)
-- 2) Ensure org-scoped resources only accessible when org.status = 'active'
-- 3) Provide a SECURITY DEFINER function to provision orgs from enterprise_requests
-- ══════════════════════════════════════════════════════════════════

-- 1. Guard membership inserts: require service_role (backend) for INSERT/UPDATE/DELETE
DROP POLICY IF EXISTS "Admins manage members" ON organization_members;
CREATE POLICY "Admins manage members (server-only)" ON organization_members
  FOR ALL USING (
    auth.role() = 'service_role'
  ) WITH CHECK (
    auth.role() = 'service_role'
  );

-- 2. Ensure org resources are only visible when organization.status = 'active'
-- Apply to ideas, reports, simulations, agent_activities
-- ideas
DROP POLICY IF EXISTS "Users manage own ideas" ON ideas;
CREATE POLICY "Users manage own ideas (org active)" ON ideas
  FOR ALL USING (
    auth.uid() = user_id
    OR (
      organization_id IS NOT NULL
      AND organization_id IN (
        SELECT id FROM organizations WHERE status = 'active'
      )
      AND organization_id IN (
        SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
      )
    )
    OR public.get_auth_platform_role() = 'super_admin'
  );

-- reports
DROP POLICY IF EXISTS "Users view own reports" ON reports;
CREATE POLICY "Users view own reports (org active)" ON reports
  FOR ALL USING (
    idea_id IN (SELECT id FROM ideas WHERE user_id = auth.uid())
    OR (
      organization_id IS NOT NULL
      AND organization_id IN (SELECT id FROM organizations WHERE status = 'active')
      AND organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid())
    )
    OR public.get_auth_platform_role() = 'super_admin'
  );

-- simulations
DROP POLICY IF EXISTS "Users view own simulations" ON simulations;
CREATE POLICY "Users view own simulations (org active)" ON simulations
  FOR ALL USING (
    idea_id IN (SELECT id FROM ideas WHERE user_id = auth.uid())
    OR (
      organization_id IS NOT NULL
      AND organization_id IN (SELECT id FROM organizations WHERE status = 'active')
      AND organization_id IN (SELECT organization_id FROM organization_members WHERE user_id = auth.uid())
    )
    OR public.get_auth_platform_role() = 'super_admin'
  );

-- agent_activities
DROP POLICY IF EXISTS "Users view own activities" ON agent_activities;
CREATE POLICY "Users view own activities (org active)" ON agent_activities
  FOR ALL USING (
    idea_id IN (SELECT id FROM ideas WHERE user_id = auth.uid())
    OR (
      organization_id IS NOT NULL
      AND organization_id IN (SELECT id FROM organizations WHERE status = 'active')
      AND public.get_auth_user_org_role(organization_id) IS NOT NULL
    )
    OR public.get_auth_platform_role() = 'super_admin'
  );


-- 3. Server-side provisioning function
CREATE OR REPLACE FUNCTION public.create_organization_from_request(
  req_id UUID,
  approver_id UUID
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  r RECORD;
  new_org_id UUID := gen_random_uuid();
  approver_role TEXT;
BEGIN
  SELECT platform_role INTO approver_role FROM profiles WHERE id = approver_id;
  IF approver_role IS NULL OR approver_role <> 'super_admin' THEN
    RAISE EXCEPTION 'Only super_admin may provision enterprise organizations';
  END IF;

  SELECT * INTO r FROM enterprise_requests WHERE id = req_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Enterprise request not found';
  END IF;
  IF r.status NOT IN ('paid','pending_payment') THEN
    RAISE EXCEPTION 'Enterprise request not paid or pending payment';
  END IF;

  INSERT INTO organizations (
    id, name, slug, plan, owner_id, max_members, subscription_status, stripe_customer_id, stripe_subscription_id, billing_email, created_at, updated_at, status
  ) VALUES (
    new_org_id,
    r.company_name,
    substring(lower(regexp_replace(r.company_name, '[^a-z0-9]+', '-', 'g')) from 1 for 50),
    'enterprise',
    NULL,
    COALESCE(r.required_seats, 10),
    'active',
    NULL,
    NULL,
    r.contact_email,
    now(), now(), 'active'
  );

  -- Mark enterprise request as approved
  UPDATE enterprise_requests SET status = 'approved', updated_at = now() WHERE id = req_id;

  RETURN new_org_id;
END;
$$;

-- Grant execute to authenticated (service-role uses RPC via service key); keep restricted
GRANT EXECUTE ON FUNCTION public.create_organization_from_request(uuid, uuid) TO authenticated;
