"""Tests for memory middleware user isolation.

Property 54: 用户记忆隔离
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dataagent_core.config import Settings
from dataagent_core.middleware.memory import AgentMemoryMiddleware


class TestMemoryIsolation:
    """Tests for user memory isolation.
    
    Property 54: 用户记忆隔离
    """

    def test_single_tenant_path(self):
        """Test single-tenant mode uses standard path."""
        settings = MagicMock(spec=Settings)
        settings.user_deepagents_dir = Path("/home/user/.deepagents")
        settings.get_agent_dir.return_value = Path("/home/user/.deepagents/agent1")
        settings.project_root = None
        
        middleware = AgentMemoryMiddleware(
            settings=settings,
            assistant_id="agent1",
        )
        
        assert middleware.agent_dir == Path("/home/user/.deepagents/agent1")
        assert "users" not in str(middleware.agent_dir)

    def test_multi_tenant_path(self):
        """Property 54: 多租户模式使用用户隔离路径."""
        settings = MagicMock(spec=Settings)
        settings.user_deepagents_dir = Path("/home/user/.deepagents")
        settings.project_root = None
        
        middleware = AgentMemoryMiddleware(
            settings=settings,
            assistant_id="agent1",
            user_id="user123",
        )
        
        expected = Path("/home/user/.deepagents/users/user123/agent1")
        assert middleware.agent_dir == expected
        assert "users/user123" in str(middleware.agent_dir)

    def test_different_users_different_paths(self):
        """Property 54: 不同用户有不同的记忆路径."""
        settings = MagicMock(spec=Settings)
        settings.user_deepagents_dir = Path("/home/user/.deepagents")
        settings.project_root = None
        
        middleware1 = AgentMemoryMiddleware(
            settings=settings,
            assistant_id="agent1",
            user_id="user1",
        )
        middleware2 = AgentMemoryMiddleware(
            settings=settings,
            assistant_id="agent1",
            user_id="user2",
        )
        
        assert middleware1.agent_dir != middleware2.agent_dir
        assert "user1" in str(middleware1.agent_dir)
        assert "user2" in str(middleware2.agent_dir)

    def test_get_user_memory_path(self):
        """Property 54: 获取用户记忆文件路径."""
        settings = MagicMock(spec=Settings)
        settings.user_deepagents_dir = Path("/home/user/.deepagents")
        settings.project_root = None
        
        middleware = AgentMemoryMiddleware(
            settings=settings,
            assistant_id="agent1",
            user_id="user123",
        )
        
        memory_path = middleware.get_user_memory_path()
        expected = Path("/home/user/.deepagents/users/user123/agent1/agent.md")
        assert memory_path == expected

    def test_ensure_memory_dir(self):
        """Property 54: 确保记忆目录存在."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = MagicMock(spec=Settings)
            settings.user_deepagents_dir = Path(tmpdir)
            settings.project_root = None
            
            middleware = AgentMemoryMiddleware(
                settings=settings,
                assistant_id="agent1",
                user_id="user123",
            )
            
            middleware.ensure_memory_dir()
            assert middleware.agent_dir.exists()

    def test_clear_memory(self):
        """Property 54: 清除用户记忆."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = MagicMock(spec=Settings)
            settings.user_deepagents_dir = Path(tmpdir)
            settings.project_root = None
            
            middleware = AgentMemoryMiddleware(
                settings=settings,
                assistant_id="agent1",
                user_id="user123",
            )
            
            # Create memory
            middleware.ensure_memory_dir()
            memory_path = middleware.get_user_memory_path()
            memory_path.write_text("test memory")
            
            # Clear memory
            result = middleware.clear_memory()
            assert result is True
            assert not middleware.agent_dir.exists()

    def test_clear_memory_nonexistent(self):
        """Property 54: 清除不存在的记忆返回 False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = MagicMock(spec=Settings)
            settings.user_deepagents_dir = Path(tmpdir)
            settings.project_root = None
            
            middleware = AgentMemoryMiddleware(
                settings=settings,
                assistant_id="agent1",
                user_id="nonexistent",
            )
            
            result = middleware.clear_memory()
            assert result is False

    def test_user_memory_isolation_in_before_agent(self):
        """Property 54: before_agent 加载用户隔离的记忆."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = MagicMock(spec=Settings)
            settings.user_deepagents_dir = Path(tmpdir)
            settings.project_root = None
            settings.get_project_agent_md_path.return_value = None
            
            # Create memory for user1
            middleware1 = AgentMemoryMiddleware(
                settings=settings,
                assistant_id="agent1",
                user_id="user1",
            )
            middleware1.ensure_memory_dir()
            middleware1.get_user_memory_path().write_text("User 1 memory")
            
            # Create memory for user2
            middleware2 = AgentMemoryMiddleware(
                settings=settings,
                assistant_id="agent1",
                user_id="user2",
            )
            middleware2.ensure_memory_dir()
            middleware2.get_user_memory_path().write_text("User 2 memory")
            
            # Load memory for user1
            state1 = middleware1.before_agent({}, MagicMock())
            assert state1.get("user_memory") == "User 1 memory"
            
            # Load memory for user2
            state2 = middleware2.before_agent({}, MagicMock())
            assert state2.get("user_memory") == "User 2 memory"

    def test_agent_dir_display_format(self):
        """Property 54: 显示路径格式正确."""
        settings = MagicMock(spec=Settings)
        settings.user_deepagents_dir = Path("/home/user/.deepagents")
        settings.project_root = None
        
        # Single tenant
        middleware1 = AgentMemoryMiddleware(
            settings=settings,
            assistant_id="agent1",
        )
        settings.get_agent_dir.return_value = Path("/home/user/.deepagents/agent1")
        assert middleware1.agent_dir_display == "~/.deepagents/agent1"
        
        # Multi tenant
        middleware2 = AgentMemoryMiddleware(
            settings=settings,
            assistant_id="agent1",
            user_id="user123",
        )
        assert middleware2.agent_dir_display == "~/.deepagents/users/user123/agent1"
