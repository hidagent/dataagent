"""Tests for SQLiteUserProfileStore."""

import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings

from dataagent_core.user.profile import UserProfile
from dataagent_core.user.sqlite_store import SQLiteUserProfileStore


class TestSQLiteUserProfileStore:
    """Tests for SQLiteUserProfileStore."""
    
    @pytest.fixture
    async def store(self):
        """Create a fresh store with temp database for each test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SQLiteUserProfileStore(db_path)
            await store.init_tables()
            yield store
            await store.close()
    
    @pytest.fixture
    def sample_profile(self):
        """Create a sample profile."""
        return UserProfile(
            user_id="user1",
            username="testuser",
            display_name="测试用户",
            email="test@example.com",
            department="技术部",
            role="工程师",
            custom_fields={"level": "P7", "team": "数据平台"},
        )
    
    @pytest.mark.asyncio
    async def test_save_and_get(self, store, sample_profile):
        """Test saving and retrieving a profile."""
        await store.save_profile(sample_profile)
        
        retrieved = await store.get_profile("user1")
        
        assert retrieved is not None
        assert retrieved.user_id == "user1"
        assert retrieved.username == "testuser"
        assert retrieved.display_name == "测试用户"
        assert retrieved.email == "test@example.com"
        assert retrieved.department == "技术部"
        assert retrieved.role == "工程师"
        assert retrieved.custom_fields == {"level": "P7", "team": "数据平台"}
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store):
        """Test getting a nonexistent profile."""
        result = await store.get_profile("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete(self, store, sample_profile):
        """Test deleting a profile."""
        await store.save_profile(sample_profile)
        
        result = await store.delete_profile("user1")
        
        assert result is True
        assert await store.get_profile("user1") is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, store):
        """Test deleting a nonexistent profile."""
        result = await store.delete_profile("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_update(self, store, sample_profile):
        """Test updating a profile."""
        await store.save_profile(sample_profile)
        
        updated = await store.update_profile("user1", {
            "display_name": "新名字",
            "department": "新部门",
            "custom_fields": {"level": "P8"},
        })
        
        assert updated is not None
        assert updated.display_name == "新名字"
        assert updated.department == "新部门"
        assert updated.custom_fields == {"level": "P8"}
        assert updated.username == "testuser"  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_nonexistent(self, store):
        """Test updating a nonexistent profile."""
        result = await store.update_profile("nonexistent", {"display_name": "新名字"})
        assert result is None
    
    @pytest.mark.asyncio
    async def test_list_profiles(self, store):
        """Test listing all profiles."""
        profile1 = UserProfile(
            user_id="user1",
            username="user1",
            display_name="用户1",
        )
        profile2 = UserProfile(
            user_id="user2",
            username="user2",
            display_name="用户2",
        )
        
        await store.save_profile(profile1)
        await store.save_profile(profile2)
        
        profiles = await store.list_profiles()
        
        assert len(profiles) == 2
        user_ids = {p.user_id for p in profiles}
        assert user_ids == {"user1", "user2"}
    
    @pytest.mark.asyncio
    async def test_save_overwrites_existing(self, store, sample_profile):
        """Test that saving overwrites existing profile."""
        await store.save_profile(sample_profile)
        
        updated_profile = UserProfile(
            user_id="user1",
            username="newuser",
            display_name="新用户",
        )
        await store.save_profile(updated_profile)
        
        retrieved = await store.get_profile("user1")
        assert retrieved.username == "newuser"
        assert retrieved.display_name == "新用户"
    
    @pytest.mark.asyncio
    async def test_custom_fields_persistence(self, store):
        """Test that custom fields are persisted correctly."""
        profile = UserProfile(
            user_id="user1",
            username="testuser",
            display_name="测试用户",
            custom_fields={
                "string_field": "value",
                "int_field": 42,
                "float_field": 3.14,
                "bool_field": True,
                "nested": {"key": "value"},
            },
        )
        
        await store.save_profile(profile)
        retrieved = await store.get_profile("user1")
        
        assert retrieved.custom_fields["string_field"] == "value"
        assert retrieved.custom_fields["int_field"] == 42
        assert retrieved.custom_fields["float_field"] == 3.14
        assert retrieved.custom_fields["bool_field"] is True
        assert retrieved.custom_fields["nested"] == {"key": "value"}


class TestSQLiteUserProfileStorePropertyTests:
    """Property-based tests for SQLiteUserProfileStore."""
    
    @given(
        user_id=st.text(min_size=1, max_size=64, alphabet=st.characters(
            whitelist_categories=("L", "N"),
            whitelist_characters="_-"
        )),
        username=st.text(min_size=1, max_size=64, alphabet=st.characters(
            whitelist_categories=("L", "N"),
            whitelist_characters="_-"
        )),
        display_name=st.text(min_size=1, max_size=128),
        custom_fields=st.dictionaries(
            keys=st.text(min_size=1, max_size=32, alphabet=st.characters(
                whitelist_categories=("L", "N"),
                whitelist_characters="_"
            )),
            values=st.text(max_size=100),
            max_size=5,
        ),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_save_get_roundtrip(
        self, user_id, username, display_name, custom_fields
    ):
        """Property 3: 自定义字段支持
        
        For any UserProfile with custom_fields, the custom fields SHALL be
        preserved through storage and retrieval.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SQLiteUserProfileStore(db_path)
            await store.init_tables()
            
            try:
                profile = UserProfile(
                    user_id=user_id,
                    username=username,
                    display_name=display_name,
                    custom_fields=custom_fields,
                )
                
                await store.save_profile(profile)
                retrieved = await store.get_profile(user_id)
                
                assert retrieved is not None
                assert retrieved.user_id == user_id
                assert retrieved.username == username
                assert retrieved.display_name == display_name
                assert retrieved.custom_fields == custom_fields
            finally:
                await store.close()
