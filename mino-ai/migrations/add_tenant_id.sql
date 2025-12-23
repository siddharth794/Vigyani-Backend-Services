-- Migration script to add tenant_id column to users table
-- Run this script on your database to add the tenant_id column

-- Add tenant_id column if it doesn't exist
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS tenant_id INT NULL AFTER subscription;

-- Add index on tenant_id for better query performance
CREATE INDEX IF NOT EXISTS idx_tenant_id ON users(tenant_id);

-- Note: Existing users will have tenant_id = NULL
-- You may want to create tenants for existing users separately if needed

