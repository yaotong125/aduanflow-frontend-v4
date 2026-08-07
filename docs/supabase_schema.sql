-- ==============================================================================
-- AduanFlow Supabase PostgreSQL Database Schema
-- ==============================================================================
-- 
-- Instructions:
-- 1. Open your Supabase Project Dashboard.
-- 2. Navigate to the "SQL Editor" on the left sidebar.
-- 3. Create a new query, paste the contents of this file, and click "RUN".
-- 
-- This schema accurately matches the SQLModel schema defined in the codebase.
-- ==============================================================================

-- 1. Table: dispute_cases
CREATE TABLE IF NOT EXISTS dispute_cases (
    id VARCHAR NOT NULL,
    customer_name VARCHAR NOT NULL,
    customer_email VARCHAR NOT NULL,
    masked_account VARCHAR NOT NULL,
    masked_card VARCHAR,
    category VARCHAR NOT NULL,
    urgency VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    verification_result VARCHAR,
    amount DOUBLE PRECISION NOT NULL,
    assigned_to VARCHAR,
    received_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    due_date TIMESTAMP WITHOUT TIME ZONE,
    processing_time VARCHAR,
    email_subject VARCHAR,
    email_body VARCHAR,
    nric_encrypted VARCHAR,
    account_number_encrypted VARCHAR,
    card_number_encrypted VARCHAR,
    dispute_amount_encrypted VARCHAR,
    ocr_results JSON,
    classification JSON,
    verification JSON,
    financial_resolution JSON,
    communication JSON,
    audit_log JSON,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_dispute_cases_customer_name ON dispute_cases (customer_name);
CREATE INDEX IF NOT EXISTS ix_dispute_cases_category ON dispute_cases (category);
CREATE INDEX IF NOT EXISTS ix_dispute_cases_status ON dispute_cases (status);

-- 2. Table: audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR NOT NULL,
    case_id VARCHAR NOT NULL,
    actor VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    detail VARCHAR,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_case_id ON audit_logs (case_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_actor ON audit_logs (actor);

-- 3. Table: system_settings
CREATE TABLE IF NOT EXISTS system_settings (
    id VARCHAR NOT NULL,
    gmail_email VARCHAR,
    gmail_refresh_token_encrypted VARCHAR,
    is_gmail_connected BOOLEAN NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);

-- 4. Table: users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL NOT NULL,
    email VARCHAR NOT NULL,
    full_name VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    department VARCHAR NOT NULL,
    is_active BOOLEAN NOT NULL,
    hashed_password VARCHAR NOT NULL,
    email_enabled BOOLEAN NOT NULL,
    quiet_hours BOOLEAN NOT NULL,
    notif_case_assigned BOOLEAN NOT NULL,
    notif_status_changed BOOLEAN NOT NULL,
    notif_sla_breach BOOLEAN NOT NULL,
    notif_manual_review BOOLEAN NOT NULL,
    notif_weekly_digest BOOLEAN NOT NULL,
    sec_2fa BOOLEAN NOT NULL,
    sec_password_expiry BOOLEAN NOT NULL,
    sec_ip_allowlist BOOLEAN NOT NULL,
    sec_new_device_alert BOOLEAN NOT NULL,
    sec_session_timeout VARCHAR NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

-- 5. Default Users Seed
CREATE EXTENSION IF NOT EXISTS pgcrypto;

INSERT INTO users (
  email, 
  full_name, 
  role, 
  department, 
  is_active, 
  hashed_password,
  email_enabled, quiet_hours, notif_case_assigned, notif_status_changed,
  notif_sla_breach, notif_manual_review, notif_weekly_digest,
  sec_2fa, sec_password_expiry, sec_ip_allowlist, sec_new_device_alert,
  sec_session_timeout, created_at, updated_at
) VALUES 
(
  'admin@aduanflow.com', 
  'System Administrator', 
  'admin', 
  'Dispute Resolution Taskforce', 
  true, 
  encode(digest('admin123', 'sha256'), 'hex'), 
  true, false, true, true, true, false, true, false, false, false, true, '30', NOW(), NOW()
),
(
  'investigator@aduanflow.com', 
  'Senior Investigator', 
  'investigator', 
  'Dispute Resolution Taskforce', 
  true, 
  encode(digest('invest123', 'sha256'), 'hex'), 
  true, false, true, true, true, false, true, false, false, false, true, '30', NOW(), NOW()
) ON CONFLICT (email) DO NOTHING;
