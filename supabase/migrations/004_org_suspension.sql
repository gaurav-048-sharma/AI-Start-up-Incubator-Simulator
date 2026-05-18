-- Add status column to organizations table
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active';

-- Create an index for faster lookups since we'll check this on many requests
CREATE INDEX IF NOT EXISTS idx_organizations_status ON organizations(status);
