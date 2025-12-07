# Implementation Plan

## Phase 1: Core Data Models and Parser

- [x] 1. Implement Rule data models
  - [x] 1.1 Create Rule, RuleScope, RuleInclusion models in dataagent_core/rules/models.py
    - Define Rule dataclass with all fields (name, description, content, scope, inclusion, etc.)
    - Implement to_dict() and from_dict() methods for serialization
    - Define RuleMatch and RuleEvaluationTrace dataclasses
    - _Requirements: 1.1, 10.1, 10.2_

  - [x] 1.2 Write property test for Rule serialization round trip
    - **Property 1: Rule Parsing Round Trip**
    - **Property 12: Rule Serialization Completeness**
    - **Validates: Requirements 1.1, 10.1, 10.2, 10.5**

  - [x] 1.3 Implement RuleParser in dataagent_core/rules/parser.py
    - Implement YAML frontmatter parsing with regex
    - Implement required field validation (name, description)
    - Implement file size limit check (1MB)
    - Implement file reference resolution (#[[file:path]])
    - Implement path safety validation
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 12.1, 12.2_

  - [x] 1.4 Write property tests for RuleParser
    - **Property 2: Frontmatter Extraction Completeness**
    - **Property 3: Invalid Frontmatter Handling**
    - **Property 11: Path Safety Validation**
    - **Validates: Requirements 1.1, 1.2, 1.4, 1.5, 12.1, 12.2**

- [x] 2. Checkpoint - Ensure all tests pass
  - All tests pass (83 tests in Phase 1-3).

## Phase 2: Rule Storage

- [x] 3. Implement Rule Store
  - [x] 3.1 Create RuleStore abstract base class in dataagent_core/rules/store.py
    - Define abstract methods: list_rules, get_rule, save_rule, delete_rule, reload
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.2 Implement FileRuleStore in dataagent_core/rules/store.py
    - Implement file-based storage with global/user/project directories
    - Implement rule caching with lazy loading
    - Implement reload functionality
    - Implement rule file generation from Rule objects
    - _Requirements: 2.1, 2.2, 2.3, 2.6, 8.1, 8.2_

  - [x] 3.3 Write unit tests for FileRuleStore
    - Test CRUD operations
    - Test directory creation
    - Test caching behavior
    - Test reload functionality
    - _Requirements: 2.1, 2.2, 2.3, 2.6_

- [x] 4. Checkpoint - Ensure all tests pass
  - All tests pass.

## Phase 3: Rule Matching and Merging

- [ ] 5. Implement Rule Matcher
  - [x] 5.1 Create MatchContext and RuleMatcher in dataagent_core/rules/matcher.py
    - Implement MatchContext dataclass with current_files, user_query, manual_rules
    - Implement match_rules method returning matched and skipped rules
    - Implement always inclusion mode matching
    - Implement fileMatch inclusion mode with glob pattern support
    - Implement manual inclusion mode matching
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 5.2 Write property tests for RuleMatcher
    - **Property 5: Always Inclusion Guarantee**
    - **Property 6: FileMatch Pattern Correctness**
    - **Property 7: Manual Reference Inclusion**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.6**

  - [x] 5.3 Implement RuleMerger in dataagent_core/rules/merger.py
    - Implement scope priority ordering (session > project > user > global)
    - Implement priority-based sorting within scope
    - Implement alphabetical sorting for same priority
    - Implement override behavior for same-name rules
    - Implement size limit truncation
    - Implement build_prompt_section for system prompt generation
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 5.4 Write property tests for RuleMerger
    - **Property 4: Scope Priority Ordering**
    - **Property 8: Priority Ordering Consistency**
    - **Property 9: Override Behavior**
    - **Property 10: Size Limit Truncation**
    - **Validates: Requirements 2.4, 2.5, 4.1, 4.2, 4.3, 4.4, 4.5**

- [x] 6. Checkpoint - Ensure all tests pass
  - All tests pass.

## Phase 4: Rules Middleware Integration

- [x] 7. Implement Rules Middleware
  - [x] 7.1 Create RulesMiddleware in dataagent_core/middleware/rules.py
    - Implemented RulesState and RulesStateUpdate types
    - Implemented before_agent hook for rule loading
    - Implemented wrap_model_call and awrap_model_call for prompt injection
    - Implemented match context extraction from request
    - Implemented manual rule reference parsing (@rulename)
    - Implemented debug mode with trace information
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 13.1, 13.2, 13.3, 13.4_

  - [x] 7.2 Write property test for RulesMiddleware trace recording
    - **Property 13: Trace Recording Completeness**
    - **Validates: Requirements 13.1, 13.2**

  - [x] 7.3 Integrate RulesMiddleware into AgentFactory
    - Added enable_rules and rules_debug_mode config options to AgentConfig
    - Added RulesMiddleware to middleware stack in factory.py
    - Configured rule store paths based on settings
    - _Requirements: 7.1, 7.5_

  - [x] 7.4 Write integration tests for middleware
    - Test rule injection into system prompt
    - Test fileMatch triggering with file context
    - Test manual rule reference
    - Test debug mode output
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 8. Checkpoint - Ensure all tests pass
  - All 102 tests pass.

## Phase 5: Rule Events

- [x] 9. Implement Rule Events
  - [x] 9.1 Create RulesAppliedEvent and RuleDebugEvent in dataagent_core/events/rules.py
    - Implemented RulesAppliedEvent with triggered_rules, skipped_count, conflicts
    - Implemented RuleDebugEvent with full trace information
    - Registered events in events/__init__.py
    - _Requirements: 13.2, 13.3_

  - [x] 9.2 Emit events from RulesMiddleware
    - Emit RulesAppliedEvent after rule evaluation
    - Emit RuleDebugEvent when debug mode is enabled
    - _Requirements: 13.2, 13.4_

- [x] 10. Checkpoint - Ensure all tests pass
  - All 106 tests pass (102 rules + 4 event tests).

## Phase 6: Conflict Detection

- [x] 11. Implement Conflict Detection
  - [x] 11.1 Create ConflictDetector in dataagent_core/rules/conflict.py
    - Implemented same-name conflict detection across scopes
    - Implemented contradictory rule detection via keywords
    - Implemented conflict report generation
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [x] 11.2 Write property test for conflict detection
    - **Property 14: Conflict Detection Accuracy**
    - **Validates: Requirements 14.1, 14.4**

- [x] 12. Checkpoint - Ensure all tests pass
  - All 119 tests pass.

## Phase 7: CLI Commands

- [x] 13. Implement CLI Commands for Rules
  - [x] 13.1 Add /rules list command in dataagent_cli/commands.py
    - Display rules grouped by scope
    - Show name, description, inclusion mode, priority
    - _Requirements: 5.1_

  - [x] 13.2 Add /rules create command
    - Create new rule file with template
    - Support --scope option
    - _Requirements: 5.2, 9.5_

  - [ ] 13.3 Add /rules edit command (deferred - requires editor integration)
    - Open rule file in default editor
    - _Requirements: 5.3_

  - [x] 13.4 Add /rules delete command
    - Delete rule file
    - _Requirements: 5.4_

  - [x] 13.5 Add /rules show command
    - Display full rule content
    - _Requirements: 5.5_

  - [x] 13.6 Add /rules validate command
    - Validate all rule files and report errors
    - _Requirements: 5.6_

  - [x] 13.7 Add /rules debug command
    - Enable/disable debug mode for rule evaluation
    - _Requirements: 13.3_

  - [x] 13.8 Add /rules reload command
    - Reload all rules from disk
    - _Requirements: 8.2_

  - [x] 13.9 Add /rules conflicts command
    - Display rule conflicts
    - _Requirements: 14.3_

  - [ ] 13.10 Write unit tests for CLI commands (deferred)
    - Test each command with valid and invalid inputs
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 14. Checkpoint - Ensure all tests pass
  - All 119 rules tests pass. CLI commands implemented.

## Phase 8: REST API

- [x] 15. Implement REST API for Rules
  - [x] 15.1 Create rules router in dataagent_server/api/v1/rules.py
    - Defined Pydantic models for request/response
    - Implemented dependency injection for RuleStore
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 15.2 Implement GET /api/v1/users/{user_id}/rules endpoint
    - List all rules with optional scope filter
    - _Requirements: 6.1, 13.6_

  - [x] 15.3 Implement GET /api/v1/users/{user_id}/rules/{name} endpoint
    - Return full rule content
    - _Requirements: 6.2_

  - [x] 15.4 Implement POST /api/v1/users/{user_id}/rules endpoint
    - Create new rule with validation
    - Return 409 if rule already exists
    - _Requirements: 6.3_

  - [x] 15.5 Implement PUT /api/v1/users/{user_id}/rules/{name} endpoint
    - Update existing rule
    - Return 404 if rule not found
    - _Requirements: 6.4_

  - [x] 15.6 Implement DELETE /api/v1/users/{user_id}/rules/{name} endpoint
    - Delete rule
    - Return 404 if rule not found
    - _Requirements: 6.5_

  - [x] 15.7 Implement POST /api/v1/users/{user_id}/rules/validate endpoint
    - Validate rule content without saving
    - Return errors and warnings
    - _Requirements: 6.6_

  - [x] 15.8 Implement GET /api/v1/users/{user_id}/rules/conflicts/list endpoint
    - Return list of rule conflicts
    - _Requirements: 14.3_

  - [x] 15.9 Implement POST /api/v1/users/{user_id}/rules/reload endpoint
    - Reload rules and return count
    - _Requirements: 8.2, 8.5_

  - [x] 15.10 Register rules router in main.py
    - Added router to FastAPI app
    - _Requirements: 6.1_

  - [ ] 15.11 Write API integration tests (deferred)
    - Test all endpoints with valid and invalid inputs
    - Test error responses
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 16. Checkpoint - Ensure all tests pass
  - All 119 rules tests pass. REST API implemented.

## Phase 9: Built-in Templates

- [ ] 17. Create Built-in Rule Templates
  - [ ] 17.1 Create templates directory and loader
    - Create dataagent_core/rules/templates/ directory
    - Implement template loader function
    - _Requirements: 9.1, 9.4_

  - [ ] 17.2 Create coding-standards template
    - Include Python/TypeScript coding guidelines
    - _Requirements: 9.2, 9.3_

  - [ ] 17.3 Create file-operations template
    - Include file handling best practices
    - _Requirements: 9.2, 9.3_

  - [ ] 17.4 Create error-handling template
    - Include error handling guidelines
    - _Requirements: 9.2, 9.3_

  - [ ] 17.5 Create security-practices template
    - Include security review checklist
    - _Requirements: 9.2, 9.3_

  - [ ] 17.6 Add /rules init command
    - Create default rules from templates
    - _Requirements: 9.1_

  - [ ] 17.7 Add /rules templates command
    - List available templates
    - _Requirements: 9.4_

- [ ] 18. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 10: Usage Statistics and Logging

- [ ] 19. Implement Usage Statistics
  - [ ] 19.1 Create RuleUsageTracker in dataagent_core/rules/usage.py
    - Track rule usage counts
    - Track last-used timestamps
    - Implement stale rule detection (30 days)
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [ ] 19.2 Add statistics export functionality
    - Export to JSON format
    - _Requirements: 11.5_

  - [ ] 19.3 Add /rules stats command
    - Display usage statistics
    - _Requirements: 11.2_

- [ ] 20. Implement Rule Execution Logging
  - [ ] 20.1 Create RuleLogger in dataagent_core/rules/logging.py
    - Log rule evaluation with timestamp and request_id
    - Log skip reasons
    - Log errors with details
    - _Requirements: 16.1, 16.2, 16.3_

  - [ ] 20.2 Add log filtering and export
    - Filter by time range, rule name, scope
    - Export to JSON and CSV
    - _Requirements: 16.4, 16.5_

  - [ ] 20.3 Add summary logging
    - Log summary after each request
    - _Requirements: 16.6_

- [ ] 21. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
