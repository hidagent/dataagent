# Subagent 工作目录隔离解决方案

## 状态: ✅ 已完成

## 问题根因

1. **glob/grep 工具默认路径为 "/"** - 当不指定路径时，工具从根目录开始搜索
2. **Subagent 没有继承工作目录上下文** - 主 agent 的 `working_directory` 没有传递给 subagent
3. **System prompt 没有明确工作目录** - Subagent 不知道应该在哪个目录工作

## 已完成的修改

### 1. FilesystemState 添加 working_directory

文件: `libs/deepagents/deepagents/middleware/filesystem.py`

```python
class FilesystemState(AgentState):
    files: Annotated[NotRequired[dict[str, FileData]], _file_data_reducer]
    working_directory: NotRequired[str]  # 新增
```

### 2. glob 工具使用工作目录

文件: `libs/deepagents/deepagents/middleware/filesystem.py`

- `path` 参数默认值改为 `None`
- 当 `path` 为 `None` 时，从 `runtime.state.get("working_directory", "/")` 获取

### 3. grep 工具使用工作目录

文件: `libs/deepagents/deepagents/middleware/filesystem.py`

- `path` 参数默认值改为 `None`
- 当 `path` 为 `None` 时，从 `runtime.state.get("working_directory")` 获取

### 4. Subagent 任务描述增强

文件: `libs/deepagents/deepagents/middleware/subagents.py`

`_validate_and_prepare_state` 函数修改:
- 确保 `working_directory` 被传递给 subagent state
- 在任务描述中添加工作目录上下文和文件操作规则

### 5. CLI 初始化设置工作目录

文件: `libs/deepagents-cli/deepagents_cli/execution.py`

`execute_task` 函数中的 `stream_input` 包含 `working_directory`:

```python
stream_input = {
    "messages": [{"role": "user", "content": final_input}],
    "working_directory": os.getcwd(),
}
```

## 修改的文件列表

1. `libs/deepagents/deepagents/middleware/filesystem.py`
2. `libs/deepagents/deepagents/middleware/subagents.py`
3. `libs/deepagents-cli/deepagents_cli/execution.py`

## 测试验证

修改后的行为:
- 主 agent 使用 `glob("*.py")` 将从当前工作目录搜索
- 主 agent 使用 `grep("pattern")` 将从当前工作目录搜索
- Subagent 继承主 agent 的工作目录
- Subagent 的任务描述中包含工作目录信息和文件操作规则

## 未来增强（可选）

### 路径验证增强

可以添加路径验证，拒绝访问工作目录外的文件:

```python
def _validate_path_in_workspace(path: str, working_directory: str) -> str:
    """验证路径在工作目录内"""
    normalized = os.path.normpath(os.path.join(working_directory, path))
    if not normalized.startswith(working_directory):
        raise ValueError(f"Path {path} is outside workspace {working_directory}")
    return normalized
```

### 审计日志

```python
def log_file_access(user_id: str, agent_id: str, path: str, action: str):
    """记录文件访问"""
    logger.info(f"File access: user={user_id}, agent={agent_id}, path={path}, action={action}")
```
