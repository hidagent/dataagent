# 用户记忆多租户隔离方案

## 概述

DataAgent 实现了完整的用户记忆多租户隔离，确保每个租户的 Agent 记忆、用户偏好和上下文信息完全隔离，提供个性化的 AI 体验。

## 架构设计

### 1. 记忆层次结构

```
┌─────────────────────────────────────────────────────────┐
│                    用户记忆系统                           │
├─────────────────────────────────────────────────────────┤
│  Tenant A          │  Tenant B          │  Tenant C      │
│  (user_id: alice)  │  (user_id: bob)    │  (user_id: c1) │
├────────────────────┼────────────────────┼────────────────┤
│ 用户档案           │ 用户档案           │ 用户档案        │
│ (UserProfile)      │ (UserProfile)      │ (UserProfile)  │
├────────────────────┼────────────────────┼────────────────┤
│ Agent 记忆         │ Agent 记忆         │ Agent 记忆      │
│ (AgentMemory)      │ (AgentMemory)      │ (AgentMemory)  │
├────────────────────┼────────────────────┼────────────────┤
│ 会话历史           │ 会话历史           │ 会话历史        │
│ (SessionHistory)   │ (SessionHistory)   │ (SessionHistory)│
├────────────────────┼────────────────────┼────────────────┤
│ 用户偏好           │ 用户偏好           │ 用户偏好        │
│ (UserPreferences)  │ (UserPreferences)  │ (UserPreferences)│
└────────────────────┴────────────────────┴────────────────┘
```

### 2. 记忆类型

| 记忆类型 | 存储位置 | 隔离方式 | 用途 |
|---------|---------|---------|------|
| **用户档案** | 数据库 | `user_id` | 基本身份信息 |
| **Agent 记忆** | 文件系统 | 用户目录 | 长期记忆和学习 |
| **会话历史** | 数据库 | `session_id` | 对话上下文 |
| **用户偏好** | 文件系统 | 用户目录 | 个性化设置 |
| **技能记忆** | 文件系统 | 用户目录 | 学习的技能和模式 |

## 实现细节

### 1. Agent 记忆管理器

```python
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import json


@dataclass
class MemoryEntry:
    """记忆条目。"""
    id: str
    content: str
    category: str  # 'fact', 'preference', 'skill', 'context'
    importance: float  # 0.0 - 1.0
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMemory:
    """Agent 记忆结构。"""
    user_id: str
    entries: List[MemoryEntry] = field(default_factory=list)
    summary: str = ""
    last_updated: datetime = field(default_factory=datetime.now)
    version: int = 1


class AgentMemoryManager:
    """Agent 记忆管理器。"""
    
    def __init__(self, dir_manager: UserDirectoryManager):
        self.dir_manager = dir_manager
    
    def _get_memory_file(self, user_id: str) -> Path:
        """获取用户记忆文件路径。"""
        memory_dir = self.dir_manager.get_user_memory_dir(user_id)
        return memory_dir / "agent.json"
    
    def _get_summary_file(self, user_id: str) -> Path:
        """获取记忆摘要文件路径。"""
        memory_dir = self.dir_manager.get_user_memory_dir(user_id)
        return memory_dir / "summary.md"
    
    async def load_memory(self, user_id: str) -> AgentMemory:
        """加载用户的 Agent 记忆。"""
        memory_file = self._get_memory_file(user_id)
        
        if not memory_file.exists():
            return AgentMemory(user_id=user_id)
        
        try:
            data = json.loads(memory_file.read_text(encoding='utf-8'))
            entries = []
            for entry_data in data.get('entries', []):
                entry = MemoryEntry(
                    id=entry_data['id'],
                    content=entry_data['content'],
                    category=entry_data['category'],
                    importance=entry_data['importance'],
                    created_at=datetime.fromisoformat(entry_data['created_at']),
                    last_accessed=datetime.fromisoformat(entry_data['last_accessed']),
                    access_count=entry_data.get('access_count', 0),
                    tags=entry_data.get('tags', []),
                    metadata=entry_data.get('metadata', {}),
                )
                entries.append(entry)
            
            return AgentMemory(
                user_id=user_id,
                entries=entries,
                summary=data.get('summary', ''),
                last_updated=datetime.fromisoformat(data.get('last_updated', datetime.now().isoformat())),
                version=data.get('version', 1),
            )
        except Exception as e:
            logger.warning(f"Failed to load memory for {user_id}: {e}")
            return AgentMemory(user_id=user_id)
    
    async def save_memory(self, memory: AgentMemory) -> None:
        """保存用户的 Agent 记忆。"""
        memory_file = self._get_memory_file(memory.user_id)
        memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为可序列化的格式
        data = {
            'user_id': memory.user_id,
            'entries': [
                {
                    'id': entry.id,
                    'content': entry.content,
                    'category': entry.category,
                    'importance': entry.importance,
                    'created_at': entry.created_at.isoformat(),
                    'last_accessed': entry.last_accessed.isoformat(),
                    'access_count': entry.access_count,
                    'tags': entry.tags,
                    'metadata': entry.metadata,
                }
                for entry in memory.entries
            ],
            'summary': memory.summary,
            'last_updated': memory.last_updated.isoformat(),
            'version': memory.version,
        }
        
        memory_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        # 同时保存可读的摘要
        await self._save_readable_summary(memory)
    
    async def _save_readable_summary(self, memory: AgentMemory) -> None:
        """保存可读的记忆摘要。"""
        summary_file = self._get_summary_file(memory.user_id)
        
        content = f"""# Agent 记忆摘要

**用户**: {memory.user_id}
**最后更新**: {memory.last_updated.strftime('%Y-%m-%d %H:%M:%S')}
**记忆条目数**: {len(memory.entries)}

## 总体摘要

{memory.summary or '暂无摘要'}

## 重要记忆

"""
        
        # 按重要性排序，显示前10个
        important_entries = sorted(
            memory.entries,
            key=lambda x: x.importance,
            reverse=True
        )[:10]
        
        for entry in important_entries:
            content += f"""### {entry.category.title()} - {entry.id}

**重要性**: {entry.importance:.2f}
**标签**: {', '.join(entry.tags) if entry.tags else '无'}
**访问次数**: {entry.access_count}

{entry.content}

---

"""
        
        summary_file.write_text(content, encoding='utf-8')
    
    async def add_memory(
        self,
        user_id: str,
        content: str,
        category: str = 'fact',
        importance: float = 0.5,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """添加新的记忆条目。"""
        import uuid
        
        memory = await self.load_memory(user_id)
        
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            content=content,
            category=category,
            importance=importance,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            tags=tags or [],
            metadata=metadata or {},
        )
        
        memory.entries.append(entry)
        memory.last_updated = datetime.now()
        
        # 如果记忆条目过多，清理旧的低重要性条目
        await self._cleanup_memory(memory)
        
        await self.save_memory(memory)
        return entry.id
    
    async def search_memory(
        self,
        user_id: str,
        query: str,
        category: str = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """搜索记忆条目。"""
        memory = await self.load_memory(user_id)
        
        # 简单的文本匹配搜索
        results = []
        query_lower = query.lower()
        
        for entry in memory.entries:
            if category and entry.category != category:
                continue
            
            # 检查内容、标签是否匹配
            if (query_lower in entry.content.lower() or
                any(query_lower in tag.lower() for tag in entry.tags)):
                
                # 更新访问信息
                entry.last_accessed = datetime.now()
                entry.access_count += 1
                results.append(entry)
        
        # 按重要性和最近访问排序
        results.sort(
            key=lambda x: (x.importance, x.last_accessed),
            reverse=True
        )
        
        # 保存更新的访问信息
        if results:
            await self.save_memory(memory)
        
        return results[:limit]
    
    async def _cleanup_memory(self, memory: AgentMemory, max_entries: int = 1000) -> None:
        """清理记忆，保留重要的条目。"""
        if len(memory.entries) <= max_entries:
            return
        
        # 按重要性和访问频率排序
        memory.entries.sort(
            key=lambda x: (x.importance, x.access_count, x.last_accessed),
            reverse=True
        )
        
        # 保留前 max_entries 个
        memory.entries = memory.entries[:max_entries]
    
    async def get_context_for_prompt(self, user_id: str, query: str = "") -> str:
        """获取用于 System Prompt 的记忆上下文。"""
        memory = await self.load_memory(user_id)
        
        if not memory.entries:
            return ""
        
        # 如果有查询，搜索相关记忆
        if query:
            relevant_entries = await self.search_memory(user_id, query, limit=5)
        else:
            # 否则获取最重要的记忆
            relevant_entries = sorted(
                memory.entries,
                key=lambda x: x.importance,
                reverse=True
            )[:5]
        
        if not relevant_entries:
            return ""
        
        context = "## 相关记忆\n\n"
        for entry in relevant_entries:
            context += f"- **{entry.category}**: {entry.content}\n"
        
        return context
```

### 2. 用户偏好管理器

```python
@dataclass
class UserPreferences:
    """用户偏好设置。"""
    user_id: str
    language: str = "zh-CN"
    timezone: str = "Asia/Shanghai"
    response_style: str = "professional"  # professional, casual, technical
    max_response_length: int = 1000
    preferred_formats: List[str] = field(default_factory=lambda: ["markdown"])
    notification_settings: Dict[str, bool] = field(default_factory=dict)
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.now)


class UserPreferencesManager:
    """用户偏好管理器。"""
    
    def __init__(self, dir_manager: UserDirectoryManager):
        self.dir_manager = dir_manager
    
    def _get_preferences_file(self, user_id: str) -> Path:
        """获取用户偏好文件路径。"""
        memory_dir = self.dir_manager.get_user_memory_dir(user_id)
        return memory_dir / "preferences.json"
    
    async def load_preferences(self, user_id: str) -> UserPreferences:
        """加载用户偏好。"""
        prefs_file = self._get_preferences_file(user_id)
        
        if not prefs_file.exists():
            return UserPreferences(user_id=user_id)
        
        try:
            data = json.loads(prefs_file.read_text(encoding='utf-8'))
            return UserPreferences(
                user_id=user_id,
                language=data.get('language', 'zh-CN'),
                timezone=data.get('timezone', 'Asia/Shanghai'),
                response_style=data.get('response_style', 'professional'),
                max_response_length=data.get('max_response_length', 1000),
                preferred_formats=data.get('preferred_formats', ['markdown']),
                notification_settings=data.get('notification_settings', {}),
                custom_settings=data.get('custom_settings', {}),
                updated_at=datetime.fromisoformat(
                    data.get('updated_at', datetime.now().isoformat())
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to load preferences for {user_id}: {e}")
            return UserPreferences(user_id=user_id)
    
    async def save_preferences(self, preferences: UserPreferences) -> None:
        """保存用户偏好。"""
        prefs_file = self._get_preferences_file(preferences.user_id)
        prefs_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'user_id': preferences.user_id,
            'language': preferences.language,
            'timezone': preferences.timezone,
            'response_style': preferences.response_style,
            'max_response_length': preferences.max_response_length,
            'preferred_formats': preferences.preferred_formats,
            'notification_settings': preferences.notification_settings,
            'custom_settings': preferences.custom_settings,
            'updated_at': preferences.updated_at.isoformat(),
        }
        
        prefs_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    
    async def update_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
    ) -> UserPreferences:
        """更新单个偏好设置。"""
        preferences = await self.load_preferences(user_id)
        
        if hasattr(preferences, key):
            setattr(preferences, key, value)
        else:
            preferences.custom_settings[key] = value
        
        preferences.updated_at = datetime.now()
        await self.save_preferences(preferences)
        return preferences
```

### 3. 统一记忆上下文管理器

```python
class UnifiedMemoryManager:
    """统一记忆管理器，整合所有记忆组件。"""
    
    def __init__(
        self,
        user_context_manager: UserContextManager,
        agent_memory_manager: AgentMemoryManager,
        preferences_manager: UserPreferencesManager,
    ):
        self.user_context = user_context_manager
        self.agent_memory = agent_memory_manager
        self.preferences = preferences_manager
    
    async def build_full_context(
        self,
        user_id: str,
        query: str = "",
        include_memory: bool = True,
        include_preferences: bool = True,
    ) -> str:
        """构建完整的用户上下文，用于 System Prompt。"""
        context_parts = []
        
        # 1. 用户基本信息
        user_context = await self.user_context.get_user_context(user_id)
        user_section = self.user_context.build_system_prompt_section(user_context)
        if user_section:
            context_parts.append(user_section)
        
        # 2. Agent 记忆
        if include_memory:
            memory_context = await self.agent_memory.get_context_for_prompt(user_id, query)
            if memory_context:
                context_parts.append(memory_context)
        
        # 3. 用户偏好
        if include_preferences:
            preferences = await self.preferences.load_preferences(user_id)
            prefs_context = self._build_preferences_context(preferences)
            if prefs_context:
                context_parts.append(prefs_context)
        
        return "\n\n".join(context_parts)
    
    def _build_preferences_context(self, preferences: UserPreferences) -> str:
        """构建用户偏好的上下文。"""
        if not preferences:
            return ""
        
        context = f"""## 用户偏好

- **语言**: {preferences.language}
- **时区**: {preferences.timezone}
- **回复风格**: {preferences.response_style}
- **最大回复长度**: {preferences.max_response_length} 字符
- **偏好格式**: {', '.join(preferences.preferred_formats)}

请根据用户的偏好调整回复风格和格式。"""
        
        return context
    
    async def learn_from_interaction(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
        feedback: str = None,
    ) -> None:
        """从交互中学习，更新记忆。"""
        # 提取可能的事实和偏好
        facts = await self._extract_facts(user_message, assistant_response)
        preferences = await self._extract_preferences(user_message, feedback)
        
        # 添加到记忆
        for fact in facts:
            await self.agent_memory.add_memory(
                user_id=user_id,
                content=fact,
                category='fact',
                importance=0.6,
            )
        
        for pref in preferences:
            await self.agent_memory.add_memory(
                user_id=user_id,
                content=pref,
                category='preference',
                importance=0.8,
            )
    
    async def _extract_facts(self, user_message: str, response: str) -> List[str]:
        """从对话中提取事实信息。"""
        # 这里可以使用 NLP 技术或 LLM 来提取事实
        # 简化实现：查找明确的陈述
        facts = []
        
        # 查找 "我是"、"我的"、"我在" 等模式
        import re
        patterns = [
            r'我是(.+?)(?:[，。！？]|$)',
            r'我的(.+?)是(.+?)(?:[，。！？]|$)',
            r'我在(.+?)(?:[，。！？]|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, user_message)
            for match in matches:
                if isinstance(match, tuple):
                    facts.append(f"用户的{match[0]}是{match[1]}")
                else:
                    facts.append(f"用户是{match}")
        
        return facts
    
    async def _extract_preferences(self, user_message: str, feedback: str) -> List[str]:
        """从对话中提取偏好信息。"""
        preferences = []
        
        # 查找偏好表达
        pref_patterns = [
            r'我喜欢(.+?)(?:[，。！？]|$)',
            r'我不喜欢(.+?)(?:[，。！？]|$)',
            r'我希望(.+?)(?:[，。！？]|$)',
            r'请(.+?)(?:[，。！？]|$)',
        ]
        
        for pattern in pref_patterns:
            matches = re.findall(pattern, user_message)
            for match in matches:
                preferences.append(f"用户偏好：{match}")
        
        # 从反馈中学习
        if feedback:
            if "太长" in feedback or "简短" in feedback:
                preferences.append("用户偏好简短的回复")
            elif "详细" in feedback or "更多" in feedback:
                preferences.append("用户偏好详细的回复")
        
        return preferences
```

## API 示例

### 1. 记忆管理 API

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter()

class AddMemoryRequest(BaseModel):
    content: str
    category: str = "fact"
    importance: float = 0.5
    tags: List[str] = []

@router.post("/users/{user_id}/memory")
async def add_memory(
    user_id: str,
    request: AddMemoryRequest,
    current_user_id: str = Depends(get_current_user_id),
    memory_manager: AgentMemoryManager = Depends(get_memory_manager),
):
    check_user_access(user_id, current_user_id)
    
    memory_id = await memory_manager.add_memory(
        user_id=user_id,
        content=request.content,
        category=request.category,
        importance=request.importance,
        tags=request.tags,
    )
    
    return {"memory_id": memory_id}

@router.get("/users/{user_id}/memory/search")
async def search_memory(
    user_id: str,
    query: str,
    category: str = None,
    limit: int = 10,
    current_user_id: str = Depends(get_current_user_id),
    memory_manager: AgentMemoryManager = Depends(get_memory_manager),
):
    check_user_access(user_id, current_user_id)
    
    results = await memory_manager.search_memory(
        user_id=user_id,
        query=query,
        category=category,
        limit=limit,
    )
    
    return {
        "results": [
            {
                "id": entry.id,
                "content": entry.content,
                "category": entry.category,
                "importance": entry.importance,
                "tags": entry.tags,
                "access_count": entry.access_count,
            }
            for entry in results
        ]
    }
```

### 2. 偏好管理 API

```python
class UpdatePreferenceRequest(BaseModel):
    key: str
    value: Any

@router.get("/users/{user_id}/preferences")
async def get_preferences(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    prefs_manager: UserPreferencesManager = Depends(get_prefs_manager),
):
    check_user_access(user_id, current_user_id)
    
    preferences = await prefs_manager.load_preferences(user_id)
    return {
        "language": preferences.language,
        "timezone": preferences.timezone,
        "response_style": preferences.response_style,
        "max_response_length": preferences.max_response_length,
        "preferred_formats": preferences.preferred_formats,
        "custom_settings": preferences.custom_settings,
    }

@router.put("/users/{user_id}/preferences")
async def update_preference(
    user_id: str,
    request: UpdatePreferenceRequest,
    current_user_id: str = Depends(get_current_user_id),
    prefs_manager: UserPreferencesManager = Depends(get_prefs_manager),
):
    check_user_access(user_id, current_user_id)
    
    preferences = await prefs_manager.update_preference(
        user_id=user_id,
        key=request.key,
        value=request.value,
    )
    
    return {"updated": True}
```

## 隔离保证

### 1. 数据隔离

- **用户档案**: 通过 `user_id` 在数据库中隔离
- **Agent 记忆**: 存储在用户专属目录 `~/.dataagent/users/{user_id}/memory/`
- **用户偏好**: 存储在用户专属目录
- **会话历史**: 通过 `session_id` 间接隔离

### 2. 访问控制

```python
def check_memory_access(user_id: str, current_user_id: str) -> None:
    """检查记忆访问权限。"""
    if user_id != current_user_id and current_user_id != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied to other user's memory"
        )
```

### 3. 文件系统隔离

```python
# 每个用户的记忆文件都在独立目录中
~/.dataagent/users/alice/memory/agent.json
~/.dataagent/users/bob/memory/agent.json
~/.dataagent/users/charlie/memory/agent.json
```

## 测试

### 记忆隔离测试

```python
async def test_memory_isolation():
    """测试记忆隔离。"""
    memory_manager = AgentMemoryManager(dir_manager)
    
    # Alice 添加记忆
    alice_memory_id = await memory_manager.add_memory(
        "alice", "我喜欢喝咖啡", "preference"
    )
    
    # Bob 添加记忆
    bob_memory_id = await memory_manager.add_memory(
        "bob", "我是软件工程师", "fact"
    )
    
    # 验证隔离
    alice_results = await memory_manager.search_memory("alice", "咖啡")
    bob_results = await memory_manager.search_memory("bob", "咖啡")
    
    assert len(alice_results) == 1
    assert len(bob_results) == 0  # Bob 搜索不到 Alice 的记忆
    
    alice_results = await memory_manager.search_memory("alice", "工程师")
    bob_results = await memory_manager.search_memory("bob", "工程师")
    
    assert len(alice_results) == 0  # Alice 搜索不到 Bob 的记忆
    assert len(bob_results) == 1
```

## 总结

用户记忆多租户隔离实现了：

✅ **用户档案隔离** - 每个租户有独立的身份信息  
✅ **Agent 记忆隔离** - 每个租户有独立的 AI 记忆  
✅ **偏好设置隔离** - 每个租户有个性化设置  
✅ **会话历史隔离** - 每个租户有独立的对话历史  
✅ **文件系统隔离** - 记忆文件存储在用户专属目录  
✅ **访问权限控制** - API 层级的权限检查  
✅ **智能学习** - 从交互中自动学习和更新记忆  