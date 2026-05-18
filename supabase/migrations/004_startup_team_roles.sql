-- ══════════════════════════════════════════════════════════════════
-- Migration 004: Startup Team Roles Expansion
-- Expands the RBAC roles to include startup-specific operational roles
-- ══════════════════════════════════════════════════════════════════

-- Drop the existing role constraint from organization_members
ALTER TABLE organization_members DROP CONSTRAINT IF EXISTS organization_members_role_check;

-- Add the new expanded role constraint
ALTER TABLE organization_members ADD CONSTRAINT organization_members_role_check 
CHECK (role IN (
    'super_admin',
    'admin',
    'incubator_manager',
    'innovation_lead',
    'investor_advisor',
    'founder',
    'founder_product_lead',
    'fullstack_engineer',
    'ai_engineer',
    'backend_engineer',
    'devops_engineer',
    'ui_ux_designer',
    'security_consultant',
    'growth_marketing_lead',
    'team_member',
    'viewer'
));

-- Note: 'profiles' table uses a generic text field without a constraint, 
-- but if we added one in the future, this is where we would update it.
