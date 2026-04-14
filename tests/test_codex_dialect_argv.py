"""Codex dialect argv contract checks."""

from __future__ import annotations

import unittest

from claude_code_gui.domain.cli_dialect import CliRunConfig, CodexDialect


class CodexDialectArgvTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dialect = CodexDialect()
        self.config = CliRunConfig(
            binary_path="/usr/bin/codex",
            cwd="/tmp/workspace",
            model="gpt-5",
            permission_mode="auto",
            disable_color=True,
        )

    def test_fresh_argv_uses_exec_options_before_prompt(self) -> None:
        argv = self.dialect.build_argv("hello", self.config)
        self.assertEqual(argv[:2], ["/usr/bin/codex", "exec"])
        self.assertIn("--json", argv)
        self.assertIn("--color", argv)
        self.assertIn("-C", argv)
        self.assertEqual(argv[-1], "hello")

    def test_resume_argv_uses_resume_options_without_color_or_cwd(self) -> None:
        argv = self.dialect.build_resume_argv("thread-123", "resume prompt", self.config)
        self.assertEqual(argv[:3], ["/usr/bin/codex", "exec", "resume"])
        self.assertIn("--json", argv)
        self.assertNotIn("--color", argv)
        self.assertNotIn("-C", argv)
        self.assertEqual(argv[-2:], ["thread-123", "resume prompt"])

    def test_parse_line_turn_failed_emits_error_event(self) -> None:
        events = self.dialect.parse_line('{"type":"turn.failed","message":"Model rejected request"}')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].raw_type, "turn.failed")
        self.assertEqual(events[0].error, "Model rejected request")


if __name__ == "__main__":
    unittest.main()
