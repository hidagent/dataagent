# DataAgent 架构设计方案

## 第五章：DataAgentCli 设计

### 5.1 设计原则

DataAgentCli 是精简的终端客户端，只包含：
1. 终端 UI 渲染
2. 终端输入处理
3. 终端 HITL 交互
4. CLI 命令解析

核心业务逻辑全部来自 DataAgentCore。

### 5.2 目录结构

```
libs/dataagent-cli/
├── pyproject.toml
├── README.md
├── dataagent_cli/
│   ├── __init__.py
│   ├── main.py               # CLI 入口
│   │
│   ├── # ========== 终端 UI ==========
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── console.py        # Rich console 封装
│   │   ├── renderer.py       # 事件渲染器
│   │   ├── diff.py           # Diff 渲染
│   │   ├── todo.py           # Todo 渲染
│   │   └── colors.py         # 颜色配置
│   │
│   ├── # ========== 输入处理 ==========
│   ├── input/
│   │   ├── __init__.py
│   │   ├── session.py        # PromptSession
│   │   ├── completers.py     # 自动补全
│   │   └── keybindings.py    # 快捷键
│   │
│   ├── # ========== HITL ==========
│   ├── hitl/
│   │   ├── __init__.py
│   │   └── terminal.py       # 终端 HITL 处理器
│   │
│   ├── # ========== 命令 ==========
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── slash.py          # 斜杠命令
│   │   ├── bash.py           # Bash 命令
│   │   └── skills.py         # 技能命令
│   │
│   └── # ========== 配置 ==========
│       └── config.py         # CLI 配置
│
└── tests/
```

### 5.3 核心实现

#### 5.3.1 事件渲染器

```python
# dataagent_cli/ui/renderer.py

from typing import AsyncIterator
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from dataagent_core.events import (
    ExecutionEvent, TextEvent, ToolCallEvent, ToolResultEvent,
    HITLRequestEvent, TodoUpdateEvent, FileOperationEvent,
    ErrorEvent, DoneEvent,
)
from dataagent_cli.ui.colors import COLORS
from dataagent_cli.ui.diff import render_diff_block
from dataagent_cli.ui.todo import render_todo_list


class TerminalRenderer:
    """终端事件渲染器"""
    
    def __init__(self, console: Console):
        self.console = console
        self._pending_text = ""
        self._has_responded = False
        self._spinner_active = False
        self._status = None
    
    async def render_events(
        self,
        events: AsyncIterator[ExecutionEvent],
    ):
        """渲染事件流"""
        self._start_spinner()
        
        try:
            async for event in events:
                await self._render_event(event)
        finally:
            self._stop_spinner()
    
    async def _render_event(self, event: ExecutionEvent):
        """渲染单个事件"""
        if isinstance(event, TextEvent):
            await self._render_text(event)
        elif isinstance(event, ToolCallEvent):
            await self._render_tool_call(event)
        elif isinstance(event, ToolResultEvent):
            await self._render_tool_result(event)
        elif isinstance(event, TodoUpdateEvent):
            await self._render_todo_update(event)
        elif isinstance(event, FileOperationEvent):
            await self._render_file_operation(event)
        elif isinstance(event, ErrorEvent):
            await self._render_error(event)
        elif isinstance(event, DoneEvent):
            await self._render_done(event)
    
    async def _render_text(self, event: TextEvent):
        """渲染文本"""
        self._pending_text += event.content
        
        if event.is_final:
            self._flush_text()
    
    def _flush_text(self):
        """刷新文本缓冲"""
        if not self._pending_text.strip():
            return
        
        self._stop_spinner()
        
        if not self._has_responded:
            self.console.print("●", style=COLORS["agent"], end=" ")
            self._has_responded = True
        
        markdown = Markdown(self._pending_text.rstrip())
        self.console.print(markdown, style=COLORS["agent"])
        self._pending_text = ""
    
    async def _render_tool_call(self, event: ToolCallEvent):
        """渲染工具调用"""
        self._flush_text()
        self._stop_spinner()
        
        icon = self._get_tool_icon(event.tool_name)
        display = self._format_tool_display(event.tool_name, event.tool_args)
        
        self.console.print(f"  {icon} {display}", style=f"dim {COLORS['tool']}")
        
        self._start_spinner(f"Executing {display}...")
    
    async def _render_tool_result(self, event: ToolResultEvent):
        """渲染工具结果"""
        if event.status == "error":
            self._stop_spinner()
            self.console.print(f"  [red]Error: {event.result}[/red]")
    
    async def _render_todo_update(self, event: TodoUpdateEvent):
        """渲染 Todo 更新"""
        self._stop_spinner()
        self.console.print()
        render_todo_list(self.console, event.todos)
        self.console.print()
    
    async def _render_file_operation(self, event: FileOperationEvent):
        """渲染文件操作"""
        self._stop_spinner()
        self.console.print()
        self._render_file_op_summary(event)
        if event.diff:
            render_diff_block(self.console, event.diff, event.file_path)
        self.console.print()
    
    async def _render_error(self, event: ErrorEvent):
        """渲染错误"""
        self._stop_spinner()
        self.console.print(f"[red]Error: {event.error}[/red]")
    
    async def _render_done(self, event: DoneEvent):
        """渲染完成"""
        self._stop_spinner()
        if self._has_responded:
            self.console.print()
    
    def _start_spinner(self, message: str = "Agent is thinking..."):
        """启动 spinner"""
        if not self._spinner_active:
            self._status = self.console.status(
                f"[bold {COLORS['thinking']}]{message}",
                spinner="dots",
            )
            self._status.start()
            self._spinner_active = True
        elif self._status:
            self._status.update(f"[bold {COLORS['thinking']}]{message}")
    
    def _stop_spinner(self):
        """停止 spinner"""
        if self._spinner_active and self._status:
            self._status.stop()
            self._spinner_active = False
    
    def _get_tool_icon(self, tool_name: str) -> str:
        """获取工具图标"""
        icons = {
            "read_file": "📖",
            "write_file": "✏️",
            "edit_file": "✂️",
            "ls": "📁",
            "glob": "🔍",
            "grep": "🔎",
            "shell": "⚡",
            "execute": "🔧",
            "web_search": "🌐",
            "http_request": "🌍",
            "task": "🤖",
            "write_todos": "📋",
        }
        return icons.get(tool_name, "🔧")
    
    def _format_tool_display(self, name: str, args: dict) -> str:
        """格式化工具显示"""
        # 简化显示逻辑
        if name in ("read_file", "write_file", "edit_file"):
            path = args.get("file_path") or args.get("path", "")
            return f"{name}({path})"
        elif name == "shell":
            cmd = args.get("command", "")[:80]
            return f'{name}("{cmd}")'
        else:
            return f"{name}(...)"
```

#### 5.3.2 终端 HITL 处理器

```python
# dataagent_cli/hitl/terminal.py

import sys
import termios
import tty
from rich.console import Console
from rich.panel import Panel
from rich import box

from dataagent_core.hitl import HITLHandler, ActionRequest, Decision
from dataagent_cli.ui.diff import render_diff_block


class TerminalHITLHandler(HITLHandler):
    """终端 HITL 处理器"""
    
    def __init__(self, console: Console):
        self.console = console
    
    async def request_approval(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> Decision:
        """请求用户审批"""
        # 显示操作信息
        self._display_action_info(action_request)
        
        # 获取用户选择
        selected = self._prompt_selection()
        
        if selected == 0:
            return {"type": "approve", "message": None}
        elif selected == 1:
            return {"type": "reject", "message": "User rejected"}
        else:
            # 自动审批模式
            return {"type": "auto_approve_all", "message": None}
    
    def _display_action_info(self, action_request: ActionRequest):
        """显示操作信息"""
        name = action_request["name"]
        description = action_request.get("description", "")
        
        self.console.print(
            Panel(
                f"[bold yellow]⚠️  Tool Action Requires Approval[/bold yellow]\n\n"
                f"{description}",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )
    
    def _prompt_selection(self) -> int:
        """提示用户选择"""
        options = ["approve", "reject", "auto-accept all"]
        selected = 0
        
        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            
            try:
                tty.setraw(fd)
                sys.stdout.write("\033[?25l")  # 隐藏光标
                
                while True:
                    self._render_options(options, selected)
                    
                    char = sys.stdin.read(1)
                    
                    if char == "\x1b":  # ESC
                        next1 = sys.stdin.read(1)
                        next2 = sys.stdin.read(1)
                        if next1 == "[":
                            if next2 == "B":  # Down
                                selected = (selected + 1) % len(options)
                            elif next2 == "A":  # Up
                                selected = (selected - 1) % len(options)
                    elif char in {"\r", "\n"}:
                        sys.stdout.write("\r\n")
                        break
                    elif char.lower() == "a":
                        selected = 0
                        break
                    elif char.lower() == "r":
                        selected = 1
                        break
            finally:
                sys.stdout.write("\033[?25h")  # 显示光标
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        except (termios.error, AttributeError):
            # 非 Unix 系统回退
            choice = input("Choice (A/R/Auto): ").strip().lower()
            if choice in {"r", "reject"}:
                selected = 1
            elif choice in {"auto"}:
                selected = 2
            else:
                selected = 0
        
        return selected
    
    def _render_options(self, options: list, selected: int):
        """渲染选项"""
        sys.stdout.write("\033[3A\r")  # 上移 3 行
        
        for i, option in enumerate(options):
            sys.stdout.write("\r\033[K")
            if i == selected:
                if option == "approve":
                    sys.stdout.write("\033[1;32m☑ Approve\033[0m\n")
                elif option == "reject":
                    sys.stdout.write("\033[1;31m☑ Reject\033[0m\n")
                else:
                    sys.stdout.write("\033[1;34m☑ Auto-accept all\033[0m\n")
            else:
                sys.stdout.write(f"\033[2m☐ {option.title()}\033[0m\n")
        
        sys.stdout.flush()
```

#### 5.3.3 CLI 主入口

```python
# dataagent_cli/main.py

import argparse
import asyncio
from pathlib import Path
from rich.console import Console

from dataagent_core.engine import AgentFactory, AgentExecutor, AgentConfig
from dataagent_core.config import Settings

from dataagent_cli.ui.renderer import TerminalRenderer
from dataagent_cli.ui.colors import COLORS, BANNER
from dataagent_cli.input.session import create_prompt_session
from dataagent_cli.hitl.terminal import TerminalHITLHandler
from dataagent_cli.commands.slash import handle_slash_command
from dataagent_cli.commands.bash import execute_bash_command


console = Console(highlight=False)


async def main_loop(
    agent_factory: AgentFactory,
    config: AgentConfig,
    session_state,
):
    """主循环"""
    # 创建 Agent
    agent, backend = agent_factory.create_agent(config)
    
    # 创建组件
    hitl_handler = TerminalHITLHandler(console)
    executor = AgentExecutor(agent, backend, hitl_handler, config.assistant_id)
    renderer = TerminalRenderer(console)
    prompt_session = create_prompt_session(session_state)
    
    # 显示欢迎信息
    console.print(BANNER, style=f"bold {COLORS['primary']}")
    console.print("Ready to work! What would you like to do?", style=COLORS["agent"])
    console.print()
    
    while True:
        try:
            user_input = await prompt_session.prompt_async()
            user_input = user_input.strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye!", style=COLORS["primary"])
            break
        
        if not user_input:
            continue
        
        # 斜杠命令
        if user_input.startswith("/"):
            result = handle_slash_command(user_input, console)
            if result == "exit":
                break
            continue
        
        # Bash 命令
        if user_input.startswith("!"):
            execute_bash_command(user_input, console)
            continue
        
        # 退出命令
        if user_input.lower() in ["quit", "exit", "q"]:
            console.print("\nGoodbye!", style=COLORS["primary"])
            break
        
        # 执行任务
        events = executor.execute(user_input, session_state.thread_id)
        await renderer.render_events(events)


def cli_main():
    """CLI 入口"""
    args = parse_args()
    
    # 初始化设置
    settings = Settings.from_environment()
    
    # 创建工厂
    agent_factory = AgentFactory(settings)
    
    # 创建配置
    config = AgentConfig(
        assistant_id=args.agent,
        auto_approve=args.auto_approve,
        sandbox_type=args.sandbox if args.sandbox != "none" else None,
    )
    
    # 创建会话状态
    session_state = SessionState(auto_approve=args.auto_approve)
    
    # 运行主循环
    asyncio.run(main_loop(agent_factory, config, session_state))


if __name__ == "__main__":
    cli_main()
```

### 5.4 依赖关系

```toml
# pyproject.toml

[project]
name = "dataagent-cli"
dependencies = [
    "dataagent-core",
    "rich>=13.0.0",
    "prompt-toolkit>=3.0.52",
]

[project.scripts]
dataagent = "dataagent_cli:cli_main"
```

---

下一章：[06-implementation-plan.md](./06-implementation-plan.md) - 实施计划
