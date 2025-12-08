-- =============================================================================
-- DataAgent Multi-Tenant Database Schema - PostgreSQL Version
-- =============================================================================
-- 
-- This script creates all tables for the DataAgent multi-tenant system.
-- Compatible with PostgreSQL 15+
--
-- Tables:
--   - schema_versions: Migration version tracking
--   - users: User accounts and profiles
--   - api_keys: API authentication keys
--   - sessions: Chat sessions
--   - messages: Chat messages
--   - mcp_servers: MCP server configurations
--   - workspaces: User workspace metadata
--   - rules: User-specific rules
--   - skills: User-specific skills
--   - audit_logs: Security audit logs
--
-- Usage:
--   psql -U postgres -d dataagent -f postgres_schema.sql
--
-- =============================================================================

-- =============================================================================
-- Schema Version Tracking
-- =============================================================================

CREATE TABLE IF NOT EXISTS schema_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(32) UNIQUE NOT NULL,
    description TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64)
);

-- =============================================================================
-- User Management Tables
-- =============================================================================

-- Users table: Core user accounts
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) UNIQUE NOT NULL,
    username VARCHAR(64) UNIQUE NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    email VARCHAR(256),
    password_hash VARCHAR(256),
    department VARCHAR(128),
    role VARCHAR(64),
    status VARCHAR(32) DEFAULT 'active' NOT NULL CHECK (status IN ('active', 'inactive', 'suspended')),
    custom_fields JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_department ON users(department);

COMMENT ON TABLE users IS 'User accounts and profiles for multi-tenant system';

-- API Keys table: Authentication tokens
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    key_hash VARCHAR(256) NOT NULL,
    name VARCHAR(128) NOT NULL,
    scopes JSONB, -- Array of allowed scopes/permissions
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key_id ON api_keys(key_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON api_keys(expires_at);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);

COMMENT ON TABLE api_keys IS 'API authentication keys for users';

-- =============================================================================
-- Session Management Tables
-- =============================================================================

-- Sessions table: Chat sessions
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    assistant_id VARCHAR(64) NOT NULL,
    title VARCHAR(256),
    state JSONB, -- Session state data
    metadata JSONB, -- Additional session metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_archived BOOLEAN DEFAULT FALSE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_assistant_id ON sessions(assistant_id);
CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active);
CREATE INDEX IF NOT EXISTS idx_sessions_user_assistant ON sessions(user_id, assistant_id);
CREATE INDEX IF NOT EXISTS idx_sessions_archived ON sessions(is_archived);

COMMENT ON TABLE sessions IS 'User chat sessions';

-- Messages table: Chat messages
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    tool_calls JSONB, -- Tool call requests from assistant
    tool_call_id VARCHAR(64), -- ID for tool response messages
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_message_id ON messages(message_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

COMMENT ON TABLE messages IS 'Chat messages within sessions';

-- =============================================================================
-- MCP Configuration Tables
-- =============================================================================

-- MCP Servers table: MCP server configurations per user
CREATE TABLE IF NOT EXISTS mcp_servers (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    server_name VARCHAR(128) NOT NULL,
    command VARCHAR(512), -- Command for stdio transport
    args JSONB, -- Command arguments array
    env JSONB, -- Environment variables object
    url VARCHAR(512), -- URL for SSE/HTTP transport
    transport VARCHAR(32) DEFAULT 'stdio' NOT NULL,
    headers JSONB, -- HTTP headers for HTTP transport
    disabled BOOLEAN DEFAULT FALSE NOT NULL,
    auto_approve JSONB, -- Auto-approved tools array
    timeout_seconds INT DEFAULT 30 NOT NULL,
    max_retries INT DEFAULT 3 NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (user_id, server_name)
);

CREATE INDEX IF NOT EXISTS idx_mcp_servers_user_id ON mcp_servers(user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_disabled ON mcp_servers(disabled);

COMMENT ON TABLE mcp_servers IS 'MCP server configurations per user';

-- =============================================================================
-- Workspace Tables
-- =============================================================================

-- Workspaces table: User workspace metadata
CREATE TABLE IF NOT EXISTS workspaces (
    id SERIAL PRIMARY KEY,
    workspace_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    path VARCHAR(512) NOT NULL, -- Filesystem path
    max_size_bytes BIGINT DEFAULT 1073741824 NOT NULL, -- 1GB default
    max_files INT DEFAULT 10000 NOT NULL,
    current_size_bytes BIGINT DEFAULT 0 NOT NULL,
    current_file_count INT DEFAULT 0 NOT NULL,
    is_default BOOLEAN DEFAULT FALSE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    description TEXT,
    settings JSONB, -- Workspace-specific settings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_accessed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workspaces_workspace_id ON workspaces(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_user_id ON workspaces(user_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_user_default ON workspaces(user_id, is_default);
CREATE INDEX IF NOT EXISTS idx_workspaces_active ON workspaces(is_active);

COMMENT ON TABLE workspaces IS 'User workspace metadata';

-- =============================================================================
-- Rules Tables
-- =============================================================================

-- Rules table: User-specific rules
CREATE TABLE IF NOT EXISTS rules (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    rule_name VARCHAR(128) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    scope VARCHAR(32) DEFAULT 'user' NOT NULL CHECK (scope IN ('global', 'user', 'project', 'session')),
    inclusion VARCHAR(32) DEFAULT 'always' NOT NULL CHECK (inclusion IN ('always', 'fileMatch', 'manual')),
    file_match_pattern VARCHAR(256),
    priority INT DEFAULT 50 NOT NULL CHECK (priority >= 1 AND priority <= 100),
    override BOOLEAN DEFAULT FALSE NOT NULL,
    enabled BOOLEAN DEFAULT TRUE NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (user_id, rule_name)
);

CREATE INDEX IF NOT EXISTS idx_rules_user_id ON rules(user_id);
CREATE INDEX IF NOT EXISTS idx_rules_scope ON rules(scope);
CREATE INDEX IF NOT EXISTS idx_rules_enabled ON rules(enabled);
CREATE INDEX IF NOT EXISTS idx_rules_priority ON rules(priority);

COMMENT ON TABLE rules IS 'User-specific rules for agent behavior';

-- =============================================================================
-- Skills Tables
-- =============================================================================

-- Skills table: User-specific skills
CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    skill_name VARCHAR(128) NOT NULL,
    description TEXT,
    content TEXT NOT NULL, -- Skill definition/prompt
    category VARCHAR(64),
    tags JSONB, -- Array of tags
    parameters JSONB, -- Input parameters JSON schema
    enabled BOOLEAN DEFAULT TRUE NOT NULL,
    usage_count INT DEFAULT 0 NOT NULL,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (user_id, skill_name)
);

CREATE INDEX IF NOT EXISTS idx_skills_user_id ON skills(user_id);
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category);
CREATE INDEX IF NOT EXISTS idx_skills_enabled ON skills(enabled);
CREATE INDEX IF NOT EXISTS idx_skills_usage ON skills(usage_count);

COMMENT ON TABLE skills IS 'User-specific reusable skills';

-- =============================================================================
-- Audit Log Tables
-- =============================================================================

-- Audit Logs table: Security audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    requesting_user_id VARCHAR(64) NOT NULL,
    target_user_id VARCHAR(64),
    resource_type VARCHAR(32) NOT NULL CHECK (resource_type IN ('user', 'session', 'message', 'mcp', 'workspace', 'rule', 'skill', 'api_key')),
    resource_id VARCHAR(128),
    action VARCHAR(32) NOT NULL CHECK (action IN ('create', 'read', 'update', 'delete', 'execute', 'login', 'logout')),
    result VARCHAR(32) NOT NULL CHECK (result IN ('success', 'failure', 'denied')),
    ip_address VARCHAR(45), -- IPv6 compatible
    user_agent VARCHAR(512),
    session_id VARCHAR(64),
    request_id VARCHAR(64),
    details JSONB,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_requesting_user ON audit_logs(requesting_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_target_user ON audit_logs(target_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_result ON audit_logs(result);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp_user ON audit_logs(timestamp, requesting_user_id);

COMMENT ON TABLE audit_logs IS 'Security audit logs for compliance';

-- =============================================================================
-- Initial Schema Version Record
-- =============================================================================

INSERT INTO schema_versions (version, description) 
VALUES ('005', 'Complete multi-tenant schema')
ON CONFLICT (version) DO NOTHING;

-- =============================================================================
-- Views for Common Queries
-- =============================================================================

-- Active users view
CREATE OR REPLACE VIEW v_active_users AS
SELECT 
    u.user_id,
    u.username,
    u.display_name,
    u.department,
    u.role,
    u.created_at,
    u.last_login_at,
    COUNT(DISTINCT s.session_id) AS session_count,
    COUNT(DISTINCT m.server_name) AS mcp_server_count
FROM users u
LEFT JOIN sessions s ON u.user_id = s.user_id AND s.is_archived = FALSE
LEFT JOIN mcp_servers m ON u.user_id = m.user_id AND m.disabled = FALSE
WHERE u.status = 'active'
GROUP BY u.user_id, u.username, u.display_name, u.department, u.role, u.created_at, u.last_login_at;

-- User session summary view
CREATE OR REPLACE VIEW v_user_sessions AS
SELECT 
    s.session_id,
    s.user_id,
    s.assistant_id,
    s.title,
    s.created_at,
    s.last_active,
    s.is_archived,
    COUNT(m.id) AS message_count,
    MAX(m.created_at) AS last_message_at
FROM sessions s
LEFT JOIN messages m ON s.session_id = m.session_id
GROUP BY s.session_id, s.user_id, s.assistant_id, s.title, s.created_at, s.last_active, s.is_archived;

-- =============================================================================
-- Functions and Triggers for updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_users_updated_at') THEN
        CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_sessions_updated_at') THEN
        CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_mcp_servers_updated_at') THEN
        CREATE TRIGGER update_mcp_servers_updated_at BEFORE UPDATE ON mcp_servers
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_workspaces_updated_at') THEN
        CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON workspaces
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_rules_updated_at') THEN
        CREATE TRIGGER update_rules_updated_at BEFORE UPDATE ON rules
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_skills_updated_at') THEN
        CREATE TRIGGER update_skills_updated_at BEFORE UPDATE ON skills
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- =============================================================================
-- Stored Functions
-- =============================================================================

-- Function to clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions(p_timeout_hours INT)
RETURNS INT AS $$
DECLARE
    v_cutoff TIMESTAMP;
    v_count INT;
BEGIN
    v_cutoff := NOW() - (p_timeout_hours || ' hours')::INTERVAL;
    
    -- Archive old sessions instead of deleting
    UPDATE sessions 
    SET is_archived = TRUE 
    WHERE last_active < v_cutoff AND is_archived = FALSE;
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get user statistics
CREATE OR REPLACE FUNCTION get_user_stats(p_user_id VARCHAR(64))
RETURNS TABLE (
    total_sessions BIGINT,
    active_sessions BIGINT,
    total_messages BIGINT,
    mcp_servers BIGINT,
    workspaces BIGINT,
    active_rules BIGINT,
    active_skills BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM sessions WHERE user_id = p_user_id),
        (SELECT COUNT(*) FROM sessions WHERE user_id = p_user_id AND is_archived = FALSE),
        (SELECT COUNT(*) FROM messages m JOIN sessions s ON m.session_id = s.session_id WHERE s.user_id = p_user_id),
        (SELECT COUNT(*) FROM mcp_servers WHERE user_id = p_user_id),
        (SELECT COUNT(*) FROM workspaces WHERE user_id = p_user_id),
        (SELECT COUNT(*) FROM rules WHERE user_id = p_user_id AND enabled = TRUE),
        (SELECT COUNT(*) FROM skills WHERE user_id = p_user_id AND enabled = TRUE);
END;
$$ LANGUAGE plpgsql;
