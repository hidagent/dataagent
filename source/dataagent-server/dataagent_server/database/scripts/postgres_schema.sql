-- DataAgent Server PostgreSQL Schema
-- All system tables use s_ prefix
-- All relationship tables use _rel suffix

-- Schema version tracking
CREATE TABLE IF NOT EXISTS s_schema_version (
    id SERIAL PRIMARY KEY,
    version VARCHAR(32) UNIQUE NOT NULL,
    description VARCHAR(256),
    checksum VARCHAR(64),
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_by VARCHAR(64)
);

-- User account table
CREATE TABLE IF NOT EXISTS s_user (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) UNIQUE NOT NULL,
    username VARCHAR(64) UNIQUE NOT NULL,
    user_account VARCHAR(128), -- Domain account (LDAP/AD)
    user_source VARCHAR(32) NOT NULL DEFAULT 'local', -- local, ldap, oauth, sso
    display_name VARCHAR(128) NOT NULL,
    email VARCHAR(256),
    password_hash VARCHAR(256),
    department VARCHAR(128),
    role VARCHAR(64),
    status VARCHAR(32) DEFAULT 'active', -- active, inactive, suspended
    custom_fields JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_s_user_user_id ON s_user(user_id);
CREATE INDEX IF NOT EXISTS ix_s_user_username ON s_user(username);

-- API key table
CREATE TABLE IF NOT EXISTS s_api_key (
    id SERIAL PRIMARY KEY,
    key_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL REFERENCES s_user(user_id) ON DELETE CASCADE,
    key_hash VARCHAR(256) NOT NULL,
    name VARCHAR(128),
    scopes JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_s_api_key_key_id ON s_api_key(key_id);
CREATE INDEX IF NOT EXISTS ix_s_api_key_user_id ON s_api_key(user_id);

-- Session table
CREATE TABLE IF NOT EXISTS s_session (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL REFERENCES s_user(user_id) ON DELETE CASCADE,
    assistant_id VARCHAR(64) NOT NULL,
    title VARCHAR(256),
    state JSONB,
    extra_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_s_session_session_id ON s_session(session_id);
CREATE INDEX IF NOT EXISTS ix_s_session_user_id ON s_session(user_id);

-- Message entity table
CREATE TABLE IF NOT EXISTS s_message (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(64) UNIQUE NOT NULL,
    role VARCHAR(32) NOT NULL, -- user, assistant, system, tool
    content TEXT NOT NULL,
    tool_calls JSONB,
    tool_call_id VARCHAR(64),
    extra_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_s_message_message_id ON s_message(message_id);

-- Session-Message relationship table
CREATE TABLE IF NOT EXISTS s_session_message_rel (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES s_session(session_id) ON DELETE CASCADE,
    message_id VARCHAR(64) NOT NULL REFERENCES s_message(message_id) ON DELETE CASCADE,
    sequence_number INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (session_id, message_id),
    UNIQUE (session_id, sequence_number)
);
CREATE INDEX IF NOT EXISTS ix_s_session_message_rel_session_id ON s_session_message_rel(session_id);

-- MCP server configuration table
CREATE TABLE IF NOT EXISTS s_mcp_server (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES s_user(user_id) ON DELETE CASCADE,
    server_name VARCHAR(128) NOT NULL,
    command VARCHAR(512),
    args JSONB,
    env JSONB,
    url VARCHAR(512),
    transport VARCHAR(32) DEFAULT 'stdio', -- stdio, sse, streamable_http
    headers JSONB,
    auto_approve JSONB,
    disabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, server_name)
);
CREATE INDEX IF NOT EXISTS ix_s_mcp_server_user_id ON s_mcp_server(user_id);

-- Workspace entity table
CREATE TABLE IF NOT EXISTS s_workspace (
    id SERIAL PRIMARY KEY,
    workspace_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    path VARCHAR(512) NOT NULL,
    description TEXT,
    max_size_bytes BIGINT DEFAULT 1073741824, -- 1GB
    max_files INT DEFAULT 10000,
    current_size_bytes BIGINT DEFAULT 0,
    current_file_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    settings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_s_workspace_workspace_id ON s_workspace(workspace_id);

-- User-Workspace relationship table
CREATE TABLE IF NOT EXISTS s_user_workspace_rel (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES s_user(user_id) ON DELETE CASCADE,
    workspace_id VARCHAR(64) NOT NULL REFERENCES s_workspace(workspace_id) ON DELETE CASCADE,
    is_default BOOLEAN DEFAULT FALSE,
    permission VARCHAR(32) DEFAULT 'read_write', -- read_only, read_write, admin
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, workspace_id)
);
CREATE INDEX IF NOT EXISTS ix_s_user_workspace_rel_user_id ON s_user_workspace_rel(user_id);

-- Rule table
CREATE TABLE IF NOT EXISTS s_rule (
    id SERIAL PRIMARY KEY,
    rule_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL REFERENCES s_user(user_id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    scope VARCHAR(32) DEFAULT 'user', -- global, user, project, session
    priority INT DEFAULT 50, -- 1-100
    is_active BOOLEAN DEFAULT TRUE,
    extra_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_s_rule_rule_id ON s_rule(rule_id);
CREATE INDEX IF NOT EXISTS ix_s_rule_user_id ON s_rule(user_id);

-- Skill table
CREATE TABLE IF NOT EXISTS s_skill (
    id SERIAL PRIMARY KEY,
    skill_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL REFERENCES s_user(user_id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    category VARCHAR(64),
    tags JSONB,
    usage_count INT DEFAULT 0,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    extra_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_s_skill_skill_id ON s_skill(skill_id);
CREATE INDEX IF NOT EXISTS ix_s_skill_user_id ON s_skill(user_id);

-- Audit log table
CREATE TABLE IF NOT EXISTS s_audit_log (
    id SERIAL PRIMARY KEY,
    log_id VARCHAR(64) UNIQUE NOT NULL,
    requesting_user_id VARCHAR(64),
    target_user_id VARCHAR(64),
    resource_type VARCHAR(64) NOT NULL, -- user, session, mcp_server, etc.
    resource_id VARCHAR(64),
    action VARCHAR(32) NOT NULL, -- create, read, update, delete
    result VARCHAR(32) NOT NULL, -- success, denied, error
    details JSONB,
    ip_address VARCHAR(64),
    user_agent VARCHAR(512),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_s_audit_log_log_id ON s_audit_log(log_id);
CREATE INDEX IF NOT EXISTS ix_s_audit_log_created_at ON s_audit_log(created_at);
CREATE INDEX IF NOT EXISTS ix_s_audit_log_requesting_user_id ON s_audit_log(requesting_user_id);

-- Insert initial schema version
INSERT INTO s_schema_version (version, description) 
VALUES ('V001', 'Initial schema with all system tables')
ON CONFLICT (version) DO NOTHING;

-- Create function for auto-updating updated_at
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
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_s_user_updated_at') THEN
        CREATE TRIGGER update_s_user_updated_at BEFORE UPDATE ON s_user
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_s_mcp_server_updated_at') THEN
        CREATE TRIGGER update_s_mcp_server_updated_at BEFORE UPDATE ON s_mcp_server
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_s_workspace_updated_at') THEN
        CREATE TRIGGER update_s_workspace_updated_at BEFORE UPDATE ON s_workspace
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_s_rule_updated_at') THEN
        CREATE TRIGGER update_s_rule_updated_at BEFORE UPDATE ON s_rule
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_s_skill_updated_at') THEN
        CREATE TRIGGER update_s_skill_updated_at BEFORE UPDATE ON s_skill
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;
