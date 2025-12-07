# Subagent 工作目录隔离需求文档

## 问题描述

当前 subagent 在执行文件系统操作时存在安全风险：

1. **路径检索从根目录开始** - subagent 使用 `ls("/")` 从系统根目录开始检索，而不是从用户当前工作目录开始
2. **工作目录上下文丢失** - 主 agent 的工作目录信息没有正确传递给 subagent
3. **安全风险** - subagent 可能访问用户工作目录以外的敏感文件

## 需求

### Requirement 1: 工作目录上下文传递

**User Story:** As a developer, I want subagents to inherit the main agent's working directory context, so that file operations are scoped correctly.

#### Acceptance Criteria

1. WHEN a subagent is created THEN it SHALL inherit the main agent's working directory from state
2. WHEN the working directory is passed to subagent THEN it SHALL be stored in subagent's state
3. WHEN subagent executes file tools THEN it SHALL use the inherited working directory as base path
4. WHEN working directory is not set THEN the system SHALL default to current working directory (cwd)

### Requirement 2: 路径限制

**User Story:** As a security engineer, I want file operations to be restricted to the user's workspace, so that sensitive system files cannot be accessed.

#### Acceptance Criteria

1. WHEN ls tool is called without path THEN it SHALL default to working directory, not "/"
2. WHEN glob tool is called without path THEN it SHALL default to working directory, not "/"
3. WHEN grep tool is called without path THEN it SHALL default to working directory, not "/"
4. WHEN a path outside working directory is requested THEN the system SHALL reject the request
5. WHEN path traversal is attempted (e.g., "../..") THEN the system SHALL block the request

### Requirement 3: Subagent System Prompt 增强

**User Story:** As a developer, I want subagents to be aware of their working directory, so that they use correct paths.

#### Acceptance Criteria

1. WHEN subagent is created THEN its system prompt SHALL include working directory information
2. WHEN subagent receives task description THEN it SHALL include working directory context
3. WHEN subagent uses file tools THEN it SHALL prefer relative paths within working directory

### Requirement 4: 安全审计

**User Story:** As a security auditor, I want all file access attempts to be logged, so that I can detect unauthorized access.

#### Acceptance Criteria

1. WHEN a file operation is performed THEN the system SHALL log the requesting agent and path
2. WHEN a path outside workspace is blocked THEN the system SHALL log a security warning
3. WHEN subagent accesses files THEN the audit log SHALL include subagent identifier
