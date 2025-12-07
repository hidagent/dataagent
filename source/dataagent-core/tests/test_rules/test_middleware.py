"""Tests for RulesMiddleware.

**Feature: agent-rules**
**Property 13: Trace Recording Completeness**
**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 13.1, 13.2**
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

from dataagent_core.rules.models import Rule, RuleScope, RuleInclusion
from dataagent_core.rules.store import MemoryRuleStore
from dataagent_core.middleware.rules import RulesMiddleware, RulesState


class MockMessage:
    """Mock message for testing."""
    def __init__(self, content: str):
        self.content = content


class MockModelRequest:
    """Mock model request for testing."""
    def __init__(
        self,
        messages: list[MockMessage] | None = None,
        system_prompt: str | None = None,
        state: dict | None = None,
    ):
        self.messages = messages or []
        self.system_prompt = system_prompt
        self.state = state or {}
    
    def override(self, system_prompt: str) -> "MockModelRequest":
        return MockModelRequest(
            messages=self.messages,
            system_prompt=system_prompt,
            state=self.state,
        )


class MockModelResponse:
    """Mock model response for testing."""
    def __init__(self, content: str = "response"):
        self.content = content


class TestRulesMiddlewareBasic:
    """Basic tests for RulesMiddleware."""

    def test_middleware_creation(self) -> None:
        """Test creating a RulesMiddleware instance."""
        store = MemoryRuleStore()
        middleware = RulesMiddleware(store)
        
        assert middleware.store is store
        assert middleware.debug_mode is False
        assert middleware._last_trace is None

    def test_before_agent_reloads_rules(self) -> None:
        """Test that before_agent reloads rules."""
        store = MemoryRuleStore()
        middleware = RulesMiddleware(store)
        
        state: RulesState = {}
        runtime = MagicMock()
        
        result = middleware.before_agent(state, runtime)
        
        assert result is not None
        assert result["rules_loaded"] is True
        assert result["triggered_rules"] == []

    def test_inject_always_rule(self) -> None:
        """Test that always rules are injected into system prompt."""
        store = MemoryRuleStore()
        rule = Rule(
            name="always-rule",
            description="Always included",
            content="Always follow this rule.",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.ALWAYS,
        )
        store.save_rule(rule)
        
        middleware = RulesMiddleware(store)
        
        request = MockModelRequest(
            messages=[MockMessage("Hello")],
            system_prompt="Base prompt",
        )
        
        handler = MagicMock(return_value=MockModelResponse())
        middleware.wrap_model_call(request, handler)
        
        # Check that handler was called with modified request
        call_args = handler.call_args[0][0]
        assert "Always follow this rule." in call_args.system_prompt
        assert "Base prompt" in call_args.system_prompt

    def test_inject_manual_rule_when_referenced(self) -> None:
        """Test that manual rules are injected when referenced."""
        store = MemoryRuleStore()
        rule = Rule(
            name="security-check",
            description="Security checklist",
            content="Check for vulnerabilities.",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.MANUAL,
        )
        store.save_rule(rule)
        
        middleware = RulesMiddleware(store)
        
        # Reference the rule with @security-check
        request = MockModelRequest(
            messages=[MockMessage("Please review @security-check")],
            system_prompt="Base prompt",
        )
        
        handler = MagicMock(return_value=MockModelResponse())
        middleware.wrap_model_call(request, handler)
        
        call_args = handler.call_args[0][0]
        assert "Check for vulnerabilities." in call_args.system_prompt

    def test_skip_manual_rule_when_not_referenced(self) -> None:
        """Test that manual rules are skipped when not referenced."""
        store = MemoryRuleStore()
        rule = Rule(
            name="security-check",
            description="Security checklist",
            content="Check for vulnerabilities.",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.MANUAL,
        )
        store.save_rule(rule)
        
        middleware = RulesMiddleware(store)
        
        request = MockModelRequest(
            messages=[MockMessage("Hello world")],
            system_prompt="Base prompt",
        )
        
        handler = MagicMock(return_value=MockModelResponse())
        middleware.wrap_model_call(request, handler)
        
        call_args = handler.call_args[0][0]
        assert "Check for vulnerabilities." not in call_args.system_prompt

    def test_inject_file_match_rule(self) -> None:
        """Test that fileMatch rules are injected when files match."""
        store = MemoryRuleStore()
        rule = Rule(
            name="python-rules",
            description="Python coding rules",
            content="Follow PEP 8.",
            scope=RuleScope.PROJECT,
            inclusion=RuleInclusion.FILE_MATCH,
            file_match_pattern="*.py",
        )
        store.save_rule(rule)
        
        middleware = RulesMiddleware(store)
        
        # Reference a Python file
        request = MockModelRequest(
            messages=[MockMessage("Please check `main.py`")],
            system_prompt="Base prompt",
        )
        
        handler = MagicMock(return_value=MockModelResponse())
        middleware.wrap_model_call(request, handler)
        
        call_args = handler.call_args[0][0]
        assert "Follow PEP 8." in call_args.system_prompt


class TestRulesMiddlewareAsync:
    """Async tests for RulesMiddleware."""

    @pytest.mark.asyncio
    async def test_async_wrap_model_call(self) -> None:
        """Test async model call wrapping."""
        store = MemoryRuleStore()
        rule = Rule(
            name="async-rule",
            description="Async test rule",
            content="Async content.",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.ALWAYS,
        )
        store.save_rule(rule)
        
        middleware = RulesMiddleware(store)
        
        request = MockModelRequest(
            messages=[MockMessage("Hello")],
            system_prompt="Base",
        )
        
        handler = AsyncMock(return_value=MockModelResponse())
        await middleware.awrap_model_call(request, handler)
        
        call_args = handler.call_args[0][0]
        assert "Async content." in call_args.system_prompt


class TestTraceRecording:
    """Tests for trace recording functionality.
    
    **Property 13: Trace Recording Completeness**
    """

    def test_trace_records_evaluated_rules(self) -> None:
        """Test that trace records all evaluated rules."""
        store = MemoryRuleStore()
        rule1 = Rule(
            name="rule1",
            description="Rule 1",
            content="Content 1",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.ALWAYS,
        )
        rule2 = Rule(
            name="rule2",
            description="Rule 2",
            content="Content 2",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.MANUAL,
        )
        store.save_rule(rule1)
        store.save_rule(rule2)
        
        middleware = RulesMiddleware(store)
        
        request = MockModelRequest(messages=[MockMessage("Hello")])
        handler = MagicMock(return_value=MockModelResponse())
        middleware.wrap_model_call(request, handler)
        
        trace = middleware.get_last_trace()
        assert trace is not None
        assert "rule1" in trace.evaluated_rules
        assert "rule2" in trace.evaluated_rules

    def test_trace_records_matched_rules(self) -> None:
        """Test that trace records matched rules with reasons."""
        store = MemoryRuleStore()
        rule = Rule(
            name="always-rule",
            description="Always rule",
            content="Content",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.ALWAYS,
        )
        store.save_rule(rule)
        
        middleware = RulesMiddleware(store)
        
        request = MockModelRequest(messages=[MockMessage("Hello")])
        handler = MagicMock(return_value=MockModelResponse())
        middleware.wrap_model_call(request, handler)
        
        trace = middleware.get_last_trace()
        assert trace is not None
        assert len(trace.matched_rules) == 1
        assert trace.matched_rules[0].rule.name == "always-rule"
        assert "always" in trace.matched_rules[0].match_reason.lower()

    def test_trace_records_skipped_rules(self) -> None:
        """Test that trace records skipped rules with reasons."""
        store = MemoryRuleStore()
        rule = Rule(
            name="manual-rule",
            description="Manual rule",
            content="Content",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.MANUAL,
        )
        store.save_rule(rule)
        
        middleware = RulesMiddleware(store)
        
        request = MockModelRequest(messages=[MockMessage("Hello")])
        handler = MagicMock(return_value=MockModelResponse())
        middleware.wrap_model_call(request, handler)
        
        trace = middleware.get_last_trace()
        assert trace is not None
        assert len(trace.skipped_rules) == 1
        assert trace.skipped_rules[0][0] == "manual-rule"

    def test_trace_records_final_rules(self) -> None:
        """Test that trace records final applied rules."""
        store = MemoryRuleStore()
        rule = Rule(
            name="final-rule",
            description="Final rule",
            content="Final content",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.ALWAYS,
        )
        store.save_rule(rule)
        
        middleware = RulesMiddleware(store)
        
        request = MockModelRequest(messages=[MockMessage("Hello")])
        handler = MagicMock(return_value=MockModelResponse())
        middleware.wrap_model_call(request, handler)
        
        trace = middleware.get_last_trace()
        assert trace is not None
        assert "final-rule" in trace.final_rules

    def test_trace_records_content_size(self) -> None:
        """Test that trace records total content size."""
        store = MemoryRuleStore()
        content = "X" * 100
        rule = Rule(
            name="sized-rule",
            description="Sized rule",
            content=content,
            scope=RuleScope.USER,
            inclusion=RuleInclusion.ALWAYS,
        )
        store.save_rule(rule)
        
        middleware = RulesMiddleware(store)
        
        request = MockModelRequest(messages=[MockMessage("Hello")])
        handler = MagicMock(return_value=MockModelResponse())
        middleware.wrap_model_call(request, handler)
        
        trace = middleware.get_last_trace()
        assert trace is not None
        assert trace.total_content_size == 100


class TestDebugMode:
    """Tests for debug mode functionality."""

    def test_debug_mode_adds_trace_to_prompt(self) -> None:
        """Test that debug mode adds trace info to system prompt."""
        store = MemoryRuleStore()
        rule = Rule(
            name="debug-rule",
            description="Debug rule",
            content="Debug content",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.ALWAYS,
        )
        store.save_rule(rule)
        
        middleware = RulesMiddleware(store, debug_mode=True)
        
        request = MockModelRequest(messages=[MockMessage("Hello")])
        handler = MagicMock(return_value=MockModelResponse())
        middleware.wrap_model_call(request, handler)
        
        call_args = handler.call_args[0][0]
        assert "[DEBUG] Rule Evaluation Trace" in call_args.system_prompt
        assert "debug-rule" in call_args.system_prompt

    def test_set_debug_mode(self) -> None:
        """Test setting debug mode dynamically."""
        store = MemoryRuleStore()
        middleware = RulesMiddleware(store)
        
        assert middleware.debug_mode is False
        
        middleware.set_debug_mode(True)
        assert middleware.debug_mode is True
        
        middleware.set_debug_mode(False)
        assert middleware.debug_mode is False


class TestFileReferenceExtraction:
    """Tests for file reference extraction."""

    def test_extract_backtick_references(self) -> None:
        """Test extracting file references from backticks."""
        store = MemoryRuleStore()
        middleware = RulesMiddleware(store)
        
        content = "Check `src/main.py` and `tests/test_main.py`"
        files = middleware._extract_file_references(content)
        
        assert "src/main.py" in files
        assert "tests/test_main.py" in files

    def test_extract_file_prefix_references(self) -> None:
        """Test extracting file: prefix references."""
        store = MemoryRuleStore()
        middleware = RulesMiddleware(store)
        
        content = "See file:config.yaml for details"
        files = middleware._extract_file_references(content)
        
        assert "config.yaml" in files

    def test_extract_path_prefix_references(self) -> None:
        """Test extracting path: prefix references."""
        store = MemoryRuleStore()
        middleware = RulesMiddleware(store)
        
        content = "Located at path:/etc/config.json"
        files = middleware._extract_file_references(content)
        
        assert "/etc/config.json" in files


class TestGetTriggeredRules:
    """Tests for get_triggered_rules method."""

    def test_get_triggered_rules_returns_final_rules(self) -> None:
        """Test that get_triggered_rules returns final rule names."""
        store = MemoryRuleStore()
        rule = Rule(
            name="triggered-rule",
            description="Triggered",
            content="Content",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.ALWAYS,
        )
        store.save_rule(rule)
        
        middleware = RulesMiddleware(store)
        
        request = MockModelRequest(messages=[MockMessage("Hello")])
        handler = MagicMock(return_value=MockModelResponse())
        middleware.wrap_model_call(request, handler)
        
        triggered = middleware.get_triggered_rules()
        assert "triggered-rule" in triggered

    def test_get_triggered_rules_empty_before_call(self) -> None:
        """Test that get_triggered_rules returns empty list before any call."""
        store = MemoryRuleStore()
        middleware = RulesMiddleware(store)
        
        triggered = middleware.get_triggered_rules()
        assert triggered == []



class TestEventEmission:
    """Tests for event emission functionality."""

    def test_emits_rules_applied_event(self) -> None:
        """Test that RulesAppliedEvent is emitted."""
        store = MemoryRuleStore()
        rule = Rule(
            name="event-rule",
            description="Event test rule",
            content="Content",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.ALWAYS,
        )
        store.save_rule(rule)
        
        events: list = []
        middleware = RulesMiddleware(store, event_callback=events.append)
        
        request = MockModelRequest(messages=[MockMessage("Hello")])
        handler = MagicMock(return_value=MockModelResponse())
        middleware.wrap_model_call(request, handler)
        
        # Check that RulesAppliedEvent was emitted
        from dataagent_core.events.rules import RulesAppliedEvent
        applied_events = [e for e in events if isinstance(e, RulesAppliedEvent)]
        assert len(applied_events) == 1
        assert len(applied_events[0].triggered_rules) == 1
        assert applied_events[0].triggered_rules[0]["name"] == "event-rule"

    def test_emits_debug_event_when_debug_mode(self) -> None:
        """Test that RuleDebugEvent is emitted in debug mode."""
        store = MemoryRuleStore()
        rule = Rule(
            name="debug-event-rule",
            description="Debug event test",
            content="Content",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.ALWAYS,
        )
        store.save_rule(rule)
        
        events: list = []
        middleware = RulesMiddleware(
            store,
            debug_mode=True,
            event_callback=events.append,
        )
        
        request = MockModelRequest(messages=[MockMessage("Hello")])
        handler = MagicMock(return_value=MockModelResponse())
        middleware.wrap_model_call(request, handler)
        
        # Check that RuleDebugEvent was emitted
        from dataagent_core.events.rules import RuleDebugEvent
        debug_events = [e for e in events if isinstance(e, RuleDebugEvent)]
        assert len(debug_events) == 1
        assert "debug-event-rule" in debug_events[0].final_rules

    def test_no_events_without_callback(self) -> None:
        """Test that no events are emitted without callback."""
        store = MemoryRuleStore()
        rule = Rule(
            name="no-callback-rule",
            description="No callback test",
            content="Content",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.ALWAYS,
        )
        store.save_rule(rule)
        
        # No event_callback provided
        middleware = RulesMiddleware(store)
        
        request = MockModelRequest(messages=[MockMessage("Hello")])
        handler = MagicMock(return_value=MockModelResponse())
        
        # Should not raise any errors
        middleware.wrap_model_call(request, handler)

    def test_event_contains_conflict_info(self) -> None:
        """Test that events contain conflict information."""
        store = MemoryRuleStore()
        # Create two rules with same name at different scopes
        rule1 = Rule(
            name="conflict-rule",
            description="First rule",
            content="Content 1",
            scope=RuleScope.GLOBAL,
            inclusion=RuleInclusion.ALWAYS,
        )
        rule2 = Rule(
            name="conflict-rule",
            description="Second rule",
            content="Content 2",
            scope=RuleScope.USER,
            inclusion=RuleInclusion.ALWAYS,
            override=True,
        )
        store.save_rule(rule1)
        store.save_rule(rule2)
        
        events: list = []
        middleware = RulesMiddleware(store, event_callback=events.append)
        
        request = MockModelRequest(messages=[MockMessage("Hello")])
        handler = MagicMock(return_value=MockModelResponse())
        middleware.wrap_model_call(request, handler)
        
        from dataagent_core.events.rules import RulesAppliedEvent
        applied_events = [e for e in events if isinstance(e, RulesAppliedEvent)]
        assert len(applied_events) == 1
        # Should have conflict info
        assert len(applied_events[0].conflicts) > 0
