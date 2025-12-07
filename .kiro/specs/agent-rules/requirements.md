# Requirements Document

## Introduction

本文档定义了 DataAgent 系统的 Agent Rules（智能体规则）功能需求。该功能类似于 Cursor Rules 和 Claude Code 的 claude.md 文件机制，允许用户通过配置文件定义 Agent 的行为规则、工作流程和领域知识，从而提升 Agent 的智能水平和任务执行质量。

Agent Rules 是企业级核心功能，支持：
- 多层级规则配置（全局、用户、项目、会话）
- 规则的条件触发（基于文件类型、任务类型等）
- 规则的优先级和合并策略
- 规则的版本管理和热更新

## Glossary

- **Agent Rules（智能体规则）**: 指导 Agent 行为的配置文件，包含指令、工作流程、最佳实践等
- **Rule File（规则文件）**: 存储 Agent Rules 的 Markdown 文件，支持 YAML frontmatter
- **Rule Scope（规则作用域）**: 规则的生效范围，包括 global（全局）、user（用户）、project（项目）、session（会话）
- **Rule Inclusion（规则包含模式）**: 规则的加载方式，包括 always（始终加载）、fileMatch（文件匹配时加载）、manual（手动引用）
- **Rule Priority（规则优先级）**: 当多个规则冲突时的优先顺序
- **DataAgent Core**: 核心业务逻辑层，提供 Agent 创建和执行能力
- **DataAgent CLI**: 终端客户端，提供命令行交互界面
- **DataAgent Server**: Web 服务层，提供 REST API 和 WebSocket 接口
- **System Prompt（系统提示词）**: 发送给 LLM 的系统级指令
- **Middleware（中间件）**: 在 Agent 执行过程中拦截和修改请求的组件

## Requirements

### Requirement 1: 规则文件格式与解析

**User Story:** As a developer, I want to define agent rules in Markdown files with YAML frontmatter, so that I can easily configure agent behavior with familiar syntax.

#### Acceptance Criteria

1. WHEN a rule file is loaded THEN the system SHALL parse YAML frontmatter containing metadata fields (name, description, inclusion, fileMatchPattern, priority)
2. WHEN a rule file contains invalid YAML frontmatter THEN the system SHALL log a warning and skip the invalid rule without crashing
3. WHEN a rule file exceeds 1MB in size THEN the system SHALL skip the file and log a warning to prevent memory issues
4. WHEN a rule file contains Markdown content after frontmatter THEN the system SHALL extract and store the content as rule instructions
5. WHEN parsing a rule file THEN the system SHALL validate that required fields (name, description) are present
6. WHEN a rule file is parsed THEN the system SHALL support file reference syntax (#[[file:relative_path]]) for including external content

### Requirement 2: 规则作用域与存储位置

**User Story:** As a system administrator, I want to configure rules at different scopes (global, user, project), so that I can manage rules hierarchically for different use cases.

#### Acceptance Criteria

1. WHEN the system initializes THEN the system SHALL load global rules from ~/.dataagent/rules/ directory
2. WHEN a user session starts THEN the system SHALL load user-specific rules from ~/.dataagent/users/{user_id}/rules/ directory
3. WHEN a project is detected THEN the system SHALL load project rules from {project_root}/.dataagent/rules/ directory
4. WHEN rules exist at multiple scopes THEN the system SHALL merge rules with priority order: session > project > user > global
5. WHEN a rule with the same name exists at multiple scopes THEN the system SHALL use the higher-priority scope's rule
6. WHEN the rules directory does not exist THEN the system SHALL create it automatically on first rule creation

### Requirement 3: 规则包含模式

**User Story:** As a developer, I want rules to be loaded conditionally based on context, so that only relevant rules are applied to each request.

#### Acceptance Criteria

1. WHEN a rule has inclusion mode "always" THEN the system SHALL include the rule in every request's system prompt
2. WHEN a rule has inclusion mode "fileMatch" with a pattern THEN the system SHALL include the rule only when a matching file is in context
3. WHEN a rule has inclusion mode "manual" THEN the system SHALL include the rule only when explicitly referenced by the user
4. WHEN evaluating fileMatch patterns THEN the system SHALL support glob syntax (e.g., "*.py", "src/**/*.ts")
5. WHEN multiple fileMatch rules match the same file THEN the system SHALL include all matching rules
6. WHEN a user references a manual rule using @rulename syntax THEN the system SHALL load and include that rule

### Requirement 4: 规则优先级与合并

**User Story:** As a developer, I want to control rule priority and merging behavior, so that I can resolve conflicts between rules predictably.

#### Acceptance Criteria

1. WHEN a rule specifies a priority value (1-100) THEN the system SHALL use that value for ordering within the same scope
2. WHEN rules have the same priority THEN the system SHALL order them alphabetically by name
3. WHEN merging rules into the system prompt THEN the system SHALL concatenate rule contents in priority order
4. WHEN a rule specifies "override: true" THEN the system SHALL replace any lower-priority rule with the same name
5. WHEN the total merged rules exceed the context limit THEN the system SHALL truncate lower-priority rules first

### Requirement 5: 规则管理 CLI 命令

**User Story:** As a developer, I want CLI commands to manage rules, so that I can easily create, list, edit, and delete rules.

#### Acceptance Criteria

1. WHEN a user runs "dataagent rules list" THEN the system SHALL display all available rules grouped by scope with their metadata
2. WHEN a user runs "dataagent rules create <name>" THEN the system SHALL create a new rule file with template content
3. WHEN a user runs "dataagent rules edit <name>" THEN the system SHALL open the rule file in the default editor
4. WHEN a user runs "dataagent rules delete <name>" THEN the system SHALL remove the rule file after confirmation
5. WHEN a user runs "dataagent rules show <name>" THEN the system SHALL display the full content of the specified rule
6. WHEN a user runs "dataagent rules validate" THEN the system SHALL check all rule files for syntax errors and report issues

### Requirement 6: 规则管理 REST API

**User Story:** As a frontend developer, I want REST APIs to manage rules, so that I can build a web interface for rule management.

#### Acceptance Criteria

1. WHEN a client sends GET /api/v1/rules THEN the system SHALL return a list of all rules with metadata
2. WHEN a client sends GET /api/v1/rules/{name} THEN the system SHALL return the full content of the specified rule
3. WHEN a client sends POST /api/v1/rules THEN the system SHALL create a new rule with the provided content
4. WHEN a client sends PUT /api/v1/rules/{name} THEN the system SHALL update the existing rule content
5. WHEN a client sends DELETE /api/v1/rules/{name} THEN the system SHALL delete the specified rule
6. WHEN a client sends POST /api/v1/rules/validate THEN the system SHALL validate the provided rule content and return errors

### Requirement 7: 规则中间件集成

**User Story:** As a system architect, I want rules to be integrated via middleware, so that rules are automatically applied to agent requests.

#### Acceptance Criteria

1. WHEN an agent request is processed THEN the RulesMiddleware SHALL load applicable rules based on context
2. WHEN rules are loaded THEN the RulesMiddleware SHALL inject rule content into the system prompt
3. WHEN the request contains file references THEN the RulesMiddleware SHALL evaluate fileMatch rules against those files
4. WHEN a user explicitly references rules THEN the RulesMiddleware SHALL include those manual rules
5. WHEN rules are updated during a session THEN the RulesMiddleware SHALL reload rules on the next request
6. WHEN rule loading fails THEN the RulesMiddleware SHALL log the error and continue with available rules

### Requirement 8: 规则热更新

**User Story:** As a developer, I want rules to be reloaded without restarting the agent, so that I can iterate quickly on rule definitions.

#### Acceptance Criteria

1. WHEN a rule file is modified THEN the system SHALL detect the change on the next request
2. WHEN a user runs "/rules reload" command THEN the system SHALL immediately reload all rules
3. WHEN rules are reloaded THEN the system SHALL validate all rules and report any errors
4. WHEN a rule reload fails THEN the system SHALL keep the previous valid rules and report the error
5. WHEN rules are reloaded via API THEN the system SHALL return the new rule list in the response

### Requirement 9: 内置规则模板

**User Story:** As a new user, I want built-in rule templates, so that I can quickly start with best practices for common scenarios.

#### Acceptance Criteria

1. WHEN a user runs "dataagent rules init" THEN the system SHALL create default rule files for common scenarios
2. WHEN initializing rules THEN the system SHALL include templates for: coding-standards, file-operations, error-handling, security-practices
3. WHEN a template is created THEN the system SHALL include comprehensive instructions and examples
4. WHEN a user runs "dataagent rules templates" THEN the system SHALL list all available built-in templates
5. WHEN a user runs "dataagent rules create --template <name>" THEN the system SHALL create a rule from the specified template

### Requirement 10: 规则序列化与反序列化

**User Story:** As a developer, I want rules to be serializable to JSON, so that rules can be stored in databases and transmitted via APIs.

#### Acceptance Criteria

1. WHEN a rule is serialized THEN the system SHALL produce a JSON object containing all rule metadata and content
2. WHEN a JSON object is deserialized THEN the system SHALL reconstruct the rule with all properties intact
3. WHEN serializing a rule with file references THEN the system SHALL resolve and inline the referenced content
4. WHEN deserializing invalid JSON THEN the system SHALL raise a validation error with details
5. WHEN a rule is serialized then deserialized THEN the resulting rule SHALL be equivalent to the original

### Requirement 11: 规则使用统计

**User Story:** As a system administrator, I want to track rule usage, so that I can understand which rules are most valuable.

#### Acceptance Criteria

1. WHEN a rule is included in a request THEN the system SHALL increment the rule's usage counter
2. WHEN a user requests rule statistics THEN the system SHALL return usage counts per rule
3. WHEN displaying rule statistics THEN the system SHALL show last-used timestamp for each rule
4. WHEN a rule has not been used in 30 days THEN the system SHALL flag it as potentially stale
5. WHEN exporting statistics THEN the system SHALL support JSON format output

### Requirement 12: 规则安全性

**User Story:** As a security engineer, I want rules to be validated for security, so that malicious content cannot be injected.

#### Acceptance Criteria

1. WHEN a rule file path is resolved THEN the system SHALL validate it is within allowed directories to prevent path traversal
2. WHEN a rule contains file references THEN the system SHALL validate referenced files are within allowed directories
3. WHEN a rule file is loaded THEN the system SHALL sanitize content to prevent prompt injection attacks
4. WHEN a rule exceeds size limits THEN the system SHALL reject it to prevent denial of service
5. WHEN a rule contains suspicious patterns THEN the system SHALL log a security warning

### Requirement 13: 规则触发透明度与调试

**User Story:** As a developer, I want to see which rules are triggered for each request, so that I can understand and debug agent behavior.

#### Acceptance Criteria

1. WHEN a request is processed THEN the system SHALL record which rules were evaluated and their match results
2. WHEN rules are applied THEN the system SHALL emit a RulesAppliedEvent containing the list of triggered rules with their sources (global/user/project)
3. WHEN a user runs "/rules debug" command THEN the system SHALL enable verbose logging of rule evaluation for subsequent requests
4. WHEN debug mode is enabled THEN the system SHALL display rule matching details including: rule name, scope, inclusion mode, match reason
5. WHEN a user runs "/rules trace <request_id>" THEN the system SHALL show the complete rule evaluation trace for that request
6. WHEN rules are applied via API THEN the response SHALL include a "triggered_rules" field listing all applied rules
7. WHEN a fileMatch rule is evaluated THEN the system SHALL log which files triggered the match and which pattern matched

### Requirement 14: 规则冲突检测与报告

**User Story:** As a developer, I want to be notified of rule conflicts, so that I can resolve ambiguities in rule configuration.

#### Acceptance Criteria

1. WHEN multiple rules with the same name exist at different scopes THEN the system SHALL report the conflict with scope information
2. WHEN rules have contradictory instructions THEN the system SHALL log a warning with the conflicting rule names
3. WHEN a user runs "dataagent rules conflicts" THEN the system SHALL analyze and report all potential rule conflicts
4. WHEN a conflict is detected THEN the system SHALL indicate which rule takes precedence based on priority
5. WHEN loading rules THEN the system SHALL generate a conflict report accessible via API and CLI

### Requirement 15: 规则执行上下文

**User Story:** As a developer, I want rules to have access to request context, so that rules can make dynamic decisions based on the current situation.

#### Acceptance Criteria

1. WHEN a rule is evaluated THEN the system SHALL provide context variables including: current_files, user_query, session_id, assistant_id
2. WHEN a rule uses conditional expressions THEN the system SHALL evaluate them against the current context
3. WHEN context variables are referenced in rule content THEN the system SHALL substitute them with actual values
4. WHEN a context variable is undefined THEN the system SHALL use an empty string and log a debug message
5. WHEN displaying triggered rules THEN the system SHALL show which context conditions caused the rule to activate

### Requirement 16: 规则执行日志

**User Story:** As a system administrator, I want comprehensive rule execution logs, so that I can audit and troubleshoot rule behavior.

#### Acceptance Criteria

1. WHEN rules are evaluated THEN the system SHALL log the evaluation with timestamp, request_id, and rule names
2. WHEN a rule is skipped due to inclusion mode THEN the system SHALL log the skip reason
3. WHEN a rule fails to load THEN the system SHALL log the error with file path and error details
4. WHEN rule logs are requested THEN the system SHALL support filtering by time range, rule name, and scope
5. WHEN exporting rule logs THEN the system SHALL support JSON and CSV formats
6. WHEN a request completes THEN the system SHALL log a summary of rules applied including total count and combined size
