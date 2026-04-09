"""Threaded CLI runner and stream parser for Claude Code, independent of GTK window."""

from __future__ import annotations

import json
import subprocess
import threading
from typing import Any, Callable

from gi.repository import GLib

from claude_code_gui.domain.claude_types import ClaudeRunConfig, ClaudeRunResult


class ClaudeProcess:
    """Runs Claude CLI non-interactively and emits parsed events back to GTK main thread."""

    def __init__(
        self,
        on_running_changed: Callable[[str, bool], None],
        on_assistant_chunk: Callable[[str, str], None],
        on_system_message: Callable[[str, str], None],
        on_permission_request: Callable[[str, dict[str, Any]], None],
        on_complete: Callable[[str, ClaudeRunResult], None],
    ) -> None:
        self._on_running_changed = on_running_changed
        self._on_assistant_chunk = on_assistant_chunk
        self._on_system_message = on_system_message
        self._on_permission_request = on_permission_request
        self._on_complete = on_complete

        self._lock = threading.Lock()
        self._running = False
        self._stop_requested = False
        self._process: subprocess.Popen[str] | None = None
        self._permission_counter = 0

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def stop(self) -> None:
        with self._lock:
            self._stop_requested = True
            process = self._process

        if process is None:
            return

        if process.poll() is None:
            try:
                process.terminate()
            except OSError:
                return

    def send_permission_response(self, *, action: str, comment: str = "", request_id: str = "") -> bool:
        normalized_action = str(action or "").strip().lower()
        payload = ""

        if normalized_action == "allow":
            payload = "y\n"
        elif normalized_action == "deny":
            payload = "n\n"
        elif normalized_action == "comment":
            text = str(comment or "").strip()
            if not text:
                return False
            payload = f"{text}\n"
        else:
            return False

        with self._lock:
            process = self._process
            running = self._running and not self._stop_requested

        if not running or process is None or process.stdin is None or process.poll() is not None:
            return False

        try:
            process.stdin.write(payload)
            process.stdin.flush()
        except OSError:
            return False

        _ = request_id
        return True

    def send_message(self, *, request_token: str, config: ClaudeRunConfig) -> bool:
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._stop_requested = False

        worker = threading.Thread(
            target=self._run,
            args=(request_token, config),
            daemon=True,
        )
        worker.start()
        return True

    def _run(self, request_token: str, config: ClaudeRunConfig) -> None:
        self._emit_running_changed(request_token, True)

        modes: list[str] = []
        if config.supports_output_format_flag:
            if config.supports_stream_json:
                modes.append("stream-json")
            if config.supports_json:
                modes.append("json")
        modes.append("text")

        final_result = ClaudeRunResult(
            success=False,
            assistant_text="",
            streamed_assistant=False,
            conversation_id=config.conversation_id,
            error_message="Claude CLI execution failed.",
        )

        try:
            for index, mode in enumerate(modes):
                if index > 0:
                    label = "JSON" if mode == "json" else "Plain text"
                    self._emit_system_message(request_token, f"Falling back to {label} output mode.")

                result, unsupported_output = self._run_single_attempt(
                    request_token=request_token,
                    config=config,
                    mode=mode,
                )

                final_result = result
                if unsupported_output and index < len(modes) - 1:
                    continue
                break
        finally:
            with self._lock:
                self._running = False
                self._process = None
                was_stopped = self._stop_requested

            if was_stopped and not final_result.success and not final_result.error_message:
                final_result.error_message = "Request stopped"

            self._emit_running_changed(request_token, False)
            self._emit_complete(request_token, final_result)

    def _run_single_attempt(
        self,
        *,
        request_token: str,
        config: ClaudeRunConfig,
        mode: str,
    ) -> tuple[ClaudeRunResult, bool]:
        argv = [config.binary_path, "-p", config.message]

        if mode in {"stream-json", "json"}:
            argv.extend(["--output-format", mode])

        if mode == "stream-json" and config.stream_json_requires_verbose:
            argv.append("--verbose")

        if config.supports_model_flag:
            argv.extend(["--model", config.model])

        if config.supports_permission_flag:
            argv.extend(["--permission-mode", config.permission_mode])

        if config.supports_reasoning_flag and config.reasoning_level:
            argv.extend(["--effort", config.reasoning_level])

        if config.conversation_id:
            argv.extend(["--resume", config.conversation_id])

        try:
            process = subprocess.Popen(
                argv,
                cwd=config.cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as error:
            return (
                ClaudeRunResult(
                    success=False,
                    assistant_text="",
                    streamed_assistant=False,
                    conversation_id=config.conversation_id,
                    error_message=f"Could not start Claude CLI: {error}",
                ),
                False,
            )

        with self._lock:
            self._process = process

        assistant_parts: list[str] = []
        streamed_assistant = False
        detected_conversation_id = config.conversation_id
        result_text: str | None = None
        error_messages: list[str] = []
        captured_output: list[str] = []
        parsed_json = False
        cost_usd = 0.0
        input_tokens = 0
        output_tokens = 0

        stdout = process.stdout
        if stdout is not None:
            for raw_line in stdout:
                if raw_line is None:
                    continue

                line = raw_line.rstrip("\n")
                stripped = line.strip()
                if stripped:
                    captured_output.append(stripped)
                    if len(captured_output) > 120:
                        captured_output = captured_output[-120:]

                with self._lock:
                    if self._stop_requested:
                        break

                if mode == "stream-json":
                    event = self._parse_json_line(stripped)
                    if event is None:
                        continue
                    parsed_json = True
                    event_type = str(event.get("type") or "")

                    if event_type == "assistant":
                        texts, tools, permission_requests = self._extract_assistant_content(
                            event.get("message"),
                            request_token=request_token,
                        )
                        for permission_request in permission_requests:
                            self._emit_permission_request(request_token, permission_request)
                        for tool_message in tools:
                            self._emit_system_message(request_token, tool_message)
                        for text_chunk in texts:
                            assistant_parts.append(text_chunk)
                            streamed_assistant = True
                            self._emit_assistant_chunk(request_token, text_chunk)
                        continue

                    if event_type == "tool_use":
                        tool_data = self._extract_tool_data(event)
                        permission_request = self._extract_permission_request(
                            event,
                            request_token=request_token,
                            fallback_tool_data=tool_data,
                        )
                        if permission_request is not None:
                            self._emit_permission_request(request_token, permission_request)
                            continue
                        if tool_data is not None:
                            self._emit_system_message(
                                request_token,
                                json.dumps(tool_data, ensure_ascii=False),
                            )
                        continue

                    permission_request = self._extract_permission_request(
                        event,
                        request_token=request_token,
                        fallback_tool_data=None,
                    )
                    if permission_request is not None:
                        self._emit_permission_request(request_token, permission_request)
                        continue

                    if event_type == "result":
                        raw_conversation_id = event.get("conversation_id") or event.get("session_id")
                        if isinstance(raw_conversation_id, str) and raw_conversation_id.strip():
                            detected_conversation_id = raw_conversation_id.strip()

                        raw_result = event.get("result")
                        if isinstance(raw_result, str):
                            result_text = raw_result

                        raw_cost = event.get("total_cost_usd")
                        if isinstance(raw_cost, (int, float)):
                            cost_usd = float(raw_cost)
                        usage = event.get("usage")
                        if isinstance(usage, dict):
                            input_tokens = int(usage.get("input_tokens") or 0)
                            output_tokens = int(usage.get("output_tokens") or 0)

                        if bool(event.get("is_error")):
                            if isinstance(raw_result, str) and raw_result.strip():
                                error_messages.append(raw_result.strip())
                            else:
                                error_messages.append("Claude returned an error result.")
                        continue

                    if event_type == "error":
                        message_text = event.get("error") or event.get("message")
                        if isinstance(message_text, str) and message_text.strip():
                            error_messages.append(message_text.strip())
                        continue

                    if event_type == "system":
                        subtype = str(event.get("subtype") or "")
                        if subtype in {"error", "warning"}:
                            raw_message = event.get("message") or event.get("output")
                            if isinstance(raw_message, str) and raw_message.strip():
                                self._emit_system_message(request_token, raw_message.strip())
                        continue

                elif mode == "json":
                    event = self._parse_json_line(stripped)
                    if event is None:
                        continue
                    parsed_json = True

                    raw_conversation_id = event.get("conversation_id") or event.get("session_id")
                    if isinstance(raw_conversation_id, str) and raw_conversation_id.strip():
                        detected_conversation_id = raw_conversation_id.strip()

                    raw_result = event.get("result")
                    if isinstance(raw_result, str):
                        result_text = raw_result

                    if bool(event.get("is_error")):
                        if isinstance(raw_result, str) and raw_result.strip():
                            error_messages.append(raw_result.strip())
                        else:
                            error_messages.append("Claude returned an error result.")

                else:
                    if line:
                        assistant_parts.append(line + "\n")
                        streamed_assistant = True
                        self._emit_assistant_chunk(request_token, line + "\n")

        return_code = process.wait()

        unsupported_output = False
        if mode in {"stream-json", "json"}:
            combined = "\n".join(captured_output).lower()
            unsupported_output = (
                "output-format" in combined
                and (
                    "unknown option" in combined
                    or "invalid value" in combined
                    or "requires --verbose" in combined
                    or "only works with --print" in combined
                    or "must be one of" in combined
                )
            )
            if mode == "stream-json" and not parsed_json and return_code != 0:
                unsupported_output = unsupported_output or "error" in combined

        assistant_text = "".join(assistant_parts)
        if not assistant_text.strip() and isinstance(result_text, str) and result_text.strip():
            assistant_text = result_text
            streamed_assistant = True
            self._emit_assistant_chunk(request_token, result_text)

        error_message: str | None = None
        if error_messages:
            error_message = error_messages[-1]
        elif return_code != 0:
            output_hint = captured_output[-1] if captured_output else "Claude exited with an error."
            error_message = output_hint

        success = return_code == 0 and not error_messages

        return (
            ClaudeRunResult(
                success=success,
                assistant_text=assistant_text,
                streamed_assistant=streamed_assistant,
                conversation_id=detected_conversation_id,
                error_message=error_message,
                cost_usd=cost_usd,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
            unsupported_output,
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

    def _extract_assistant_content(
        self,
        message: Any,
        *,
        request_token: str,
    ) -> tuple[list[str], list[str], list[dict[str, Any]]]:
        texts: list[str] = []
        tools: list[str] = []
        permission_requests: list[dict[str, Any]] = []

        if not isinstance(message, dict):
            return texts, tools, permission_requests

        content = message.get("content")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                block_type = str(block.get("type") or "")

                if block_type == "text":
                    chunk = block.get("text")
                    if isinstance(chunk, str) and chunk:
                        texts.append(chunk)
                    continue

                if block_type == "tool_use":
                    tool_data = self._extract_tool_data(block)
                    if tool_data is None:
                        continue
                    permission_request = self._extract_permission_request(
                        block,
                        request_token=request_token,
                        fallback_tool_data=tool_data,
                    )
                    if permission_request is not None:
                        permission_requests.append(permission_request)
                    else:
                        tools.append(json.dumps(tool_data, ensure_ascii=False))
                    continue

            return texts, tools, permission_requests

        if isinstance(content, str) and content:
            texts.append(content)

        return texts, tools, permission_requests

    def _extract_tool_data(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        tool_name = str(
            payload.get("name")
            or payload.get("tool_name")
            or (
                payload.get("tool", {}).get("name")
                if isinstance(payload.get("tool"), dict)
                else ""
            )
            or "tool"
        )
        tool_input = payload.get("input")
        if not isinstance(tool_input, dict):
            tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            tool_input = {}

        tool_data: dict[str, Any] = {"__tool__": True, "name": tool_name}

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
            tool_data["description"] = description.strip()[:400]

        if tool_name in ("Edit", "edit", "MultiEdit", "multiedit"):
            old_s = str(tool_input.get("old_string") or "")
            new_s = str(tool_input.get("new_string") or "")
            if old_s or new_s:
                tool_data["old"] = old_s[:800]
                tool_data["new"] = new_s[:800]
        elif tool_name in ("Write", "write"):
            content = str(tool_input.get("content") or "")
            if content:
                tool_data["content"] = content[:600]
        elif tool_name in ("Bash", "bash"):
            cmd = str(tool_input.get("command") or payload.get("command") or "")
            if cmd:
                tool_data["command"] = cmd[:400]
        else:
            cmd = str(tool_input.get("command") or payload.get("command") or "")
            if cmd:
                tool_data["command"] = cmd[:400]

        return tool_data

    def _extract_permission_request(
        self,
        payload: dict[str, Any],
        *,
        request_token: str,
        fallback_tool_data: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not self._requires_permission(payload):
            return None

        tool_data = fallback_tool_data or self._extract_tool_data(payload)
        if tool_data is None:
            return None

        request_id = str(
            payload.get("request_id")
            or payload.get("permission_request_id")
            or payload.get("id")
            or ""
        ).strip()
        if not request_id:
            request_id = self._next_permission_request_id(request_token)

        description = self._permission_description(payload, tool_data)
        proposed_action = self._permission_action(payload, tool_data)

        permission_data: dict[str, Any] = {
            "__permission_request__": True,
            "requestId": request_id,
            "name": tool_data.get("name") or "tool",
            "description": description,
            "proposedAction": proposed_action,
        }

        for key in ("path", "command", "old", "new", "content"):
            value = tool_data.get(key)
            if value:
                permission_data[key] = value

        return permission_data

    @staticmethod
    def _requires_permission(payload: dict[str, Any]) -> bool:
        truthy_fields = (
            "requires_permission",
            "requires_approval",
            "requires_confirmation",
            "permission_required",
            "approval_required",
            "awaiting_approval",
            "needs_confirmation",
        )
        for field in truthy_fields:
            value = payload.get(field)
            if value is True:
                return True
            if isinstance(value, str) and value.strip().lower() in {"true", "yes", "1", "required"}:
                return True

        status = str(payload.get("status") or payload.get("state") or "").strip().lower()
        if status in {
            "pending_approval",
            "requires_approval",
            "awaiting_approval",
            "awaiting_confirmation",
            "requires_permission",
            "permission_required",
            "pending_permission",
        }:
            return True

        event_type = str(payload.get("type") or "").strip().lower()
        subtype = str(payload.get("subtype") or "").strip().lower()
        if event_type in {"permission_request", "approval_request"}:
            return True
        if event_type in {"system", "input"} and subtype in {"permission_request", "approval_request"}:
            return True

        return False

    @staticmethod
    def _permission_description(payload: dict[str, Any], tool_data: dict[str, Any]) -> str:
        for key in ("description", "prompt", "message"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:400]

        tool_name = str(tool_data.get("name") or "tool").strip().lower()
        if tool_name == "bash":
            return "Claude wants to execute a shell command."
        if tool_name in {"edit", "multiedit", "write"}:
            return "Claude wants to modify project files."
        return "Claude requests approval before running this tool."

    @staticmethod
    def _permission_action(payload: dict[str, Any], tool_data: dict[str, Any]) -> str:
        explicit = payload.get("proposed_action") or payload.get("action")
        if isinstance(explicit, str) and explicit.strip():
            return explicit.strip()[:400]

        command = tool_data.get("command")
        if isinstance(command, str) and command.strip():
            return f"Run command: {command.strip()[:240]}"

        path = tool_data.get("path")
        if isinstance(path, str) and path.strip():
            return f"Access path: {path.strip()}"

        name = str(tool_data.get("name") or "tool").strip()
        return f"Run tool: {name}"

    def _next_permission_request_id(self, request_token: str) -> str:
        with self._lock:
            self._permission_counter += 1
            next_value = self._permission_counter
        return f"{request_token}-permission-{next_value}"

    def _emit_running_changed(self, request_token: str, running: bool) -> None:
        GLib.idle_add(self._on_running_changed, request_token, running)

    def _emit_assistant_chunk(self, request_token: str, chunk: str) -> None:
        GLib.idle_add(self._on_assistant_chunk, request_token, chunk)

    def _emit_system_message(self, request_token: str, message: str) -> None:
        GLib.idle_add(self._on_system_message, request_token, message)

    def _emit_permission_request(self, request_token: str, payload: dict[str, Any]) -> None:
        GLib.idle_add(self._on_permission_request, request_token, payload)

    def _emit_complete(self, request_token: str, result: ClaudeRunResult) -> None:
        GLib.idle_add(self._on_complete, request_token, result)
