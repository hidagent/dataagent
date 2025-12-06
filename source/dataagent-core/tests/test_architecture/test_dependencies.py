"""Tests for module dependency validation.

Property 22: 模块依赖单向性
DataAgentCli 和 DataAgentServer 可以导入 DataAgentCore, 
但 DataAgentCore 不能导入 CLI 或 Server
"""

import ast
import os
from pathlib import Path


def get_imports_from_file(file_path: Path) -> set[str]:
    """Extract all import statements from a Python file."""
    imports = set()
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except SyntaxError:
        return imports
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    
    return imports


def get_all_imports_from_package(package_path: Path) -> set[str]:
    """Get all imports from all Python files in a package."""
    all_imports = set()
    
    for py_file in package_path.rglob("*.py"):
        # Skip test files
        if "test" in str(py_file):
            continue
        all_imports.update(get_imports_from_file(py_file))
    
    return all_imports


class TestModuleDependencies:
    """Tests for module dependency validation."""
    
    def test_core_does_not_import_cli(self):
        """
        **Feature: dataagent-development-specs, Property 22: 模块依赖单向性**
        
        DataAgentCore must not import DataAgentCli.
        **Validates: Requirements 1.5**
        """
        core_path = Path(__file__).parent.parent.parent / "dataagent_core"
        
        if not core_path.exists():
            # Skip if running from different location
            return
        
        imports = get_all_imports_from_package(core_path)
        
        assert "dataagent_cli" not in imports, \
            "DataAgentCore should not import dataagent_cli"
    
    def test_core_does_not_import_server(self):
        """
        **Feature: dataagent-development-specs, Property 22: 模块依赖单向性**
        
        DataAgentCore must not import DataAgentServer.
        **Validates: Requirements 1.5**
        """
        core_path = Path(__file__).parent.parent.parent / "dataagent_core"
        
        if not core_path.exists():
            # Skip if running from different location
            return
        
        imports = get_all_imports_from_package(core_path)
        
        assert "dataagent_server" not in imports, \
            "DataAgentCore should not import dataagent_server"
    
    def test_core_modules_have_init_files(self):
        """
        **Feature: dataagent-development-specs**
        
        All core modules must have __init__.py files.
        **Validates: Requirements 1.3**
        """
        core_path = Path(__file__).parent.parent.parent / "dataagent_core"
        
        if not core_path.exists():
            return
        
        # Check all subdirectories have __init__.py
        for subdir in core_path.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("__"):
                init_file = subdir / "__init__.py"
                assert init_file.exists(), \
                    f"Module {subdir.name} is missing __init__.py"
    
    def test_core_public_api_exports(self):
        """
        **Feature: dataagent-development-specs**
        
        Core module should export all public APIs.
        **Validates: Requirements 1.3**
        """
        from dataagent_core import __all__
        
        expected_exports = [
            # Config
            "Settings",
            "SessionState",
            # Engine
            "AgentFactory",
            "AgentExecutor",
            "AgentConfig",
            # Events
            "ExecutionEvent",
            "TextEvent",
            "ToolCallEvent",
            "ToolResultEvent",
            "HITLRequestEvent",
            "TodoUpdateEvent",
            "FileOperationEvent",
            "ErrorEvent",
            "DoneEvent",
            # HITL
            "HITLHandler",
            "ActionRequest",
            "Decision",
            # Session
            "Session",
            "SessionStore",
            "MemorySessionStore",
            "SessionManager",
        ]
        
        for export in expected_exports:
            assert export in __all__, \
                f"Expected {export} to be in __all__"
