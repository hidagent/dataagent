-- =============================================================================
-- DataAgent Multi-Tenant Database Schema - SQLite3 Version
-- =============================================================================
-- 
-- This script creates all tables for the DataAgent multi-tenant system.
-- Compatible with SQLite 3.x
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
--   sqlite3 dataagent.db < sqlite_schema.sql
--
-- =============================================================================

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- =============================================================================
-- Schema Version Tracking
-- =============================================================================

CREATE TABLE IF NOT EXISTS schema_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT,
    password_hash TEXT,
    department TEXT,
    role TEXT,
    status TEXT DEFAULT 'active' NOT NULL CHECK (status IN ('active', 'inactive', 'suspended')),
    custom_fields TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_department ON users(department);

-- API Keys table: Authentication tokens
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    scopes TEXT,  -- JSON array of allowed scopes
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active INTEGER DEFAULT 1 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key_id ON api_keys(key_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON api_keys(expires_at);

-- =============================================================================
-- Session Management Tables
-- =============================================================================

-- Sessions table: Chat sessions
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    assistant_id TEXT NOT NULL,
    title TEXT,
    state TEXT,  -- JSON
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_archived INTEGER DEFAULT 0 NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_assistant_id ON sessions(assistant_id);
CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active);
CREATE INDEX IF NOT EXISTS idx_sessions_user_assistant ON sessions(user_id, assistant_id);

-- Messages table: Chat messages
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    tool_calls TEXT,  -- JSON
    tool_call_id TEXT,
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_message_id ON messages(message_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- =============================================================================
-- MCP Configuration Tables
-- =============================================================================

-- MCP Servers table: MCP server configurations per user
CREATE TABLE IF NOT EXISTS mcp_servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    server_name TEXT NOT NULL,
    command TEXT,
    args TEXT,  -- JSON array
    env TEXT,  -- JSON object
    url TEXT,
    transport TEXT DEFAULT 'stdio' NOT NULL,
    headers TEXT,  -- JSON object
    disabled INTEGER DEFAULT 0 NOT NULL,
    auto_approve TEXT,  -- JSON array
    timeout_seconds INTEGER DEFAULT 30 NOT NULL,
    max_retries INTEGER DEFAULT 3 NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE(user_id, server_name)
);

CREATE INDEX IF NOT EXISTS idx_mcp_servers_user_id ON mcp_servers(user_id);

-- =============================================================================
-- Workspace Tables
-- =============================================================================

-- Workspaces table: User workspace metadata
CREATE TABLE IF NOT EXISTS workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    max_size_bytes INTEGER DEFAULT 1073741824 NOT NULL,  -- 1GB
    max_files INTEGER DEFAULT 10000 NOT NULL,
    current_size_bytes INTEGER DEFAULT 0 NOT NULL,
    current_file_count INTEGER DEFAULT 0 NOT NULL,
    is_default INTEGER DEFAULT 0 NOT NULL,
    is_active INTEGER DEFAULT 1 NOT NULL,
    description TEXT,
    settings TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_accessed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workspaces_workspace_id ON workspaces(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_user_id ON workspaces(user_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_user_default ON workspaces(user_id, is_default);

-- =============================================================================
-- Rules Tables
-- =============================================================================

-- Rules table: User-specific rules
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    rule_name TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    scope TEXT DEFAULT 'user' NOT NULL CHECK (scope IN ('global', 'user', 'project', 'session')),
    inclusion TEXT DEFAULT 'always' NOT NULL CHECK (inclusion IN ('always', 'fileMatch', 'manual')),
    file_match_pattern TEXT,
    priority INTEGER DEFAULT 50 NOT NULL CHECK (priority >= 1 AND priority <= 100),
    override INTEGER DEFAULT 0 NOT NULL,
    enabled INTEGER DEFAULT 1 NOT NULL,
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE(user_id, rule_name)
);

CREATE INDEX IF NOT EXISTS idx_rules_user_id ON rules(user_id);
CREATE INDEX IF NOT EXISTS idx_rules_scope ON rules(scope);
CREATE INDEX IF NOT EXISTS idx_rules_enabled ON rules(enabled);

-- =============================================================================
-- Skills Tables
-- =============================================================================

-- Skills table: User-specific skills
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    category TEXT,
    tags TEXT,  -- JSON array
    parameters TEXT,  -- JSON schema
    enabled INTEGER DEFAULT 1 NOT NULL,
    usage_count INTEGER DEFAULT 0 NOT NULL,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE(user_id, skill_name)
);

CREATE INDEX IF NOT EXISTS idx_skills_user_id ON skills(user_id);
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category);
CREATE INDEX IF NOT EXISTS idx_skills_enabled ON skills(enabled);

-- =============================================================================
-- Audit Log Tables
-- =============================================================================

-- Audit Logs table: Security audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    requesting_user_id TEXT NOT NULL,
    target_user_id TEXT,
    resource_type TEXT NOT NULL CHECK (resource_type IN ('user', 'session', 'message', 'mcp', 'workspace', 'rule', 'skill', 'api_key')),
    resource_id TEXT,
    action TEXT NOT NULL CHECK (action IN ('create', 'read', 'update', 'delete', 'execute', 'login', 'logout')),
    result TEXT NOT NULL CHECK (result IN ('success', 'failure', 'denied')),
    ip_address TEXT,
    user_agent TEXT,
    session_id TEXT,
    request_id TEXT,
    details TEXT,  -- JSON
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_requesting_user ON audit_logs(requesting_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_target_user ON audit_logs(target_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_result ON audit_logs(result);

-- =============================================================================
-- Initial Schema Version Record
-- =============================================================================

INSERT OR IGNORE INTO schema_versions (version, description) 
VALUES ('005', 'Complete multi-tenant schema');

-- =============================================================================
-- Triggers for updated_at
-- =============================================================================

CREATE TRIGGER IF NOT EXISTS users_updated_at 
AFTER UPDATE ON users
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS sessions_updated_at 
AFTER UPDATE ON sessions
BEGIN
    UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS mcp_servers_updated_at 
AFTER UPDATE ON mcp_servers
BEGIN
    UPDATE mcp_servers SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS workspaces_updated_at 
AFTER UPDATE ON workspaces
BEGIN
    UPDATE workspaces SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS rules_updated_at 
AFTER UPDATE ON rules
BEGIN
    UPDATE rules SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS skills_updated_at 
AFTER UPDATE ON skills
BEGIN
    UPDATE skills SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
