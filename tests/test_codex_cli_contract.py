from __future__ import annotations

import json
import os
import subprocess

import pytest

from claude_code_gui.services.binary_probe import find_provider_binary, is_codex_authenticated

pytestmark = [
    pytest.mark.contract,
    pytest.mark.skipif(
        os.getenv("RUN_CONTRACT_TESTS") != "1",
        reason="Contract tests disabled (set RUN_CONTRACT_TESTS=1)",
    ),
]


def _require_codex_binary() -> str:
    binary = find_provider_binary(["codex"])
    if not binary:
        pytest.skip("codex binary not found")
    return binary


def test_codex_exec_help_contract() -> None:
    binary = _require_codex_binary()

    result = subprocess.run(
        [binary, "exec", "--help"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    output = f"{result.stdout}\n{result.stderr}".lower()
    assert result.returncode == 0
    assert "exec" in output
    assert "--json" in output


def test_codex_jsonl_schema_contract() -> None:
    binary = _require_codex_binary()
    if not is_codex_authenticated():
        pytest.skip("codex is not authenticated")

    result = subprocess.run(
        [
            binary,
            "exec",
            "--json",
            "--color",
            "never",
            "-s",
            "read-only",
            "Reply exactly with OK",
        ],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )

    assert result.returncode == 0, f"codex exec failed: {result.stderr.strip() or result.stdout.strip()}"

    events: list[dict] = []
    for line in (result.stdout.splitlines() + result.stderr.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            events.append(parsed)

    assert events, "No JSONL events detected in codex output"

    event_types = {str(event.get("type") or "") for event in events}
    assert "thread.started" in event_types
    assert "turn.completed" in event_types or "turn.error" in event_types

    if "turn.completed" in event_types:
        turn_event = next(event for event in events if event.get("type") == "turn.completed")
        usage = turn_event.get("usage")
        assert isinstance(usage, dict)
        assert isinstance(usage.get("input_tokens"), int)
        assert isinstance(usage.get("output_tokens"), int)
