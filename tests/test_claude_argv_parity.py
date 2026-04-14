"""Parity checks for ClaudeDialect argv generation against legacy HEAD behavior.

Legacy source of truth:
    git show HEAD:claude_code_gui/runtime/claude_process.py
"""

from __future__ import annotations

import itertools
import unittest

from claude_code_gui.domain.cli_dialect import ClaudeDialect, CliRunConfig


def _legacy_head_build_argv(prompt: str, config: CliRunConfig) -> list[str]:
    """Reconstruct the legacy HEAD argv shape from ClaudeProcess._run_single_attempt."""
    argv = [config.binary_path, "-p", prompt]

    mode = str(config.output_format or "").strip().lower()
    if mode in {"stream-json", "json"}:
        argv.extend(["--output-format", mode])

    if mode == "stream-json" and config.stream_json_requires_verbose:
        argv.append("--verbose")
    if mode == "stream-json" and config.supports_include_partial_messages:
        argv.append("--include-partial-messages")

    if config.supports_model_flag:
        argv.extend(["--model", config.model])

    if config.supports_permission_flag:
        argv.extend(["--permission-mode", config.permission_mode])

    if config.supports_reasoning_flag and config.reasoning_level:
        argv.extend(["--effort", config.reasoning_level])

    # Important parity detail: legacy HEAD did not append --allowedTools.
    return argv


def _legacy_head_build_resume_argv(session_id: str, prompt: str, config: CliRunConfig) -> list[str]:
    argv = _legacy_head_build_argv(prompt, config)
    if session_id:
        argv.extend(["--resume", session_id])
    return argv


def run_parity_matrix() -> tuple[int, int]:
    dialect = ClaudeDialect()
    modes = ("stream-json", "json", "text")
    allowed_tools_cases = (None, [], ["Bash", "Edit"])

    checked = 0
    mismatches = 0

    bool_cases = itertools.product((False, True), repeat=7)
    for (
        supports_output_format_flag,
        stream_json_requires_verbose,
        supports_include_partial_messages,
        supports_model_flag,
        supports_permission_flag,
        supports_reasoning_flag,
        resume,
    ) in bool_cases:
        for mode in modes:
            if not supports_output_format_flag and mode != "text":
                continue
            for allowed_tools in allowed_tools_cases:
                config = CliRunConfig(
                    binary_path="/usr/bin/claude",
                    cwd="/tmp",
                    model="sonnet",
                    permission_mode="plan",
                    reasoning_level="medium",
                    allowed_tools=allowed_tools,
                    output_format=mode,
                    supports_model_flag=supports_model_flag,
                    supports_permission_flag=supports_permission_flag,
                    supports_output_format_flag=supports_output_format_flag,
                    supports_include_partial_messages=supports_include_partial_messages,
                    stream_json_requires_verbose=stream_json_requires_verbose,
                    supports_reasoning_flag=supports_reasoning_flag,
                )

                prompt = "hello"
                session_id = "sess-1"

                if resume:
                    actual = dialect.build_resume_argv(session_id, prompt, config)
                    expected = _legacy_head_build_resume_argv(session_id, prompt, config)
                else:
                    actual = dialect.build_argv(prompt, config)
                    expected = _legacy_head_build_argv(prompt, config)

                checked += 1
                if actual != expected:
                    mismatches += 1

    return checked, mismatches


class TestClaudeArgvParity(unittest.TestCase):
    def test_parity_including_allowed_tools_cases(self) -> None:
        checked, mismatches = run_parity_matrix()
        self.assertEqual(checked, 768)
        self.assertEqual(mismatches, 0)


if __name__ == "__main__":
    checked, mismatches = run_parity_matrix()
    print(f"claude-argv-combinations: {checked}")
    print(f"claude-argv-mismatches: {mismatches}")
    if mismatches != 0:
        raise SystemExit(1)
