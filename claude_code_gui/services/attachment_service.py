"""Decode, validate, materialize attachments and cleanup temporary files."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import tempfile
from urllib.parse import unquote_to_bytes

from claude_code_gui.app.constants import ATTACHMENT_MAX_BYTES

MAX_ATTACHMENTS_PER_MESSAGE = 12
MAX_ATTACHMENT_TOTAL_BYTES = 64 * 1024 * 1024
MAX_SEND_MESSAGE_CHARS = 120_000
MAX_DATA_URL_CHARS = ATTACHMENT_MAX_BYTES * 2 + 1024


def _guess_attachment_mime_type(path: str) -> str:
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type:
        mime_type = "application/octet-stream"
    if mime_type == "application/octet-stream":
        lower_suffix = os.path.splitext(path)[1].lower()
        mime_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".bmp": "image/bmp",
            ".avif": "image/avif",
            ".heic": "image/heic",
        }.get(lower_suffix, mime_type)
    return mime_type


def encode_host_attachment_payloads(
    selected_paths: list[str],
) -> tuple[list[dict[str, str]], int, bool, bool]:
    payloads: list[dict[str, str]] = []
    skipped_count = 0
    total_bytes = 0
    hit_file_size_limit = False
    hit_total_size_limit = False

    for selected in selected_paths:
        if len(payloads) >= MAX_ATTACHMENTS_PER_MESSAGE:
            skipped_count += 1
            continue
        if not os.path.isfile(selected):
            skipped_count += 1
            continue
        try:
            file_size = os.path.getsize(selected)
        except OSError:
            skipped_count += 1
            continue
        if file_size > ATTACHMENT_MAX_BYTES:
            skipped_count += 1
            hit_file_size_limit = True
            continue
        if total_bytes + file_size > MAX_ATTACHMENT_TOTAL_BYTES:
            skipped_count += 1
            hit_total_size_limit = True
            continue
        try:
            with open(selected, "rb") as handle:
                raw_bytes = handle.read()
        except OSError:
            skipped_count += 1
            continue

        mime_type = _guess_attachment_mime_type(selected)
        payloads.append(
            {
                "name": os.path.basename(selected),
                "path": selected,
                "type": mime_type,
                "data": f"data:{mime_type};base64,{base64.b64encode(raw_bytes).decode('ascii')}",
            }
        )
        total_bytes += file_size

    return payloads, skipped_count, hit_file_size_limit, hit_total_size_limit


def decode_data_url(data_url: str) -> tuple[str, bytes] | None:
    if not data_url.startswith("data:"):
        return None
    header, separator, payload = data_url.partition(",")
    if not separator:
        return None
    meta = header[5:]
    is_base64 = ";base64" in meta
    mime_type = meta.split(";")[0].strip() or "application/octet-stream"
    try:
        data = base64.b64decode(payload) if is_base64 else unquote_to_bytes(payload)
    except (ValueError, TypeError):
        return None
    return mime_type, data


def parse_send_payload(raw_text: str) -> tuple[str, list[dict[str, str]]]:
    parsed_text = raw_text.strip()
    if not parsed_text:
        return "", []
    try:
        payload = json.loads(parsed_text)
    except json.JSONDecodeError:
        return parsed_text[:MAX_SEND_MESSAGE_CHARS], []

    if not isinstance(payload, dict):
        return parsed_text[:MAX_SEND_MESSAGE_CHARS], []

    allowed_root_keys = {"text", "attachments"}
    if any(not isinstance(key, str) or key not in allowed_root_keys for key in payload.keys()):
        return "", []

    message = str(payload.get("text") or "").strip()[:MAX_SEND_MESSAGE_CHARS]
    raw_attachments = payload.get("attachments")
    attachments: list[dict[str, str]] = []
    if isinstance(raw_attachments, list):
        if len(raw_attachments) > MAX_ATTACHMENTS_PER_MESSAGE:
            raw_attachments = raw_attachments[:MAX_ATTACHMENTS_PER_MESSAGE]
        for item in raw_attachments:
            if not isinstance(item, dict):
                continue
            allowed_attachment_keys = {"name", "type", "data", "path"}
            if any(
                not isinstance(key, str) or key not in allowed_attachment_keys
                for key in item.keys()
            ):
                continue
            name = str(item.get("name") or "attachment").strip() or "attachment"
            file_type = str(item.get("type") or "application/octet-stream").strip() or "application/octet-stream"
            data = str(item.get("data") or "").strip()
            if file_type == "application/octet-stream" and data.startswith("data:"):
                comma_index = data.find(",")
                if comma_index >= 5:
                    header = data[5:comma_index]
                else:
                    header = ""
                inferred = header.split(";", 1)[0].strip()
                if inferred.startswith("image/"):
                    file_type = inferred
            if len(data) > MAX_DATA_URL_CHARS:
                continue
            if not data:
                continue
            attachments.append({"name": name, "type": file_type, "data": data})
    return message, attachments


def materialize_attachments(attachments: list[dict[str, str]]) -> list[str]:
    temp_paths: list[str] = []
    total_bytes = 0
    for attachment in attachments:
        decoded = decode_data_url(attachment.get("data", ""))
        if decoded is None:
            continue
        mime_type, raw_bytes = decoded
        if len(raw_bytes) > ATTACHMENT_MAX_BYTES:
            continue

        if total_bytes + len(raw_bytes) > MAX_ATTACHMENT_TOTAL_BYTES:
            continue
        total_bytes += len(raw_bytes)

        original_name = attachment.get("name", "attachment")
        _, suffix = os.path.splitext(original_name)
        if not suffix:
            guessed = mimetypes.guess_extension(mime_type)
            suffix = guessed or ""

        try:
            handle = tempfile.NamedTemporaryFile(
                mode="wb",
                prefix="claude-gui-attachment-",
                suffix=suffix,
                delete=False,
            )
        except OSError:
            continue

        with handle:
            handle.write(raw_bytes)
        temp_paths.append(handle.name)
    return temp_paths


def compose_message_with_attachments(message: str, attachment_paths: list[str]) -> str:
    base_text = message.strip()
    if not attachment_paths:
        return base_text
    attachment_block = "\n".join(f"- {path}" for path in attachment_paths)
    if not base_text:
        base_text = "Please use the attached files as context."
    return f"{base_text}\n\nAttached files:\n{attachment_block}"


def cleanup_temp_paths(paths: list[str]) -> None:
    for path in paths:
        if not path:
            continue
        try:
            os.unlink(path)
        except OSError:
            continue
