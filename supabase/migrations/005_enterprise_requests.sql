-- ══════════════════════════════════════════════════════════════════
-- Migration 005: Enterprise Access Requests
-- Stores enterprise onboarding inquiries before they are manually 
-- approved and provisioned as full organizations.
-- ══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS enterprise_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    team_size TEXT,
    industry TEXT,
    use_case TEXT,
    required_seats INTEGER,
    compliance_requirements TEXT,
    white_label_needs BOOLEAN DEFAULT false,
    billing_preferences TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'under_review', 'approved', 'rejected')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security
ALTER TABLE enterprise_requests ENABLE ROW LEVEL SECURITY;

-- Anyone can insert a request (public endpoint)
CREATE POLICY "Anyone can submit enterprise requests" ON enterprise_requests
    FOR INSERT WITH CHECK (true);

-- Only super admins can view or update requests
CREATE POLICY "Super admins can manage enterprise requests" ON enterprise_requests
    FOR ALL USING (
        auth.uid() IN (
            SELECT id FROM profiles WHERE role = 'super_admin'
            -- We fallback to profiles if admin access is needed globally, 
            -- or we rely on a backend service role for admin dashboard viewing.
        )
    );
