"""Agent executor for running agents and producing event streams."""

import json
import time
from typing import AsyncIterator, Any

from langchain.agents.middleware.human_in_the_loop import HITLRequest
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.pregel import Pregel
from langgraph.types import Command
from pydantic import TypeAdapter, ValidationError

from dataagent_core.events import (
    ExecutionEvent,
    TextEvent,
    ToolCallEvent,
    ToolResultEvent,
    HITLRequestEvent,
    TodoUpdateEvent,
    FileOperationEvent,
    ErrorEvent,
    DoneEvent,
)
from dataagent_core.hitl import HITLHandler, Decision
from dataagent_core.tools.file_tracker import FileOpTracker

_HITL_REQUEST_ADAPTER = TypeAdapter(HITLRequest)


class AgentExecutor:
    """Executor for running agents and producing event streams."""

    def __init__(
        self,
        agent: Pregel,
        backend: Any,
        hitl_handler: HITLHandler | None = None,
        assistant_id: str | None = None,
    ):
        self.agent = agent
        self.backend = backend
        self.hitl_handler = hitl_handler
        self.assistant_id = assistant_id
        self._file_tracker = FileOpTracker(assistant_id=assistant_id, backend=backend)

    async def execute(
        self,
        user_input: str,
        session_id: str,
        context: dict | None = None,
    ) -> AsyncIterator[ExecutionEvent]:
        """Execute user input and yield events."""
        config = {
            "configurable": {"thread_id": session_id},
            "metadata": {"assistant_id": self.assistant_id} if self.assistant_id else {},
        }

        stream_input = {"messages": [{"role": "user", "content": user_input}]}

        try:
            async for event in self._execute_stream(stream_input, config, session_id):
                yield event
        except Exception as e:
            yield ErrorEvent(
                error=str(e),
                recoverable=False,
            )

    async def _execute_stream(
        self,
        stream_input: dict,
        config: dict,
        session_id: str,
    ) -> AsyncIterator[ExecutionEvent]:
        """Internal execution stream with HITL handling."""
        displayed_tool_ids = set()
        tool_call_buffers: dict[str | int, dict] = {}
        pending_text = ""
        current_todos = None

        while True:
            pending_interrupts: dict[str, HITLRequest] = {}

            async for chunk in self.agent.astream(
                stream_input,
                stream_mode=["messages", "updates"],
                subgraphs=True,
                config=config,
                durability="exit",
            ):
                if not isinstance(chunk, tuple) or len(chunk) != 3:
                    continue

                _namespace, stream_mode, data = chunk

                # Handle updates stream
                if stream_mode == "updates":
                    if not isinstance(data, dict):
                        continue

                    # Check for interrupts
                    if "__interrupt__" in data:
                        for interrupt_obj in data["__interrupt__"]:
                            try:
                                validated_request = _HITL_REQUEST_ADAPTER.validate_python(
                                    interrupt_obj.value
                                )
                                pending_interrupts[interrupt_obj.id] = validated_request
                            except ValidationError:
                                pass

                    # Check for todo updates
                    chunk_data = next(iter(data.values())) if data else None
                    if chunk_data and isinstance(chunk_data, dict) and "todos" in chunk_data:
                        new_todos = chunk_data["todos"]
                        if new_todos != current_todos:
                            current_todos = new_todos
                            yield TodoUpdateEvent(todos=new_todos)

                # Handle messages stream
                elif stream_mode == "messages":
                    if not isinstance(data, tuple) or len(data) != 2:
                        continue

                    message, _metadata = data

                    # Handle tool messages
                    if isinstance(message, ToolMessage):
                        tool_name = getattr(message, "name", "")
                        tool_status = getattr(message, "status", "success")
                        content = message.content
                        if isinstance(content, list):
                            content = "\n".join(str(item) for item in content)
                        else:
                            content = str(content) if content else ""

                        yield ToolResultEvent(
                            tool_call_id=message.tool_call_id,
                            result=content,
                            status=tool_status,
                        )

                        # Complete file operation tracking
                        record = self._file_tracker.complete_with_message(message)
                        if record:
                            yield FileOperationEvent(
                                operation=record.tool_name,
                                file_path=record.display_path,
                                metrics={
                                    "lines_read": record.metrics.lines_read,
                                    "lines_written": record.metrics.lines_written,
                                    "lines_added": record.metrics.lines_added,
                                    "lines_removed": record.metrics.lines_removed,
                                },
                                diff=record.diff,
                                status=record.status,
                            )
                        continue

                    # Handle AI message chunks
                    if not hasattr(message, "content_blocks"):
                        continue

                    for block in message.content_blocks:
                        block_type = block.get("type")

                        if block_type == "text":
                            text = block.get("text", "")
                            if text:
                                pending_text += text
                                yield TextEvent(content=text, is_final=False)

                        elif block_type in ("tool_call_chunk", "tool_call"):
                            chunk_name = block.get("name")
                            chunk_args = block.get("args")
                            chunk_id = block.get("id")
                            chunk_index = block.get("index")

                            buffer_key = chunk_index if chunk_index is not None else (chunk_id or f"unknown-{len(tool_call_buffers)}")
                            buffer = tool_call_buffers.setdefault(
                                buffer_key,
                                {"name": None, "id": None, "args": None, "args_parts": []},
                            )

                            if chunk_name:
                                buffer["name"] = chunk_name
                            if chunk_id:
                                buffer["id"] = chunk_id

                            if isinstance(chunk_args, dict):
                                buffer["args"] = chunk_args
                                buffer["args_parts"] = []
                            elif isinstance(chunk_args, str):
                                if chunk_args:
                                    parts = buffer.setdefault("args_parts", [])
                                    if not parts or chunk_args != parts[-1]:
                                        parts.append(chunk_args)
                                    buffer["args"] = "".join(parts)
                            elif chunk_args is not None:
                                buffer["args"] = chunk_args

                            buffer_name = buffer.get("name")
                            buffer_id = buffer.get("id")
                            if buffer_name is None:
                                continue

                            parsed_args = buffer.get("args")
                            if isinstance(parsed_args, str):
                                if not parsed_args:
                                    continue
                                try:
                                    parsed_args = json.loads(parsed_args)
                                except json.JSONDecodeError:
                                    continue
                            elif parsed_args is None:
                                continue

                            if not isinstance(parsed_args, dict):
                                parsed_args = {"value": parsed_args}

                            if buffer_id is not None:
                                if buffer_id not in displayed_tool_ids:
                                    displayed_tool_ids.add(buffer_id)
                                    self._file_tracker.start_operation(
                                        buffer_name, parsed_args, buffer_id
                                    )

                                    yield ToolCallEvent(
                                        tool_name=buffer_name,
                                        tool_args=parsed_args,
                                        tool_call_id=buffer_id,
                                    )
                                else:
                                    self._file_tracker.update_args(buffer_id, parsed_args)

                            tool_call_buffers.pop(buffer_key, None)

                    if getattr(message, "chunk_position", None) == "last":
                        if pending_text:
                            yield TextEvent(content="", is_final=True)
                            pending_text = ""

            # Handle HITL interrupts
            if pending_interrupts:
                hitl_response = await self._handle_hitl(pending_interrupts, session_id)

                if hitl_response is None:
                    yield DoneEvent(cancelled=True)
                    return

                stream_input = Command(resume=hitl_response)
            else:
                yield DoneEvent()
                return

    async def _handle_hitl(
        self,
        pending_interrupts: dict,
        session_id: str,
    ) -> dict | None:
        """Handle HITL interrupts."""
        if not self.hitl_handler:
            # Auto-approve all
            return {
                interrupt_id: {
                    "decisions": [{"type": "approve"} for _ in request["action_requests"]]
                }
                for interrupt_id, request in pending_interrupts.items()
            }

        hitl_response = {}

        for interrupt_id, request in pending_interrupts.items():
            decisions = []

            for action_request in request["action_requests"]:
                decision = await self.hitl_handler.request_approval(
                    action_request,
                    session_id,
                )
                decisions.append(decision)

                if decision.get("type") == "reject":
                    return None

            hitl_response[interrupt_id] = {"decisions": decisions}

        return hitl_response
