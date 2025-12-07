#!/usr/bin/env python3
"""
版本管理工具 - 基于 Conventional Commits 自动分析和更新版本号

使用方法:
    # 分析某个模块的版本变更
    python scripts/version_manager.py analyze dataagent-server
    
    # 更新版本号
    python scripts/version_manager.py bump dataagent-server --type minor
    
    # 自动分析 git commits 并更新版本
    python scripts/version_manager.py auto-bump dataagent-server
    
    # 显示所有模块版本
    python scripts/version_manager.py show-all
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Literal

# 模块配置
MODULES = {
    "dataagent-core": {
        "path": "source/dataagent-core",
        "pyproject": "source/dataagent-core/pyproject.toml",
    },
    "dataagent-cli": {
        "path": "source/dataagent-cli",
        "pyproject": "source/dataagent-cli/pyproject.toml",
    },
    "dataagent-server": {
        "path": "source/dataagent-server",
        "pyproject": "source/dataagent-server/pyproject.toml",
    },
    "dataagent-server-demo": {
        "path": "source/dataagent-server-demo",
        "pyproject": "source/dataagent-server-demo/pyproject.toml",
    },
    "dataagent-harbor": {
        "path": "source/dataagent-harbor",
        "pyproject": "source/dataagent-harbor/pyproject.toml",
    },
}

# Conventional Commits 类型映射到版本变更
COMMIT_TYPE_TO_BUMP = {
    "feat": "minor",      # 新功能 -> minor
    "fix": "patch",       # 修复 -> patch
    "perf": "patch",      # 性能优化 -> patch
    "refactor": "patch",  # 重构 -> patch
    "docs": None,         # 文档 -> 不变更版本
    "style": None,        # 代码风格 -> 不变更版本
    "test": None,         # 测试 -> 不变更版本
    "chore": None,        # 杂项 -> 不变更版本
    "ci": None,           # CI -> 不变更版本
    "build": "patch",     # 构建 -> patch
}


def get_current_version(module: str) -> str:
    """获取模块当前版本号"""
    if module not in MODULES:
        raise ValueError(f"Unknown module: {module}")
    
    pyproject_path = Path(MODULES[module]["pyproject"])
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found: {pyproject_path}")
    
    content = pyproject_path.read_text()
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if not match:
        raise ValueError(f"Version not found in {pyproject_path}")
    
    return match.group(1)


def set_version(module: str, new_version: str) -> None:
    """设置模块版本号"""
    if module not in MODULES:
        raise ValueError(f"Unknown module: {module}")
    
    pyproject_path = Path(MODULES[module]["pyproject"])
    content = pyproject_path.read_text()
    
    # 替换版本号
    new_content = re.sub(
        r'(version\s*=\s*)"[^"]+"',
        f'\\1"{new_version}"',
        content
    )
    
    pyproject_path.write_text(new_content)
    print(f"✓ Updated {module} to version {new_version}")


def bump_version(
    current: str, 
    bump_type: Literal["major", "minor", "patch"]
) -> str:
    """计算新版本号"""
    parts = current.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {current}")
    
    major, minor, patch = map(int, parts)
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"


def get_commits_since_tag(module: str, tag: str | None = None) -> list[str]:
    """获取自上次 tag 以来的 commits"""
    module_path = MODULES[module]["path"]
    
    if tag:
        cmd = ["git", "log", f"{tag}..HEAD", "--oneline", "--", module_path]
    else:
        # 获取最近 50 条 commits
        cmd = ["git", "log", "-50", "--oneline", "--", module_path]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        return []


def parse_commit_type(commit_msg: str) -> tuple[str | None, bool]:
    """
    解析 commit message 的类型
    返回: (类型, 是否是 breaking change)
    """
    # 检查 breaking change
    is_breaking = "BREAKING CHANGE" in commit_msg or "!" in commit_msg.split(":")[0]
    
    # 解析类型: feat(scope): message 或 feat: message
    match = re.match(r"^[a-f0-9]+\s+(\w+)(?:\([^)]+\))?!?:", commit_msg)
    if match:
        return match.group(1).lower(), is_breaking
    
    return None, is_breaking


def analyze_commits(module: str) -> Literal["major", "minor", "patch"] | None:
    """分析 commits 确定版本变更类型"""
    commits = get_commits_since_tag(module)
    
    if not commits:
        print(f"No commits found for {module}")
        return None
    
    print(f"\nAnalyzing {len(commits)} commits for {module}:")
    
    max_bump: Literal["major", "minor", "patch"] | None = None
    
    for commit in commits:
        commit_type, is_breaking = parse_commit_type(commit)
        
        if is_breaking:
            print(f"  🔴 BREAKING: {commit}")
            max_bump = "major"
        elif commit_type:
            bump = COMMIT_TYPE_TO_BUMP.get(commit_type)
            if bump:
                icon = "🟡" if bump == "minor" else "🟢"
                print(f"  {icon} {commit_type}: {commit}")
                
                if max_bump is None:
                    max_bump = bump
                elif bump == "minor" and max_bump == "patch":
                    max_bump = "minor"
        else:
            print(f"  ⚪ (no type): {commit}")
    
    return max_bump


def show_all_versions() -> None:
    """显示所有模块版本"""
    print("\n📦 DataAgent 模块版本:\n")
    for module in MODULES:
        try:
            version = get_current_version(module)
            print(f"  {module}: {version}")
        except Exception as e:
            print(f"  {module}: ❌ {e}")


def cmd_analyze(args: argparse.Namespace) -> None:
    """分析命令"""
    module = args.module
    current = get_current_version(module)
    print(f"\n📦 {module} current version: {current}")
    
    bump_type = analyze_commits(module)
    
    if bump_type:
        new_version = bump_version(current, bump_type)
        print(f"\n📈 Suggested bump: {bump_type}")
        print(f"   {current} → {new_version}")
    else:
        print("\n✓ No version bump needed")


def cmd_bump(args: argparse.Namespace) -> None:
    """手动更新版本"""
    module = args.module
    bump_type = args.type
    
    current = get_current_version(module)
    new_version = bump_version(current, bump_type)
    
    print(f"\n📦 {module}: {current} → {new_version}")
    
    if not args.dry_run:
        set_version(module, new_version)
    else:
        print("(dry-run, no changes made)")


def cmd_auto_bump(args: argparse.Namespace) -> None:
    """自动分析并更新版本"""
    module = args.module
    current = get_current_version(module)
    
    print(f"\n📦 {module} current version: {current}")
    
    bump_type = analyze_commits(module)
    
    if bump_type:
        new_version = bump_version(current, bump_type)
        print(f"\n📈 Auto bump: {bump_type}")
        print(f"   {current} → {new_version}")
        
        if not args.dry_run:
            set_version(module, new_version)
        else:
            print("(dry-run, no changes made)")
    else:
        print("\n✓ No version bump needed")


def cmd_show_all(args: argparse.Namespace) -> None:
    """显示所有版本"""
    show_all_versions()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DataAgent 版本管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # analyze 命令
    analyze_parser = subparsers.add_parser("analyze", help="分析模块的版本变更")
    analyze_parser.add_argument("module", choices=list(MODULES.keys()))
    analyze_parser.set_defaults(func=cmd_analyze)
    
    # bump 命令
    bump_parser = subparsers.add_parser("bump", help="手动更新版本号")
    bump_parser.add_argument("module", choices=list(MODULES.keys()))
    bump_parser.add_argument("--type", "-t", choices=["major", "minor", "patch"], required=True)
    bump_parser.add_argument("--dry-run", "-n", action="store_true", help="只显示不执行")
    bump_parser.set_defaults(func=cmd_bump)
    
    # auto-bump 命令
    auto_parser = subparsers.add_parser("auto-bump", help="自动分析并更新版本")
    auto_parser.add_argument("module", choices=list(MODULES.keys()))
    auto_parser.add_argument("--dry-run", "-n", action="store_true", help="只显示不执行")
    auto_parser.set_defaults(func=cmd_auto_bump)
    
    # show-all 命令
    show_parser = subparsers.add_parser("show-all", help="显示所有模块版本")
    show_parser.set_defaults(func=cmd_show_all)
    
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
