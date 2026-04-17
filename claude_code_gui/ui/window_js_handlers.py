"""JavaScript bridge handlers extracted from the main window module."""

from __future__ import annotations

import ast
import json
import logging
import os
import threading
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_code_gui.app.constants import (
    CONNECTION_STARTING,
    SESSION_STATUS_ACTIVE,
    SESSION_STATUS_ERROR,
    STATUS_ERROR,
    STATUS_INFO,
    STATUS_MUTED,
    STATUS_WARNING,
)
from claude_code_gui.core.time_utils import current_timestamp
from claude_code_gui.domain.claude_types import ClaudeRunConfig
from claude_code_gui.gi_runtime import GLib, GTK4, Gio, Gtk
from claude_code_gui.services.attachment_service import (
    cleanup_temp_paths,
    compose_message_with_attachments,
    encode_host_attachment_payloads,
    materialize_attachments,
    parse_send_payload,
)
from claude_code_gui.services.binary_probe import get_cached_codex_authentication

if TYPE_CHECKING:
    from claude_code_gui.ui.window import ClaudeCodeWindow


logger = logging.getLogger(__name__)


def extract_message_from_js_result(
    js_result: Any,
    *,
    max_chars: int | None = None,
) -> str:
    try:
        raw_obj = js_result
        if hasattr(js_result, "get_js_value"):
            raw_obj = js_result.get_js_value()
        elif hasattr(js_result, "get_value"):
            raw_obj = js_result.get_value()

        if hasattr(raw_obj, "to_string"):
            raw = raw_obj.to_string()
        elif hasattr(raw_obj, "get_string"):
            raw = raw_obj.get_string()
        elif hasattr(raw_obj, "unpack"):
            raw = raw_obj.unpack()
        else:
            raw = raw_obj
    except Exception:
        logger.exception("Could not extract message payload from JavaScript result.")
        return ""

    if raw is None:
        return ""

    text = str(raw)
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        try:
            parsed = json.loads(text)
            if isinstance(parsed, str):
                text = parsed
        except json.JSONDecodeError:
            text = text[1:-1]

    if isinstance(max_chars, int) and max_chars > 0 and len(text) > max_chars:
        return text[:max_chars]

    return text


def extract_action_from_js_result(
    js_result: Any,
    *,
    allowed_actions: set[str],
    max_chars: int,
) -> str | None:
    raw_value = extract_message_from_js_result(
        js_result,
        max_chars=max_chars,
    ).strip().lower()
    if not raw_value:
        return None

    if raw_value in allowed_actions:
        return raw_value

    payload = None
    if len(raw_value) >= 2 and raw_value[0] in "[{\"'" and raw_value[-1] in "]}\"'":
        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError:
            try:
                payload = ast.literal_eval(raw_value)
            except (SyntaxError, ValueError):
                payload = None

    if payload is None:
        return None

    action = None
    if isinstance(payload, dict):
        action = payload.get("action")
        if not isinstance(action, str):
            action = payload.get("type")
        if not isinstance(action, str):
            action = payload.get("event")
        if not isinstance(action, str):
            action = payload.get("name")
    elif isinstance(payload, str):
        action = payload
    elif isinstance(payload, (list, tuple)) and payload:
        head = payload[0]
        if isinstance(head, dict):
            action = head.get("action")
        else:
            action = head

    if not isinstance(action, str):
        return None

    normalized_action = action.strip().lower()
    return normalized_action if normalized_action in allowed_actions else None


def on_js_attach_file(
    window: "ClaudeCodeWindow",
    pane_id: str,
    js_result: Any,
    *,
    max_option_payload_chars: int,
) -> None:
    if not window._activate_existing_pane(pane_id):
        return
    raw_payload = window._extract_message_from_js_result(
        js_result,
        max_chars=max_option_payload_chars,
    )
    action = window._extract_action_from_js_result(
        js_result,
        allowed_actions={
            "open",
            "attach",
            "attachfile",
            "attach_file",
            "add",
            "openfile",
            "open_file",
            "add_file",
            "select",
            "browse",
        },
    )
    normalized_payload = raw_payload.strip().lower()
    if action is None and normalized_payload in {"", "null", "none", "undefined"}:
        action = "open"
    if action is None:
        return
    window._set_status_message("Opening file chooser...", STATUS_INFO)

    attach_folder = str(Path.home())
    if os.path.isdir(window._project_folder):
        attach_folder = window._project_folder
    image_filter = Gtk.FileFilter()
    image_filter.set_name("Images")
    for mime_type in ("image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml"):
        image_filter.add_mime_type(mime_type)

    text_filter = Gtk.FileFilter()
    text_filter.set_name("Text files")
    for mime_type in (
        "text/plain",
        "text/markdown",
        "application/json",
        "application/x-yaml",
        "text/x-python",
        "text/x-shellscript",
    ):
        text_filter.add_mime_type(mime_type)
    for pattern in ("*.txt", "*.md", "*.py", "*.js", "*.ts", "*.json", "*.yaml", "*.yml", "*.csv", "*.log"):
        text_filter.add_pattern(pattern)

    all_filter = Gtk.FileFilter()
    all_filter.set_name("All files")
    all_filter.add_pattern("*")
    selected_paths: list[str] = []

    if GTK4 and hasattr(Gtk, "FileChooserNative"):
        chooser = Gtk.FileChooserNative.new(
            "Attach file",
            window,
            Gtk.FileChooserAction.OPEN,
            "Attach",
            "Cancel",
        )
        chooser.set_modal(True)
        chooser.set_select_multiple(True)
        chooser.add_filter(image_filter)
        chooser.add_filter(text_filter)
        chooser.add_filter(all_filter)
        try:
            chooser.set_current_folder(Gio.File.new_for_path(attach_folder))
        except Exception:
            pass

        try:
            response = window._run_native_chooser(chooser)
            if window._is_dialog_accept_response(response):
                selected_paths = window._extract_selected_paths_from_chooser(chooser)
        finally:
            chooser.destroy()
    else:
        dialog = Gtk.FileChooserDialog(
            title="Attach file",
            parent=window,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.set_show_hidden(True)
        dialog.add_buttons(
            "Cancel",
            Gtk.ResponseType.CANCEL,
            "Attach",
            Gtk.ResponseType.OK,
        )
        dialog.set_modal(True)
        dialog.set_select_multiple(True)
        dialog.add_filter(image_filter)
        dialog.add_filter(text_filter)
        dialog.add_filter(all_filter)
        try:
            dialog.set_current_folder(attach_folder)
        except Exception:
            pass

        try:
            response = window._run_dialog(dialog)
            if window._is_dialog_accept_response(response):
                selected_paths = window._extract_selected_paths_from_chooser(dialog)
        finally:
            dialog.destroy()

    if not selected_paths:
        return

    window._set_status_message("Preparing attachments...", STATUS_INFO)

    def _apply_encoded_attachments(
        payloads: list[dict[str, str]],
        skipped_count: int,
        hit_file_size_limit: bool,
        hit_total_size_limit: bool,
    ) -> bool:
        if not window._activate_existing_pane(pane_id):
            return False
        added_count = 0
        for payload in payloads:
            window._call_js("addHostAttachment", payload)
            added_count += 1
        if hit_file_size_limit:
            window._add_system_message("One or more attachments exceeded size limit.")
        if hit_total_size_limit:
            window._add_system_message("Attachment total size limit reached.")
        if added_count == 0 and skipped_count == 0:
            return False
        if skipped_count:
            window._set_status_message(
                f"{added_count} attached, {skipped_count} skipped.",
                STATUS_WARNING,
            )
            return False
        window._set_status_message(f"{added_count} file(s) attached.", STATUS_INFO)
        return False

    def _encode_selected_files() -> None:
        payloads, skipped_count, hit_file_size_limit, hit_total_size_limit = encode_host_attachment_payloads(
            selected_paths
        )
        GLib.idle_add(
            _apply_encoded_attachments,
            payloads,
            skipped_count,
            hit_file_size_limit,
            hit_total_size_limit,
        )

    threading.Thread(target=_encode_selected_files, daemon=True).start()


def on_js_permission_response(
    window: "ClaudeCodeWindow",
    pane_id: str,
    js_result: Any,
    *,
    max_permission_payload_chars: int,
) -> None:
    if not window._activate_existing_pane(pane_id):
        return
    raw_payload = window._extract_message_from_js_result(
        js_result,
        max_chars=max_permission_payload_chars + 1,
    )
    if not raw_payload:
        return
    if len(raw_payload) > max_permission_payload_chars:
        window._set_status_message("Permission payload too large", STATUS_WARNING)
        logger.warning(
            "pane=%s provider=%s permission_payload_rejected reason=too_large",
            pane_id,
            window._active_provider_id,
        )
        return

    def _pick(payload: dict[str, Any], *names: str) -> Any:
        for name in names:
            if name in payload:
                return payload[name]

            if isinstance(name, str):
                lower = name.lower()
                for key in payload.keys():
                    if isinstance(key, str) and key.lower() == lower:
                        return payload[key]
        return None

    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().casefold()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        if isinstance(value, (int, float)):
            return value != 0
        return False

    try:
        parsed_payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        try:
            parsed_payload = ast.literal_eval(raw_payload)
        except (SyntaxError, ValueError):
            logger.warning(
                "pane=%s provider=%s permission_payload_rejected reason=invalid_json",
                pane_id,
                window._active_provider_id,
            )
            return

    if isinstance(parsed_payload, str):
        parsed_payload = {"action": parsed_payload}

    if not isinstance(parsed_payload, dict):
        logger.warning(
            "pane=%s provider=%s permission_payload_rejected reason=not_object",
            pane_id,
            window._active_provider_id,
        )
        return

    action = str(_pick(parsed_payload, "action", "response", "result", "choice", "value") or "").strip().casefold()
    if action in {"y", "yes", "ja"}:
        action = "allow"
    elif action in {"n", "no", "nein"}:
        action = "deny"
    elif action in {"1", "on", "true"}:
        action = "allow"
    elif action in {"0", "off", "false"}:
        action = "deny"
    elif action == "always allow":
        action = "always_allow"

    if action not in {"allow", "deny", "comment", "always_allow"}:
        if action and action not in {"", "true", "false"}:
            logger.warning(
                "pane=%s provider=%s permission_payload_rejected reason=invalid_action action=%s",
                pane_id,
                window._active_provider_id,
                action,
            )
            return
        action = "comment"

    comment = str(
        _pick(parsed_payload, "comment", "text", "note", "message")
        or ""
    ).strip()[:4000]

    if action == "comment" and not comment:
        comment = str(_pick(parsed_payload, "value", "response", "choice") or "").strip()[:4000]

    if not comment and action == "comment":
        logger.warning(
            "pane=%s provider=%s permission_payload_rejected reason=invalid_action action=%s",
            pane_id,
            window._active_provider_id,
            action,
        )
        return

    tool_name = str(_pick(parsed_payload, "toolName", "tool_name", "tool", "name") or "").strip()[:120]
    request_id = str(_pick(parsed_payload, "requestId", "request_id", "id") or "").strip()[:160]
    is_denial_card = _to_bool(_pick(parsed_payload, "isDenialCard", "is_denial_card", "isDenial"))
    selected_value = str(
        _pick(parsed_payload, "value", "response", "choice", "text", "comment", "message")
        or ""
    ).strip()[:4000]

    if action == "always_allow" and tool_name:
        window._allowed_tools.add(tool_name)
        window._set_status_message(f"Always allowing {tool_name} for this session", STATUS_INFO)
        window._add_system_message(
            f"Tool '{tool_name}' has been added to the allowed list. "
            "It will be pre-approved on future requests in this session."
        )
        if not is_denial_card:
            window._claude_process.send_permission_response(
                action="allow",
                request_id=request_id,
            )
        return

    if is_denial_card:
        if action == "allow" and tool_name:
            window._allowed_tools.add(tool_name)
            window._set_status_message(
                f"Tool '{tool_name}' allowed. Re-send your message to retry.", STATUS_INFO,
            )
            window._add_system_message(
                f"Tool '{tool_name}' has been allowed. Please re-send your message "
                f"so {window._active_provider.name} can use this tool."
            )
        elif action == "deny":
            window._set_status_message("Permission denied", STATUS_WARNING)
        return

    sent = window._claude_process.send_permission_response(
        action=action,
        comment=comment,
        request_id=request_id,
    )
    if not sent:
        fallback_reply = comment or selected_value
        if not fallback_reply:
            if action == "allow":
                fallback_reply = "yes"
            elif action == "deny":
                fallback_reply = "no"

        if fallback_reply and not window._claude_process.is_running():
            window._set_status_message(
                "Permission response could not be delivered directly. Sent as follow-up message.",
                STATUS_WARNING,
            )
            window._add_system_message(
                "Could not deliver permission response directly. Sending your answer as a normal reply."
            )
            window._call_js("hostSendMessage", fallback_reply)
            return

        window._set_status_message("Could not deliver permission response", STATUS_WARNING)
        window._add_system_message(
            f"Could not send permission response to {window._active_provider.name}."
        )
        return

    if action == "allow":
        window._set_status_message("Permission approved", STATUS_INFO)
    elif action == "deny":
        window._set_status_message("Permission denied", STATUS_WARNING)
    else:
        window._set_status_message("Permission comment sent", STATUS_INFO)


def on_js_send_message(
    window: "ClaudeCodeWindow",
    pane_id: str,
    js_result: Any,
    *,
    max_send_payload_chars: int,
    agentctl_hint: str,
) -> None:
    if not window._activate_existing_pane(pane_id):
        return
    raw_text = window._extract_message_from_js_result(
        js_result,
        max_chars=max_send_payload_chars + 1,
    )
    if len(raw_text) > max_send_payload_chars:
        window._set_status_message("Message payload too large", STATUS_WARNING)
        return
    message, attachments = parse_send_payload(raw_text)
    if not message and not attachments:
        if raw_text.strip():
            window._set_status_message("Invalid message payload", STATUS_WARNING)
            logger.warning(
                "pane=%s provider=%s send_payload_rejected reason=invalid_schema",
                pane_id,
                window._active_provider_id,
            )
        return
    if message and window._handle_agent_command(pane_id, message):
        if attachments:
            window._set_status_message("Attachments are ignored for local /agent commands.", STATUS_MUTED)
        return

    if window._binary_path is None:
        window._refresh_connection_state()
        window._set_status_message(f"{window._active_provider.name} CLI not found", STATUS_ERROR)
        window._add_system_message(f"{window._provider_cli_label()} is not available.")
        return
    if window._active_provider_id == "codex":
        auth_state, is_fresh = get_cached_codex_authentication(max_age_seconds=30.0)
        if not is_fresh and hasattr(window, "_refresh_codex_auth_async"):
            try:
                window._refresh_codex_auth_async()
            except Exception:
                pass
        if auth_state is not True:
            window._refresh_connection_state()
            window._set_status_message(
                "Codex login status could not be confirmed; sending anyway.",
                STATUS_WARNING,
            )

    _, model_value = window._model_options[window._selected_model_index]
    _, permission_value, _ = window._permission_options[window._selected_permission_index]
    reasoning_value = window._reasoning_value_from_index(window._selected_reasoning_index)
    if not window._active_provider.supports_reasoning:
        reasoning_value = "medium"

    def _continue_send_with_attachments(attachment_paths: list[str]) -> bool:
        if not window._activate_existing_pane(pane_id):
            cleanup_temp_paths(attachment_paths)
            return False

        if window._active_session_id is None:
            if os.path.isdir(window._project_folder):
                window._start_new_session(window._project_folder, reset_conversation=False)
            else:
                cleanup_temp_paths(attachment_paths)
                window._set_status_message("No active session", STATUS_ERROR)
                window._add_system_message("Create a session first.")
                return False

        if window._claude_process.is_running():
            cleanup_temp_paths(attachment_paths)
            window._add_system_message(f"{window._active_provider.name} is still responding. Please wait.")
            return False

        active_session = window._get_active_session()
        if active_session is None:
            cleanup_temp_paths(attachment_paths)
            window._set_status_message("No active session", STATUS_ERROR)
            window._add_system_message("No active session available.")
            return False

        if not os.path.isdir(window._project_folder):
            cleanup_temp_paths(attachment_paths)
            window._set_status_message("Session folder not found", STATUS_ERROR)
            window._add_system_message("The selected project folder no longer exists.")
            window._set_active_session_status(SESSION_STATUS_ERROR)
            return False

        composed_message = compose_message_with_attachments(message, attachment_paths)
        if not composed_message.strip():
            cleanup_temp_paths(attachment_paths)
            return False

        if window._is_primary_pane(pane_id) and window._agentctl_auto_enabled:
            composed_message = f"{agentctl_hint}\n\nUser request:\n{composed_message}"

        window._has_messages = True
        window._context_char_count += len(composed_message)
        window._update_context_indicator()

        # Do not create an empty assistant row immediately on send.
        # The row will be created when the first assistant chunk arrives.
        window._pulse_chat_shell()
        window._set_connection_state(CONNECTION_STARTING)
        window._set_status_message(f"Sending message to {window._active_provider.name}...", STATUS_INFO)
        active_caps = window._cli_caps_for(window._active_provider_id)

        active_session.status = SESSION_STATUS_ACTIVE
        active_session.last_used_at = current_timestamp()
        window._save_sessions_safe("Could not save sessions")
        window._refresh_session_list()

        window._add_to_history("user", composed_message)
        window._permission_request_pending = False

        request_token = str(uuid.uuid4())
        previous_request_token = window._active_request_token
        previous_request_session_id = window._active_request_session_id
        window._active_request_token = request_token
        window._active_request_session_id = active_session.id
        logger.info(
            "pane=%s request=%s provider=%s session=%s send_start",
            pane_id,
            request_token,
            window._active_provider_id,
            active_session.id,
        )
        config = ClaudeRunConfig(
            binary_path=window._binary_path,
            message=composed_message,
            cwd=window._project_folder,
            model=model_value,
            permission_mode=permission_value,
            conversation_id=window._conversation_id,
            supports_model_flag=active_caps.supports_model_flag,
            supports_permission_flag=active_caps.supports_permission_flag,
            supports_output_format_flag=active_caps.supports_output_format_flag,
            supports_stream_json=active_caps.supports_stream_json,
            supports_json=active_caps.supports_json,
            supports_include_partial_messages=active_caps.supports_include_partial_messages,
            stream_json_requires_verbose=window._stream_json_requires_verbose,
            reasoning_level=reasoning_value,
            supports_reasoning_flag=(
                active_caps.supports_reasoning_flag
                or window._active_provider_id in {"codex", "gemini"}
            )
            and window._active_provider.supports_reasoning,
            allowed_tools=list(window._allowed_tools) if window._allowed_tools else None,
            provider_id=window._active_provider_id,
        )
        started = window._claude_process.send_message(request_token=request_token, config=config)

        if not started:
            cleanup_temp_paths(attachment_paths)
            window._context_char_count = max(0, window._context_char_count - len(composed_message))
            window._update_context_indicator()
            window._active_request_token = previous_request_token
            window._active_request_session_id = previous_request_session_id
            window._finish_assistant_message(target_session_id=active_session.id)
            window._set_typing(False)
            window._refresh_connection_state()
            window._set_status_message("A request is already running", STATUS_WARNING)
            logger.warning(
                "pane=%s request=%s provider=%s send_rejected_already_running",
                pane_id,
                request_token,
                window._active_provider_id,
            )
            return False

        window._request_temp_files[request_token] = attachment_paths
        return False

    if attachments:
        window._set_status_message("Preparing attachments...", STATUS_INFO)

    def _materialize_attachments_worker() -> None:
        attachment_paths = materialize_attachments(attachments)
        GLib.idle_add(_continue_send_with_attachments, attachment_paths)

    threading.Thread(target=_materialize_attachments_worker, daemon=True).start()
