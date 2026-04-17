from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from claude_code_gui.services import attachment_service

pytestmark = pytest.mark.unit


def _data_url(payload: bytes, mime_type: str = "text/plain") -> str:
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def test_decode_data_url_supports_base64_and_urlencoded_payloads() -> None:
    decoded = attachment_service.decode_data_url(_data_url(b"hello", "text/plain"))
    assert decoded == ("text/plain", b"hello")

    decoded_text = attachment_service.decode_data_url("data:text/plain,hello%20world")
    assert decoded_text == ("text/plain", b"hello world")

    assert attachment_service.decode_data_url("not-a-data-url") is None
    assert attachment_service.decode_data_url("data:text/plain") is None


def test_parse_send_payload_validates_schema_and_normalizes_attachments() -> None:
    payload = json.dumps(
        {
            "text": "  hello  ",
            "attachments": [
                {
                    "name": "image",
                    "type": "application/octet-stream",
                    "data": _data_url(b"png-bytes", "image/png"),
                },
                {
                    "name": "ignored-extra-key",
                    "type": "text/plain",
                    "data": _data_url(b"x"),
                    "extra": "not-allowed",
                },
                {"name": "missing-data", "type": "text/plain", "data": ""},
            ],
        }
    )

    message, attachments = attachment_service.parse_send_payload(payload)

    assert message == "hello"
    assert len(attachments) == 1
    assert attachments[0]["name"] == "image"
    assert attachments[0]["type"] == "image/png"

    rejected_message, rejected_attachments = attachment_service.parse_send_payload(
        '{"text":"hello","unexpected":true}'
    )
    assert rejected_message == ""
    assert rejected_attachments == []


def test_parse_send_payload_enforces_attachment_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    one_attachment = {
        "name": "file.txt",
        "type": "text/plain",
        "data": _data_url(b"x"),
    }
    many = [dict(one_attachment, name=f"file-{i}.txt") for i in range(attachment_service.MAX_ATTACHMENTS_PER_MESSAGE + 3)]

    message, attachments = attachment_service.parse_send_payload(
        json.dumps({"text": "ok", "attachments": many})
    )

    assert message == "ok"
    assert len(attachments) == attachment_service.MAX_ATTACHMENTS_PER_MESSAGE

    monkeypatch.setattr(attachment_service, "MAX_DATA_URL_CHARS", 10)
    _, long_attachment = attachment_service.parse_send_payload(
        json.dumps(
            {
                "text": "ok",
                "attachments": [{"name": "long", "type": "text/plain", "data": _data_url(b"way-too-long")}],
            }
        )
    )
    assert long_attachment == []


def test_materialize_attachments_respects_size_and_total_limits() -> None:
    attachments = [
        {"name": "first.txt", "data": _data_url(b"1234"), "type": "text/plain"},
        {"name": "second.txt", "data": _data_url(b"5678"), "type": "text/plain"},
    ]

    original_per_file_limit = attachment_service.ATTACHMENT_MAX_BYTES
    original_total_limit = attachment_service.MAX_ATTACHMENT_TOTAL_BYTES
    paths: list[str] = []
    try:
        attachment_service.ATTACHMENT_MAX_BYTES = 10
        attachment_service.MAX_ATTACHMENT_TOTAL_BYTES = 6
        paths = attachment_service.materialize_attachments(attachments)
    finally:
        attachment_service.ATTACHMENT_MAX_BYTES = original_per_file_limit
        attachment_service.MAX_ATTACHMENT_TOTAL_BYTES = original_total_limit

    try:
        assert len(paths) == 1
        written = Path(paths[0]).read_bytes()
        assert written == b"1234"
    finally:
        attachment_service.cleanup_temp_paths(paths)


def test_materialize_compose_and_cleanup_roundtrip() -> None:
    paths = attachment_service.materialize_attachments(
        [{"name": "notes.txt", "data": _data_url(b"hello"), "type": "text/plain"}]
    )

    try:
        assert len(paths) == 1
        assert Path(paths[0]).is_file()

        composed = attachment_service.compose_message_with_attachments("Use this", paths)
        assert composed.startswith("Use this")
        assert "Attached files:" in composed
        assert f"- {paths[0]}" in composed

        default_composed = attachment_service.compose_message_with_attachments("   ", paths)
        assert default_composed.startswith("Please use the attached files as context.")
    finally:
        attachment_service.cleanup_temp_paths(paths)
        attachment_service.cleanup_temp_paths(["", paths[0], "/tmp/definitely-not-existing-attachment"])


def test_encode_host_attachment_payloads_builds_data_urls(tmp_path: Path) -> None:
    first = tmp_path / "image.png"
    first.write_bytes(b"\x89PNG")
    second = tmp_path / "note.txt"
    second.write_text("hello", encoding="utf-8")

    payloads, skipped_count, hit_file_size_limit, hit_total_size_limit = attachment_service.encode_host_attachment_payloads(
        [str(first), str(second)]
    )

    assert skipped_count == 0
    assert hit_file_size_limit is False
    assert hit_total_size_limit is False
    assert len(payloads) == 2
    assert payloads[0]["name"] == "image.png"
    assert payloads[0]["type"] == "image/png"
    assert payloads[0]["data"].startswith("data:image/png;base64,")
    assert payloads[1]["name"] == "note.txt"
    assert payloads[1]["type"] == "text/plain"


def test_encode_host_attachment_payloads_respects_limits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    small = tmp_path / "small.txt"
    small.write_text("abc", encoding="utf-8")
    big = tmp_path / "big.bin"
    big.write_bytes(b"x" * 20)

    monkeypatch.setattr(attachment_service, "ATTACHMENT_MAX_BYTES", 10)
    monkeypatch.setattr(attachment_service, "MAX_ATTACHMENT_TOTAL_BYTES", 5)

    payloads, skipped_count, hit_file_size_limit, hit_total_size_limit = attachment_service.encode_host_attachment_payloads(
        [str(small), str(big), str(small)]
    )

    assert len(payloads) == 1
    assert skipped_count == 2
    assert hit_file_size_limit is True
    assert hit_total_size_limit is True
