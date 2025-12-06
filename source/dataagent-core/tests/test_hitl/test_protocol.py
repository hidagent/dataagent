"""Tests for HITL protocol implementation."""

import pytest
from dataagent_core.hitl import HITLHandler, ActionRequest, Decision, AutoApproveHandler


class TestAutoApproveHandler:
    """Tests for AutoApproveHandler."""

    @pytest.mark.asyncio
    async def test_auto_approve_returns_approve_decision(self):
        """Test that AutoApproveHandler always returns approve decision."""
        handler = AutoApproveHandler()
        action_request: ActionRequest = {
            "name": "write_file",
            "args": {"file_path": "/test/file.txt", "content": "test"},
            "description": "Write test file",
        }
        
        decision = await handler.request_approval(action_request, "session_123")
        
        assert decision["type"] == "approve"
        assert decision["message"] is None

    @pytest.mark.asyncio
    async def test_auto_approve_handles_any_action(self):
        """
        **Feature: dataagent-development-specs, Property 8: 无 HITLHandler 时自动批准**
        
        Test that AutoApproveHandler approves any action type.
        """
        handler = AutoApproveHandler()
        
        actions = [
            {"name": "shell", "args": {"command": "ls -la"}, "description": "List files"},
            {"name": "edit_file", "args": {"file_path": "/test.py"}, "description": "Edit file"},
            {"name": "web_search", "args": {"query": "test"}, "description": "Search web"},
        ]
        
        for action in actions:
            decision = await handler.request_approval(action, "session_123")
            assert decision["type"] == "approve"


class TestActionRequest:
    """Tests for ActionRequest type."""

    def test_action_request_has_required_fields(self):
        """Test that ActionRequest contains name, args, description fields."""
        action: ActionRequest = {
            "name": "read_file",
            "args": {"file_path": "/test/file.txt"},
            "description": "Read test file",
        }
        
        assert "name" in action
        assert "args" in action
        assert "description" in action


class TestDecision:
    """Tests for Decision type."""

    def test_approve_decision(self):
        """Test approve decision structure."""
        decision: Decision = {"type": "approve", "message": None}
        assert decision["type"] == "approve"

    def test_reject_decision(self):
        """Test reject decision structure."""
        decision: Decision = {"type": "reject", "message": "User rejected"}
        assert decision["type"] == "reject"
        assert decision["message"] == "User rejected"
