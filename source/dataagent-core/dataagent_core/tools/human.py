"""Human interaction tool for DataAgent Core.

This tool allows the agent to request user interaction through various UI components:
- choice: Multiple choice selection
- confirm: Yes/No confirmation
- input: Text input
- form: Multi-field form

The tool triggers a HITL (Human-in-the-Loop) interrupt and waits for user response.
"""

from typing import Literal, Any


def human(
    interaction_type: Literal["choice", "confirm", "input", "form"],
    title: str,
    message: str,
    options: list[dict[str, Any]] | None = None,
    fields: list[dict[str, Any]] | None = None,
    confirm_text: str = "确认",
    cancel_text: str = "取消",
    placeholder: str | None = None,
    default_value: str | None = None,
    timeout: int | None = None,
) -> dict[str, Any]:
    """Request user interaction through a UI component.
    
    This tool pauses agent execution and displays an interactive UI to the user.
    The agent will receive the user's response and can continue based on it.
    
    Args:
        interaction_type: Type of interaction UI to display.
            - "choice": Display multiple options for user to select one
            - "confirm": Display a confirmation dialog with confirm/cancel buttons
            - "input": Display a text input field
            - "form": Display a multi-field form
        title: Title displayed at the top of the interaction card.
        message: Descriptive message explaining what the user should do.
        options: List of options for "choice" type. Each option should have:
            - id: Unique identifier for the option
            - label: Display text for the option
            - value: Value returned when selected
            - type: Optional, "primary" | "secondary" | "danger" for styling
            - description: Optional description text
        fields: List of form fields for "form" type. Each field should have:
            - id: Unique identifier for the field
            - type: "text" | "number" | "select" | "textarea"
            - label: Display label for the field
            - placeholder: Optional placeholder text
            - required: Optional boolean, whether field is required
            - options: For "select" type, list of {value, label} options
        confirm_text: Text for the confirm/submit button (default: "确认")
        cancel_text: Text for the cancel button (default: "取消")
        placeholder: Placeholder text for "input" type
        default_value: Default value for "input" type
        timeout: Optional timeout in seconds for user response
        
    Returns:
        dict containing the user's response:
        - For "choice": {"selected_option_id": str, "selected_option_value": str}
        - For "confirm": {"confirmed": bool}
        - For "input": {"input_value": str}
        - For "form": {"form_values": dict}
        - If cancelled: {"cancelled": True}
        
    Examples:
        # Choice interaction
        result = human(
            interaction_type="choice",
            title="选择操作",
            message="请选择要执行的操作",
            options=[
                {"id": "1", "label": "继续执行", "value": "continue", "type": "primary"},
                {"id": "2", "label": "跳过此步", "value": "skip"},
                {"id": "3", "label": "取消操作", "value": "cancel", "type": "danger"},
            ]
        )
        
        # Confirmation
        result = human(
            interaction_type="confirm",
            title="确认删除",
            message="确定要删除这个文件吗？此操作不可撤销。",
            confirm_text="删除",
            cancel_text="保留"
        )
        
        # Text input
        result = human(
            interaction_type="input",
            title="输入名称",
            message="请输入新文件的名称",
            placeholder="例如: my_file.py",
            default_value="untitled.py"
        )
        
        # Form
        result = human(
            interaction_type="form",
            title="配置参数",
            message="请填写以下配置信息",
            fields=[
                {"id": "name", "type": "text", "label": "名称", "required": True},
                {"id": "count", "type": "number", "label": "数量", "placeholder": "输入数字"},
                {"id": "type", "type": "select", "label": "类型", "options": [
                    {"value": "a", "label": "类型A"},
                    {"value": "b", "label": "类型B"}
                ]},
            ]
        )
    """
    # Build the request payload
    # This will be intercepted by the HITL middleware and sent to the frontend
    request = {
        "type": interaction_type,
        "title": title,
        "message": message,
    }
    
    if interaction_type == "choice":
        if not options:
            return {"error": "options is required for choice type"}
        request["options"] = options
        
    elif interaction_type == "confirm":
        request["confirmText"] = confirm_text
        request["cancelText"] = cancel_text
        
    elif interaction_type == "input":
        if placeholder:
            request["placeholder"] = placeholder
        if default_value:
            request["defaultValue"] = default_value
            
    elif interaction_type == "form":
        if not fields:
            return {"error": "fields is required for form type"}
        request["fields"] = fields
    
    if timeout:
        request["timeout"] = timeout
    
    # The actual HITL interrupt is handled by the middleware
    # This return value is a placeholder - the real response comes from user interaction
    # The middleware will intercept this tool call and handle the HITL flow
    return {
        "__hitl_request__": True,
        "request": request,
    }


# Tool metadata for registration
human.__doc_short__ = "Request user interaction through UI components (choice, confirm, input, form)"
