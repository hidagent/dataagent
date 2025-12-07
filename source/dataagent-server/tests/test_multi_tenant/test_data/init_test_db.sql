-- Multi-Tenant Isolation Test Database Initialization
-- This script creates test data for verifying user isolation

-- =============================================================================
-- Test Users Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS test_users (
    user_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    department TEXT,
    role TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR REPLACE INTO test_users (user_id, display_name, department, role) VALUES
    ('test_alice', 'Alice Test', 'Engineering', 'Developer'),
    ('test_bob', 'Bob Test', 'Sales', 'Analyst');

-- =============================================================================
-- Alice's Data Tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS alice_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    secret_marker TEXT NOT NULL,
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR REPLACE INTO alice_data (id, content, secret_marker, category) VALUES
    (1, 'Alice project report Q4 2024', 'ALICE_DB_SECRET_GHI012_001', 'report'),
    (2, 'Alice code review notes for PR #123', 'ALICE_DB_SECRET_GHI012_002', 'review'),
    (3, 'Alice architecture design document', 'ALICE_DB_SECRET_GHI012_003', 'design'),
    (4, 'Alice performance optimization plan', 'ALICE_DB_SECRET_GHI012_004', 'plan'),
    (5, 'Alice team meeting notes', 'ALICE_DB_SECRET_GHI012_005', 'notes');

-- =============================================================================
-- Bob's Data Tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS bob_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    secret_marker TEXT NOT NULL,
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR REPLACE INTO bob_data (id, content, secret_marker, category) VALUES
    (1, 'Bob sales forecast 2024 Q4', 'BOB_DB_SECRET_VWX567_001', 'forecast'),
    (2, 'Bob customer analysis report', 'BOB_DB_SECRET_VWX567_002', 'analysis'),
    (3, 'Bob revenue report monthly', 'BOB_DB_SECRET_VWX567_003', 'report'),
    (4, 'Bob lead generation strategy', 'BOB_DB_SECRET_VWX567_004', 'strategy'),
    (5, 'Bob client meeting summary', 'BOB_DB_SECRET_VWX567_005', 'summary');

-- =============================================================================
-- MCP Server Configurations
-- =============================================================================

CREATE TABLE IF NOT EXISTS mcp_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    server_name TEXT NOT NULL,
    config_json TEXT NOT NULL,
    disabled INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, server_name)
);

INSERT OR REPLACE INTO mcp_configs (user_id, server_name, config_json) VALUES
    ('test_alice', 'alice-database', '{"type": "sqlite", "path": "alice.db", "user": "test_alice"}'),
    ('test_alice', 'alice-api', '{"type": "http", "url": "http://localhost:9001/alice", "user": "test_alice"}'),
    ('test_bob', 'bob-database', '{"type": "sqlite", "path": "bob.db", "user": "test_bob"}'),
    ('test_bob', 'bob-api', '{"type": "http", "url": "http://localhost:9002/bob", "user": "test_bob"}');

-- =============================================================================
-- Rules Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    rule_content TEXT NOT NULL,
    scope TEXT DEFAULT 'user',
    inclusion TEXT DEFAULT 'always',
    priority INTEGER DEFAULT 50,
    enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, rule_name)
);

INSERT OR REPLACE INTO rules (user_id, rule_name, rule_content, scope, priority) VALUES
    ('test_alice', 'alice-main-rule', 'Alice main rule content with ALICE_RULE_MARKER_ABC456', 'user', 90),
    ('test_alice', 'alice-coding-rule', 'Alice coding standards with ALICE_RULE_MARKER_ABC456_CODING', 'user', 80),
    ('test_alice', 'alice-review-rule', 'Alice code review guidelines with ALICE_RULE_MARKER_ABC456_REVIEW', 'user', 70),
    ('test_bob', 'bob-main-rule', 'Bob main rule content with BOB_RULE_MARKER_PQR901', 'user', 90),
    ('test_bob', 'bob-sales-rule', 'Bob sales guidelines with BOB_RULE_MARKER_PQR901_SALES', 'user', 80),
    ('test_bob', 'bob-crm-rule', 'Bob CRM procedures with BOB_RULE_MARKER_PQR901_CRM', 'user', 70);

-- =============================================================================
-- Security Audit Log Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS security_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    requesting_user TEXT NOT NULL,
    target_user TEXT NOT NULL,
    resource_type TEXT NOT NULL,  -- mcp, rule, file, skill, memory
    resource_id TEXT NOT NULL,
    action TEXT NOT NULL,         -- read, write, delete, execute, list
    result TEXT NOT NULL,         -- allowed, denied
    details TEXT,                 -- JSON details
    session_id TEXT,
    request_id TEXT
);

-- Create index for efficient querying
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON security_audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_requesting_user ON security_audit_log(requesting_user);
CREATE INDEX IF NOT EXISTS idx_audit_target_user ON security_audit_log(target_user);
CREATE INDEX IF NOT EXISTS idx_audit_resource_type ON security_audit_log(resource_type);

-- =============================================================================
-- Skills Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    skill_content TEXT NOT NULL,
    description TEXT,
    enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, skill_name)
);

INSERT OR REPLACE INTO skills (user_id, skill_name, skill_content, description) VALUES
    ('test_alice', 'alice-report-skill', 'Generate engineering reports with ALICE_SKILL_MARKER_JKL345', 'Engineering report generator'),
    ('test_alice', 'alice-analysis-skill', 'Code analysis tool with ALICE_SKILL_MARKER_JKL345_ANALYSIS', 'Code analysis'),
    ('test_bob', 'bob-sales-skill', 'Generate sales reports with BOB_SKILL_MARKER_YZA890', 'Sales report generator'),
    ('test_bob', 'bob-forecast-skill', 'Sales forecasting tool with BOB_SKILL_MARKER_YZA890_FORECAST', 'Sales forecasting');

-- =============================================================================
-- Verification Queries (for testing)
-- =============================================================================

-- Verify Alice's data isolation
-- SELECT * FROM alice_data WHERE secret_marker LIKE '%BOB%';  -- Should return 0 rows

-- Verify Bob's data isolation
-- SELECT * FROM bob_data WHERE secret_marker LIKE '%ALICE%';  -- Should return 0 rows

-- Verify MCP config isolation
-- SELECT * FROM mcp_configs WHERE user_id = 'test_alice' AND server_name LIKE '%bob%';  -- Should return 0 rows

-- Verify rules isolation
-- SELECT * FROM rules WHERE user_id = 'test_alice' AND rule_content LIKE '%BOB%';  -- Should return 0 rows
