#!/usr/bin/env python3
"""Test script for HITL functionality.

This script tests the human tool and HITL flow without running the full server.
"""

import asyncio
import json
from dataagent_core.tools.human import human


def test_human_tool_choice():
    """Test human tool with choice type."""
    print("\n=== Testing Choice Mode ===")
    result = human(
        interaction_type="choice",
        title="测试选择模式",
        message="请选择一个选项",
        options=[
            {"id": "1", "label": "选项A", "value": "a", "type": "primary"},
            {"id": "2", "label": "选项B", "value": "b"},
            {"id": "3", "label": "取消", "value": "cancel", "type": "danger"},
        ]
    )
    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
    assert result.get("__hitl_request__") == True
    assert result["request"]["type"] == "choice"
    assert len(result["request"]["options"]) == 3
    print("✅ Choice mode test passed!")


def test_human_tool_confirm():
    """Test human tool with confirm type."""
    print("\n=== Testing Confirm Mode ===")
    result = human(
        interaction_type="confirm",
        title="确认操作",
        message="您确定要继续吗？",
        confirm_text="是的",
        cancel_text="不了"
    )
    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
    assert result.get("__hitl_request__") == True
    assert result["request"]["type"] == "confirm"
    assert result["request"]["confirmText"] == "是的"
    print("✅ Confirm mode test passed!")


def test_human_tool_input():
    """Test human tool with input type."""
    print("\n=== Testing Input Mode ===")
    result = human(
        interaction_type="input",
        title="输入测试",
        message="请输入您的名字",
        placeholder="例如: 张三",
        default_value="默认值"
    )
    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
    assert result.get("__hitl_request__") == True
    assert result["request"]["type"] == "input"
    assert result["request"]["placeholder"] == "例如: 张三"
    print("✅ Input mode test passed!")


def test_human_tool_form():
    """Test human tool with form type."""
    print("\n=== Testing Form Mode ===")
    result = human(
        interaction_type="form",
        title="表单测试",
        message="请填写信息",
        fields=[
            {"id": "name", "type": "text", "label": "姓名", "required": True},
            {"id": "age", "type": "number", "label": "年龄"},
            {"id": "gender", "type": "select", "label": "性别", "options": [
                {"value": "m", "label": "男"},
                {"value": "f", "label": "女"}
            ]},
        ]
    )
    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
    assert result.get("__hitl_request__") == True
    assert result["request"]["type"] == "form"
    assert len(result["request"]["fields"]) == 3
    print("✅ Form mode test passed!")


def test_sse_hitl_handler():
    """Test SSE HITL handler."""
    print("\n=== Testing SSE HITL Handler ===")
    from dataagent_server.hitl.sse_handler import SSEHITLHandler
    
    # Test _build_human_tool_args
    tool_args = {
        "interaction_type": "choice",
        "title": "测试",
        "message": "请选择",
        "options": [{"id": "1", "label": "A", "value": "a"}]
    }
    hitl_args = SSEHITLHandler._build_human_tool_args(tool_args)
    print(f"HITL Args: {json.dumps(hitl_args, indent=2, ensure_ascii=False)}")
    assert hitl_args["type"] == "choice"
    assert hitl_args["title"] == "测试"
    assert len(hitl_args["options"]) == 1
    print("✅ SSE HITL Handler test passed!")
    
    # Test _build_tool_approval_args
    action_request = {
        "name": "shell",
        "args": {"command": "ls -la"},
        "description": "列出文件"
    }
    approval_args = SSEHITLHandler._build_tool_approval_args(action_request)
    print(f"Approval Args: {json.dumps(approval_args, indent=2, ensure_ascii=False)}")
    assert approval_args["type"] == "confirm"
    assert "shell" in approval_args["title"]
    print("✅ Tool approval args test passed!")


def main():
    """Run all tests."""
    print("=" * 60)
    print("HITL Functionality Tests")
    print("=" * 60)
    
    try:
        test_human_tool_choice()
        test_human_tool_confirm()
        test_human_tool_input()
        test_human_tool_form()
        test_sse_hitl_handler()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()
