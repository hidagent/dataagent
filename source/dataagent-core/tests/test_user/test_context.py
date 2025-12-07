"""Tests for UserContextManager."""

import pytest
from hypothesis import given, strategies as st, settings

from dataagent_core.user.profile import UserProfile
from dataagent_core.user.store import MemoryUserProfileStore
from dataagent_core.user.context import UserContextManager, build_user_context_prompt


class TestUserContextManager:
    """Tests for UserContextManager."""
    
    @pytest.fixture
    def store(self):
        """Create a fresh store for each test."""
        return MemoryUserProfileStore()
    
    @pytest.fixture
    def manager(self, store):
        """Create a context manager with the store."""
        return UserContextManager(store)
    
    @pytest.fixture
    def sample_profile(self):
        """Create a sample profile."""
        return UserProfile(
            user_id="user1",
            username="zhangsan",
            display_name="张三",
            email="zhangsan@example.com",
            department="数据部",
            role="数据工程师",
            custom_fields={"level": "P7"},
        )
    
    @pytest.mark.asyncio
    async def test_get_user_context_existing(self, manager, store, sample_profile):
        """Test getting context for existing user."""
        await store.save_profile(sample_profile)
        
        context = await manager.get_user_context("user1")
        
        assert context["user_id"] == "user1"
        assert context["username"] == "zhangsan"
        assert context["display_name"] == "张三"
        assert context["department"] == "数据部"
        assert context["role"] == "数据工程师"
        assert context["is_anonymous"] is False
        # Email should NOT be in context (sensitive)
        assert "email" not in context
    
    @pytest.mark.asyncio
    async def test_get_user_context_nonexistent(self, manager):
        """Test getting context for nonexistent user."""
        context = await manager.get_user_context("nonexistent")
        
        assert context["user_id"] == "nonexistent"
        assert context["is_anonymous"] is True
    
    @pytest.mark.asyncio
    async def test_get_user_profile(self, manager, store, sample_profile):
        """Test getting user profile."""
        await store.save_profile(sample_profile)
        
        profile = await manager.get_user_profile("user1")
        
        assert profile is not None
        assert profile.user_id == "user1"
    
    @pytest.mark.asyncio
    async def test_save_user_profile(self, manager, sample_profile):
        """Test saving user profile."""
        await manager.save_user_profile(sample_profile)
        
        profile = await manager.get_user_profile("user1")
        
        assert profile is not None
        assert profile.display_name == "张三"
    
    def test_build_system_prompt_section_existing(self, manager, sample_profile):
        """Test building system prompt section for existing user."""
        context = sample_profile.to_context()
        context["is_anonymous"] = False
        
        prompt = manager.build_system_prompt_section(context)
        
        assert "张三" in prompt
        assert "zhangsan" in prompt
        assert "数据部" in prompt
        assert "数据工程师" in prompt
        assert "我" in prompt  # Pronoun resolution instructions
        assert "email" not in prompt.lower()  # No email
    
    def test_build_system_prompt_section_anonymous(self, manager):
        """Test building system prompt section for anonymous user."""
        context = {"user_id": "unknown_user", "is_anonymous": True}
        
        prompt = manager.build_system_prompt_section(context)
        
        assert "unknown_user" in prompt
        assert "尚未配置" in prompt or "尚未设置" in prompt
    
    def test_build_system_prompt_section_with_custom_fields(self, manager):
        """Test building system prompt section with custom fields."""
        context = {
            "user_id": "user1",
            "username": "zhangsan",
            "display_name": "张三",
            "department": "数据部",
            "role": "工程师",
            "custom_fields": {"level": "P7", "team": "数据平台"},
            "is_anonymous": False,
        }
        
        prompt = manager.build_system_prompt_section(context)
        
        assert "level" in prompt
        assert "P7" in prompt
        assert "team" in prompt
        assert "数据平台" in prompt


class TestBuildUserContextPrompt:
    """Tests for build_user_context_prompt helper function."""
    
    def test_none_context(self):
        """Test with None context."""
        result = build_user_context_prompt(None)
        assert result == ""
    
    def test_empty_context(self):
        """Test with empty context."""
        result = build_user_context_prompt({})
        assert result == ""
    
    def test_anonymous_context(self):
        """Test with anonymous context."""
        context = {"user_id": "user1", "is_anonymous": True}
        
        result = build_user_context_prompt(context)
        
        assert "user1" in result
        assert "尚未配置" in result
    
    def test_full_context(self):
        """Test with full user context."""
        context = {
            "user_id": "user1",
            "username": "zhangsan",
            "display_name": "张三",
            "department": "数据部",
            "role": "工程师",
            "is_anonymous": False,
        }
        
        result = build_user_context_prompt(context)
        
        assert "张三" in result
        assert "zhangsan" in result
        assert "数据部" in result
        assert "我" in result  # Pronoun resolution


class TestUserContextPropertyTests:
    """Property-based tests for user context."""
    
    @given(
        user_id=st.text(min_size=1, max_size=64),
        username=st.text(min_size=1, max_size=64),
        display_name=st.text(min_size=1, max_size=128),
        email=st.emails(),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_system_prompt_contains_user_info(
        self, user_id, username, display_name, email
    ):
        """Property 1: System Prompt 包含用户信息
        
        For any user with a valid profile, when a message is sent, the system
        prompt SHALL contain the user's display_name and user_id.
        """
        store = MemoryUserProfileStore()
        manager = UserContextManager(store)
        
        profile = UserProfile(
            user_id=user_id,
            username=username,
            display_name=display_name,
            email=email,
        )
        await store.save_profile(profile)
        
        context = await manager.get_user_context(user_id)
        prompt = manager.build_system_prompt_section(context)
        
        # System prompt should contain user_id and display_name
        assert user_id in prompt
        assert display_name in prompt
    
    @given(
        email=st.emails(),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_system_prompt_excludes_email(self, email):
        """Property 8: Prompt 不包含敏感信息
        
        For any system prompt generated with user context, the prompt SHALL NOT
        contain the user's email address.
        """
        store = MemoryUserProfileStore()
        manager = UserContextManager(store)
        
        profile = UserProfile(
            user_id="user1",
            username="testuser",
            display_name="测试用户",
            email=email,
        )
        await store.save_profile(profile)
        
        context = await manager.get_user_context("user1")
        prompt = manager.build_system_prompt_section(context)
        
        # Email should NOT be in the prompt
        assert email not in prompt
