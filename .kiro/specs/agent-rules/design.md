# Agent Rules Design Document

## Overview

Agent Rules 是 DataAgent 系统的核心功能，允许用户通过配置文件定义 Agent 的行为规则、工作流程和领域知识。该功能借鉴了 Cursor Rules 和 Claude Code 的设计理念，支持多层级规则配置、条件触发、优先级管理和规则调试。

### 设计目标

1. **灵活性**: 支持全局、用户、项目多层级规则配置
2. **可扩展性**: 通过中间件架构支持规则的动态加载和热更新
3. **透明性**: 提供完整的规则触发追踪和调试能力
4. **安全性**: 防止路径遍历和提示词注入攻击
5. **易用性**: 提供 CLI 和 API 两种管理方式

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Agent Rules Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐         ┌─────────────────────────────────────────┐  │
│   │  DataAgentCli   │         │           DataAgentServer               │  │
│   │                 │         │                                         │  │
│   │  /rules list    │         │  GET  /api/v1/rules                    │  │
│   │  /rules create  │         │  POST /api/v1/rules                    │  │
│   │  /rules debug   │         │  PUT  /api/v1/rules/{name}             │  │
│   │  /rules trace   │         │  DELETE /api/v1/rules/{name}           │  │
│   └────────┬────────┘         └─────────────────┬───────────────────────┘  │
│            │                                    │                          │
│            ▼                                    ▼                          │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         DataAgentCore                                │  │
│   │                                                                      │  │
│   │  ┌──────────────────────────────────────────────────────────────┐   │  │
│   │  │                    RulesMiddleware                            │   │  │
│   │  │                                                               │   │  │
│   │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │  │
│   │  │  │ RuleLoader  │  │ RuleMatcher │  │ RuleContextBuilder  │  │   │  │
│   │  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │  │
│   │  │                                                               │   │  │
│   │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │  │
│   │  │  │ RuleMerger  │  │ RuleTracer  │  │ ConflictDetector    │  │   │  │
│   │  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │  │
│   │  └──────────────────────────────────────────────────────────────┘   │  │
│   │                                                                      │  │
│   │  ┌──────────────────────────────────────────────────────────────┐   │  │
│   │  │                      RuleStore                                │   │  │
│   │  │                                                               │   │  │
│   │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │  │
│   │  │  │ FileStore   │  │ MemoryStore │  │ DatabaseStore       │  │   │  │
│   │  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │  │
│   │  └──────────────────────────────────────────────────────────────┘   │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                        Rule Storage Locations                        │  │
│   │                                                                      │  │
│   │  Global:  ~/.dataagent/rules/                                       │  │
│   │  User:    ~/.dataagent/users/{user_id}/rules/                       │  │
│   │  Project: {project_root}/.dataagent/rules/                          │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Rule Model

```python
# dataagent_core/rules/models.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RuleScope(Enum):
    """规则作用域"""
    GLOBAL = "global"      # 全局规则
    USER = "user"          # 用户级规则
    PROJECT = "project"    # 项目级规则
    SESSION = "session"    # 会话级规则


class RuleInclusion(Enum):
    """规则包含模式"""
    ALWAYS = "always"           # 始终包含
    FILE_MATCH = "fileMatch"    # 文件匹配时包含
    MANUAL = "manual"           # 手动引用时包含


@dataclass
class Rule:
    """规则模型"""
    name: str                                    # 规则名称（唯一标识）
    description: str                             # 规则描述
    content: str                                 # 规则内容（Markdown）
    scope: RuleScope                             # 作用域
    inclusion: RuleInclusion = RuleInclusion.ALWAYS  # 包含模式
    file_match_pattern: str | None = None        # 文件匹配模式（glob）
    priority: int = 50                           # 优先级（1-100，越大越优先）
    override: bool = False                       # 是否覆盖同名低优先级规则
    enabled: bool = True                         # 是否启用
    source_path: str | None = None               # 源文件路径
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "scope": self.scope.value,
            "inclusion": self.inclusion.value,
            "file_match_pattern": self.file_match_pattern,
            "priority": self.priority,
            "override": self.override,
            "enabled": self.enabled,
            "source_path": self.source_path,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Rule":
        """从字典反序列化"""
        return cls(
            name=data["name"],
            description=data["description"],
            content=data["content"],
            scope=RuleScope(data["scope"]),
            inclusion=RuleInclusion(data.get("inclusion", "always")),
            file_match_pattern=data.get("file_match_pattern"),
            priority=data.get("priority", 50),
            override=data.get("override", False),
            enabled=data.get("enabled", True),
            source_path=data.get("source_path"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            metadata=data.get("metadata", {}),
        )


@dataclass
class RuleMatch:
    """规则匹配结果"""
    rule: Rule
    match_reason: str              # 匹配原因
    matched_files: list[str] = field(default_factory=list)  # 匹配的文件
    context_vars: dict[str, Any] = field(default_factory=dict)  # 上下文变量


@dataclass
class RuleEvaluationTrace:
    """规则评估追踪"""
    request_id: str
    timestamp: datetime
    evaluated_rules: list[str]     # 评估的规则列表
    matched_rules: list[RuleMatch] # 匹配的规则
    skipped_rules: list[tuple[str, str]]  # 跳过的规则及原因
    conflicts: list[tuple[str, str, str]]  # 冲突（规则1, 规则2, 原因）
    final_rules: list[str]         # 最终应用的规则
    total_content_size: int        # 总内容大小
```

### 2. Rule Parser

```python
# dataagent_core/rules/parser.py

import re
from pathlib import Path
from typing import Any

from dataagent_core.rules.models import Rule, RuleScope, RuleInclusion


MAX_RULE_FILE_SIZE = 1 * 1024 * 1024  # 1MB


class RuleParseError(Exception):
    """规则解析错误"""
    pass


class RuleParser:
    """规则文件解析器"""

    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    FILE_REFERENCE_PATTERN = re.compile(r"#\[\[file:([^\]]+)\]\]")

    def parse_file(self, file_path: Path, scope: RuleScope) -> Rule | None:
        """解析规则文件"""
        if not file_path.exists():
            return None

        # 检查文件大小
        if file_path.stat().st_size > MAX_RULE_FILE_SIZE:
            raise RuleParseError(f"Rule file exceeds size limit: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        return self.parse_content(content, scope, str(file_path))

    def parse_content(
        self, content: str, scope: RuleScope, source_path: str | None = None
    ) -> Rule:
        """解析规则内容"""
        # 解析 YAML frontmatter
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            raise RuleParseError("Missing YAML frontmatter")

        frontmatter = match.group(1)
        metadata = self._parse_yaml(frontmatter)

        # 验证必需字段
        if "name" not in metadata:
            raise RuleParseError("Missing required field: name")
        if "description" not in metadata:
            raise RuleParseError("Missing required field: description")

        # 提取 Markdown 内容
        rule_content = content[match.end():]

        # 解析包含模式
        inclusion = RuleInclusion(metadata.get("inclusion", "always"))

        return Rule(
            name=metadata["name"],
            description=metadata["description"],
            content=rule_content,
            scope=scope,
            inclusion=inclusion,
            file_match_pattern=metadata.get("fileMatchPattern"),
            priority=int(metadata.get("priority", 50)),
            override=metadata.get("override", "false").lower() == "true",
            enabled=metadata.get("enabled", "true").lower() != "false",
            source_path=source_path,
            metadata=metadata,
        )

    def _parse_yaml(self, yaml_content: str) -> dict[str, Any]:
        """简单的 YAML 解析（仅支持单层键值对）"""
        result = {}
        for line in yaml_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"^(\w+):\s*(.*)$", line)
            if match:
                key, value = match.groups()
                result[key] = value.strip().strip('"').strip("'")
        return result

    def resolve_file_references(
        self, content: str, base_path: Path, allowed_dirs: list[Path]
    ) -> str:
        """解析并替换文件引用"""
        def replace_reference(match: re.Match) -> str:
            ref_path = match.group(1)
            full_path = (base_path / ref_path).resolve()

            # 安全检查
            if not self._is_safe_path(full_path, allowed_dirs):
                return f"[File reference blocked: {ref_path}]"

            if not full_path.exists():
                return f"[File not found: {ref_path}]"

            try:
                return full_path.read_text(encoding="utf-8")
            except Exception as e:
                return f"[Error reading file: {e}]"

        return self.FILE_REFERENCE_PATTERN.sub(replace_reference, content)

    def _is_safe_path(self, path: Path, allowed_dirs: list[Path]) -> bool:
        """检查路径是否安全"""
        try:
            resolved = path.resolve()
            for allowed in allowed_dirs:
                try:
                    resolved.relative_to(allowed.resolve())
                    return True
                except ValueError:
                    continue
            return False
        except (OSError, RuntimeError):
            return False
```

### 3. Rule Store

```python
# dataagent_core/rules/store.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator

from dataagent_core.rules.models import Rule, RuleScope
from dataagent_core.rules.parser import RuleParser


class RuleStore(ABC):
    """规则存储抽象基类"""

    @abstractmethod
    def list_rules(self, scope: RuleScope | None = None) -> list[Rule]:
        """列出规则"""
        ...

    @abstractmethod
    def get_rule(self, name: str, scope: RuleScope | None = None) -> Rule | None:
        """获取规则"""
        ...

    @abstractmethod
    def save_rule(self, rule: Rule) -> None:
        """保存规则"""
        ...

    @abstractmethod
    def delete_rule(self, name: str, scope: RuleScope) -> bool:
        """删除规则"""
        ...

    @abstractmethod
    def reload(self) -> None:
        """重新加载规则"""
        ...


class FileRuleStore(RuleStore):
    """基于文件系统的规则存储"""

    def __init__(
        self,
        global_dir: Path | None = None,
        user_dir: Path | None = None,
        project_dir: Path | None = None,
    ):
        self.global_dir = global_dir
        self.user_dir = user_dir
        self.project_dir = project_dir
        self.parser = RuleParser()
        self._cache: dict[str, Rule] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.reload()

    def list_rules(self, scope: RuleScope | None = None) -> list[Rule]:
        self._ensure_loaded()
        if scope is None:
            return list(self._cache.values())
        return [r for r in self._cache.values() if r.scope == scope]

    def get_rule(self, name: str, scope: RuleScope | None = None) -> Rule | None:
        self._ensure_loaded()
        if scope:
            key = f"{scope.value}:{name}"
            return self._cache.get(key)
        # 按优先级查找
        for s in [RuleScope.PROJECT, RuleScope.USER, RuleScope.GLOBAL]:
            key = f"{s.value}:{name}"
            if key in self._cache:
                return self._cache[key]
        return None

    def save_rule(self, rule: Rule) -> None:
        # 确定保存目录
        dir_path = self._get_dir_for_scope(rule.scope)
        if not dir_path:
            raise ValueError(f"No directory configured for scope: {rule.scope}")

        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / f"{rule.name}.md"

        # 生成文件内容
        content = self._generate_rule_file(rule)
        file_path.write_text(content, encoding="utf-8")

        # 更新缓存
        key = f"{rule.scope.value}:{rule.name}"
        rule.source_path = str(file_path)
        self._cache[key] = rule

    def delete_rule(self, name: str, scope: RuleScope) -> bool:
        dir_path = self._get_dir_for_scope(scope)
        if not dir_path:
            return False

        file_path = dir_path / f"{name}.md"
        if file_path.exists():
            file_path.unlink()
            key = f"{scope.value}:{name}"
            self._cache.pop(key, None)
            return True
        return False

    def reload(self) -> None:
        self._cache.clear()
        for scope, dir_path in [
            (RuleScope.GLOBAL, self.global_dir),
            (RuleScope.USER, self.user_dir),
            (RuleScope.PROJECT, self.project_dir),
        ]:
            if dir_path and dir_path.exists():
                for rule in self._load_rules_from_dir(dir_path, scope):
                    key = f"{scope.value}:{rule.name}"
                    self._cache[key] = rule
        self._loaded = True

    def _load_rules_from_dir(self, dir_path: Path, scope: RuleScope) -> Iterator[Rule]:
        for file_path in dir_path.glob("*.md"):
            try:
                rule = self.parser.parse_file(file_path, scope)
                if rule:
                    yield rule
            except Exception:
                # 记录错误但继续加载其他规则
                continue

    def _get_dir_for_scope(self, scope: RuleScope) -> Path | None:
        return {
            RuleScope.GLOBAL: self.global_dir,
            RuleScope.USER: self.user_dir,
            RuleScope.PROJECT: self.project_dir,
        }.get(scope)

    def _generate_rule_file(self, rule: Rule) -> str:
        lines = [
            "---",
            f"name: {rule.name}",
            f"description: {rule.description}",
            f"inclusion: {rule.inclusion.value}",
        ]
        if rule.file_match_pattern:
            lines.append(f"fileMatchPattern: {rule.file_match_pattern}")
        if rule.priority != 50:
            lines.append(f"priority: {rule.priority}")
        if rule.override:
            lines.append("override: true")
        if not rule.enabled:
            lines.append("enabled: false")
        lines.extend(["---", "", rule.content])
        return "\n".join(lines)
```

### 4. Rule Matcher

```python
# dataagent_core/rules/matcher.py

import fnmatch
from dataclasses import dataclass, field
from typing import Any

from dataagent_core.rules.models import Rule, RuleInclusion, RuleMatch


@dataclass
class MatchContext:
    """匹配上下文"""
    current_files: list[str] = field(default_factory=list)
    user_query: str = ""
    session_id: str = ""
    assistant_id: str = ""
    manual_rules: list[str] = field(default_factory=list)  # 手动引用的规则
    extra_vars: dict[str, Any] = field(default_factory=dict)


class RuleMatcher:
    """规则匹配器"""

    def match_rules(
        self, rules: list[Rule], context: MatchContext
    ) -> tuple[list[RuleMatch], list[tuple[str, str]]]:
        """
        匹配规则

        Returns:
            (matched_rules, skipped_rules) - 匹配的规则和跳过的规则（含原因）
        """
        matched: list[RuleMatch] = []
        skipped: list[tuple[str, str]] = []

        for rule in rules:
            if not rule.enabled:
                skipped.append((rule.name, "disabled"))
                continue

            match_result = self._match_rule(rule, context)
            if match_result:
                matched.append(match_result)
            else:
                skipped.append((rule.name, self._get_skip_reason(rule, context)))

        return matched, skipped

    def _match_rule(self, rule: Rule, context: MatchContext) -> RuleMatch | None:
        """匹配单个规则"""
        if rule.inclusion == RuleInclusion.ALWAYS:
            return RuleMatch(
                rule=rule,
                match_reason="always included",
            )

        if rule.inclusion == RuleInclusion.MANUAL:
            if rule.name in context.manual_rules:
                return RuleMatch(
                    rule=rule,
                    match_reason=f"manually referenced",
                )
            return None

        if rule.inclusion == RuleInclusion.FILE_MATCH:
            if not rule.file_match_pattern:
                return None

            matched_files = self._match_files(
                rule.file_match_pattern, context.current_files
            )
            if matched_files:
                return RuleMatch(
                    rule=rule,
                    match_reason=f"file pattern matched: {rule.file_match_pattern}",
                    matched_files=matched_files,
                )
            return None

        return None

    def _match_files(self, pattern: str, files: list[str]) -> list[str]:
        """匹配文件列表"""
        matched = []
        for file_path in files:
            if fnmatch.fnmatch(file_path, pattern):
                matched.append(file_path)
            # 也检查文件名
            elif fnmatch.fnmatch(file_path.split("/")[-1], pattern):
                matched.append(file_path)
        return matched

    def _get_skip_reason(self, rule: Rule, context: MatchContext) -> str:
        """获取跳过原因"""
        if rule.inclusion == RuleInclusion.MANUAL:
            return "not manually referenced"
        if rule.inclusion == RuleInclusion.FILE_MATCH:
            return f"no files matched pattern: {rule.file_match_pattern}"
        return "unknown"
```

### 5. Rule Merger

```python
# dataagent_core/rules/merger.py

from dataagent_core.rules.models import Rule, RuleMatch, RuleScope


class RuleMerger:
    """规则合并器"""

    # 作用域优先级（数字越大优先级越高）
    SCOPE_PRIORITY = {
        RuleScope.GLOBAL: 1,
        RuleScope.USER: 2,
        RuleScope.PROJECT: 3,
        RuleScope.SESSION: 4,
    }

    def __init__(self, max_content_size: int = 100_000):
        self.max_content_size = max_content_size

    def merge_rules(
        self, matches: list[RuleMatch]
    ) -> tuple[list[Rule], list[tuple[str, str, str]]]:
        """
        合并规则

        Returns:
            (final_rules, conflicts) - 最终规则列表和冲突信息
        """
        conflicts: list[tuple[str, str, str]] = []

        # 按优先级排序
        sorted_matches = self._sort_by_priority(matches)

        # 处理覆盖和冲突
        final_rules: list[Rule] = []
        seen_names: dict[str, Rule] = {}

        for match in sorted_matches:
            rule = match.rule
            if rule.name in seen_names:
                existing = seen_names[rule.name]
                if rule.override:
                    # 覆盖已有规则
                    final_rules = [r for r in final_rules if r.name != rule.name]
                    final_rules.append(rule)
                    seen_names[rule.name] = rule
                    conflicts.append((
                        rule.name,
                        existing.name,
                        f"overridden by {rule.scope.value} scope"
                    ))
                else:
                    # 记录冲突但保留高优先级规则
                    conflicts.append((
                        rule.name,
                        existing.name,
                        f"duplicate name, keeping {existing.scope.value} scope"
                    ))
            else:
                final_rules.append(rule)
                seen_names[rule.name] = rule

        # 检查总大小限制
        final_rules = self._truncate_if_needed(final_rules)

        return final_rules, conflicts

    def _sort_by_priority(self, matches: list[RuleMatch]) -> list[RuleMatch]:
        """按优先级排序"""
        def sort_key(match: RuleMatch) -> tuple[int, int, str]:
            rule = match.rule
            scope_priority = self.SCOPE_PRIORITY.get(rule.scope, 0)
            return (-scope_priority, -rule.priority, rule.name)

        return sorted(matches, key=sort_key)

    def _truncate_if_needed(self, rules: list[Rule]) -> list[Rule]:
        """如果超出大小限制则截断"""
        total_size = 0
        result = []

        for rule in rules:
            rule_size = len(rule.content)
            if total_size + rule_size <= self.max_content_size:
                result.append(rule)
                total_size += rule_size
            else:
                # 超出限制，停止添加
                break

        return result

    def build_prompt_section(self, rules: list[Rule]) -> str:
        """构建系统提示词部分"""
        if not rules:
            return ""

        sections = ["## Agent Rules\n"]
        sections.append("The following rules guide your behavior:\n")

        for rule in rules:
            sections.append(f"### {rule.name}\n")
            sections.append(f"*{rule.description}*\n")
            sections.append(rule.content)
            sections.append("\n")

        return "\n".join(sections)
```


### 6. Rules Middleware

```python
# dataagent_core/middleware/rules.py

import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, NotRequired, TypedDict, cast

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langgraph.runtime import Runtime

from dataagent_core.rules.models import Rule, RuleEvaluationTrace, RuleMatch, RuleScope
from dataagent_core.rules.store import RuleStore
from dataagent_core.rules.matcher import RuleMatcher, MatchContext
from dataagent_core.rules.merger import RuleMerger


class RulesState(AgentState):
    """规则中间件状态"""
    rules_loaded: NotRequired[bool]
    triggered_rules: NotRequired[list[str]]
    rule_trace: NotRequired[dict[str, Any]]


class RulesStateUpdate(TypedDict):
    """规则状态更新"""
    rules_loaded: bool
    triggered_rules: list[str]
    rule_trace: dict[str, Any]


RULES_MANUAL_REFERENCE_PATTERN = re.compile(r"@(\w[\w\-]*)")


class RulesMiddleware(AgentMiddleware):
    """规则中间件"""

    state_schema = RulesState

    def __init__(
        self,
        store: RuleStore,
        *,
        debug_mode: bool = False,
        max_content_size: int = 100_000,
    ):
        self.store = store
        self.matcher = RuleMatcher()
        self.merger = RuleMerger(max_content_size=max_content_size)
        self.debug_mode = debug_mode
        self._last_trace: RuleEvaluationTrace | None = None

    def before_agent(
        self, state: RulesState, runtime: Runtime
    ) -> RulesStateUpdate | None:
        """Agent 执行前加载规则"""
        # 确保规则已加载
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
        """同步包装模型调用"""
        system_prompt = self._build_system_prompt(request)
        return handler(request.override(system_prompt=system_prompt))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """异步包装模型调用"""
        system_prompt = self._build_system_prompt(request)
        return await handler(request.override(system_prompt=system_prompt))

    def _build_system_prompt(self, request: ModelRequest) -> str:
        """构建包含规则的系统提示词"""
        state = cast("RulesState", request.state)

        # 构建匹配上下文
        context = self._build_match_context(request)

        # 获取所有规则
        all_rules = self.store.list_rules()

        # 匹配规则
        matched, skipped = self.matcher.match_rules(all_rules, context)

        # 合并规则
        final_rules, conflicts = self.merger.merge_rules(matched)

        # 记录追踪信息
        trace = RuleEvaluationTrace(
            request_id=str(time.time()),
            timestamp=time.time(),
            evaluated_rules=[r.name for r in all_rules],
            matched_rules=matched,
            skipped_rules=skipped,
            conflicts=conflicts,
            final_rules=[r.name for r in final_rules],
            total_content_size=sum(len(r.content) for r in final_rules),
        )
        self._last_trace = trace

        # 构建规则部分
        rules_section = self.merger.build_prompt_section(final_rules)

        # 添加调试信息
        if self.debug_mode:
            rules_section += self._build_debug_section(trace)

        # 合并到系统提示词
        if request.system_prompt:
            return f"{request.system_prompt}\n\n{rules_section}"
        return rules_section

    def _build_match_context(self, request: ModelRequest) -> MatchContext:
        """从请求构建匹配上下文"""
        # 提取用户消息
        user_query = ""
        current_files = []

        for msg in request.messages:
            if hasattr(msg, "content") and isinstance(msg.content, str):
                user_query = msg.content
                # 提取文件引用
                # 假设文件引用格式为 @file:path 或在消息中提到的文件路径
                current_files.extend(self._extract_file_references(msg.content))

        # 提取手动规则引用
        manual_rules = RULES_MANUAL_REFERENCE_PATTERN.findall(user_query)

        return MatchContext(
            current_files=current_files,
            user_query=user_query,
            session_id=request.state.get("session_id", ""),
            assistant_id=request.state.get("assistant_id", ""),
            manual_rules=manual_rules,
        )

    def _extract_file_references(self, content: str) -> list[str]:
        """从内容中提取文件引用"""
        # 匹配常见的文件路径模式
        patterns = [
            r"`([^`]+\.\w+)`",  # 反引号中的文件路径
            r"file:([^\s]+)",   # file: 前缀
            r"path:([^\s]+)",   # path: 前缀
        ]
        files = []
        for pattern in patterns:
            files.extend(re.findall(pattern, content))
        return files

    def _build_debug_section(self, trace: RuleEvaluationTrace) -> str:
        """构建调试信息部分"""
        lines = [
            "\n---",
            "## [DEBUG] Rule Evaluation Trace",
            f"Request ID: {trace.request_id}",
            f"Evaluated: {len(trace.evaluated_rules)} rules",
            f"Matched: {len(trace.matched_rules)} rules",
            f"Final: {len(trace.final_rules)} rules",
            f"Total Size: {trace.total_content_size} chars",
            "",
            "### Triggered Rules:",
        ]

        for match in trace.matched_rules:
            lines.append(f"- {match.rule.name} ({match.rule.scope.value}): {match.match_reason}")
            if match.matched_files:
                lines.append(f"  Files: {', '.join(match.matched_files)}")

        if trace.skipped_rules:
            lines.append("\n### Skipped Rules:")
            for name, reason in trace.skipped_rules[:10]:  # 限制显示数量
                lines.append(f"- {name}: {reason}")

        if trace.conflicts:
            lines.append("\n### Conflicts:")
            for r1, r2, reason in trace.conflicts:
                lines.append(f"- {r1} vs {r2}: {reason}")

        lines.append("---\n")
        return "\n".join(lines)

    def get_last_trace(self) -> RuleEvaluationTrace | None:
        """获取最后一次规则评估追踪"""
        return self._last_trace

    def set_debug_mode(self, enabled: bool) -> None:
        """设置调试模式"""
        self.debug_mode = enabled
```

### 7. Rule Events

```python
# dataagent_core/events/rules.py

from dataclasses import dataclass, field
from typing import Any

from dataagent_core.events import ExecutionEvent


@dataclass
class RulesAppliedEvent(ExecutionEvent):
    """规则应用事件"""
    triggered_rules: list[dict[str, Any]] = field(default_factory=list)
    skipped_count: int = 0
    conflicts: list[dict[str, str]] = field(default_factory=list)
    total_size: int = 0

    def __post_init__(self):
        self.event_type = "rules_applied"

    def _extra_fields(self) -> dict:
        return {
            "triggered_rules": self.triggered_rules,
            "skipped_count": self.skipped_count,
            "conflicts": self.conflicts,
            "total_size": self.total_size,
        }


@dataclass
class RuleDebugEvent(ExecutionEvent):
    """规则调试事件"""
    trace: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.event_type = "rule_debug"

    def _extra_fields(self) -> dict:
        return {"trace": self.trace}
```

### 8. REST API

```python
# dataagent_server/api/v1/rules.py

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any

from dataagent_core.rules.models import Rule, RuleScope, RuleInclusion
from dataagent_core.rules.store import RuleStore
from dataagent_core.rules.parser import RuleParser, RuleParseError


router = APIRouter(prefix="/rules", tags=["rules"])


class RuleCreate(BaseModel):
    """创建规则请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    scope: str = Field(default="user")
    inclusion: str = Field(default="always")
    file_match_pattern: str | None = None
    priority: int = Field(default=50, ge=1, le=100)
    override: bool = False


class RuleUpdate(BaseModel):
    """更新规则请求"""
    description: str | None = None
    content: str | None = None
    inclusion: str | None = None
    file_match_pattern: str | None = None
    priority: int | None = Field(default=None, ge=1, le=100)
    override: bool | None = None
    enabled: bool | None = None


class RuleResponse(BaseModel):
    """规则响应"""
    name: str
    description: str
    content: str
    scope: str
    inclusion: str
    file_match_pattern: str | None
    priority: int
    override: bool
    enabled: bool
    source_path: str | None
    created_at: str
    updated_at: str


class RuleListResponse(BaseModel):
    """规则列表响应"""
    rules: list[RuleResponse]
    total: int
    triggered_rules: list[str] | None = None  # 当前请求触发的规则


class RuleValidateRequest(BaseModel):
    """验证规则请求"""
    content: str


class RuleValidateResponse(BaseModel):
    """验证规则响应"""
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class RuleConflictResponse(BaseModel):
    """规则冲突响应"""
    conflicts: list[dict[str, str]]


@router.get("/", response_model=RuleListResponse)
async def list_rules(
    scope: str | None = Query(None, description="Filter by scope"),
    store: RuleStore = Depends(get_rule_store),
):
    """列出所有规则"""
    scope_enum = RuleScope(scope) if scope else None
    rules = store.list_rules(scope_enum)
    return RuleListResponse(
        rules=[_rule_to_response(r) for r in rules],
        total=len(rules),
    )


@router.get("/{name}", response_model=RuleResponse)
async def get_rule(
    name: str,
    scope: str | None = Query(None),
    store: RuleStore = Depends(get_rule_store),
):
    """获取规则详情"""
    scope_enum = RuleScope(scope) if scope else None
    rule = store.get_rule(name, scope_enum)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return _rule_to_response(rule)


@router.post("/", response_model=RuleResponse, status_code=201)
async def create_rule(
    request: RuleCreate,
    store: RuleStore = Depends(get_rule_store),
):
    """创建规则"""
    # 检查是否已存在
    scope = RuleScope(request.scope)
    existing = store.get_rule(request.name, scope)
    if existing:
        raise HTTPException(status_code=409, detail="Rule already exists")

    rule = Rule(
        name=request.name,
        description=request.description,
        content=request.content,
        scope=scope,
        inclusion=RuleInclusion(request.inclusion),
        file_match_pattern=request.file_match_pattern,
        priority=request.priority,
        override=request.override,
    )
    store.save_rule(rule)
    return _rule_to_response(rule)


@router.put("/{name}", response_model=RuleResponse)
async def update_rule(
    name: str,
    request: RuleUpdate,
    scope: str = Query("user"),
    store: RuleStore = Depends(get_rule_store),
):
    """更新规则"""
    scope_enum = RuleScope(scope)
    rule = store.get_rule(name, scope_enum)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # 更新字段
    if request.description is not None:
        rule.description = request.description
    if request.content is not None:
        rule.content = request.content
    if request.inclusion is not None:
        rule.inclusion = RuleInclusion(request.inclusion)
    if request.file_match_pattern is not None:
        rule.file_match_pattern = request.file_match_pattern
    if request.priority is not None:
        rule.priority = request.priority
    if request.override is not None:
        rule.override = request.override
    if request.enabled is not None:
        rule.enabled = request.enabled

    store.save_rule(rule)
    return _rule_to_response(rule)


@router.delete("/{name}", status_code=204)
async def delete_rule(
    name: str,
    scope: str = Query("user"),
    store: RuleStore = Depends(get_rule_store),
):
    """删除规则"""
    scope_enum = RuleScope(scope)
    if not store.delete_rule(name, scope_enum):
        raise HTTPException(status_code=404, detail="Rule not found")


@router.post("/validate", response_model=RuleValidateResponse)
async def validate_rule(request: RuleValidateRequest):
    """验证规则内容"""
    parser = RuleParser()
    errors = []
    warnings = []

    try:
        parser.parse_content(request.content, RuleScope.USER)
    except RuleParseError as e:
        errors.append(str(e))
    except Exception as e:
        errors.append(f"Unexpected error: {e}")

    # 检查内容大小
    if len(request.content) > 100_000:
        warnings.append("Rule content is very large, may impact performance")

    return RuleValidateResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


@router.get("/conflicts", response_model=RuleConflictResponse)
async def get_conflicts(store: RuleStore = Depends(get_rule_store)):
    """获取规则冲突"""
    rules = store.list_rules()

    # 检测同名规则
    name_map: dict[str, list[Rule]] = {}
    for rule in rules:
        if rule.name not in name_map:
            name_map[rule.name] = []
        name_map[rule.name].append(rule)

    conflicts = []
    for name, rule_list in name_map.items():
        if len(rule_list) > 1:
            scopes = [r.scope.value for r in rule_list]
            conflicts.append({
                "name": name,
                "scopes": scopes,
                "resolution": f"Using {rule_list[0].scope.value} scope (highest priority)",
            })

    return RuleConflictResponse(conflicts=conflicts)


@router.post("/reload", status_code=200)
async def reload_rules(store: RuleStore = Depends(get_rule_store)):
    """重新加载规则"""
    store.reload()
    rules = store.list_rules()
    return {"message": "Rules reloaded", "count": len(rules)}


def _rule_to_response(rule: Rule) -> RuleResponse:
    return RuleResponse(
        name=rule.name,
        description=rule.description,
        content=rule.content,
        scope=rule.scope.value,
        inclusion=rule.inclusion.value,
        file_match_pattern=rule.file_match_pattern,
        priority=rule.priority,
        override=rule.override,
        enabled=rule.enabled,
        source_path=rule.source_path,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
    )


def get_rule_store() -> RuleStore:
    """依赖注入：获取规则存储"""
    # 实际实现中从应用状态获取
    from fastapi import Request
    # return request.app.state.rule_store
    raise NotImplementedError("Implement in actual application")
```

## Data Models

### Rule File Format

规则文件使用 Markdown 格式，包含 YAML frontmatter：

```markdown
---
name: coding-standards
description: Python coding standards and best practices
inclusion: always
priority: 60
---

# Python Coding Standards

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Maximum line length: 100 characters

## Naming Conventions

- Classes: PascalCase
- Functions/variables: snake_case
- Constants: UPPER_SNAKE_CASE

## Documentation

- All public functions must have docstrings
- Use Google-style docstrings
```

### File Match Rule Example

```markdown
---
name: react-components
description: Guidelines for React component development
inclusion: fileMatch
fileMatchPattern: "**/*.tsx"
priority: 70
---

# React Component Guidelines

## Component Structure

- Use functional components with hooks
- Keep components small and focused
- Extract reusable logic into custom hooks

## State Management

- Use useState for local state
- Use useReducer for complex state logic
- Consider context for shared state
```

### Manual Rule Example

```markdown
---
name: security-review
description: Security review checklist for code changes
inclusion: manual
priority: 90
---

# Security Review Checklist

When reviewing code for security:

1. **Input Validation**
   - All user inputs are validated
   - SQL injection prevention
   - XSS prevention

2. **Authentication**
   - Proper session management
   - Secure password handling

3. **Authorization**
   - Role-based access control
   - Resource ownership verification
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Rule Parsing Round Trip
*For any* valid Rule object, serializing it to a rule file format and then parsing it back SHALL produce an equivalent Rule object with the same name, description, content, scope, inclusion mode, and priority.
**Validates: Requirements 1.1, 10.5**

### Property 2: Frontmatter Extraction Completeness
*For any* rule file with valid YAML frontmatter containing name, description, and optional fields (inclusion, fileMatchPattern, priority), parsing SHALL extract all specified fields correctly.
**Validates: Requirements 1.1, 1.4**

### Property 3: Invalid Frontmatter Handling
*For any* rule file with invalid YAML frontmatter (missing required fields, malformed YAML), the parser SHALL raise a RuleParseError without crashing the system.
**Validates: Requirements 1.2, 1.5**

### Property 4: Scope Priority Ordering
*For any* set of rules with the same name at different scopes, merging SHALL always select the rule from the highest-priority scope (session > project > user > global).
**Validates: Requirements 2.4, 2.5**

### Property 5: Always Inclusion Guarantee
*For any* rule with inclusion mode "always", the rule SHALL be included in the matched rules list regardless of the match context (files, manual references).
**Validates: Requirements 3.1**

### Property 6: FileMatch Pattern Correctness
*For any* rule with inclusion mode "fileMatch" and a glob pattern, the rule SHALL be included if and only if at least one file in the context matches the pattern.
**Validates: Requirements 3.2, 3.4**

### Property 7: Manual Reference Inclusion
*For any* rule with inclusion mode "manual", the rule SHALL be included if and only if its name appears in the manual_rules list of the match context.
**Validates: Requirements 3.3, 3.6**

### Property 8: Priority Ordering Consistency
*For any* set of matched rules, the final merged list SHALL be ordered by: scope priority (descending), then rule priority (descending), then alphabetically by name.
**Validates: Requirements 4.1, 4.2, 4.3**

### Property 9: Override Behavior
*For any* rule with override=true, if a lower-priority rule with the same name exists, the override rule SHALL replace it in the final list.
**Validates: Requirements 4.4**

### Property 10: Size Limit Truncation
*For any* set of rules whose total content exceeds the max_content_size limit, the merger SHALL truncate lower-priority rules first while keeping higher-priority rules intact.
**Validates: Requirements 4.5**

### Property 11: Path Safety Validation
*For any* file path used in rule loading or file references, the system SHALL reject paths that resolve outside the allowed directories (preventing path traversal).
**Validates: Requirements 12.1, 12.2**

### Property 12: Rule Serialization Completeness
*For any* Rule object, serializing to JSON and deserializing back SHALL produce an equivalent Rule with all fields preserved.
**Validates: Requirements 10.1, 10.2, 10.5**

### Property 13: Trace Recording Completeness
*For any* rule evaluation, the trace SHALL contain all evaluated rules, all matched rules with reasons, all skipped rules with reasons, and all conflicts detected.
**Validates: Requirements 13.1, 13.2**

### Property 14: Conflict Detection Accuracy
*For any* set of rules with duplicate names across different scopes, the conflict detector SHALL identify and report all such conflicts.
**Validates: Requirements 14.1, 14.4**

## Error Handling

### Parse Errors
- Invalid YAML frontmatter: Log warning, skip rule, continue loading others
- Missing required fields: Raise RuleParseError with field name
- File too large: Skip file, log warning with file path and size
- File read error: Log error, skip file, continue

### Runtime Errors
- Rule store unavailable: Use empty rule list, log error
- Pattern matching error: Skip rule, log error, continue with others
- Context extraction error: Use empty context, log warning

### API Errors
- Rule not found: Return 404 with rule name
- Duplicate rule: Return 409 with existing rule info
- Validation error: Return 400 with error details
- Server error: Return 500 with error ID for debugging

## Testing Strategy

### Unit Testing
- Rule parser: Test frontmatter extraction, content parsing, error handling
- Rule matcher: Test each inclusion mode, pattern matching, context extraction
- Rule merger: Test priority ordering, override behavior, size truncation
- Rule store: Test CRUD operations, caching, reload

### Property-Based Testing
Using Hypothesis library for Python:

- **Rule round-trip**: Generate random valid rules, serialize/deserialize, verify equivalence
- **Scope priority**: Generate rules at multiple scopes, verify correct selection
- **Pattern matching**: Generate file paths and patterns, verify correct matching
- **Size truncation**: Generate large rule sets, verify truncation preserves priority order

Each property-based test MUST:
- Run minimum 100 iterations
- Be tagged with the property number from this design document
- Use format: `**Feature: agent-rules, Property {number}: {property_text}**`

### Integration Testing
- CLI commands: Test list, create, edit, delete, validate
- REST API: Test all endpoints with valid and invalid inputs
- Middleware: Test rule injection into system prompt
- Hot reload: Test rule updates are reflected in next request
