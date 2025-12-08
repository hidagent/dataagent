-- DataAgent Server SQLite Schema
-- All system tables use s_ prefix
-- All relationship tables use _rel suffix

-- Schema version tracking
CREATE TABLE IF NOT EXISTS s_schema_version (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version VARCHAR(32) UNIQUE NOT NULL,
    description VARCHAR(256),
    checksum VARCHAR(64),
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_by VARCHAR(64)
);

-- User account table
CREATE TABLE IF NOT EXISTS s_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64) UNIQUE NOT NULL,
    username VARCHAR(64) UNIQUE NOT NULL,
    user_account VARCHAR(128),  -- Domain account (LDAP/AD)
    user_source VARCHAR(32) NOT NULL DEFAULT 'local',  -- local, ldap, oauth, sso
    display_name VARCHAR(128) NOT NULL,
    email VARCHAR(256),
    password_hash VARCHAR(256),
    department VARCHAR(128),
    role VARCHAR(64),
    status VARCHAR(32) DEFAULT 'active',  -- active, inactive, suspended
    custom_fields TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_s_user_user_id ON s_user(user_id);
CREATE INDEX IF NOT EXISTS ix_s_user_username ON s_user(username);

-- API key table
CREATE TABLE IF NOT EXISTS s_api_key (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL REFERENCES s_user(user_id) ON DELETE CASCADE,
    key_hash VARCHAR(256) NOT NULL,
    name VARCHAR(128),
    scopes TEXT,  -- JSON array
    is_active INTEGER DEFAULT 1,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_s_api_key_key_id ON s_api_key(key_id);
CREATE INDEX IF NOT EXISTS ix_s_api_key_user_id ON s_api_key(user_id);

-- Session table
CREATE TABLE IF NOT EXISTS s_session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL REFERENCES s_user(user_id) ON DELETE CASCADE,
    assistant_id VARCHAR(64) NOT NULL,
    title VARCHAR(256),
    state TEXT,  -- JSON
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_archived INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_s_session_session_id ON s_session(session_id);
CREATE INDEX IF NOT EXISTS ix_s_session_user_id ON s_session(user_id);

-- Message entity table
CREATE TABLE IF NOT EXISTS s_message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id VARCHAR(64) UNIQUE NOT NULL,
    role VARCHAR(32) NOT NULL,  -- user, assistant, system, tool
    content TEXT NOT NULL,
    tool_calls TEXT,  -- JSON
    tool_call_id VARCHAR(64),
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_s_message_message_id ON s_message(message_id);

-- Session-Message relationship table
CREATE TABLE IF NOT EXISTS s_session_message_rel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(64) NOT NULL REFERENCES s_session(session_id) ON DELETE CASCADE,
    message_id VARCHAR(64) NOT NULL REFERENCES s_message(message_id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, message_id),
    UNIQUE(session_id, sequence_number)
);

CREATE INDEX IF NOT EXISTS ix_s_session_message_rel_session_id ON s_session_message_rel(session_id);

-- MCP server configuration table
CREATE TABLE IF NOT EXISTS s_mcp_server (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64) NOT NULL REFERENCES s_user(user_id) ON DELETE CASCADE,
    server_name VARCHAR(128) NOT NULL,
    command VARCHAR(512),
    args TEXT,  -- JSON array
    env TEXT,  -- JSON
    url VARCHAR(512),
    transport VARCHAR(32) DEFAULT 'stdio',  -- stdio, sse, streamable_http
    headers TEXT,  -- JSON
    auto_approve TEXT,  -- JSON array
    disabled INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, server_name)
);

CREATE INDEX IF NOT EXISTS ix_s_mcp_server_user_id ON s_mcp_server(user_id);

-- Workspace entity table
CREATE TABLE IF NOT EXISTS s_workspace (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    path VARCHAR(512) NOT NULL,
    description TEXT,
    max_size_bytes BIGINT DEFAULT 1073741824,  -- 1GB
    max_files INTEGER DEFAULT 10000,
    current_size_bytes BIGINT DEFAULT 0,
    current_file_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    settings TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_s_workspace_workspace_id ON s_workspace(workspace_id);

-- User-Workspace relationship table
CREATE TABLE IF NOT EXISTS s_user_workspace_rel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64) NOT NULL REFERENCES s_user(user_id) ON DELETE CASCADE,
    workspace_id VARCHAR(64) NOT NULL REFERENCES s_workspace(workspace_id) ON DELETE CASCADE,
    is_default INTEGER DEFAULT 0,
    permission VARCHAR(32) DEFAULT 'read_write',  -- read_only, read_write, admin
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, workspace_id)
);

CREATE INDEX IF NOT EXISTS ix_s_user_workspace_rel_user_id ON s_user_workspace_rel(user_id);

-- Rule table
CREATE TABLE IF NOT EXISTS s_rule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL REFERENCES s_user(user_id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    scope VARCHAR(32) DEFAULT 'user',  -- global, user, project, session
    priority INTEGER DEFAULT 50,  -- 1-100
    is_active INTEGER DEFAULT 1,
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_s_rule_rule_id ON s_rule(rule_id);
CREATE INDEX IF NOT EXISTS ix_s_rule_user_id ON s_rule(user_id);

-- Skill table
CREATE TABLE IF NOT EXISTS s_skill (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL REFERENCES s_user(user_id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    category VARCHAR(64),
    tags TEXT,  -- JSON array
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_s_skill_skill_id ON s_skill(skill_id);
CREATE INDEX IF NOT EXISTS ix_s_skill_user_id ON s_skill(user_id);

-- Audit log table
CREATE TABLE IF NOT EXISTS s_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id VARCHAR(64) UNIQUE NOT NULL,
    requesting_user_id VARCHAR(64),
    target_user_id VARCHAR(64),
    resource_type VARCHAR(64) NOT NULL,  -- user, session, mcp_server, etc.
    resource_id VARCHAR(64),
    action VARCHAR(32) NOT NULL,  -- create, read, update, delete
    result VARCHAR(32) NOT NULL,  -- success, denied, error
    details TEXT,  -- JSON
    ip_address VARCHAR(64),
    user_agent VARCHAR(512),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_s_audit_log_log_id ON s_audit_log(log_id);
CREATE INDEX IF NOT EXISTS ix_s_audit_log_created_at ON s_audit_log(created_at);
CREATE INDEX IF NOT EXISTS ix_s_audit_log_requesting_user_id ON s_audit_log(requesting_user_id);

-- Insert initial schema version
INSERT OR IGNORE INTO s_schema_version (version, description) 
VALUES ('V001', 'Initial schema with all system tables');
