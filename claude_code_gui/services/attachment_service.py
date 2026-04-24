"""Decode, validate, materialize attachments and cleanup temporary files."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import unquote_to_bytes

from claude_code_gui.app.constants import ATTACHMENT_MAX_BYTES

MAX_ATTACHMENTS_PER_MESSAGE = 12
MAX_ATTACHMENT_TOTAL_BYTES = 64 * 1024 * 1024
MAX_SEND_MESSAGE_CHARS = 120_000
MAX_DATA_URL_CHARS = ATTACHMENT_MAX_BYTES * 2 + 1024

_SUFFIX_MIME_OVERRIDES: dict[str, str] = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".csv": "text/csv",
    ".log": "text/plain",
    ".json": "application/json",
    ".yaml": "application/x-yaml",
    ".yml": "application/x-yaml",
    ".toml": "application/toml",
    ".ini": "text/plain",
    ".cfg": "text/plain",
    ".xml": "application/xml",
    ".html": "text/html",
    ".htm": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".mjs": "application/javascript",
    ".cjs": "application/javascript",
    ".ts": "text/x-typescript",
    ".tsx": "text/x-typescript",
    ".jsx": "text/javascript",
    ".py": "text/x-python",
    ".sh": "text/x-shellscript",
    ".bash": "text/x-shellscript",
    ".zsh": "text/x-shellscript",
    ".rs": "text/plain",
    ".go": "text/plain",
    ".java": "text/plain",
    ".c": "text/plain",
    ".cc": "text/plain",
    ".cpp": "text/plain",
    ".h": "text/plain",
    ".hpp": "text/plain",
    ".sql": "text/plain",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
    ".avif": "image/avif",
    ".heic": "image/heic",
}

_TEXT_ATTACHMENT_MIME_TYPES = {
    "application/javascript",
    "application/json",
    "application/toml",
    "application/xml",
    "application/x-yaml",
    "text/csv",
    "text/css",
    "text/html",
    "text/javascript",
    "text/markdown",
    "text/plain",
    "text/xml",
    "text/x-python",
    "text/x-shellscript",
    "text/x-typescript",
}

_BINARY_SIGNATURE_MIME_TYPES = {
    "application/pdf",
    "image/avif",
    "image/bmp",
    "image/gif",
    "image/heic",
    "image/jpeg",
    "image/png",
    "image/svg+xml",
    "image/webp",
}

_ALLOWED_ATTACHMENT_MIME_TYPES = _TEXT_ATTACHMENT_MIME_TYPES | _BINARY_SIGNATURE_MIME_TYPES
_STRICT_MARKUP_MIME_TYPES = {
    "application/xml",
    "image/svg+xml",
    "text/html",
    "text/xml",
}
_MARKUP_PREFIX_RE = re.compile(
    r"^\s*(?:<\?xml\b|<!doctype\s+html\b|<html\b|<svg\b|<script\b)",
    flags=re.IGNORECASE,
)
_SVG_PREFIX_RE = re.compile(r"^\s*(?:<\?xml\b|<svg\b)", flags=re.IGNORECASE)


def _normalize_mime_type(mime_type: str) -> str:
    normalized = str(mime_type or "").strip().lower()
    if normalized == "image/jpg":
        return "image/jpeg"
    if normalized == "text/x-markdown":
        return "text/markdown"
    if normalized == "application/yaml":
        return "application/x-yaml"
    return normalized


def _guess_attachment_mime_type(path: str) -> str:
    lower_suffix = Path(path).suffix.lower()
    override = _SUFFIX_MIME_OVERRIDES.get(lower_suffix)
    if override:
        return override
    mime_type, _ = mimetypes.guess_type(path)
    return _normalize_mime_type(mime_type or "application/octet-stream")


def _looks_like_text_attachment(raw_bytes: bytes) -> bool:
    if b"\x00" in raw_bytes:
        return False
    try:
        raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _decode_text_attachment_header(raw_bytes: bytes, *, limit: int = 2048) -> str:
    if not _looks_like_text_attachment(raw_bytes):
        return ""
    return raw_bytes[:limit].decode("utf-8", errors="ignore").lstrip("\ufeff")


def _looks_like_markup_attachment(raw_bytes: bytes) -> bool:
    return bool(_MARKUP_PREFIX_RE.match(_decode_text_attachment_header(raw_bytes)))


def _has_iso_bmff_brand(raw_bytes: bytes, *brands: str) -> bool:
    if len(raw_bytes) < 12 or raw_bytes[4:8] != b"ftyp":
        return False
    brand = raw_bytes[8:12].decode("ascii", errors="ignore").lower()
    return brand in {value.lower() for value in brands}


def _looks_like_svg(raw_bytes: bytes) -> bool:
    return bool(_SVG_PREFIX_RE.match(_decode_text_attachment_header(raw_bytes)))


def _matches_binary_signature(mime_type: str, raw_bytes: bytes) -> bool:
    normalized = _normalize_mime_type(mime_type)
    if normalized == "application/pdf":
        return raw_bytes.startswith(b"%PDF-")
    if normalized == "image/png":
        return raw_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    if normalized == "image/jpeg":
        return raw_bytes.startswith(b"\xff\xd8\xff")
    if normalized == "image/gif":
        return raw_bytes.startswith((b"GIF87a", b"GIF89a"))
    if normalized == "image/webp":
        return len(raw_bytes) >= 12 and raw_bytes.startswith(b"RIFF") and raw_bytes[8:12] == b"WEBP"
    if normalized == "image/bmp":
        return raw_bytes.startswith(b"BM")
    if normalized == "image/svg+xml":
        return _looks_like_svg(raw_bytes)
    if normalized == "image/avif":
        return _has_iso_bmff_brand(raw_bytes, "avif", "avis")
    if normalized == "image/heic":
        return _has_iso_bmff_brand(raw_bytes, "heic", "heix", "hevc", "hevx", "mif1", "msf1")
    return False


def _validated_attachment_mime_type(
    *,
    name: str,
    declared_mime_type: str,
    raw_bytes: bytes,
) -> str | None:
    normalized_declared = _normalize_mime_type(declared_mime_type)
    guessed = _guess_attachment_mime_type(name)
    candidate = normalized_declared or guessed
    if candidate == "application/octet-stream":
        candidate = guessed
    candidate = _normalize_mime_type(candidate)
    if candidate not in _ALLOWED_ATTACHMENT_MIME_TYPES:
        return None
    if candidate in _TEXT_ATTACHMENT_MIME_TYPES:
        if not _looks_like_text_attachment(raw_bytes):
            return None
        if candidate == "text/plain" and _looks_like_markup_attachment(raw_bytes):
            return None
        if candidate in _STRICT_MARKUP_MIME_TYPES and candidate != "image/svg+xml":
            return candidate if _looks_like_markup_attachment(raw_bytes) else None
        return candidate
    return candidate if _matches_binary_signature(candidate, raw_bytes) else None


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

        raw_size = len(raw_bytes)
        if raw_size > ATTACHMENT_MAX_BYTES:
            skipped_count += 1
            hit_file_size_limit = True
            continue
        if total_bytes + raw_size > MAX_ATTACHMENT_TOTAL_BYTES:
            skipped_count += 1
            hit_total_size_limit = True
            continue

        mime_type = _validated_attachment_mime_type(
            name=selected,
            declared_mime_type=_guess_attachment_mime_type(selected),
            raw_bytes=raw_bytes,
        )
        if not mime_type:
            skipped_count += 1
            continue
        payloads.append(
            {
                "name": os.path.basename(selected),
                "path": selected,
                "type": mime_type,
                "data": f"data:{mime_type};base64,{base64.b64encode(raw_bytes).decode('ascii')}",
            }
        )
        total_bytes += raw_size

    return payloads, skipped_count, hit_file_size_limit, hit_total_size_limit


def decode_data_url(data_url: str) -> tuple[str, bytes] | None:
    if not data_url.startswith("data:"):
        return None
    header, separator, payload = data_url.partition(",")
    if not separator:
        return None
    meta = header[5:]
    meta_parts = [part.strip() for part in meta.split(";") if part.strip()]
    is_base64 = any(part.lower() == "base64" for part in meta_parts[1:])
    mime_type = _normalize_mime_type(meta_parts[0] if meta_parts else "application/octet-stream") or "application/octet-stream"
    try:
        data = base64.b64decode(payload, validate=True) if is_base64 else unquote_to_bytes(payload)
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

    allowed_root_keys = {"text", "attachments", "kind"}
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


def parse_send_payload_kind(raw_text: str) -> str:
    parsed_text = raw_text.strip()
    if not parsed_text:
        return "user"
    try:
        payload = json.loads(parsed_text)
    except json.JSONDecodeError:
        return "user"

    if not isinstance(payload, dict):
        return "user"

    normalized = str(payload.get("kind") or "").strip().lower()
    if normalized == "agent_prompt":
        return "agent_prompt"
    return "user"


def materialize_attachments(attachments: list[dict[str, str]]) -> list[str]:
    temp_paths: list[str] = []
    total_bytes = 0
    for attachment in attachments:
        decoded = decode_data_url(attachment.get("data", ""))
        if decoded is None:
            continue
        decoded_mime_type, raw_bytes = decoded
        if len(raw_bytes) > ATTACHMENT_MAX_BYTES:
            continue
        mime_type = _validated_attachment_mime_type(
            name=attachment.get("name", "attachment"),
            declared_mime_type=attachment.get("type") or decoded_mime_type,
            raw_bytes=raw_bytes,
        )
        if not mime_type:
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
