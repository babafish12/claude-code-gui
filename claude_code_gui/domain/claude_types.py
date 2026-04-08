"""Data contracts for Claude CLI run configuration and results."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClaudeRunResult:
    success: bool
    assistant_text: str
    streamed_assistant: bool
    conversation_id: str | None
    error_message: str | None


@dataclass
class ClaudeRunConfig:
    binary_path: str
    message: str
    cwd: str
    model: str
    permission_mode: str
    conversation_id: str | None
    supports_model_flag: bool
    supports_permission_flag: bool
    supports_output_format_flag: bool
    supports_stream_json: bool
    supports_json: bool
    stream_json_requires_verbose: bool
