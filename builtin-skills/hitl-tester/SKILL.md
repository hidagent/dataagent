---
name: hitl-tester
description: HITL 人机交互测试技能，用于测试和演示多步人机交互功能（选择、确认、输入、表单）
category: testing
tags: [hitl, human-in-the-loop, testing, interaction, demo]
---

# HITL 人机交互测试技能

## 概述

这个技能用于测试和演示 DataAgent 的人机交互 (Human-in-the-Loop) 功能。当用户说"测试人机交互"、"测试HITL"、"test hitl" 或类似请求时，你应该使用 `human` 工具来展示各种交互类型。

## 触发条件

当用户的消息包含以下关键词时触发此技能：
- "测试人机交互"
- "测试HITL"
- "test hitl"
- "演示交互卡片"
- "测试交互功能"

## 执行流程

**重要**: 这是一个多步交互流程。你需要按顺序调用 `human` 工具，并根据用户的响应决定下一步操作。

### 第一步：展示选择卡片

首先，使用 `human` 工具展示一个选择模式的交互卡片，让用户选择要测试的交互类型：

```
调用 human 工具，参数如下：
- interaction_type: "choice"
- title: "选择测试类型"
- message: "请选择您想要测试的交互类型："
- options:
  - id: "confirm", label: "确认模式", value: "confirm", type: "primary", description: "测试确认/取消对话框"
  - id: "input", label: "输入模式", value: "input", description: "测试文本输入框"
  - id: "form", label: "表单模式", value: "form", description: "测试多字段表单"
  - id: "all", label: "全部测试", value: "all", type: "secondary", description: "依次测试所有交互类型"
```

### 第二步：根据用户选择执行对应测试

根据用户在第一步的选择，执行相应的测试：

#### 如果用户选择 "confirm" (确认模式)

```
调用 human 工具，参数如下：
- interaction_type: "confirm"
- title: "确认操作测试"
- message: "这是一个确认对话框测试。\n\n您确定要继续执行此操作吗？"
- confirm_text: "是的，继续"
- cancel_text: "不，取消"
```

然后根据用户响应：
- 如果用户确认：回复 "✅ 您选择了确认操作。确认模式测试完成！"
- 如果用户取消：回复 "❌ 您选择了取消操作。确认模式测试完成！"

#### 如果用户选择 "input" (输入模式)

```
调用 human 工具，参数如下：
- interaction_type: "input"
- title: "文本输入测试"
- message: "请输入您的名字或任意文本："
- placeholder: "例如：张三"
- default_value: ""
```

然后根据用户响应：
- 回复 "📝 您输入的内容是：「{用户输入的内容}」\n\n输入模式测试完成！"

#### 如果用户选择 "form" (表单模式)

```
调用 human 工具，参数如下：
- interaction_type: "form"
- title: "表单填写测试"
- message: "请填写以下信息："
- fields:
  - id: "name", type: "text", label: "姓名", required: true, placeholder: "请输入您的姓名"
  - id: "age", type: "number", label: "年龄", placeholder: "请输入您的年龄"
  - id: "gender", type: "select", label: "性别", options: [{value: "male", label: "男"}, {value: "female", label: "女"}, {value: "other", label: "其他"}]
  - id: "bio", type: "textarea", label: "简介", placeholder: "请简单介绍一下自己"
```

然后根据用户响应：
- 回复 "📋 您提交的表单信息：\n- 姓名：{name}\n- 年龄：{age}\n- 性别：{gender}\n- 简介：{bio}\n\n表单模式测试完成！"

#### 如果用户选择 "all" (全部测试)

依次执行上述三种测试（confirm → input → form），每完成一个测试后继续下一个。

### 第三步：测试完成总结

所有测试完成后，给出总结：

```
## 🎉 HITL 测试完成！

您已成功测试了以下交互类型：
- ✅ 选择模式 (choice)
- ✅ 确认模式 (confirm) / 输入模式 (input) / 表单模式 (form)

人机交互功能运行正常！如需再次测试，请说"测试人机交互"。
```

## human 工具参数说明

`human` 工具支持以下参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| interaction_type | string | 是 | 交互类型：choice/confirm/input/form |
| title | string | 是 | 卡片标题 |
| message | string | 是 | 提示消息 |
| options | array | choice时必填 | 选项列表，每项包含 id, label, value, type?, description? |
| fields | array | form时必填 | 表单字段列表 |
| confirm_text | string | 否 | 确认按钮文本（默认"确认"） |
| cancel_text | string | 否 | 取消按钮文本（默认"取消"） |
| placeholder | string | 否 | 输入框占位符 |
| default_value | string | 否 | 输入框默认值 |
| timeout | number | 否 | 超时时间（秒） |

## 用户响应格式

用户交互后，你会收到一个响应对象，格式如下：

- **choice 响应**: `{"selected_option_id": "xxx", "selected_option_value": "xxx"}`
- **confirm 响应**: `{"confirmed": true/false}`
- **input 响应**: `{"input_value": "用户输入的文本"}`
- **form 响应**: `{"form_values": {"field_id": "value", ...}}`
- **取消响应**: `{"cancelled": true}`

## 注意事项

1. **等待用户响应**: 每次调用 `human` 工具后，必须等待用户响应才能继续
2. **处理取消操作**: 如果用户取消了操作（cancelled: true），应该友好地提示并询问是否继续
3. **多步交互**: 这是一个多步交互流程，根据用户的每一步选择决定下一步操作
4. **错误处理**: 如果用户响应格式异常，应该友好地提示并重新请求

## 示例对话

**用户**: 测试人机交互

**Agent**: 好的，我来为您演示 HITL 人机交互功能。首先请选择您想要测试的交互类型：
[调用 human 工具显示选择卡片]

**用户**: [点击"确认模式"]

**Agent**: 您选择了确认模式测试。现在我将展示一个确认对话框：
[调用 human 工具显示确认对话框]

**用户**: [点击"是的，继续"]

**Agent**: ✅ 您选择了确认操作。确认模式测试完成！

🎉 HITL 测试完成！人机交互功能运行正常。
