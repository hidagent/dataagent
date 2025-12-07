"""Tests for UserProfile data model."""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st

from dataagent_core.user.profile import UserProfile


class TestUserProfile:
    """Tests for UserProfile dataclass."""
    
    def test_create_minimal(self):
        """Test creating profile with minimal fields."""
        profile = UserProfile(
            user_id="user1",
            username="testuser",
            display_name="测试用户",
        )
        
        assert profile.user_id == "user1"
        assert profile.username == "testuser"
        assert profile.display_name == "测试用户"
        assert profile.email is None
        assert profile.department is None
        assert profile.role is None
        assert profile.custom_fields == {}
        assert profile.created_at is not None
        assert profile.updated_at is not None
    
    def test_create_full(self):
        """Test creating profile with all fields."""
        now = datetime.now()
        profile = UserProfile(
            user_id="user1",
            username="testuser",
            display_name="测试用户",
            email="test@example.com",
            department="技术部",
            role="工程师",
            custom_fields={"level": "P7", "team": "数据平台"},
            created_at=now,
            updated_at=now,
        )
        
        assert profile.email == "test@example.com"
        assert profile.department == "技术部"
        assert profile.role == "工程师"
        assert profile.custom_fields == {"level": "P7", "team": "数据平台"}
    
    def test_to_dict(self):
        """Test converting profile to dictionary."""
        profile = UserProfile(
            user_id="user1",
            username="testuser",
            display_name="测试用户",
            department="技术部",
        )
        
        data = profile.to_dict()
        
        assert data["user_id"] == "user1"
        assert data["username"] == "testuser"
        assert data["display_name"] == "测试用户"
        assert data["department"] == "技术部"
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_from_dict(self):
        """Test creating profile from dictionary."""
        data = {
            "user_id": "user1",
            "username": "testuser",
            "display_name": "测试用户",
            "email": "test@example.com",
            "department": "技术部",
            "role": "工程师",
            "custom_fields": {"level": "P7"},
        }
        
        profile = UserProfile.from_dict(data)
        
        assert profile.user_id == "user1"
        assert profile.username == "testuser"
        assert profile.display_name == "测试用户"
        assert profile.email == "test@example.com"
        assert profile.department == "技术部"
        assert profile.role == "工程师"
        assert profile.custom_fields == {"level": "P7"}
    
    def test_from_dict_with_datetime_strings(self):
        """Test creating profile from dictionary with datetime strings."""
        now = datetime.now()
        data = {
            "user_id": "user1",
            "username": "testuser",
            "display_name": "测试用户",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        
        profile = UserProfile.from_dict(data)
        
        assert profile.created_at is not None
        assert profile.updated_at is not None
    
    def test_to_context_excludes_email(self):
        """Test that to_context excludes email by default."""
        profile = UserProfile(
            user_id="user1",
            username="testuser",
            display_name="测试用户",
            email="test@example.com",
        )
        
        context = profile.to_context()
        
        assert "email" not in context
        assert context["user_id"] == "user1"
        assert context["display_name"] == "测试用户"
    
    def test_to_context_includes_email_when_requested(self):
        """Test that to_context includes email when requested."""
        profile = UserProfile(
            user_id="user1",
            username="testuser",
            display_name="测试用户",
            email="test@example.com",
        )
        
        context = profile.to_context(include_sensitive=True)
        
        assert context["email"] == "test@example.com"
    
    def test_update(self):
        """Test updating profile fields."""
        profile = UserProfile(
            user_id="user1",
            username="testuser",
            display_name="测试用户",
        )
        old_updated_at = profile.updated_at
        
        profile.update(display_name="新名字", department="新部门")
        
        assert profile.display_name == "新名字"
        assert profile.department == "新部门"
        assert profile.updated_at > old_updated_at
    
    def test_update_ignores_user_id(self):
        """Test that update ignores user_id."""
        profile = UserProfile(
            user_id="user1",
            username="testuser",
            display_name="测试用户",
        )
        
        profile.update(user_id="user2")
        
        assert profile.user_id == "user1"


class TestUserProfilePropertyTests:
    """Property-based tests for UserProfile."""
    
    @given(
        user_id=st.text(min_size=1, max_size=64),
        username=st.text(min_size=1, max_size=64),
        display_name=st.text(min_size=1, max_size=128),
        email=st.one_of(st.none(), st.emails()),
        department=st.one_of(st.none(), st.text(max_size=128)),
        role=st.one_of(st.none(), st.text(max_size=64)),
    )
    def test_serialization_roundtrip(
        self, user_id, username, display_name, email, department, role
    ):
        """Property 2: 用户档案字段完整性
        
        For any UserProfile with standard fields set, serializing then
        deserializing SHALL produce an equivalent profile with all fields preserved.
        """
        profile = UserProfile(
            user_id=user_id,
            username=username,
            display_name=display_name,
            email=email,
            department=department,
            role=role,
        )
        
        # Serialize and deserialize
        data = profile.to_dict()
        restored = UserProfile.from_dict(data)
        
        # Verify all fields preserved
        assert restored.user_id == profile.user_id
        assert restored.username == profile.username
        assert restored.display_name == profile.display_name
        assert restored.email == profile.email
        assert restored.department == profile.department
        assert restored.role == profile.role
    
    @given(
        custom_fields=st.dictionaries(
            keys=st.text(min_size=1, max_size=32),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(),
                st.floats(allow_nan=False),
                st.booleans(),
            ),
            max_size=10,
        )
    )
    def test_custom_fields_roundtrip(self, custom_fields):
        """Property 3: 自定义字段支持
        
        For any UserProfile with custom_fields, the custom fields SHALL be
        preserved through serialization and deserialization.
        """
        profile = UserProfile(
            user_id="user1",
            username="testuser",
            display_name="测试用户",
            custom_fields=custom_fields,
        )
        
        # Serialize and deserialize
        data = profile.to_dict()
        restored = UserProfile.from_dict(data)
        
        # Verify custom fields preserved
        assert restored.custom_fields == profile.custom_fields
    
    @given(
        email=st.emails(),
    )
    def test_context_excludes_sensitive_info(self, email):
        """Property 8: Prompt 不包含敏感信息
        
        For any system prompt generated with user context, the prompt SHALL NOT
        contain the user's email address.
        """
        profile = UserProfile(
            user_id="user1",
            username="testuser",
            display_name="测试用户",
            email=email,
        )
        
        context = profile.to_context(include_sensitive=False)
        
        # Email should not be in context
        assert "email" not in context
