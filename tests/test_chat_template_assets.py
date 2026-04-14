"""Tests for chat template glass tokens and behavior hooks."""

from __future__ import annotations

import hashlib
import re

from claude_code_gui.assets.chat_template import CHAT_WEBVIEW_HTML
from pathlib import Path


def _extract_rules(html: str, selector: str) -> list[str]:
    rules: list[str] = []
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", html, flags=re.DOTALL):
        if selector in selectors:
            rules.append(body)
    return rules


def test_glass_classes_have_backdrop_filter_and_tint() -> None:
    classes = [
        "folder-path-btn",
        "plus-btn",
        "selector-btn",
        "permission-btn",
        "permission-selector",
        "assistant-action",
        "chip",
        "artifact-action-btn",
        "action-btn",
        "code-copy-btn",
        "quick-chip",
        "stop-process-btn",
        "example-prompt",
        "popup-menu",
    ]
    for cls in classes:
        selector = f".{cls}"
        rules = _extract_rules(CHAT_WEBVIEW_HTML, selector)
        assert rules, selector
        assert any(
            "backdrop-filter: blur(" in rule and "-webkit-backdrop-filter: blur(" in rule
            for rule in rules
        ), selector
        assert any("var(--glass-tint-interactive" in rule for rule in rules), selector


def test_popup_option_no_backdrop_filter() -> None:
    rules = _extract_rules(CHAT_WEBVIEW_HTML, ".popup-option")
    assert rules, ".popup-option"
    assert all("backdrop-filter" not in rule for rule in rules)
    assert any("background: transparent" in rule for rule in rules)


def test_reduced_motion_media_query_exists() -> None:
    assert "@media (prefers-reduced-motion: reduce)" in CHAT_WEBVIEW_HTML
    assert "body.reduced-motion" in CHAT_WEBVIEW_HTML
    assert "window.setReducedMotion" in CHAT_WEBVIEW_HTML


def test_reduced_transparency_media_query_exists() -> None:
    assert "@media (prefers-reduced-transparency: reduce)" in CHAT_WEBVIEW_HTML


def test_motion_one_injected() -> None:
    assert "window.Motion" in CHAT_WEBVIEW_HTML
    assert "window.Motion.animate" in CHAT_WEBVIEW_HTML
    assert "__INLINE_MOTION_ONE_JS__" not in CHAT_WEBVIEW_HTML


def test_spring_press_signature_present() -> None:
    assert "duration: 0.28" in CHAT_WEBVIEW_HTML
    assert "[1, 0.96, 1]" in CHAT_WEBVIEW_HTML
    assert "window.Motion.spring" in CHAT_WEBVIEW_HTML


def test_glass_hover_will_change_clear_on_leave() -> None:
    assert "GLASS_ACTIVE_ANIMATIONS" in CHAT_WEBVIEW_HTML


def test_motion_one_vendor_integrity() -> None:
    motion_content = Path("claude_code_gui/assets/vendor/motion.min.js").read_text(encoding="utf-8")
    digest = hashlib.sha256(motion_content.encode("utf-8")).hexdigest()
    versions = Path("claude_code_gui/assets/vendor/VERSIONS.md").read_text(encoding="utf-8")
    assert digest in versions
