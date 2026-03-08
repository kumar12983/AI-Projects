-- Migration: Add password reset token support to webapp.users
-- Run this against your PostgreSQL database before deploying the password reset feature

ALTER TABLE webapp.users
    ADD COLUMN IF NOT EXISTS reset_token      VARCHAR(64),
    ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP;

-- Index speeds up token lookups; partial index only covers rows with a token set
CREATE INDEX IF NOT EXISTS idx_users_reset_token
    ON webapp.users(reset_token)
    WHERE reset_token IS NOT NULL;
