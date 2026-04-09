"""Threaded CLI runner and stream parser for Claude Code, independent of GTK window."""

from __future__ import annotations

import json
import re
import shlex
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
        pending_shell_tools: dict[str, dict[str, Any]] = {}

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
                            parsed_tool = self._parse_json_line(tool_message)
                            if parsed_tool is not None:
                                tool_use_id = str(parsed_tool.get("toolUseId") or "").strip()
                                if tool_use_id:
                                    pending_shell_tools[tool_use_id] = dict(parsed_tool)
                            self._emit_system_message(request_token, tool_message)
                        for text_chunk in texts:
                            assistant_parts.append(text_chunk)
                            streamed_assistant = True
                            self._emit_assistant_chunk(request_token, text_chunk)
                        continue

                    if event_type == "user":
                        for tool_result_entry in self._extract_tool_result_entries(event.get("message")):
                            merged_tool = self._merge_tool_result_with_tool_use(
                                tool_result_entry,
                                pending_shell_tools,
                            )
                            if merged_tool is None:
                                continue
                            self._emit_system_message(
                                request_token,
                                json.dumps(merged_tool, ensure_ascii=False),
                            )
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
                            tool_use_id = str(tool_data.get("toolUseId") or "").strip()
                            if tool_use_id:
                                pending_shell_tools[tool_use_id] = dict(tool_data)
                            self._emit_system_message(
                                request_token,
                                json.dumps(tool_data, ensure_ascii=False),
                            )
                        continue

                    if event_type == "tool_result":
                        merged_tool = self._merge_tool_result_with_tool_use(
                            {
                                "toolUseId": event.get("tool_use_id") or event.get("toolUseId") or event.get("id"),
                                "output": self._coerce_text(
                                    event.get("content")
                                    or event.get("output")
                                    or event.get("result")
                                ),
                            },
                            pending_shell_tools,
                        )
                        if merged_tool is not None:
                            self._emit_system_message(
                                request_token,
                                json.dumps(merged_tool, ensure_ascii=False),
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

        self._attach_cipr_metadata(tool_data)
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
            chunks = [
                self._coerce_text(item, depth=depth + 1).strip()
                for item in value
            ]
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
            output = self._coerce_text(
                block.get("content")
                or block.get("output")
                or block.get("result")
            ).strip()
            if not output:
                continue
            entries.append(
                {
                    "toolUseId": block.get("tool_use_id") or block.get("toolUseId") or block.get("id"),
                    "output": output,
                }
            )
        return entries

    def _merge_tool_result_with_tool_use(
        self,
        entry: dict[str, Any],
        pending_shell_tools: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        tool_use_id = str(entry.get("toolUseId") or "").strip()
        output_text = self._coerce_text(entry.get("output")).strip()
        if not output_text:
            return None

        base_tool = pending_shell_tools.get(tool_use_id) if tool_use_id else None
        merged: dict[str, Any]
        if base_tool:
            merged = dict(base_tool)
        else:
            merged = {"__tool__": True, "name": "tool_result"}
            if tool_use_id:
                merged["toolUseId"] = tool_use_id

        merged["output"] = self._clip_text(output_text, limit=12000)
        self._attach_cipr_metadata(merged)

        has_cipr = bool(merged.get("git_event") or merged.get("pr_event") or merged.get("ci_event"))
        if not base_tool and not has_cipr:
            return None

        if tool_use_id and base_tool:
            pending_shell_tools.pop(tool_use_id, None)
        return merged

    @staticmethod
    def _is_shell_tool_name(tool_name: str) -> bool:
        normalized = str(tool_name or "").strip().lower()
        return "bash" in normalized or "execute" in normalized

    @staticmethod
    def _extract_flag_value(command: str, flag: str) -> str:
        raw_command = str(command or "").strip()
        if not raw_command:
            return ""
        try:
            tokens = shlex.split(raw_command)
        except ValueError:
            tokens = raw_command.split()
        if not tokens:
            return ""

        prefix = flag + "="
        for index, token in enumerate(tokens):
            if token == flag and index + 1 < len(tokens):
                return tokens[index + 1]
            if token.startswith(prefix):
                return token[len(prefix):]
        return ""

    @staticmethod
    def _extract_first_match(pattern: str, text: str, *, flags: int = 0, group: int = 0) -> str:
        if not text:
            return ""
        match = re.search(pattern, text, flags)
        if not match:
            return ""
        value = match.group(group)
        return str(value or "").strip()

    def _attach_cipr_metadata(self, tool_data: dict[str, Any]) -> None:
        if not self._is_shell_tool_name(str(tool_data.get("name") or "")):
            return

        command = str(tool_data.get("command") or "").strip()
        output = str(tool_data.get("output") or "").strip()

        git_event = self._detect_git_event(command=command, output=output)
        if git_event:
            tool_data["git_event"] = git_event

        pr_event = self._detect_pr_event(command=command, output=output, git_event=git_event)
        if pr_event:
            tool_data["pr_event"] = pr_event

        ci_event = self._detect_ci_event(command=command, output=output, pr_event=pr_event)
        if ci_event:
            tool_data["ci_event"] = ci_event

    def _detect_git_event(self, *, command: str, output: str) -> dict[str, Any] | None:
        normalized_command = command.lower()
        if not normalized_command:
            return None

        if re.search(r"\bgit\s+commit\b", normalized_command):
            hash_value = self._extract_first_match(r"\b([0-9a-f]{7,40})\b", output, flags=re.IGNORECASE, group=1)
            message_value = self._extract_first_match(r"\[[^\]]+\]\s+(.+)", output, group=1)
            if not message_value:
                message_value = self._extract_flag_value(command, "-m")
            files_changed_raw = self._extract_first_match(
                r"(\d+)\s+files?\s+changed",
                output,
                flags=re.IGNORECASE,
                group=1,
            )
            event: dict[str, Any] = {"operation": "commit"}
            if hash_value:
                event["hash"] = hash_value
            if message_value:
                event["message"] = message_value[:240]
            if files_changed_raw.isdigit():
                event["filesChanged"] = int(files_changed_raw)
            return event

        if re.search(r"\bgit\s+push\b", normalized_command):
            remote = "origin"
            branch = ""
            commit_count_raw = self._extract_first_match(
                r"(\d+)\s+commits?",
                output,
                flags=re.IGNORECASE,
                group=1,
            )
            try:
                tokens = shlex.split(command)
            except ValueError:
                tokens = command.split()
            push_index = -1
            for index, token in enumerate(tokens):
                if token == "push" and index > 0 and tokens[index - 1] == "git":
                    push_index = index
                    break
            if push_index >= 0:
                args = tokens[push_index + 1:]
                filtered = [arg for arg in args if not arg.startswith("-")]
                if filtered:
                    remote = filtered[0]
                if len(filtered) > 1:
                    branch = filtered[1]
            if branch.startswith("HEAD:"):
                branch = branch.split(":", 1)[1]
            if not branch:
                branch = self._extract_first_match(r"->\s*([A-Za-z0-9._/-]+)", output, group=1)

            event = {
                "operation": "push",
                "remote": remote or "origin",
            }
            if branch:
                event["branch"] = branch
            if commit_count_raw.isdigit():
                event["commitCount"] = int(commit_count_raw)
            return event

        checkout_match = re.search(
            r"\bgit\s+(?:checkout\s+-b|switch\s+-c)\s+([^\s]+)(?:\s+([^\s]+))?",
            command,
            flags=re.IGNORECASE,
        )
        if not checkout_match:
            checkout_match = re.search(
                r"\bgit\s+branch\s+([^\s-][^\s]*)(?:\s+([^\s]+))?",
                command,
                flags=re.IGNORECASE,
            )
        if checkout_match:
            branch_name = str(checkout_match.group(1) or "").strip()
            base_name = str(checkout_match.group(2) or "").strip()
            if branch_name:
                event = {
                    "operation": "branch",
                    "branch": branch_name,
                }
                if base_name:
                    event["createdFrom"] = base_name
                return event

        return None

    def _detect_pr_event(
        self,
        *,
        command: str,
        output: str,
        git_event: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        normalized_command = command.lower()
        combined_text = "\n".join(part for part in (command, output) if part)
        pr_url = self._extract_first_match(r"https?://[^\s)]+/pull/\d+", combined_text, flags=re.IGNORECASE)
        if "gh pr create" not in normalized_command and not pr_url:
            return None

        pr_number = self._extract_first_match(r"/pull/(\d+)", pr_url, group=1) if pr_url else ""
        title = self._extract_flag_value(command, "--title")
        if not title and pr_number:
            title = f"PR #{pr_number}"
        if not title:
            title = "Pull Request"

        source_branch = self._extract_flag_value(command, "--head")
        if not source_branch and git_event and str(git_event.get("operation")) == "push":
            source_branch = str(git_event.get("branch") or "").strip()
        target_branch = self._extract_flag_value(command, "--base")

        lower_output = output.lower()
        status = "open"
        if "merged" in lower_output:
            status = "merged"
        elif "closed" in lower_output:
            status = "closed"

        file_summary = ""
        changed_raw = self._extract_first_match(
            r"(\d+)\s+files?\s+changed",
            output,
            flags=re.IGNORECASE,
            group=1,
        )
        insertions_raw = self._extract_first_match(
            r"(\d+)\s+insertions?\(\+\)",
            output,
            flags=re.IGNORECASE,
            group=1,
        )
        deletions_raw = self._extract_first_match(
            r"(\d+)\s+deletions?\(-\)",
            output,
            flags=re.IGNORECASE,
            group=1,
        )
        if changed_raw.isdigit():
            changed_count = int(changed_raw)
            file_summary = f"{changed_count} file{'s' if changed_count != 1 else ''} changed"
            if insertions_raw.isdigit() or deletions_raw.isdigit():
                file_summary += (
                    f" (+{int(insertions_raw or '0')}/-{int(deletions_raw or '0')})"
                )

        event: dict[str, Any] = {
            "title": title[:300],
            "status": status,
        }
        if pr_number:
            event["number"] = pr_number
        if pr_url:
            event["url"] = pr_url
        if source_branch:
            event["sourceBranch"] = source_branch
        if target_branch:
            event["targetBranch"] = target_branch
        if file_summary:
            event["fileSummary"] = file_summary
        return event

    def _detect_ci_event(
        self,
        *,
        command: str,
        output: str,
        pr_event: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        lower_command = command.lower()
        lower_output = output.lower()
        explicit_ci_command = any(
            marker in lower_command
            for marker in (
                "gh pr checks",
                "gh run",
                "github actions",
                "workflow",
                "pipeline",
                "buildkite",
                "jenkins",
                "circleci",
            )
        )

        status = ""
        if any(token in lower_output for token in ("failing", "failed", "failure", "error", "❌")):
            status = "failing"
        elif any(token in lower_output for token in ("passing", "passed", "success", "successful", "✅")):
            status = "passing"
        elif any(token in lower_output for token in ("pending", "queued", "in progress", "running", "⏳")):
            status = "pending"
        elif explicit_ci_command:
            status = "pending"

        ci_url = self._extract_first_match(
            r"https?://[^\s)]+(?:/actions/runs/\d+|/runs/\d+|/pipelines/[^\s)]+)",
            output,
            flags=re.IGNORECASE,
        )
        if not ci_url:
            ci_url = self._extract_first_match(
                r"https?://[^\s)]+(?:actions/runs/\d+|runs/\d+|pipelines/[^\s)]+)",
                command,
                flags=re.IGNORECASE,
            )

        has_ci_signal = explicit_ci_command or bool(ci_url) or bool(status)
        if not has_ci_signal or not status:
            return None

        pipeline = self._extract_first_match(
            r"(?:workflow|pipeline)\s*[:=]\s*([^\n\r]+)",
            output,
            flags=re.IGNORECASE,
            group=1,
        )
        if not pipeline:
            pipeline = self._extract_first_match(
                r"^([^\n\r]+?)\s+\.\.\.\s+(?:pass|fail|pending|queued|running)",
                output,
                flags=re.IGNORECASE | re.MULTILINE,
                group=1,
            )

        duration = self._extract_first_match(
            r"\b(\d+m\d+s|\d+\.\d+s|\d+\s*(?:ms|s|sec|secs|seconds|min|mins|minutes|hr|hrs|hours))\b",
            output,
            flags=re.IGNORECASE,
            group=1,
        )

        event: dict[str, Any] = {"status": status}
        if pipeline:
            event["pipeline"] = pipeline[:200]
        if duration:
            event["duration"] = duration
        if ci_url:
            event["url"] = ci_url

        if pr_event and pr_event.get("url"):
            event["prUrl"] = pr_event.get("url")
        elif output:
            linked_pr_url = self._extract_first_match(r"https?://[^\s)]+/pull/\d+", output, flags=re.IGNORECASE)
            if linked_pr_url:
                event["prUrl"] = linked_pr_url

        if status == "failing":
            event["suggestFix"] = True
        return event

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

        for key in ("path", "command", "old", "new", "old_content", "new_content", "content"):
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
