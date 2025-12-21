# 用户工作目录多租户隔离实现计划

## Implementation Status: ✅ 已完成

- [x] 1. 创建 Workspace API
  - [x] 1.1 创建 workspaces.py API 文件
    - 实现 WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse 模型
    - 实现 list_workspaces, get_default_workspace, create_workspace 端点
    - 实现 get_workspace, update_workspace, delete_workspace 端点
    - 实现 set_default_workspace 端点
    - 实现 get_user_default_workspace_path 辅助函数
    - 实现 ensure_user_default_workspace 辅助函数
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 2. 扩展 AgentConfig
  - [x] 2.1 添加 user_id 字段
    - 用于多租户用户标识
    - _Requirements: 3.1_
  - [x] 2.2 添加 workspace_path 字段
    - 用于指定用户工作目录路径
    - _Requirements: 3.1, 3.2_

- [x] 3. 修改 AgentFactory
  - [x] 3.1 修改 get_system_prompt 函数
    - 添加 workspace_path 参数
    - 使用 workspace_path 替代 Path.cwd()
    - _Requirements: 3.3_
  - [x] 3.2 修改 create_agent 方法
    - 使用 config.workspace_path 配置 ShellMiddleware
    - 将 workspace_path 传递给 get_system_prompt
    - _Requirements: 3.2, 3.4_

- [x] 4. 修改 WebSocket Handler
  - [x] 4.1 添加 _get_user_workspace_path 方法
    - 从数据库获取用户默认工作目录
    - 如果不存在则创建默认工作目录
    - _Requirements: 1.1, 1.2_
  - [x] 4.2 修改 _get_or_create_executor 方法
    - 调用 _get_user_workspace_path 获取工作目录
    - 设置 config.workspace_path
    - 设置 config.user_id
    - _Requirements: 3.1, 3.2_

- [x] 5. 修改 Chat Stream API
  - [x] 5.1 添加工作目录获取逻辑
    - 调用 get_user_default_workspace_path
    - 如果不存在则调用 ensure_user_default_workspace
    - 设置 config.workspace_path
    - _Requirements: 3.1, 3.2_

- [x] 6. 添加配置项
  - [x] 6.1 修改 ServerSettings
    - 添加 workspace_base_path 配置
    - 添加 workspace_default_max_size_bytes 配置
    - 添加 workspace_default_max_files 配置
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 7. 注册 API 路由
  - [x] 7.1 修改 main.py
    - 导入 workspaces 模块
    - 注册 workspaces.router
    - _Requirements: 2.1_
  - [x] 7.2 修改 api/v1/__init__.py
    - 导出 workspaces 模块
    - _Requirements: 2.1_

- [x] 8. 更新文档
  - [x] 8.1 更新 docs/api-reference.md
    - 添加工作目录管理 API 文档
    - 添加相关环境变量说明
    - _Requirements: 2.1, 4.1_

## 已完成的文件修改

| 文件 | 修改类型 | 描述 |
|------|----------|------|
| `source/dataagent-server/dataagent_server/api/v1/workspaces.py` | 新增 | Workspace API 实现 |
| `source/dataagent-core/dataagent_core/engine/factory.py` | 修改 | AgentConfig 扩展, get_system_prompt 修改 |
| `source/dataagent-server/dataagent_server/ws/handlers.py` | 修改 | 添加工作目录获取逻辑 |
| `source/dataagent-server/dataagent_server/api/v1/chat_stream.py` | 修改 | 添加工作目录获取逻辑 |
| `source/dataagent-server/dataagent_server/config/settings.py` | 修改 | 添加 workspace 配置项 |
| `source/dataagent-server/dataagent_server/main.py` | 修改 | 注册 workspaces 路由 |
| `source/dataagent-server/dataagent_server/api/v1/__init__.py` | 修改 | 导出 workspaces 模块 |
| `docs/api-reference.md` | 修改 | 添加 API 文档 |

## 验证结果

```bash
# 导入验证
python -c "from dataagent_server.main import app; print('Import successful')"
# 输出: Import successful

# 路由验证
python -c "
from dataagent_server.api.v1 import workspaces
print(f'Workspace routes: {[r.path for r in workspaces.router.routes]}')
"
# 输出: Workspace routes: ['/workspaces', '/workspaces/default', ...]

# AgentConfig 验证
python -c "
from dataagent_core.engine import AgentConfig
import dataclasses
for f in dataclasses.fields(AgentConfig):
    if f.name in ['user_id', 'workspace_path']:
        print(f'{f.name}: {f.type}')
"
# 输出:
# user_id: str | None
# workspace_path: str | None
```

## 使用示例

### 1. 获取用户工作目录列表

```bash
curl -X GET http://localhost:8000/api/v1/workspaces \
  -H "X-User-ID: user123"
```

### 2. 创建新工作目录

```bash
curl -X POST http://localhost:8000/api/v1/workspaces \
  -H "X-User-ID: user123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Project",
    "path": "/var/dataagent/workspaces/user123/project1",
    "is_default": true
  }'
```

### 3. 设置默认工作目录

```bash
curl -X POST http://localhost:8000/api/v1/workspaces/{workspace_id}/set-default \
  -H "X-User-ID: user123"
```

## 环境变量配置

```bash
# 工作目录基础路径
export DATAAGENT_WORKSPACE_BASE_PATH=/var/dataagent/workspaces

# 默认最大大小 (1GB)
export DATAAGENT_WORKSPACE_DEFAULT_MAX_SIZE_BYTES=1073741824

# 默认最大文件数
export DATAAGENT_WORKSPACE_DEFAULT_MAX_FILES=10000
```
