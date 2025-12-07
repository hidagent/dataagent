"""Rules middleware for injecting agent rules into system prompt.

This middleware loads and applies agent rules based on context,
supporting always, fileMatch, and manual inclusion modes.

**Feature: agent-rules**
**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 13.1, 13.2, 13.3, 13.4**
"""

import re
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, NotRequired, TypedDict, cast

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langgraph.runtime import Runtime

from dataagent_core.rules.models import Rule, RuleEvaluationTrace, RuleMatch
from dataagent_core.rules.store import RuleStore
from dataagent_core.rules.matcher import RuleMatcher, MatchContext
from dataagent_core.rules.merger import RuleMerger
from dataagent_core.events.rules import RulesAppliedEvent, RuleDebugEvent


class RulesState(AgentState):
    """State for the rules middleware."""
    rules_loaded: NotRequired[bool]
    triggered_rules: NotRequired[list[str]]
    rule_trace: NotRequired[dict[str, Any]]


class RulesStateUpdate(TypedDict):
    """State update for the rules middleware."""
    rules_loaded: bool
    triggered_rules: list[str]
    rule_trace: dict[str, Any]


# Pattern for manual rule references: @rulename
RULES_MANUAL_REFERENCE_PATTERN = re.compile(r"@(\w[\w\-]*)")


class RulesMiddleware(AgentMiddleware):
    """Middleware for loading and applying agent rules.
    
    This middleware:
    1. Loads rules from the configured RuleStore
    2. Matches rules based on context (files, manual references)
    3. Merges rules by priority and scope
    4. Injects rule content into the system prompt
    5. Records evaluation traces for debugging
    """

    state_schema = RulesState

    def __init__(
        self,
        store: RuleStore,
        *,
        debug_mode: bool = False,
        max_content_size: int = 100_000,
        event_callback: Callable[[RulesAppliedEvent | RuleDebugEvent], None] | None = None,
    ) -> None:
        """Initialize rules middleware.
        
        Args:
            store: The rule store to load rules from.
            debug_mode: If True, include debug info in system prompt.
            max_content_size: Maximum total size of rule content.
            event_callback: Optional callback to receive rule events.
        """
        self.store = store
        self.matcher = RuleMatcher()
        self.merger = RuleMerger(max_content_size=max_content_size)
        self.debug_mode = debug_mode
        self._last_trace: RuleEvaluationTrace | None = None
        self._event_callback = event_callback

    def before_agent(
        self,
        state: RulesState,
        runtime: Runtime,
    ) -> RulesStateUpdate | None:
        """Load rules before agent execution."""
        # Reload rules to pick up any changes
        self.store.reload()
        return RulesStateUpdate(
            rules_loaded=True,
            triggered_rules=[],
            rule_trace={},
        )

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Synchronously wrap model call with rule injection."""
        modified_request = self._inject_rules(request)
        return handler(modified_request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Asynchronously wrap model call with rule injection."""
        modified_request = self._inject_rules(request)
        return await handler(modified_request)

    def _inject_rules(self, request: ModelRequest) -> ModelRequest:
        """Inject rules into the request's system prompt."""
        # Build match context from request
        context = self._build_match_context(request)
        
        # Get all rules from store
        all_rules = self.store.list_rules()
        
        # Match rules against context
        matched, skipped = self.matcher.match_rules(all_rules, context)
        
        # Merge matched rules
        final_rules, conflicts = self.merger.merge_rules(matched)
        
        # Record trace
        request_id = str(uuid.uuid4())[:8]
        trace = RuleEvaluationTrace(
            request_id=request_id,
            timestamp=datetime.now(),
            evaluated_rules=[r.name for r in all_rules],
            matched_rules=matched,
            skipped_rules=skipped,
            conflicts=conflicts,
            final_rules=[r.name for r in final_rules],
            total_content_size=sum(len(r.content) for r in final_rules),
        )
        self._last_trace = trace
        
        # Emit events
        self._emit_events(trace, matched, conflicts)
        
        # Build rules section for system prompt
        rules_section = self.merger.build_prompt_section(final_rules)
        
        # Add debug info if enabled
        if self.debug_mode:
            rules_section += self._build_debug_section(trace)
        
        # Combine with existing system prompt
        if rules_section:
            if request.system_prompt:
                new_system_prompt = f"{request.system_prompt}\n\n{rules_section}"
            else:
                new_system_prompt = rules_section
            return request.override(system_prompt=new_system_prompt)
        
        return request

    def _build_match_context(self, request: ModelRequest) -> MatchContext:
        """Build match context from the model request."""
        user_query = ""
        current_files: list[str] = []
        
        # Extract user query from messages
        for msg in request.messages:
            if hasattr(msg, "content") and isinstance(msg.content, str):
                user_query = msg.content
                # Extract file references from content
                current_files.extend(self._extract_file_references(msg.content))
        
        # Extract manual rule references (@rulename)
        manual_rules = RULES_MANUAL_REFERENCE_PATTERN.findall(user_query)
        
        # Get session/assistant info from state
        state = cast("RulesState", request.state)
        session_id = state.get("session_id", "")
        assistant_id = state.get("assistant_id", "")
        
        return MatchContext(
            current_files=current_files,
            user_query=user_query,
            session_id=session_id,
            assistant_id=assistant_id,
            manual_rules=manual_rules,
        )

    def _extract_file_references(self, content: str) -> list[str]:
        """Extract file references from message content."""
        files: list[str] = []
        
        # Match files in backticks: `path/to/file.py`
        backtick_pattern = r"`([^`]+\.\w+)`"
        files.extend(re.findall(backtick_pattern, content))
        
        # Match file: prefix
        file_prefix_pattern = r"file:([^\s]+)"
        files.extend(re.findall(file_prefix_pattern, content))
        
        # Match path: prefix
        path_prefix_pattern = r"path:([^\s]+)"
        files.extend(re.findall(path_prefix_pattern, content))
        
        return files

    def _build_debug_section(self, trace: RuleEvaluationTrace) -> str:
        """Build debug information section."""
        lines = [
            "\n---",
            "## [DEBUG] Rule Evaluation Trace",
            f"Request ID: {trace.request_id}",
            f"Timestamp: {trace.timestamp.isoformat()}",
            f"Evaluated: {len(trace.evaluated_rules)} rules",
            f"Matched: {len(trace.matched_rules)} rules",
            f"Final: {len(trace.final_rules)} rules",
            f"Total Size: {trace.total_content_size} chars",
            "",
            "### Triggered Rules:",
        ]
        
        for match in trace.matched_rules:
            lines.append(
                f"- {match.rule.name} ({match.rule.scope.value}): {match.match_reason}"
            )
            if match.matched_files:
                lines.append(f"  Files: {', '.join(match.matched_files)}")
        
        if trace.skipped_rules:
            lines.append("\n### Skipped Rules:")
            # Limit to first 10 to avoid overwhelming output
            for name, reason in trace.skipped_rules[:10]:
                lines.append(f"- {name}: {reason}")
            if len(trace.skipped_rules) > 10:
                lines.append(f"  ... and {len(trace.skipped_rules) - 10} more")
        
        if trace.conflicts:
            lines.append("\n### Conflicts:")
            for r1, r2, reason in trace.conflicts:
                lines.append(f"- {r1} vs {r2}: {reason}")
        
        lines.append("---\n")
        return "\n".join(lines)

    def get_last_trace(self) -> RuleEvaluationTrace | None:
        """Get the last rule evaluation trace."""
        return self._last_trace

    def set_debug_mode(self, enabled: bool) -> None:
        """Enable or disable debug mode."""
        self.debug_mode = enabled

    def get_triggered_rules(self) -> list[str]:
        """Get list of triggered rule names from last evaluation."""
        if self._last_trace:
            return self._last_trace.final_rules
        return []

    def _emit_events(
        self,
        trace: RuleEvaluationTrace,
        matched: list[RuleMatch],
        conflicts: list[tuple[str, str, str]],
    ) -> None:
        """Emit rule events if callback is configured."""
        if not self._event_callback:
            return
        
        # Always emit RulesAppliedEvent
        triggered_rules = [
            {
                "name": m.rule.name,
                "scope": m.rule.scope.value,
                "match_reason": m.match_reason,
            }
            for m in matched
        ]
        conflict_dicts = [
            {"rule1": c[0], "rule2": c[1], "reason": c[2]}
            for c in conflicts
        ]
        
        applied_event = RulesAppliedEvent(
            triggered_rules=triggered_rules,
            skipped_count=len(trace.skipped_rules),
            conflicts=conflict_dicts,
            total_size=trace.total_content_size,
        )
        self._event_callback(applied_event)
        
        # Emit RuleDebugEvent if debug mode is enabled
        if self.debug_mode:
            matched_dicts = [
                {
                    "name": m.rule.name,
                    "scope": m.rule.scope.value,
                    "match_reason": m.match_reason,
                    "matched_files": m.matched_files,
                }
                for m in matched
            ]
            skipped_dicts = [
                {"name": name, "reason": reason}
                for name, reason in trace.skipped_rules
            ]
            
            debug_event = RuleDebugEvent(
                request_id=trace.request_id,
                evaluated_rules=trace.evaluated_rules,
                matched_rules=matched_dicts,
                skipped_rules=skipped_dicts,
                conflicts=conflict_dicts,
                final_rules=trace.final_rules,
                total_content_size=trace.total_content_size,
            )
            self._event_callback(debug_event)
