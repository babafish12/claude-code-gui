"""JavaScript bridge handlers extracted from the main window module."""

from __future__ import annotations

import ast
import base64
import json
import logging
import os
import tempfile
import threading
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_code_gui.app.constants import (
    ATTACHMENT_MAX_BYTES,
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
from claude_code_gui.gi_runtime import GTK4, GLib, Gio, Gtk
from claude_code_gui.services.attachment_service import (
    cleanup_temp_paths,
    compose_message_with_attachments,
    encode_host_attachment_payloads,
    materialize_attachments,
    parse_send_payload,
    parse_send_payload_kind,
)
from claude_code_gui.services.binary_probe import is_codex_authenticated
from claude_code_gui.services.speech_transcribe import transcribe_audio_file

if TYPE_CHECKING:
    from claude_code_gui.ui.window import ClaudeCodeWindow


logger = logging.getLogger(__name__)


def _normalize_attachment_path(path_value: str) -> str | None:
    try:
        return str(Path(path_value).expanduser().resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        return None


def _path_is_within_root(path_value: str, root_value: str) -> bool:
    if not path_value or not root_value:
        return False
    try:
        return os.path.commonpath([path_value, root_value]) == root_value
    except ValueError:
        return False


def _attachment_scope_id(
    window: "ClaudeCodeWindow",
    pane_id: str,
    *,
    session_id: str | None = None,
) -> str:
    pane = window._pane_by_id(pane_id)
    if pane is None:
        return ""
    active_session_id = str(
        session_id
        or getattr(pane, "_active_session_id", None)
        or getattr(window, "_active_session_id", None)
        or ""
    ).strip()
    return active_session_id or f"__pane__:{pane_id}"


def _pane_approved_attachment_paths(
    window: "ClaudeCodeWindow",
    pane_id: str,
    *,
    session_id: str | None = None,
) -> set[str]:
    pane = window._pane_by_id(pane_id)
    if pane is None:
        return set()
    approved_by_session = getattr(pane, "_approved_attachment_paths_by_session", None)
    if not isinstance(approved_by_session, dict):
        approved_by_session = {}
        pane._approved_attachment_paths_by_session = approved_by_session
    scope_id = _attachment_scope_id(window, pane_id, session_id=session_id)
    if not scope_id:
        return set()
    approved = approved_by_session.get(scope_id)
    if not isinstance(approved, set):
        approved = set()
        approved_by_session[scope_id] = approved
    return approved


def _publish_host_attachment_payloads_async(
    window: "ClaudeCodeWindow",
    pane_id: str,
    selected_paths: list[str],
    *,
    skipped_count: int = 0,
    session_id: str | None = None,
) -> None:
    if not selected_paths:
        return
    target_session_id = str(session_id or "").strip()

    def _finish(
        payloads: list[dict[str, str]],
        worker_skipped_count: int,
        hit_file_size_limit: bool,
        hit_total_size_limit: bool,
    ) -> bool:
        if pane_id not in window._pane_registry:
            return False
        with window._pane_context(pane_id):
            pane = window._pane_by_id(pane_id)
            current_session_id = str(getattr(pane, "_active_session_id", None) or "").strip() if pane is not None else ""
            if target_session_id and current_session_id != target_session_id:
                logger.warning(
                    "pane=%s attachment_publish_discarded reason=session_switched target_session=%s current_session=%s",
                    pane_id,
                    target_session_id,
                    current_session_id,
                )
                window._set_status_message(
                    "Attachments were discarded because the active session changed.",
                    STATUS_WARNING,
                )
                return False
            added_count = len(payloads)
            for payload in payloads:
                window._call_js_in_pane(pane_id, "addHostAttachment", payload)
            total_skipped = skipped_count + worker_skipped_count
            if hit_file_size_limit:
                window._add_system_message("One or more attachments exceeded size limit.")
            if hit_total_size_limit:
                window._add_system_message("Attachment total size limit reached.")
            if added_count == 0 and total_skipped == 0:
                return False
            if total_skipped:
                window._set_status_message(
                    f"{added_count} attached, {total_skipped} skipped.",
                    STATUS_WARNING,
                )
            else:
                window._set_status_message(f"{added_count} file(s) attached.", STATUS_INFO)
        return False

    def _work() -> None:
        payloads, worker_skipped_count, hit_file_size_limit, hit_total_size_limit = encode_host_attachment_payloads(
            selected_paths,
        )
        GLib.idle_add(
            _finish,
            payloads,
            worker_skipped_count,
            hit_file_size_limit,
            hit_total_size_limit,
        )

    threading.Thread(target=_work, daemon=True).start()


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

    normalized_paths: list[str] = []
    target_session_id = str(getattr(window._pane_by_id(pane_id), "_active_session_id", None) or "").strip() or None
    approved_paths = _pane_approved_attachment_paths(window, pane_id, session_id=target_session_id)
    for selected in selected_paths:
        normalized = _normalize_attachment_path(selected)
        if normalized:
            normalized_paths.append(normalized)
            approved_paths.add(normalized)
    _publish_host_attachment_payloads_async(
        window,
        pane_id,
        normalized_paths,
        session_id=target_session_id,
    )


def on_js_attach_paths(
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
    if not raw_payload:
        return

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict):
        return

    raw_paths = payload.get("paths")
    if not isinstance(raw_paths, list):
        return

    project_root = _normalize_attachment_path(window._project_folder) if window._project_folder else None
    target_session_id = str(getattr(window._pane_by_id(pane_id), "_active_session_id", None) or "").strip() or None
    approved_paths = _pane_approved_attachment_paths(window, pane_id, session_id=target_session_id)
    candidate_paths: list[str] = []
    skipped_count = 0
    for entry in raw_paths:
        if not isinstance(entry, str):
            continue
        clean = entry.strip()
        if not clean:
            continue
        if len(clean) > 4096:
            continue
        normalized = _normalize_attachment_path(clean)
        if not normalized:
            skipped_count += 1
            continue
        if normalized in approved_paths or (project_root and _path_is_within_root(normalized, project_root)):
            candidate_paths.append(normalized)
            continue
        skipped_count += 1

    if not candidate_paths:
        if skipped_count:
            window._set_status_message(
                "Only project files or file-chooser approved paths can be attached from pasted paths.",
                STATUS_WARNING,
            )
        return

    _publish_host_attachment_payloads_async(
        window,
        pane_id,
        candidate_paths,
        skipped_count=skipped_count,
        session_id=target_session_id,
    )


def on_js_arm_user_media(
    window: "ClaudeCodeWindow",
    pane_id: str,
    _js_result: Any,
) -> None:
    if not window._activate_existing_pane(pane_id):
        return
    window._arm_user_media_permission(pane_id)


def on_js_disarm_user_media(
    window: "ClaudeCodeWindow",
    pane_id: str,
    _js_result: Any,
) -> None:
    if not window._activate_existing_pane(pane_id):
        return
    if hasattr(window, "_disarm_user_media_permission"):
        window._disarm_user_media_permission(pane_id)


def on_js_transcribe_audio(
    window: "ClaudeCodeWindow",
    pane_id: str,
    js_result: Any,
    *,
    max_audio_payload_chars: int,
) -> None:
    if not window._activate_existing_pane(pane_id):
        return
    raw_payload = window._extract_message_from_js_result(
        js_result,
        max_chars=max_audio_payload_chars + 1,
    )
    if not raw_payload:
        return
    if len(raw_payload) > max_audio_payload_chars:
        window._set_status_message("Voice payload too large", STATUS_WARNING)
        window._call_js("finishVoiceTranscription")
        return

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        window._set_status_message("Invalid voice payload", STATUS_WARNING)
        window._call_js("finishVoiceTranscription")
        return
    if not isinstance(payload, dict):
        window._set_status_message("Invalid voice payload", STATUS_WARNING)
        window._call_js("finishVoiceTranscription")
        return

    data_url = str(payload.get("data") or "").strip()
    if not data_url.startswith("data:") or "," not in data_url:
        window._set_status_message("Invalid voice data URL", STATUS_WARNING)
        window._call_js("finishVoiceTranscription")
        return

    header, encoded = data_url.split(",", 1)
    header_lower = header.lower()
    if ";base64" not in header_lower:
        window._set_status_message("Voice payload must be base64 data URL", STATUS_WARNING)
        window._call_js("finishVoiceTranscription")
        return

    try:
        audio_bytes = base64.b64decode(encoded, validate=False)
    except Exception:
        window._set_status_message("Could not decode voice payload", STATUS_WARNING)
        window._call_js("finishVoiceTranscription")
        return

    if not audio_bytes:
        window._set_status_message("Voice payload is empty", STATUS_WARNING)
        window._call_js("finishVoiceTranscription")
        return

    if len(audio_bytes) > ATTACHMENT_MAX_BYTES:
        window._set_status_message(
            f"Voice recording exceeds {ATTACHMENT_MAX_BYTES // (1024 * 1024)} MB limit.",
            STATUS_WARNING,
        )
        window._call_js("finishVoiceTranscription")
        return

    raw_type = str(payload.get("type") or "").strip().lower()
    suffix = {
        "audio/webm": ".webm",
        "audio/webm;codecs=opus": ".webm",
        "audio/ogg": ".ogg",
        "audio/ogg;codecs=opus": ".ogg",
        "audio/mp4": ".mp4",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
    }.get(raw_type, ".webm")
    language = str(payload.get("language") or "").strip()

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            prefix="ccg-voice-",
            suffix=suffix,
            delete=False,
        ) as handle:
            handle.write(audio_bytes)
            temp_path = handle.name
    except OSError as error:
        window._set_status_message(f"Could not store voice payload: {error}", STATUS_WARNING)
        window._call_js("finishVoiceTranscription")
        return

    if not temp_path:
        window._set_status_message("Could not store voice payload", STATUS_WARNING)
        window._call_js("finishVoiceTranscription")
        return

    window._set_status_message("Transcribing voice input with whisper.cpp...", STATUS_INFO)
    logger.info(
        "voice: received audio bytes=%d type=%r lang=%r tmp=%s",
        len(audio_bytes),
        raw_type,
        language,
        temp_path,
    )

    def _finish_on_ui(*, transcript: str, error_text: str) -> bool:
        try:
            if pane_id not in window._pane_registry:
                return False
            with window._pane_context(pane_id):
                if transcript:
                    window._call_js("applyVoiceTranscription", transcript)
                    window._set_status_message("Voice transcription inserted.", STATUS_INFO)
                    return False
                window._call_js("finishVoiceTranscription")
                window._set_status_message(error_text, STATUS_WARNING)
                window._add_system_message(error_text)
        except Exception:
            logger.exception("Could not publish voice transcription result.")
        return False

    def _work() -> None:
        transcript = ""
        error_text = ""
        try:
            logger.info("voice: starting transcription for %s", temp_path)
            try:
                transcript, error_text = transcribe_audio_file(
                    temp_path,
                    language=language,
                )
            finally:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            logger.info(
                "voice: transcription done transcript_len=%d error=%r",
                len(transcript or ""),
                error_text,
            )
        except Exception as exc:
            logger.exception("voice: _work crashed")
            error_text = f"Voice worker crashed: {exc}"

        cleaned = (transcript or "").strip()
        if cleaned:
            GLib.idle_add(_finish_on_ui, transcript=cleaned, error_text="")
            return

        fallback_error = error_text.strip() if isinstance(error_text, str) else ""
        if not fallback_error:
            fallback_error = "Voice transcription failed."
        GLib.idle_add(_finish_on_ui, transcript="", error_text=fallback_error)

    threading.Thread(target=_work, daemon=True).start()


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

    if action == "always_allow":
        action = "allow"

    tool_name = str(_pick(parsed_payload, "toolName", "tool_name", "tool", "name") or "").strip()[:120]
    request_id = str(_pick(parsed_payload, "requestId", "request_id", "id") or "").strip()[:160]
    is_denial_card = _to_bool(_pick(parsed_payload, "isDenialCard", "is_denial_card", "isDenial"))
    selected_value = str(
        _pick(parsed_payload, "value", "response", "choice", "text", "comment", "message")
        or ""
    ).strip()[:4000]
    pane = window._pane_by_id(pane_id)
    target_session_id = getattr(pane, "_active_session_id", None) or getattr(window, "_active_session_id", None)
    pending_payload = None
    if hasattr(window, "_pending_permission_payload_for_session"):
        try:
            pending_payload = window._pending_permission_payload_for_session(
                target_session_id,
                request_id=request_id,
            )
        except TypeError:
            pending_payload = window._pending_permission_payload_for_session(target_session_id)

    pending_request_id = ""
    pending_tool_name = ""
    if isinstance(pending_payload, dict):
        pending_request_id = str(
            _pick(pending_payload, "requestId", "request_id", "id") or ""
        ).strip()[:160]
        pending_tool_name = str(
            _pick(pending_payload, "toolName", "tool_name", "tool", "name") or ""
        ).strip()[:120]

    if (
        not pending_request_id
        or not request_id
        or request_id != pending_request_id
        or not pending_tool_name
        or not tool_name
        or tool_name.casefold() != pending_tool_name.casefold()
    ):
        logger.warning(
            "pane=%s provider=%s permission_payload_rejected reason=pending_mismatch request_id=%s tool=%s",
            pane_id,
            window._active_provider_id,
            request_id,
            tool_name,
        )
        window._set_status_message("Permission response ignored because the pending request changed.", STATUS_WARNING)
        return

    if is_denial_card:
        if action == "allow" and tool_name:
            window._set_status_message(
                f"Tool '{tool_name}' allowed. Re-send your message to retry.", STATUS_INFO,
            )
            window._add_system_message(
                f"Tool '{tool_name}' has been allowed. Please re-send your message "
                f"so {window._active_provider.name} can use this tool."
            )
        elif action == "deny":
            window._set_status_message("Permission denied", STATUS_WARNING)
        if hasattr(window, "_clear_pending_permission_state_for_session"):
            window._clear_pending_permission_state_for_session(target_session_id, request_id=request_id)
        return

    sent = window._claude_process.send_permission_response(
        action=action,
        comment=comment,
        request_id=request_id,
    )
    if not sent:
        if hasattr(window, "_clear_pending_permission_state_for_session"):
            window._clear_pending_permission_state_for_session(target_session_id, request_id=request_id)
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

    if hasattr(window, "_clear_pending_permission_state_for_session"):
        window._clear_pending_permission_state_for_session(target_session_id, request_id=request_id)
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
    history_role = parse_send_payload_kind(raw_text)
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

    effective_provider_id = window._pane_effective_provider_id(pane_id)
    effective_provider = window._pane_effective_provider(pane_id)
    effective_binary_path = window._pane_effective_binary_path(pane_id)
    if effective_binary_path is None:
        window._refresh_connection_state()
        window._set_status_message(f"{effective_provider.name} CLI not found", STATUS_ERROR)
        window._add_system_message(f"{window._provider_cli_label(effective_provider_id)} is not available.")
        return
    if effective_provider_id == "codex" and not is_codex_authenticated():
        window._refresh_connection_state()
        window._set_status_message(
            "Codex login status could not be confirmed; sending anyway.",
            STATUS_WARNING,
        )

    if window._active_session_id is None:
        if os.path.isdir(window._project_folder):
            window._start_new_session(
                window._project_folder,
                reset_conversation=False,
                provider_id=effective_provider_id,
            )
        else:
            window._set_status_message("No active session", STATUS_ERROR)
            window._add_system_message("Create a session first.")
            return

    if window._claude_process.is_running():
        window._add_system_message(f"{effective_provider.name} is still responding. Please wait.")
        return

    active_session = window._get_active_session()
    if active_session is None:
        window._set_status_message("No active session", STATUS_ERROR)
        window._add_system_message("No active session available.")
        return

    if not os.path.isdir(window._project_folder):
        window._set_status_message("Session folder not found", STATUS_ERROR)
        window._add_system_message("The selected project folder no longer exists.")
        window._set_active_session_status(SESSION_STATUS_ERROR)
        return

    if effective_provider_id == window._active_provider_id:
        _, model_value = window._model_options[window._selected_model_index]
        _, permission_value, _ = window._permission_options[window._selected_permission_index]
    else:
        provider_models = list(effective_provider.model_options)
        if not provider_models:
            provider_models = [("Default", "")]
        model_value = (
            active_session.model
            or (provider_models[1][1] if len(provider_models) > 1 else provider_models[0][1])
        )
        provider_permissions = list(effective_provider.permission_options)
        permission_value = (
            active_session.permission_mode
            or (provider_permissions[0][1] if provider_permissions else "auto")
        )
    reasoning_value = window._reasoning_value_from_index(window._selected_reasoning_index)
    if not effective_provider.supports_reasoning:
        reasoning_value = "medium"

    attachment_paths = materialize_attachments(attachments)
    composed_message = compose_message_with_attachments(message, attachment_paths)
    if not composed_message.strip():
        cleanup_temp_paths(attachment_paths)
        return

    if window._is_primary_pane(pane_id) and window._agentctl_auto_enabled:
        composed_message = f"{agentctl_hint}\n\nUser request:\n{composed_message}"

    window._has_messages = True
    window._context_char_count += len(composed_message)
    window._update_context_indicator()

    # Do not create an empty assistant row immediately on send.
    # The row will be created when the first assistant chunk arrives.
    window._pulse_chat_shell()
    window._set_connection_state(CONNECTION_STARTING)
    window._set_status_message(f"Sending message to {effective_provider.name}...", STATUS_INFO)
    active_caps = window._cli_caps_for(effective_provider_id)

    active_session.status = SESSION_STATUS_ACTIVE
    active_session.last_used_at = current_timestamp()
    window._save_sessions_safe("Could not save sessions")
    window._refresh_session_list()

    window._add_to_history(history_role, message or composed_message)
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
        binary_path=effective_binary_path,
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
            or effective_provider_id in {"codex", "gemini"}
        )
        and effective_provider.supports_reasoning,
        provider_id=effective_provider_id,
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
        return

    tracker = getattr(window, "_session_runtime_tracker", None)
    if not isinstance(tracker, set):
        tracker = set()
        window._session_runtime_tracker = tracker
    tracker.add(active_session.id)
    window._request_temp_files[request_token] = attachment_paths
