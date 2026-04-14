"""Provider-neutral CLI dialect contract and concrete Claude/Codex implementations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class ParsedEvent:
    """Normalized parser event that can represent both Claude and Codex streams."""

    session_id: str | None = None
    text: str | None = None
    tool: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None
    error: str | None = None
    raw_type: str | None = None


@dataclass(slots=True)
class CliRunConfig:
    """Provider-neutral argv configuration used by dialect builders."""

    binary_path: str
    cwd: str
    model: str
    permission_mode: str
    reasoning_level: str = "medium"
    allowed_tools: list[str] | None = None
    output_format: str | None = "stream-json"
    supports_model_flag: bool = True
    supports_permission_flag: bool = True
    supports_output_format_flag: bool = True
    supports_include_partial_messages: bool = False
    stream_json_requires_verbose: bool = False
    supports_reasoning_flag: bool = False
    disable_color: bool = True


class CliDialect(Protocol):
    """Protocol for provider-specific argv and JSONL parsing behavior."""

    def build_argv(self, prompt: str, config: CliRunConfig) -> list[str]:
        """Build argv for a fresh run."""

    def build_resume_argv(self, session_id: str, prompt: str, config: CliRunConfig) -> list[str]:
        """Build argv for a resumed run."""

    def parse_line(self, line: str) -> list[ParsedEvent]:
        """Parse one CLI output line into normalized events."""


class ClaudeDialect:
    """Claude argv builder + stream-json parser extracted from ClaudeProcess."""

    def __init__(self) -> None:
        self._pending_shell_tools: dict[str, dict[str, Any]] = {}

    def build_argv(self, prompt: str, config: CliRunConfig) -> list[str]:
        argv = [config.binary_path, "-p", prompt]

        output_mode = str(config.output_format or "").strip().lower()
        if config.supports_output_format_flag and output_mode in {"stream-json", "json"}:
            argv.extend(["--output-format", output_mode])

        if output_mode == "stream-json" and config.stream_json_requires_verbose:
            argv.append("--verbose")
        if output_mode == "stream-json" and config.supports_include_partial_messages:
            argv.append("--include-partial-messages")

        if config.supports_model_flag and config.model:
            argv.extend(["--model", config.model])

        if config.supports_permission_flag and config.permission_mode:
            argv.extend(["--permission-mode", config.permission_mode])

        if config.supports_reasoning_flag and config.reasoning_level:
            argv.extend(["--effort", config.reasoning_level])

        return argv

    def build_resume_argv(self, session_id: str, prompt: str, config: CliRunConfig) -> list[str]:
        argv = self.build_argv(prompt, config)
        if session_id:
            argv.extend(["--resume", session_id])
        return argv

    def parse_line(self, line: str) -> list[ParsedEvent]:
        event = self._parse_json_line(line.strip())
        if event is None:
            return []

        stream_event = event
        event_type = str(stream_event.get("type") or "").strip().lower()
        if event_type == "stream_event":
            nested_event = stream_event.get("event")
            if isinstance(nested_event, dict):
                stream_event = nested_event
                event_type = str(stream_event.get("type") or "").strip().lower()

        parsed_events: list[ParsedEvent] = []

        delta_texts = self._extract_text_deltas(stream_event)
        for text_chunk in delta_texts:
            parsed_events.append(ParsedEvent(text=text_chunk, raw_type=event_type))

        if event_type == "assistant":
            texts, tools = self._extract_assistant_content(stream_event.get("message"))
            if not delta_texts:
                for text_chunk in texts:
                    parsed_events.append(ParsedEvent(text=text_chunk, raw_type=event_type))
            for tool_data in tools:
                parsed_events.append(ParsedEvent(tool=tool_data, raw_type=event_type))
            return parsed_events

        if event_type == "content_block_start":
            block_payload = stream_event.get("content_block")
            if not isinstance(block_payload, dict):
                block_payload = stream_event.get("contentBlock")
            if isinstance(block_payload, dict) and str(block_payload.get("type") or "").strip().lower() == "tool_use":
                tool_data = self._extract_tool_data(block_payload)
                if tool_data is not None:
                    tool_use_id = str(tool_data.get("toolUseId") or "").strip()
                    if tool_use_id:
                        self._pending_shell_tools[tool_use_id] = dict(tool_data)
                    parsed_events.append(ParsedEvent(tool=tool_data, raw_type=event_type))
            return parsed_events

        if event_type == "tool_use":
            tool_data = self._extract_tool_data(stream_event)
            if tool_data is not None:
                tool_use_id = str(tool_data.get("toolUseId") or "").strip()
                if tool_use_id:
                    self._pending_shell_tools[tool_use_id] = dict(tool_data)
                parsed_events.append(ParsedEvent(tool=tool_data, raw_type=event_type))
            return parsed_events

        if event_type == "user":
            for tool_result_entry in self._extract_tool_result_entries(stream_event.get("message")):
                merged_tool = self._merge_tool_result_with_tool_use(tool_result_entry)
                if merged_tool is not None:
                    parsed_events.append(ParsedEvent(tool=merged_tool, raw_type=event_type))
            return parsed_events

        if event_type == "tool_result":
            tool_use_id = str(
                stream_event.get("tool_use_id")
                or stream_event.get("toolUseId")
                or stream_event.get("id")
                or ""
            ).strip()
            result_output = self._coerce_text(
                stream_event.get("content")
                or stream_event.get("output")
                or stream_event.get("result")
            )
            merged_tool = self._merge_tool_result_with_tool_use(
                {
                    "toolUseId": tool_use_id or None,
                    "output": result_output,
                }
            )
            if merged_tool is not None:
                parsed_events.append(ParsedEvent(tool=merged_tool, raw_type=event_type))
            return parsed_events

        if event_type == "result" or self._looks_like_result_payload(stream_event):
            session_id = stream_event.get("conversation_id") or stream_event.get("session_id")
            if isinstance(session_id, str) and session_id.strip():
                parsed_events.append(ParsedEvent(session_id=session_id.strip(), raw_type="result"))

            usage = stream_event.get("usage")
            usage_payload: dict[str, Any] | None = None
            if isinstance(usage, dict):
                usage_payload = {
                    "input_tokens": int(usage.get("input_tokens") or 0),
                    "output_tokens": int(usage.get("output_tokens") or 0),
                }

            raw_cost = stream_event.get("total_cost_usd")
            if isinstance(raw_cost, (int, float)):
                if usage_payload is None:
                    usage_payload = {}
                usage_payload["total_cost_usd"] = float(raw_cost)

            if usage_payload is not None:
                parsed_events.append(ParsedEvent(usage=usage_payload, raw_type="result"))

            raw_result = stream_event.get("result")
            if isinstance(raw_result, str) and raw_result:
                if bool(stream_event.get("is_error")):
                    parsed_events.append(ParsedEvent(error=raw_result.strip(), raw_type="result"))
                else:
                    parsed_events.append(ParsedEvent(text=raw_result, raw_type="result"))
            elif bool(stream_event.get("is_error")):
                parsed_events.append(ParsedEvent(error="Claude returned an error result.", raw_type="result"))

            return parsed_events

        if event_type == "error":
            message_text = stream_event.get("error") or stream_event.get("message") or stream_event.get("result")
            if isinstance(message_text, str) and message_text.strip():
                parsed_events.append(ParsedEvent(error=message_text.strip(), raw_type=event_type))
            return parsed_events

        if event_type == "system":
            subtype = str(stream_event.get("subtype") or "").strip().lower()
            if subtype in {"error", "warning"}:
                raw_message = stream_event.get("message") or stream_event.get("output")
                if isinstance(raw_message, str) and raw_message.strip():
                    parsed_events.append(ParsedEvent(error=raw_message.strip(), raw_type=event_type))
            return parsed_events

        return parsed_events

    @staticmethod
    def _looks_like_result_payload(event: dict[str, Any]) -> bool:
        return any(
            key in event
            for key in ("conversation_id", "session_id", "result", "is_error", "usage", "total_cost_usd")
        )

    @staticmethod
    def _parse_json_line(value: str) -> dict[str, Any] | None:
        if not value:
            return None
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
        return None

    def _extract_assistant_content(self, message: Any) -> tuple[list[str], list[dict[str, Any]]]:
        texts: list[str] = []
        tools: list[dict[str, Any]] = []

        if not isinstance(message, dict):
            return texts, tools

        content = message.get("content")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue

                block_type = str(block.get("type") or "").strip().lower()
                if block_type == "text":
                    chunk = block.get("text")
                    if isinstance(chunk, str) and chunk:
                        texts.append(chunk)
                    continue

                if block_type == "tool_use":
                    tool_data = self._extract_tool_data(block)
                    if tool_data is None:
                        continue
                    tool_use_id = str(tool_data.get("toolUseId") or "").strip()
                    if tool_use_id:
                        self._pending_shell_tools[tool_use_id] = dict(tool_data)
                    tools.append(tool_data)
                    continue

            return texts, tools

        if isinstance(content, str) and content:
            texts.append(content)

        message_text = message.get("text")
        if isinstance(message_text, str) and message_text:
            texts.append(message_text)

        return texts, tools

    def _extract_text_deltas(self, event: dict[str, Any]) -> list[str]:
        event_type = str(event.get("type") or "").strip().lower()
        if event_type in {"assistant", "result", "error", "system", "tool_use", "tool_result", "user"}:
            return []

        chunks: list[str] = []

        def _collect(value: Any) -> None:
            if isinstance(value, str):
                if value:
                    chunks.append(value)
                return
            if isinstance(value, list):
                for item in value:
                    _collect(item)
                return
            if not isinstance(value, dict):
                return

            value_type = str(value.get("type") or "").strip().lower()
            if value_type in {"tool_use", "tool_result"}:
                return

            text_value = value.get("text")
            if isinstance(text_value, str) and text_value:
                chunks.append(text_value)

            delta_value = value.get("delta")
            if isinstance(delta_value, str) and delta_value:
                chunks.append(delta_value)
            elif isinstance(delta_value, (dict, list)):
                _collect(delta_value)

            value_value = value.get("value")
            if isinstance(value_value, str) and value_value:
                chunks.append(value_value)

            content_value = value.get("content")
            if isinstance(content_value, (dict, list)):
                _collect(content_value)

        _collect(event.get("delta"))
        _collect(event.get("content_block"))
        _collect(event.get("contentBlock"))
        _collect(event.get("content"))
        message = event.get("message")
        if isinstance(message, dict):
            _collect(message.get("delta"))
            _collect(message.get("content"))

        deduped: list[str] = []
        for chunk in chunks:
            if deduped and deduped[-1] == chunk:
                continue
            deduped.append(chunk)
        return deduped

    def _extract_tool_data(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        text_limit = 12000
        command_limit = 400
        description_limit = 400

        def _pick_text(*values: Any) -> str:
            for value in values:
                text = self._coerce_text(value).strip()
                if text:
                    return text
            return ""

        tool_name = str(
            payload.get("name")
            or payload.get("tool_name")
            or (payload.get("tool", {}).get("name") if isinstance(payload.get("tool"), dict) else "")
            or "tool"
        )
        tool_input = payload.get("input")
        if not isinstance(tool_input, dict):
            tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            tool_input = {}

        tool_data: dict[str, Any] = {"name": tool_name}

        tool_use_id = str(
            payload.get("tool_use_id")
            or payload.get("toolUseId")
            or payload.get("id")
            or ""
        ).strip()
        if tool_use_id:
            tool_data["toolUseId"] = tool_use_id[:120]

        file_path = str(
            tool_input.get("file_path")
            or tool_input.get("path")
            or tool_input.get("target_file")
            or tool_input.get("target_path")
            or payload.get("file_path")
            or payload.get("path")
            or ""
        ).strip()
        if file_path:
            tool_data["path"] = file_path

        description = payload.get("description")
        if isinstance(description, str) and description.strip():
            tool_data["description"] = description.strip()[:description_limit]

        normalized_tool = tool_name.strip().lower()

        old_s = ""
        new_s = ""
        content = ""

        if normalized_tool in {"edit", "multiedit"}:
            old_s = _pick_text(
                tool_input.get("old_string"),
                tool_input.get("old_content"),
                tool_input.get("old"),
                payload.get("old_content"),
                payload.get("old"),
            )
            new_s = _pick_text(
                tool_input.get("new_string"),
                tool_input.get("new_content"),
                tool_input.get("new"),
                payload.get("new_content"),
                payload.get("new"),
            )
        elif normalized_tool == "write":
            old_s = _pick_text(
                tool_input.get("old_content"),
                tool_input.get("old"),
                payload.get("old_content"),
                payload.get("old"),
            )
            new_s = _pick_text(
                tool_input.get("content"),
                tool_input.get("new_content"),
                tool_input.get("new"),
                payload.get("content"),
                payload.get("new_content"),
                payload.get("new"),
            )
            content = new_s
        else:
            old_s = _pick_text(
                tool_input.get("old_content"),
                tool_input.get("old"),
                payload.get("old_content"),
                payload.get("old"),
            )
            new_s = _pick_text(
                tool_input.get("new_content"),
                tool_input.get("new"),
                payload.get("new_content"),
                payload.get("new"),
            )

        if old_s or new_s:
            clipped_old = self._clip_text(old_s, limit=text_limit)
            clipped_new = self._clip_text(new_s, limit=text_limit)
            tool_data["old"] = clipped_old
            tool_data["new"] = clipped_new
            tool_data["old_content"] = clipped_old
            tool_data["new_content"] = clipped_new

        if content:
            tool_data["content"] = self._clip_text(content, limit=text_limit)
        elif normalized_tool == "write":
            derived_content = _pick_text(new_s)
            if derived_content:
                tool_data["content"] = self._clip_text(derived_content, limit=text_limit)

        cmd = str(tool_input.get("command") or payload.get("command") or "").strip()
        if cmd:
            tool_data["command"] = cmd[:command_limit]

        output = _pick_text(
            payload.get("output"),
            payload.get("stdout"),
            payload.get("stderr"),
            payload.get("result"),
            payload.get("response"),
            payload.get("tool_output"),
            tool_input.get("output"),
            tool_input.get("stdout"),
            tool_input.get("stderr"),
            tool_input.get("result"),
        )
        if output:
            tool_data["output"] = self._clip_text(output, limit=text_limit)

        return tool_data

    @staticmethod
    def _clip_text(value: str, *, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[:limit]

    def _coerce_text(self, value: Any, *, depth: int = 0) -> str:
        if value is None or depth > 4:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            chunks = [self._coerce_text(item, depth=depth + 1).strip() for item in value]
            return "\n".join(chunk for chunk in chunks if chunk)
        if isinstance(value, dict):
            for key in ("text", "output", "stdout", "stderr", "result", "message", "content", "value"):
                nested = self._coerce_text(value.get(key), depth=depth + 1).strip()
                if nested:
                    return nested
            if depth <= 2:
                try:
                    return json.dumps(value, ensure_ascii=False)
                except (TypeError, ValueError):
                    return ""
        return ""

    def _extract_tool_result_entries(self, message: Any) -> list[dict[str, Any]]:
        if not isinstance(message, dict):
            return []
        content = message.get("content")
        if not isinstance(content, list):
            return []

        entries: list[dict[str, Any]] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if str(block.get("type") or "").strip().lower() != "tool_result":
                continue
            output = self._coerce_text(block.get("content") or block.get("output") or block.get("result")).strip()
            if not output:
                continue
            entries.append(
                {
                    "toolUseId": block.get("tool_use_id") or block.get("toolUseId") or block.get("id"),
                    "output": output,
                }
            )
        return entries

    def _merge_tool_result_with_tool_use(self, entry: dict[str, Any]) -> dict[str, Any] | None:
        tool_use_id = str(entry.get("toolUseId") or "").strip()
        output_text = self._coerce_text(entry.get("output")).strip()
        if not output_text:
            return None

        base_tool = self._pending_shell_tools.get(tool_use_id) if tool_use_id else None
        if base_tool:
            merged = dict(base_tool)
        else:
            merged = {"name": "tool_result"}
            if tool_use_id:
                merged["toolUseId"] = tool_use_id

        merged["output"] = self._clip_text(output_text, limit=12000)
        if tool_use_id and base_tool:
            self._pending_shell_tools.pop(tool_use_id, None)
        return merged


class CodexDialect:
    """Codex argv builder + JSONL parser based on verified local schema."""

    def build_argv(self, prompt: str, config: CliRunConfig) -> list[str]:
        argv = [config.binary_path, "exec"]
        argv.extend(
            self._build_exec_flags(
                config,
                include_color=True,
                include_cwd=True,
            )
        )
        argv.append(prompt)
        return argv

    def build_resume_argv(self, session_id: str, prompt: str, config: CliRunConfig) -> list[str]:
        argv = [config.binary_path, "exec", "resume"]
        argv.extend(
            self._build_exec_flags(
                config,
                include_color=False,
                include_cwd=False,
            )
        )
        argv.extend([session_id, prompt])
        return argv

    def parse_line(self, line: str) -> list[ParsedEvent]:
        event = self._parse_json_line(line.strip())
        if event is None:
            return []

        event_type = str(event.get("type") or "").strip().lower()
        parsed_events: list[ParsedEvent] = []

        if event_type == "thread.started":
            thread_id = event.get("thread_id")
            if isinstance(thread_id, str) and thread_id.strip():
                parsed_events.append(ParsedEvent(session_id=thread_id.strip(), raw_type=event_type))
            return parsed_events

        if event_type in {"item.started", "item.completed"}:
            item = event.get("item")
            if not isinstance(item, dict):
                return parsed_events
            item_type = str(item.get("type") or "").strip().lower()

            if item_type == "agent_message" and event_type == "item.completed":
                text = item.get("text")
                if isinstance(text, str) and text:
                    parsed_events.append(ParsedEvent(text=text, raw_type=event_type))
                return parsed_events

            if item_type == "command_execution":
                tool_payload: dict[str, Any] = {
                    "type": item_type,
                    "id": item.get("id"),
                    "command": item.get("command"),
                    "output": item.get("aggregated_output"),
                    "exit_code": item.get("exit_code"),
                    "status": item.get("status"),
                    "phase": "started" if event_type == "item.started" else "completed",
                }
                parsed_events.append(ParsedEvent(tool=tool_payload, raw_type=event_type))
                return parsed_events

            return parsed_events

        if event_type == "turn.completed":
            usage = event.get("usage")
            if isinstance(usage, dict):
                usage_payload = {
                    "input_tokens": int(usage.get("input_tokens") or 0),
                    "cached_input_tokens": int(usage.get("cached_input_tokens") or 0),
                    "output_tokens": int(usage.get("output_tokens") or 0),
                }
                parsed_events.append(ParsedEvent(usage=usage_payload, raw_type=event_type))
            return parsed_events

        if event_type in {"error", "turn.error", "turn.failed", "fatal"} or bool(event.get("is_error")):
            message = event.get("error") or event.get("message") or event.get("result")
            if isinstance(message, str) and message.strip():
                parsed_events.append(ParsedEvent(error=message.strip(), raw_type=event_type or "error"))
            else:
                parsed_events.append(ParsedEvent(error="Codex returned an error event.", raw_type=event_type or "error"))
            return parsed_events

        return parsed_events

    def _build_exec_flags(
        self,
        config: CliRunConfig,
        *,
        include_color: bool,
        include_cwd: bool,
    ) -> list[str]:
        argv: list[str] = ["--json"]

        if include_color and config.disable_color:
            argv.extend(["--color", "never"])

        if config.model:
            argv.extend(["-m", config.model])

        permission_flags = self._permission_flags(config.permission_mode)
        argv.extend(permission_flags)

        if include_cwd and config.cwd:
            argv.extend(["-C", config.cwd])

        return argv

    @staticmethod
    def _permission_flags(permission_mode: str) -> list[str]:
        normalized = str(permission_mode or "").strip().lower()

        if normalized == "auto":
            return ["--full-auto"]
        if normalized in {"bypasspermissions", "bypass_permissions", "bypass-permissions"}:
            return ["--dangerously-bypass-approvals-and-sandbox"]
        if normalized == "plan":
            return ["-s", "read-only"]
        if normalized in {"read-only", "workspace-write", "danger-full-access"}:
            return ["-s", normalized]
        return []

    @staticmethod
    def _parse_json_line(value: str) -> dict[str, Any] | None:
        if not value:
            return None
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
        return None
