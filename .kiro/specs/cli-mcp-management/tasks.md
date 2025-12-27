# Implementation Plan: CLI MCP Management

## Overview

This implementation adds complete MCP server management commands to the DataAgent CLI. The work is organized into extending the MCPConfigLoader, implementing command handlers, and adding comprehensive property-based tests.

## Tasks

- [x] 1. Extend MCPConfigLoader with save/modify capabilities
  - [x] 1.1 Add `save_config()` method to persist configuration to mcp.json
    - Implement JSON serialization using MCPConfig.to_dict()
    - Create parent directories if needed
    - _Requirements: 8.1, 8.2_
  - [x] 1.2 Add `add_server()` method to add new server configuration
    - Check for duplicate names before adding
    - Call save_config() after modification
    - _Requirements: 2.4_
  - [x] 1.3 Add `remove_server()` method to remove server configuration
    - Return False if server not found
    - Call save_config() after modification
    - _Requirements: 3.1, 3.3_
  - [x] 1.4 Add `update_server()` method to modify existing server
    - Only update provided fields
    - Preserve unmodified fields
    - _Requirements: 7.1, 7.3_
  - [x] 1.5 Add `get_server()` method to retrieve single server config
    - Return None if not found
    - _Requirements: 5.1_
  - [x] 1.6 Write property test for configuration round-trip
    - **Property 1: Configuration Round-Trip**
    - **Validates: Requirements 8.4**

- [x] 2. Implement MCP command router and help
  - [x] 2.1 Refactor handle_slash_command to route /mcp commands to handle_mcp_command
    - Extract existing /mcp and /mcp reload logic
    - Add routing for new subcommands
    - _Requirements: 1.1, 9.1_
  - [x] 2.2 Implement mcp_help() command handler
    - Display all available subcommands with descriptions
    - Show usage examples
    - _Requirements: 9.1, 9.2_

- [x] 3. Implement mcp_list and mcp_show commands
  - [x] 3.1 Implement mcp_list() to display all servers
    - Show name, command/url, enabled status in table format
    - Handle empty configuration case
    - _Requirements: 1.1, 1.2, 1.3_
  - [x] 3.2 Implement mcp_show() to display server details
    - Show all configuration fields
    - Handle server not found error
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 4. Implement mcp_add command
  - [x] 4.1 Implement argument parser for add command
    - Parse --command, --url, --args, --env, --transport flags
    - Validate required parameters
    - _Requirements: 2.1, 2.2, 2.5_
  - [x] 4.2 Implement mcp_add() command handler
    - Create MCPServerConfig from parsed arguments
    - Check for duplicate names
    - Save configuration and display result
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [x] 4.3 Write property test for add server increases count
    - **Property 2: Add Server Increases Count**
    - **Validates: Requirements 2.4**
  - [x] 4.4 Write property test for server name uniqueness
    - **Property 5: Server Name Uniqueness**
    - **Validates: Requirements 2.3**

- [x] 5. Implement mcp_remove command
  - [x] 5.1 Implement mcp_remove() command handler
    - Remove server by name
    - Handle server not found error
    - Save configuration and display result
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 5.2 Write property test for remove server decreases count
    - **Property 3: Remove Server Decreases Count**
    - **Validates: Requirements 3.3**

- [x] 6. Implement mcp_enable and mcp_disable commands
  - [x] 6.1 Implement mcp_enable() command handler
    - Set server.disabled = False
    - Handle server not found error
    - Save configuration and display result
    - _Requirements: 4.1, 4.3, 4.4_
  - [x] 6.2 Implement mcp_disable() command handler
    - Set server.disabled = True
    - Handle server not found error
    - Save configuration and display result
    - _Requirements: 4.2, 4.3, 4.4_
  - [x] 6.3 Write property test for enable/disable toggle
    - **Property 4: Enable/Disable Toggle**
    - **Validates: Requirements 4.1, 4.2**

- [x] 7. Implement mcp_update command
  - [x] 7.1 Implement argument parser for update command
    - Parse optional --command, --url, --args, --env flags
    - Only update provided fields
    - _Requirements: 7.1_
  - [x] 7.2 Implement mcp_update() command handler
    - Update only specified fields
    - Handle server not found error
    - Save configuration and display result
    - _Requirements: 7.1, 7.2, 7.3_
  - [x] 7.3 Write property test for update preserves other servers
    - **Property 6: Update Preserves Other Servers**
    - **Validates: Requirements 8.3**

- [x] 8. Implement mcp_test command
  - [x] 8.1 Implement mcp_test() command handler
    - Check if server exists and is enabled
    - Attempt connection using MCPConfigLoader
    - Display tools on success, error on failure
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Integration and final testing
  - [x] 10.1 Add unit tests for error handling cases
    - Test missing arguments
    - Test server not found scenarios
    - Test invalid input formats
    - _Requirements: 2.5, 3.2, 4.3, 5.3, 6.4, 7.2_
  - [x] 10.2 Write integration tests for command flow
    - Test add → list → show → update → disable → enable → remove flow
    - Created test_cli_integration.py with 5 integration tests
    - _Requirements: All_

- [x] 11. Final checkpoint - Ensure all tests pass
  - All 150 MCP tests passing (including 13 property-based tests, 18 unit tests, 5 integration tests)

## Notes

- All tasks including property tests are required for comprehensive coverage
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation uses Python's `hypothesis` library for property-based testing
