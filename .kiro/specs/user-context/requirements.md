# Requirements Document

## Introduction

本功能为 DataAgent 添加用户上下文感知能力，使 AI 助手能够识别当前用户身份，并在对话中自动将"我"、"我的"等代词解析为具体的用户信息。这类似于 OpenAI 的"用户记忆"功能，但更侧重于用户身份上下文的注入。

核心场景：
- 用户问"我是谁"，系统回复用户的登录信息
- 用户问"帮我查询我今年的绩效"，系统自动将"我"替换为用户真实姓名进行查询
- 对话过程中，AI 能够使用用户信息进行个性化回复

## Glossary

- **User Context（用户上下文）**: 包含当前登录用户的身份信息，如用户ID、姓名、部门等
- **System Prompt（系统提示词）**: 发送给 LLM 的系统级指令，用于设定 AI 的行为和上下文
- **User Profile（用户档案）**: 存储用户基本信息和偏好的数据结构
- **Context Injection（上下文注入）**: 将用户信息自动注入到 LLM 对话上下文中的过程
- **Pronoun Resolution（代词解析）**: 将"我"、"我的"等代词解析为具体用户信息的能力

## Requirements

### Requirement 1

**User Story:** As a user, I want the chatbot to know who I am, so that I can ask "who am I" and get my profile information.

#### Acceptance Criteria

1. WHEN a user sends a message to the chatbot THEN the system SHALL include the user's profile information in the system prompt
2. WHEN a user asks "我是谁" or similar identity questions THEN the system SHALL respond with the user's name, username, and other available profile information
3. WHEN user profile information is not available THEN the system SHALL respond that the user information is not configured
4. WHEN the system prompt is constructed THEN the system SHALL format user information in a clear, structured way for the LLM to understand

### Requirement 2

**User Story:** As a user, I want the chatbot to understand "我" refers to me, so that I can make queries about myself naturally.

#### Acceptance Criteria

1. WHEN a user's message contains pronouns like "我", "我的", "本人" THEN the system SHALL provide context to the LLM to resolve these to the user's actual identity
2. WHEN the LLM needs to query data about "我" THEN the system SHALL ensure the LLM uses the user's actual name or identifier
3. WHEN constructing tool calls THEN the system SHALL have access to user context to substitute pronouns with actual values
4. WHEN the user asks "帮我查询我今年的绩效" THEN the system SHALL interpret "我" as the logged-in user's name for the query

### Requirement 3

**User Story:** As a system administrator, I want to configure user profile fields, so that different deployments can customize what user information is available.

#### Acceptance Criteria

1. WHEN configuring user profiles THEN the system SHALL support standard fields: user_id, username, display_name, email, department, role
2. WHEN configuring user profiles THEN the system SHALL support custom fields through a flexible key-value structure
3. WHEN a user profile is updated THEN the system SHALL persist the changes to storage
4. WHEN retrieving user profiles THEN the system SHALL return all configured fields

### Requirement 4

**User Story:** As a developer, I want to pass user context through the API, so that I can integrate DataAgent with existing authentication systems.

#### Acceptance Criteria

1. WHEN a chat request is made THEN the system SHALL accept user context in the request payload
2. WHEN user context is provided in the request THEN the system SHALL use it to enrich the conversation
3. WHEN user context is provided via WebSocket THEN the system SHALL maintain it throughout the session
4. WHEN user context changes during a session THEN the system SHALL update the context for subsequent messages

### Requirement 5

**User Story:** As a user, I want the chatbot to remember my context throughout the conversation, so that I don't need to repeat my identity.

#### Acceptance Criteria

1. WHEN a session is created THEN the system SHALL associate user context with the session
2. WHEN multiple messages are sent in a session THEN the system SHALL maintain consistent user context
3. WHEN the session ends THEN the system SHALL preserve user context for future sessions with the same user
4. WHEN a user returns to a previous session THEN the system SHALL restore the user context

### Requirement 6

**User Story:** As a security-conscious user, I want my profile information to be handled securely, so that sensitive data is protected.

#### Acceptance Criteria

1. WHEN storing user profiles THEN the system SHALL encrypt sensitive fields like email
2. WHEN logging or debugging THEN the system SHALL mask sensitive user information
3. WHEN user context is injected into prompts THEN the system SHALL only include necessary information
4. WHEN a user requests their data THEN the system SHALL only return their own profile information
