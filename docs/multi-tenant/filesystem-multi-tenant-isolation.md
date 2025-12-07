# 文件系统多租户隔离方案

## 概述

DataAgent 实现了完整的文件系统多租户隔离，确保每个租户的文件、配置和数据完全隔离，防止跨租户访问。

## 架构设计

### 1. 目录结构

```
~/.dataagent/
├── config/                         # 全局配置（共享）
│   └── settings.yaml
├── rules/                          # 全局规则（共享）
│   └── security-practices.md
├── users/                          # 租户隔离目录
│   ├── alice/                      # 租户 Alice
│   │   ├── mcp.json               # MCP 配置
│   │   ├── rules/                 # 用户规则
│   │   │   └── my-rules.md
│   │   ├── memory/                # Agent 记忆
│   │   │   ├── agent.md           # 长期记忆
│   │   │   └── preferences.json   # 用户偏好
│   │   ├── files/                 # 用户文件
│   │   │   ├── uploads/           # 上传文件
│   │   │   └── exports/           # 导出文件
│   │   └── cache/                 # 缓存数据
│   ├── bob/                        # 租户 Bob
│   │   ├── mcp.json
│   │   ├── rules/
│   │   ├── memory/
│   │   ├── files/
│   │   └── cache/
│   └── charlie/                    # 租户 Charlie
│       └── ...
└── shared/                         # 共享资源（只读）
    ├── templates/
    └── assets/
```

### 2. 隔离层次

```
┌─────────────────────────────────────────────────────────┐
│                    多租户文件系统                         │
├─────────────────────────────────────────────────────────┤
│  Tenant A          │  Tenant B          │  Tenant C      │
│  (user_id: alice)  │  (user_id: bob)    │  (user_id: c1) │
├────────────────────┼────────────────────┼────────────────┤
│ ~/.dataagent/      │ ~/.dataagent/      │ ~/.dataagent/  │
│ users/alice/       │ users/bob/         │ users/c1/      │
├────────────────────┼────────────────────┼────────────────┤
│ ├─ mcp.json        │ ├─ mcp.json        │ ├─ mcp.json    │
│ ├─ rules/          │ ├─ rules/          │ ├─ rules/      │
│ ├─ memory/         │ ├─ memory/         │ ├─ memory/     │
│ └─ files/          │ └─ files/          │ └─ files/      │
└────────────────────┴────────────────────┴────────────────┘
```

## 实现细节

### 1. 用户目录管理器

```python
import re
from pathlib import Path
from typing import Optional


class UserDirectoryManager:
    """用户目录管理器，确保文件系统隔离。"""
    
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path.home() / ".dataagent"
        self.users_dir = self.base_dir / "users"
    
    def _validate_user_id(self, user_id: str) -> None:
        """验证 user_id 格式，防止路径遍历攻击。"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
            raise ValueError(f"Invalid user_id: {user_id}")
        if '..' in user_id or '/' in user_id or '\\' in user_id:
            raise ValueError(f"Invalid user_id: {user_id}")
    
    def get_user_dir(self, user_id: str) -> Path:
        """获取用户根目录。"""
        self._validate_user_id(user_id)
        user_dir = self.users_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def get_user_mcp_config(self, user_id: str) -> Path:
        """获取用户 MCP 配置文件路径。"""
        return self.get_user_dir(user_id) / "mcp.json"
    
    def get_user_rules_dir(self, user_id: str) -> Path:
        """获取用户规则目录。"""
        rules_dir = self.get_user_dir(user_id) / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        return rules_dir
    
    def get_user_memory_dir(self, user_id: str) -> Path:
        """获取用户记忆目录。"""
        memory_dir = self.get_user_dir(user_id) / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        return memory_dir
    
    def get_user_files_dir(self, user_id: str) -> Path:
        """获取用户文件目录。"""
        files_dir = self.get_user_dir(user_id) / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        return files_dir
    
    def get_user_cache_dir(self, user_id: str) -> Path:
        """获取用户缓存目录。"""
        cache_dir = self.get_user_dir(user_id) / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    def resolve_user_path(self, user_id: str, relative_path: str) -> Path:
        """解析用户相对路径，确保不会逃逸出用户目录。"""
        self._validate_user_id(user_id)
        user_dir = self.get_user_dir(user_id)
        
        # 解析路径
        resolved = (user_dir / relative_path).resolve()
        
        # 确保路径在用户目录内
        if not str(resolved).startswith(str(user_dir.resolve())):
            raise ValueError(f"Path traversal detected: {relative_path}")
        
        return resolved
    
    def delete_user_data(self, user_id: str) -> bool:
        """删除用户所有数据。"""
        import shutil
        self._validate_user_id(user_id)
        user_dir = self.users_dir / user_id
        if user_dir.exists():
            shutil.rmtree(user_dir)
            return True
        return False
    
    def get_user_storage_usage(self, user_id: str) -> int:
        """获取用户存储使用量（字节）。"""
        self._validate_user_id(user_id)
        user_dir = self.users_dir / user_id
        if not user_dir.exists():
            return 0
        
        total_size = 0
        for path in user_dir.rglob('*'):
            if path.is_file():
                total_size += path.stat().st_size
        return total_size
```

### 2. 安全文件操作

```python
class SecureFileOperations:
    """安全的文件操作，确保租户隔离。"""
    
    def __init__(self, dir_manager: UserDirectoryManager):
        self.dir_manager = dir_manager
    
    async def read_file(self, user_id: str, relative_path: str) -> bytes:
        """安全读取用户文件。"""
        path = self.dir_manager.resolve_user_path(user_id, relative_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return path.read_bytes()
    
    async def write_file(
        self, user_id: str, relative_path: str, content: bytes
    ) -> Path:
        """安全写入用户文件。"""
        path = self.dir_manager.resolve_user_path(user_id, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path
    
    async def delete_file(self, user_id: str, relative_path: str) -> bool:
        """安全删除用户文件。"""
        path = self.dir_manager.resolve_user_path(user_id, relative_path)
        if path.exists():
            path.unlink()
            return True
        return False
    
    async def list_files(
        self, user_id: str, relative_dir: str = ""
    ) -> list[dict]:
        """列出用户目录下的文件。"""
        dir_path = self.dir_manager.resolve_user_path(user_id, relative_dir)
        if not dir_path.exists():
            return []
        
        files = []
        for path in dir_path.iterdir():
            files.append({
                "name": path.name,
                "is_dir": path.is_dir(),
                "size": path.stat().st_size if path.is_file() else 0,
                "modified": path.stat().st_mtime,
            })
        return files
```

### 3. 存储配额管理

```python
from dataclasses import dataclass


@dataclass
class StorageQuota:
    """存储配额配置。"""
    max_storage_bytes: int = 100 * 1024 * 1024  # 100MB
    max_file_size_bytes: int = 10 * 1024 * 1024  # 10MB
    max_files_count: int = 1000


class StorageQuotaManager:
    """存储配额管理器。"""
    
    def __init__(
        self,
        dir_manager: UserDirectoryManager,
        default_quota: StorageQuota | None = None,
    ):
        self.dir_manager = dir_manager
        self.default_quota = default_quota or StorageQuota()
        self._user_quotas: dict[str, StorageQuota] = {}
    
    def set_user_quota(self, user_id: str, quota: StorageQuota) -> None:
        """设置用户配额。"""
        self._user_quotas[user_id] = quota
    
    def get_user_quota(self, user_id: str) -> StorageQuota:
        """获取用户配额。"""
        return self._user_quotas.get(user_id, self.default_quota)
    
    def check_quota(self, user_id: str, additional_bytes: int = 0) -> bool:
        """检查用户是否超出配额。"""
        quota = self.get_user_quota(user_id)
        current_usage = self.dir_manager.get_user_storage_usage(user_id)
        return (current_usage + additional_bytes) <= quota.max_storage_bytes
    
    def get_usage_info(self, user_id: str) -> dict:
        """获取用户存储使用信息。"""
        quota = self.get_user_quota(user_id)
        current_usage = self.dir_manager.get_user_storage_usage(user_id)
        
        return {
            "user_id": user_id,
            "used_bytes": current_usage,
            "max_bytes": quota.max_storage_bytes,
            "used_percentage": (current_usage / quota.max_storage_bytes) * 100,
            "remaining_bytes": quota.max_storage_bytes - current_usage,
        }
```

## 安全措施

### 1. 路径遍历防护

```python
def safe_join(base: Path, *paths: str) -> Path:
    """安全的路径拼接，防止路径遍历。"""
    result = base
    for p in paths:
        # 移除危险字符
        p = p.replace('..', '').replace('\0', '')
        result = result / p
    
    # 确保结果在 base 目录内
    resolved = result.resolve()
    if not str(resolved).startswith(str(base.resolve())):
        raise ValueError("Path traversal detected")
    
    return resolved
```

### 2. 文件类型验证

```python
ALLOWED_EXTENSIONS = {'.txt', '.md', '.json', '.yaml', '.yml', '.csv', '.pdf'}
MAX_FILENAME_LENGTH = 255


def validate_filename(filename: str) -> bool:
    """验证文件名安全性。"""
    if not filename or len(filename) > MAX_FILENAME_LENGTH:
        return False
    
    # 检查危险字符
    dangerous_chars = ['..', '/', '\\', '\0', '\n', '\r']
    for char in dangerous_chars:
        if char in filename:
            return False
    
    # 检查扩展名
    ext = Path(filename).suffix.lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        return False
    
    return True
```

### 3. 权限检查

```python
def check_file_access(
    user_id: str,
    current_user_id: str,
    operation: str = "read"
) -> None:
    """检查文件访问权限。"""
    if user_id != current_user_id and current_user_id != "admin":
        raise PermissionError(
            f"Access denied: {current_user_id} cannot {operation} "
            f"{user_id}'s files"
        )
```

## API 示例

### 1. 文件上传

```python
from fastapi import APIRouter, UploadFile, HTTPException, Depends

router = APIRouter()

@router.post("/users/{user_id}/files/upload")
async def upload_file(
    user_id: str,
    file: UploadFile,
    path: str = "uploads",
    current_user_id: str = Depends(get_current_user_id),
    dir_manager: UserDirectoryManager = Depends(get_dir_manager),
    quota_manager: StorageQuotaManager = Depends(get_quota_manager),
):
    # 权限检查
    check_file_access(user_id, current_user_id, "write")
    
    # 验证文件名
    if not validate_filename(file.filename):
        raise HTTPException(400, "Invalid filename")
    
    # 检查配额
    content = await file.read()
    if not quota_manager.check_quota(user_id, len(content)):
        raise HTTPException(413, "Storage quota exceeded")
    
    # 保存文件
    file_ops = SecureFileOperations(dir_manager)
    relative_path = f"{path}/{file.filename}"
    saved_path = await file_ops.write_file(user_id, relative_path, content)
    
    return {
        "filename": file.filename,
        "path": relative_path,
        "size": len(content),
    }
```

### 2. 文件列表

```python
@router.get("/users/{user_id}/files")
async def list_files(
    user_id: str,
    path: str = "",
    current_user_id: str = Depends(get_current_user_id),
    dir_manager: UserDirectoryManager = Depends(get_dir_manager),
):
    check_file_access(user_id, current_user_id, "read")
    
    file_ops = SecureFileOperations(dir_manager)
    files = await file_ops.list_files(user_id, path)
    
    return {"files": files, "path": path}
```

### 3. 存储使用情况

```python
@router.get("/users/{user_id}/storage")
async def get_storage_usage(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    quota_manager: StorageQuotaManager = Depends(get_quota_manager),
):
    check_file_access(user_id, current_user_id, "read")
    return quota_manager.get_usage_info(user_id)
```

## 测试

### 隔离性测试

```python
import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def dir_manager():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield UserDirectoryManager(Path(tmpdir))


async def test_user_isolation(dir_manager):
    """测试用户目录隔离。"""
    # Alice 的目录
    alice_dir = dir_manager.get_user_dir("alice")
    alice_files = dir_manager.get_user_files_dir("alice")
    
    # Bob 的目录
    bob_dir = dir_manager.get_user_dir("bob")
    bob_files = dir_manager.get_user_files_dir("bob")
    
    # 验证目录不同
    assert alice_dir != bob_dir
    assert alice_files != bob_files
    
    # 验证目录存在
    assert alice_dir.exists()
    assert bob_dir.exists()


async def test_path_traversal_prevention(dir_manager):
    """测试路径遍历防护。"""
    # 尝试路径遍历
    with pytest.raises(ValueError, match="Path traversal"):
        dir_manager.resolve_user_path("alice", "../bob/secret.txt")
    
    with pytest.raises(ValueError, match="Path traversal"):
        dir_manager.resolve_user_path("alice", "../../etc/passwd")


async def test_invalid_user_id(dir_manager):
    """测试无效用户ID。"""
    with pytest.raises(ValueError, match="Invalid user_id"):
        dir_manager.get_user_dir("../admin")
    
    with pytest.raises(ValueError, match="Invalid user_id"):
        dir_manager.get_user_dir("user;rm -rf /")
```

## 总结

文件系统多租户隔离实现了：

✅ **目录隔离** - 每个租户有独立的目录结构  
✅ **路径安全** - 防止路径遍历攻击  
✅ **权限控制** - API 层级的访问检查  
✅ **配额管理** - 存储空间限制  
✅ **文件验证** - 文件名和类型检查  
