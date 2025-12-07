# 多租户隔离测试框架需求文档

## Introduction

本文档定义了 DataAgent 系统的多租户隔离测试框架需求。该框架提供内置测试用户、测试数据和自动化验证脚本，用于验证多租户环境下的资源隔离安全性。

**核心目标：**
- 验证用户 A 无法访问用户 B 的任何资源
- 提供可重复执行的自动化测试
- 支持新人快速验证系统安全性
- 持续迭代保证企业级安全要求

## Glossary

- **测试用户 (Test User)**: 内置的测试账户，用于验证多租户隔离
- **资源隔离 (Resource Isolation)**: 确保用户只能访问自己的资源
- **跨租户访问 (Cross-Tenant Access)**: 用户尝试访问其他用户资源的行为
- **隔离验证 (Isolation Verification)**: 验证跨租户访问被正确拒绝
- **测试数据集 (Test Dataset)**: 预置的 SQLite 数据和文件，用于测试
- **安全审计 (Security Audit)**: 记录和检查所有跨租户访问尝试

## Requirements

### Requirement 1: 内置测试用户

**User Story:** As a QA engineer, I want built-in test users with pre-configured resources, so that I can quickly verify multi-tenant isolation.

#### Acceptance Criteria

1. WHEN the test framework initializes THEN the system SHALL create two test users: "test_alice" and "test_bob"
2. WHEN test users are created THEN each user SHALL have isolated: workspace directory, rules, MCP configurations, skills, and memory
3. WHEN test users are created THEN the system SHALL populate each user with distinct test data that can be used to verify isolation
4. WHEN a test user's resources are accessed THEN the system SHALL verify the requesting user matches the resource owner
5. WHEN test users exist THEN the system SHALL provide a reset command to restore them to initial state

### Requirement 2: MCP 隔离验证

**User Story:** As a security engineer, I want to verify MCP server isolation, so that users cannot access each other's MCP tools and data.

#### Acceptance Criteria

1. WHEN test_alice configures an MCP server THEN test_bob SHALL NOT be able to see or use that server
2. WHEN test_alice calls an MCP tool THEN the tool execution SHALL be scoped to test_alice's context only
3. WHEN test_bob attempts to access test_alice's MCP server THEN the system SHALL return 403 Forbidden
4. WHEN listing MCP servers THEN each user SHALL only see their own configured servers
5. WHEN MCP server credentials are stored THEN they SHALL be isolated per user and not visible to other users
6. WHEN the test runs THEN it SHALL verify MCP tool results contain only the requesting user's data

### Requirement 3: Rules 隔离验证

**User Story:** As a security engineer, I want to verify rule isolation, so that users cannot access or modify each other's rules.

#### Acceptance Criteria

1. WHEN test_alice creates a rule THEN test_bob SHALL NOT be able to read, update, or delete that rule
2. WHEN test_bob lists rules THEN the response SHALL NOT include test_alice's user-scope rules
3. WHEN test_alice's rule is triggered THEN it SHALL NOT affect test_bob's agent behavior
4. WHEN test_bob attempts to access test_alice's rule by name THEN the system SHALL return 404 Not Found
5. WHEN rules are loaded for a session THEN only the current user's rules SHALL be included
6. WHEN the test runs THEN it SHALL verify rule content is user-specific and not leaked

### Requirement 4: 文件系统隔离验证

**User Story:** As a security engineer, I want to verify filesystem isolation, so that users cannot access each other's files.

#### Acceptance Criteria

1. WHEN test_alice writes a file THEN test_bob SHALL NOT be able to read that file
2. WHEN test_bob attempts path traversal to test_alice's directory THEN the system SHALL reject the request
3. WHEN listing files THEN each user SHALL only see files in their own workspace
4. WHEN test_alice searches files THEN results SHALL NOT include test_bob's files
5. WHEN file operations are performed THEN the system SHALL validate paths are within user's workspace
6. WHEN the test runs THEN it SHALL attempt various path traversal attacks and verify they are blocked

### Requirement 5: Skills 隔离验证

**User Story:** As a security engineer, I want to verify skill isolation, so that users cannot access or execute each other's custom skills.

#### Acceptance Criteria

1. WHEN test_alice creates a custom skill THEN test_bob SHALL NOT be able to see or execute that skill
2. WHEN test_bob lists available skills THEN the response SHALL NOT include test_alice's user-scope skills
3. WHEN test_alice executes a skill THEN it SHALL run in test_alice's context only
4. WHEN test_bob attempts to execute test_alice's skill by name THEN the system SHALL return 404 Not Found
5. WHEN skills access resources THEN they SHALL be restricted to the owning user's resources
6. WHEN the test runs THEN it SHALL verify skill execution results are user-specific

### Requirement 6: Memory/Knowledge 隔离验证

**User Story:** As a security engineer, I want to verify memory isolation, so that users cannot access each other's stored knowledge and preferences.

#### Acceptance Criteria

1. WHEN test_alice stores memory/knowledge THEN test_bob SHALL NOT be able to read that data
2. WHEN test_bob queries knowledge THEN results SHALL NOT include test_alice's stored information
3. WHEN agent.md is loaded THEN only the current user's agent.md SHALL be used
4. WHEN test_bob attempts to access test_alice's memory path THEN the system SHALL return 403 Forbidden
5. WHEN memory is cleared THEN only the requesting user's memory SHALL be affected
6. WHEN the test runs THEN it SHALL verify knowledge retrieval returns only user-specific data

### Requirement 7: 测试数据初始化

**User Story:** As a developer, I want automated test data initialization, so that tests can run with consistent, known data.

#### Acceptance Criteria

1. WHEN the test framework starts THEN it SHALL create a SQLite database with test data for each user
2. WHEN test data is initialized THEN test_alice SHALL have: 5 knowledge files, 3 rules, 2 MCP servers, 2 skills
3. WHEN test data is initialized THEN test_bob SHALL have: different 5 knowledge files, different 3 rules, different 2 MCP servers, different 2 skills
4. WHEN test data contains identifiable markers THEN each user's data SHALL contain their username for verification
5. WHEN the reset command is run THEN all test data SHALL be restored to initial state
6. WHEN test data is created THEN it SHALL include realistic content for meaningful testing

### Requirement 8: 自动化测试套件

**User Story:** As a QA engineer, I want an automated test suite, so that I can run comprehensive isolation tests with one command.

#### Acceptance Criteria

1. WHEN running "pytest tests/test_multi_tenant/" THEN all isolation tests SHALL execute automatically
2. WHEN tests run THEN they SHALL cover: MCP isolation, rules isolation, filesystem isolation, skills isolation, memory isolation
3. WHEN a test fails THEN it SHALL provide clear error message indicating which isolation was breached
4. WHEN tests complete THEN they SHALL generate a security audit report
5. WHEN tests run THEN they SHALL attempt cross-tenant access in both directions (alice→bob and bob→alice)
6. WHEN tests run THEN they SHALL verify both positive cases (own resources accessible) and negative cases (other's resources blocked)

### Requirement 9: 安全审计日志

**User Story:** As a security auditor, I want comprehensive audit logs, so that I can review all cross-tenant access attempts.

#### Acceptance Criteria

1. WHEN any cross-tenant access is attempted THEN the system SHALL log: timestamp, requesting_user, target_user, resource_type, resource_id, result
2. WHEN audit logs are queried THEN they SHALL be filterable by user, resource type, and time range
3. WHEN a security violation is detected THEN the system SHALL emit a SecurityViolationEvent
4. WHEN tests complete THEN they SHALL output a summary of all cross-tenant access attempts and their results
5. WHEN audit logs are exported THEN they SHALL support JSON format for integration with security tools

### Requirement 10: 快速验证脚本

**User Story:** As a new team member, I want a simple verification script, so that I can quickly validate the system's security.

#### Acceptance Criteria

1. WHEN running "make test-isolation" THEN the system SHALL execute all isolation tests and report results
2. WHEN running the verification script THEN it SHALL: initialize test users, run all isolation tests, generate report, cleanup
3. WHEN verification completes THEN it SHALL display a clear PASS/FAIL summary for each isolation category
4. WHEN verification fails THEN it SHALL provide remediation guidance
5. WHEN the script runs THEN it SHALL complete within 60 seconds for quick feedback
6. WHEN the script is run by a new user THEN it SHALL require no additional setup beyond basic dependencies

### Requirement 11: CI/CD 集成

**User Story:** As a DevOps engineer, I want isolation tests in CI/CD, so that security regressions are caught automatically.

#### Acceptance Criteria

1. WHEN code is pushed THEN the CI pipeline SHALL run isolation tests automatically
2. WHEN isolation tests fail THEN the CI build SHALL fail and block merge
3. WHEN tests run in CI THEN they SHALL use isolated test database and directories
4. WHEN CI tests complete THEN they SHALL upload security audit report as artifact
5. WHEN a security regression is detected THEN the system SHALL notify the security team

### Requirement 12: 测试报告生成

**User Story:** As a project manager, I want detailed test reports, so that I can track security compliance over time.

#### Acceptance Criteria

1. WHEN tests complete THEN the system SHALL generate a HTML report with test results
2. WHEN generating report THEN it SHALL include: test date, test count, pass/fail counts, detailed results per category
3. WHEN generating report THEN it SHALL include security audit summary with all access attempts
4. WHEN tests are run multiple times THEN reports SHALL be archived with timestamps
5. WHEN viewing report THEN it SHALL clearly highlight any security violations in red
