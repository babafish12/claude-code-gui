"""Provider-neutral CLI dialect contract and concrete Claude/Codex implementations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

_SAFE_CLI_TOKEN_RE = re.compile(r"^[A-Za-z0-9._:/+\-@]{1,160}$")
_SAFE_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9._:\-]{1,160}$")
_SAFE_REASONING_LEVELS = {"low", "medium", "high", "xhigh", "minimal"}
_MAX_PENDING_TOOL_ITEMS = 100


def _sanitize_cli_token(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("-"):
        return ""
    if _SAFE_CLI_TOKEN_RE.fullmatch(text) is None:
        return ""
    return text


def _sanitize_session_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("-"):
        return ""
    if _SAFE_SESSION_ID_RE.fullmatch(text) is None:
        return ""
    return text


def _sanitize_reasoning_level(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in _SAFE_REASONING_LEVELS:
        return text
    return "medium"


def _sanitize_path_arg(value: Any) -> str:
    text = str(value or "")
    if not text.strip():
        return ""
    if any(ch in text for ch in ("\x00", "\n", "\r")):
        return ""
    return text


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _remember_pending_tool(
    pending_tools: dict[str, dict[str, Any]],
    tool_use_id: str,
    payload: dict[str, Any],
) -> None:
    if not tool_use_id:
        return
    pending_tools.pop(tool_use_id, None)
    pending_tools[tool_use_id] = dict(payload)
    while len(pending_tools) > _MAX_PENDING_TOOL_ITEMS:
        oldest_key = next(iter(pending_tools))
        pending_tools.pop(oldest_key, None)


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

        model_value = _sanitize_cli_token(config.model)
        if config.supports_model_flag and model_value:
            argv.extend(["--model", model_value])

        permission_value = _sanitize_cli_token(config.permission_mode)
        if config.supports_permission_flag and permission_value:
            argv.extend(["--permission-mode", permission_value])

        if config.supports_reasoning_flag:
            argv.extend(["--effort", _sanitize_reasoning_level(config.reasoning_level)])

        return argv

    def build_resume_argv(self, session_id: str, prompt: str, config: CliRunConfig) -> list[str]:
        argv = self.build_argv(prompt, config)
        safe_session_id = _sanitize_session_id(session_id)
        if safe_session_id:
            argv.extend(["--resume", safe_session_id])
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
                        _remember_pending_tool(self._pending_shell_tools, tool_use_id, tool_data)
                    parsed_events.append(ParsedEvent(tool=tool_data, raw_type=event_type))
            return parsed_events

        if event_type == "tool_use":
            tool_data = self._extract_tool_data(stream_event)
            if tool_data is not None:
                tool_use_id = str(tool_data.get("toolUseId") or "").strip()
                _remember_pending_tool(self._pending_shell_tools, tool_use_id, tool_data)
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
                    "input_tokens": _coerce_int(usage.get("input_tokens") or 0),
                    "output_tokens": _coerce_int(usage.get("output_tokens") or 0),
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

            self._pending_shell_tools.clear()
            return parsed_events

        if event_type == "error":
            message_text = stream_event.get("error") or stream_event.get("message") or stream_event.get("result")
            if isinstance(message_text, str) and message_text.strip():
                parsed_events.append(ParsedEvent(error=message_text.strip(), raw_type=event_type))
            self._pending_shell_tools.clear()
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


class GeminiDialect:
    """Gemini argv builder + stream parser for headless JSON/stream-json events."""

    def __init__(self) -> None:
        self._pending_tools: dict[str, dict[str, Any]] = {}

    def build_argv(self, prompt: str, config: CliRunConfig) -> list[str]:
        argv = [config.binary_path]
        argv.extend(self._build_common_flags(config))
        argv.extend(["-p", prompt])
        return argv

    def build_resume_argv(self, session_id: str, prompt: str, config: CliRunConfig) -> list[str]:
        argv = [config.binary_path]
        argv.extend(self._build_common_flags(config))
        safe_session_id = _sanitize_session_id(session_id)
        if safe_session_id:
            argv.extend(["--resume", safe_session_id])
        argv.extend(["-p", prompt])
        return argv

    def parse_line(self, line: str) -> list[ParsedEvent]:
        event = self._parse_json_line(line.strip())
        if event is None:
            return []
        return self._parse_event(event)

    def _parse_event(self, event: dict[str, Any]) -> list[ParsedEvent]:
        parsed_events: list[ParsedEvent] = []
        event_type = str(event.get("type") or "").strip().lower()

        if event_type == "stream_event":
            nested = event.get("event")
            if isinstance(nested, dict):
                return self._parse_event(nested)
            return parsed_events

        session_id = self._coerce_text(
            event.get("session_id")
            or event.get("sessionId")
            or event.get("session")
            or event.get("id")
        )

        if event_type == "init":
            self._pending_tools.clear()
            if session_id:
                parsed_events.append(ParsedEvent(session_id=session_id, raw_type=event_type))
            return parsed_events

        if event_type == "message":
            role = self._coerce_text(event.get("role")).lower()
            message_content = event.get("content")
            text = self._extract_text_payload(message_content or event.get("text") or event.get("message"))
            if session_id:
                parsed_events.append(ParsedEvent(session_id=session_id, raw_type=event_type))
            if role == "assistant" and text:
                parsed_events.append(ParsedEvent(text=text, raw_type=event_type))
            elif role not in {"user", "assistant"} and text:
                parsed_events.append(ParsedEvent(text=text, raw_type=event_type))
            if isinstance(message_content, list):
                for block in message_content:
                    if not isinstance(block, dict):
                        continue
                    block_type = str(block.get("type") or "").strip().lower()
                    if self._looks_like_tool_call_event(block_type, block):
                        tool_payload = self._parse_tool_payload(block)
                        if tool_payload is not None:
                            parsed_events.append(ParsedEvent(tool=tool_payload, raw_type=block_type or event_type))
                        continue
                    if self._looks_like_tool_output_event(block_type, block):
                        tool_payload = self._parse_tool_output_payload(block)
                        if tool_payload is not None:
                            parsed_events.append(ParsedEvent(tool=tool_payload, raw_type=block_type or event_type))
            return parsed_events

        if self._looks_like_tool_call_event(event_type, event):
            tool_payload = self._parse_tool_payload(event)
            if tool_payload is not None:
                parsed_events.append(ParsedEvent(tool=tool_payload, raw_type=event_type))
            return parsed_events

        if self._looks_like_tool_output_event(event_type, event):
            tool_payload = self._parse_tool_output_payload(event)
            if tool_payload is not None:
                parsed_events.append(ParsedEvent(tool=tool_payload, raw_type=event_type))
            return parsed_events

        if event_type in {"error", "fatal"}:
            self._pending_tools.clear()
            error_text = self._extract_text_payload(
                event.get("error")
                or event.get("message")
                or event.get("content")
                or event.get("result")
            ) or "Gemini returned an error event."
            parsed_events.append(ParsedEvent(error=error_text, raw_type=event_type))
            return parsed_events

        if event_type in {"done", "result", "complete", "completed"}:
            self._pending_tools.clear()
            if session_id:
                parsed_events.append(ParsedEvent(session_id=session_id, raw_type=event_type))
            usage = self._extract_usage_payload(event.get("usage"))
            if usage is not None:
                parsed_events.append(ParsedEvent(usage=usage, raw_type=event_type))

            status_text = self._coerce_text(event.get("status")).lower()
            result_text = self._extract_text_payload(
                event.get("result")
                or event.get("message")
                or event.get("content")
                or event.get("text")
            )
            if status_text in {"error", "failed", "failure"}:
                parsed_events.append(
                    ParsedEvent(
                        error=result_text or "Gemini reported an unsuccessful completion.",
                        raw_type=event_type,
                    )
                )
            elif result_text:
                parsed_events.append(ParsedEvent(text=result_text, raw_type=event_type))
            return parsed_events

        if session_id:
            parsed_events.append(ParsedEvent(session_id=session_id, raw_type=event_type or "event"))

        fallback_text = self._extract_text_payload(event)
        if fallback_text:
            parsed_events.append(ParsedEvent(text=fallback_text, raw_type=event_type or "event"))
        return parsed_events

    @staticmethod
    def _extract_usage_payload(raw_usage: Any) -> dict[str, Any] | None:
        if not isinstance(raw_usage, dict):
            return None

        def _to_int(value: Any) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0

        usage_payload = {
            "input_tokens": _to_int(raw_usage.get("input_tokens") or raw_usage.get("inputTokens")),
            "cached_input_tokens": _to_int(
                raw_usage.get("cached_input_tokens")
                or raw_usage.get("cachedInputTokens")
            ),
            "output_tokens": _to_int(raw_usage.get("output_tokens") or raw_usage.get("outputTokens")),
        }
        return usage_payload

    @staticmethod
    def _looks_like_tool_call_event(event_type: str, event: dict[str, Any]) -> bool:
        if event_type in {"tool_call", "tool_use", "tool", "function_call", "toolcall", "functioncall"}:
            return True
        return any(
            isinstance(event.get(key), dict)
            for key in ("tool_call", "toolCall", "function_call", "functionCall")
        )

    @staticmethod
    def _looks_like_tool_output_event(event_type: str, event: dict[str, Any]) -> bool:
        if event_type in {"tool_output", "tool_result", "tooloutput", "toolresult"}:
            return True
        return any(
            isinstance(event.get(key), dict)
            for key in ("tool_output", "toolOutput", "tool_result", "toolResult")
        )

    @staticmethod
    def _parse_json_object(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            if any(isinstance(entry, dict) for entry in value):
                return {"edits": value}
            return {}
        if not isinstance(value, str):
            return {}
        text = value.strip()
        if not text or text[0] not in "{[":
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list) and any(isinstance(entry, dict) for entry in parsed):
            return {"edits": parsed}
        return {}

    def _event_like_payload(self, event: dict[str, Any]) -> dict[str, Any]:
        for key in ("tool_call", "toolCall", "function_call", "functionCall", "tool", "function"):
            raw_value = event.get(key)
            if isinstance(raw_value, dict):
                return raw_value
        return event

    def _extract_tool_input(self, event: dict[str, Any], nested_event: dict[str, Any]) -> dict[str, Any]:
        candidates: list[Any] = [
            nested_event.get("args"),
            nested_event.get("arguments"),
            nested_event.get("input"),
            nested_event.get("parameters"),
            event.get("args"),
            event.get("arguments"),
            event.get("input"),
            event.get("parameters"),
        ]
        function_payload = nested_event.get("function")
        if isinstance(function_payload, dict):
            candidates.extend(
                [
                    function_payload.get("args"),
                    function_payload.get("arguments"),
                    function_payload.get("input"),
                    function_payload.get("parameters"),
                ]
            )

        for candidate in candidates:
            parsed = self._parse_json_object(candidate)
            if parsed:
                return parsed

        return {}

    @staticmethod
    def _clip_text(value: str, *, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[:limit]

    def _collect_edit_series(self, edits: Any, *, keys: tuple[str, ...]) -> str:
        if not isinstance(edits, list):
            return ""

        chunks: list[str] = []
        for entry in edits:
            if not isinstance(entry, dict):
                continue
            for key in keys:
                value = self._extract_text_payload(entry.get(key))
                if value:
                    chunks.append(value)
                    break

        if not chunks:
            return ""
        return "\n\n".join(chunks)

    def _parse_tool_payload(self, event: dict[str, Any]) -> dict[str, Any] | None:
        nested_event = self._event_like_payload(event)
        tool_input = self._extract_tool_input(event, nested_event)

        tool_name = self._coerce_text(
            nested_event.get("tool")
            or nested_event.get("tool_name")
            or nested_event.get("name")
            or nested_event.get("function_name")
            or (
                nested_event.get("function", {}).get("name")
                if isinstance(nested_event.get("function"), dict)
                else ""
            )
            or event.get("tool")
            or event.get("tool_name")
            or event.get("name")
            or event.get("function_name")
            or (
                event.get("function", {}).get("name")
                if isinstance(event.get("function"), dict)
                else event.get("function")
            )
        ) or "tool"

        payload: dict[str, Any] = {"name": tool_name}

        tool_use_id = self._coerce_text(
            nested_event.get("tool_use_id")
            or nested_event.get("toolUseId")
            or nested_event.get("call_id")
            or nested_event.get("callId")
            or nested_event.get("id")
            or event.get("tool_use_id")
            or event.get("toolUseId")
            or event.get("call_id")
            or event.get("callId")
            or event.get("id")
        )
        if tool_use_id:
            payload["toolUseId"] = tool_use_id

        command = self._coerce_text(
            tool_input.get("command")
            or tool_input.get("cmd")
            or nested_event.get("command")
            or nested_event.get("cmd")
            or event.get("command")
            or event.get("cmd")
        )
        if command:
            payload["command"] = command[:400]

        path = self._coerce_text(
            tool_input.get("path")
            or tool_input.get("file_path")
            or tool_input.get("file")
            or tool_input.get("target_file")
            or tool_input.get("target_path")
            or nested_event.get("path")
            or nested_event.get("file_path")
            or event.get("path")
            or event.get("file_path")
        )
        if path:
            payload["path"] = path

        description = self._extract_text_payload(
            nested_event.get("description")
            or event.get("description")
            or tool_input.get("description")
        )
        if description:
            payload["description"] = description[:400]

        normalized_tool = tool_name.strip().lower()
        old_text = ""
        new_text = ""
        content_text = ""

        def _pick_text(*values: Any) -> str:
            for value in values:
                text = self._extract_text_payload(value)
                if text:
                    return text
            return ""

        if normalized_tool in {"edit", "multiedit"}:
            old_text = _pick_text(
                tool_input.get("old_string"),
                tool_input.get("old_content"),
                tool_input.get("old"),
                nested_event.get("old_content"),
                nested_event.get("old"),
                event.get("old_content"),
                event.get("old"),
            )
            new_text = _pick_text(
                tool_input.get("new_string"),
                tool_input.get("new_content"),
                tool_input.get("new"),
                nested_event.get("new_content"),
                nested_event.get("new"),
                event.get("new_content"),
                event.get("new"),
            )
            if not old_text and not new_text:
                old_text = self._collect_edit_series(
                    tool_input.get("edits"),
                    keys=("old_string", "old_content", "old"),
                )
                new_text = self._collect_edit_series(
                    tool_input.get("edits"),
                    keys=("new_string", "new_content", "new"),
                )
        elif normalized_tool == "write":
            old_text = _pick_text(
                tool_input.get("old_content"),
                tool_input.get("old"),
                nested_event.get("old_content"),
                nested_event.get("old"),
                event.get("old_content"),
                event.get("old"),
            )
            new_text = _pick_text(
                tool_input.get("content"),
                tool_input.get("new_content"),
                tool_input.get("new"),
                nested_event.get("content"),
                nested_event.get("new_content"),
                nested_event.get("new"),
                event.get("content"),
                event.get("new_content"),
                event.get("new"),
            )
            content_text = new_text
        else:
            old_text = _pick_text(
                tool_input.get("old_content"),
                tool_input.get("old"),
                nested_event.get("old_content"),
                nested_event.get("old"),
                event.get("old_content"),
                event.get("old"),
            )
            new_text = _pick_text(
                tool_input.get("new_content"),
                tool_input.get("new"),
                nested_event.get("new_content"),
                nested_event.get("new"),
                event.get("new_content"),
                event.get("new"),
            )

        if old_text or new_text:
            clipped_old = self._clip_text(old_text, limit=12000)
            clipped_new = self._clip_text(new_text, limit=12000)
            payload["old"] = clipped_old
            payload["new"] = clipped_new
            payload["old_content"] = clipped_old
            payload["new_content"] = clipped_new

        if content_text:
            payload["content"] = self._clip_text(content_text, limit=12000)

        if tool_use_id:
            _remember_pending_tool(self._pending_tools, tool_use_id, payload)
        return payload if payload else None

    def _parse_tool_output_payload(self, event: dict[str, Any]) -> dict[str, Any] | None:
        nested_event = self._event_like_payload(event)
        tool_use_id = self._coerce_text(
            nested_event.get("tool_use_id")
            or nested_event.get("toolUseId")
            or nested_event.get("call_id")
            or nested_event.get("callId")
            or nested_event.get("id")
            or event.get("tool_use_id")
            or event.get("toolUseId")
            or event.get("call_id")
            or event.get("callId")
            or event.get("id")
        )
        pending_payload = self._pending_tools.pop(tool_use_id, {}) if tool_use_id else {}

        tool_name = self._coerce_text(
            nested_event.get("tool")
            or nested_event.get("tool_name")
            or nested_event.get("name")
            or event.get("tool")
            or event.get("tool_name")
            or event.get("name")
            or pending_payload.get("name")
            or "tool_result"
        )
        output = self._extract_text_payload(
            nested_event.get("output")
            or nested_event.get("result")
            or nested_event.get("content")
            or nested_event.get("message")
            or event.get("output")
            or event.get("result")
            or event.get("content")
            or event.get("message")
        )
        if not output:
            return None

        payload: dict[str, Any] = dict(pending_payload)
        payload["name"] = tool_name
        payload["output"] = output[:12000]
        if tool_use_id:
            payload["toolUseId"] = tool_use_id
        return payload

    def _build_common_flags(self, config: CliRunConfig) -> list[str]:
        argv: list[str] = []
        output_mode = str(config.output_format or "").strip().lower()
        if config.supports_output_format_flag and output_mode in {"text", "json", "stream-json"}:
            argv.extend(["--output-format", output_mode])

        model_value = _sanitize_cli_token(config.model) or "auto"
        if config.supports_reasoning_flag and model_value == "auto":
            model_value = self._model_alias_for_reasoning(config.reasoning_level)
        if config.supports_model_flag and model_value:
            argv.extend(["--model", model_value])

        if config.supports_permission_flag:
            argv.extend(["--approval-mode", self._approval_mode_for_permission(config.permission_mode)])
        return argv

    @staticmethod
    def _approval_mode_for_permission(permission_mode: str) -> str:
        normalized = str(permission_mode or "").strip().lower()
        if normalized in {"default", "ask"}:
            return "default"
        if normalized in {"auto", "auto_edit", "auto-edit"}:
            return "auto_edit"
        if normalized in {"plan"}:
            return "plan"
        if normalized in {"bypasspermissions", "bypass_permissions", "bypass-permissions", "yolo"}:
            return "yolo"
        return "default"

    @staticmethod
    def _model_alias_for_reasoning(reasoning_level: str) -> str:
        normalized = _sanitize_reasoning_level(reasoning_level)
        if normalized in {"high", "xhigh"}:
            return "pro"
        if normalized in {"low", "minimal"}:
            return "flash-lite"
        return "flash"

    @staticmethod
    def _coerce_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float, bool)):
            return str(value)
        return ""

    def _extract_text_payload(self, value: Any) -> str:
        chunks: list[str] = []

        def _collect(raw: Any) -> None:
            if raw is None:
                return
            if isinstance(raw, str):
                text = raw.strip()
                if text:
                    chunks.append(text)
                return
            if isinstance(raw, (int, float, bool)):
                chunks.append(str(raw))
                return
            if isinstance(raw, list):
                for item in raw:
                    _collect(item)
                return
            if not isinstance(raw, dict):
                return

            for key in (
                "text",
                "content",
                "result",
                "output",
                "message",
                "summary",
                "description",
                "value",
                "delta",
            ):
                if key in raw:
                    _collect(raw.get(key))

        _collect(value)
        if not chunks:
            return ""
        deduped: list[str] = []
        for chunk in chunks:
            if deduped and deduped[-1] == chunk:
                continue
            deduped.append(chunk)
        return "\n".join(deduped)

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


class CodexDialect:
    """Codex argv builder + JSONL parser based on verified local schema."""

    def build_argv(self, prompt: str, config: CliRunConfig) -> list[str]:
        argv = [config.binary_path, "exec"]
        argv.extend(
            self._build_exec_flags(
                config,
                include_color=True,
                include_cwd=True,
                include_sandbox=True,
            )
        )
        argv.append(prompt)
        return argv

    def build_resume_argv(self, session_id: str, prompt: str, config: CliRunConfig) -> list[str]:
        safe_session_id = _sanitize_session_id(session_id)
        if not safe_session_id:
            return self.build_argv(prompt, config)
        argv = [config.binary_path, "exec", "resume"]
        argv.extend(
            self._build_exec_flags(
                config,
                include_color=False,
                include_cwd=False,
                include_sandbox=False,
            )
        )
        argv.extend([safe_session_id, prompt])
        return argv

    def parse_line(self, line: str) -> list[ParsedEvent]:
        event = self._parse_json_line(line.strip())
        if event is None:
            return []

        return self._parse_codex_event(event)

    def _parse_codex_event(self, event: dict[str, Any]) -> list[ParsedEvent]:
        parsed_events: list[ParsedEvent] = []
        event_type = str(event.get("type") or "").strip().lower()

        if event_type == "stream_event":
            nested = event.get("event")
            if isinstance(nested, dict):
                return self._parse_codex_event(nested)

        if event_type == "thread.started":
            thread_id = self._coerce_event_value(event.get("thread_id") or event.get("id"))
            if thread_id:
                parsed_events.append(ParsedEvent(session_id=thread_id, raw_type=event_type))
            return parsed_events

        if event_type in {"thread.finished", "thread.ended"}:
            thread_id = self._coerce_event_value(event.get("thread_id") or event.get("id"))
            if thread_id:
                parsed_events.append(ParsedEvent(session_id=thread_id, raw_type=event_type))
            return parsed_events

        if event_type in {"item.started", "item.completed", "item.error", "item.failed"}:
            item = event.get("item")
            if not isinstance(item, dict):
                return parsed_events
            parsed_events.extend(self._parse_codex_item_payload(item, event_type))
            return parsed_events

        if event_type in {"assistant", "assistant_message", "agent_message", "message"}:
            parsed_events.extend(self._parse_codex_item_payload(event, event_type))
            return parsed_events

        item_payload = event.get("item")
        if isinstance(item_payload, dict):
            parsed_events.extend(self._parse_codex_item_payload(item_payload, event_type or "item"))
            if parsed_events:
                return parsed_events

            nested_item_text = self._extract_text_payload(item_payload)
            if nested_item_text:
                parsed_events.append(ParsedEvent(text=nested_item_text, raw_type=event_type or "event"))
                return parsed_events

        items_payload = event.get("items")
        if isinstance(items_payload, list):
            for item in items_payload:
                if not isinstance(item, dict):
                    continue
                parsed_events.extend(self._parse_codex_item_payload(item, event_type or "event"))

            if parsed_events:
                return parsed_events

        if event_type in {"turn.completed", "turn.error", "turn.failed", "turn.started", "result", "fatal", "error"}:
            usage = event.get("usage")
            if isinstance(usage, dict):
                usage_payload = {
                    "input_tokens": _coerce_int(usage.get("input_tokens") or 0),
                    "cached_input_tokens": _coerce_int(usage.get("cached_input_tokens") or 0),
                    "output_tokens": _coerce_int(usage.get("output_tokens") or 0),
                }
                parsed_events.append(ParsedEvent(usage=usage_payload, raw_type=event_type))

            raw_cost = event.get("total_cost_usd")
            if isinstance(raw_cost, (int, float)):
                if not parsed_events or not isinstance(parsed_events[-1].usage, dict):
                    parsed_events.append(
                        ParsedEvent(usage={"total_cost_usd": float(raw_cost)}, raw_type=event_type)
                    )
                else:
                    parsed_events[-1].usage["total_cost_usd"] = float(raw_cost)

            raw_result = self._extract_text_payload(
                event.get("result")
                or event.get("message")
                or event.get("output")
                or event.get("text")
                or event.get("content")
                or event.get("response")
            )
            if raw_result:
                is_error_event = event_type in {"error", "turn.error", "turn.failed", "fatal"}
                if is_error_event or bool(event.get("is_error")) and event_type not in {
                    "turn.completed",
                    "result",
                    "assistant",
                    "assistant_message",
                    "agent_message",
                }:
                    parsed_events.append(ParsedEvent(error=raw_result, raw_type=event_type))
                else:
                    parsed_events.append(ParsedEvent(text=raw_result, raw_type=event_type))

            if event_type in {"error", "turn.error", "turn.failed", "fatal"} and not raw_result:
                message = self._coerce_event_value(event.get("message") or event.get("error"))
                if message:
                    parsed_events.append(ParsedEvent(error=message, raw_type=event_type))
                else:
                    parsed_events.append(ParsedEvent(error="Codex returned an error event.", raw_type=event_type))

            return parsed_events

        for nested_key in ("payload", "data", "body", "details"):
            payload = event.get(nested_key)
            if isinstance(payload, dict):
                parsed_events.extend(self._parse_codex_event(payload))
                if parsed_events:
                    return parsed_events
            if isinstance(payload, list):
                for entry in payload:
                    if not isinstance(entry, dict):
                        continue
                    parsed_events.extend(self._parse_codex_event(entry))
                    if parsed_events:
                        return parsed_events

        message = self._extract_text_payload(event)
        if message:
            parsed_events.append(ParsedEvent(text=message, raw_type=event_type or "event"))

        return parsed_events

    def _parse_codex_item_payload(self, item: dict[str, Any], phase: str) -> list[ParsedEvent]:
        parsed_events: list[ParsedEvent] = []
        if not isinstance(item, dict):
            return parsed_events

        item_type = str(item.get("type") or "").strip().lower()

        if item_type in {"agent_message", "assistant", "assistant_message", "message"}:
            text = self._extract_text_payload(
                item.get("text")
                or item.get("content")
                or item.get("message")
                or item.get("delta")
            )
            if text:
                parsed_events.append(ParsedEvent(text=text, raw_type=phase))
            return parsed_events

        if item_type in {"command_execution", "command"}:
            command_payload: dict[str, Any] = {
                "type": item_type,
                "id": item.get("id"),
                "command": self._coerce_event_value(item.get("command") or item.get("command_text")),
                "output": self._coerce_event_value(
                    item.get("aggregated_output") or item.get("stdout") or item.get("output") or item.get("result")
                ),
                "exit_code": item.get("exit_code"),
                "status": item.get("status"),
                "phase": "started" if phase == "item.started" else "completed",
            }
            parsed_events.append(ParsedEvent(tool=command_payload, raw_type=phase))
            return parsed_events

        if item_type == "file_change":
            normalized_phase = phase
            if phase == "item.started":
                normalized_phase = "started"
            elif phase == "item.completed":
                normalized_phase = "completed"

            changes: list[dict[str, str]] = []
            raw_changes = item.get("changes")
            if isinstance(raw_changes, list):
                for entry in raw_changes:
                    if not isinstance(entry, dict):
                        continue
                    path = self._coerce_event_value(
                        entry.get("path")
                        or entry.get("file_path")
                        or entry.get("file")
                        or entry.get("target")
                    )
                    if not path:
                        continue
                    kind = self._coerce_event_value(
                        entry.get("kind")
                        or entry.get("change_type")
                        or entry.get("change")
                        or entry.get("type")
                    ).lower()
                    change_entry: dict[str, str] = {"path": path}
                    if kind:
                        change_entry["kind"] = kind
                    changes.append(change_entry)

            file_change_payload: dict[str, Any] = {
                "type": "file_change",
                "name": "file_change",
                "id": self._coerce_event_value(item.get("id")),
                "status": self._coerce_event_value(item.get("status")),
                "phase": normalized_phase,
                "changes": changes,
            }
            parsed_events.append(ParsedEvent(tool=file_change_payload, raw_type=phase))
            return parsed_events

        if item_type == "tool_result":
            output = self._coerce_event_value(item.get("output") or item.get("result") or item.get("text"))
            if output:
                tool_payload: dict[str, Any] = {
                    "type": "tool_result",
                    "toolUseId": self._coerce_event_value(item.get("tool_use_id") or item.get("toolUseId") or item.get("id")),
                    "output": output,
                }
                parsed_events.append(ParsedEvent(tool=tool_payload, raw_type=phase))
            return parsed_events

        fallback_text = self._extract_text_payload(item)
        if fallback_text:
            parsed_events.append(ParsedEvent(text=fallback_text, raw_type=phase))
        return parsed_events

    @staticmethod
    def _coerce_event_value(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            stripped = value.strip()
            return stripped
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            for candidate in value:
                found = CodexDialect._coerce_event_value(candidate)
                if found:
                    return found
            return ""
        if isinstance(value, dict):
            for key in ("text", "content", "result", "output", "message", "summary", "delta"):
                found = CodexDialect._coerce_event_value(value.get(key))
                if found:
                    return found
        return ""

    def _extract_text_payload(self, value: Any) -> str:
        chunks: list[str] = []

        def _collect(value_inner: Any) -> None:
            if isinstance(value_inner, str):
                text = value_inner.strip()
                if text:
                    chunks.append(text)
                return

            if isinstance(value_inner, list):
                for item in value_inner:
                    _collect(item)
                return

            if not isinstance(value_inner, dict):
                return

            for key in (
                "text",
                "content",
                "output",
                "result",
                "message",
                "summary",
                "reasoning",
                "response",
                "delta",
            ):
                if key in value_inner:
                    _collect(value_inner.get(key))
                    if chunks:
                        return

        _collect(value)
        if not chunks:
            return ""

        deduped: list[str] = []
        for chunk in chunks:
            if deduped and deduped[-1] == chunk:
                continue
            deduped.append(chunk)

        return "".join(deduped)

    def _build_exec_flags(
        self,
        config: CliRunConfig,
        *,
        include_color: bool,
        include_cwd: bool,
        include_sandbox: bool,
    ) -> list[str]:
        argv: list[str] = []
        output_format = str(config.output_format or "").strip().lower()
        if output_format in {"stream-json", "json"}:
            argv.append("--json")

        if include_color and config.disable_color:
            argv.extend(["--color", "never"])

        model_value = _sanitize_cli_token(config.model)
        if model_value:
            argv.extend(["-m", model_value])

        permission_flags = self._permission_flags(
            config.permission_mode,
            include_sandbox=include_sandbox,
        )
        argv.extend(permission_flags)

        if config.supports_reasoning_flag:
            argv.extend(["-c", f"model_reasoning_effort={_sanitize_reasoning_level(config.reasoning_level)}"])

        safe_cwd = _sanitize_path_arg(config.cwd)
        if include_cwd and safe_cwd:
            argv.extend(["-C", safe_cwd])

        if include_cwd and safe_cwd:
            argv.append("--skip-git-repo-check")

        return argv

    @staticmethod
    def _permission_flags(permission_mode: str, *, include_sandbox: bool) -> list[str]:
        normalized = str(permission_mode or "").strip().lower()

        if normalized == "auto":
            return ["--full-auto"]
        if normalized == "ask":
            return []
        if normalized in {"bypasspermissions", "bypass_permissions", "bypass-permissions"}:
            return ["--dangerously-bypass-approvals-and-sandbox"]
        if normalized == "plan":
            return ["--sandbox", "read-only"] if include_sandbox else []
        if normalized in {"read-only", "workspace-write", "danger-full-access"}:
            return ["--sandbox", normalized] if include_sandbox else []
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
